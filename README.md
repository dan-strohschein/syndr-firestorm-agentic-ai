# 🔥 Syndr Firestorm - AI-Driven Load Testing Framework

AI-powered concurrent load testing framework for validating SyndrDB performance, accuracy, and concurrency handling.

## Overview

Syndr Firestorm uses AI agents powered by Ollama to simulate realistic user behavior patterns against SyndrDB. Unlike traditional load testing tools, agents make intelligent decisions about what actions to take next, creating organic traffic patterns similar to real users.

## Features

- **4 Persona Types**: Casual browsers, power users, admins, and analysts
- **AI-Driven Behavior**: Ollama LLM decides agent actions in real-time
- **Realistic Distribution**: 10 casual, 6 power, 2 admin, 2 analyst (configurable)
- **Comprehensive Metrics**: Latency percentiles (p50/p95/p99), success rates, throughput
- **Dual Output**: JSON files for analysis + text summaries for humans
- **Health Monitoring**: Real-time tracking of database health during tests
- **Flexible Scenarios**: Quick tests, standard loads, stress tests, endurance runs

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install and start Ollama (if not already installed)
# macOS:
./scripts/ollama-mac-install.sh

# Linux:
./scripts/ollama-linux-install.sh

# Pull the AI model
ollama pull llama3.2:1b
```

### 2. Start SyndrDB

Make sure SyndrDB is running on `localhost:1776` (or configure custom host/port).

### 3. Run a Test

```bash
# Quick test (5 agents, 2 minutes)
python run-firestorm.py --quick-test

# Standard test (20 agents, 30 minutes)
python run-firestorm.py

# Custom configuration
python run-firestorm.py --agents 50 --duration 60

# Skip environment setup (use existing database)
python run-firestorm.py --no-setup
```

## Command-Line Options

```
--agents N          Number of concurrent agents (default: 20)
--duration M        Test duration in minutes (default: 30)
--host HOST         SyndrDB host (default: localhost)
--port PORT         SyndrDB port (default: 1776)
--ollama URL        Ollama API URL (default: http://localhost:11434)
--no-setup          Skip environment setup
--quick-test        Quick test: 5 agents for 2 minutes
```

## Agent Personas

### Casual Browser (50% of users)
- Browsing focused (70% reads)
- 3-8 second think time
- 5-10 minute sessions
- Window shopping behavior

### Power User (30% of users)
- Efficient and fast (5-8 actions/min)
- Uses filters and advanced features
- Completes purchases
- Writes reviews

### Admin (10% of users)
- Bulk operations (50-200 items)
- Order processing
- Report generation
- Inventory management

### Analyst (10% of users)
- Complex analytical queries
- Multi-table JOINs
- Patient with slow queries
- Business intelligence focus

## Test Scenarios

Predefined scenarios in `config/test-scenarios.yaml`:

- **quick_test**: 5 agents, 2 minutes (debugging)
- **standard**: 20 agents, 30 minutes (default)
- **stress**: 50 agents, 60 minutes (high load)
- **endurance**: 20 agents, 4 hours (stability)
- **peak_load**: 100 agents, 30 minutes (traffic spike)
- **admin_heavy**: Focus on bulk operations
- **analyst_heavy**: Focus on complex queries

## Results

Results are saved to the `results/` directory:

- `firestorm_YYYYMMDD_HHMMSS.json` - Full metrics in JSON format
- `firestorm_YYYYMMDD_HHMMSS.txt` - Human-readable summary
- `firestorm.log` - Detailed execution log

### Sample Output

```
================================================================================
🔥🔥🔥 FIRESTORM TEST COMPLETE 🔥🔥🔥
================================================================================

✅ Total Queries: 4,523
✅ Success Rate: 99.8%
✅ Avg Latency: 42.3 ms
✅ Queries/Second: 2.51

================================================================================
```

## Architecture

```
syndr-firestorm/
├── agents/                    # AI agent implementations
│   ├── base-agent.py         # Base agent class
│   ├── casual-browser.py     # Casual browser agent
│   ├── power-user-agent.py   # Power user agent
│   ├── admin-agent.py        # Admin agent
│   ├── analyst-agent.py      # Analyst agent
│   └── personas.py           # Persona definitions
├── conductor/                 # Test orchestration
│   ├── conductor.py          # Main conductor
│   ├── health-monitor.py     # Health monitoring
│   └── data-seeder.py        # Test data generation
├── tools/                     # Utilities
│   ├── syndrdb-client.py     # SyndrDB TCP client
│   └── metrics-collector.py  # Metrics aggregation
├── config/                    # Configuration files
│   └── test-scenarios.yaml   # Test scenarios
├── results/                   # Test results output
├── run-firestorm.py          # Main entry point
└── requirements.txt          # Python dependencies
```

## Metrics Collected

### Per-Agent Metrics
- Queries executed
- Success/failure counts
- Average latency
- Error details

### Aggregate Metrics
- Total queries
- Success rate (%)
- Latency distribution (p50, p95, p99, avg, min, max)
- Throughput (queries/second)
- Error rate

### Performance Assessment
- Automated grading (EXCELLENT/GOOD/ACCEPTABLE/POOR)
- Pass/fail thresholds (95% success, <10s p99 latency)
- Data integrity checks
- Collision detection

## Validation Goals

Firestorm validates SyndrDB's ability to:

1. **Maintain Accuracy**: No data collisions under concurrent load
2. **Sustain Performance**: Latency remains stable (20 users = 1 user)
3. **Handle Mixed Workloads**: Reads, writes, bulk operations, complex queries
4. **Stay Responsive**: 95%+ success rate, <5s p99 latency

## Troubleshooting

### Ollama Not Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### SyndrDB Connection Failed
- Verify SyndrDB is running on port 1776
- Check connection string format
- Review firewall settings

### Agent Errors
- Check `results/firestorm.log` for details
- Verify AI model is pulled: `ollama list`
- Ensure sufficient system resources

### High Error Rate
- Check SyndrDB logs for issues
- Reduce agent count (`--agents 5`)
- Verify database schema is correct

## High-Concurrency Testing

Firestorm implements **high-entropy test data** to reduce overlapping operations during concurrent testing:

- **475+ Product Categories**: Agents work on diverse data segments
- **Agent-Specific Subsets**: Each agent operates on 15-25 unique categories
- **Multi-Dimensional Filtering**: 25,650+ unique query combinations
- **95% Reduction in UPDATE Conflicts**: Realistic concurrent workload simulation

See [ENTROPY_IMPROVEMENTS.md](ENTROPY_IMPROVEMENTS.md) for details and [docs/HIGH_ENTROPY_STRATEGIES.md](docs/HIGH_ENTROPY_STRATEGIES.md) for technical documentation.


## License

MIT License - See LICENSE file for details

## Author

Built for validating SyndrDB concurrent performance 🔥
