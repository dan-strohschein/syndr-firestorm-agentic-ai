#!/usr/bin/env python3
"""
Firestorm Ollama Mock Test
- REAL Ollama AI decision making (launches Ollama container)
- MOCKED database (captures queries without executing)
- Shows what queries AI agents would generate
"""

import sys
import time
import json
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import threading
from tools.mmap_logger import setup_mmap_logging, register_handler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('results/ollama_mock_test.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

# Set up memory-mapped logging on a separate thread
mmap_handler = setup_mmap_logging(
    filepath='results/ollama_mock_test_mmap.log',
    max_size=50 * 1024 * 1024,  # 50 MB
    level=logging.INFO
)
register_handler(mmap_handler)
logger.info("Memory-mapped logging initialized")

# Mock database client that captures queries
class MockSyndrDBClient:
    """Mock SyndrDB client that captures queries without executing"""
    
    def __init__(self, host="localhost", port=1776):
        self.host = host
        self.port = port
        self.connected = False
        self.queries = []
        
    def connect(self):
        """Mock connection"""
        self.connected = True
        logger.info(f"[MOCK DB] Connected to SyndrDB at {self.host}:{self.port}")
        
        # Simulate welcome message response
        return {
            "success": True,
            "message": "S0001: Welcome to SyndrDB"
        }
    
    def disconnect(self):
        """Mock disconnection"""
        self.connected = False
        logger.info(f"[MOCK DB] Disconnected from SyndrDB")
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Mock query execution - just capture the query"""
        query_data = {
            "timestamp": time.time(),
            "query": query.strip(),
            "thread": threading.current_thread().name
        }
        self.queries.append(query_data)
        
        # Log truncated query
        query_preview = query.strip()[:100].replace('\n', ' ')
        logger.info(f"[MOCK DB QUERY #{len(self.queries)}] {query_preview}...")
        
        # Return mock success response
        return {
            "success": True,
            "latency_ms": 10.0,  # Fake latency
            "result": {"ResultCount": 42}  # Fake result
        }
    
    def get_captured_queries(self) -> List[Dict[str, Any]]:
        """Return all captured queries"""
        return self.queries


def check_ollama_running():
    """Check if Ollama container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=upbeat_lewin", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return "upbeat_lewin" in result.stdout
    except:
        return False


def start_ollama():
    """Start Ollama container"""
    logger.info("🚀 Starting Ollama container...")
    
    if check_ollama_running():
        logger.info("✅ Ollama container already running")
        return True
    
    try:
        # Start Ollama container
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", "upbeat_lewin",
                "-p", "11434:11434",
                "-v", "ollama:/root/.ollama",
                "ollama/ollama"
            ],
            check=True,
            capture_output=True
        )
        logger.info("✅ Ollama container started")
        
        # Wait for Ollama to be ready
        logger.info("⏳ Waiting for Ollama to be ready...")
        time.sleep(5)
        
        # Pull the model if not already present
        logger.info("📥 Ensuring model is available...")
        subprocess.run(
            ["docker", "exec", "ollama", "ollama", "pull", "llama3.2:1b"],
            check=True
        )
        logger.info("✅ Model ready")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start Ollama: {e}")
        return False


def stop_ollama():
    """Stop Ollama container"""
    logger.info("🛑 Stopping Ollama container...")
    try:
        subprocess.run(["docker", "stop", "upbeat-lewin"], capture_output=True)
        subprocess.run(["docker", "rm", "upbeat-lewin"], capture_output=True)
        logger.info("✅ Ollama container stopped")
    except:
        pass


