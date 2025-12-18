"""
LLM Tracing Service for observability.
Provides context managers and utilities for tracing LLM calls and operations.
"""

import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import deque

from sqlalchemy.orm import Session
from database import SessionLocal


# Token cost estimates (per 1M tokens, USD)
TOKEN_COSTS = {
    "gemini": {"input": 0.075, "output": 0.30},  # Gemini 1.5 Flash
    "gemini-pro": {"input": 1.25, "output": 5.00},  # Gemini 1.5 Pro
    "openai": {"input": 0.50, "output": 1.50},  # GPT-4o-mini
    "gpt-4o": {"input": 2.50, "output": 10.00},  # GPT-4o
    "default": {"input": 0.50, "output": 1.50}
}


@dataclass
class SpanData:
    """In-memory span data before persistence."""
    id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    error_message: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    input_preview: Optional[str] = None
    output_preview: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceData:
    """In-memory trace data before persistence."""
    id: str
    name: str
    user_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    error_message: Optional[str] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    spans: List[SpanData] = field(default_factory=list)


class TracingService:
    """
    Service for tracing LLM operations and persisting to database.
    Thread-safe singleton pattern.
    """
    
    _instance = None
    _lock = threading.Lock()
    
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
        
        # Current trace context (thread-local)
        self._trace_context = threading.local()
        
        # Recent traces cache (for quick access)
        self._recent_traces: deque = deque(maxlen=100)
        
        # Aggregated stats
        self._total_traces = 0
        self._total_llm_calls = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        
        self._initialized = True
    
    def _get_current_trace(self) -> Optional[TraceData]:
        """Get current trace from thread-local context."""
        return getattr(self._trace_context, 'current_trace', None)
    
    def _set_current_trace(self, trace: Optional[TraceData]):
        """Set current trace in thread-local context."""
        self._trace_context.current_trace = trace
    
    def _get_current_span(self) -> Optional[SpanData]:
        """Get current span from thread-local context."""
        return getattr(self._trace_context, 'current_span', None)
    
    def _set_current_span(self, span: Optional[SpanData]):
        """Set current span in thread-local context."""
        self._trace_context.current_span = span
    
    @contextmanager
    def trace(
        self,
        name: str,
        user_id: Optional[str] = None,
        input_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for creating a trace.
        
        Usage:
            with tracing_service.trace("rag_query", user_id="user123", input_summary="What is my spending?"):
                # ... perform operations
        """
        trace_data = TraceData(
            id=str(uuid.uuid4()),
            name=name,
            user_id=user_id,
            start_time=datetime.utcnow(),
            input_summary=input_summary[:500] if input_summary else None,
            metadata=metadata or {}
        )
        
        self._set_current_trace(trace_data)
        start_time = time.perf_counter()
        
        try:
            yield trace_data
            trace_data.status = "success"
        except Exception as e:
            trace_data.status = "error"
            trace_data.error_message = str(e)
            raise
        finally:
            trace_data.end_time = datetime.utcnow()
            trace_data.duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Add to recent traces
            self._recent_traces.append(trace_data)
            self._total_traces += 1
            
            # Persist to database
            self._persist_trace(trace_data)
            
            # Clear context
            self._set_current_trace(None)
            self._set_current_span(None)
    
    @contextmanager
    def span(
        self,
        name: str,
        span_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for creating a span within a trace.
        
        Usage:
            with tracing_service.span("retrieval", "retrieval"):
                # ... perform retrieval
        """
        current_trace = self._get_current_trace()
        parent_span = self._get_current_span()
        
        span_data = SpanData(
            id=str(uuid.uuid4()),
            trace_id=current_trace.id if current_trace else "orphan",
            parent_span_id=parent_span.id if parent_span else None,
            name=name,
            span_type=span_type,
            start_time=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self._set_current_span(span_data)
        start_time = time.perf_counter()
        
        try:
            yield span_data
            span_data.status = "success"
        except Exception as e:
            span_data.status = "error"
            span_data.error_message = str(e)
            raise
        finally:
            span_data.end_time = datetime.utcnow()
            span_data.duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Add to current trace
            if current_trace:
                current_trace.spans.append(span_data)
            
            # Update LLM stats
            if span_data.total_tokens:
                self._total_llm_calls += 1
                self._total_tokens += span_data.total_tokens
                if span_data.estimated_cost_usd:
                    self._total_cost += span_data.estimated_cost_usd
            
            # Restore parent span
            self._set_current_span(parent_span)
    
    def record_llm_call(
        self,
        model_name: str,
        provider: str,
        input_text: str,
        output_text: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ):
        """
        Record an LLM call on the current span.
        Call this within a span context to add LLM details.
        """
        current_span = self._get_current_span()
        if not current_span:
            return
        
        # Estimate tokens if not provided
        if input_tokens is None:
            input_tokens = len(input_text) // 4
        if output_tokens is None:
            output_tokens = len(output_text) // 4
        
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        cost_key = provider.lower()
        if "pro" in model_name.lower():
            cost_key = f"{provider.lower()}-pro"
        if "gpt-4o" in model_name.lower() and "mini" not in model_name.lower():
            cost_key = "gpt-4o"
        
        costs = TOKEN_COSTS.get(cost_key, TOKEN_COSTS["default"])
        estimated_cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
        
        # Update span
        current_span.model_name = model_name
        current_span.provider = provider
        current_span.input_tokens = input_tokens
        current_span.output_tokens = output_tokens
        current_span.total_tokens = total_tokens
        current_span.estimated_cost_usd = estimated_cost
        current_span.input_preview = input_text[:500] if input_text else None
        current_span.output_preview = output_text[:500] if output_text else None
    
    def set_output_summary(self, summary: str):
        """Set output summary on current trace."""
        current_trace = self._get_current_trace()
        if current_trace:
            current_trace.output_summary = summary[:500] if summary else None
    
    def _persist_trace(self, trace_data: TraceData):
        """Persist trace and spans to database."""
        try:
            from models.tracing import Trace, Span
            
            db: Session = SessionLocal()
            try:
                # Create trace record
                trace = Trace(
                    id=trace_data.id,
                    name=trace_data.name,
                    user_id=trace_data.user_id,
                    start_time=trace_data.start_time,
                    end_time=trace_data.end_time,
                    duration_ms=trace_data.duration_ms,
                    status=trace_data.status,
                    error_message=trace_data.error_message,
                    input_summary=trace_data.input_summary,
                    output_summary=trace_data.output_summary,
                    metadata=trace_data.metadata
                )
                db.add(trace)
                
                # Create span records
                for span_data in trace_data.spans:
                    span = Span(
                        id=span_data.id,
                        trace_id=trace_data.id,
                        parent_span_id=span_data.parent_span_id,
                        name=span_data.name,
                        span_type=span_data.span_type,
                        start_time=span_data.start_time,
                        end_time=span_data.end_time,
                        duration_ms=span_data.duration_ms,
                        status=span_data.status,
                        error_message=span_data.error_message,
                        model_name=span_data.model_name,
                        provider=span_data.provider,
                        input_tokens=span_data.input_tokens,
                        output_tokens=span_data.output_tokens,
                        total_tokens=span_data.total_tokens,
                        estimated_cost_usd=span_data.estimated_cost_usd,
                        input_preview=span_data.input_preview,
                        output_preview=span_data.output_preview,
                        metadata=span_data.metadata
                    )
                    db.add(span)
                
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"Failed to persist trace: {e}")
    
    def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent traces from memory cache."""
        traces = list(self._recent_traces)[-limit:]
        return [
            {
                "id": t.id,
                "name": t.name,
                "user_id": t.user_id,
                "start_time": t.start_time.isoformat(),
                "duration_ms": t.duration_ms,
                "status": t.status,
                "input_summary": t.input_summary,
                "output_summary": t.output_summary[:100] if t.output_summary else None,
                "span_count": len(t.spans),
                "llm_spans": sum(1 for s in t.spans if s.model_name),
                "total_tokens": sum(s.total_tokens or 0 for s in t.spans),
                "total_cost": sum(s.estimated_cost_usd or 0 for s in t.spans)
            }
            for t in reversed(traces)
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated tracing statistics."""
        return {
            "total_traces": self._total_traces,
            "total_llm_calls": self._total_llm_calls,
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 6),
            "recent_trace_count": len(self._recent_traces)
        }
    
    def get_llm_calls_summary(self) -> Dict[str, Any]:
        """Get summary of LLM calls from recent traces."""
        llm_spans = []
        for trace in self._recent_traces:
            for span in trace.spans:
                if span.model_name:
                    llm_spans.append(span)
        
        # Group by provider
        by_provider = {}
        for span in llm_spans:
            provider = span.provider or "unknown"
            if provider not in by_provider:
                by_provider[provider] = {
                    "call_count": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "avg_duration_ms": 0.0
                }
            by_provider[provider]["call_count"] += 1
            by_provider[provider]["total_tokens"] += span.total_tokens or 0
            by_provider[provider]["total_cost"] += span.estimated_cost_usd or 0
        
        # Calculate averages
        for provider in by_provider:
            durations = [s.duration_ms for s in llm_spans if s.provider == provider and s.duration_ms]
            if durations:
                by_provider[provider]["avg_duration_ms"] = round(sum(durations) / len(durations), 2)
        
        return {
            "total_calls": len(llm_spans),
            "by_provider": by_provider
        }


# Global instance
tracing_service = TracingService()
