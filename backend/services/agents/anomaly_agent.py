"""
Anomaly Detector Agent - Flags suspicious transactions.
"""

from typing import Dict, Any, List

from .base import BaseFinanceAgent, AgentResult
from .tools import agent_tools


class AnomalyDetectorAgent(BaseFinanceAgent):
    """Agent that detects unusual transactions and potential fraud."""
    
    agent_id = "anomaly"
    agent_name = "Anomaly Detector"
    description = "Flags unusual transactions based on amount, merchant, and spending patterns"
    icon = "🚨"
    
    STDDEV_THRESHOLD = 2.0
    LARGE_TRANSACTION = 500
    
    async def analyze(self, user_id: str, context: Dict[str, Any] = None) -> AgentResult:
        """Detect anomalies in transactions."""
        try:
            stats = await agent_tools.get_transaction_stats(user_id)
            transactions = stats.get("transactions", [])
            avg = stats.get("avg", 0)
            stddev = stats.get("stddev", 0)
            
            if not transactions:
                return AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status="no_data",
                    summary="No transaction data available for anomaly detection.",
                    insights=[],
                    recommendations=["Upload bank statements to enable anomaly detection."],
                    data=None,
                    llm_analysis=None
                )
            
            insights = []
            anomalies = []
            
            # Detect statistical anomalies
            if stddev > 0:
                threshold = avg + (self.STDDEV_THRESHOLD * stddev)
                for trans in transactions:
                    amount = trans.get("amount", 0)
                    if amount > threshold:
                        anomalies.append({
                            "type": "statistical",
                            "transaction": trans,
                            "reason": f"Amount ${amount:,.2f} is {((amount - avg) / stddev):.1f}x std dev above average",
                            "severity": "high" if amount > threshold * 1.5 else "medium"
                        })
                    elif amount > self.LARGE_TRANSACTION:
                        anomalies.append({
                            "type": "large_amount",
                            "transaction": trans,
                            "reason": f"Large transaction: ${amount:,.2f}",
                            "severity": "medium"
                        })
            
            # First-time merchants
            merchant_counts = {}
            for trans in transactions:
                merchant = trans.get("merchant", "Unknown")
                merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1
            
            for trans in transactions:
                merchant = trans.get("merchant", "Unknown")
                amount = trans.get("amount", 0)
                if merchant_counts.get(merchant, 0) == 1 and amount > 200:
                    if not any(a["transaction"] == trans for a in anomalies):
                        anomalies.append({
                            "type": "new_merchant",
                            "transaction": trans,
                            "reason": f"First-time merchant with ${amount:,.2f} charge",
                            "severity": "low"
                        })
            
            # Sort by severity
            severity_order = {"high": 0, "medium": 1, "low": 2}
            anomalies.sort(key=lambda x: severity_order.get(x["severity"], 3))
            
            high_count = len([a for a in anomalies if a["severity"] == "high"])
            medium_count = len([a for a in anomalies if a["severity"] == "medium"])
            
            if anomalies:
                insights.append({
                    "type": "metric",
                    "title": "Anomalies Detected",
                    "detail": f"{len(anomalies)} unusual transactions ({high_count} high, {medium_count} medium severity)"
                })
                for anomaly in anomalies[:3]:
                    trans = anomaly["transaction"]
                    insights.append({
                        "type": "warning" if anomaly["severity"] == "high" else "info",
                        "title": f"{anomaly['severity'].title()}: {trans.get('merchant', 'Unknown')}",
                        "detail": f"${trans.get('amount', 0):,.2f} on {trans.get('date', 'N/A')} - {anomaly['reason']}"
                    })
            else:
                insights.append({
                    "type": "info",
                    "title": "No Anomalies Found",
                    "detail": "All transactions appear within normal patterns"
                })
            
            insights.append({
                "type": "metric",
                "title": "Transaction Stats",
                "detail": f"Average: ${avg:,.2f}, Std Dev: ${stddev:,.2f}"
            })
            
            # Build data for LLM
            analysis_data = {
                "total_analyzed": len(transactions),
                "anomaly_count": len(anomalies),
                "high_severity": high_count,
                "medium_severity": medium_count,
                "average_amount": avg,
                "stddev": stddev,
                "anomalies": anomalies[:10]
            }
            
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(
                analysis_data,
                "Analyze flagged transactions for potential fraud or unusual spending patterns"
            )
            
            # Get smart recommendations
            recommendations = await self._generate_smart_recommendations(insights, analysis_data)
            if not recommendations and anomalies:
                recommendations = [f"Review {high_count + medium_count} flagged transactions for accuracy"]
            
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status="success",
                summary=f"Analyzed {len(transactions)} transactions, found {len(anomalies)} anomalies",
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
                summary=f"Error detecting anomalies: {str(e)}",
                insights=[],
                recommendations=[],
                data=None,
                llm_analysis=None
            )

