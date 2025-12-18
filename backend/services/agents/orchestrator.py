"""
Agent Orchestrator - Coordinates multiple agents.
"""

from typing import Dict, Any, List, Optional
import asyncio

from .base import AgentResult
from .budget_agent import BudgetPlannerAgent
from .subscription_agent import SubscriptionAuditorAgent
from .savings_agent import SavingsOptimizerAgent
from .anomaly_agent import AnomalyDetectorAgent
from .forecast_agent import SpendingForecastAgent
from .goals_agent import FinancialGoalsAgent


class AgentOrchestrator:
    """Orchestrates execution of multiple finance agents."""
    
    def __init__(self):
        """Initialize all agents."""
        self.agents = {
            "budget": BudgetPlannerAgent(),
            "subscription": SubscriptionAuditorAgent(),
            "savings": SavingsOptimizerAgent(),
            "anomaly": AnomalyDetectorAgent(),
            "forecast": SpendingForecastAgent(),
            "goals": FinancialGoalsAgent(),
        }
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents with their info."""
        return [agent.get_info() for agent in self.agents.values()]
    
    async def run_agent(self, agent_id: str, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Run a single agent.
        
        Args:
            agent_id: ID of the agent to run
            user_id: User to analyze
            context: Additional context
            
        Returns:
            AgentResult from the agent
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return AgentResult(
                agent_id=agent_id,
                agent_name="Unknown",
                status="error",
                summary=f"Agent '{agent_id}' not found",
                insights=[],
                recommendations=[],
                data=None
            )
        
        return await agent.analyze(user_id, context)
    
    async def run_all_agents(self, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run all agents concurrently and aggregate results.
        
        Args:
            user_id: User to analyze
            context: Additional context
            
        Returns:
            Aggregated results from all agents
        """
        # Run all agents concurrently
        tasks = [
            agent.analyze(user_id, context)
            for agent in self.agents.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        agent_results = {}
        all_insights = []
        all_recommendations = []
        successful = 0
        
        for i, (agent_id, agent) in enumerate(self.agents.items()):
            result = results[i]
            
            if isinstance(result, Exception):
                agent_results[agent_id] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                agent_results[agent_id] = result
                if result.get("status") == "success":
                    successful += 1
                    # Prefix insights with agent name
                    for insight in result.get("insights", []):
                        insight["agent"] = agent.agent_name
                        all_insights.append(insight)
                    
                    for rec in result.get("recommendations", []):
                        all_recommendations.append({
                            "agent": agent.agent_name,
                            "recommendation": rec
                        })
        
        # Prioritize and deduplicate insights
        # Sort by type: warnings first, then metrics, then info
        type_order = {"warning": 0, "metric": 1, "info": 2}
        all_insights.sort(key=lambda x: type_order.get(x.get("type", "info"), 3))
        
        return {
            "summary": f"Ran {len(self.agents)} agents, {successful} successful",
            "agents": agent_results,
            "combined_insights": all_insights[:15],  # Top 15 insights
            "combined_recommendations": all_recommendations[:10],  # Top 10 recommendations
            "stats": {
                "total_agents": len(self.agents),
                "successful": successful,
                "total_insights": len(all_insights),
                "total_recommendations": len(all_recommendations)
            }
        }


# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()
