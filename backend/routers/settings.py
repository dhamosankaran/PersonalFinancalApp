"""Settings router for diagnostics and configuration."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
import os
from pathlib import Path

from database import get_db
from models import User, Transaction, UploadedDocument, ChatMessage
from services import vector_store, analytics_service, llm_factory
from config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMProviderRequest(BaseModel):
    """Request body for setting LLM provider."""
    provider: str  # "openai" or "gemini"


@router.get("/diagnostics")
async def get_diagnostics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get system diagnostics including vector DB stats."""
    
    # Database stats
    total_users = db.query(User).count()
    total_transactions = db.query(Transaction).count()
    total_documents = db.query(UploadedDocument).count()
    processed_documents = db.query(UploadedDocument).filter(
        UploadedDocument.processed == True
    ).count()
    total_chat_messages = db.query(ChatMessage).count()
    
    # Vector store stats
    vector_stats = vector_store.get_stats()
    
    # LLM provider stats
    llm_status = llm_factory.get_provider_status()
    
    # Statements directory info
    statements_dir = settings.statements_directory
    if not os.path.isabs(statements_dir):
        project_root = Path(__file__).parent.parent.parent
        statements_dir = str(project_root / statements_dir)
    
    statements_count = 0
    if os.path.exists(statements_dir):
        statements_count = len([f for f in os.listdir(statements_dir) if f.endswith('.pdf')])
    
    return {
        "database": {
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "total_chat_messages": total_chat_messages
        },
        "vector_store": vector_stats,
        "statements_directory": {
            "path": statements_dir,
            "exists": os.path.exists(statements_dir),
            "pdf_count": statements_count
        },
        "configuration": {
            "embedding_model": settings.embedding_model,
            "chroma_path": settings.chroma_persist_directory,
            "openai_configured": bool(settings.openai_api_key),
            "gemini_configured": bool(settings.gemini_api_key),
            "current_llm_provider": llm_status["current_provider"]
        }
    }


@router.get("/vector-db/sample")
async def get_vector_db_sample(limit: int = 20) -> Dict[str, Any]:
    """Get a sample of documents from the vector database."""
    try:
        # Get sample from collection
        collection = vector_store.collection
        count = collection.count()
        
        if count == 0:
            return {
                "count": 0,
                "sample": [],
                "message": "No documents in vector database"
            }
        
        # Get sample documents
        results = collection.get(
            limit=min(limit, count),
            include=["documents", "metadatas"]
        )
        
        sample = []
        for i, doc_id in enumerate(results['ids']):
            sample.append({
                "id": doc_id,
                "document": results['documents'][i] if results['documents'] else None,
                "metadata": results['metadatas'][i] if results['metadatas'] else None
            })
        
        return {
            "total_count": count,
            "sample_count": len(sample),
            "sample": sample
        }
    except Exception as e:
        return {
            "error": str(e),
            "count": 0,
            "sample": []
        }


