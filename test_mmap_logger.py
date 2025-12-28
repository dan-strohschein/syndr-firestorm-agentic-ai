#!/usr/bin/env python3
"""
Simple test to verify memory-mapped logging works correctly
"""

import logging
import time
import sys
from pathlib import Path
from tools.mmap_logger import setup_mmap_logging, register_handler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Set up memory-mapped logging
Path("results").mkdir(exist_ok=True)
mmap_handler = setup_mmap_logging(
    filepath='results/test_mmap.log',
    max_size=1 * 1024 * 1024,  # 1 MB for testing
    level=logging.INFO
)
register_handler(mmap_handler)

def main():
    """Run test"""
    logger.info("Starting memory-mapped logging test...")
    
    # Generate some log messages
    for i in range(100):
        logger.info(f"Test message {i+1}")
        logger.debug(f"Debug message {i+1}")
        logger.warning(f"Warning message {i+1}")
        
        if i % 10 == 0:
            stats = mmap_handler.get_stats()
            logger.info(f"Stats: {stats}")
        
        # Small delay to simulate real logging
        time.sleep(0.01)
    
    logger.info("Test complete! Flushing logs...")
    
    # Flush to ensure all logs are written
    mmap_handler.flush()
    
    # Get final stats
    final_stats = mmap_handler.get_stats()
    logger.info(f"Final stats: {final_stats}")
    
    # Verify the file was written
    mmap_file = Path('results/test_mmap.log')
    if mmap_file.exists():
        file_size = mmap_file.stat().st_size
        logger.info(f"Memory-mapped file created: {mmap_file} ({file_size:,} bytes)")
        
        # Read a sample of the content
        with open(mmap_file, 'rb') as f:
            content = f.read(1000).decode('utf-8', errors='ignore')
            lines = content.split('\n')[:5]
            logger.info(f"First few lines from mmap file:")
            for line in lines:
                if line.strip():
                    logger.info(f"  {line}")
    
    logger.info("✅ Memory-mapped logging test complete!")

if __name__ == "__main__":
    main()
