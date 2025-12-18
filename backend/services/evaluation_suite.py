"""
Evaluation Suite Service.
Provides pre-built test cases for RAG quality evaluation and regression testing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import statistics

from services.ragas_evaluation import ragas_service
from services import rag_service


@dataclass
class TestCase:
    """A single test case for evaluation."""
    id: str
    question: str
    category: str  # "spending", "merchants", "categories", "trends", "general"
    description: str
    ground_truth: Optional[str] = None  # Expected answer pattern
    min_faithfulness: float = 0.7
    min_relevancy: float = 0.7
    min_precision: float = 0.7


@dataclass
class TestResult:
    """Result of running a single test case."""
    test_case_id: str
    question: str
    answer: str
    sources_count: int
    faithfulness: Optional[float] = None
    calculation_accuracy: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    overall_score: Optional[float] = None
    passed: bool = False
    failure_reason: Optional[str] = None
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "question": self.question,
            "answer": self.answer[:200] + "..." if len(self.answer) > 200 else self.answer,
            "sources_count": self.sources_count,
            "faithfulness": self.faithfulness,
            "calculation_accuracy": self.calculation_accuracy,
            "answer_relevancy": self.answer_relevancy,
            "context_precision": self.context_precision,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "failure_reason": self.failure_reason,
            "latency_ms": round(self.latency_ms, 2)
        }


@dataclass
class SuiteResult:
    """Result of running the full test suite."""
    run_id: str
    start_time: datetime
    end_time: datetime
    total_cases: int
    passed_cases: int
    failed_cases: int
    avg_faithfulness: Optional[float] = None
    avg_relevancy: Optional[float] = None
    avg_precision: Optional[float] = None
    avg_overall: Optional[float] = None
    avg_latency_ms: float = 0.0
    results: List[TestResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": round(self.passed_cases / max(self.total_cases, 1), 2),
            "avg_faithfulness": self.avg_faithfulness,
            "avg_relevancy": self.avg_relevancy,
            "avg_precision": self.avg_precision,
            "avg_overall": self.avg_overall,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "results": [r.to_dict() for r in self.results]
        }


# Pre-built test cases for financial RAG
DEFAULT_TEST_CASES = [
    TestCase(
        id="spending_total",
        question="What is my total spending?",
        category="spending",
        description="Tests ability to calculate total spending"
    ),
    TestCase(
        id="spending_top_category",
        question="What category do I spend the most on?",
        category="categories",
        description="Tests category-based spending analysis"
    ),
    TestCase(
        id="spending_food",
        question="How much did I spend on food and dining?",
        category="categories",
        description="Tests category-specific spending lookup"
    ),
    TestCase(
        id="merchants_top",
        question="What are my top 5 merchants by spending?",
        category="merchants",
        description="Tests merchant ranking and aggregation"
    ),
    TestCase(
        id="merchants_amazon",
        question="How much did I spend at Amazon?",
        category="merchants",
        description="Tests specific merchant lookup"
    ),
    TestCase(
        id="trends_monthly",
        question="How has my spending changed month over month?",
        category="trends",
        description="Tests temporal trend analysis"
    ),
    TestCase(
        id="subscriptions",
        question="What recurring subscriptions do I have?",
        category="general",
        description="Tests subscription detection"
    ),
    TestCase(
        id="transactions_recent",
        question="What were my most recent transactions?",
        category="general",
        description="Tests recent transaction retrieval"
    ),
    TestCase(
        id="savings_opportunities",
        question="Where can I cut spending to save money?",
        category="general",
        description="Tests actionable insights generation"
    ),
    TestCase(
        id="spending_entertainment",
        question="How much do I spend on entertainment?",
        category="categories",
        description="Tests entertainment category analysis"
    ),
]


class EvaluationSuiteService:
    """Service for running evaluation test suites."""
    
    def __init__(self):
        self._test_cases = DEFAULT_TEST_CASES.copy()
        self._baseline_scores: Dict[str, float] = {}
        self._run_history: List[SuiteResult] = []
    
    def get_test_cases(self) -> List[Dict[str, Any]]:
        """Get all available test cases."""
        return [
            {
                "id": tc.id,
                "question": tc.question,
                "category": tc.category,
                "description": tc.description,
                "min_faithfulness": tc.min_faithfulness,
                "min_relevancy": tc.min_relevancy,
                "min_precision": tc.min_precision
            }
            for tc in self._test_cases
        ]
    
    def add_test_case(self, test_case: TestCase):
        """Add a custom test case."""
        self._test_cases.append(test_case)
    
    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case and evaluate."""
        import time
        
        start_time = time.perf_counter()
        
        # Run RAG query
        rag_result = await rag_service.query(
            question=test_case.question,
            user_id=None,  # Search all data for evaluation
            n_results=10
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Extract contexts
        contexts = [
            source.get("text", "") 
            for source in rag_result.get("sources", [])
            if source.get("text")
        ]
        
        if not contexts and rag_result.get("context"):
            contexts = [rag_result["context"]]
        
        # Create result
        result = TestResult(
            test_case_id=test_case.id,
            question=test_case.question,
            answer=rag_result.get("answer", ""),
            sources_count=len(rag_result.get("sources", [])),
            latency_ms=latency_ms
        )
        
        # Run RAGAS evaluation if available
        if ragas_service.is_available and contexts:
            eval_result = await ragas_service.evaluate_single(
                question=test_case.question,
                answer=rag_result.get("answer", ""),
                contexts=contexts,
                ground_truth=test_case.ground_truth
            )
            
            result.faithfulness = eval_result.faithfulness
            result.calculation_accuracy = eval_result.calculation_accuracy
            result.answer_relevancy = eval_result.answer_relevancy
            result.context_precision = eval_result.context_precision
            result.overall_score = eval_result.overall_score
            
            # Check if passed thresholds
            passed = True
            reasons = []
            
            if result.faithfulness and result.faithfulness < test_case.min_faithfulness:
                passed = False
                reasons.append(f"faithfulness {result.faithfulness:.2f} < {test_case.min_faithfulness}")
            
            if result.answer_relevancy and result.answer_relevancy < test_case.min_relevancy:
                passed = False
                reasons.append(f"relevancy {result.answer_relevancy:.2f} < {test_case.min_relevancy}")
            
            if result.context_precision and result.context_precision < test_case.min_precision:
                passed = False
                reasons.append(f"precision {result.context_precision:.2f} < {test_case.min_precision}")
            
            result.passed = passed
            result.failure_reason = ", ".join(reasons) if reasons else None
        else:
            # Without RAGAS, mark as passed if we got an answer
            result.passed = bool(result.answer and result.sources_count > 0)
            if not result.passed:
                result.failure_reason = "No answer or no sources retrieved"
        
        return result
    
    async def run_suite(self, test_case_ids: Optional[List[str]] = None) -> SuiteResult:
        """Run the full test suite or selected test cases."""
        import uuid
        
        start_time = datetime.utcnow()
        
        # Filter test cases if specific IDs provided
        if test_case_ids:
            test_cases = [tc for tc in self._test_cases if tc.id in test_case_ids]
        else:
            test_cases = self._test_cases
        
        results = []
        for test_case in test_cases:
            try:
                result = await self.run_single_test(test_case)
                results.append(result)
            except Exception as e:
                results.append(TestResult(
                    test_case_id=test_case.id,
                    question=test_case.question,
                    answer=f"Error: {str(e)}",
                    sources_count=0,
                    passed=False,
                    failure_reason=str(e)
                ))
        
        end_time = datetime.utcnow()
        
        # Calculate aggregates
        def safe_mean(values: List[float]) -> Optional[float]:
            valid = [v for v in values if v is not None]
            return statistics.mean(valid) if valid else None
        
        suite_result = SuiteResult(
            run_id=str(uuid.uuid4()),
            start_time=start_time,
            end_time=end_time,
            total_cases=len(results),
            passed_cases=sum(1 for r in results if r.passed),
            failed_cases=sum(1 for r in results if not r.passed),
            avg_faithfulness=safe_mean([r.faithfulness for r in results]),
            avg_relevancy=safe_mean([r.answer_relevancy for r in results]),
            avg_precision=safe_mean([r.context_precision for r in results]),
            avg_overall=safe_mean([r.overall_score for r in results]),
            avg_latency_ms=statistics.mean([r.latency_ms for r in results]) if results else 0,
            results=results
        )
        
        # Save to history
        self._run_history.append(suite_result)
        if len(self._run_history) > 10:
            self._run_history = self._run_history[-10:]
        
        return suite_result
    
    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent suite run history."""
        return [
            {
                "run_id": r.run_id,
                "start_time": r.start_time.isoformat(),
                "total_cases": r.total_cases,
                "passed_cases": r.passed_cases,
                "pass_rate": round(r.passed_cases / max(r.total_cases, 1), 2),
                "avg_overall": r.avg_overall
            }
            for r in reversed(self._run_history[-limit:])
        ]
    
    def set_baseline(self, scores: Dict[str, float]):
        """Set baseline scores for regression detection."""
        self._baseline_scores = scores
    
    def get_baseline(self) -> Dict[str, float]:
        """Get current baseline scores."""
        return self._baseline_scores


# Global instance
evaluation_suite = EvaluationSuiteService()
