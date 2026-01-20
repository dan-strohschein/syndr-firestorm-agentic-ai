# Seed Data Generation and Execution

This document describes how to use the seed data pre-generation and execution features.

## Overview

You can now generate seed data queries and save them to a file for later execution. This is useful for:

- **Faster repeated testing**: Generate queries once, execute multiple times
- **Consistent test data**: Use the same seed data across multiple test runs
- **Offline preparation**: Generate queries without needing a running database
- **Large datasets**: Pre-generate large datasets without timeouts

## Menu Options

When running `./start-firestorm.sh`, you'll see 5 menu options:

### Option 4: Pre-generate Seed Data Queries

This option generates seed data queries and saves them to a JSON file **without executing them**.

**What it does:**
1. Prompts you for the number of entities to generate (users, products, orders, reviews)
2. Generates realistic queries using Faker library
3. Saves all queries to `results/seed_queries.json`

**Usage:**
```bash
./start-firestorm.sh
# Select option 4
# Enter quantities (or press Enter for defaults)
```

**Or directly:**
```bash
python generate_seed_queries.py --users 10000 --products 5000 --orders 5000 --reviews 10000
```

**Output:** `results/seed_queries.json` containing all generated queries

### Option 5: Seed Database from Pre-generated File

This option loads queries from a file and executes them against the database.

**What it does:**
1. Checks that `results/seed_queries.json` exists
2. Sets up the database and bundles
3. Executes queries in two phases:
   - Phase 1: Users and Products (captures DocumentIDs)
   - Phase 2: Orders, Reviews, Order Items, Cart Items (with real foreign key references)

**Usage:**
```bash
./start-firestorm.sh
# Select option 5
# Enter database name (or press Enter for default: firestorm_test)
```

**Or directly:**
```bash
python seed_from_file.py --database firestorm_test
```

## Two-Phase Execution

The seed execution uses a smart two-phase approach:

### Phase 1: Base Entities
- Executes all user and product inserts
- Captures DocumentIDs from the database responses
- Builds ID mapping tables

### Phase 2: Related Entities
- Replaces placeholder IDs (e.g., `{USER_ID_123}`) with real DocumentIDs
- Executes orders, reviews, order_items, and cart_items
- Maintains referential integrity

## File Format

The `seed_queries.json` file has this structure:

```json
{
  "users": [
    "ADD DOCUMENT TO BUNDLE \"users\" WITH ...",
    "ADD DOCUMENT TO BUNDLE \"users\" WITH ...",
    ...
  ],
  "products": [
    "ADD DOCUMENT TO BUNDLE \"products\" WITH ...",
    ...
  ],
  "orders": [
    "ADD DOCUMENT TO BUNDLE \"orders\" WITH ...",
    ...
  ],
  "reviews": [...],
  "order_items": [...],
  "cart_items": [...]
}
```

## Command-Line Options

### generate_seed_queries.py

```bash
python generate_seed_queries.py [OPTIONS]

Options:
  --users INT          Number of users (default: 10000)
  --products INT       Number of products (default: 5000)
  --orders INT         Number of orders (default: 5000)
  --reviews INT        Number of reviews (default: 10000)
  --order-items INT    Number of order items (default: 8000)
  --cart-items INT     Number of cart items (default: 1000)
  --output PATH        Output file path (default: results/seed_queries.json)
```

### seed_from_file.py

```bash
python seed_from_file.py [OPTIONS]

Options:
  --input PATH         Input file path (default: results/seed_queries.json)
  --host STR           SyndrDB host (default: 127.0.0.1)
  --port INT           SyndrDB port (default: 1776)
  --database STR       Database name (default: firestorm_test)
```

## Example Workflows

### Workflow 1: Generate Once, Execute Multiple Times

```bash
# Generate queries once
python generate_seed_queries.py --users 50000 --products 25000

# Execute multiple times with different databases
python seed_from_file.py --database test_db_1
python seed_from_file.py --database test_db_2
python seed_from_file.py --database test_db_3
```

### Workflow 2: Custom Dataset Sizes

```bash
# Small dataset for quick tests
python generate_seed_queries.py \
  --users 1000 \
  --products 500 \
  --orders 500 \
  --reviews 1000 \
  --output results/small_seed.json

# Execute small dataset
python seed_from_file.py --input results/small_seed.json
```

### Workflow 3: Interactive Menu

```bash
# Use the interactive menu
./start-firestorm.sh

# Choose option 4 to generate
# Choose option 5 to execute
```

## Benefits

1. **Speed**: Generate once, reuse many times
2. **Consistency**: Same data across test runs
3. **Flexibility**: Different sizes for different tests
4. **Offline**: Generate queries without database access
5. **Version Control**: Save seed files in git for reproducible tests

## Logs

- Generation logs: `results/seed_generation.log`
- Execution logs: `results/seed_execution.log`
