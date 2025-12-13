"""Uploaded document model."""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class UploadedDocument(Base):
    """Model for tracking uploaded documents."""
    
    __tablename__ = "uploaded_documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # 'pdf' or 'csv'
    processed = Column(Boolean, default=False, index=True)
    transaction_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    
    def __repr__(self) -> str:
        return f"<UploadedDocument(filename={self.filename}, processed={self.processed})>"
