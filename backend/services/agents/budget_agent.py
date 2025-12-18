"""
Budget Planning Agent - Creates and monitors monthly budgets.
"""

from typing import Dict, Any, List

from .base import BaseFinanceAgent, AgentResult
from .tools import agent_tools


class BudgetPlannerAgent(BaseFinanceAgent):
    """Agent that analyzes spending and suggests budget allocations."""
    
    agent_id = "budget"
    agent_name = "Budget Planner"
    description = "Analyzes spending patterns and recommends monthly budget allocations by category"
    icon = "📊"
    
    # Recommended budget percentages (50/30/20 rule adapted)
    BUDGET_GUIDELINES = {
        "needs": {
            "categories": ["Groceries", "Utilities", "Healthcare", "Transportation"],
            "target_pct": 50
        },
        "wants": {
            "categories": ["Food & Dining", "Entertainment", "Shopping", "Subscriptions"],
            "target_pct": 30
        },
        "savings": {
            "categories": ["Savings", "Investments"],
            "target_pct": 20
        }
    }
    
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """Analyze spending and generate budget recommendations."""
        try:
            # Get spending data
            monthly_data = await agent_tools.get_monthly_spending(user_id, months=3)
            category_data = await agent_tools.get_category_breakdown(user_id, months=3)
            
            if not category_data.get("data"):
                return AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status="no_data",
                    summary="No spending data available for budget analysis.",
                    insights=[],
                    recommendations=["Upload bank statements to enable budget planning."],
                    data=None,
                    llm_analysis=None
                )
            
            # Calculate current allocation
            total_spend = category_data.get("total", 0)
            categories = category_data.get("data", [])
            
            # Categorize spending into needs/wants
            needs_total = 0
            wants_total = 0
            
            for cat in categories:
                cat_name = cat.get("category", "")
                amount = cat.get("amount", 0)
                
                if cat_name in self.BUDGET_GUIDELINES["needs"]["categories"]:
                    needs_total += amount
                elif cat_name in self.BUDGET_GUIDELINES["wants"]["categories"]:
                    wants_total += amount
            
            # Calculate percentages
            needs_pct = (needs_total / total_spend * 100) if total_spend > 0 else 0
            wants_pct = (wants_total / total_spend * 100) if total_spend > 0 else 0
            other_pct = 100 - needs_pct - wants_pct
            
            # Generate insights
            insights = []
            recommendations = []
            
            # Analyze allocation
            if wants_pct > 40:
                insights.append({
                    "type": "warning",
                    "title": "High Discretionary Spending",
                    "detail": f"Wants spending is {wants_pct:.1f}% of budget (target: 30%)"
                })
                recommendations.append(f"Consider reducing discretionary spending by ${(wants_pct - 30) * total_spend / 100:.0f}/month")
            
            if needs_pct < 40:
                insights.append({
                    "type": "info", 
                    "title": "Low Essential Spending",
                    "detail": f"Essential spending is only {needs_pct:.1f}% - you may have room to save more"
                })
            
            # Top category analysis
            if categories:
                top_category = categories[0]
                insights.append({
                    "type": "info",
                    "title": f"Top Category: {top_category.get('category')}",
                    "detail": f"${top_category.get('amount', 0):,.2f} ({top_category.get('percentage', 0):.1f}% of spending)"
                })
            
            # Monthly trend
            avg_monthly = monthly_data.get("average", 0)
            if avg_monthly > 0:
                insights.append({
                    "type": "metric",
                    "title": "Average Monthly Spending",
                    "detail": f"${avg_monthly:,.2f}/month over the last 3 months"
                })
            
            # Build data for LLM
            analysis_data = {
                "total_spend": total_spend,
                "monthly_average": avg_monthly,
                "allocation": {
                    "needs": {"amount": needs_total, "percentage": needs_pct},
                    "wants": {"amount": wants_total, "percentage": wants_pct},
                    "other": {"percentage": other_pct}
                },
                "top_categories": categories[:5]
            }
            
            # Generate LLM-enhanced analysis
            llm_analysis = await self._generate_llm_analysis(
                analysis_data,
                "Analyze budget allocation using 50/30/20 rule (50% needs, 30% wants, 20% savings)"
            )
            
            # Get smart recommendations from LLM
            smart_recs = await self._generate_smart_recommendations(insights, analysis_data)
            if smart_recs:
                recommendations = smart_recs  # Replace with LLM recommendations
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="success",
                summary=f"Analyzed ${total_spend:,.2f} in spending across {len(categories)} categories. Needs: {needs_pct:.0f}%, Wants: {wants_pct:.0f}%",
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
                summary=f"Error analyzing budget: {str(e)}",
                insights=[],
                recommendations=[],
                data=None,
                llm_analysis=None
            )

