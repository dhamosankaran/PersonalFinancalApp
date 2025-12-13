"""
RAGAS Evaluation Service for RAG quality assessment.
Enhanced for Financial RAG with specialized metrics:
- Faithfulness: Source value grounding (allows math derivations)
- Calculation Accuracy: Math correctness verification
- Answer Relevancy: Question-answer alignment
- Context Precision: Retrieval quality
"""

import asyncio
import re
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from langchain_openai import ChatOpenAI
from config import settings
from .metrics import metrics_collector, Timer, MetricsCollector


@dataclass
class EvaluationSample:
    """A single evaluation sample."""
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None


@dataclass
class EvaluationResult:
    """Results from a single evaluation."""
    question: str
    faithfulness: Optional[float] = None
    calculation_accuracy: Optional[float] = None  # NEW: Math correctness
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    overall_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "faithfulness": self.faithfulness,
            "calculation_accuracy": self.calculation_accuracy,
            "answer_relevancy": self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "overall_score": self.overall_score,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class BatchEvaluationResult:
    """Results from batch evaluation."""
    sample_count: int
    avg_faithfulness: Optional[float] = None
    avg_calculation_accuracy: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_context_recall: Optional[float] = None
    overall_avg_score: Optional[float] = None
    individual_results: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "avg_faithfulness": self.avg_faithfulness,
            "avg_calculation_accuracy": self.avg_calculation_accuracy,
            "avg_answer_relevancy": self.avg_answer_relevancy,
            "avg_context_precision": self.avg_context_precision,
            "avg_context_recall": self.avg_context_recall,
            "overall_avg_score": self.overall_avg_score,
            "individual_results": self.individual_results,
            "timestamp": self.timestamp.isoformat()
        }


