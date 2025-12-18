"""
Tracing API router.
Provides endpoints for viewing traces, spans, and LLM call history.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from services.tracing import tracing_service
from database import SessionLocal

router = APIRouter(prefix="/api/traces", tags=["tracing"])


@router.get("/recent")
async def get_recent_traces(limit: int = Query(50, ge=1, le=100)) -> Dict[str, Any]:
    """
    Get recent traces from memory cache.
    
    Args:
        limit: Maximum number of traces to return (1-100)
    """
    traces = tracing_service.get_recent_traces(limit)
    return {
        "traces": traces,
        "count": len(traces)
    }


@router.get("/stats")
async def get_tracing_stats() -> Dict[str, Any]:
    """Get aggregated tracing statistics."""
    return tracing_service.get_stats()


@router.get("/llm-calls")
async def get_llm_calls_summary() -> Dict[str, Any]:
    """Get summary of LLM calls grouped by provider."""
    return tracing_service.get_llm_calls_summary()


@router.get("/history")
async def get_trace_history(
    limit: int = Query(50, ge=1, le=200),
    name: Optional[str] = None,
    status: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168)
) -> Dict[str, Any]:
    """
    Get trace history from database.
    
    Args:
        limit: Maximum traces to return
        name: Filter by trace name
        status: Filter by status (success, error, running)
        hours: Look back this many hours (max 168 = 1 week)
    """
    try:
        from models.tracing import Trace, Span
        
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.query(Trace).filter(Trace.start_time >= cutoff)
            
            if name:
                query = query.filter(Trace.name == name)
            if status:
                query = query.filter(Trace.status == status)
            
            query = query.order_by(Trace.start_time.desc()).limit(limit)
            traces = query.all()
            
            return {
                "traces": [t.to_dict() for t in traces],
                "count": len(traces),
                "filters": {
                    "name": name,
                    "status": status,
                    "hours": hours
                }
            }
        finally:
            db.close()
    except Exception as e:
        # If table doesn't exist yet, return empty
        return {
            "traces": [],
            "count": 0,
            "error": str(e)
        }


@router.get("/{trace_id}")
async def get_trace_details(trace_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific trace including all spans.
    """
    try:
        from models.tracing import Trace, Span
        
        db = SessionLocal()
        try:
            trace = db.query(Trace).filter(Trace.id == trace_id).first()
            
            if not trace:
                raise HTTPException(status_code=404, detail="Trace not found")
            
            spans = db.query(Span).filter(Span.trace_id == trace_id).order_by(Span.start_time).all()
            
            trace_dict = trace.to_dict()
            trace_dict["spans"] = [s.to_dict() for s in spans]
            
            # Calculate totals
            trace_dict["total_tokens"] = sum(s.total_tokens or 0 for s in spans)
            trace_dict["total_cost"] = sum(s.estimated_cost_usd or 0 for s in spans)
            trace_dict["llm_call_count"] = sum(1 for s in spans if s.model_name)
            
            return trace_dict
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-calls/history")
async def get_llm_call_history(
    limit: int = Query(100, ge=1, le=500),
    hours: int = Query(24, ge=1, le=168),
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed LLM call history from database.
    
    Args:
        limit: Maximum calls to return
        hours: Look back this many hours
        provider: Filter by provider (openai, gemini)
    """
    try:
        from models.tracing import Span
        
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.query(Span).filter(
                Span.start_time >= cutoff,
                Span.model_name.isnot(None)
            )
            
            if provider:
                query = query.filter(Span.provider == provider)
            
            query = query.order_by(Span.start_time.desc()).limit(limit)
            spans = query.all()
            
            # Calculate aggregates
            total_tokens = sum(s.total_tokens or 0 for s in spans)
            total_cost = sum(s.estimated_cost_usd or 0 for s in spans)
            
            return {
                "llm_calls": [s.to_dict() for s in spans],
                "count": len(spans),
                "aggregates": {
                    "total_tokens": total_tokens,
                    "total_cost_usd": round(total_cost, 6),
                    "avg_tokens_per_call": round(total_tokens / max(len(spans), 1)),
                    "avg_duration_ms": round(
                        sum(s.duration_ms or 0 for s in spans) / max(len(spans), 1), 2
                    )
                }
            }
        finally:
            db.close()
    except Exception as e:
        return {
            "llm_calls": [],
            "count": 0,
            "error": str(e)
        }


@router.delete("/clear")
async def clear_trace_history(hours: Optional[int] = None) -> Dict[str, str]:
    """
    Clear trace history from database.
    
    Args:
        hours: If provided, only clear traces older than this many hours.
               If not provided, clear all traces.
    """
    try:
        from models.tracing import Trace, Span
        
        db = SessionLocal()
        try:
            if hours:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                # Delete spans first (foreign key)
                deleted_spans = db.query(Span).filter(Span.start_time < cutoff).delete()
                deleted_traces = db.query(Trace).filter(Trace.start_time < cutoff).delete()
            else:
                deleted_spans = db.query(Span).delete()
                deleted_traces = db.query(Trace).delete()
            
            db.commit()
            return {
                "message": f"Cleared {deleted_traces} traces and {deleted_spans} spans"
            }
        finally:
            db.close()
    except Exception as e:
        return {"message": f"Error clearing traces: {e}"}
