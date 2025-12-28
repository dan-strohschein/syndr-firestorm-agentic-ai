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
from typing import List, Dict, Any
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
        setup_env: bool = True
    ):
        self.num_agents = num_agents
        self.duration_seconds = duration_minutes * 60
        self.syndrdb_host = syndrdb_host
        self.syndrdb_port = syndrdb_port
        self.ollama_url = ollama_url
        self.setup_env = setup_env
        
        self.agents: List[Any] = []
        self.agent_threads: List[threading.Thread] = []
        self.conductor = FirestormConductor(syndrdb_host, syndrdb_port, 
                                           username="root", password="root", database="primary")
        
        self.test_start_time: float = 0
        self.test_end_time: float = 0
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
        results_dir = Path("results")
        query_files = list(results_dir.glob("agent_*_queries.json"))
        for query_file in query_files:
            query_file.unlink()
            logger.info(f"   Deleted {query_file}")
        
        logger.info(f"✅ Cleaned {len(query_files)} query files")
    
    def save_queries_to_files(self):
        """Save each agent's queries to individual files"""
        logger.info("💾 Saving queries to files...")
        
        for agent in self.agents:
            if hasattr(agent, 'pregenerated_queries') and agent.pregenerated_queries:
                query_file = Path(f"results/{agent.agent_id}_queries.json")
                
                with open(query_file, 'w') as f:
                    json.dump(agent.pregenerated_queries, f, indent=2)
                
                logger.info(f"   Saved {len(agent.pregenerated_queries)} queries to {query_file}")
        
        logger.info("✅ All queries saved to files")
    
    def load_queries_from_files(self):
        """Load queries from files into agents"""
        logger.info("📂 Loading queries from files...")
        
        total_loaded = 0
        for agent in self.agents:
            query_file = Path(f"results/{agent.agent_id}_queries.json")
            
            if not query_file.exists():
                logger.error(f"❌ Query file not found: {query_file}")
                raise FileNotFoundError(f"Missing query file for {agent.agent_id}")
            
            with open(query_file, 'r') as f:
                queries = json.load(f)
            
            agent.pregenerated_queries = queries
            total_loaded += len(queries)
            logger.info(f"   Loaded {len(queries)} queries for {agent.agent_id}")
        
        logger.info(f"✅ Loaded {total_loaded} total queries from files")
    
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
    
    def _run_agent(self, agent, duration: int):
        """Run a single agent for specified duration"""
        try:
            # Check if agent has pre-generated queries
            if hasattr(agent, 'pregenerated_queries') and agent.pregenerated_queries:
                # Use pre-generated query execution mode
                from agents.personas import PERSONAS
                persona = PERSONAS.get(agent.persona_name, {})
                think_time_range = persona.get("think_time_seconds", (1, 3))
                agent.run_pregenerated_session(think_time_range=think_time_range)
            else:
                # Fall back to original runtime generation mode
                agent.run_session(duration_minutes=duration / 60)
        except Exception as e:
            logger.error(f"Agent {agent.agent_id} crashed: {e}")
    
    def start_test(self):
        """Start the load test"""
        logger.info("🔥🔥🔥 FIRESTORM TEST STARTING 🔥🔥🔥")
        logger.info(f"Agents: {self.num_agents}")
        logger.info(f"Duration: {self.duration_seconds / 60:.1f} minutes")
        logger.info(f"Target: {self.syndrdb_host}:{self.syndrdb_port}")
        
        self.running = True
        self.test_start_time = time.time()
        
        # Start all agent threads
        for agent in self.agents:
            thread = threading.Thread(
                target=self._run_agent,
                args=(agent, self.duration_seconds),
                daemon=True
            )
            thread.start()
            self.agent_threads.append(thread)
            logger.info(f"Started {agent.agent_id} ({agent.persona_name})")
        
        # Start health monitoring in background
        health_thread = threading.Thread(
            target=self._monitor_health,
            daemon=True
        )
        health_thread.start()
        
        logger.info("✅ All agents launched!")
        
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
        """Wait for all agents to complete"""
        logger.info("Waiting for agents to complete...")
        
        # Wait for all threads
        for thread in self.agent_threads:
            thread.join()
        
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
        
        saved_count = 0
        for agent in self.agents:
            # Check if agent has execution results
            if not hasattr(agent, 'execution_results') or not agent.execution_results:
                continue
            
            # Generate filename: firestorm_{timestamp}_{persona}_{agent_id}.json
            filename = f"results/firestorm_{timestamp}_{agent.persona_name}_{agent.agent_id}.json"
            
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
    
    # Create orchestrator
    orchestrator = FirestormOrchestrator(
        num_agents=args.agents,
        duration_minutes=args.duration,
        syndrdb_host=args.host,
        syndrdb_port=args.port,
        ollama_url=args.ollama,
        setup_env=not args.no_setup
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
