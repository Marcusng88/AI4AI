"""
Seamless Human-in-the-Loop Tools for Coordinator Agent
Provides async tools that work within the same task execution without interruption.
"""

import asyncio
import json
import uuid
from typing import Optional, Dict, Any, List
from crewai.tools import BaseTool
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global variables for human interaction
_human_interaction_callback: Optional[callable] = None
_pending_requests: Dict[str, asyncio.Event] = {}
_pending_responses: Dict[str, str] = {}


def set_human_interaction_callback(callback: callable):
    """Set the callback function for human interaction.
    
    Args:
        callback: Function that takes (request_id, interaction_data) and sends to frontend
    """
    global _human_interaction_callback
    _human_interaction_callback = callback
    logger.info("Human interaction callback set for coordinator")


async def wait_for_human_response(request_id: str, timeout: int = 300) -> str:
    """Wait for human response with timeout.
    
    Args:
        request_id: Unique identifier for the request
        timeout: Timeout in seconds (default 5 minutes)
        
    Returns:
        Human response string
    """
    if request_id not in _pending_requests:
        _pending_requests[request_id] = asyncio.Event()
    
    try:
        await asyncio.wait_for(_pending_requests[request_id].wait(), timeout=timeout)
        response = _pending_responses.get(request_id, "No response provided")
        
        # Clean up
        del _pending_requests[request_id]
        if request_id in _pending_responses:
            del _pending_responses[request_id]
            
        return response
        
    except asyncio.TimeoutError:
        logger.warning(f"Human interaction timeout for request {request_id}")
        # Clean up
        if request_id in _pending_requests:
            del _pending_requests[request_id]
        return "Request timed out. Continuing with best judgment."


def provide_human_response(request_id: str, response: str):
    """Provide human response for a pending request.
    
    Args:
        request_id: Unique identifier for the request
        response: Human response
    """
    _pending_responses[request_id] = response
    
    if request_id in _pending_requests:
        _pending_requests[request_id].set()
        logger.info(f"Human response provided for request {request_id}")
    else:
        logger.warning(f"No pending request found for {request_id}")


async def send_human_interaction_request(interaction_type: str, data: Dict[str, Any]) -> str:
    """Send human interaction request and wait for response.
    
    Args:
        interaction_type: Type of interaction (help, confirmation, choice, information)
        data: Interaction data
        
    Returns:
        Human response
    """
    request_id = str(uuid.uuid4())
    
    interaction_data = {
        "request_id": request_id,
        "type": interaction_type,
        "timestamp": asyncio.get_event_loop().time(),
        **data
    }
    
    # Use callback if available (for WebSocket/SSE)
    if _human_interaction_callback:
        try:
            # Call the callback (it handles async internally)
            _human_interaction_callback(request_id, interaction_data)
            # Wait for the response
            return await wait_for_human_response(request_id)
        except Exception as e:
            logger.error(f"Error in human interaction callback: {e}")
            return f"Error getting human input: {e}. Continuing with best judgment."
    
    # Fallback to console (for testing/local development)
    logger.warning("No human interaction callback set, falling back to console")
    return _console_fallback(interaction_type, data)


def _console_fallback(interaction_type: str, data: Dict[str, Any]) -> str:
    """Console fallback for testing/development when no callback is set."""
    print(f"\n{'='*60}")
    print(f"🤖 COORDINATOR NEEDS INPUT ({interaction_type.upper()})")
    print(f"{'='*60}")
    
    if interaction_type == "information":
        info_type = data.get('information_type', 'information')
        context = data.get('context', '')
        print(f"Information needed: {info_type}")
        if context:
            print(f"Context: {context}")
        if data.get('is_sensitive'):
            print("⚠️ This appears to be sensitive information.")
        return input(f"Enter {info_type}: ").strip()
        
    elif interaction_type == "choice":
        print(f"Question: {data.get('question', '')}")
        options = data.get('options', [])
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        choice = input(f"Your choice (1-{len(options)}): ").strip()
        try:
            return options[int(choice) - 1]
        except (ValueError, IndexError):
            return choice
            
    elif interaction_type == "confirmation":
        print(f"Action: {data.get('action_description', '')}")
        print(f"Risk Level: {data.get('risk_level', 'medium')}")
        response = input("Do you want to proceed? (y/n): ").strip().lower()
        return "yes" if response in ['y', 'yes'] else "no"
        
    return "No response"


