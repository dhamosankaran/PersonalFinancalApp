"""User schemas for request/response validation."""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    
    email: EmailStr


class UserResponse(BaseModel):
    """Schema for user response."""
    
    id: UUID
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True
