#!/usr/bin/env python3
# firestorm/seed_from_file.py
"""
Load and execute seed data queries from file
"""

import argparse
import logging
import sys
from pathlib import Path

from conductor.conductor import FirestormConductor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('results/seed_execution.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Load and execute seed data queries from file"
    )
    
    parser.add_argument(
        '--input',
        type=str,
        default='results/seed_queries.json',
        help='Input file path (default: results/seed_queries.json)'
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
        '--database',
        type=str,
        default='firestorm_test',
        help='Database name (default: firestorm_test)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Check if input file exists
    if not Path(args.input).exists():
        logger.error(f"❌ Input file not found: {args.input}")
        logger.error("   Run with --generate-seed first to create seed queries")
        sys.exit(1)
    
    logger.info(f"🌱 Loading and executing seed data from: {args.input}")
    logger.info(f"   Host: {args.host}:{args.port}")
    logger.info(f"   Database: {args.database}")
    
    # Create conductor
    conductor = FirestormConductor(
        syndrdb_host=args.host,
        syndrdb_port=args.port,
        username="root",
        password="root",
        database=args.database
    )
    
    try:
        # Setup database and bundles first
        logger.info("Setting up database and bundles...")
        conductor.setup_test_environment()
        
        # Execute queries from file
        conductor.data_seeder.execute_seed_queries_from_file(filepath=args.input)
        
        logger.info("✅ Seed data execution complete!")
        
    except Exception as e:
        logger.error(f"❌ Failed to execute seed queries: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
