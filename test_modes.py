#!/usr/bin/env python3
"""
Test the test-gen and execute modes
"""

import json
import sys
from pathlib import Path

def test_generation_mode():
    """Test query generation mode"""
    print("=" * 80)
    print("Testing --test-gen mode simulation")
    print("=" * 80)
    
    # Simulate agent creation
    agents = [
        {"agent_id": "agent_1", "persona": "casual_browser", "queries": ["Q1", "Q2", "Q3"]},
        {"agent_id": "agent_2", "persona": "power_user", "queries": ["Q4", "Q5", "Q6", "Q7"]},
        {"agent_id": "agent_3", "persona": "admin", "queries": ["Q8", "Q9"]},
    ]
    
    # Clean existing files
    print("\n🧹 Cleaning existing files...")
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    manifest_path = results_dir / "test_mode_manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
        print(f"   Deleted {manifest_path}")
    
    for agent in agents:
        query_file = results_dir / f"{agent['agent_id']}_test_queries.json"
        if query_file.exists():
            query_file.unlink()
            print(f"   Deleted {query_file}")
    
    # Save queries to files
    print("\n💾 Saving queries to files...")
    for agent in agents:
        query_file = results_dir / f"{agent['agent_id']}_test_queries.json"
        with open(query_file, 'w') as f:
            json.dump(agent['queries'], f, indent=2)
        print(f"   Saved {len(agent['queries'])} queries to {query_file}")
    
    # Create manifest
    print("\n📝 Creating manifest...")
    manifest = {
        "start_time": "2025-12-26T20:00:00.000000",
        "agents": [
            {
                "agent_id": agent['agent_id'],
                "persona": agent['persona'],
                "query_count": len(agent['queries']),
                "query_file": f"{agent['agent_id']}_test_queries.json"
            }
            for agent in agents
        ]
    }
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Manifest written to {manifest_path}")
    print(f"   Total agents: {len(manifest['agents'])}")
    print(f"   Total queries: {sum(a['query_count'] for a in manifest['agents'])}")
    
    return manifest_path

def test_execution_mode(manifest_path):
    """Test execution mode"""
    print("\n" + "=" * 80)
    print("Testing --execute mode simulation")
    print("=" * 80)
    
    # Load manifest
    print(f"\n📂 Loading manifest from {manifest_path}...")
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"   Start time: {manifest['start_time']}")
    print(f"   Total agents: {len(manifest['agents'])}")
    
    # Load queries for each agent
    print("\n📂 Loading queries from files...")
    results_dir = Path("results")
    total_queries = 0
    
    for agent_info in manifest['agents']:
        query_file = results_dir / f"{agent_info['agent_id']}_test_queries.json"
        
        if not query_file.exists():
            print(f"❌ Query file not found: {query_file}")
            return False
        
        with open(query_file, 'r') as f:
            queries = json.load(f)
        
        print(f"   Loaded {len(queries)} queries for {agent_info['agent_id']}")
        total_queries += len(queries)
    
    print(f"\n✅ Loaded {total_queries} total queries from files")
    print("✅ Ready to execute test!")
    
    return True

def main():
    """Run both tests"""
    print("🔥 FIRESTORM MODE TEST 🔥\n")
    
    # Test generation mode
    manifest_path = test_generation_mode()
    
    # Test execution mode
    success = test_execution_mode(manifest_path)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        
        # Show manifest content
        print("\nGenerated manifest:")
        with open(manifest_path, 'r') as f:
            print(json.dumps(json.load(f), indent=2))
    else:
        print("\n❌ Tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