def run_test(duration_minutes: int, num_agents: int):
    """Run the Ollama mock test"""
    
    # Create mock database client
    mock_db = MockSyndrDBClient()
    
    # Import agents (after we've set up the mock)
    from agents.casual_browser import CasualBrowserAgent
    from agents.power_user_agent import PowerUserAgent
    from agents.admin_agent import AdminAgent
    from agents.analyst_agent import AnalystAgent
    
    # Patch the SyndrDBClient in agents
    import tools.syndrdb_client
    original_client = tools.syndrdb_client.SyndrDBClient
    tools.syndrdb_client.SyndrDBClient = lambda host, port: mock_db
    
    logger.info("🔥 Creating agents with REAL Ollama AI...")
    
    # Create agents with mocked database - ensure at least 1 of each persona type
    agents = []
    agent_types = [
        (CasualBrowserAgent, "casual_browser", 10),
        (PowerUserAgent, "power_user", 6),
        (AdminAgent, "admin", 2),
        (AnalystAgent, "analyst", 2)
    ]
    
    # First, create at least 1 of each persona type
    agent_id = 1
    for AgentClass, agent_type, count in agent_types:
        agent = AgentClass(
            agent_id=f"ollama_mock_agent_{agent_id}_{agent_type}",
            syndrdb_host="localhost",
            syndrdb_port=1776,
            ollama_url="http://localhost:11434"
        )
        # Replace the agent's db_client with our mock
        agent.db_client = mock_db
        agents.append(agent)
        logger.info(f"Created agent: {agent.agent_id} ({agent_type})")
        agent_id += 1
    
    # Then fill remaining slots with the distribution ratio
    remaining = num_agents - len(agents)
    if remaining > 0:
        for AgentClass, agent_type, max_count in agent_types:
            # Already created 1, so create up to max_count - 1 more
            for i in range(min(max_count - 1, remaining)):
                agent = AgentClass(
                    agent_id=f"ollama_mock_agent_{agent_id}_{agent_type}",
                    syndrdb_host="localhost",
                    syndrdb_port=1776,
                    ollama_url="http://localhost:11434"
                )
                agent.db_client = mock_db
                agents.append(agent)
                logger.info(f"Created agent: {agent.agent_id} ({agent_type})")
                agent_id += 1
                remaining -= 1
                
                if remaining <= 0:
                    break
            
            if remaining <= 0:
                break
    
    logger.info(f"✅ Created {len(agents)} agents")
    logger.info("🔥🔥🔥 STARTING OLLAMA MOCK TEST 🔥🔥🔥")
    logger.info(f"Duration: {duration_minutes} minutes")
    logger.info(f"Agents: {len(agents)}")
    logger.info("AI: REAL Ollama (making decisions)")
    logger.info("Database: MOCKED (capturing queries)")
    
    # Start agents in threads
    threads = []
    for agent in agents:
        thread = threading.Thread(
            target=agent.run_session,
            args=(duration_minutes,),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        logger.info(f"Started {agent.agent_id}")
        time.sleep(0.1)  # Stagger starts slightly
    
    # Wait for completion
    logger.info("Waiting for agents to complete...")
    
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.warning("\n🛑 Test interrupted by user")
    
    logger.info("✅ All agents completed")
    
    # Restore original client
    tools.syndrdb_client.SyndrDBClient = original_client
    
    # Collect results
    queries = mock_db.get_captured_queries()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Full JSON log
    json_file = f"results/ollama_mock_queries_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            "test_type": "ollama_mock",
            "duration_minutes": duration_minutes,
            "num_agents": len(agents),
            "total_queries": len(queries),
            "queries": queries
        }, f, indent=2)
    
    logger.info(f"📝 Saved full log to {json_file}")
    
    # Queries only (for easy review)
    queries_file = f"results/ollama_mock_queries_only_{timestamp}.txt"
    with open(queries_file, 'w') as f:
        f.write(f"Ollama Mock Test - Queries Only\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Total Queries: {len(queries)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, q in enumerate(queries, 1):
            f.write(f"Query #{i} (t={q['timestamp']:.2f}):\n")
            f.write(q['query'])
            f.write("\n\n" + "=" * 80 + "\n\n")
    
    logger.info(f"📝 Saved queries to {queries_file}")
    
    # Summary
    summary_file = f"results/ollama_mock_summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write(f"Ollama Mock Test Summary\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Test Configuration:\n")
        f.write(f"  Duration: {duration_minutes} minutes\n")
        f.write(f"  Agents: {len(agents)}\n")
        f.write(f"  AI Decision Making: REAL (Ollama)\n")
        f.write(f"  Database: MOCKED (queries captured, not executed)\n\n")
        f.write(f"Results:\n")
        f.write(f"  Total Queries Generated: {len(queries)}\n")
        f.write(f"  Queries per minute: {len(queries) / max(duration_minutes, 0.1):.1f}\n\n")
        
        # Agent metrics
        f.write("Agent Metrics:\n")
        for agent in agents:
            metrics = agent.get_metrics()
            f.write(f"  {metrics['agent_id']}:\n")
            f.write(f"    Queries: {metrics['queries_executed']}\n")
            f.write(f"    Success Rate: {metrics['success_rate']*100:.1f}%\n")
    
    logger.info(f"📝 Saved summary to {summary_file}")
    
    logger.info(f"\n🎉 Test complete! Generated {len(queries)} queries using AI decision making")


def main():
    parser = argparse.ArgumentParser(description="Firestorm Ollama Mock Test")
    parser.add_argument("--duration", type=float, default=5, help="Test duration in minutes")
    parser.add_argument("--agents", type=int, default=20, help="Number of agents to create")
    parser.add_argument("--keep-ollama", action="store_true", help="Don't stop Ollama after test")
    
    args = parser.parse_args()
    
    # Ensure results directory exists
    Path("results").mkdir(exist_ok=True)
    
    logger.info("🔥 Starting Firestorm Ollama Mock Test")
    logger.info("This test uses REAL Ollama for AI decisions but MOCKS the database")
    
    # Start Ollama
    if not start_ollama():
        logger.error("❌ Failed to start Ollama. Exiting.")
        sys.exit(1)
    
    try:
        # Run test
        run_test(args.duration, args.agents)
    finally:
        # Cleanup
        if not args.keep_ollama:
            stop_ollama()
        else:
            logger.info("⚠️  Keeping Ollama running (--keep-ollama flag)")


if __name__ == "__main__":
    main()