class AskHumanForInformationTool(BaseTool):
    """Tool for asking human for specific information needed to complete a task."""
    
    name: str = "ask_human_for_information"
    description: str = (
        "Ask human for specific information needed to complete a government service task. "
        "Use this when you need details like IC number, vehicle plate, phone number, etc. "
        "The task will continue seamlessly after getting the response."
    )
    
    def _run(self, information_type: str, context: str = "", is_sensitive: bool = False) -> str:
        """Ask human for specific information.
        
        Args:
            information_type: Type of information needed (e.g., "IC number", "vehicle plate")
            context: Additional context about why this information is needed
            is_sensitive: Whether this is sensitive information
            
        Returns:
            The information provided by the human
        """
        logger.info(f"Coordinator requesting information: {information_type}")
        
        # Use async wrapper
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                send_human_interaction_request("information", {
                    "information_type": information_type,
                    "context": context,
                    "is_sensitive": is_sensitive,
                    "placeholder": f"Enter your {information_type}",
                    "urgency": "high" if is_sensitive else "medium"
                })
            )
            
            if not result or result.strip() == "":
                return f"No {information_type} provided. Please continue without this information or ask again if required."
            
            logger.info(f"Human provided {information_type}")
            return f"Human provided {information_type}: {result}"
            
        except Exception as e:
            logger.error(f"Error getting information: {e}")
            return f"Unable to get {information_type}. Please continue without this information."
        finally:
            loop.close()


class AskHumanChoiceTool(BaseTool):
    """Tool for asking human to choose from multiple options."""
    
    name: str = "ask_human_choice"
    description: str = (
        "Ask human to choose from multiple options when uncertain about the best approach. "
        "Use this when there are different ways to proceed with a government service. "
        "The task will continue seamlessly after getting the choice."
    )
    
    def _run(self, question: str, options: List[str]) -> str:
        """Ask human to choose from multiple options.
        
        Args:
            question: The question or context for the choice
            options: List of available options
            
        Returns:
            The selected option or human's custom response
        """
        logger.info(f"Coordinator asking human to choose from options: {question}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                send_human_interaction_request("choice", {
                    "question": question,
                    "options": options + ["Other (please specify)"]
                })
            )
            
            # Try to match the response with options
            result_lower = result.lower()
            for option in options:
                if result_lower in option.lower() or option.lower() in result_lower:
                    logger.info(f"Human selected option: {option}")
                    return f"Human selected: {option}"
            
            # If no match, treat as custom response
            logger.info(f"Human provided custom response: {result}")
            return f"Human provided custom response: {result}"
            
        except Exception as e:
            logger.error(f"Error getting human choice: {e}")
            return "Unable to get human choice. Please make your best judgment."
        finally:
            loop.close()


class AskHumanConfirmationTool(BaseTool):
    """Tool for asking human to confirm before proceeding with sensitive actions."""
    
    name: str = "ask_human_confirmation"
    description: str = (
        "Ask human to confirm before proceeding with a sensitive or important action. "
        "Use this for actions like making payments, submitting forms, or accessing personal data. "
        "The task will continue seamlessly after getting the confirmation."
    )
    
    def _run(self, action_description: str, risk_level: str = "medium") -> str:
        """Ask human to confirm before proceeding with an action.
        
        Args:
            action_description: Description of the action to be performed
            risk_level: Risk level of the action (low, medium, high)
            
        Returns:
            Confirmation result
        """
        logger.info(f"Coordinator requesting confirmation for: {action_description}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                send_human_interaction_request("confirmation", {
                    "action_description": action_description,
                    "risk_level": risk_level,
                    "options": ["Yes, proceed", "No, don't proceed", "Ask for more details"]
                })
            )
            
            result_lower = result.lower()
            if any(word in result_lower for word in ['yes', 'proceed', 'continue', 'ok', 'confirm']):
                logger.info("Human confirmed the action")
                return "Human confirmed: Proceed with the action."
            elif any(word in result_lower for word in ['no', 'don\'t', 'stop', 'cancel', 'abort', 'deny']):
                logger.info("Human denied the action")
                return "Human denied: Do not proceed with this action. Find an alternative approach."
            else:
                logger.info(f"Human gave response: {result}")
                return f"Human response: {result}. Please consider this guidance before proceeding."
                
        except Exception as e:
            logger.error(f"Error getting human confirmation: {e}")
            return "Unable to get human confirmation. Do not proceed with the sensitive action."
        finally:
            loop.close()


# Create tool instances
ask_human_for_information = AskHumanForInformationTool()
ask_human_choice = AskHumanChoiceTool()
ask_human_confirmation = AskHumanConfirmationTool()

# Export tools
__all__ = [
    'ask_human_for_information',
    'ask_human_choice', 
    'ask_human_confirmation',
    'set_human_interaction_callback',
    'provide_human_response'
]
