"""Cached insights model for storing AI-generated insights."""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from database import Base


class CachedInsights(Base):
    """Model for caching AI-generated insights to reduce LLM API calls."""
    __tablename__ = "cached_insights"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    insights_json = Column(Text, nullable=False)  # JSON string of insights
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="cached_insights")

    def __repr__(self):
        return f"<CachedInsights(user_id={self.user_id}, updated_at={self.updated_at})>"
