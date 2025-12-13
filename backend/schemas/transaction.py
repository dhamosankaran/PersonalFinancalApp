"""Transaction schemas for request/response validation."""

from pydantic import BaseModel, Field
from datetime import date, datetime
from uuid import UUID
from typing import Optional
from decimal import Decimal


class CategoryCreate(BaseModel):
    """Schema for creating a category."""
    
    name: str = Field(..., max_length=100)
    parent_id: Optional[UUID] = None
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class CategoryResponse(BaseModel):
    """Schema for category response."""
    
    id: UUID
    name: str
    parent_id: Optional[UUID]
    color: Optional[str]
    icon: Optional[str]
    
    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    """Schema for creating a transaction."""
    
    transaction_date: date
    merchant: Optional[str] = Field(None, max_length=255)
    amount: Decimal = Field(..., decimal_places=2)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    source_file: Optional[str] = None


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""
    
    transaction_date: Optional[date] = None
    merchant: Optional[str] = Field(None, max_length=255)
    amount: Optional[Decimal] = Field(None, decimal_places=2)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    
    id: UUID
    user_id: UUID
    transaction_date: date
    merchant: Optional[str]
    amount: Decimal
    category: Optional[str]
    subcategory: Optional[str]
    description: Optional[str]
    source_file: Optional[str]
    is_recurring: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
