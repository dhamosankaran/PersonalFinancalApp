"""Chat router for RAG-based conversations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database import get_db
from models import ChatMessage, User
from schemas import ChatRequest, ChatResponse, ChatMessageResponse
from services import rag_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """
    Chat with the RAG system.
    Send a question and get an answer with sources.
    """
    # Get or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Save user message
    user_message = ChatMessage(
        user_id=user.id,
        role="user",
        content=request.query
    )
    db.add(user_message)
    db.commit()
    
    # Get answer from RAG service
    result = await rag_service.query(
        question=request.query,
        user_id=str(user.id)
    )
    
    # Save assistant message
    assistant_message = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=result['answer'],
        retrieved_context={
            'sources': result['sources'],
            'context': result.get('context', '')
        }
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    return ChatResponse(
        response=result['answer'],
        sources=result['sources'],
        conversation_id=assistant_message.id
    )


@router.get("/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    user_email: str = "default@example.com",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get chat history for a user."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    return list(reversed(messages))


@router.delete("/history")
async def clear_chat_history(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Clear chat history for a user."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    
    return {"message": "Chat history cleared"}
