"""
Database models for LLM tracing and observability.
Stores traces, spans, and LLM call details for historical analysis.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Trace(Base):
    """Top-level operation trace (e.g., a RAG query)."""
    __tablename__ = "traces"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)  # e.g., "rag_query", "chat"
    user_id = Column(String(50), nullable=True)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default="running")  # running, success, error
    error_message = Column(Text, nullable=True)
    
    # Input/Output summary
    input_summary = Column(Text, nullable=True)  # e.g., the question
    output_summary = Column(Text, nullable=True)  # e.g., answer preview
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary[:200] if self.output_summary else None,
            "metadata": self.metadata,
            "span_count": len(self.spans) if self.spans else 0
        }


class Span(Base):
    """Individual step within a trace."""
    __tablename__ = "spans"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    trace_id = Column(String(36), ForeignKey("traces.id"), nullable=False)
    parent_span_id = Column(String(36), nullable=True)
    
    name = Column(String(100), nullable=False)  # e.g., "retrieval", "llm_generation"
    span_type = Column(String(50), nullable=False)  # "retrieval", "llm", "embedding", "processing"
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default="running")
    error_message = Column(Text, nullable=True)
    
    # LLM-specific fields
    model_name = Column(String(100), nullable=True)
    provider = Column(String(50), nullable=True)  # "openai", "gemini"
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    
    # Input/Output (for debugging)
    input_preview = Column(Text, nullable=True)  # First 500 chars
    output_preview = Column(Text, nullable=True)  # First 500 chars
    
    # Additional data
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    trace = relationship("Trace", back_populates="spans")
    
    def to_dict(self):
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_type": self.span_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "model_name": self.model_name,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "input_preview": self.input_preview,
            "output_preview": self.output_preview,
            "metadata": self.metadata
        }


class EvaluationRun(Base):
    """Record of an evaluation suite run."""
    __tablename__ = "evaluation_runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_name = Column(String(100), nullable=True)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    
    # Results
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    
    # Aggregate scores
    avg_faithfulness = Column(Float, nullable=True)
    avg_relevancy = Column(Float, nullable=True)
    avg_precision = Column(Float, nullable=True)
    avg_overall = Column(Float, nullable=True)
    
    # Detailed results
    results_json = Column(JSON, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "run_name": self.run_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "avg_faithfulness": self.avg_faithfulness,
            "avg_relevancy": self.avg_relevancy,
            "avg_precision": self.avg_precision,
            "avg_overall": self.avg_overall,
            "results_json": self.results_json
        }
