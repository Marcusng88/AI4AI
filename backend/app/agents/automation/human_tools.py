"""
Human-in-the-Loop Tools for Browser-Use Agent
Provides various tools for the agent to interact with humans when it needs help.
"""

import asyncio
from typing import Optional, Dict, Any, List
from browser_use import Tools
from browser_use.agent.views import ActionResult
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create tools instance
tools = Tools()


@tools.action(description='Ask human for help with a specific question when the agent is stuck or unsure')
def ask_human_for_help(question: str) -> str:
    """
    Ask human for help when the agent encounters difficulties.
    
    Args:
        question: The specific question or problem the agent needs help with
        
    Returns:
        The human's response as a string
    """
    logger.info(f"Agent asking human for help: {question}")
    
    print("\n" + "="*60)
    print("🤖 AGENT NEEDS HELP")
    print("="*60)
    print(f"Question: {question}")
    print("-"*60)
    
    try:
        answer = input("Your response: ")
        if not answer.strip():
            answer = "Please continue with your best judgment."
        
        logger.info(f"Human responded: {answer}")
        return f"Human assistance: {answer}"
        
    except KeyboardInterrupt:
        logger.info("Human cancelled the request")
        return "Human cancelled the request. Please continue with your best judgment."
    except Exception as e:
        logger.error(f"Error getting human input: {e}")
        return "Unable to get human input. Please continue with your best judgment."


@tools.action(description='Ask human to confirm before proceeding with a sensitive or important action')
def ask_human_confirmation(action_description: str, risk_level: str = "medium") -> str:
    """
    Ask human to confirm before proceeding with an action.
    
    Args:
        action_description: Description of the action to be performed
        risk_level: Risk level of the action (low, medium, high)
        
    Returns:
        Confirmation result
    """
    logger.info(f"Agent requesting confirmation for: {action_description}")
    
    risk_colors = {
        "low": "🟢",
        "medium": "🟡", 
        "high": "🔴"
    }
    
    print("\n" + "="*60)
    print(f"{risk_colors.get(risk_level, '🟡')} CONFIRMATION REQUIRED ({risk_level.upper()} RISK)")
    print("="*60)
    print(f"Action: {action_description}")
    print("-"*60)
    print("Do you want to proceed? (y/yes/n/no)")
    
    try:
        response = input("Your choice: ").lower().strip()
        
        if response in ['y', 'yes', 'proceed', 'continue', 'ok']:
            logger.info("Human confirmed the action")
            return "Human confirmed: Proceed with the action."
        elif response in ['n', 'no', 'stop', 'cancel', 'abort']:
            logger.info("Human denied the action")
            return "Human denied: Do not proceed with this action. Find an alternative approach."
        else:
            logger.info(f"Human gave unclear response: {response}")
            return f"Human gave unclear response: '{response}'. Please ask for clarification before proceeding."
            
    except KeyboardInterrupt:
        logger.info("Human cancelled the confirmation")
        return "Human cancelled the confirmation. Do not proceed with the action."
    except Exception as e:
        logger.error(f"Error getting human confirmation: {e}")
        return "Unable to get human confirmation. Do not proceed with the sensitive action."


@tools.action(description='Ask human to choose from multiple options when the agent is uncertain')
def ask_human_choice(question: str, options: List[str]) -> str:
    """
    Ask human to choose from multiple options.
    
    Args:
        question: The question or context for the choice
        options: List of available options
        
    Returns:
        The selected option or human's custom response
    """
    logger.info(f"Agent asking human to choose from options: {question}")
    
    print("\n" + "="*60)
    print("🤖 MULTIPLE CHOICE QUESTION")
    print("="*60)
    print(f"Question: {question}")
    print("-"*60)
    print("Available options:")
    
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    print(f"{len(options) + 1}. Other (specify)")
    print("-"*60)
    
    try:
        response = input(f"Your choice (1-{len(options) + 1}): ").strip()
        
        if response.isdigit():
            choice_num = int(response)
            if 1 <= choice_num <= len(options):
                selected = options[choice_num - 1]
                logger.info(f"Human selected option {choice_num}: {selected}")
                return f"Human selected: {selected}"
            elif choice_num == len(options) + 1:
                custom = input("Please specify your choice: ").strip()
                logger.info(f"Human provided custom option: {custom}")
                return f"Human provided custom option: {custom}"
        
        # Try to match the response with options
        response_lower = response.lower()
        for option in options:
            if response_lower in option.lower() or option.lower() in response_lower:
                logger.info(f"Human selected by text match: {option}")
                return f"Human selected: {option}"
        
        # If no match, treat as custom response
        logger.info(f"Human provided custom response: {response}")
        return f"Human provided custom response: {response}"
        
    except KeyboardInterrupt:
        logger.info("Human cancelled the choice")
        return "Human cancelled the choice. Please make your best judgment."
    except Exception as e:
        logger.error(f"Error getting human choice: {e}")
        return "Unable to get human choice. Please make your best judgment."


