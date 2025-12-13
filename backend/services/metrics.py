"""
Metrics collection service for RAG application observability.
Tracks latency, throughput, and quality metrics across all flows.
"""

import time
import threading
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import os


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class TimingMetric:
    """Represents a timing observation."""
    flow: str
    operation: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowMetrics:
    """Aggregated metrics for a flow."""
    total_requests: int = 0
    total_errors: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    last_request_time: Optional[datetime] = None
    
    # Flow-specific counters
    counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Flow-specific gauges (current values)
    gauges: Dict[str, float] = field(default_factory=dict)
    
    # Histograms for distributions
    histograms: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    def add_timing(self, duration_ms: float):
        """Add a timing observation."""
        self.total_requests += 1
        self.latencies_ms.append(duration_ms)
        self.last_request_time = datetime.now()
        
        # Keep only last 1000 latencies for memory efficiency
        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-1000:]
    
    def add_error(self):
        """Record an error."""
        self.total_errors += 1
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter."""
        self.counters[name] += value
    
    def set_gauge(self, name: str, value: float):
        """Set a gauge value."""
        self.gauges[name] = value
    
    def add_histogram(self, name: str, value: float):
        """Add a value to a histogram."""
        self.histograms[name].append(value)
        # Keep only last 1000 values
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]
    
    def get_percentile(self, p: float) -> float:
        """Get latency percentile."""
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * p / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        stats = {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(self.total_requests, 1),
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
        }
        
        if self.latencies_ms:
            stats.update({
                "avg_latency_ms": round(statistics.mean(self.latencies_ms), 2),
                "min_latency_ms": round(min(self.latencies_ms), 2),
                "max_latency_ms": round(max(self.latencies_ms), 2),
                "p50_latency_ms": round(self.get_percentile(50), 2),
                "p95_latency_ms": round(self.get_percentile(95), 2),
                "p99_latency_ms": round(self.get_percentile(99), 2),
            })
            if len(self.latencies_ms) > 1:
                stats["stddev_latency_ms"] = round(statistics.stdev(self.latencies_ms), 2)
        
        stats["counters"] = dict(self.counters)
        stats["gauges"] = self.gauges
        
        # Add histogram stats
        histogram_stats = {}
        for name, values in self.histograms.items():
            if values:
                histogram_stats[name] = {
                    "avg": round(statistics.mean(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "count": len(values)
                }
        stats["histograms"] = histogram_stats
        
        return stats


class MetricsCollector:
    """
    Centralized metrics collection service.
    Thread-safe singleton for collecting metrics across all flows.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Flow names
    FLOW_DOCUMENT = "document_processing"
    FLOW_EMBEDDING = "embedding"
    FLOW_VECTOR_STORE = "vector_store"
    FLOW_RAG = "rag"
    FLOW_ANALYTICS = "analytics"
    FLOW_API = "api"
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._flows: Dict[str, FlowMetrics] = defaultdict(FlowMetrics)
        self._start_time = datetime.now()
        self._recent_timings: List[TimingMetric] = []
        self._max_recent = 100  # Keep last 100 timing records
        self._initialized = True
        
        # Initialize all known flows
        for flow in [self.FLOW_DOCUMENT, self.FLOW_EMBEDDING, 
                     self.FLOW_VECTOR_STORE, self.FLOW_RAG, 
                     self.FLOW_ANALYTICS, self.FLOW_API]:
            self._flows[flow] = FlowMetrics()
    
    def record_timing(
        self, 
        flow: str, 
        operation: str, 
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a timing metric for an operation.
        
        Args:
            flow: The flow name (e.g., 'rag', 'embedding')
            operation: The operation name (e.g., 'query', 'embed_text')
            duration_ms: Duration in milliseconds
            metadata: Optional additional metadata
        """
        with self._lock:
            self._flows[flow].add_timing(duration_ms)
            
            timing = TimingMetric(
                flow=flow,
                operation=operation,
                duration_ms=duration_ms,
                metadata=metadata or {}
            )
            self._recent_timings.append(timing)
            
            # Keep only recent timings
            if len(self._recent_timings) > self._max_recent:
                self._recent_timings = self._recent_timings[-self._max_recent:]
    
    def record_error(self, flow: str, error_type: str = "unknown"):
        """Record an error for a flow."""
        with self._lock:
            self._flows[flow].add_error()
            self._flows[flow].increment_counter(f"errors_{error_type}")
    
    def increment_counter(self, flow: str, name: str, value: int = 1):
        """Increment a counter for a flow."""
        with self._lock:
            self._flows[flow].increment_counter(name, value)
    
    def set_gauge(self, flow: str, name: str, value: float):
        """Set a gauge value for a flow."""
        with self._lock:
            self._flows[flow].set_gauge(name, value)
    
    def add_histogram(self, flow: str, name: str, value: float):
        """Add a value to a histogram for a flow."""
        with self._lock:
            self._flows[flow].add_histogram(name, value)
    
    def get_flow_metrics(self, flow: str) -> Dict[str, Any]:
        """Get metrics for a specific flow."""
        with self._lock:
            return self._flows[flow].get_stats()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics across all flows."""
        with self._lock:
            uptime = (datetime.now() - self._start_time).total_seconds()
            
            total_requests = sum(f.total_requests for f in self._flows.values())
            total_errors = sum(f.total_errors for f in self._flows.values())
            
            return {
                "summary": {
                    "uptime_seconds": round(uptime, 2),
                    "start_time": self._start_time.isoformat(),
                    "total_requests": total_requests,
                    "total_errors": total_errors,
                    "error_rate": round(total_errors / max(total_requests, 1), 4),
                },
                "flows": {
                    flow: metrics.get_stats() 
                    for flow, metrics in self._flows.items()
                }
            }
    
    def get_recent_timings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent timing records."""
        with self._lock:
            recent = self._recent_timings[-limit:]
            return [
                {
                    "flow": t.flow,
                    "operation": t.operation,
                    "duration_ms": t.duration_ms,
                    "timestamp": t.timestamp.isoformat(),
                    "metadata": t.metadata
                }
                for t in recent
            ]
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._flows = defaultdict(FlowMetrics)
            self._recent_timings = []
            self._start_time = datetime.now()
            
            # Re-initialize flows
            for flow in [self.FLOW_DOCUMENT, self.FLOW_EMBEDDING, 
                         self.FLOW_VECTOR_STORE, self.FLOW_RAG, 
                         self.FLOW_ANALYTICS, self.FLOW_API]:
                self._flows[flow] = FlowMetrics()


class Timer:
    """Context manager for timing operations."""
    
    def __init__(
        self, 
        flow: str, 
        operation: str,
        collector: Optional[MetricsCollector] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.flow = flow
        self.operation = operation
        self.collector = collector or metrics_collector
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        self.duration_ms = (end_time - self.start_time) * 1000
        
        if exc_type is not None:
            self.metadata["error"] = str(exc_type.__name__)
            self.collector.record_error(self.flow, exc_type.__name__)
        
        self.collector.record_timing(
            self.flow,
            self.operation,
            self.duration_ms,
            self.metadata
        )
        
        return False  # Don't suppress exceptions


# Global instance
metrics_collector = MetricsCollector()
