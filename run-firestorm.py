#!/usr/bin/env python3
# firestorm/run-firestorm.py
"""
🔥 Syndr Firestorm - AI-Driven Concurrent Load Testing Framework
Main orchestrator for spawning agents and running load tests against SyndrDB
"""

import argparse
import logging
import sys
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

from conductor.conductor import FirestormConductor
from agents.casual_browser import CasualBrowserAgent
from agents.power_user_agent import PowerUserAgent
from agents.admin_agent import AdminAgent
from agents.analyst_agent import AnalystAgent
from agents.personas import PERSONAS
from tools.mmap_logger import setup_mmap_logging, register_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('results/firestorm.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Set up memory-mapped logging on a separate thread
mmap_handler = setup_mmap_logging(
    filepath='results/firestorm_mmap.log',
    max_size=100 * 1024 * 1024,  # 100 MB
    level=logging.INFO
)
register_handler(mmap_handler)
logger.info("Memory-mapped logging initialized")

# Realistic agent distribution (10 casual, 6 power, 2 admin, 2 analyst)
AGENT_DISTRIBUTION = {
    "casual_browser": 10,
    "power_user": 6,
    "admin": 2,
    "analyst": 2
}

class FirestormOrchestrator:
    """Main orchestrator for Firestorm load testing"""
    
    def __init__(
        self,
        num_agents: int = 20,
        duration_minutes: int = 30,
        syndrdb_host: str = "127.0.0.1",
        syndrdb_port: int = 1776,
        ollama_url: str = "http://localhost:11434",
        setup_env: bool = True,
        no_delay: bool = False,
        uniform_delay_ms: Optional[int] = None,
        batch_conns: int = 10,
        read_only: bool = False,
        write_only: bool = False
    ):
        self.num_agents = num_agents
        self.duration_seconds = duration_minutes * 60
        self.syndrdb_host = syndrdb_host
        self.syndrdb_port = syndrdb_port
        self.ollama_url = ollama_url
        self.setup_env = setup_env
        self.no_delay = no_delay
        self.uniform_delay_ms = uniform_delay_ms
        self.batch_conns = batch_conns
        self.read_only = read_only
        self.write_only = write_only
        
        self.agents: List[Any] = []
        self.agent_threads: List[threading.Thread] = []
        self.conductor = FirestormConductor(syndrdb_host, syndrdb_port, 
                                           username="root", password="root", database="primary")
        
        self.test_start_time: float = 0
        self.test_end_time: float = 0
        self.stop_time: float = 0  # When the test should stop
        self.running = False
        
        # Create results directory
        Path("results").mkdir(exist_ok=True)
        
    def setup_environment(self):
        """Set up test environment"""
        logger.info("🔥 FIRESTORM: Setting up test environment...")
        self.conductor.setup_test_environment()
        logger.info("✅ Environment setup complete!")
        
    def create_agents(self):
        """Create agent instances based on distribution"""
        logger.info(f"🔥 FIRESTORM: Creating {self.num_agents} agents...")
        
        # Calculate distribution based on num_agents
        total_weight = sum(AGENT_DISTRIBUTION.values())
        agent_counts = {}
        
        for persona, weight in AGENT_DISTRIBUTION.items():
            count = max(1, int((weight / total_weight) * self.num_agents))
            agent_counts[persona] = count
        
        # Adjust to match exact num_agents
        current_total = sum(agent_counts.values())
        if current_total < self.num_agents:
            # Add remaining to casual_browser
            agent_counts["casual_browser"] += (self.num_agents - current_total)
        elif current_total > self.num_agents:
            # Remove from casual_browser
            agent_counts["casual_browser"] -= (current_total - self.num_agents)
        
        logger.info(f"Agent distribution: {agent_counts}")
        
        # Create agents
        agent_id = 1
        for persona, count in agent_counts.items():
            for i in range(count):
                agent = self._create_agent(f"agent_{agent_id}", persona)
                if agent:
                    self.agents.append(agent)
                    agent_id += 1
        
        logger.info(f"✅ Created {len(self.agents)} agents")
    
    def pregenerate_queries(self):
        """Pre-generate queries for all agents"""
        logger.info("🔥 FIRESTORM: Pre-generating queries...")
        total_queries = self.conductor.pregenerate_queries_for_agents(
            agents=self.agents,
            ollama_url=self.ollama_url
        )
        logger.info(f"✅ Pre-generated {total_queries} total queries across {len(self.agents)} agents")
    
    def clean_existing_files(self):
        """Delete existing manifest and query files"""
        logger.info("🧹 Cleaning existing manifest and query files...")
        
        # Delete manifest
        manifest_path = Path("results/firestorm_manifest.json")
        if manifest_path.exists():
            manifest_path.unlink()
            logger.info(f"   Deleted {manifest_path}")
        
        # Delete all agent query files
        results_dir = Path("results/agents")
        results_dir.mkdir(parents=True, exist_ok=True)
        query_files = list(results_dir.glob("agent_*_queries.json"))
        for query_file in query_files:
            query_file.unlink()
            logger.info(f"   Deleted {query_file}")
        
        logger.info(f"✅ Cleaned {len(query_files)} query files")
    
    def save_queries_to_files(self):
        """Save each agent's queries to individual files"""
        logger.info("💾 Saving queries to files...")
        
        # Create agents directory if it doesn't exist
        Path("results/agents").mkdir(parents=True, exist_ok=True)
        
        for agent in self.agents:
            if hasattr(agent, 'pregenerated_queries') and agent.pregenerated_queries:
                query_file = Path(f"results/agents/{agent.agent_id}_queries.json")
                
                with open(query_file, 'w') as f:
                    json.dump(agent.pregenerated_queries, f, indent=2)
                
                logger.info(f"   Saved {len(agent.pregenerated_queries)} queries to {query_file}")
        
        logger.info("✅ All queries saved to files")
    
    def load_queries_from_files(self):
        """Load queries from files into agents"""
        logger.info("📂 Loading queries from files...")
        
        total_loaded = 0
        for agent in self.agents:
            query_file = Path(f"results/agents/{agent.agent_id}_queries.json")
            
            if not query_file.exists():
                logger.error(f"❌ Query file not found: {query_file}")
                raise FileNotFoundError(f"Missing query file for {agent.agent_id}")
            
            with open(query_file, 'r') as f:
                queries = json.load(f)
            
            agent.pregenerated_queries = queries
            total_loaded += len(queries)
            logger.info(f"   Loaded {len(queries)} queries for {agent.agent_id}")
        
        logger.info(f"✅ Loaded {total_loaded} total queries from files")
        
        # Apply read-only filter if enabled
        if self.read_only:
            self.filter_queries_for_read_only()
        
        # Apply write-only filter if enabled
        if self.write_only:
            self.filter_queries_for_write_only()
    
    def filter_queries_for_read_only(self):
        """Filter agent queries to only include SELECT statements (read-only mode)"""
        logger.info("🔒 READ-ONLY MODE: Filtering out write operations (ADD, UPDATE, DELETE)...")
        
        total_original = 0
        total_filtered = 0
        
        for agent in self.agents:
            if not hasattr(agent, 'pregenerated_queries') or not agent.pregenerated_queries:
                continue
            
            original_count = len(agent.pregenerated_queries)
            total_original += original_count
            
            # Filter to only SELECT queries (case-insensitive check)
            # Exclude ADD, UPDATE, DELETE operations
            filtered_queries = []
            for query in agent.pregenerated_queries:
                query_upper = query.strip().upper()
                # Only keep SELECT queries, exclude write operations
                if query_upper.startswith('SELECT'):
                    filtered_queries.append(query)
                # Also allow SHOW commands (read-only metadata queries)
                elif query_upper.startswith('SHOW'):
                    filtered_queries.append(query)
            
            agent.pregenerated_queries = filtered_queries
            filtered_count = len(filtered_queries)
            total_filtered += filtered_count
            
            removed = original_count - filtered_count
            if removed > 0:
                logger.info(f"   {agent.agent_id}: Kept {filtered_count}/{original_count} queries (removed {removed} write operations)")
        
        removed_total = total_original - total_filtered
        logger.info(f"🔒 READ-ONLY: Kept {total_filtered}/{total_original} queries total (removed {removed_total} write operations)")
        
        if total_filtered == 0:
            logger.warning("⚠️  WARNING: No SELECT queries remaining after read-only filtering!")
    
    def filter_queries_for_write_only(self):
        """Filter agent queries to only include write operations (write-only mode)"""
        logger.info("✏️  WRITE-ONLY MODE: Filtering out read operations (SELECT, SHOW)...")
        
        total_original = 0
        total_filtered = 0
        
        for agent in self.agents:
            if not hasattr(agent, 'pregenerated_queries') or not agent.pregenerated_queries:
                continue
            
            original_count = len(agent.pregenerated_queries)
            total_original += original_count
            
            # Filter to only write queries (case-insensitive check)
            # Keep ADD, UPDATE, DELETE operations
            filtered_queries = []
            for query in agent.pregenerated_queries:
                query_upper = query.strip().upper()
                # Only keep write operations
                if query_upper.startswith('ADD'):
                    filtered_queries.append(query)
                elif query_upper.startswith('UPDATE'):
                    filtered_queries.append(query)
                elif query_upper.startswith('DELETE'):
                    filtered_queries.append(query)
            
            agent.pregenerated_queries = filtered_queries
            filtered_count = len(filtered_queries)
            total_filtered += filtered_count
            
            removed = original_count - filtered_count
            if removed > 0:
                logger.info(f"   {agent.agent_id}: Kept {filtered_count}/{original_count} queries (removed {removed} read operations)")
        
        removed_total = total_original - total_filtered
        logger.info(f"✏️  WRITE-ONLY: Kept {total_filtered}/{total_original} queries total (removed {removed_total} read operations)")
        
        if total_filtered == 0:
            logger.warning("⚠️  WARNING: No write queries remaining after write-only filtering!")
    
    def write_startup_manifest(self, include_query_files: bool = False):
        """Write startup configuration to JSON file"""
        logger.info("📝 Writing startup manifest...")
        
        manifest = {
            "start_time": datetime.now().isoformat(),
            "agents": []
        }
        
        # Collect agent information
        for agent in self.agents:
            agent_info = {
                "agent_id": agent.agent_id,
                "persona": agent.persona_name,
                "query_count": len(agent.pregenerated_queries) if hasattr(agent, 'pregenerated_queries') else 0
            }
            
            # Add query file name if requested
            if include_query_files:
                agent_info["query_file"] = f"{agent.agent_id}_queries.json"
            
            manifest["agents"].append(agent_info)
        
        # Write to file
        manifest_path = Path("results/firestorm_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"✅ Startup manifest written to {manifest_path}")
        logger.info(f"   Start time: {manifest['start_time']}")
        logger.info(f"   Total agents: {len(manifest['agents'])}")
        logger.info(f"   Total queries: {sum(a['query_count'] for a in manifest['agents'])}")
    
    def load_manifest(self):
        """Load manifest file and create agents based on it"""
        manifest_path = Path("results/firestorm_manifest.json")
        
        if not manifest_path.exists():
            logger.error(f"❌ Manifest file not found: {manifest_path}")
            logger.error("   Run with --test-gen first to generate queries")
            raise FileNotFoundError("Manifest file not found. Generate queries first with --test-gen")
        
        logger.info(f"📂 Loading manifest from {manifest_path}...")
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        logger.info(f"   Start time: {manifest['start_time']}")
        logger.info(f"   Total agents: {len(manifest['agents'])}")
        
        # Create agents based on manifest
        self.agents = []
        for agent_info in manifest['agents']:
            agent = self._create_agent(agent_info['agent_id'], agent_info['persona'])
            if agent:
                self.agents.append(agent)
        
        logger.info(f"✅ Created {len(self.agents)} agents from manifest")
        return manifest
    
    def _create_agent(self, agent_id: str, persona: str):
        """Create a single agent instance"""
        
        agent_class_map = {
            "casual_browser": CasualBrowserAgent,
            "power_user": PowerUserAgent,
            "admin": AdminAgent,
            "analyst": AnalystAgent
        }
        
        agent_class = agent_class_map.get(persona, CasualBrowserAgent)
        
        return agent_class(
            agent_id=agent_id,
            syndrdb_host=self.syndrdb_host,
            syndrdb_port=self.syndrdb_port,
            syndrdb_database=self.conductor.test_database,
            ollama_url=self.ollama_url
        )
    
    def connect_all_agents(self):
        """Connect all agents to SyndrDB in parallel batches before they start sending queries"""
        logger.info("🔥 FIRESTORM: Connecting all agents to SyndrDB...")
        logger.info(f"   Connecting {len(self.agents)} agents in batches of {self.batch_conns}...")
        
        connected_count = 0
        failed_agents = []
        batch_size = self.batch_conns
        
        def connect_agent(agent):
            """Connect a single agent and return result"""
            try:
                agent.db_client.connect()
                return (agent, True, None)
            except Exception as e:
                return (agent, False, str(e))
        
        # Process agents in batches
        for batch_start in range(0, len(self.agents), batch_size):
            batch_end = min(batch_start + batch_size, len(self.agents))
            batch = self.agents[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(self.agents) + batch_size - 1) // batch_size
            
            logger.info(f"   Batch {batch_num}/{total_batches}: Connecting {len(batch)} agents...")
            
            # Connect agents in this batch concurrently
            batch_threads = []
            batch_results = []
            
            for agent in batch:
                thread = threading.Thread(target=lambda a=agent: batch_results.append(connect_agent(a)))
                thread.start()
                batch_threads.append(thread)
            
            # Wait for all threads in this batch to complete
            for thread in batch_threads:
                thread.join()
            
            # Process results from this batch
            batch_success = 0
            batch_failed = 0
            for agent, success, error in batch_results:
                if success:
                    connected_count += 1
                    batch_success += 1
                else:
                    failed_agents.append(agent.agent_id)
                    batch_failed += 1
                    logger.error(f"     ✗ Failed to connect {agent.agent_id}: {error}")
            
            # Only log batch summary (not individual successes to reduce logging overhead)
            logger.info(f"   Batch {batch_num}/{total_batches} complete: {batch_success} connected, {batch_failed} failed")
        
        if failed_agents:
            logger.error(f"❌ Failed to connect {len(failed_agents)} agents: {failed_agents}")
            raise Exception(f"Agent connection failed for: {failed_agents}")
        
        logger.info(f"✅ All {connected_count} agents successfully connected to SyndrDB!")
        logger.info("   Agents are ready to send queries (waiting for all threads to start).")
    
    def _run_agent(self, agent, start_barrier: threading.Barrier):
        """Run a single agent until stop_time is reached"""
        try:
            # Wait at the barrier until all agent threads are ready
            agent.logger.info(f"[{agent.agent_id}] Waiting at start barrier for all agents to be ready...")
            start_barrier.wait()
            
            # After barrier, use the orchestrator's stop_time (set after all threads created)
            stop_time = self.stop_time
            agent.logger.info(f"[{agent.agent_id}] All agents ready - starting query execution!")
            
            # Check if agent has pre-generated queries
            if hasattr(agent, 'pregenerated_queries') and agent.pregenerated_queries:
                # Use pre-generated query execution mode
                from agents.personas import PERSONAS
                persona = PERSONAS.get(agent.persona_name, {})
                
                # Determine delay settings
                if self.no_delay:
                    think_time_range = (0, 0)
                elif self.uniform_delay_ms is not None:
                    delay_seconds = self.uniform_delay_ms / 1000.0
                    think_time_range = (delay_seconds, delay_seconds)
                else:
                    think_time_range = persona.get("think_time_seconds", (1, 3))
                
                # Run session without connecting (already connected)
                agent.run_pregenerated_session(think_time_range=think_time_range, stop_time=stop_time, skip_connect=True)
            else:
                # Fall back to original runtime generation mode
                agent.run_session(duration_minutes=(stop_time - time.time()) / 60)
        except Exception as e:
            logger.error(f"Agent {agent.agent_id} crashed: {e}")
    
    def start_test(self):
        """Start the load test"""
        logger.info("🔥🔥🔥 FIRESTORM TEST STARTING 🔥🔥🔥")
        logger.info(f"Agents: {self.num_agents}")
        logger.info(f"Duration: {self.duration_seconds / 60:.1f} minutes")
        logger.info(f"Target: {self.syndrdb_host}:{self.syndrdb_port}")
        if self.read_only:
            logger.info("🔒 Mode: READ-ONLY (SELECT queries only)")
        elif self.write_only:
            logger.info("✏️  Mode: WRITE-ONLY (ADD/UPDATE/DELETE queries only)")
        logger.info("")
        logger.info("Startup Sequence:")
        logger.info(f"  0. ✓ Created {self.num_agents} agents")
        logger.info(f"  1. ✓ Generated SQL statements for each agent")
        logger.info("  2. Connecting all agents to SyndrDB...")
        
        # Connect all agents first - everyone must be connected before any can send queries
        self.connect_all_agents()
        
        logger.info("  3. Starting query execution for all agents...")
        logger.info("")
        
        self.running = True
        
        # Create a barrier that all agents must wait at before starting queries
        # This ensures ALL agents are connected and ready before ANY agent starts sending queries
        # The barrier requires N+1 parties: N agents + the main thread
        # This way the main thread controls when all agents are released
        start_barrier = threading.Barrier(len(self.agents) + 1)
        
        # Start all agent threads (non-daemon so we can control shutdown)
        # Threads will wait at the barrier until all are ready
        for agent in self.agents:
            thread = threading.Thread(
                target=self._run_agent,
                args=(agent, start_barrier),
                daemon=False
            )
            thread.start()
            self.agent_threads.append(thread)
            logger.info(f"Started thread for {agent.agent_id} ({agent.persona_name})")
        
        logger.info(f"✅ All {len(self.agents)} agent threads started - synchronizing at barrier...")
        
        # Set the actual test timing RIGHT BEFORE releasing the barrier
        # This ensures all agents get the exact same stop_time when they start
        self.test_start_time = time.time()
        self.stop_time = self.test_start_time + self.duration_seconds
        
        # Main thread also waits at the barrier - this releases all agents simultaneously
        # Since we set stop_time above, all agents will read the correct value
        start_barrier.wait()
        
        logger.info(f"🚀 BARRIER RELEASED - All {len(self.agents)} agents now executing queries!")
        
        # Start health monitoring in background
        health_thread = threading.Thread(
            target=self._monitor_health,
            daemon=True
        )
        health_thread.start()
        
        logger.info("✅ All agents launched and sending queries!")
        
    def _monitor_health(self):
        """Monitor test health during execution"""
        while self.running:
            time.sleep(10)  # Check every 10 seconds
            
            # Count active agents
            active = sum(1 for t in self.agent_threads if t.is_alive())
            elapsed = time.time() - self.test_start_time
            remaining = max(0, self.duration_seconds - elapsed)
            
            logger.info(
                f"🔥 TEST STATUS: {active}/{len(self.agents)} agents active, "
                f"{elapsed/60:.1f}m elapsed, {remaining/60:.1f}m remaining"
            )
    
    def wait_for_completion(self):
        """Wait for all agents to complete or force stop at duration limit"""
        logger.info("Waiting for agents to complete...")
        
        # Calculate remaining time
        remaining_time = self.stop_time - time.time()
        
        if remaining_time > 0:
            # Wait for threads with a timeout equal to remaining time + 5 seconds grace
            timeout = remaining_time + 5
            logger.info(f"Waiting up to {timeout:.1f}s for agents to finish...")
            
            for thread in self.agent_threads:
                time_left = self.stop_time - time.time() + 5  # Grace period
                if time_left > 0:
                    thread.join(timeout=time_left)
                else:
                    break
        
        # Force stop if any threads are still running
        still_running = sum(1 for t in self.agent_threads if t.is_alive())
        if still_running > 0:
            logger.warning(f"⏰ Test duration reached! Forcing stop. {still_running} agents still running.")
        
        self.running = False
        self.test_end_time = time.time()
        
        logger.info("✅ All agents completed!")
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all agents"""
        logger.info("📊 Collecting metrics...")
        
        agent_metrics = []
        total_queries = 0
        total_successful = 0
        total_failed = 0
        total_latency_sum = 0
        
        for agent in self.agents:
            metrics = agent.get_metrics()
            agent_metrics.append(metrics)
            
            total_queries += metrics.get("queries_executed", 0)
            total_successful += metrics.get("successful_queries", 0)
            total_failed += metrics.get("failed_queries", 0)
            
            # Sum latency for average
            avg_latency = metrics.get("avg_latency_ms", 0)
            queries = metrics.get("successful_queries", 0)
            if queries > 0:
                total_latency_sum += avg_latency * queries
        
        # Calculate aggregate metrics
        test_duration = self.test_end_time - self.test_start_time
        avg_latency = total_latency_sum / total_successful if total_successful > 0 else 0
        
        aggregate = {
            "test_info": {
                "num_agents": self.num_agents,
                "duration_seconds": test_duration,
                "duration_minutes": test_duration / 60,
                "start_time": datetime.fromtimestamp(self.test_start_time).isoformat(),
                "end_time": datetime.fromtimestamp(self.test_end_time).isoformat()
            },
            "aggregate_metrics": {
                "total_queries": total_queries,
                "successful_queries": total_successful,
                "failed_queries": total_failed,
                "success_rate": (total_successful / total_queries * 100) if total_queries > 0 else 0,
                "avg_latency_ms": avg_latency,
                "queries_per_second": total_queries / test_duration if test_duration > 0 else 0
            },
            "agent_metrics": agent_metrics
        }
        
        return aggregate
    
    def save_results(self, metrics: Dict[str, Any]):
        """Save results to JSON and text files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save aggregated JSON
        json_file = f"results/firestorm_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"💾 Saved JSON metrics to {json_file}")
        
        # Save text summary
        text_file = f"results/firestorm_{timestamp}.txt"
        with open(text_file, 'w') as f:
            self._write_text_summary(f, metrics)
        logger.info(f"💾 Saved text summary to {text_file}")
        
        # Save detailed per-agent results
        self._save_detailed_agent_results(timestamp)
    
    def _save_detailed_agent_results(self, timestamp: str):
        """Save detailed execution results for each agent"""
        logger.info("💾 Saving detailed per-agent results...")
        
        # Create agents directory if it doesn't exist
        Path("results/agents").mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        for agent in self.agents:
            # Check if agent has execution results
            if not hasattr(agent, 'execution_results') or not agent.execution_results:
                continue
            
            # Generate filename: firestorm_{timestamp}_{persona}_{agent_id}.json
            filename = f"results/agents/firestorm_{timestamp}_{agent.persona_name}_{agent.agent_id}.json"
            
            # Prepare metadata and results
            output_data = {
                "metadata": {
                    "agent_id": agent.agent_id,
                    "persona": agent.persona_name,
                    "total_queries": len(agent.execution_results),
                    "test_timestamp": timestamp,
                    "successful_queries": agent.successful_queries,
                    "failed_queries": agent.failed_queries,
                    "success_rate": f"{(agent.successful_queries / len(agent.execution_results) * 100):.2f}%" if agent.execution_results else "0%",
                    "avg_latency_ms": f"{agent.total_latency / agent.successful_queries:.2f}" if agent.successful_queries > 0 else "0"
                },
                "execution_results": agent.execution_results
            }
            
            # Write to file with readable formatting
            with open(filename, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            saved_count += 1
            logger.info(f"   ✓ Saved {filename} ({len(agent.execution_results)} queries)")
        
        logger.info(f"💾 Saved {saved_count} detailed agent result files")

    
    def _write_text_summary(self, f, metrics: Dict[str, Any]):
        """Write human-readable summary"""
        f.write("=" * 80 + "\n")
        f.write("🔥 SYNDR FIRESTORM - LOAD TEST RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        # Test info
        info = metrics["test_info"]
        f.write(f"Test Duration: {info['duration_minutes']:.2f} minutes\n")
        f.write(f"Number of Agents: {info['num_agents']}\n")
        f.write(f"Start Time: {info['start_time']}\n")
        f.write(f"End Time: {info['end_time']}\n\n")
        
        # Aggregate metrics
        agg = metrics["aggregate_metrics"]
        f.write("-" * 80 + "\n")
        f.write("AGGREGATE METRICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Queries: {agg['total_queries']}\n")
        f.write(f"Successful: {agg['successful_queries']}\n")
        f.write(f"Failed: {agg['failed_queries']}\n")
        f.write(f"Success Rate: {agg['success_rate']:.2f}%\n")
        f.write(f"Avg Latency: {agg['avg_latency_ms']:.2f} ms\n")
        f.write(f"Queries/Second: {agg['queries_per_second']:.2f}\n\n")
        
        # Per-agent metrics
        f.write("-" * 80 + "\n")
        f.write("PER-AGENT METRICS\n")
        f.write("-" * 80 + "\n")
        for agent_m in metrics["agent_metrics"]:
            f.write(f"\nAgent: {agent_m['agent_id']} ({agent_m['persona']})\n")
            f.write(f"  Queries: {agent_m['queries_executed']}\n")
            f.write(f"  Success Rate: {agent_m['success_rate']*100:.2f}%\n")
            f.write(f"  Avg Latency: {agent_m['avg_latency_ms']:.2f} ms\n")
            f.write(f"  Errors: {agent_m['error_count']}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")
    
    def print_summary(self, metrics: Dict[str, Any]):
        """Print summary to console"""
        agg = metrics["aggregate_metrics"]
        
        print("\n" + "=" * 80)
        print("🔥🔥🔥 FIRESTORM TEST COMPLETE 🔥🔥🔥")
        print("=" * 80)
        print(f"\n✅ Total Queries: {agg['total_queries']}")
        print(f"✅ Success Rate: {agg['success_rate']:.2f}%")
        print(f"✅ Avg Latency: {agg['avg_latency_ms']:.2f} ms")
        print(f"✅ Queries/Second: {agg['queries_per_second']:.2f}")
        print("\n" + "=" * 80 + "\n")


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="🔥 Syndr Firestorm - AI-Driven Load Testing Framework"
    )
    
    parser.add_argument(
        '--agents',
        type=int,
        default=20,
        help='Number of concurrent agents (default: 20)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Test duration in minutes (default: 30)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='SyndrDB host (default: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=1776,
        help='SyndrDB port (default: 1776)'
    )
    
    parser.add_argument(
        '--ollama',
        type=str,
        default='http://localhost:11434',
        help='Ollama API URL (default: http://localhost:11434)'
    )
    
    parser.add_argument(
        '--no-setup',
        action='store_true',
        help='Skip environment setup (use existing database)'
    )
    
    parser.add_argument(
        '--quick-test',
        action='store_true',
        help='Quick test: 5 agents for 2 minutes'
    )
    
    parser.add_argument(
        '--test-gen',
        action='store_true',
        help='Generate queries and save to files (no execution)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Load queries from files and execute test'
    )
    
    parser.add_argument(
        '--no-delay',
        action='store_true',
        help='Remove all delays between queries (maximum load)'
    )
    
    parser.add_argument(
        '--uniform-delay',
        type=int,
        metavar='MS',
        help='Set uniform delay in milliseconds between all queries (overrides persona delays)'
    )
    
    parser.add_argument(
        '--batch-conns',
        type=int,
        default=10,
        help='Number of agents to connect simultaneously in each batch (default: 10)'
    )
    
    parser.add_argument(
        '--read-only',
        action='store_true',
        help='Only execute SELECT queries (no ADD, UPDATE, or DELETE operations)'
    )
    
    parser.add_argument(
        '--write-only',
        action='store_true',
        help='Only execute write queries (ADD, UPDATE, DELETE - no SELECT operations)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Validate mode selection
    if args.test_gen and args.execute:
        logger.error("❌ Cannot use --test-gen and --execute together")
        logger.error("   Use --test-gen to generate queries OR --execute to run the test")
        sys.exit(1)
    
    # Quick test override
    if args.quick_test:
        args.agents = 5
        args.duration = 2
        logger.info("🔥 Running QUICK TEST: 5 agents for 2 minutes")
    
    # Validate delay options
    if args.no_delay and args.uniform_delay:
        logger.error("❌ Cannot use --no-delay and --uniform-delay together")
        sys.exit(1)
    
    # Validate read-only and write-only mutual exclusion
    if args.read_only and args.write_only:
        logger.error("❌ Cannot use --read-only and --write-only together")
        logger.error("   Use --read-only for SELECT queries only")
        logger.error("   Use --write-only for ADD/UPDATE/DELETE queries only")
        logger.error("   Leave both off to allow mixed read and write operations")
        sys.exit(1)
    
    # Create orchestrator
    orchestrator = FirestormOrchestrator(
        num_agents=args.agents,
        duration_minutes=args.duration,
        syndrdb_host=args.host,
        syndrdb_port=args.port,
        ollama_url=args.ollama,
        setup_env=not args.no_setup,
        no_delay=args.no_delay,
        uniform_delay_ms=args.uniform_delay,
        batch_conns=args.batch_conns,
        read_only=args.read_only,
        write_only=args.write_only
    )
    
    try:
        # MODE 1: TEST GENERATION (--test-gen)
        if args.test_gen:
            logger.info("🔥 MODE: TEST GENERATION 🔥")
            logger.info("Generating queries and saving to files (no execution)\n")
            
            # Clean existing files
            orchestrator.clean_existing_files()
            
            # Setup environment
            if orchestrator.setup_env:
                orchestrator.setup_environment()
            
            # Create agents
            orchestrator.create_agents()
            
            # Pre-generate queries for all agents
            orchestrator.pregenerate_queries()
            
            # Save queries to files
            orchestrator.save_queries_to_files()
            
            # Write startup manifest with query file references
            orchestrator.write_startup_manifest(include_query_files=True)
            
            logger.info("\n🔥 QUERY GENERATION COMPLETE! 🔥")
            logger.info("Run with --execute to execute the test")
            print("SUCCESS")
            return
        
        # MODE 2: EXECUTION (--execute)
        elif args.execute:
            logger.info("🔥 MODE: EXECUTION 🔥")
            logger.info("Loading queries from files and executing test\n")
            
            # Load manifest (creates agents)
            orchestrator.load_manifest()
            
            # Load queries from files
            orchestrator.load_queries_from_files()
            
            # Start test
            orchestrator.start_test()
            
            # Wait for completion
            orchestrator.wait_for_completion()
            
            # Collect and save results
            metrics = orchestrator.collect_metrics()
            orchestrator.save_results(metrics)
            orchestrator.print_summary(metrics)
            
            logger.info("🔥 FIRESTORM COMPLETE! 🔥")
        
        # MODE 3: LEGACY (no switches - run everything)
        else:
            logger.info("🔥 MODE: FULL RUN (legacy) 🔥")
            logger.info("Running complete test (generation + execution)\n")
            
            # Setup environment
            if orchestrator.setup_env:
                orchestrator.setup_environment()
            
            # Create agents
            orchestrator.create_agents()
            
            # Pre-generate queries for all agents
            orchestrator.pregenerate_queries()
            
            # Apply read-only filter if enabled
            if orchestrator.read_only:
                orchestrator.filter_queries_for_read_only()
            
            # Apply write-only filter if enabled
            if orchestrator.write_only:
                orchestrator.filter_queries_for_write_only()
            
            # Write startup manifest
            orchestrator.write_startup_manifest()
            
            # Start test
            orchestrator.start_test()
            
            # Wait for completion
            orchestrator.wait_for_completion()
            
            # Collect and save results
            metrics = orchestrator.collect_metrics()
            orchestrator.save_results(metrics)
            orchestrator.print_summary(metrics)
            
            logger.info("🔥 FIRESTORM COMPLETE! 🔥")
        
    except KeyboardInterrupt:
        logger.warning("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
