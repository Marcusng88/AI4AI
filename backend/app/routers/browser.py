"""Simple browser router for live view URL access."""

from fastapi import APIRouter, HTTPException
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Store active browser sessions and their live view URLs
active_sessions: dict = {}

@router.get("/sessions/{session_id}/live-view-url")
async def get_live_view_url(session_id: str):
    """Get the live view URL for a browser session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Browser session not found")
    
    session_info = active_sessions[session_id]
    return {
        "session_id": session_id,
        "live_view_url": session_info.get("live_view_url"),
        "status": "active"
    }

def register_browser_session(session_id: str, live_view_url: str):
    """Register a browser session with its live view URL."""
    active_sessions[session_id] = {
        "live_view_url": live_view_url,
        "status": "active"
    }
    logger.info(f"Registered browser session {session_id} with live view URL")

def unregister_browser_session(session_id: str):
    """Unregister a browser session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        logger.info(f"Unregistered browser session {session_id}")
