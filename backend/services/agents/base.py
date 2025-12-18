"""
Base agent classes and shared state management.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from abc import ABC, abstractmethod
import operator
import json

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class AgentState(TypedDict):
    """Shared state for all agents."""
    user_id: str
    messages: Annotated[List[BaseMessage], operator.add]
    context: Dict[str, Any]
    insights: List[Dict[str, Any]]
    current_agent: str
    completed_agents: List[str]


class AgentResult(TypedDict):
    """Result from an agent execution."""
    agent_id: str
    agent_name: str
    status: str  # "success", "error", "no_data"
    summary: str
    insights: List[Dict[str, Any]]
    recommendations: List[str]
    data: Optional[Dict[str, Any]]
    llm_analysis: Optional[str]  # LLM-generated analysis


class BaseFinanceAgent(ABC):
    """Base class for all finance agents."""
    
    agent_id: str = "base"
    agent_name: str = "Base Agent"
    description: str = "Base agent class"
    icon: str = "🤖"
    
    def __init__(self, llm=None):
        """Initialize the agent with optional LLM."""
        self._llm = llm
        self._llm_enabled = True  # Enable LLM by default
    
    @property
    def llm(self):
        """Get LLM from factory if not provided."""
        if not self._llm_enabled:
            return None
        if self._llm is None:
            try:
                from services.llm_factory import llm_factory
                self._llm = llm_factory.get_llm(temperature=0.3)
            except Exception as e:
                print(f"Failed to get LLM: {e}")
                return None
        return self._llm
    
    @abstractmethod
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Run the agent's analysis.
        
        Args:
            user_id: User to analyze
            context: Additional context data
            
        Returns:
            AgentResult with insights and recommendations
        """
        pass
    
    def _format_currency(self, amount: float) -> str:
        """Format amount as currency."""
        return f"${amount:,.2f}"
    
    def _format_percentage(self, value: float) -> str:
        """Format value as percentage."""
        return f"{value:.1f}%"
    
    async def _generate_llm_analysis(self, data: Dict[str, Any], agent_context: str) -> str:
        """
        Use LLM to generate a comprehensive analysis.
        
        Args:
            data: The analysis data from the agent
            agent_context: Context about what the agent analyzes
            
        Returns:
            LLM-generated analysis string
        """
        if not self.llm:
            return ""
        
        try:
            # Format data for LLM
            data_str = json.dumps(data, indent=2, default=str)
            
            prompt = f"""You are a personal finance advisor analyzing a user's financial data.

Agent: {self.agent_name}
Purpose: {agent_context}

Financial Data:
{data_str}

Based on this data, provide:
1. A brief 2-3 sentence summary of the key findings
2. 2-3 specific, actionable recommendations
3. Any potential concerns or areas to watch

Be concise, specific, and use actual numbers from the data. Speak directly to the user."""

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            print(f"LLM analysis failed for {self.agent_name}: {e}")
            return ""
    
    async def _generate_smart_recommendations(self, insights: List[Dict], data: Dict) -> List[str]:
        """
        Use LLM to generate smarter, personalized recommendations.
        
        Args:
            insights: List of insights from rules-based analysis
            data: Raw analysis data
            
        Returns:
            List of LLM-enhanced recommendations
        """
        if not self.llm:
            return []
        
        try:
            insights_str = "\n".join([f"- {i.get('title')}: {i.get('detail')}" for i in insights])
            data_str = json.dumps(data, indent=2, default=str)[:2000]  # Limit size
            
            prompt = f"""Based on these financial insights and data, generate 3 specific, actionable recommendations.

Insights:
{insights_str}

Data Summary:
{data_str}

Generate exactly 3 recommendations that are:
- Specific (mention actual amounts or categories)
- Actionable (things the user can do today)
- Prioritized (most impactful first)

Return only the recommendations, one per line, without numbering."""

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse recommendations from response
            recs = [r.strip() for r in response.content.strip().split('\n') if r.strip()]
            return recs[:3]  # Limit to 3
        except Exception as e:
            print(f"Smart recommendations failed: {e}")
            return []
    
    def get_info(self) -> Dict[str, str]:
        """Get agent information for display."""
        return {
            "id": self.agent_id,
            "name": self.agent_name,
            "description": self.description,
            "icon": self.icon
        }

