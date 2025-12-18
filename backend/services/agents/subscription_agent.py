"""
Subscription Auditor Agent - Detects and analyzes recurring subscriptions.
"""

from typing import Dict, Any, List

from .base import BaseFinanceAgent, AgentResult
from .tools import agent_tools


class SubscriptionAuditorAgent(BaseFinanceAgent):
    """Agent that audits subscriptions and identifies savings opportunities."""
    
    agent_id = "subscription"
    agent_name = "Subscription Auditor"
    description = "Detects recurring charges and identifies potentially unused or duplicate subscriptions"
    icon = "🔄"
    
    # Known subscription categories for better detection
    STREAMING_SERVICES = ["netflix", "hulu", "disney", "hbo", "spotify", "apple music", "youtube"]
    SIMILAR_SERVICES = {
        "streaming_video": ["netflix", "hulu", "disney", "hbo max", "amazon prime video", "peacock"],
        "streaming_music": ["spotify", "apple music", "youtube music", "tidal", "pandora"],
        "cloud_storage": ["icloud", "google one", "dropbox", "onedrive"],
        "news": ["nytimes", "wsj", "washington post", "substack"]
    }
    
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """Analyze subscriptions and find savings opportunities."""
        try:
            # Get subscription data
            subscriptions = await agent_tools.get_subscriptions(user_id)
            
            if not subscriptions:
                return AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status="no_data",
                    summary="No recurring subscriptions detected.",
                    insights=[{
                        "type": "info",
                        "title": "No Subscriptions Found",
                        "detail": "Either you have no subscriptions or more transaction data is needed."
                    }],
                    recommendations=["Upload more months of statements for better subscription detection."],
                    data=None,
                    llm_analysis=None
                )
            
            # Calculate totals
            monthly_total = sum(s.get("amount", 0) for s in subscriptions)
            annual_total = monthly_total * 12
            
            insights = []
            recommendations = []
            
            # Add summary insight
            insights.append({
                "type": "metric",
                "title": "Subscription Summary",
                "detail": f"{len(subscriptions)} recurring charges totaling ${monthly_total:,.2f}/month (${annual_total:,.2f}/year)"
            })
            
            # Find potentially duplicate/similar services
            found_services = {}
            for sub in subscriptions:
                merchant = sub.get("merchant", "").lower()
                for category, services in self.SIMILAR_SERVICES.items():
                    for service in services:
                        if service in merchant:
                            if category not in found_services:
                                found_services[category] = []
                            found_services[category].append({
                                "merchant": sub.get("merchant"),
                                "amount": sub.get("amount")
                            })
                            break
            
            # Flag duplicate categories
            for category, services in found_services.items():
                if len(services) > 1:
                    total_cost = sum(s["amount"] for s in services)
                    service_names = ", ".join(s["merchant"] for s in services)
                    insights.append({
                        "type": "warning",
                        "title": f"Multiple {category.replace('_', ' ').title()} Services",
                        "detail": f"You have {len(services)} services: {service_names}"
                    })
            
            # Identify high-cost subscriptions
            high_cost = [s for s in subscriptions if s.get("amount", 0) > 50]
            for sub in high_cost[:3]:
                insights.append({
                    "type": "info",
                    "title": f"High-Cost: {sub.get('merchant')}",
                    "detail": f"${sub.get('amount', 0):,.2f}/month (${sub.get('amount', 0) * 12:,.2f}/year)"
                })
            
            # Sort subscriptions by amount for display
            sorted_subs = sorted(subscriptions, key=lambda x: x.get("amount", 0), reverse=True)
            
            # Build data for LLM
            analysis_data = {
                "subscription_count": len(subscriptions),
                "monthly_total": monthly_total,
                "annual_total": annual_total,
                "subscriptions": sorted_subs[:10],
                "duplicate_categories": list(found_services.keys())
            }
            
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(
                analysis_data,
                "Identify unused subscriptions and consolidation opportunities for streaming, music, and cloud services"
            )
            
            # Get smart recommendations from LLM
            smart_recs = await self._generate_smart_recommendations(insights, analysis_data)
            if smart_recs:
                recommendations = smart_recs
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="success",
                summary=f"Found {len(subscriptions)} subscriptions totaling ${monthly_total:,.2f}/month",
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
                summary=f"Error analyzing subscriptions: {str(e)}",
                insights=[],
                recommendations=[],
                data=None,
                llm_analysis=None
            )

