"""
Savings Optimizer Agent - Identifies cost-cutting opportunities.
"""

from typing import Dict, Any, List

from .base import BaseFinanceAgent, AgentResult
from .tools import agent_tools


class SavingsOptimizerAgent(BaseFinanceAgent):
    """Agent that finds opportunities to reduce spending."""
    
    agent_id = "savings"
    agent_name = "Savings Optimizer"
    description = "Analyzes spending patterns and identifies opportunities to reduce expenses"
    icon = "💰"
    
    # Benchmark percentages for common categories
    SPENDING_BENCHMARKS = {
        "Food & Dining": 10,  # % of income
        "Entertainment": 5,
        "Shopping": 10,
        "Transportation": 15,
        "Groceries": 15,
        "Utilities": 10,
    }
    
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """Analyze spending and find savings opportunities."""
        try:
            # Get data - use 12 months to match Dashboard
            category_data = await agent_tools.get_category_breakdown(user_id, months=12)
            merchant_data = await agent_tools.get_top_merchants(user_id, months=12, limit=15)
            
            if not category_data.get("data"):
                return AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status="no_data",
                    summary="No spending data available for savings analysis.",
                    insights=[],
                    recommendations=["Upload bank statements to analyze savings opportunities."],
                    data=None,
                    llm_analysis=None
                )
            
            total_spend = category_data.get("total", 0)
            categories = category_data.get("data", [])
            merchants = merchant_data.get("top_merchants", [])
            
            insights = []
            savings_opportunities = []
            
            # Analyze each category against benchmarks
            for cat in categories:
                cat_name = cat.get("category", "")
                amount = cat.get("amount", 0)
                percentage = cat.get("percentage", 0)
                
                if cat_name in self.SPENDING_BENCHMARKS:
                    benchmark = self.SPENDING_BENCHMARKS[cat_name]
                    if percentage > benchmark * 1.5:
                        potential_savings = amount - (total_spend * benchmark / 100)
                        savings_opportunities.append({
                            "category": cat_name,
                            "current": amount,
                            "benchmark": total_spend * benchmark / 100,
                            "potential_savings": potential_savings,
                            "percentage_over": percentage - benchmark
                        })
            
            savings_opportunities.sort(key=lambda x: x["potential_savings"], reverse=True)
            total_potential = sum(s["potential_savings"] for s in savings_opportunities)
            
            if savings_opportunities:
                insights.append({
                    "type": "metric",
                    "title": "Total Potential Savings",
                    "detail": f"${total_potential:,.2f} identified across {len(savings_opportunities)} categories"
                })
                
                for opp in savings_opportunities[:3]:
                    insights.append({
                        "type": "warning",
                        "title": f"High Spending: {opp['category']}",
                        "detail": f"${opp['current']:,.2f} spent ({opp['percentage_over']:.1f}% over benchmark)"
                    })
            
            # Impulse merchants
            impulse_merchants = [m for m in merchants if m.get("transaction_count", 0) > 5 and m.get("average_amount", 0) < 20]
            if impulse_merchants:
                insights.append({
                    "type": "info",
                    "title": "Frequent Small Purchases",
                    "detail": f"{impulse_merchants[0].get('merchant')}: {impulse_merchants[0].get('transaction_count')} transactions"
                })
            
            monthly_avg = total_spend / 3
            insights.append({
                "type": "metric",
                "title": "Monthly Average",
                "detail": f"${monthly_avg:,.2f}/month over 3 months"
            })
            
            # Build data for LLM
            analysis_data = {
                "total_spend": total_spend,
                "monthly_average": monthly_avg,
                "potential_savings": total_potential,
                "opportunities": savings_opportunities[:5],
                "impulse_merchants": [m.get("merchant") for m in impulse_merchants[:3]]
            }
            
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(
                analysis_data,
                "Identify specific cost-cutting opportunities by comparing spending to category benchmarks"
            )
            
            # Get smart recommendations
            recommendations = await self._generate_smart_recommendations(insights, analysis_data)
            if not recommendations:
                recommendations = ["Your spending looks reasonable - keep tracking to maintain good habits!"]
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="success",
                summary=f"Identified ${total_potential:,.2f} in potential savings across {len(savings_opportunities)} categories",
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
                summary=f"Error analyzing savings: {str(e)}",
                insights=[],
                recommendations=[],
                data=None,
                llm_analysis=None
            )

