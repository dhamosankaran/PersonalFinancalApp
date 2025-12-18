"""Routers package."""

from .upload import router as upload_router
from .transactions import router as transactions_router
from .chat import router as chat_router
from .analytics import router as analytics_router
from .settings import router as settings_router
from .metrics import router as metrics_router
from .evaluation import router as evaluation_router
from .agents import router as agents_router
from .tracing import router as tracing_router

__all__ = [
    "upload_router",
    "transactions_router",
    "chat_router",
    "analytics_router",
    "settings_router",
    "metrics_router",
    "evaluation_router",
    "agents_router",
    "tracing_router",
]
