"""Analytics schemas."""

from pydantic import BaseModel
from typing import List, Dict, Any
from decimal import Decimal
from datetime import date


class MonthlySpendResponse(BaseModel):
    """Schema for monthly spend analysis."""
    
    data: List[Dict[str, Any]]  # [{"month": "2023-01", "amount": 1234.56}, ...]
    total: Decimal
    average: Decimal
    previous_total: Decimal = Decimal("0")  # Previous period total for comparison
    period_change: float = 0.0  # Percentage change from previous period
    potential_savings: Decimal = Decimal("0")  # Estimated potential savings


class CategoryBreakdownResponse(BaseModel):
    """Schema for category breakdown."""
    
    data: List[Dict[str, Any]]  # [{"category": "Food", "amount": 500.00, "percentage": 25}, ...]
    total: Decimal


class MerchantAnalysisResponse(BaseModel):
    """Schema for merchant analysis."""
    
    top_merchants: List[Dict[str, Any]]  # [{"merchant": "Amazon", "amount": 300, "count": 15}, ...]
    total_merchants: int


class RecurringSubscription(BaseModel):
    """Schema for recurring subscription."""
    
    merchant: str
    amount: Decimal
    frequency: str  # 'monthly', 'yearly', etc.
    last_charge: date
    next_expected: date
    total_paid: Decimal
