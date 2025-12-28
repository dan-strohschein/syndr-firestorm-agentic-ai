#!/usr/bin/env python3
# firestorm/test-firestorm-mock.py
"""
Mock test for Firestorm - captures database queries without executing them
Runs agents for 5 minutes and logs all queries that would be sent to SyndrDB
"""

import json
import logging
import sys
import time
import threading
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from unittest.mock import Mock, MagicMock
from tools.mmap_logger import setup_mmap_logging, register_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('results/mock_test.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

# Set up memory-mapped logging on a separate thread
mmap_handler = setup_mmap_logging(
    filepath='results/mock_test_mmap.log',
    max_size=50 * 1024 * 1024,  # 50 MB
    level=logging.INFO
)
register_handler(mmap_handler)
logger.info("Memory-mapped logging initialized")

# Import agent classes
from agents.casual_browser import CasualBrowserAgent
from agents.power_user_agent import PowerUserAgent
from agents.admin_agent import AdminAgent
from agents.analyst_agent import AnalystAgent

# Create results directory
Path("results").mkdir(exist_ok=True)

class MockSyndrDBClient:
    """Mock SyndrDB client that captures queries instead of executing them"""
    
    def __init__(self, host: str = "localhost", port: int = 1776):
        self.host = host
        self.port = port
        self.connected = False
        self.queries: List[Dict[str, Any]] = []
        self.query_count = 0
        
    def connect(self) -> bool:
        """Mock connection"""
        self.connected = True
        logger.info(f"[MOCK] Connected to SyndrDB at {self.host}:{self.port}")
        return True
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Mock query execution - just capture the query"""
        self.query_count += 1
        timestamp = time.time()
        
        # Capture query details
        query_record = {
            "query_id": self.query_count,
            "timestamp": timestamp,
            "timestamp_readable": datetime.fromtimestamp(timestamp).isoformat(),
            "query": query.strip(),
            "latency_ms": 0  # Mock latency
        }
        
        self.queries.append(query_record)
        
        # Log query
        logger.info(f"[MOCK QUERY #{self.query_count}] {query[:100]}...")
        
        # Return mock success response
        # Simulate different responses based on query type
        if query.strip().upper().startswith("SELECT COUNT"):
            return {
                "success": True,
                "result": {"ResultCount": 5000},
                "latency_ms": 5.0
            }
        elif query.strip().upper().startswith("SELECT"):
            return {
                "success": True,
                "result": {"rows": [], "count": 10},
                "latency_ms": 10.0
            }
        elif query.strip().upper().startswith("ADD DOCUMENT"):
            return {
                "success": True,
                "result": {"document_id": self.query_count},
                "latency_ms": 8.0
            }
        elif "SHOW DATABASES" in query.strip().upper():
            return {
                "success": True,
                "result": {"databases": ["firestorm_test", "default"]},
                "latency_ms": 2.0
            }
        elif "SHOW BUNDLES" in query.strip().upper():
            return {
                "success": True,
                "result": {"bundles": ["users", "products", "orders", "order_items", "cart_items", "reviews"]},
                "latency_ms": 2.0
            }
        else:
            return {
                "success": True,
                "result": {},
                "latency_ms": 3.0
            }
    
    def disconnect(self):
        """Mock disconnect"""
        self.connected = False
        logger.info(f"[MOCK] Disconnected from SyndrDB")
    
    def get_query_summary(self) -> Dict[str, Any]:
        """Get summary of captured queries"""
        query_types = {}
        
        for q in self.queries:
            query = q["query"].strip().upper()
            if query.startswith("SELECT"):
                query_type = "SELECT"
            elif query.startswith("ADD DOCUMENT"):
                query_type = "INSERT"
            elif query.startswith("UPDATE"):
                query_type = "UPDATE"
            elif query.startswith("DELETE"):
                query_type = "DELETE"
            elif query.startswith("CREATE"):
                query_type = "CREATE"
            elif "SHOW" in query:
                query_type = "SHOW"
            elif "USE" in query:
                query_type = "USE"
            else:
                query_type = "OTHER"
            
            query_types[query_type] = query_types.get(query_type, 0) + 1
        
        return {
            "total_queries": len(self.queries),
            "query_types": query_types,
            "queries": self.queries
        }


class MockOllamaAgent:
    """Wrapper to mock Ollama calls for agents"""
    
    def __init__(self, agent_class, agent_id: str):
        self.agent = agent_class(
            agent_id=agent_id,
            syndrdb_host="mock",
            syndrdb_port=1776,
            ollama_url="http://mock:11434"
        )
        
        # Replace db_client with mock
        self.mock_db = MockSyndrDBClient()
        self.agent.db_client = self.mock_db
        
        # Mock Ollama calls to return fallback actions
        self.agent._call_ollama = self._mock_ollama_call
    
    def _mock_ollama_call(self, prompt: str, system_prompt: str) -> str:
        """Mock Ollama to return empty response (triggers fallback actions)"""
        return ""
    
    def run_session(self, duration_minutes: float):
        """Run agent session"""
        self.agent.run_session(duration_minutes=duration_minutes)
    
    def get_metrics(self):
        """Get agent metrics"""
        return self.agent.get_metrics()
    
    def get_queries(self):
        """Get captured queries"""
        return self.mock_db.get_query_summary()


class MockFirestormTest:
    """Mock Firestorm test orchestrator"""
    
    def __init__(self, duration_minutes: int = 5):
        self.duration_minutes = duration_minutes
        self.agents: List[MockOllamaAgent] = []
        self.agent_threads: List[threading.Thread] = []
        self.test_start_time = 0
        self.test_end_time = 0
        
        # Agent distribution (scaled down for testing)
        self.agent_distribution = {
            "casual_browser": 2,
            "power_user": 1,
            "admin": 1,
            "analyst": 1
        }
    
    def create_agents(self):
        """Create mock agents"""
        logger.info("🔥 Creating mock agents...")
        
        agent_classes = {
            "casual_browser": CasualBrowserAgent,
            "power_user": PowerUserAgent,
            "admin": AdminAgent,
            "analyst": AnalystAgent
        }
        
        agent_id = 1
        for persona, count in self.agent_distribution.items():
            for i in range(count):
                agent = MockOllamaAgent(
                    agent_classes[persona],
                    f"mock_agent_{agent_id}_{persona}"
                )
                self.agents.append(agent)
                logger.info(f"Created mock agent: {agent.agent.agent_id} ({persona})")
                agent_id += 1
        
        logger.info(f"✅ Created {len(self.agents)} mock agents")
    
    def run_test(self):
        """Run the mock test"""
        logger.info("🔥🔥🔥 STARTING MOCK TEST 🔥🔥🔥")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info(f"Agents: {len(self.agents)}")
        
        self.test_start_time = time.time()
        
        # Start agent threads
        for agent in self.agents:
            thread = threading.Thread(
                target=agent.run_session,
                args=(self.duration_minutes,),
                daemon=True
            )
            thread.start()
            self.agent_threads.append(thread)
            logger.info(f"Started {agent.agent.agent_id}")
        
        # Wait for all threads to complete
        logger.info("Waiting for agents to complete...")
        for thread in self.agent_threads:
            thread.join()
        
        self.test_end_time = time.time()
        logger.info("✅ All mock agents completed!")
    
    def collect_results(self) -> Dict[str, Any]:
        """Collect all captured queries and metrics"""
        all_queries = []
        all_metrics = []
        total_query_count = 0
        query_type_totals = {}
        
        for agent in self.agents:
            metrics = agent.get_metrics()
            queries = agent.get_queries()
            
            all_metrics.append(metrics)
            all_queries.extend(queries["queries"])
            total_query_count += queries["total_queries"]
            
            # Aggregate query types
            for qtype, count in queries["query_types"].items():
                query_type_totals[qtype] = query_type_totals.get(qtype, 0) + count
        
        return {
            "test_info": {
                "duration_minutes": self.duration_minutes,
                "duration_seconds": self.test_end_time - self.test_start_time,
                "num_agents": len(self.agents),
                "start_time": datetime.fromtimestamp(self.test_start_time).isoformat(),
                "end_time": datetime.fromtimestamp(self.test_end_time).isoformat()
            },
            "query_summary": {
                "total_queries": total_query_count,
                "query_types": query_type_totals,
                "queries_per_second": total_query_count / (self.test_end_time - self.test_start_time)
            },
            "agent_metrics": all_metrics,
            "all_queries": sorted(all_queries, key=lambda x: x["timestamp"])
        }
    
    def save_results(self, results: Dict[str, Any]):
        """Save captured queries and summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full query log as JSON
        json_file = f"results/mock_queries_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"💾 Saved query log to {json_file}")
        
        # Save human-readable summary
        summary_file = f"results/mock_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            self._write_summary(f, results)
        logger.info(f"💾 Saved summary to {summary_file}")
        
        # Save queries only (for easy inspection)
        queries_file = f"results/mock_queries_only_{timestamp}.txt"
        with open(queries_file, 'w') as f:
            for q in results["all_queries"]:
                f.write(f"[{q['timestamp_readable']}] Query #{q['query_id']}\n")
                f.write(f"{q['query']}\n")
                f.write("-" * 80 + "\n")
        logger.info(f"💾 Saved queries to {queries_file}")
    
    def _write_summary(self, f, results: Dict[str, Any]):
        """Write human-readable summary"""
        f.write("=" * 80 + "\n")
        f.write("🔥 FIRESTORM MOCK TEST SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        
        info = results["test_info"]
        f.write(f"Duration: {info['duration_minutes']} minutes ({info['duration_seconds']:.2f} seconds)\n")
        f.write(f"Agents: {info['num_agents']}\n")
        f.write(f"Start: {info['start_time']}\n")
        f.write(f"End: {info['end_time']}\n\n")
        
        summary = results["query_summary"]
        f.write("-" * 80 + "\n")
        f.write("QUERY SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Queries Captured: {summary['total_queries']}\n")
        f.write(f"Queries Per Second: {summary['queries_per_second']:.2f}\n\n")
        
        f.write("Query Types:\n")
        for qtype, count in sorted(summary["query_types"].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / summary['total_queries'] * 100) if summary['total_queries'] > 0 else 0
            f.write(f"  {qtype}: {count} ({percentage:.1f}%)\n")
        
        f.write("\n" + "-" * 80 + "\n")
        f.write("AGENT METRICS\n")
        f.write("-" * 80 + "\n")
        for metrics in results["agent_metrics"]:
            f.write(f"\n{metrics['agent_id']} ({metrics['persona']})\n")
            f.write(f"  Queries: {metrics['queries_executed']}\n")
            f.write(f"  Success Rate: {metrics['success_rate'] * 100:.1f}%\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"Sample Queries (first 10):\n")
        f.write("=" * 80 + "\n")
        for q in results["all_queries"][:10]:
            f.write(f"\n[{q['timestamp_readable']}]\n")
            f.write(f"{q['query']}\n")
            f.write("-" * 40 + "\n")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print summary to console"""
        summary = results["query_summary"]
        
        print("\n" + "=" * 80)
        print("🔥 MOCK TEST COMPLETE 🔥")
        print("=" * 80)
        print(f"\n✅ Total Queries Captured: {summary['total_queries']}")
        print(f"✅ Queries Per Second: {summary['queries_per_second']:.2f}")
        print("\nQuery Types:")
        for qtype, count in sorted(summary["query_types"].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / summary['total_queries'] * 100) if summary['total_queries'] > 0 else 0
            print(f"  {qtype}: {count} ({percentage:.1f}%)")
        print("\n" + "=" * 80 + "\n")


def main():
    """Main test entry point"""
    logger.info("🔥 Starting Firestorm Mock Test")
    logger.info("This test will capture all database queries without executing them")
    
    try:
        # Create test orchestrator (5 minutes)
        test = MockFirestormTest(duration_minutes=5)
        
        # Create mock agents
        test.create_agents()
        
        # Run test
        test.run_test()
        
        # Collect and save results
        results = test.collect_results()
        test.save_results(results)
        test.print_summary(results)
        
        logger.info("🔥 Mock test complete! Check results/ directory for captured queries.")
        
    except KeyboardInterrupt:
        logger.warning("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
