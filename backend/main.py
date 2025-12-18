"""
Personal Finance Planner API
FastAPI backend with RAG capabilities for financial insights.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import init_db
from routers import upload_router, transactions_router, chat_router, analytics_router, settings_router, metrics_router, evaluation_router, agents_router, tracing_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    print("Initializing database...")
    init_db()
    print("Database initialized")
    
    # Initialize tracing tables
    print("Initializing tracing tables...")
    try:
        from models.tracing import Trace, Span, EvaluationRun
        from database import engine, Base
        # Create tables if they don't exist
        Trace.__table__.create(engine, checkfirst=True)
        Span.__table__.create(engine, checkfirst=True)
        EvaluationRun.__table__.create(engine, checkfirst=True)
        print("Tracing tables ready")
    except Exception as e:
        print(f"Warning: Could not initialize tracing tables: {e}")
    
    print("Initializing embedding service...")
    from services import embedding_service
    print("Embedding service ready")
    
    print("Initializing vector store...")
    from services import vector_store
    print("Vector store ready")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    from services import analytics_service
    analytics_service.close()
    print("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Personal Finance Planner API",
    description="Local-first financial planning with RAG and AI insights",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(transactions_router)
app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(settings_router)
app.include_router(metrics_router)
app.include_router(evaluation_router)
app.include_router(agents_router)
app.include_router(tracing_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Personal Finance Planner API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with metrics info."""
    from services import metrics_collector
    all_metrics = metrics_collector.get_all_metrics()
    
    return {
        "status": "healthy",
        "database": "connected",
        "vector_store": "ready",
        "metrics": {
            "uptime_seconds": all_metrics.get("summary", {}).get("uptime_seconds", 0),
            "total_requests": all_metrics.get("summary", {}).get("total_requests", 0)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
