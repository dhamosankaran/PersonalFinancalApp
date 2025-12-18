"""
RAG (Retrieval-Augmented Generation) service.
Combines vector search with LLM reasoning.
Instrumented with comprehensive metrics for observability.
"""

import time
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
import json

from config import settings
from .vector_store import vector_store
from .metrics import metrics_collector, Timer, MetricsCollector
from .llm_factory import llm_factory
from .tracing import tracing_service


class RAGService:
    """Service for RAG-based question answering."""
    
    def __init__(self):
        """Initialize the RAG service."""
        # LLM is now obtained dynamically from factory
        pass
    
    @property
    def llm(self):
        """Get the current LLM from factory."""
        return llm_factory.get_llm(temperature=0)
    
    def _is_temporal_query(self, question: str) -> bool:
        """Detect if query requires temporal ordering (recent, latest, last, etc.)."""
        temporal_keywords = [
            'recent', 'latest', 'last', 'newest', 'most recent',
            'yesterday', 'today', 'this week', 'this month',
            'past week', 'past month', 'previous'
        ]
        question_lower = question.lower()
        return any(kw in question_lower for kw in temporal_keywords)
    
    async def _get_recent_transactions_context(self, user_id: str, limit: int = 10) -> str:
        """Get context from database ordered by date for temporal queries."""
        from database import SessionLocal
        from models.transaction import Transaction
        from sqlalchemy import desc
        
        db = SessionLocal()
        try:
            query = db.query(Transaction).order_by(desc(Transaction.transaction_date))
            if user_id:
                query = query.filter(Transaction.user_id == user_id)
            txns = query.limit(limit).all()
            
            if not txns:
                return ""
            
            lines = ["MOST RECENT TRANSACTIONS (ordered by date, newest first):"]
            for t in txns:
                date_str = t.transaction_date.strftime('%Y-%m-%d') if t.transaction_date else 'Unknown'
                lines.append(f"- {date_str}: ${t.amount:.2f} at {t.merchant or 'Unknown'} ({t.category or 'Uncategorized'})")
            
            return "\n".join(lines)
        finally:
            db.close()
    
    async def query(
        self,
        question: str,
        user_id: str,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            user_id: User ID for filtering
            n_results: Number of documents to retrieve
            
        Returns:
            Dictionary with answer and sources
        """
        # Wrap entire query in a trace
        with tracing_service.trace(
            name="rag_query",
            user_id=user_id,
            input_summary=question
        ) as trace:
            total_start = time.perf_counter()
            step_timings = {}
            
            # Check if this is a temporal query (needs date ordering)
            is_temporal = self._is_temporal_query(question)
            temporal_context = ""
            if is_temporal:
                temporal_context = await self._get_recent_transactions_context(user_id, limit=15)
            
            # Step 1: Retrieve relevant documents via vector search
            with tracing_service.span("retrieval", "retrieval", metadata={"n_results": n_results, "temporal": is_temporal}):
                retrieval_start = time.perf_counter()
                search_results = await vector_store.search(
                    query=question,
                    user_id=user_id,
                    n_results=n_results
                )
                step_timings['retrieval_ms'] = (time.perf_counter() - retrieval_start) * 1000
            
            # Step 2: Format retrieved context
            context_start = time.perf_counter()
            context = self._format_context(search_results)
            
            # For temporal queries, prepend the date-ordered context
            if temporal_context:
                context = temporal_context + "\n\n---\n\nADDITIONAL CONTEXT FROM VECTOR SEARCH:\n" + context
            
            step_timings['context_formatting_ms'] = (time.perf_counter() - context_start) * 1000
            
            # Step 3: Generate answer using LLM
            if not self.llm:
                total_time_ms = (time.perf_counter() - total_start) * 1000
                self._record_query_metrics(total_time_ms, step_timings, 0, len(context), False)
                
                answer = "LLM is not configured. Please set OPENAI_API_KEY or GEMINI_API_KEY."
                tracing_service.set_output_summary(answer)
                
                return {
                    "answer": answer,
                    "sources": [],
                    "context": context,
                    "metrics": {
                        "total_time_ms": round(total_time_ms, 2),
                        **{k: round(v, 2) for k, v in step_timings.items()}
                    }
                }
            
            # LLM generation with tracing
            with tracing_service.span("llm_generation", "llm") as llm_span:
                llm_start = time.perf_counter()
                answer = await self._generate_answer(question, context)
                step_timings['llm_generation_ms'] = (time.perf_counter() - llm_start) * 1000
            
            # Set output summary for trace
            tracing_service.set_output_summary(answer)
            
            # Step 4: Extract sources
            sources_start = time.perf_counter()
            sources = self._extract_sources(search_results)
            step_timings['source_extraction_ms'] = (time.perf_counter() - sources_start) * 1000
            
            # Calculate total time
            total_time_ms = (time.perf_counter() - total_start) * 1000
            
            # Record all metrics
            self._record_query_metrics(
                total_time_ms, 
                step_timings, 
                len(sources), 
                len(context),
                True
            )
            
            return {
                "answer": answer,
                "sources": sources,
                "context": context,
                "metrics": {
                    "total_time_ms": round(total_time_ms, 2),
                    **{k: round(v, 2) for k, v in step_timings.items()},
                    "source_count": len(sources),
                    "context_length": len(context),
                    "trace_id": trace.id
                }
            }
    
    def _record_query_metrics(
        self, 
        total_time_ms: float, 
        step_timings: Dict[str, float],
        source_count: int,
        context_length: int,
        llm_used: bool
    ):
        """Record detailed metrics for the query."""
        # Record total query time
        metrics_collector.record_timing(
            MetricsCollector.FLOW_RAG,
            "query",
            total_time_ms,
            metadata={
                "source_count": source_count,
                "context_length": context_length,
                "llm_used": llm_used
            }
        )
        
        # Record step timings as histograms
        for step_name, duration in step_timings.items():
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_RAG,
                step_name,
                duration
            )
        
        # Record source count histogram
        metrics_collector.add_histogram(
            MetricsCollector.FLOW_RAG,
            "source_count",
            source_count
        )
        
        # Record context length histogram
        metrics_collector.add_histogram(
            MetricsCollector.FLOW_RAG,
            "context_length",
            context_length
        )
        
        # Increment query counter
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_RAG,
            "queries_processed"
        )
        
        if llm_used:
            metrics_collector.increment_counter(
                MetricsCollector.FLOW_RAG,
                "llm_calls"
            )
    
    def _format_context(self, search_results: Dict[str, Any]) -> str:
        """Format search results into context string."""
        if not search_results.get('documents') or not search_results['documents'][0]:
            return "No relevant transactions found."
        
        documents = search_results['documents'][0]
        metadatas = search_results['metadatas'][0]
        
        context_parts = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
            context_parts.append(f"{i}. {doc}")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM with retrieved context."""
        
        system_prompt = """You are a helpful financial assistant analyzing personal credit card transactions.
You have access to transaction data and should provide accurate, helpful insights.

Guidelines:
- Base your answers on the provided transaction data
- Provide specific numbers, dates, and merchant names when available
- If the data doesn't contain enough information, say so clearly
- Suggest actionable insights when appropriate
- Be concise but comprehensive
- Format monetary amounts as currency (e.g., $1,234.56)
"""
        
        user_prompt = f"""Based on the following transaction data, please answer the question:

TRANSACTION DATA:
{context}

QUESTION: {question}

Please provide a clear, accurate answer based on the transaction data above."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            # Estimate tokens (rough approximation)
            input_text = system_prompt + user_prompt
            output_text = response.content
            input_tokens = len(input_text) // 4
            output_tokens = len(output_text) // 4
            
            # Record LLM call for tracing
            provider = llm_factory.get_current_provider()
            model_name = llm_factory.get_model_name()
            tracing_service.record_llm_call(
                model_name=model_name,
                provider=provider,
                input_text=input_text,
                output_text=output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_RAG,
                "estimated_input_tokens",
                input_tokens
            )
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_RAG,
                "estimated_output_tokens",
                output_tokens
            )
            
            return response.content
        except Exception as e:
            metrics_collector.record_error(
                MetricsCollector.FLOW_RAG,
                "llm_error"
            )
            return f"Error generating answer: {str(e)}"
    
    def _extract_sources(self, search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract source information from search results."""
        sources = []
        
        if not search_results.get('metadatas') or not search_results['metadatas'][0]:
            return sources
        
        metadatas = search_results['metadatas'][0]
        documents = search_results['documents'][0]
        distances = search_results.get('distances', [[]])[0]
        
        for i, meta in enumerate(metadatas):
            source = {
                "transaction_id": meta.get('transaction_id'),
                "date": meta.get('date'),
                "merchant": meta.get('merchant'),
                "amount": meta.get('amount'),
                "category": meta.get('category'),
                "relevance_score": 1 - distances[i] if i < len(distances) else 0,
                "text": documents[i] if i < len(documents) else ""
            }
            sources.append(source)
        
        return sources
    
    async def generate_insights(
        self,
        user_id: str,
        time_period: str = "last 12 months"
    ) -> Dict[str, Any]:
        """
        Generate financial insights for a user.
        
        Args:
            user_id: User ID
            time_period: Time period for analysis
            
        Returns:
            Dictionary with insights
        """
        with Timer(
            MetricsCollector.FLOW_RAG,
            "generate_insights",
            metadata={"time_period": time_period}
        ):
            questions = [
                f"What are the top spending categories in the {time_period}?",
                f"What are the biggest opportunities to save money?",
                f"Are there any unusual spending patterns?",
                f"What are the top 5 merchants by spending?"
            ]
            
            insights = {}
            for question in questions:
                result = await self.query(question, user_id, n_results=50)
                insights[question] = result['answer']
        
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_RAG,
            "insights_generated"
        )
        
        return insights


# Global instance
rag_service = RAGService()
