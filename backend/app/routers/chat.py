"""Chat endpoints for user interactions."""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime
from typing import List, Optional
import uuid

from app.models.requests import ChatRequest, AddMessageRequest
from app.models.responses import ChatResponse, ResponseStatus
from app.services.chat_service import ChatService
from app.services.dynamodb_service import dynamodb_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest, fastapi_request: Request):
    """Chat endpoint for user interactions with AI agents."""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Initialize chat service
        chat_service = ChatService()
        
        # Process the chat request
        response = await chat_service.process_message(
            message=request.message,
            session_id=session_id,
            language=request.language,
            user_id=request.user_id,
            user_context=request.user_context
        )
        
        return ChatResponse(
            message=response["message"],
            session_id=session_id,
            status=ResponseStatus.SUCCESS if response.get("status") != "error" else ResponseStatus.ERROR,
            metadata=response.get("metadata"),
            payment_links=response.get("payment_links", []),
            screenshots=response.get("screenshots", [])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


@router.get("/chat/sessions/{session_id}/history")
async def get_chat_history(session_id: str, fastapi_request: Request):
    """Get chat history for a session."""
    try:
        # Initialize chat service
        chat_service = ChatService()
        history = await chat_service.get_chat_history(session_id)
        
        return {
            "session_id": session_id,
            "history": history,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {str(e)}"
        )


@router.delete("/chat/sessions/{session_id}")
async def clear_chat_session(session_id: str, fastapi_request: Request):
    """Clear chat session history."""
    try:
        # Initialize chat service
        chat_service = ChatService()
        await chat_service.clear_session(session_id)
        
        return {
            "message": "Session cleared successfully",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing session: {str(e)}"
        )


# DynamoDB Session Management Endpoints

@router.post("/sessions")
async def create_session(user_id: str, title: Optional[str] = None):
    """Create a new chat session for a user."""
    try:
        session = await dynamodb_service.create_session(user_id, title)
        return {
            "status": "success",
            "session": session,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating session: {str(e)}"
        )


@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user."""
    try:
        sessions = await dynamodb_service.get_user_sessions(user_id)
        return {
            "status": "success",
            "sessions": sessions,
            "count": len(sessions),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 100):
    """Get messages for a session."""
    try:
        messages = await dynamodb_service.get_session_messages(session_id, limit)
        return {
            "status": "success",
            "session_id": session_id,
            "messages": messages,
            "count": len(messages),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching messages: {str(e)}"
        )


@router.post("/sessions/{session_id}/messages")
async def add_message(session_id: str, request: AddMessageRequest):
    """Add a message to a session."""
    try:
        message = await dynamodb_service.add_message(
            session_id, 
            request.role, 
            request.content, 
            request.metadata
        )
        return {
            "status": "success",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding message: {str(e)}"
        )


@router.get("/sessions/{user_id}/{session_id}")
async def get_session(user_id: str, session_id: str):
    """Get a specific session."""
    try:
        session = await dynamodb_service.get_session(user_id, session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        return {
            "status": "success",
            "session": session,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching session: {str(e)}"
        )


@router.put("/sessions/{user_id}/{session_id}")
async def update_session(user_id: str, session_id: str, title: Optional[str] = None):
    """Update session information."""
    try:
        success = await dynamodb_service.update_session(user_id, session_id, title)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or update failed"
            )
        return {
            "status": "success",
            "message": "Session updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating session: {str(e)}"
        )


@router.delete("/sessions/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    """Delete a session and all its messages."""
    try:
        success = await dynamodb_service.delete_session(user_id, session_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or deletion failed"
            )
        return {
            "status": "success",
            "message": "Session deleted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting session: {str(e)}"
        )
