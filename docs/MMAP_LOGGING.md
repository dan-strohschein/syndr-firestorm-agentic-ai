# Memory-Mapped File Logging

## Overview

The Firestorm load testing framework now includes memory-mapped file logging that runs on a separate thread. This ensures that logging operations **do not impact execution timing or performance** of the main load testing operations.

## How It Works

### Architecture

1. **Queue-Based Design**: Log records are added to a thread-safe queue using `put_nowait()` to avoid any blocking
2. **Separate Writer Thread**: A dedicated background thread continuously pulls log records from the queue and writes them to the memory-mapped file
3. **Memory-Mapped File**: Uses Python's `mmap` module for efficient file I/O without system call overhead for each write

### Key Features

- **Zero Impact on Execution**: Logging calls return immediately after queuing, with no I/O blocking
- **Thread-Safe**: All operations are protected by locks and use thread-safe queue operations
- **Automatic Cleanup**: `atexit` handlers ensure proper shutdown and flushing of pending logs
- **Configurable Size**: Memory-mapped file size is configurable (default: 100 MB)
- **Performance Monitoring**: Built-in statistics tracking (queue size, bytes written, etc.)

## Usage

### Basic Setup

```python
from tools.mmap_logger import setup_mmap_logging, register_handler

# Set up memory-mapped logging
mmap_handler = setup_mmap_logging(
    filepath='results/firestorm_mmap.log',
    max_size=100 * 1024 * 1024,  # 100 MB
    level=logging.INFO
)
register_handler(mmap_handler)
```

### Configuration Options

- `filepath`: Path to the memory-mapped log file
- `max_size`: Maximum size in bytes (default: 100 MB)
- `queue_size`: Maximum queue size for pending log records (default: 10,000)
- `level`: Logging level (default: `logging.NOTSET`)

### Getting Statistics

```python
stats = mmap_handler.get_stats()
# Returns:
# {
#     'queue_size': 0,
#     'bytes_written': 13766,
#     'max_size': 1048576,
#     'percent_full': 1.31,
#     'running': True
# }
```

## Implementation Details

### File Structure

The memory-mapped file is:
1. Pre-allocated to the specified `max_size`
2. Initialized with null bytes (`\x00`)
3. Written sequentially as log records arrive
4. Flushed after each write to ensure data persistence

### Thread Safety

- **Emit Method**: Called from any thread, adds to queue without blocking
- **Writer Thread**: Single background thread processes queue
- **Lock Protection**: File write operations are protected by a threading lock

### Queue Behavior

When the queue is full (10,000 records by default):
- New log records are **silently dropped** to avoid blocking
- This ensures main execution threads are never blocked by logging

When the file is full:
- Writes stop to avoid overwriting existing data
- Consider increasing `max_size` if this occurs

## Files Modified

### Core Implementation
- **tools/mmap_logger.py**: Complete memory-mapped logging handler implementation

### Integration Points
- **run-firestorm.py**: Main Firestorm orchestrator
- **test-firestorm-mock.py**: Mock database test script
- **test-firestorm-ollama-mock.py**: Ollama AI + mock database test

### Test Files
- **test_mmap_logger.py**: Standalone test to verify functionality

## Performance Characteristics

### Advantages
- **Non-blocking**: Main thread execution is never blocked by logging
- **Fast Writes**: Memory-mapped I/O is faster than traditional file writes
- **Batch Efficiency**: Background thread can batch process log records

### Trade-offs
- **Memory Usage**: Pre-allocates the entire file size (100 MB by default)
- **Log Drops**: Under extreme load, logs may be dropped if queue fills
- **Sequential Write**: Cannot write past the pre-allocated size

## Testing

Run the standalone test:
```bash
python test_mmap_logger.py
```

This will:
1. Create a memory-mapped log file in `results/test_mmap.log`
2. Generate 100 test log messages
3. Display statistics about queue size and bytes written
4. Verify the file was created correctly

## Notes

- The background writer thread is created as a daemon thread
- Automatic cleanup via `atexit` ensures logs are flushed on exit
- All log messages go to **both** the memory-mapped file and regular log file/console
- The memory-mapped file uses UTF-8 encoding for all log messages
