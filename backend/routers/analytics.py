"""Analytics router for dashboard data."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from database import get_db
from models import User, Transaction
from schemas import (
    MonthlySpendResponse,
    CategoryBreakdownResponse,
    MerchantAnalysisResponse,
    RecurringSubscription
)
from services import analytics_service, rag_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/monthly", response_model=MonthlySpendResponse)
async def get_monthly_spend(
    user_email: str = "default@example.com",
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db)
):
    """Get monthly spending breakdown."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Sync latest data
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    transactions_dict = [
        {
            'id': t.id,
            'user_id': t.user_id,
            'transaction_date': t.transaction_date,
            'merchant': t.merchant,
            'amount': t.amount,
            'category': t.category,
            'subcategory': t.subcategory,
            'description': t.description,
            'is_recurring': t.is_recurring,
            'created_at': t.created_at
        }
        for t in transactions
    ]
    await analytics_service.sync_transactions(transactions_dict)
    
    result = await analytics_service.get_monthly_spend(str(user.id), months)
    return result


@router.get("/category", response_model=CategoryBreakdownResponse)
async def get_category_breakdown(
    user_email: str = "default@example.com",
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db)
):
    """Get spending breakdown by category."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Sync latest data to DuckDB
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    transactions_dict = [
        {
            'id': t.id,
            'user_id': t.user_id,
            'transaction_date': t.transaction_date,
            'merchant': t.merchant,
            'amount': t.amount,
            'category': t.category,
            'subcategory': t.subcategory,
            'description': t.description,
            'is_recurring': t.is_recurring,
            'created_at': t.created_at
        }
        for t in transactions
    ]
    await analytics_service.sync_transactions(transactions_dict)
    
    result = await analytics_service.get_category_breakdown(str(user.id), months)
    return result


@router.get("/merchants", response_model=MerchantAnalysisResponse)
async def get_top_merchants(
    user_email: str = "default@example.com",
    months: int = Query(12, ge=1, le=36),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get top merchants by spending."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Sync latest data to DuckDB
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    transactions_dict = [
        {
            'id': t.id,
            'user_id': t.user_id,
            'transaction_date': t.transaction_date,
            'merchant': t.merchant,
            'amount': t.amount,
            'category': t.category,
            'subcategory': t.subcategory,
            'description': t.description,
            'is_recurring': t.is_recurring,
            'created_at': t.created_at
        }
        for t in transactions
    ]
    await analytics_service.sync_transactions(transactions_dict)
    
    result = await analytics_service.get_top_merchants(str(user.id), months, limit)
    return result


@router.get("/subscriptions", response_model=List[RecurringSubscription])
async def get_recurring_subscriptions(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Detect recurring subscriptions."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    subscriptions = await analytics_service.detect_recurring_subscriptions(str(user.id))
    
    # Convert to schema format
    result = []
    for sub in subscriptions:
        result.append(RecurringSubscription(
            merchant=sub['merchant'],
            amount=sub['amount'],
            frequency=sub['frequency'],
            last_charge=sub['last_charge'],
            next_expected=sub['last_charge'],  # Simplified - could calculate based on frequency
            total_paid=sub['total_paid']
        ))
    
    return result


@router.get("/insights")
async def get_insights(
    user_email: str = "default@example.com",
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get AI-generated financial insights.
    
    - Returns cached insights by default (fast, no LLM call)
    - Set force_refresh=true to regenerate insights using LLM (slower, costs API credits)
    
    Returns:
        Dictionary with insights, cache status, and last updated time
    """
    from models import CachedInsights
    import json
    from datetime import datetime
    
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for cached insights
    cached = db.query(CachedInsights).filter(CachedInsights.user_id == user.id).first()
    
    # Return cached if available and not forcing refresh
    if cached and not force_refresh:
        try:
            insights_data = json.loads(cached.insights_json)
            return {
                "insights": insights_data,
                "cached": True,
                "last_updated": cached.updated_at.isoformat() if cached.updated_at else None,
                "message": "Returning cached insights. Use force_refresh=true to regenerate."
            }
        except json.JSONDecodeError:
            # Cache is corrupted, regenerate
            pass
    
    # Generate fresh insights using LLM
    insights = await rag_service.generate_insights(str(user.id))
    
    # Cache the results
    insights_json = json.dumps(insights)
    
    if cached:
        cached.insights_json = insights_json
        cached.updated_at = datetime.utcnow()
    else:
        cached = CachedInsights(
            user_id=user.id,
            insights_json=insights_json
        )
        db.add(cached)
    
    db.commit()
    
    return {
        "insights": insights,
        "cached": False,
        "last_updated": datetime.utcnow().isoformat(),
        "message": "Fresh insights generated using AI."
    }


@router.post("/insights/refresh")
async def refresh_insights(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """
    Force refresh AI insights - makes a new LLM API call.
    Use this endpoint when you want to explicitly regenerate insights.
    """
    return await get_insights(user_email=user_email, force_refresh=True, db=db)


@router.delete("/insights/cache")
async def clear_insights_cache(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Clear cached insights for a user."""
    from models import CachedInsights
    
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    deleted = db.query(CachedInsights).filter(CachedInsights.user_id == user.id).delete()
    db.commit()
    
    return {"message": f"Cleared {deleted} cached insight(s)"}

