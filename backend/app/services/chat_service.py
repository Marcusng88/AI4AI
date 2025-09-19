"""Chat service for handling user interactions."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from app.core.logging import get_logger
from app.models.requests import Language
from app.agents.coordinator.coordinator_agent import coordinator_agent

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat interactions."""
    
    def __init__(self):
        """Initialize chat service."""
        self.coordinator_agent = coordinator_agent
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        language: Language,
        user_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a user message through the coordinator agent."""
        
        logger.info(f"Processing message for session {session_id}")
        
        try:
            # Add message to session history
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            
            self.sessions[session_id].append({
                "timestamp": datetime.utcnow().isoformat(),
                "role": "user",
                "message": message,
                "language": language.value,
                "user_id": user_id
            })
            
            # Process through coordinator agent with complete request processing
            response = await self.coordinator_agent.process_complete_request(
                user_message=message,
                user_context=user_context or {},
                session_id=session_id,
                user_id=user_id
            )
            
            # Format response for frontend
            formatted_response = {
                "message": response.get("message", "I'm not sure how to help with that."),
                "status": response.get("status", "error"),
                "requires_human": response.get("requires_human", True),
                "metadata": {
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "language": language.value
                }
            }
            
            # Add additional fields based on response type
            if response.get("status") == "needs_information":
                formatted_response["missing_information"] = response.get("missing_information", [])
            elif response.get("status") == "incomplete":
                formatted_response["missing_information"] = response.get("missing_information", [])
            elif response.get("status") == "success":
                formatted_response["details"] = response.get("details", "")
            elif response.get("status") == "error":
                formatted_response["error"] = response.get("message", "Unknown error occurred")
            
            # Add response to session history
            self.sessions[session_id].append({
                "timestamp": datetime.utcnow().isoformat(),
                "role": "assistant",
                "message": formatted_response["message"],
                "metadata": formatted_response.get("metadata", {}),
                "status": formatted_response.get("status", "error"),
                "requires_human": formatted_response.get("requires_human", True)
            })
            
            logger.info(f"Successfully processed message for session {session_id}")
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {str(e)}")
            
            error_response = {
                "message": "Sorry, I encountered an error. Please try again.",
                "status": "error",
                "requires_human": True,
                "error": str(e),
                "metadata": {
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "language": language.value
                }
            }
            
            # Add error to session history
            self.sessions[session_id].append({
                "timestamp": datetime.utcnow().isoformat(),
                "role": "system",
                "message": error_response["message"],
                "error": str(e)
            })
            
            return error_response
    
    async def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        return self.sessions[session_id]
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear chat session history."""
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session {session_id}")
            return True
        
        return False
