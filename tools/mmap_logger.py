#!/usr/bin/env python3
"""
Memory-Mapped File Logger
Provides a thread-safe logging handler that writes log records to a memory-mapped file
on a separate thread to avoid impacting execution timing.
"""

import logging
import mmap
import threading
import queue
import time
import os
from pathlib import Path
from typing import Optional


class MemoryMappedLogHandler(logging.Handler):
    """
    Logging handler that writes to a memory-mapped file on a separate thread.
    
    This handler queues log records and processes them asynchronously to ensure
    that logging operations don't impact the timing or performance of the main
    execution thread.
    """
    
    def __init__(
        self,
        filepath: str,
        max_size: int = 100 * 1024 * 1024,  # 100 MB default
        queue_size: int = 10000,
        level: int = logging.NOTSET
    ):
        """
        Initialize the memory-mapped log handler.
        
        Args:
            filepath: Path to the memory-mapped log file
            max_size: Maximum size of the memory-mapped file in bytes
            queue_size: Maximum number of log records to queue
            level: Logging level
        """
        super().__init__(level)
        
        self.filepath = Path(filepath)
        self.max_size = max_size
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.running = False
        self.writer_thread: Optional[threading.Thread] = None
        self.current_position = 0
        self.lock = threading.Lock()
        
        # Create the file and initialize it
        self._initialize_file()
        
        # Start the writer thread
        self.start()
    
    def _initialize_file(self):
        """Create and initialize the memory-mapped file."""
        # Ensure directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not self.filepath.exists():
            with open(self.filepath, 'wb') as f:
                # Initialize file with zeros to the max size
                f.write(b'\x00' * self.max_size)
        else:
            # If file exists, ensure it's the right size
            file_size = self.filepath.stat().st_size
            if file_size < self.max_size:
                with open(self.filepath, 'ab') as f:
                    f.write(b'\x00' * (self.max_size - file_size))
        
        # Open the memory-mapped file
        self.file_handle = open(self.filepath, 'r+b')
        self.mmap = mmap.mmap(self.file_handle.fileno(), self.max_size)
        
        # Find the current position (end of written data)
        self._find_current_position()
    
    def _find_current_position(self):
        """Find the current write position in the memory-mapped file."""
        # Look for the first null byte
        try:
            pos = self.mmap.find(b'\x00')
            self.current_position = pos if pos != -1 else 0
        except:
            self.current_position = 0
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record by adding it to the queue.
        
        This method is called by the logging system and executes on the caller's thread.
        It simply adds the record to a queue for asynchronous processing.
        """
        try:
            # Format the record
            msg = self.format(record) + '\n'
            
            # Add to queue without blocking (use put_nowait to avoid delays)
            try:
                self.log_queue.put_nowait(msg)
            except queue.Full:
                # If queue is full, silently drop the message to avoid blocking
                pass
                
        except Exception:
            # Don't let logging errors propagate
            self.handleError(record)
    
    def _writer_loop(self):
        """
        Main loop for the writer thread.
        
        This thread continuously pulls log records from the queue and writes
        them to the memory-mapped file.
        """
        while self.running:
            try:
                # Get message from queue with timeout
                try:
                    msg = self.log_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Write to memory-mapped file
                self._write_to_mmap(msg)
                
                # Mark task as done
                self.log_queue.task_done()
                
            except Exception as e:
                # Don't let exceptions kill the writer thread
                print(f"MemoryMappedLogHandler writer error: {e}", flush=True)
    
    def _write_to_mmap(self, msg: str):
        """
        Write a message to the memory-mapped file.
        
        Args:
            msg: The message to write
        """
        with self.lock:
            try:
                msg_bytes = msg.encode('utf-8')
                msg_len = len(msg_bytes)
                
                # Check if we have space
                if self.current_position + msg_len >= self.max_size:
                    # Wrap around or stop writing
                    # For now, we'll just stop writing to avoid overwriting
                    return
                
                # Write to memory-mapped file
                self.mmap.seek(self.current_position)
                self.mmap.write(msg_bytes)
                self.current_position += msg_len
                
                # Flush to ensure data is written
                self.mmap.flush()
                
            except Exception as e:
                print(f"MemoryMappedLogHandler write error: {e}", flush=True)
    
    def start(self):
        """Start the writer thread."""
        if not self.running:
            self.running = True
            self.writer_thread = threading.Thread(
                target=self._writer_loop,
                name="MemoryMappedLogWriter",
                daemon=True
            )
            self.writer_thread.start()
    
    def stop(self, timeout: float = 5.0):
        """
        Stop the writer thread and wait for it to finish.
        
        Args:
            timeout: Maximum time to wait for the thread to finish
        """
        if self.running:
            self.running = False
            
            # Wait for queue to be processed
            try:
                self.log_queue.join()
            except:
                pass
            
            # Wait for thread to finish
            if self.writer_thread and self.writer_thread.is_alive():
                self.writer_thread.join(timeout=timeout)
    
    def close(self):
        """Close the handler and clean up resources."""
        # Stop the writer thread
        self.stop()
        
        # Close the memory-mapped file
        if hasattr(self, 'mmap') and self.mmap:
            try:
                self.mmap.close()
            except:
                pass
        
        # Close the file handle
        if hasattr(self, 'file_handle') and self.file_handle:
            try:
                self.file_handle.close()
            except:
                pass
        
        super().close()
    
    def flush(self):
        """Flush the handler by waiting for the queue to be processed."""
        try:
            self.log_queue.join()
            if hasattr(self, 'mmap') and self.mmap:
                self.mmap.flush()
        except:
            pass
    
    def get_stats(self) -> dict:
        """
        Get statistics about the handler.
        
        Returns:
            Dictionary with stats about queue size, bytes written, etc.
        """
        return {
            'queue_size': self.log_queue.qsize(),
            'bytes_written': self.current_position,
            'max_size': self.max_size,
            'percent_full': (self.current_position / self.max_size) * 100,
            'running': self.running
        }


def setup_mmap_logging(
    filepath: str = 'results/firestorm_mmap.log',
    max_size: int = 100 * 1024 * 1024,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> MemoryMappedLogHandler:
    """
    Set up memory-mapped logging and add it to the root logger.
    
    Args:
        filepath: Path to the memory-mapped log file
        max_size: Maximum size of the memory-mapped file in bytes
        level: Logging level
        format_string: Custom format string for log messages
    
    Returns:
        The configured MemoryMappedLogHandler instance
    """
    # Create the handler
    handler = MemoryMappedLogHandler(filepath, max_size, level=level)
    
    # Set up formatter
    if format_string is None:
        format_string = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    
    # Add to root logger
    logging.getLogger().addHandler(handler)
    
    return handler


# Ensure handler is properly closed on program exit
import atexit

_handlers = []

def _cleanup_handlers():
    """Clean up all memory-mapped handlers on exit."""
    for handler in _handlers:
        try:
            handler.close()
        except:
            pass

atexit.register(_cleanup_handlers)

def register_handler(handler: MemoryMappedLogHandler):
    """Register a handler for cleanup on exit."""
    _handlers.append(handler)
