"""
Financial Goals Agent - Tracks savings goals.
"""

from typing import Dict, Any, List

from .base import BaseFinanceAgent, AgentResult
from .tools import agent_tools


class FinancialGoalsAgent(BaseFinanceAgent):
    """Agent that tracks savings goals and provides progress updates."""
    
    agent_id = "goals"
    agent_name = "Financial Goals"
    description = "Analyzes spending to determine savings capacity and tracks progress toward goals"
    icon = "🎯"
    
    DEFAULT_GOALS = [
        {"name": "Emergency Fund", "target": 10000, "priority": "high"},
        {"name": "Vacation Fund", "target": 3000, "priority": "medium"},
        {"name": "Down Payment", "target": 50000, "priority": "long-term"},
    ]
    
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """Analyze savings capacity and goal progress."""
        try:
            monthly_data = await agent_tools.get_monthly_spending(user_id, months=6)
            
            if not monthly_data.get("data"):
                return AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status="no_data",
                    summary="No spending data available for goals analysis.",
                    insights=[],
                    recommendations=["Upload bank statements to analyze savings potential."],
                    data=None,
                    llm_analysis=None
                )
            
            insights = []
            
            avg_monthly_spend = monthly_data.get("average", 0)
            potential_savings = monthly_data.get("potential_savings", 0)
            estimated_income = avg_monthly_spend / 0.7 if avg_monthly_spend > 0 else 0
            
            monthly_savings_capacity = 0
            current_savings_rate = 0
            if estimated_income > 0:
                monthly_savings_capacity = estimated_income - avg_monthly_spend
                current_savings_rate = (monthly_savings_capacity / estimated_income) * 100
            
            insights.append({
                "type": "metric",
                "title": "Monthly Savings Capacity",
                "detail": f"${monthly_savings_capacity:,.2f}/month (~{current_savings_rate:.0f}% of estimated income)"
            })
            
            user_goals = context.get("goals", self.DEFAULT_GOALS) if context else self.DEFAULT_GOALS
            goal_analysis = []
            
            for goal in user_goals:
                target = goal.get("target", 0)
                name = goal.get("name", "Unknown Goal")
                
                if monthly_savings_capacity > 0:
                    months_to_goal = target / monthly_savings_capacity
                    years_to_goal = months_to_goal / 12
                    
                    goal_info = {
                        "name": name,
                        "target": target,
                        "months_to_goal": months_to_goal,
                        "years_to_goal": years_to_goal,
                        "monthly_needed": target / 12
                    }
                    goal_analysis.append(goal_info)
                    
                    if months_to_goal <= 12:
                        insights.append({
                            "type": "info",
                            "title": f"Goal: {name}",
                            "detail": f"Achievable in {months_to_goal:.0f} months at current rate"
                        })
                    elif months_to_goal <= 36:
                        insights.append({
                            "type": "info",
                            "title": f"Goal: {name}",
                            "detail": f"Target: ${target:,.0f} - {years_to_goal:.1f} years at current rate"
                        })
            
            if current_savings_rate < 10:
                insights.append({
                    "type": "warning",
                    "title": "Low Savings Rate",
                    "detail": f"Currently saving ~{current_savings_rate:.0f}% (target: 20%)"
                })
            elif current_savings_rate >= 20:
                insights.append({
                    "type": "info",
                    "title": "Healthy Savings Rate",
                    "detail": f"Saving ~{current_savings_rate:.0f}% of estimated income"
                })
            
            analysis_data = {
                "estimated_income": estimated_income,
                "average_spending": avg_monthly_spend,
                "savings_capacity": monthly_savings_capacity,
                "savings_rate": current_savings_rate,
                "potential_additional": potential_savings,
                "goals": goal_analysis
            }
            
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(
                analysis_data,
                "Provide personalized advice on achieving financial goals based on savings capacity"
            )
            
            # Get smart recommendations
            recommendations = await self._generate_smart_recommendations(insights, analysis_data)
            if not recommendations:
                if goal_analysis:
                    quickest = min(goal_analysis, key=lambda x: x["months_to_goal"])
                    recommendations = [f"Focus on \"{quickest['name']}\" first - achievable in {quickest['months_to_goal']:.0f} months"]
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="success",
                summary=f"Savings capacity: ${monthly_savings_capacity:,.2f}/month ({current_savings_rate:.0f}% rate)",
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
                summary=f"Error analyzing goals: {str(e)}",
                insights=[],
                recommendations=[],
                data=None,
                llm_analysis=None
            )

