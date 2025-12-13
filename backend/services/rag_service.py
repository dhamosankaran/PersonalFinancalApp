"""
RAG (Retrieval-Augmented Generation) service.
Combines vector search with LLM reasoning.
Instrumented with comprehensive metrics for observability.
Supports multiple LLM providers via MCP-inspired abstraction.
"""

import time
from typing import List, Dict, Any, Optional
import json
import logging

from config import settings
from .vector_store import vector_store
from .metrics import metrics_collector, Timer, MetricsCollector
from .llm_provider import llm_manager, initialize_providers, ModelProvider

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG-based question answering with multi-model support."""
    
    def __init__(self):
        """Initialize the RAG service with LLM providers."""
        # Initialize all configured LLM providers
        initialize_providers()
        logger.info(f"RAG Service initialized with providers: {llm_manager.get_available_providers()}")
    
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
        total_start = time.perf_counter()
        step_timings = {}
        
        # Step 1: Retrieve relevant documents
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
        step_timings['context_formatting_ms'] = (time.perf_counter() - context_start) * 1000
        
        # Step 3: Generate answer using LLM
        if not llm_manager.is_available():
            total_time_ms = (time.perf_counter() - total_start) * 1000
            self._record_query_metrics(total_time_ms, step_timings, 0, len(context), False)
            
            return {
                "answer": "No LLM is configured. Please set OPENAI_API_KEY or GEMINI_API_KEY in your environment.",
                "sources": [],
                "context": context,
                "model_info": None,
                "metrics": {
                    "total_time_ms": round(total_time_ms, 2),
                    **{k: round(v, 2) for k, v in step_timings.items()}
                }
            }
        
        llm_start = time.perf_counter()
        answer, model_info = await self._generate_answer(question, context)
        step_timings['llm_generation_ms'] = (time.perf_counter() - llm_start) * 1000
        
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
            "model_info": model_info,
            "metrics": {
                "total_time_ms": round(total_time_ms, 2),
                **{k: round(v, 2) for k, v in step_timings.items()},
                "source_count": len(sources),
                "context_length": len(context)
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
    
    async def _generate_answer(self, question: str, context: str) -> tuple:
        """Generate answer using LLM with retrieved context.
        
        Returns:
            Tuple of (answer_text, model_info_dict)
        """
        
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
        
        try:
            # Use the LLM provider manager for multi-model support
            response = await llm_manager.generate(system_prompt, user_prompt)
            
            # Record metrics
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_RAG,
                "estimated_input_tokens",
                response.usage.get("prompt_tokens", 0)
            )
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_RAG,
                "estimated_output_tokens",
                response.usage.get("completion_tokens", 0)
            )
            
            # Create model info for the response
            model_info = {
                "provider": response.provider.value,
                "model": response.model,
                "latency_ms": round(response.latency_ms, 2)
            }
            
            return response.content, model_info
            
        except Exception as e:
            metrics_collector.record_error(
                MetricsCollector.FLOW_RAG,
                "llm_error"
            )
            logger.error(f"LLM generation error: {e}")
            return f"Error generating answer: {str(e)}", None
    
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
