"""
Agents router - API endpoints for AI agents.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel

from database import get_db
from models import User
from services.agents.orchestrator import agent_orchestrator


router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    """Request body for running an agent."""
    context: Dict[str, Any] = {}


@router.get("")
async def list_agents() -> Dict[str, Any]:
    """Get list of available AI agents."""
    agents = agent_orchestrator.get_available_agents()
    return {
        "agents": agents,
        "count": len(agents)
    }


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: str,
    request: AgentRunRequest = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Run a specific agent.
    
    Args:
        agent_id: ID of agent to run (budget, subscription, savings, anomaly, forecast, goals)
        request: Optional context for the agent
    """
    # Get default user
    user = db.query(User).first()
    if not user:
        return {
            "status": "error",
            "error": "No user found. Please upload bank statements first."
        }
    
    context = request.context if request else {}
    result = await agent_orchestrator.run_agent(agent_id, str(user.id), context)
    
    return result


@router.get("/insights")
async def get_all_insights(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Run all agents and get aggregated insights.
    This is the main endpoint for comprehensive financial analysis.
    """
    # Get default user
    user = db.query(User).first()
    if not user:
        return {
            "status": "error",
            "error": "No user found. Please upload bank statements first."
        }
    
    results = await agent_orchestrator.run_all_agents(str(user.id))
    
    return results


@router.post("/run-all")
async def run_all_agents(
    request: AgentRunRequest = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Run all agents with optional context.
    Same as /insights but accepts POST with context.
    """
    user = db.query(User).first()
    if not user:
        return {
            "status": "error",
            "error": "No user found. Please upload bank statements first."
        }
    
    context = request.context if request else {}
    results = await agent_orchestrator.run_all_agents(str(user.id), context)
    
    return results
