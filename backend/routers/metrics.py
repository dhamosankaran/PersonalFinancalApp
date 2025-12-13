"""
Metrics router for observability and monitoring.
Exposes metrics collected across all flows.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime
import time

from services.metrics import metrics_collector, MetricsCollector

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Get overall system metrics summary.
    Returns uptime, total requests, error rates, and per-flow summaries.
    """
    return metrics_collector.get_all_metrics()


@router.get("/flows/{flow_name}")
async def get_flow_metrics(flow_name: str) -> Dict[str, Any]:
    """
    Get detailed metrics for a specific flow.
    
    Args:
        flow_name: One of: document_processing, embedding, vector_store, rag, analytics, api
    """
    valid_flows = [
        MetricsCollector.FLOW_DOCUMENT,
        MetricsCollector.FLOW_EMBEDDING,
        MetricsCollector.FLOW_VECTOR_STORE,
        MetricsCollector.FLOW_RAG,
        MetricsCollector.FLOW_ANALYTICS,
        MetricsCollector.FLOW_API,
    ]
    
    if flow_name not in valid_flows:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid flow name. Valid flows: {valid_flows}"
        )
    
    return {
        "flow": flow_name,
        "metrics": metrics_collector.get_flow_metrics(flow_name)
    }


@router.get("/recent")
async def get_recent_timings(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent timing records for debugging and monitoring.
    
    Args:
        limit: Maximum number of records to return (default: 50)
    """
    return {
        "count": min(limit, 100),
        "timings": metrics_collector.get_recent_timings(min(limit, 100))
    }


@router.get("/benchmark")
async def get_benchmark_stats() -> Dict[str, Any]:
    """
    Get performance benchmarks across all flows.
    Returns p50, p95, p99 latencies for each flow.
    """
    all_metrics = metrics_collector.get_all_metrics()
    
    benchmarks = {}
    for flow_name, flow_data in all_metrics.get("flows", {}).items():
        if flow_data.get("total_requests", 0) > 0:
            benchmarks[flow_name] = {
                "total_requests": flow_data.get("total_requests", 0),
                "avg_latency_ms": flow_data.get("avg_latency_ms"),
                "p50_latency_ms": flow_data.get("p50_latency_ms"),
                "p95_latency_ms": flow_data.get("p95_latency_ms"),
                "p99_latency_ms": flow_data.get("p99_latency_ms"),
                "error_rate": flow_data.get("error_rate", 0),
            }
    
    return {
        "generated_at": datetime.now().isoformat(),
        "uptime_seconds": all_metrics.get("summary", {}).get("uptime_seconds", 0),
        "benchmarks": benchmarks
    }


@router.post("/benchmark/run")
async def run_benchmark() -> Dict[str, Any]:
    """
    Run a quick benchmark test on the RAG pipeline.
    This performs a sample query to measure current performance.
    """
    from services import rag_service
    
    start_time = time.perf_counter()
    
    try:
        # Run a sample query
        result = await rag_service.query(
            question="What are my recent transactions?",
            user_id="benchmark_user",
            n_results=5
        )
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return {
            "status": "success",
            "query": "What are my recent transactions?",
            "elapsed_ms": round(elapsed_ms, 2),
            "metrics": result.get("metrics", {}),
            "message": f"Benchmark completed in {elapsed_ms:.2f}ms"
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "error",
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(e)
        }


@router.delete("/reset")
async def reset_metrics() -> Dict[str, str]:
    """
    Reset all metrics. Useful for testing and starting fresh.
    """
    metrics_collector.reset()
    return {"message": "All metrics have been reset"}


@router.get("/health")
async def metrics_health() -> Dict[str, Any]:
    """
    Health check for the metrics system.
    """
    all_metrics = metrics_collector.get_all_metrics()
    
    return {
        "status": "healthy",
        "uptime_seconds": all_metrics.get("summary", {}).get("uptime_seconds", 0),
        "total_requests_tracked": all_metrics.get("summary", {}).get("total_requests", 0),
        "flows_being_tracked": len(all_metrics.get("flows", {}))
    }
