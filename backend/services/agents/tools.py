"""
Agent tools - wrappers around analytics service for agent use.
"""

from typing import Dict, Any, List
import asyncio

from services.analytics import analytics_service


class AgentTools:
    """Tools available to finance agents."""
    
    @staticmethod
    async def get_monthly_spending(user_id: str, months: int = 12) -> Dict[str, Any]:
        """Get monthly spending data for analysis."""
        return await analytics_service.get_monthly_spend(user_id, months)
    
    @staticmethod
    async def get_category_breakdown(user_id: str, months: int = 12) -> Dict[str, Any]:
        """Get spending breakdown by category."""
        return await analytics_service.get_category_breakdown(user_id, months)
    
    @staticmethod
    async def get_subscriptions(user_id: str) -> List[Dict[str, Any]]:
        """Get detected recurring subscriptions."""
        return await analytics_service.detect_recurring_subscriptions(user_id)
    
    @staticmethod
    async def get_top_merchants(user_id: str, months: int = 12, limit: int = 20) -> Dict[str, Any]:
        """Get top merchants by spending."""
        return await analytics_service.get_top_merchants(user_id, months, limit)
    
    @staticmethod
    async def get_transaction_stats(user_id: str) -> Dict[str, Any]:
        """Get transaction statistics for anomaly detection."""
        try:
            # Get raw transaction data from DuckDB
            query = """
                SELECT 
                    amount,
                    merchant,
                    transaction_date,
                    category,
                    AVG(amount) OVER () as overall_avg,
                    STDDEV(amount) OVER () as overall_stddev
                FROM transactions
                WHERE user_id = ?
                ORDER BY transaction_date DESC
                LIMIT 500
            """
            result = analytics_service.conn.execute(query, [user_id]).fetchall()
            
            if not result:
                return {"transactions": [], "avg": 0, "stddev": 0}
            
            transactions = []
            avg = result[0][4] if result else 0
            stddev = result[0][5] if result else 0
            
            for row in result:
                transactions.append({
                    "amount": float(row[0]),
                    "merchant": row[1],
                    "date": str(row[2]),
                    "category": row[3]
                })
            
            return {
                "transactions": transactions,
                "avg": float(avg) if avg else 0,
                "stddev": float(stddev) if stddev else 0
            }
        except Exception as e:
            print(f"Error getting transaction stats: {e}")
            return {"transactions": [], "avg": 0, "stddev": 0}
    
    @staticmethod
    async def get_spending_by_month(user_id: str, months: int = 6) -> List[Dict[str, Any]]:
        """Get spending grouped by month for forecasting."""
        try:
            query = f"""
                SELECT 
                    strftime(transaction_date, '%Y-%m') as month,
                    SUM(amount) as total,
                    COUNT(*) as count,
                    AVG(amount) as avg_transaction
                FROM transactions
                WHERE user_id = ?
                    AND transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
                GROUP BY month
                ORDER BY month DESC
            """
            result = analytics_service.conn.execute(query, [user_id]).fetchall()
            
            return [
                {
                    "month": row[0],
                    "total": float(row[1]),
                    "count": row[2],
                    "avg_transaction": float(row[3])
                }
                for row in result
            ]
        except Exception as e:
            print(f"Error getting monthly spending: {e}")
            return []


# Global tools instance
agent_tools = AgentTools()
