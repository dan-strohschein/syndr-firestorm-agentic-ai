# Two-Phase Test Execution

## Overview

Firestorm now supports a **two-phase workflow** that separates query generation from test execution. This provides flexibility to pre-generate queries once and run multiple tests, or to inspect/modify queries before execution.

## Workflow Phases

### Phase 1: Query Generation (`--test-gen`)
Generate all queries and save them to files without executing the test.

### Phase 2: Test Execution (`--execute`)
Load pre-generated queries and execute the test.

## Usage

### Phase 1: Generate Queries

```bash
python run-firestorm.py --test-gen --agents 20 --duration 30
```

**What happens:**
1. ✅ Deletes existing manifest and query files
2. ✅ Sets up test environment (if needed)
3. ✅ Creates agents based on distribution
4. ✅ Generates queries using Ollama AI
5. ✅ Saves queries to individual JSON files (one per agent)
6. ✅ Writes manifest with query file references
7. ⏹️ **Does NOT execute the test**

**Output files:**
```
results/
  ├── firestorm_manifest.json      # Test configuration
  ├── agent_1_queries.json         # Queries for agent 1
  ├── agent_2_queries.json         # Queries for agent 2
  └── ...                          # One file per agent
```

**Console output:**
```
🔥 MODE: TEST GENERATION 🔥
Generating queries and saving to files (no execution)

🧹 Cleaning existing manifest and query files...
   Deleted results/firestorm_manifest.json
   Deleted results/agent_1_queries.json
   ...
✅ Cleaned 20 query files

🔥 FIRESTORM: Creating 20 agents...
✅ Created 20 agents

🔥 FIRESTORM: Pre-generating queries...
✅ Pre-generated 5240 total queries across 20 agents

💾 Saving queries to files...
   Saved 250 queries to results/agent_1_queries.json
   Saved 245 queries to results/agent_2_queries.json
   ...
✅ All queries saved to files

📝 Writing startup manifest...
✅ Startup manifest written to results/firestorm_manifest.json

🔥 QUERY GENERATION COMPLETE! 🔥
Run with --execute to execute the test
```

### Phase 2: Execute Test

```bash
python run-firestorm.py --execute --duration 30
```

**What happens:**
1. ✅ Loads manifest file
2. ✅ Creates agents based on manifest
3. ✅ Loads queries from individual files
4. ✅ Executes the test
5. ✅ Collects and saves results

**Console output:**
```
🔥 MODE: EXECUTION 🔥
Loading queries from files and executing test

📂 Loading manifest from results/firestorm_manifest.json...
   Start time: 2025-12-26T20:00:00.000000
   Total agents: 20
✅ Created 20 agents from manifest

📂 Loading queries from files...
   Loaded 250 queries for agent_1
   Loaded 245 queries for agent_2
   ...
✅ Loaded 5240 total queries from files

🔥🔥🔥 FIRESTORM TEST STARTING 🔥🔥🔥
Agents: 20
Duration: 30.0 minutes
...
🔥 FIRESTORM COMPLETE! 🔥
```

## Manifest File Format (with query files)

When using `--test-gen`, the manifest includes query file references:

```json
{
  "start_time": "2025-12-26T20:00:00.000000",
  "agents": [
    {
      "agent_id": "agent_1",
      "persona": "casual_browser",
      "query_count": 250,
      "query_file": "agent_1_queries.json"
    },
    {
      "agent_id": "agent_2",
      "persona": "power_user",
      "query_count": 280,
      "query_file": "agent_2_queries.json"
    }
  ]
}
```

## Query File Format

Each agent's queries are stored in a JSON array:

```json
[
  "SELECT * FROM products WHERE category = 'electronics' LIMIT 10;",
  "SELECT * FROM users WHERE created_at > '2024-01-01';",
  ...
]
```

## Use Cases

### 1. Pre-generate Once, Run Multiple Times
```bash
# Generate queries once
python run-firestorm.py --test-gen --agents 20

# Run test multiple times with same queries
python run-firestorm.py --execute --duration 10
python run-firestorm.py --execute --duration 20
python run-firestorm.py --execute --duration 30
```

### 2. Inspect/Modify Queries Before Execution
```bash
# Generate queries
python run-firestorm.py --test-gen --agents 20

# Manually inspect/edit query files
cat results/agent_1_queries.json
# Edit files as needed...

# Execute with modified queries
python run-firestorm.py --execute --duration 30
```

### 3. Quick Iteration During Development
```bash
# Generate queries once (can take several minutes)
python run-firestorm.py --test-gen --agents 5 --quick-test

# Execute multiple times quickly (no regeneration)
python run-firestorm.py --execute --quick-test
python run-firestorm.py --execute --quick-test
```

### 4. Separate CI/CD Stages
```bash
# Stage 1: Generate queries (can be slow)
python run-firestorm.py --test-gen --agents 20

# Stage 2: Execute test (faster, uses pre-generated queries)
python run-firestorm.py --execute --duration 30
```

## Legacy Mode (No Switches)

Running without `--test-gen` or `--execute` executes the complete flow (legacy behavior):

```bash
python run-firestorm.py --agents 20 --duration 30
```

This will:
1. Setup environment
2. Create agents
3. Generate queries
4. Execute test immediately
5. Collect results

## Command-Line Options

### Generation Phase Options
- `--agents N` - Number of agents to create
- `--ollama URL` - Ollama API URL for query generation
- `--no-setup` - Skip database environment setup

### Execution Phase Options
- `--duration N` - Test duration in minutes
- `--host HOST` - SyndrDB host
- `--port PORT` - SyndrDB port

### Both Phases
- `--quick-test` - Quick test mode (5 agents, 2 minutes)

## Error Handling

### Missing Manifest File
If you run `--execute` without generating queries first:
```
❌ Manifest file not found: results/firestorm_manifest.json
   Run with --test-gen first to generate queries
```

### Missing Query Files
If query files are deleted after generation:
```
❌ Query file not found: results/agent_3_queries.json
```

### Invalid Mode Combination
If you try to use both switches:
```
❌ Cannot use --test-gen and --execute together
   Use --test-gen to generate queries OR --execute to run the test
```

## Best Practices

1. **Version Control**: Consider committing generated query files to track test scenarios
2. **File Management**: Clean old query files before regenerating (`--test-gen` does this automatically)
3. **Query Inspection**: Review generated queries before execution to ensure quality
4. **Iteration**: Use `--test-gen` once, then iterate quickly with `--execute`
5. **CI/CD**: Split generation and execution into separate pipeline stages

## Examples

### Quick Test Workflow
```bash
# Generate queries for quick test
python run-firestorm.py --test-gen --quick-test

# Run quick test multiple times
python run-firestorm.py --execute --quick-test
```

### Full Production Test
```bash
# Generate queries for 100 agents
python run-firestorm.py --test-gen --agents 100

# Execute 1-hour load test
python run-firestorm.py --execute --duration 60
```

### Development Workflow
```bash
# Generate with minimal agents
python run-firestorm.py --test-gen --agents 3

# Edit queries manually
nano results/agent_1_queries.json

# Test with modified queries
python run-firestorm.py --execute --duration 5
```
