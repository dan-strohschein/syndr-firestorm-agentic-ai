# Startup Manifest

## Overview

When Firestorm starts, it automatically generates a JSON manifest file that captures the configuration of the load test run. This file is created **immediately after query pre-generation** and **before the test begins**.

## File Location

```
results/firestorm_manifest.json
```

## File Format

The manifest is a JSON object with the following structure:

```json
{
  "start_time": "2025-12-26T19:38:28.384972",
  "agents": [
    {
      "agent_id": "agent_1",
      "persona": "casual_browser",
      "query_count": 250
    },
    {
      "agent_id": "agent_2",
      "persona": "casual_browser",
      "query_count": 245
    },
    {
      "agent_id": "agent_3",
      "persona": "power_user",
      "query_count": 280
    }
  ]
}
```

## Fields

### `start_time`
- **Type**: ISO 8601 timestamp string
- **Description**: The exact date and time when the test run started
- **Format**: `YYYY-MM-DDTHH:MM:SS.microseconds`
- **Example**: `"2025-12-26T19:38:28.384972"`

### `agents`
- **Type**: Array of agent objects
- **Description**: List of all agents participating in the load test

#### Agent Object Fields

- **`agent_id`**: Unique identifier for the agent (e.g., `"agent_1"`, `"agent_2"`)
- **`persona`**: The persona/role this agent is running as:
  - `casual_browser` - Casual user browsing behavior
  - `power_user` - Active user with more complex queries
  - `admin` - Administrative queries
  - `analyst` - Analytical/reporting queries
- **`query_count`**: Number of pre-generated queries assigned to this agent

## Purpose

The manifest file provides:

1. **Run Identification**: Timestamp for correlating test results
2. **Configuration Documentation**: Records exactly which agents ran and their roles
3. **Query Distribution**: Shows how queries were distributed across agents
4. **Reproducibility**: Documents the test configuration for future reference

## Timing

The manifest is written at this specific point in the test lifecycle:

1. ✅ Environment setup (if enabled)
2. ✅ Agent creation
3. ✅ Query pre-generation
4. **📝 Manifest written** ← HERE
5. 🔥 Test execution begins

This ensures that all agent configurations and query counts are finalized before being written to the manifest.

## Example Usage

After a test run, you can use the manifest to:

```python
import json

# Load the manifest
with open('results/firestorm_manifest.json', 'r') as f:
    manifest = json.load(f)

# Get test start time
start_time = manifest['start_time']

# Count agents by persona
from collections import Counter
persona_counts = Counter(agent['persona'] for agent in manifest['agents'])

# Calculate total queries
total_queries = sum(agent['query_count'] for agent in manifest['agents'])

print(f"Test started at: {start_time}")
print(f"Agent distribution: {dict(persona_counts)}")
print(f"Total queries: {total_queries}")
```

## Log Output

When the manifest is written, you'll see:

```
📝 Writing startup manifest...
✅ Startup manifest written to results/firestorm_manifest.json
   Start time: 2025-12-26T19:38:28.384972
   Total agents: 20
   Total queries: 5240
```
