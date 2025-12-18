"""
RAGAS Evaluation API router.
Provides endpoints for evaluating RAG quality using RAGAS metrics.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.ragas_evaluation import ragas_service, EvaluationSample
from services import rag_service

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


class SingleEvaluationRequest(BaseModel):
    """Request for single evaluation."""
    question: str = Field(..., description="The user's question")
    answer: str = Field(..., description="The generated answer")
    contexts: List[str] = Field(..., description="List of retrieved context strings")
    ground_truth: Optional[str] = Field(None, description="Optional ground truth answer")


class BatchEvaluationRequest(BaseModel):
    """Request for batch evaluation."""
    samples: List[SingleEvaluationRequest]


class LiveQueryEvaluationRequest(BaseModel):
    """Request to run a query and evaluate it."""
    question: str = Field(..., description="Question to ask the RAG system")
    ground_truth: Optional[str] = Field(None, description="Optional ground truth for context recall")


@router.get("/status")
async def get_evaluation_status() -> Dict[str, Any]:
    """Check if RAGAS evaluation is available."""
    return {
        "ragas_available": ragas_service.is_available,
        "message": "RAGAS is ready for evaluation" if ragas_service.is_available else "RAGAS not installed. Run: pip install ragas datasets"
    }


@router.post("/single")
async def evaluate_single(request: SingleEvaluationRequest) -> Dict[str, Any]:
    """
    Evaluate a single RAG response using RAGAS metrics.
    
    Returns:
        Faithfulness, answer relevancy, context precision, and optionally context recall scores.
    """
    if not ragas_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAGAS not available. Install with: pip install ragas datasets"
        )
    
    result = await ragas_service.evaluate_single(
        question=request.question,
        answer=request.answer,
        contexts=request.contexts,
        ground_truth=request.ground_truth
    )
    
    return result.to_dict()


@router.post("/batch")
async def evaluate_batch(request: BatchEvaluationRequest) -> Dict[str, Any]:
    """
    Evaluate multiple RAG responses in batch.
    
    Returns:
        Aggregated scores and individual results.
    """
    if not ragas_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAGAS not available. Install with: pip install ragas datasets"
        )
    
    samples = [
        EvaluationSample(
            question=s.question,
            answer=s.answer,
            contexts=s.contexts,
            ground_truth=s.ground_truth
        )
        for s in request.samples
    ]
    
    result = await ragas_service.evaluate_batch(samples)
    
    return result.to_dict()


@router.post("/live-query")
async def evaluate_live_query(request: LiveQueryEvaluationRequest) -> Dict[str, Any]:
    """
    Run a live query through the RAG system and evaluate the response.
    
    This is a convenience endpoint that:
    1. Sends the question to the RAG system
    2. Gets the answer and sources
    3. Evaluates the response using RAGAS
    
    Returns:
        The RAG response plus RAGAS evaluation scores.
    """
    # Run the RAG query (user_id=None searches all users for evaluation)
    rag_result = await rag_service.query(
        question=request.question,
        user_id=None,
        n_results=10
    )
    
    # Extract contexts - use the FULL context that was passed to the LLM
    # This includes temporal context + vector search results
    contexts = []
    
    # First, use the full context string if available (includes temporal data)
    if rag_result.get("context"):
        contexts = [rag_result["context"]]
    else:
        # Fall back to source texts if no full context
        contexts = [
            source.get("text", "") 
            for source in rag_result.get("sources", [])
            if source.get("text")
        ]
    
    # Evaluate with RAGAS if available
    evaluation = None
    if ragas_service.is_available and contexts:
        eval_result = await ragas_service.evaluate_single(
            question=request.question,
            answer=rag_result["answer"],
            contexts=contexts,
            ground_truth=request.ground_truth
        )
        evaluation = eval_result.to_dict()
    
    return {
        "question": request.question,
        "answer": rag_result["answer"],
        "sources_count": len(rag_result.get("sources", [])),
        "rag_metrics": rag_result.get("metrics", {}),
        "ragas_evaluation": evaluation,
        "ragas_available": ragas_service.is_available
    }


@router.get("/history")
async def get_evaluation_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent evaluation results from cache.
    """
    return {
        "results": ragas_service.get_cached_results(limit),
        "count": min(limit, len(ragas_service.get_cached_results(limit)))
    }


