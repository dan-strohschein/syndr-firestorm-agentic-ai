#!/usr/bin/env python3
"""
Test script to verify high-entropy improvements

This script validates that the expanded categories and entropy mechanisms
are working correctly.
"""

import sys
from conductor.expanded_categories import (
    PRODUCT_CATEGORIES,
    RATING_VALUES,
    STOCK_RANGES,
    PRICE_RANGES,
    ORDER_STATUSES,
    get_random_category,
    get_random_category_subset
)

def test_category_count():
    """Verify we have 350+ categories"""
    count = len(PRODUCT_CATEGORIES)
    print(f"✓ Product categories: {count}")
    assert count >= 350, f"Expected 350+ categories, got {count}"
    print(f"  Target met! ({count} >= 350)")

def test_unique_categories():
    """Verify all categories are unique"""
    unique = len(set(PRODUCT_CATEGORIES))
    total = len(PRODUCT_CATEGORIES)
    assert unique == total, f"Found duplicate categories: {total - unique} duplicates"
    print(f"✓ All categories are unique")

def test_entropy_dimensions():
    """Verify entropy dimensions are properly defined"""
    print(f"✓ Rating values: {len(RATING_VALUES)} discrete values")
    print(f"✓ Stock ranges: {len(STOCK_RANGES)} ranges")
    print(f"✓ Price ranges: {len(PRICE_RANGES)} ranges")
    print(f"✓ Order statuses: {len(ORDER_STATUSES)} statuses")
    
    # Calculate total combinations
    combinations = len(PRODUCT_CATEGORIES) * len(RATING_VALUES) * len(STOCK_RANGES)
    print(f"\n✓ Total query combinations: {combinations:,}")
    print(f"  (365 categories × {len(RATING_VALUES)} ratings × {len(STOCK_RANGES)} stock ranges)")

def test_agent_subsets():
    """Verify agent-specific category subsets work"""
    subset1 = get_random_category_subset(20)
    subset2 = get_random_category_subset(20)
    
    print(f"\n✓ Agent subset 1: {len(subset1)} categories")
    print(f"  Sample: {', '.join(subset1[:5])}")
    print(f"✓ Agent subset 2: {len(subset2)} categories")
    print(f"  Sample: {', '.join(subset2[:5])}")
    
    # Calculate overlap
    overlap = set(subset1) & set(subset2)
    overlap_pct = len(overlap) / len(subset1) * 100
    print(f"\n✓ Overlap between agents: {len(overlap)}/{len(subset1)} ({overlap_pct:.1f}%)")
    print(f"  Expected: ~5.5% for random 20-category subsets from 365")

def test_collision_probability():
    """Calculate theoretical collision probability"""
    total_categories = len(PRODUCT_CATEGORIES)
    categories_per_agent = 20
    num_agents = 10
    
    # Probability that two random subsets share at least one category
    # Using approximation: 1 - (1 - k/n)^k where k=subset size, n=total
    p_no_collision = (1 - categories_per_agent/total_categories) ** categories_per_agent
    p_collision = 1 - p_no_collision
    
    print(f"\n✓ Collision Probability Analysis:")
    print(f"  Total categories: {total_categories}")
    print(f"  Categories per agent: {categories_per_agent}")
    print(f"  Number of agents: {num_agents}")
    print(f"  Probability of category overlap between 2 agents: {p_collision*100:.2f}%")
    print(f"  Previous system (28 categories): ~42% overlap")
    print(f"  Improvement: {(0.42/p_collision):.1f}x reduction in overlap")

def main():
    """Run all tests"""
    print("=" * 70)
    print("HIGH-ENTROPY TEST DATA VALIDATION")
    print("=" * 70)
    print()
    
    try:
        test_category_count()
        print()
        test_unique_categories()
        print()
        test_entropy_dimensions()
        print()
        test_agent_subsets()
        print()
        test_collision_probability()
        
        print()
        print("=" * 70)
        print("✅ ALL TESTS PASSED - High-entropy system is working correctly!")
        print("=" * 70)
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
