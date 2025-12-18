"""
Spending Forecast Agent - Predicts future expenses.
"""

from typing import Dict, Any, List

from .base import BaseFinanceAgent, AgentResult
from .tools import agent_tools


class SpendingForecastAgent(BaseFinanceAgent):
    """Agent that predicts upcoming spending based on patterns."""
    
    agent_id = "forecast"
    agent_name = "Spending Forecast"
    description = "Predicts next month's expenses based on historical patterns and recurring items"
    icon = "📈"
    
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """Forecast next month's spending."""
        try:
            monthly_data = await agent_tools.get_spending_by_month(user_id, months=6)
            subscriptions = await agent_tools.get_subscriptions(user_id)
            
            if not monthly_data:
                return AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status="no_data",
                    summary="Insufficient data for spending forecast.",
                    insights=[],
                    recommendations=["Upload at least 3 months of statements for accurate forecasting."],
                    data=None,
                    llm_analysis=None
                )
            
            insights = []
            
            # Calculate average and trend
            totals = [m.get("total", 0) for m in monthly_data]
            avg_spend = sum(totals) / len(totals) if totals else 0
            
            if len(totals) >= 3:
                recent_avg = sum(totals[:3]) / 3
                older_avg = sum(totals[3:]) / len(totals[3:]) if len(totals) > 3 else recent_avg
                trend_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            else:
                trend_pct = 0
                recent_avg = avg_spend
            
            recurring_total = sum(s.get("amount", 0) for s in subscriptions)
            base_forecast = recent_avg * (1 + trend_pct / 100)
            forecast = max(base_forecast, recurring_total * 1.5)
            
            variance = sum((t - avg_spend) ** 2 for t in totals) / len(totals) if totals else 0
            stddev = variance ** 0.5
            confidence = "high" if stddev < avg_spend * 0.2 else "medium" if stddev < avg_spend * 0.4 else "low"
            
            insights.append({
                "type": "metric",
                "title": "Next Month Forecast",
                "detail": f"${forecast:,.2f} (Confidence: {confidence})"
            })
            
            insights.append({
                "type": "info",
                "title": "Historical Average",
                "detail": f"${avg_spend:,.2f}/month over {len(monthly_data)} months"
            })
            
            if trend_pct > 5:
                insights.append({
                    "type": "warning",
                    "title": "Spending Trend: Increasing",
                    "detail": f"↑ {trend_pct:.1f}% compared to earlier months"
                })
            elif trend_pct < -5:
                insights.append({
                    "type": "info",
                    "title": "Spending Trend: Decreasing",
                    "detail": f"↓ {abs(trend_pct):.1f}% compared to earlier months"
                })
            
            if recurring_total > 0:
                insights.append({
                    "type": "metric",
                    "title": "Fixed Recurring",
                    "detail": f"${recurring_total:,.2f}/month in subscriptions"
                })
            
            monthly_breakdown = [
                {"month": m.get("month"), "amount": m.get("total")}
                for m in monthly_data[:6]
            ]
            
            analysis_data = {
                "forecast": forecast,
                "confidence": confidence,
                "average_monthly": avg_spend,
                "trend_percent": trend_pct,
                "recurring_total": recurring_total,
                "historical": monthly_breakdown
            }
            
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(
                analysis_data,
                "Predict next month's spending and identify budget adjustments based on spending trends"
            )
            
            # Get smart recommendations
            recommendations = await self._generate_smart_recommendations(insights, analysis_data)
            if not recommendations:
                if trend_pct > 5:
                    recommendations = [f"Spending trending up - consider setting a budget of ${avg_spend:,.0f}"]
                else:
                    recommendations = ["Your spending is stable - continue monitoring"]
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="success",
                summary=f"Forecasted ${forecast:,.2f} for next month ({confidence} confidence)",
                insights=insights,
                recommendations=recommendations,
                data=analysis_data,
                llm_analysis=llm_analysis
            )
            
        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="error",
                summary=f"Error forecasting: {str(e)}",
                insights=[],
                recommendations=[],
                data=None,
                llm_analysis=None
            )