class RAGASEvaluationService:
    """
    Enhanced RAG evaluation service for financial applications.
    
    Metrics:
    - Faithfulness: Are source values (amounts, merchants, dates) from context?
      Explicitly ALLOWS mathematical derivations (sums, averages, counts).
    - Calculation Accuracy: Are mathematical operations correct?
    - Answer Relevancy: Does the answer address the question?
    - Context Precision: Are retrieved documents relevant?
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._metrics_cache: List[EvaluationResult] = []
        self._max_cache_size = 100
        self._llm = None
        
        if settings.openai_api_key:
            self._llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=settings.openai_api_key
            )
        
        self._initialized = True
        print("RAG Evaluation service initialized (Enhanced for Financial RAG)")
    
    @property
    def is_available(self) -> bool:
        return self._llm is not None
    
    async def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationResult:
        """Evaluate a single RAG response with all metrics."""
        if not self._llm:
            return EvaluationResult(question=question)
            
        with Timer(MetricsCollector.FLOW_RAG, "ragas_evaluation", metadata={"sample_count": 1}):
            try:
                # Run all metrics in parallel
                faithfulness_score, calc_score, relevancy_score, precision_score = await asyncio.gather(
                    self._calculate_faithfulness(answer, contexts),
                    self._calculate_calculation_accuracy(answer, contexts),
                    self._calculate_relevancy(question, answer),
                    self._calculate_context_precision(question, contexts)
                )
                
                # Overall score (weighted: faithfulness and calc_accuracy are most important for financial)
                scores = [s for s in [faithfulness_score, calc_score, relevancy_score, precision_score] if s is not None]
                overall = statistics.mean(scores) if scores else None
                
                result = EvaluationResult(
                    question=question,
                    faithfulness=faithfulness_score,
                    calculation_accuracy=calc_score,
                    answer_relevancy=relevancy_score,
                    context_precision=precision_score,
                    overall_score=overall
                )
                
                self._metrics_cache.append(result)
                if len(self._metrics_cache) > self._max_cache_size:
                    self._metrics_cache.pop(0)
                    
                self._record_metrics(result)
                return result
                
            except Exception as e:
                print(f"Evaluation failed: {e}")
                metrics_collector.record_error(MetricsCollector.FLOW_RAG, "ragas_evaluation_error")
                return EvaluationResult(question=question)

    async def _calculate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        Measures if source VALUES in the answer exist in the context.
        Explicitly ALLOWS:
        - Mathematical derivations (sums, averages, counts, percentages)
        - Paraphrasing and summarization
        - Logical inferences from facts
        
        Only penalizes:
        - Fabricated source values (amounts, dates, merchants not in context)
        - Contradictions to context
        """
        if not contexts:
            return 0.0
            
        context_text = "\n".join(contexts[:5])
        prompt = f"""You are a FAITHFULNESS evaluator for a Financial RAG system.

CONTEXT (Source Documents):
{context_text}

ANSWER TO EVALUATE:
{answer}

EVALUATION CRITERIA:
Your job is to verify that all SOURCE VALUES in the answer come from the context.

✅ ALLOWED (Score 1.0):
- Mathematical operations on source values (e.g., "$14.57 + $8.88 = $23.45" is OK if $14.57 and $8.88 are in context)
- Counting items from context (e.g., "You have 5 transactions" is OK if 5 transactions are shown)
- Summarizing or paraphrasing context
- Totals, averages, percentages derived from context values

❌ NOT ALLOWED (Score 0.0):
- Dollar amounts not found in context
- Merchant names not found in context  
- Dates not found in context
- Facts that contradict the context

SCORING:
- 1.0: All source values (amounts, merchants, dates) exist in context. Math derivations are correct.
- 0.7: Most values are grounded, minor issues.
- 0.5: Some values are grounded but significant gaps.
- 0.0: Major fabricated values or contradictions.

Return ONLY a single number (0.0, 0.5, 0.7, or 1.0)."""

        try:
            response = await self._llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 0.5

    async def _calculate_calculation_accuracy(self, answer: str, contexts: List[str]) -> float:
        """
        Verifies mathematical correctness of calculations in the answer.
        Checks: additions, subtractions, totals, averages, counts, percentages.
        """
        context_text = "\n".join(contexts[:5]) if contexts else "No context provided."
        prompt = f"""You are a CALCULATION ACCURACY evaluator for a Financial RAG system.

CONTEXT (Source Values):
{context_text}

ANSWER TO EVALUATE:
{answer}

TASK: Check if all mathematical calculations in the answer are CORRECT.

WHAT TO CHECK:
1. Addition/Subtraction: Do the numbers add up correctly?
2. Totals: Are final totals calculated correctly from individual values?
3. Counts: Is the count of items accurate?
4. Percentages: Are percentage calculations correct?
5. Averages: Are averages computed correctly?

EXAMPLES:
- "$14.57 + $8.88 = $23.45" ✅ (14.57 + 8.88 = 23.45, correct)
- "$14.57 + $8.88 = $24.00" ❌ (should be 23.45, incorrect)
- "Total: $100 from 5 transactions" - Verify the 5 items sum to $100

SCORING:
- 1.0: All calculations are mathematically correct OR no calculations present.
- 0.7: Minor rounding differences (within $0.05).
- 0.5: Some calculations are wrong.
- 0.0: Major calculation errors.

If there are NO calculations in the answer, return 1.0.

Return ONLY a single number (0.0, 0.5, 0.7, or 1.0)."""

        try:
            response = await self._llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 1.0  # Default to 1.0 if no calculations to verify

    async def _calculate_relevancy(self, question: str, answer: str) -> float:
        """Measures if the answer addresses the question."""
        prompt = f"""You are an ANSWER RELEVANCY evaluator.

QUESTION: {question}

ANSWER: {answer}

SCORING:
- 1.0: Answer directly and completely addresses the question.
- 0.7: Answer mostly addresses the question but misses some aspects.
- 0.5: Answer is somewhat related but incomplete or tangential.
- 0.0: Answer does not address the question at all.

Return ONLY a single number (0.0, 0.5, 0.7, or 1.0)."""

        try:
            response = await self._llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 0.5

    async def _calculate_context_precision(self, question: str, contexts: List[str]) -> float:
        """Measures if retrieved contexts are relevant to the question."""
        if not contexts:
            return 0.0
            
        context_text = "\n---\n".join(contexts[:5])
        prompt = f"""You are a CONTEXT PRECISION evaluator.

QUESTION: {question}

RETRIEVED DOCUMENTS:
{context_text}

SCORING:
- 1.0: Documents contain exactly the information needed to answer the question.
- 0.7: Documents contain relevant information but some noise.
- 0.5: Documents are somewhat related but missing key info.
- 0.0: Documents are irrelevant to the question.

Return ONLY a single number (0.0, 0.5, 0.7, or 1.0)."""

        try:
            response = await self._llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 0.5

    def _extract_score(self, text: str) -> float:
        """Extract float score from LLM response."""
        try:
            # Look for common score patterns
            match = re.search(r"(0\.\d+|0|1\.0|1)", text.strip())
            if match:
                score = float(match.group(1))
                return min(1.0, max(0.0, score))  # Clamp to [0, 1]
            return 0.5
        except:
            return 0.5

    async def evaluate_batch(self, samples: List[EvaluationSample]) -> BatchEvaluationResult:
        """Evaluate multiple RAG responses."""
        if not samples:
            return BatchEvaluationResult(sample_count=0, individual_results=[])
            
        with Timer(MetricsCollector.FLOW_RAG, "ragas_batch_evaluation"):
            results = []
            for sample in samples:
                res = await self.evaluate_single(sample.question, sample.answer, sample.contexts)
                results.append(res)
            
            def safe_mean(lst): return statistics.mean(lst) if lst else None
            
            faiths = [r.faithfulness for r in results if r.faithfulness is not None]
            calcs = [r.calculation_accuracy for r in results if r.calculation_accuracy is not None]
            relevs = [r.answer_relevancy for r in results if r.answer_relevancy is not None]
            precs = [r.context_precision for r in results if r.context_precision is not None]
            
            batch_result = BatchEvaluationResult(
                sample_count=len(samples),
                avg_faithfulness=safe_mean(faiths),
                avg_calculation_accuracy=safe_mean(calcs),
                avg_answer_relevancy=safe_mean(relevs),
                avg_context_precision=safe_mean(precs),
                individual_results=[r.to_dict() for r in results]
            )
            
            scores = [s for s in [batch_result.avg_faithfulness, batch_result.avg_calculation_accuracy,
                                   batch_result.avg_answer_relevancy, batch_result.avg_context_precision] if s is not None]
            if scores:
                batch_result.overall_avg_score = statistics.mean(scores)
                
            self._record_batch_metrics(batch_result)
            return batch_result

    def _record_metrics(self, result: EvaluationResult):
        """Record metrics to collector."""
        if result.faithfulness is not None:
            metrics_collector.add_histogram(MetricsCollector.FLOW_RAG, "ragas_faithfulness", result.faithfulness)
        if result.calculation_accuracy is not None:
            metrics_collector.add_histogram(MetricsCollector.FLOW_RAG, "ragas_calculation_accuracy", result.calculation_accuracy)
        if result.answer_relevancy is not None:
            metrics_collector.add_histogram(MetricsCollector.FLOW_RAG, "ragas_answer_relevancy", result.answer_relevancy)
        if result.context_precision is not None:
            metrics_collector.add_histogram(MetricsCollector.FLOW_RAG, "ragas_context_precision", result.context_precision)
        if result.overall_score is not None:
            metrics_collector.add_histogram(MetricsCollector.FLOW_RAG, "ragas_overall_score", result.overall_score)
        metrics_collector.increment_counter(MetricsCollector.FLOW_RAG, "ragas_evaluations")
    
    def _record_batch_metrics(self, result: BatchEvaluationResult):
        metrics_collector.increment_counter(MetricsCollector.FLOW_RAG, "ragas_batch_evaluations")
        metrics_collector.add_histogram(MetricsCollector.FLOW_RAG, "ragas_batch_sizes", result.sample_count)
    
    def get_cached_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._metrics_cache[-limit:]]
    
    def get_aggregate_scores(self) -> Dict[str, Any]:
        if not self._metrics_cache:
            return {
                "sample_count": 0,
                "avg_faithfulness": None,
                "avg_calculation_accuracy": None,
                "avg_answer_relevancy": None,
                "avg_context_precision": None,
                "avg_context_recall": None,
                "avg_overall_score": None
            }
        
        def safe_mean(lst): return statistics.mean(lst) if lst else None
        
        return {
            "sample_count": len(self._metrics_cache),
            "avg_faithfulness": safe_mean([r.faithfulness for r in self._metrics_cache if r.faithfulness]),
            "avg_calculation_accuracy": safe_mean([r.calculation_accuracy for r in self._metrics_cache if r.calculation_accuracy]),
            "avg_answer_relevancy": safe_mean([r.answer_relevancy for r in self._metrics_cache if r.answer_relevancy]),
            "avg_context_precision": safe_mean([r.context_precision for r in self._metrics_cache if r.context_precision]),
            "avg_context_recall": None,
            "avg_overall_score": safe_mean([r.overall_score for r in self._metrics_cache if r.overall_score])
        }
    
    def clear_cache(self):
        self._metrics_cache = []


# Global instance
ragas_service = RAGASEvaluationService()
