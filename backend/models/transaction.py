"""Transaction and Category models."""

from sqlalchemy import Column, String, DateTime, Date, Numeric, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class Category(Base):
    """Category model for transaction categorization."""
    
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    icon = Column(String(50), nullable=True)  # Icon name
    
    # Self-referential relationship for parent/child
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    
    def __repr__(self) -> str:
        return f"<Category(name={self.name})>"


class Transaction(Base):
    """Transaction model for financial transactions."""
    
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    merchant = Column(String(255), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    subcategory = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    source_file = Column(String(255), nullable=True)
    is_recurring = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self) -> str:
        return f"<Transaction(date={self.transaction_date}, merchant={self.merchant}, amount={self.amount})>"
