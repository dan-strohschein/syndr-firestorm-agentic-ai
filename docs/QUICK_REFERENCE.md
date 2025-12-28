# Firestorm Quick Reference

## Command Modes

### Generate Queries Only
```bash
python run-firestorm.py --test-gen [options]
```
- Generates and saves queries to files
- Does NOT execute test
- Creates: manifest + query files

### Execute Pre-generated Test
```bash
python run-firestorm.py --execute [options]
```
- Loads queries from files
- Executes the test
- Requires: manifest + query files

### Full Run (Legacy)
```bash
python run-firestorm.py [options]
```
- Generates queries + executes immediately
- Complete end-to-end run

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--agents N` | Number of concurrent agents | 20 |
| `--duration N` | Test duration (minutes) | 30 |
| `--host HOST` | SyndrDB host | 127.0.0.1 |
| `--port PORT` | SyndrDB port | 1776 |
| `--ollama URL` | Ollama API URL | http://localhost:11434 |
| `--no-setup` | Skip environment setup | false |
| `--quick-test` | Quick test (5 agents, 2 min) | false |

## Quick Workflows

### Standard Two-Phase
```bash
# 1. Generate
python run-firestorm.py --test-gen --agents 20

# 2. Execute
python run-firestorm.py --execute --duration 30
```

### Quick Test
```bash
# Generate
python run-firestorm.py --test-gen --quick-test

# Execute
python run-firestorm.py --execute --quick-test
```

### Multiple Runs Same Queries
```bash
# Generate once
python run-firestorm.py --test-gen --agents 10

# Run multiple times
python run-firestorm.py --execute --duration 10
python run-firestorm.py --execute --duration 20
python run-firestorm.py --execute --duration 30
```

## File Locations

```
results/
├── firestorm_manifest.json       # Test configuration
├── agent_1_queries.json          # Agent 1 queries
├── agent_2_queries.json          # Agent 2 queries
├── ...
├── firestorm.log                 # Standard log
├── firestorm_mmap.log            # Memory-mapped log
└── firestorm_results_*.json      # Test results
```

## Typical Workflow

```
┌─────────────────┐
│  --test-gen     │  Generate queries
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Query Files     │  Inspect/modify if needed
│ Created         │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  --execute      │  Run test (can repeat)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Results         │  Analyze metrics
└─────────────────┘
```