@tools.action(description='Ask human to provide specific information needed to complete a task')
def ask_human_for_information(information_type: str, context: str = "") -> str:
    """
    Ask human for specific information needed to complete a task.
    
    Args:
        information_type: Type of information needed (e.g., "password", "address", "phone number")
        context: Additional context about why this information is needed
        
    Returns:
        The information provided by the human
    """
    logger.info(f"Agent requesting information: {information_type}")
    
    print("\n" + "="*60)
    print("📝 INFORMATION REQUIRED")
    print("="*60)
    print(f"Information needed: {information_type}")
    if context:
        print(f"Context: {context}")
    print("-"*60)
    
    # Handle sensitive information types
    sensitive_types = ['password', 'pin', 'ssn', 'credit card', 'secret']
    is_sensitive = any(sensitive in information_type.lower() for sensitive in sensitive_types)
    
    if is_sensitive:
        print("⚠️  This appears to be sensitive information.")
        print("⚠️  Make sure you trust this application before proceeding.")
    
    try:
        if is_sensitive:
            # For sensitive info, we might want to use getpass, but since we're in a web context,
            # we'll just use regular input with a warning
            info = input(f"Enter {information_type} (input will be visible): ").strip()
        else:
            info = input(f"Enter {information_type}: ").strip()
        
        if not info:
            return f"No {information_type} provided. Please continue without this information or ask again if required."
        
        logger.info(f"Human provided {information_type}")
        return f"Human provided {information_type}: {info}"
        
    except KeyboardInterrupt:
        logger.info("Human cancelled the information request")
        return f"Human cancelled providing {information_type}. Please continue without this information."
    except Exception as e:
        logger.error(f"Error getting information: {e}")
        return f"Unable to get {information_type}. Please continue without this information."


@tools.action(description='Report progress to human and ask if they want to continue or modify the approach')
def report_progress_and_ask(progress_description: str, next_steps: str = "") -> str:
    """
    Report current progress to human and ask for guidance on next steps.
    
    Args:
        progress_description: Description of what has been accomplished so far
        next_steps: Planned next steps (optional)
        
    Returns:
        Human's guidance on how to proceed
    """
    logger.info(f"Agent reporting progress: {progress_description}")
    
    print("\n" + "="*60)
    print("📊 PROGRESS REPORT")
    print("="*60)
    print(f"Progress: {progress_description}")
    if next_steps:
        print(f"Planned next steps: {next_steps}")
    print("-"*60)
    print("How would you like to proceed?")
    print("- Type 'continue' to proceed as planned")
    print("- Type 'stop' to stop the current task")
    print("- Provide specific instructions for modifications")
    
    try:
        guidance = input("Your guidance: ").strip()
        
        if not guidance:
            guidance = "continue"
        
        guidance_lower = guidance.lower()
        
        if guidance_lower in ['continue', 'proceed', 'go', 'yes', 'ok']:
            logger.info("Human wants to continue with current approach")
            return "Human wants to continue with the current approach."
        elif guidance_lower in ['stop', 'halt', 'cancel', 'abort', 'no']:
            logger.info("Human wants to stop the current task")
            return "Human wants to stop the current task. Please conclude and provide a summary."
        else:
            logger.info(f"Human provided specific guidance: {guidance}")
            return f"Human guidance: {guidance}"
            
    except KeyboardInterrupt:
        logger.info("Human cancelled the progress report")
        return "Human cancelled. Please continue with the current approach."
    except Exception as e:
        logger.error(f"Error getting guidance: {e}")
        return "Unable to get guidance. Please continue with the current approach."


# Export the tools instance so it can be used by the automation agent
__all__ = ['tools', 'ask_human_for_help', 'ask_human_confirmation', 'ask_human_choice', 
           'ask_human_for_information', 'report_progress_and_ask']
