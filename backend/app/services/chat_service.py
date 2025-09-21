"""Chat service for handling user interactions."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from app.core.logging import get_logger
from app.models.requests import Language
from app.agents.coordinator.coordinator_agent import coordinator_agent
from app.services.dynamodb_service import dynamodb_service

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat interactions."""
    
    def __init__(self):
        """Initialize chat service."""
        self.coordinator_agent = coordinator_agent
        self.dynamodb_service = dynamodb_service
    
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
            # Save user message to DynamoDB
            await self.dynamodb_service.add_message(
                session_id=session_id,
                role="user",
                content=message,
                metadata={
                    "language": language.value,
                    "user_id": user_id,
                    "user_context": user_context
                }
            )
            
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
            elif response.get("status") == "tutorial":
                # Handle tutorial responses
                formatted_response["tutorial"] = response.get("tutorial", "")
                formatted_response["message"] = response.get("message", "Here's a tutorial to help you:")
                logger.info(f"Tutorial response formatted for frontend: {len(formatted_response.get('tutorial', ''))} characters")
            
            # Save assistant response to DynamoDB
            assistant_metadata = formatted_response.get("metadata", {})
            assistant_metadata.update({
                "status": formatted_response.get("status", "error"),
                "requires_human": formatted_response.get("requires_human", True)
            })
            
            # Add tutorial content to metadata if present
            if formatted_response.get("tutorial"):
                assistant_metadata["tutorial"] = formatted_response["tutorial"]
                logger.info(f"Added tutorial content to session metadata: {len(formatted_response['tutorial'])} characters")
            
            await self.dynamodb_service.add_message(
                session_id=session_id,
                role="assistant",
                content=formatted_response["message"],
                metadata=assistant_metadata
            )
            
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
            
            # Save error message to DynamoDB
            try:
                await self.dynamodb_service.add_message(
                    session_id=session_id,
                    role="system",
                    content=error_response["message"],
                    metadata={
                        "error": str(e),
                        "language": language.value,
                        "user_id": user_id
                    }
                )
            except Exception as db_error:
                logger.error(f"Failed to save error message to DynamoDB: {db_error}")
            
            return error_response
    
    async def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        try:
            messages = await self.dynamodb_service.get_session_messages(session_id)
            
            # Format messages to match expected structure
            formatted_messages = []
            for message in messages:
                formatted_message = {
                    "timestamp": message["created_at"],
                    "role": message["role"],
                    "message": message["content"],
                    "metadata": message.get("metadata", {})
                }
                formatted_messages.append(formatted_message)
            
            return formatted_messages
            
        except Exception as e:
            logger.error(f"Error getting chat history for session {session_id}: {str(e)}")
            raise ValueError(f"Session {session_id} not found or error retrieving history")
    
    async def clear_session(self, session_id: str, user_id: str = None) -> bool:
        """Clear chat session history."""
        try:
            if user_id:
                # Delete entire session (including session record and all messages)
                success = await self.dynamodb_service.delete_session(user_id, session_id)
                if success:
                    logger.info(f"Cleared session {session_id} for user {user_id}")
                    return True
            else:
                # If no user_id provided, we can only clear messages, not the session record
                # This is a limitation - we need user_id to properly delete from DynamoDB
                logger.warning(f"Cannot clear session {session_id} without user_id")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {str(e)}")
            return False
