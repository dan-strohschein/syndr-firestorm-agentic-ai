#!/usr/bin/env python3
"""
Test the startup manifest generation
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add mock agents
class MockAgent:
    def __init__(self, agent_id, persona_name, query_count):
        self.agent_id = agent_id
        self.persona_name = persona_name
        self.pregenerated_queries = [None] * query_count  # Mock queries

def test_manifest_generation():
    """Test manifest generation"""
    print("Testing startup manifest generation...")
    
    # Create mock agents
    agents = [
        MockAgent("agent_1", "casual_browser", 250),
        MockAgent("agent_2", "casual_browser", 245),
        MockAgent("agent_3", "power_user", 280),
        MockAgent("agent_4", "admin", 300),
        MockAgent("agent_5", "analyst", 290),
    ]
    
    # Create manifest
    manifest = {
        "start_time": datetime.now().isoformat(),
        "agents": []
    }
    
    # Collect agent information
    for agent in agents:
        agent_info = {
            "agent_id": agent.agent_id,
            "persona": agent.persona_name,
            "query_count": len(agent.pregenerated_queries) if hasattr(agent, 'pregenerated_queries') else 0
        }
        manifest["agents"].append(agent_info)
    
    # Write to file
    Path("results").mkdir(exist_ok=True)
    manifest_path = Path("results/test_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Manifest written to {manifest_path}")
    
    # Read back and verify
    with open(manifest_path, 'r') as f:
        loaded = json.load(f)
    
    print(f"\nManifest contents:")
    print(f"  Start time: {loaded['start_time']}")
    print(f"  Total agents: {len(loaded['agents'])}")
    print(f"  Total queries: {sum(a['query_count'] for a in loaded['agents'])}")
    print(f"\nAgents:")
    for agent in loaded['agents']:
        print(f"    {agent['agent_id']}: {agent['persona']} - {agent['query_count']} queries")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    test_manifest_generation()
