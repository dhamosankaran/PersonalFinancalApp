"""
AI Agents package for automated financial analysis.
Implements 6 specialized agents using LangGraph.
"""

from .base import AgentState, BaseFinanceAgent
from .budget_agent import BudgetPlannerAgent
from .subscription_agent import SubscriptionAuditorAgent
from .savings_agent import SavingsOptimizerAgent
from .anomaly_agent import AnomalyDetectorAgent
from .forecast_agent import SpendingForecastAgent
from .goals_agent import FinancialGoalsAgent
from .orchestrator import AgentOrchestrator

__all__ = [
    "AgentState",
    "BaseFinanceAgent",
    "BudgetPlannerAgent",
    "SubscriptionAuditorAgent",
    "SavingsOptimizerAgent",
    "AnomalyDetectorAgent",
    "SpendingForecastAgent",
    "FinancialGoalsAgent",
    "AgentOrchestrator",
]
