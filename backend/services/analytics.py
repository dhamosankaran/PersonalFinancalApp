"""
Analytics service using DuckDB for fast analytical queries.
"""

import duckdb
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os

from config import settings


class AnalyticsService:
    """Service for analytical queries using DuckDB."""
    
    def __init__(self):
        """Initialize the analytics service."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(settings.duckdb_path), exist_ok=True)
        
        # Connect to DuckDB
        self.conn = duckdb.connect(settings.duckdb_path)
    
    async def sync_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        """
        Sync transactions to DuckDB for analytics.
        
        Args:
            transactions: List of transactions from database
        """
        # Create table if not exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                transaction_date DATE,
                merchant VARCHAR,
                amount DECIMAL(10, 2),
                category VARCHAR,
                subcategory VARCHAR,
                description TEXT,
                is_recurring BOOLEAN,
                created_at TIMESTAMP
            )
        """)
        
        # Clear existing data before full sync (prevents duplicates)
        self.conn.execute("DELETE FROM transactions")
        
        # Insert transactions
        if transactions:
            # Convert to format DuckDB expects
            records = []
            for trans in transactions:
                records.append((
                    str(trans.get('id', '')),
                    str(trans.get('user_id', '')),
                    trans.get('transaction_date'),
                    trans.get('merchant', ''),
                    float(trans.get('amount', 0)),
                    trans.get('category', ''),
                    trans.get('subcategory', ''),
                    trans.get('description', ''),
                    trans.get('is_recurring', False),
                    trans.get('created_at', datetime.now())
                ))
            
            # Use INSERT OR REPLACE for upsert behavior
            self.conn.executemany("""
                INSERT OR REPLACE INTO transactions 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
    
    async def get_monthly_spend(self, user_id: str, months: int = 12) -> Dict[str, Any]:
        """
        Get monthly spending breakdown.
        
        Args:
            user_id: User ID
            months: Number of months to include
            
        Returns:
            Monthly spend data with period change and potential savings
        """
        # Current period query - using DuckDB's proper interval syntax
        query = f"""
            SELECT 
                strftime(transaction_date, '%Y-%m') as month,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE user_id = ?
                AND transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
            GROUP BY month
            ORDER BY month DESC
        """
        
        try:
            result = self.conn.execute(query, [user_id]).fetchall()
        except Exception as e:
            print(f"Error in get_monthly_spend query: {e}")
            result = []
        
        data = [
            {
                "month": row[0],
                "amount": float(row[1]),
                "count": row[2]
            }
            for row in result
        ]
        
        total = sum(d['amount'] for d in data)
        average = total / len(data) if data else 0
        
        # Calculate month-over-month change (more meaningful than period blocks)
        # Compare most recent complete month vs the month before it
        previous_total = 0.0
        period_change = 0.0
        comparison_type = "month"  # Indicates this is month-over-month
        
        # Data is sorted newest first, so:
        # data[0] = most recent month (may be incomplete)
        # data[1] = previous complete month
        # data[2] = month before that
        if len(data) >= 3:
            # Skip current (potentially incomplete) month, compare last 2 complete months
            current_month = data[1]['amount']  # Last complete month
            previous_month = data[2]['amount']  # Month before that
            previous_total = previous_month
            
            if previous_month > 0:
                period_change = ((current_month - previous_month) / previous_month) * 100
        elif len(data) >= 2:
            # If only 2 months, compare them directly
            current_month = data[0]['amount']
            previous_month = data[1]['amount']
            previous_total = previous_month
            
            if previous_month > 0:
                period_change = ((current_month - previous_month) / previous_month) * 100
        
        # Calculate potential savings based on category benchmarks
        # Same logic as Savings Optimizer Agent for consistency
        potential_savings = 0.0
        
        if total > 0:
            # Category benchmarks (% of total spending)
            benchmarks = {
                "Food & Dining": 10,
                "Entertainment": 5,
                "Shopping": 10,
                "Transportation": 15,
                "Groceries": 15,
                "Utilities": 10,
            }
            
            savings_query = f"""
                SELECT 
                    category,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE user_id = ?
                    AND transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
                    AND category IS NOT NULL
                GROUP BY category
            """
            try:
                category_results = self.conn.execute(savings_query, [user_id]).fetchall()
                for row in category_results:
                    cat_name = row[0]
                    cat_amount = float(row[1])
                    cat_pct = (cat_amount / total * 100) if total > 0 else 0
                    
                    if cat_name in benchmarks:
                        benchmark = benchmarks[cat_name]
                        # Flag if >50% over benchmark
                        if cat_pct > benchmark * 1.5:
                            potential_savings += cat_amount - (total * benchmark / 100)
            except Exception as e:
                print(f"Error in potential savings query: {e}")
        
        return {
            "data": data,
            "total": total,
            "average": average,
            "previous_total": previous_total,
            "period_change": round(period_change, 1),
            "comparison_type": comparison_type,  # "month" for month-over-month
            "potential_savings": round(potential_savings, 2)
        }
    
    async def get_category_breakdown(self, user_id: str, months: int = 12) -> Dict[str, Any]:
        """
        Get spending breakdown by category.
        
        Args:
            user_id: User ID
            months: Number of months to include
            
        Returns:
            Category breakdown data
        """
        query = f"""
            SELECT 
                COALESCE(category, 'Uncategorized') as category,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count,
                AVG(amount) as avg_amount
            FROM transactions
            WHERE user_id = ?
                AND transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
            GROUP BY category
            ORDER BY total_amount DESC
        """
        
        try:
            result = self.conn.execute(query, [user_id]).fetchall()
        except Exception as e:
            print(f"Error in get_category_breakdown query: {e}")
            result = []
        
        # Convert to float for consistent arithmetic
        total = float(sum(float(row[1]) for row in result)) if result else 0.0
        
        data = [
            {
                "category": row[0],
                "amount": float(row[1]),
                "count": row[2],
                "average": float(row[3]),
                "percentage": (float(row[1]) / total * 100) if total > 0 else 0
            }
            for row in result
        ]
        
        return {
            "data": data,
            "total": float(total) if total else 0.0
        }
    
    async def get_top_merchants(self, user_id: str, months: int = 12, limit: int = 10) -> Dict[str, Any]:
        """
        Get top merchants by spending.
        
        Args:
            user_id: User ID
            months: Number of months to include
            limit: Number of merchants to return
            
        Returns:
            Top merchants data
        """
        query = f"""
            SELECT 
                merchant,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count,
                AVG(amount) as avg_amount
            FROM transactions
            WHERE user_id = ?
                AND transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
                AND merchant IS NOT NULL
                AND merchant != ''
            GROUP BY merchant
            ORDER BY total_amount DESC
            LIMIT {limit}
        """
        
        try:
            result = self.conn.execute(query, [user_id]).fetchall()
        except Exception as e:
            print(f"Error in get_top_merchants query: {e}")
            result = []
        
        data = [
            {
                "merchant": row[0],
                "total_amount": float(row[1]),
                "transaction_count": row[2],
                "average_amount": float(row[3])
            }
            for row in result
        ]
        
        total_merchants = self.conn.execute("""
            SELECT COUNT(DISTINCT merchant)
            FROM transactions
            WHERE user_id = ? AND merchant IS NOT NULL AND merchant != ''
        """, [user_id]).fetchone()[0]
        
        return {
            "top_merchants": data,
            "total_merchants": total_merchants
        }
    
    async def detect_recurring_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Detect recurring subscriptions/charges.
        
        Args:
            user_id: User ID
            
        Returns:
            List of recurring subscriptions
        """
        query = """
            WITH merchant_frequency AS (
                SELECT 
                    merchant,
                    COUNT(*) as occurrence_count,
                    COUNT(DISTINCT strftime(transaction_date, '%Y-%m')) as month_count,
                    AVG(amount) as avg_amount,
                    STDDEV(amount) as stddev_amount,
                    MIN(transaction_date) as first_date,
                    MAX(transaction_date) as last_date
                FROM transactions
                WHERE user_id = ?
                    AND merchant IS NOT NULL
                    AND merchant != ''
                    AND transaction_date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY merchant
                HAVING month_count >= 3
            )
            SELECT *
            FROM merchant_frequency
            WHERE stddev_amount / avg_amount < 0.1  -- Low variance indicates recurring
                OR occurrence_count = month_count  -- One per month
            ORDER BY avg_amount DESC
        """
        
        result = self.conn.execute(query, [user_id]).fetchall()
        
        subscriptions = []
        for row in result:
            merchant, count, months, avg_amt, stddev, first, last = row
            
            subscriptions.append({
                "merchant": merchant,
                "amount": float(avg_amt),
                "frequency": "monthly" if count == months else "recurring",
                "occurrence_count": count,
                "month_count": months,
                "first_charge": str(first),
                "last_charge": str(last),
                "total_paid": float(avg_amt * count)
            })
        
        return subscriptions
    
    def close(self):
        """Close database connection."""
        self.conn.close()


# Global instance
analytics_service = AnalyticsService()
