"""Chat message model for conversation history."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class ChatMessage(Base):
    """Model for chat message history."""
    
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    retrieved_context = Column(JSON, nullable=True)  # Cross-database compatible
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_messages")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(role={self.role}, created_at={self.created_at})>"
