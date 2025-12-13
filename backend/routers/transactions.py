"""Transactions router for CRUD operations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from uuid import UUID

from database import get_db
from models import Transaction, User
from schemas import TransactionResponse, TransactionCreate, TransactionUpdate
from services import vector_store, analytics_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(
    user_email: str = "default@example.com",
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get transactions with optional filters."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    query = db.query(Transaction).filter(Transaction.user_id == user.id)
    
    if category:
        query = query.filter(Transaction.category == category)
    
    if merchant:
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    
    transactions = query.order_by(
        Transaction.transaction_date.desc()
    ).limit(limit).offset(offset).all()
    
    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Get a specific transaction."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction


@router.post("/", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Create a new transaction."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    db_transaction = Transaction(
        user_id=user.id,
        **transaction.dict()
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Add to vector store
    trans_dict = {
        'id': db_transaction.id,
        'transaction_date': db_transaction.transaction_date,
        'merchant': db_transaction.merchant,
        'amount': db_transaction.amount,
        'category': db_transaction.category,
        'subcategory': db_transaction.subcategory,
        'description': db_transaction.description
    }
    await vector_store.add_transaction(str(db_transaction.id), trans_dict, str(user.id))
    
    # Sync to analytics
    await analytics_service.sync_transactions([trans_dict])
    
    return db_transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    transaction_update: TransactionUpdate,
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Update a transaction."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    ).first()
    
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Update fields
    update_data = transaction_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)
    
    db.commit()
    db.refresh(db_transaction)
    
    # Update vector store (delete and re-add)
    await vector_store.delete_transaction(str(transaction_id))
    trans_dict = {
        'id': db_transaction.id,
        'transaction_date': db_transaction.transaction_date,
        'merchant': db_transaction.merchant,
        'amount': db_transaction.amount,
        'category': db_transaction.category,
        'subcategory': db_transaction.subcategory,
        'description': db_transaction.description
    }
    await vector_store.add_transaction(str(db_transaction.id), trans_dict, str(user.id))
    
    # Sync to analytics
    await analytics_service.sync_transactions([trans_dict])
    
    return db_transaction


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: UUID,
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Delete a transaction."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    ).first()
    
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Delete from vector store
    await vector_store.delete_transaction(str(transaction_id))
    
    # Delete from database
    db.delete(db_transaction)
    db.commit()
    
    return {"message": "Transaction deleted successfully"}
