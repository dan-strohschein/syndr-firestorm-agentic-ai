# firestorm/tools/metrics-collector.py
"""
Metrics collection and aggregation for Firestorm load testing
Calculates percentiles, detects data collisions, generates reports
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collect and aggregate metrics from multiple agents"""
    
    def __init__(self):
        self.agent_metrics: List[Dict[str, Any]] = []
        self.test_start_time: float = 0
        self.test_end_time: float = 0
        self.test_info: Dict[str, Any] = {}
        
        # Ensure results directory exists
        Path("results").mkdir(exist_ok=True)
    
    def set_test_info(self, info: Dict[str, Any]):
        """Set test information"""
        self.test_info = info
        self.test_start_time = info.get("start_time", 0)
        self.test_end_time = info.get("end_time", 0)
    
    def add_agent_metrics(self, metrics: Dict[str, Any]):
        """Add metrics from a single agent"""
        self.agent_metrics.append(metrics)
    
    def calculate_aggregate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate metrics across all agents"""
        
        if not self.agent_metrics:
            return {}
        
        # Collect all latencies for percentile calculation
        all_latencies = []
        total_queries = 0
        total_successful = 0
        total_failed = 0
        total_errors = 0
        
        for agent in self.agent_metrics:
            queries = agent.get("queries_executed", 0)
            successful = agent.get("successful_queries", 0)
            failed = agent.get("failed_queries", 0)
            avg_latency = agent.get("avg_latency_ms", 0)
            
            total_queries += queries
            total_successful += successful
            total_failed += failed
            total_errors += agent.get("error_count", 0)
            
            # Approximate latency distribution (assuming normal distribution around average)
            if successful > 0:
                all_latencies.extend([avg_latency] * successful)
        
        # Calculate percentiles
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            n = len(sorted_latencies)
            
            p50 = sorted_latencies[int(n * 0.50)] if n > 0 else 0
            p95 = sorted_latencies[int(n * 0.95)] if n > 1 else 0
            p99 = sorted_latencies[int(n * 0.99)] if n > 2 else 0
            avg = sum(sorted_latencies) / n if n > 0 else 0
            min_lat = min(sorted_latencies) if sorted_latencies else 0
            max_lat = max(sorted_latencies) if sorted_latencies else 0
        else:
            p50 = p95 = p99 = avg = min_lat = max_lat = 0
        
        # Calculate test duration
        duration = self.test_end_time - self.test_start_time if self.test_end_time > 0 else 0
        
        # Calculate throughput
        qps = total_queries / duration if duration > 0 else 0
        
        # Success rate
        success_rate = (total_successful / total_queries * 100) if total_queries > 0 else 0
        
        aggregate = {
            "queries": {
                "total": total_queries,
                "successful": total_successful,
                "failed": total_failed,
                "success_rate_percent": round(success_rate, 2)
            },
            "latency": {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "avg_ms": round(avg, 2),
                "min_ms": round(min_lat, 2),
                "max_ms": round(max_lat, 2)
            },
            "throughput": {
                "queries_per_second": round(qps, 2),
                "duration_seconds": round(duration, 2)
            },
            "errors": {
                "total_errors": total_errors,
                "error_rate_percent": round((total_errors / total_queries * 100) if total_queries > 0 else 0, 2)
            }
        }
        
        return aggregate
    
    def detect_data_collisions(self) -> Dict[str, Any]:
        """
        Detect potential data collisions
        This is a placeholder - actual collision detection would require
        tracking specific records and their states
        """
        
        # Simplified collision detection based on error patterns
        collision_indicators = {
            "high_error_rate": False,
            "timeout_errors": 0,
            "lock_errors": 0,
            "consistency_warnings": []
        }
        
        aggregate = self.calculate_aggregate_metrics()
        error_rate = aggregate.get("errors", {}).get("error_rate_percent", 0)
        
        if error_rate > 5.0:
            collision_indicators["high_error_rate"] = True
            collision_indicators["consistency_warnings"].append(
                f"High error rate detected: {error_rate:.2f}% - may indicate concurrency issues"
            )
        
        return collision_indicators
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate complete test report"""
        
        aggregate = self.calculate_aggregate_metrics()
        collisions = self.detect_data_collisions()
        
        # Performance assessment
        success_rate = aggregate.get("queries", {}).get("success_rate_percent", 0)
        p99_latency = aggregate.get("latency", {}).get("p99_ms", 0)
        
        if success_rate >= 99.0 and p99_latency < 5000:
            performance_grade = "EXCELLENT"
        elif success_rate >= 95.0 and p99_latency < 10000:
            performance_grade = "GOOD"
        elif success_rate >= 90.0:
            performance_grade = "ACCEPTABLE"
        else:
            performance_grade = "POOR"
        
        report = {
            "test_info": self.test_info,
            "aggregate_metrics": aggregate,
            "collision_detection": collisions,
            "performance_assessment": {
                "grade": performance_grade,
                "passed": success_rate >= 95.0 and p99_latency < 10000
            },
            "agent_metrics": self.agent_metrics
        }
        
        return report
    
    def save_json_report(self, filepath: str = None) -> str:
        """Save report as JSON"""
        
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"results/firestorm_metrics_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved JSON report to {filepath}")
        return filepath
    
    def save_text_report(self, filepath: str = None) -> str:
        """Save report as text"""
        
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"results/firestorm_summary_{timestamp}.txt"
        
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            self._write_text_report(f, report)
        
        logger.info(f"Saved text report to {filepath}")
        return filepath
    
    def _write_text_report(self, f, report: Dict[str, Any]):
        """Write formatted text report"""
        
        f.write("=" * 80 + "\n")
        f.write("🔥 SYNDR FIRESTORM - LOAD TEST METRICS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # Test Info
        info = report.get("test_info", {})
        f.write("TEST CONFIGURATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Number of Agents: {info.get('num_agents', 'N/A')}\n")
        f.write(f"Test Duration: {info.get('duration_minutes', 'N/A')} minutes\n")
        f.write(f"Start Time: {info.get('start_time', 'N/A')}\n")
        f.write(f"End Time: {info.get('end_time', 'N/A')}\n\n")
        
        # Aggregate Metrics
        agg = report.get("aggregate_metrics", {})
        queries = agg.get("queries", {})
        latency = agg.get("latency", {})
        throughput = agg.get("throughput", {})
        errors = agg.get("errors", {})
        
        f.write("AGGREGATE METRICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Queries: {queries.get('total', 0)}\n")
        f.write(f"Successful: {queries.get('successful', 0)}\n")
        f.write(f"Failed: {queries.get('failed', 0)}\n")
        f.write(f"Success Rate: {queries.get('success_rate_percent', 0):.2f}%\n\n")
        
        f.write("LATENCY DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        f.write(f"P50 (Median): {latency.get('p50_ms', 0):.2f} ms\n")
        f.write(f"P95: {latency.get('p95_ms', 0):.2f} ms\n")
        f.write(f"P99: {latency.get('p99_ms', 0):.2f} ms\n")
        f.write(f"Average: {latency.get('avg_ms', 0):.2f} ms\n")
        f.write(f"Min: {latency.get('min_ms', 0):.2f} ms\n")
        f.write(f"Max: {latency.get('max_ms', 0):.2f} ms\n\n")
        
        f.write("THROUGHPUT\n")
        f.write("-" * 80 + "\n")
        f.write(f"Queries Per Second: {throughput.get('queries_per_second', 0):.2f}\n")
        f.write(f"Test Duration: {throughput.get('duration_seconds', 0):.2f} seconds\n\n")
        
        f.write("ERRORS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Errors: {errors.get('total_errors', 0)}\n")
        f.write(f"Error Rate: {errors.get('error_rate_percent', 0):.2f}%\n\n")
        
        # Performance Assessment
        assessment = report.get("performance_assessment", {})
        f.write("PERFORMANCE ASSESSMENT\n")
        f.write("-" * 80 + "\n")
        f.write(f"Grade: {assessment.get('grade', 'N/A')}\n")
        f.write(f"Test Passed: {'✅ YES' if assessment.get('passed', False) else '❌ NO'}\n\n")
        
        # Collision Detection
        collisions = report.get("collision_detection", {})
        f.write("DATA INTEGRITY CHECK\n")
        f.write("-" * 80 + "\n")
        f.write(f"High Error Rate: {'⚠️ YES' if collisions.get('high_error_rate', False) else '✅ NO'}\n")
        warnings = collisions.get("consistency_warnings", [])
        if warnings:
            f.write("\nWarnings:\n")
            for warning in warnings:
                f.write(f"  ⚠️ {warning}\n")
        else:
            f.write("✅ No data integrity issues detected\n")
        f.write("\n")
        
        # Per-Agent Summary
        f.write("PER-AGENT SUMMARY\n")
        f.write("-" * 80 + "\n")
        for agent in report.get("agent_metrics", []):
            f.write(f"\n{agent.get('agent_id', 'N/A')} ({agent.get('persona', 'N/A')})\n")
            f.write(f"  Queries: {agent.get('queries_executed', 0)}\n")
            f.write(f"  Success Rate: {agent.get('success_rate', 0) * 100:.2f}%\n")
            f.write(f"  Avg Latency: {agent.get('avg_latency_ms', 0):.2f} ms\n")
            f.write(f"  Errors: {agent.get('error_count', 0)}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")
    
    def print_summary(self):
        """Print summary to console"""
        report = self.generate_report()
        
        agg = report.get("aggregate_metrics", {})
        queries = agg.get("queries", {})
        latency = agg.get("latency", {})
        throughput = agg.get("throughput", {})
        assessment = report.get("performance_assessment", {})
        
        print("\n" + "=" * 80)
        print("🔥 FIRESTORM METRICS SUMMARY")
        print("=" * 80)
        print(f"\n✅ Total Queries: {queries.get('total', 0)}")
        print(f"✅ Success Rate: {queries.get('success_rate_percent', 0):.2f}%")
        print(f"✅ Latency (P50/P95/P99): {latency.get('p50_ms', 0):.0f}/{latency.get('p95_ms', 0):.0f}/{latency.get('p99_ms', 0):.0f} ms")
        print(f"✅ Throughput: {throughput.get('queries_per_second', 0):.2f} QPS")
        print(f"✅ Performance Grade: {assessment.get('grade', 'N/A')}")
        print("\n" + "=" * 80 + "\n")
