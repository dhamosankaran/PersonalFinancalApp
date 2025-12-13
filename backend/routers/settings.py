"""Settings router for diagnostics, configuration, and LLM provider management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
from pathlib import Path

from database import get_db
from models import User, Transaction, UploadedDocument, ChatMessage
from services import vector_store, analytics_service
from services.llm_provider import llm_manager, ModelProvider, initialize_providers
from config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Pydantic models for LLM provider endpoints
class ProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    available: bool
    active: bool
    model: str


class ProvidersResponse(BaseModel):
    """Response containing all available providers."""
    providers: List[ProviderInfo]
    active_provider: Optional[str]


class SetProviderRequest(BaseModel):
    """Request to set the active LLM provider."""
    provider: str  # "openai" or "gemini"


class SetProviderResponse(BaseModel):
    """Response after setting the provider."""
    success: bool
    message: str
    active_provider: str
    model: str


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
            "openai_configured": bool(settings.openai_api_key)
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


# ============================================================================
# LLM Provider Management (MCP-inspired model switching)
# ============================================================================

@router.get("/providers", response_model=ProvidersResponse)
async def get_providers():
    """
    Get list of available LLM providers and their status.
    
    Returns information about which providers are configured
    and which one is currently active. This enables MCP-style
    model switching in the application.
    """
    # Ensure providers are initialized
    if not llm_manager.get_available_providers():
        initialize_providers()
    
    providers = llm_manager.get_available_providers()
    active = llm_manager.get_active_provider_name()
    
    return ProvidersResponse(
        providers=[ProviderInfo(**p) for p in providers],
        active_provider=active
    )


@router.post("/providers/switch", response_model=SetProviderResponse)
async def switch_provider(request: SetProviderRequest):
    """
    Switch the active LLM provider.
    
    Allows switching between OpenAI and Gemini models on the fly.
    The change takes effect immediately for subsequent chat requests.
    
    Example:
        POST /api/settings/providers/switch
        {"provider": "gemini"}
    """
    try:
        provider = ModelProvider(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {request.provider}. Valid options: openai, gemini"
        )
    
    # Check if provider is available
    providers = llm_manager.get_available_providers()
    provider_info = next((p for p in providers if p["name"] == provider.value), None)
    
    if not provider_info:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {request.provider} is not registered. Check your .env configuration."
        )
    
    if not provider_info["available"]:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {request.provider} is not available. Please check your API key configuration (OPENAI_API_KEY or GEMINI_API_KEY)."
        )
    
    # Switch the provider
    success = llm_manager.set_active_provider(provider)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch to provider {request.provider}"
        )
    
    # Get updated provider info
    active_provider = llm_manager.get_active_provider()
    
    return SetProviderResponse(
        success=True,
        message=f"Successfully switched to {provider.value}",
        active_provider=provider.value,
        model=getattr(active_provider, 'model', 'unknown')
    )


@router.get("/model-info")
async def get_model_info() -> Dict[str, Any]:
    """
    Get detailed information about the current active model.
    
    Returns the provider name, model identifier, and configuration details.
    Useful for displaying the current LLM status in the UI.
    """
    provider = llm_manager.get_active_provider()
    
    if not provider:
        return {
            "configured": False,
            "message": "No LLM provider is configured. Please set OPENAI_API_KEY or GEMINI_API_KEY in your .env file."
        }
    
    return {
        "configured": True,
        "provider": provider.provider_name.value,
        "model": getattr(provider, 'model', 'unknown'),
        "available_providers": llm_manager.get_available_providers()
    }