@router.post("/vector-db/reset")
async def reset_vector_db() -> Dict[str, Any]:
    """Reset the vector database (delete all embeddings)."""
    try:
        # Delete all documents in collection
        collection = vector_store.collection
        count_before = collection.count()
        
        # Get all IDs and delete
        if count_before > 0:
            all_ids = collection.get()['ids']
            if all_ids:
                collection.delete(ids=all_ids)
        
        return {
            "success": True,
            "message": f"Deleted {count_before} documents from vector database"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/database/transactions")
async def get_database_transactions(
    limit: int = 50,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get sample transactions from the SQL database."""
    try:
        total_count = db.query(Transaction).count()
        
        transactions = db.query(Transaction).order_by(
            Transaction.transaction_date.desc()
        ).limit(limit).all()
        
        sample = []
        for t in transactions:
            sample.append({
                "id": str(t.id),
                "date": t.transaction_date.isoformat() if t.transaction_date else None,
                "merchant": t.merchant,
                "amount": float(t.amount) if t.amount else 0,
                "category": t.category,
                "subcategory": t.subcategory,
                "source_file": t.source_file
            })
        
        return {
            "total_count": total_count,
            "sample_count": len(sample),
            "sample": sample,
            "purpose": "SQL database stores structured transaction data for fast queries, filtering, and aggregation (e.g., spending by category, date ranges)."
        }
    except Exception as e:
        return {
            "error": str(e),
            "sample": []
        }


@router.post("/database/reset")
async def reset_database(
    keep_users: bool = True,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Reset the SQL database (delete transactions, documents, and optionally users)."""
    try:
        # Delete chat messages
        chat_count = db.query(ChatMessage).delete()
        
        # Delete transactions  
        transaction_count = db.query(Transaction).delete()
        
        # Reset document processed status
        db.query(UploadedDocument).update({"processed": False, "transaction_count": 0})
        doc_count = db.query(UploadedDocument).delete()
        
        user_count = 0
        if not keep_users:
            user_count = db.query(User).delete()
        
        db.commit()
        
        return {
            "success": True,
            "deleted": {
                "transactions": transaction_count,
                "documents": doc_count,
                "chat_messages": chat_count,
                "users": user_count
            },
            "message": f"Reset database: {transaction_count} transactions, {doc_count} documents, {chat_count} chat messages deleted"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/reprocess")
async def reprocess_documents(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger reprocessing of all documents."""
    # Import here to avoid circular imports
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/upload/reprocess-all",
                timeout=300.0
            )
            return response.json()
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/embedding-comparison")
async def get_embedding_comparison_results() -> Dict[str, Any]:
    """Get pre-computed embedding comparison results."""
    import json
    
    results_path = Path(__file__).parent.parent / "data" / "embedding_comparison_results.json"
    
    if not results_path.exists():
        return {
            "available": False,
            "message": "No comparison results available. Run the comparison test first.",
            "results": None
        }
    
    try:
        with open(results_path, 'r') as f:
            data = json.load(f)
        return {
            "available": True,
            "timestamp": data.get("timestamp"),
            "test_config": data.get("test_config"),
            "results": data.get("results")
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "results": None
        }


@router.post("/embedding-comparison/run")
async def run_embedding_comparison(
    max_transactions: int = 50,
    providers: List[str] = None
) -> Dict[str, Any]:
    """Run embedding comparison test (may take a few minutes)."""
    import asyncio
    import subprocess
    import json
    
    # Run the comparison script
    try:
        result = subprocess.run(
            ["python", "test_embedding_comparison.py"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr,
                "output": result.stdout
            }
        
        # Read results file
        results_path = Path(__file__).parent.parent / "data" / "embedding_comparison_results.json"
        if results_path.exists():
            with open(results_path, 'r') as f:
                data = json.load(f)
            return {
                "success": True,
                "timestamp": data.get("timestamp"),
                "results": data.get("results"),
                "output": result.stdout[-1000:]  # Last 1000 chars of output
            }
        
        return {
            "success": True,
            "output": result.stdout,
            "message": "Comparison completed but no results file found"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Comparison test timed out (5 minute limit)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/llm-provider")
async def get_llm_provider() -> Dict[str, Any]:
    """Get current LLM provider and status for all providers."""
    return llm_factory.get_provider_status()


@router.post("/llm-provider")
async def set_llm_provider(request: LLMProviderRequest) -> Dict[str, Any]:
    """
    Set the LLM provider.
    
    Args:
        request: Contains 'provider' field with value "openai" or "gemini"
        
    Returns:
        Success status and updated provider info
    """
    provider = request.provider.lower()
    
    if provider not in ("openai", "gemini"):
        return {
            "success": False,
            "error": f"Invalid provider: {provider}. Must be 'openai' or 'gemini'"
        }
    
    success = llm_factory.set_provider(provider)
    
    if success:
        return {
            "success": True,
            "message": f"LLM provider set to {provider}",
            **llm_factory.get_provider_status()
        }
    else:
        return {
            "success": False,
            "error": f"Failed to set provider to {provider}"
        }
