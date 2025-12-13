"""Chat schemas."""

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any


class ChatMessageCreate(BaseModel):
    """Schema for creating a chat message."""
    
    role: str  # 'user' or 'assistant'
    content: str
    retrieved_context: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    
    id: UUID
    user_id: UUID
    role: str
    content: str
    retrieved_context: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat query request."""
    
    query: str
    conversation_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    """Schema for chat response."""
    
    response: str
    sources: List[Dict[str, Any]]
    conversation_id: UUID
    model_info: Optional[Dict[str, Any]] = None  # Provider and model used

