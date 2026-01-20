#!/usr/bin/env python3
# firestorm/generate_seed_queries.py
"""
Generate seed data queries and save to file (without executing)
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
        logging.FileHandler('results/seed_generation.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate seed data queries and save to file"
    )
    
    parser.add_argument(
        '--users',
        type=int,
        default=10000,
        help='Number of users (default: 10000)'
    )
    
    parser.add_argument(
        '--products',
        type=int,
        default=5000,
        help='Number of products (default: 5000)'
    )
    
    parser.add_argument(
        '--orders',
        type=int,
        default=5000,
        help='Number of orders (default: 5000)'
    )
    
    parser.add_argument(
        '--reviews',
        type=int,
        default=10000,
        help='Number of reviews (default: 10000)'
    )
    
    parser.add_argument(
        '--order-items',
        type=int,
        default=8000,
        help='Number of order items (default: 8000)'
    )
    
    parser.add_argument(
        '--cart-items',
        type=int,
        default=1000,
        help='Number of cart items (default: 1000)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='results/seed_queries.json',
        help='Output file path (default: results/seed_queries.json)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    logger.info("🌱 Generating seed data queries...")
    logger.info(f"   Users: {args.users}")
    logger.info(f"   Products: {args.products}")
    logger.info(f"   Orders: {args.orders}")
    logger.info(f"   Reviews: {args.reviews}")
    logger.info(f"   Order Items: {args.order_items}")
    logger.info(f"   Cart Items: {args.cart_items}")
    logger.info(f"   Output: {args.output}")
    
    # Create results directory
    Path("results").mkdir(exist_ok=True)
    
    # Create conductor (we only need the data seeder)
    conductor = FirestormConductor(
        syndrdb_host="127.0.0.1",
        syndrdb_port=1776,
        username="root",
        password="root",
        database="primary"
    )
    
    try:
        # Generate queries
        queries = conductor.data_seeder.generate_seed_queries(
            user_count=args.users,
            product_count=args.products,
            order_count=args.orders,
            review_count=args.reviews,
            order_item_count=args.order_items,
            cart_item_count=args.cart_items
        )
        
        # Save to file
        conductor.data_seeder.save_seed_queries_to_file(queries, filepath=args.output)
        
        logger.info("✅ Seed query generation complete!")
        logger.info(f"📄 Queries saved to: {args.output}")
        logger.info("   Run with --seed-from-file to execute these queries")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate seed queries: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
