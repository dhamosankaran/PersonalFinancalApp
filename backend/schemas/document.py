"""Document schemas."""

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class UploadedDocumentResponse(BaseModel):
    """Schema for uploaded document response."""
    
    id: UUID
    user_id: UUID
    filename: str
    file_type: str
    processed: bool
    transaction_count: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