@router.get("/aggregate")
async def get_aggregate_scores() -> Dict[str, Any]:
    """
    Get aggregate RAGAS scores from all cached evaluations.
    """
    return ragas_service.get_aggregate_scores()


@router.delete("/cache")
async def clear_evaluation_cache() -> Dict[str, str]:
    """
    Clear the evaluation results cache.
    """
    ragas_service.clear_cache()
    return {"message": "Evaluation cache cleared"}


@router.get("/metrics-explanation")
async def get_metrics_explanation() -> Dict[str, Any]:
    """
    Get explanations of RAGAS metrics.
    """
    return {
        "metrics": {
            "faithfulness": {
                "name": "Faithfulness",
                "description": "Measures how factually consistent the answer is with the retrieved context. Score of 1.0 means all claims in the answer can be inferred from the context.",
                "range": "0.0 to 1.0 (higher is better)",
                "requires_ground_truth": False
            },
            "answer_relevancy": {
                "name": "Answer Relevancy",
                "description": "Measures how well the generated answer addresses the original question. Penalizes incomplete or redundant answers.",
                "range": "0.0 to 1.0 (higher is better)",
                "requires_ground_truth": False
            },
            "context_precision": {
                "name": "Context Precision",
                "description": "Measures if the retrieved contexts are relevant to the question. Higher scores indicate better retrieval quality.",
                "range": "0.0 to 1.0 (higher is better)",
                "requires_ground_truth": False
            },
            "context_recall": {
                "name": "Context Recall",
                "description": "Measures if all the relevant information needed to answer the question was retrieved. Requires ground truth answer.",
                "range": "0.0 to 1.0 (higher is better)",
                "requires_ground_truth": True
            }
        },
        "interpretation": {
            "excellent": "Score > 0.9: Excellent quality",
            "good": "Score 0.7-0.9: Good quality",
            "fair": "Score 0.5-0.7: Fair quality, needs improvement",
            "poor": "Score < 0.5: Poor quality, significant issues"
        }
    }


# ========== Test Suite Endpoints ==========

@router.get("/test-suite")
async def get_test_suite() -> Dict[str, Any]:
    """
    Get available test cases for evaluation.
    """
    from services.evaluation_suite import evaluation_suite
    return {
        "test_cases": evaluation_suite.get_test_cases(),
        "count": len(evaluation_suite.get_test_cases())
    }


@router.post("/test-suite/run")
async def run_test_suite(request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run the evaluation test suite.
    
    Args:
        request: Optional JSON body with test_case_ids list.
                If not provided, runs all test cases.
    
    Returns:
        Suite results with pass/fail status and RAGAS scores for each test.
    """
    from services.evaluation_suite import evaluation_suite
    
    test_case_ids = None
    if request and isinstance(request, dict):
        test_case_ids = request.get("test_case_ids")
    
    result = await evaluation_suite.run_suite(test_case_ids)
    return result.to_dict()


@router.get("/test-suite/history")
async def get_test_suite_history(limit: int = 10) -> Dict[str, Any]:
    """
    Get recent test suite run history.
    """
    from services.evaluation_suite import evaluation_suite
    return {
        "runs": evaluation_suite.get_run_history(limit),
        "count": len(evaluation_suite.get_run_history(limit))
    }


@router.get("/test-suite/baseline")
async def get_baseline_scores() -> Dict[str, Any]:
    """
    Get baseline scores for regression detection.
    """
    from services.evaluation_suite import evaluation_suite
    return {
        "baseline": evaluation_suite.get_baseline()
    }


@router.post("/test-suite/baseline")
async def set_baseline_scores(scores: Dict[str, float]) -> Dict[str, Any]:
    """
    Set baseline scores for regression detection.
    
    Args:
        scores: Dictionary with score names and threshold values.
    """
    from services.evaluation_suite import evaluation_suite
    evaluation_suite.set_baseline(scores)
    return {
        "message": "Baseline scores updated",
        "baseline": evaluation_suite.get_baseline()
    }

