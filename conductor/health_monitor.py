# firestorm/conductor/health_monitor.py
"""
Health monitoring for SyndrDB during load testing
Tracks real-time metrics and database health
"""

import logging
import time
from typing import Dict, Any, List
from collections import deque

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitor SyndrDB health during load testing"""
    
    def __init__(self, db_client):
        self.db_client = db_client
        
        # Rolling windows for metrics
        self.query_times = deque(maxlen=100)  # Last 100 query times
        self.query_success = deque(maxlen=100)  # Last 100 success/fail
        self.connection_checks = deque(maxlen=20)  # Last 20 connection checks
        
        # Cumulative counters
        self.total_queries = 0
        self.total_successful = 0
        self.total_failed = 0
        
        self.monitoring_start = time.time()
        
    def record_query(self, latency_ms: float, success: bool):
        """Record a query result"""
        self.query_times.append(latency_ms)
        self.query_success.append(1 if success else 0)
        
        self.total_queries += 1
        if success:
            self.total_successful += 1
        else:
            self.total_failed += 1
    
    def check_connection(self) -> bool:
        """Check if SyndrDB is responsive"""
        try:
            # Simple ping query
            start = time.time()
            result = self.db_client.execute('SELECT 1;')
            latency = (time.time() - start) * 1000
            
            success = result.get("success", False)
            self.connection_checks.append(1 if success else 0)
            
            if not success:
                logger.warning(f"Connection check failed: {result.get('error')}")
            
            return success
        except Exception as e:
            logger.error(f"Connection check error: {e}")
            self.connection_checks.append(0)
            return False
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current health metrics"""
        
        # Calculate latency percentiles
        if self.query_times:
            sorted_times = sorted(self.query_times)
            n = len(sorted_times)
            
            p50 = sorted_times[int(n * 0.50)] if n > 0 else 0
            p95 = sorted_times[int(n * 0.95)] if n > 1 else 0
            p99 = sorted_times[int(n * 0.99)] if n > 2 else 0
            avg = sum(sorted_times) / n if n > 0 else 0
            min_lat = min(sorted_times)
            max_lat = max(sorted_times)
        else:
            p50 = p95 = p99 = avg = min_lat = max_lat = 0
        
        # Calculate success rate
        recent_success_rate = (
            sum(self.query_success) / len(self.query_success) * 100 
            if self.query_success else 0
        )
        
        overall_success_rate = (
            self.total_successful / self.total_queries * 100 
            if self.total_queries > 0 else 0
        )
        
        # Calculate query rate
        elapsed = time.time() - self.monitoring_start
        queries_per_second = self.total_queries / elapsed if elapsed > 0 else 0
        
        # Connection health
        connection_health = (
            sum(self.connection_checks) / len(self.connection_checks) * 100 
            if self.connection_checks else 0
        )
        
        return {
            "latency": {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "avg_ms": round(avg, 2),
                "min_ms": round(min_lat, 2),
                "max_ms": round(max_lat, 2)
            },
            "throughput": {
                "total_queries": self.total_queries,
                "queries_per_second": round(queries_per_second, 2)
            },
            "success_rate": {
                "recent_100": round(recent_success_rate, 2),
                "overall": round(overall_success_rate, 2)
            },
            "connection": {
                "health_percent": round(connection_health, 2),
                "recent_checks": len(self.connection_checks),
                "responsive": connection_health > 50
            },
            "uptime_seconds": round(elapsed, 2)
        }
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary"""
        metrics = self.collect_metrics()
        
        lat = metrics["latency"]
        thr = metrics["throughput"]
        suc = metrics["success_rate"]
        con = metrics["connection"]
        
        status = "✅ HEALTHY" if con["responsive"] and suc["recent_100"] > 95 else "⚠️ DEGRADED"
        
        summary = (
            f"{status} | "
            f"QPS: {thr['queries_per_second']:.1f} | "
            f"Success: {suc['recent_100']:.1f}% | "
            f"Latency p50/p95/p99: {lat['p50_ms']:.0f}/{lat['p95_ms']:.0f}/{lat['p99_ms']:.0f}ms"
        )
        
        return summary
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        metrics = self.collect_metrics()
        
        # Health criteria
        connection_ok = metrics["connection"]["responsive"]
        success_ok = metrics["success_rate"]["recent_100"] > 90
        latency_ok = metrics["latency"]["p99_ms"] < 5000  # Under 5 seconds for p99
        
        return connection_ok and success_ok and latency_ok
    
    def reset(self):
        """Reset all metrics"""
        self.query_times.clear()
        self.query_success.clear()
        self.connection_checks.clear()
        
        self.total_queries = 0
        self.total_successful = 0
        self.total_failed = 0
        
        self.monitoring_start = time.time()
        logger.info("Health monitor metrics reset")
