import requests
import json
import time
import logging
import random
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from tools.syndrdb_client import SyndrDBClient

class BaseAgent:
    """Base class for all agents using Ollama and SyndrDB"""
    
    def __init__(
        self,
        agent_id: str,
        persona_name: str,
        syndrdb_host: str = "127.0.0.1",
        syndrdb_port: int = 1776,
        syndrdb_database: str = "primary",
        ollama_url: str = "http://localhost:11434",
        connection_timeout: int = 60
    ):
        self.agent_id = agent_id
        self.persona_name = persona_name
        self.ollama_url = ollama_url
        # Use connection string format with credentials
        conn_str = f"syndrdb://{syndrdb_host}:{syndrdb_port}:{syndrdb_database}:root:root"
        self.db_client = SyndrDBClient(conn_str, timeout=connection_timeout)
        
        # Set up per-agent logger with dedicated file
        self.logger = self._setup_agent_logger()
        
        # Metrics
        self.queries_executed = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.total_latency = 0
        self.total_server_execution_ms = 0.0  # Sum of all ServerExecutionMS values
        self.errors = []
        self.transaction_counter = 0  # For tracking individual query executions

        # Session state
        self.session_memory = []  # Remember past actions
        self.current_context = {}
        
        # Pre-generated queries and execution results
        self.pregenerated_queries: List[str] = []
        self.execution_results: List[Dict[str, Any]] = []
    
    def _setup_agent_logger(self) -> logging.Logger:
        """Create a dedicated logger for this agent with its own log file"""
        # Create logger with agent-specific name
        agent_logger = logging.getLogger(f"agent.{self.agent_id}")
        agent_logger.setLevel(logging.INFO)
        agent_logger.propagate = False  # Don't propagate to root logger
        
        # Create results/agents directory if it doesn't exist
        Path("results/agents").mkdir(parents=True, exist_ok=True)
        
        # Create file handler for this agent
        log_file = f"results/agents/{self.agent_id}.log"
        file_handler = logging.FileHandler(log_file, mode='w')  # 'w' to start fresh each run
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        agent_logger.addHandler(file_handler)
        
        return agent_logger
        
    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API for agent decision-making"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2:1b",
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                },
                timeout=30
            )

            # check for HTTP errors
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                self.logger.error(f"Ollama API error: {response.status_code}")
                return ""
            
        except Exception as e:
            self.logger.error(f"Ollama call failed: {e}")
            return ""
    
    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute query and track metrics"""
        
        self.queries_executed += 1
        self.transaction_counter += 1
        txn_id = self.transaction_counter
        
        # Log which persona is executing which query - FULL query, no truncation
        self.logger.info(f"[{self.agent_id}] TXN-{txn_id} EXECUTING: {query}")
        
        result = self.db_client.execute(query)
        
        if result.get("success"):
            self.successful_queries += 1
            self.total_latency += result.get("latency_ms", 0)
            
            # Extract server execution time from response
            server_exec_time = "MISSING"
            if "result" in result and isinstance(result["result"], dict):
                if "ExecutionTimeMS" in result["result"]:
                    server_exec_ms = result['result']['ExecutionTimeMS']
                    server_exec_time = f"{server_exec_ms:.4f}"
                    self.total_server_execution_ms += server_exec_ms
            
            self.logger.info(f"[{self.agent_id}] TXN-{txn_id} ✓ Success - {result.get('latency_ms', 0):.2f}ms ServerExecutionMS: {server_exec_time}")
        else:
            self.failed_queries += 1
            self.errors.append({
                "query": query,
                "error": result.get("error"),
                "timestamp": time.time()
            })
            self.logger.error(f"[{self.agent_id}] TXN-{txn_id} ✗ Failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return agent metrics"""
        avg_latency = (
            self.total_latency / self.successful_queries 
            if self.successful_queries > 0 
            else 0
        )
        
        # Calculate Agent QPS: queries / (total_server_execution_ms / 1000)
        agent_qps = 0.0
        if self.total_server_execution_ms > 0:
            total_server_execution_sec = self.total_server_execution_ms / 1000.0
            agent_qps = self.queries_executed / total_server_execution_sec
        
        return {
            "agent_id": self.agent_id,
            "persona":  self.persona_name,
            "queries_executed": self.queries_executed,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (
                self.successful_queries / self.queries_executed 
                if self.queries_executed > 0 
                else 0
            ),
            "avg_latency_ms": avg_latency,
            "agent_qps": agent_qps,
            "error_count": len(self.errors)
        }
    
    def start_session(self):
        """Start agent session"""
        self.db_client.connect()
        self.logger.info(f"[{self.agent_id}] Session started as {self.persona_name}")
    
    def end_session(self):
        """End agent session"""
        self.db_client.disconnect()
        metrics = self.get_metrics()
        self.logger.info(f"[{self.agent_id}] Session ended. Metrics: {metrics}")
    
    def run_pregenerated_session(self, think_time_range: tuple = (1, 3), stop_time: float = None, skip_connect: bool = False):
        """
        Run session using pre-generated queries.
        
        This method replaces the standard run_session when queries are pre-generated.
        It executes each query in sequence, tracking detailed metrics.
        Queries are sent synchronously - each query waits for a response before the next is sent.
        
        Args:
            think_time_range: Tuple of (min, max) seconds to wait between queries.
                             Set to (0, 0) for no delay (continuous synchronous execution)
            stop_time: Unix timestamp when execution should stop (None = run all queries)
            skip_connect: If True, skip connection (agent already connected by orchestrator)
        """
        if not self.pregenerated_queries:
            self.logger.error(f"[{self.agent_id}] No pre-generated queries available!")
            return
        
        # Log execution mode
        if think_time_range == (0, 0):
            self.logger.info(
                f"[{self.agent_id}] ({self.persona_name}) Starting NO-DELAY mode: "
                f"{len(self.pregenerated_queries)} queries (synchronous, wait-for-response)"
            )
        else:
            self.logger.info(
                f"[{self.agent_id}] ({self.persona_name}) Starting pre-generated session "
                f"with {len(self.pregenerated_queries)} queries "
                f"(delay: {think_time_range[0]}-{think_time_range[1]}s between queries)"
            )
        
        # Only connect if not already connected
        if not skip_connect:
            self.start_session()
        else:
            self.logger.info(f"[{self.agent_id}] Using existing connection (already connected by orchestrator)")
        
        session_start_time = time.time()
        
        # Track total queries executed and cycles through query list
        total_queries_executed = 0
        cycle_count = 0
        
        # Execute queries, cycling back to beginning if time remains
        while True:
            cycle_count += 1
            if cycle_count > 1:
                self.logger.info(
                    f"[{self.agent_id}] ({self.persona_name}) Starting query cycle {cycle_count} "
                    f"(looping back to beginning)"
                )
            
            for idx, query in enumerate(self.pregenerated_queries):
                # Check if we should stop
                if stop_time is not None and time.time() >= stop_time:
                    self.logger.info(
                        f"[{self.agent_id}] ({self.persona_name}) Stopping due to time limit. "
                        f"Executed {total_queries_executed} total queries across {cycle_count} cycle(s)."
                    )
                    break
                
                # Timestamp before sending (with nanosecond precision)
                time_sent_ns = time.time_ns()
                timestamp_sent = datetime.now().isoformat()
                time_sent = time.time()
                
                # Execute query (synchronous - waits for response before continuing)
                result = self._execute_query(query)
                total_queries_executed += 1
                
                # Timestamp after receiving (with nanosecond precision)
                time_received_ns = time.time_ns()
                timestamp_received = datetime.now().isoformat()
                time_received = time.time()
                elapsed_ms = (time_received - time_sent) * 1000
                elapsed_ns = time_received_ns - time_sent_ns
                
                # Extract row count if available
                row_count = 0
                if result.get("success"):
                    result_data = result.get("result", {})
                    result_array = result_data.get("Result", [])
                    if isinstance(result_array, list):
                        row_count = len(result_array)
                
                # Store detailed execution result with FULL query and nanosecond precision
                execution_detail = {
                    "transaction_id": self.transaction_counter,
                    "query_index": total_queries_executed,
                    "cycle": cycle_count,
                    "original_query_index": idx + 1,
                    "timestamp_sent": timestamp_sent,
                    "timestamp_sent_ns": time_sent_ns,
                    "timestamp_received": timestamp_received,
                    "timestamp_received_ns": time_received_ns,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "elapsed_ns": elapsed_ns,
                    "statement": query,  # FULL query, no truncation
                    "status": "success" if result.get("success") else "error",
                    "error_message": result.get("error", "") if not result.get("success") else "",
                    "response_count": row_count
                }
                
                self.execution_results.append(execution_detail)
                
                # Think time between queries
                # When think_time_range is (0, 0), no delay - but queries still execute synchronously
                if think_time_range != (0, 0):
                    think_time = random.uniform(*think_time_range)
                    time.sleep(think_time)
            else:
                # Inner for loop completed without break - check if we should continue cycling
                if stop_time is None:
                    # No time limit, just run once
                    break
                elif time.time() >= stop_time:
                    # Time's up
                    break
                # Otherwise, continue to next cycle
                continue
            
            # Inner for loop was broken (time limit reached), exit outer while loop
            break
        
        session_duration = time.time() - session_start_time
        
        self.end_session()
        
        self.logger.info(
            f"[{self.agent_id}] ({self.persona_name}) Pre-generated session complete. "
            f"Executed {total_queries_executed} queries across {cycle_count} cycle(s) in {session_duration:.1f}s"
        )
