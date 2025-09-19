"""
Intelligent Coordinator Agent using CrewAI for government service automation.
Uses LLM-based reasoning and decision making instead of rule-based approaches.
Includes memory capabilities for persistent conversation context.
"""

import asyncio
import os
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from crewai import Agent, Task, Crew, Process, LLM
from crewai.memory.short_term.short_term_memory import ShortTermMemory
from crewai.memory.entity.entity_memory import EntityMemory

from app.core.logging import get_logger
from app.config import settings
from .tavily_tool import TavilySearchTool
# Removed complex human tools - using simple prompting approach instead
# from ..automation.automation_agent import automation_agent  # Commented out for now
from ..stagehand.stagehand_agent import GovernmentServicesAgent

logger = get_logger(__name__)


class DynamoDBMemoryManager:
    """DynamoDB-based memory manager for persistent conversation storage."""
    
    def __init__(self, table_name: str = "crewai-memory", messages_table: str = "ai4ai-chat-messages"):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = table_name
        self.messages_table_name = messages_table
        self.table = self.dynamodb.Table(table_name)
        self.messages_table = self.dynamodb.Table(messages_table)
        
    async def save_conversation_memory(self, session_id: str, user_id: str, 
                                     user_message: str, agent_response: str, 
                                     context: Dict[str, Any], 
                                     additional_attributes: Dict[str, Any] = None) -> bool:
        """Save conversation memory to DynamoDB with user and session separation."""
        try:
            memory_item = {
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'user_message': user_message,
                'agent_response': agent_response,
                'context': context,
                'memory_id': str(uuid.uuid4()),
                'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
            }
            
            # Add any additional attributes
            if additional_attributes:
                memory_item.update(additional_attributes)
            
            self.table.put_item(Item=memory_item)
            logger.debug(f"Saved memory for user {user_id}, session {session_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save memory: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving memory: {e}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve conversation history for context from the chat messages table."""
        try:
            from boto3.dynamodb.conditions import Key
            
            response = self.messages_table.query(
                KeyConditionExpression=Key('session_id').eq(session_id),
                ScanIndexForward=True,  # Oldest first for conversation flow
                Limit=limit
            )
            
            logger.debug(f"Raw DynamoDB response for session {session_id}: {response}")
            
            # Convert DynamoDB items to conversation history format
            conversation_history = []
            for item in response.get('Items', []):
                logger.debug(f"Processing DynamoDB item: {item}")
                
                try:
                    # Safely extract values from DynamoDB format
                    def safe_get(item, key, default=''):
                        """Safely get value from DynamoDB item."""
                        if key not in item:
                            return default
                        value = item[key]
                        if isinstance(value, dict):
                            return value.get('S', value.get('N', default))
                        return str(value) if value is not None else default
                    
                    role = safe_get(item, 'role')
                    content = safe_get(item, 'content')
                    timestamp = safe_get(item, 'timestamp')
                    created_at = safe_get(item, 'created_at')
                    
                    # Convert DynamoDB format to our expected format
                    conv_item = {
                        'user_message': content if role == 'user' else '',
                        'agent_response': content if role == 'assistant' else '',
                        'role': role,
                        'timestamp': timestamp,
                        'created_at': created_at
                    }
                    
                    # Only add if it's a user or assistant message
                    if conv_item['role'] in ['user', 'assistant']:
                        conversation_history.append(conv_item)
                        logger.debug(f"Added conversation item: {conv_item}")
                        
                except Exception as item_error:
                    logger.warning(f"Error processing DynamoDB item {item}: {item_error}")
                    continue
            
            logger.debug(f"Retrieved {len(conversation_history)} conversation items for session {session_id}")
            return conversation_history
            
        except ClientError as e:
            logger.error(f"Failed to retrieve conversation history: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving conversation history: {e}")
            return []
    
    async def get_user_entity_memory(self, user_id: str) -> Optional[Dict]:
        """Get user-specific entity memory (preferences, service history, etc.)."""
        try:
            response = self.table.get_item(
                Key={
                    'session_id': f"user_entity_{user_id}",
                    'timestamp': "metadata"
                }
            )
            return response.get('Item')
            
        except ClientError as e:
            logger.error(f"Failed to get user entity memory: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user entity memory: {e}")
            return None
    
    async def save_user_entity_memory(self, user_id: str, 
                                    memory_data: Dict[str, Any],
                                    additional_attributes: Dict[str, Any] = None) -> bool:
        """Save user-specific entity memory with additional attributes."""
        try:
            memory_item = {
                'session_id': f"user_entity_{user_id}",
                'timestamp': "metadata",
                'user_id': user_id,
                'memory_data': memory_data,
                'last_updated': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            }
            
            # Add any additional attributes
            if additional_attributes:
                memory_item.update(additional_attributes)
            
            self.table.put_item(Item=memory_item)
            logger.debug(f"Saved user entity memory for user {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save user entity memory: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving user entity memory: {e}")
            return False
    
    async def update_user_attributes(self, user_id: str, 
                                   attributes: Dict[str, Any]) -> bool:
        """Update specific user attributes without overwriting existing data."""
        try:
            from boto3.dynamodb.conditions import Key
            
            # Get existing user entity memory
            existing = await self.get_user_entity_memory(user_id)
            if not existing:
                # Create new if doesn't exist
                return await self.save_user_entity_memory(user_id, {}, attributes)
            
            # Update existing attributes
            updated_data = existing.get('memory_data', {})
            updated_data.update(attributes)
            
            # Update the item
            response = self.table.update_item(
                Key={
                    'session_id': f"user_entity_{user_id}",
                    'timestamp': "metadata"
                },
                UpdateExpression="SET memory_data = :data, last_updated = :updated",
                ExpressionAttributeValues={
                    ':data': updated_data,
                    ':updated': datetime.utcnow().isoformat()
                },
                ReturnValues="UPDATED_NEW"
            )
            
            logger.debug(f"Updated user attributes for user {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update user attributes: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating user attributes: {e}")
            return False


class CoordinatorAgent:
    """Intelligent coordinator agent using CrewAI with LLM-based reasoning."""
    
    def __init__(self):
        # Initialize LLM with conservative settings for rate limiting
        self.llm = self._initialize_llm()
        
        # Initialize memory manager
        self.memory_manager = DynamoDBMemoryManager()
        
        # Initialize CrewAI memory components (simplified - no ChromaDB)
        self.short_term_memory = None
        self.entity_memory = None
        
        # Initialize tools
        try:
            self.tavily_tool = TavilySearchTool()
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily tool: {str(e)}")
            self.tavily_tool = None
        
        # Initialize stagehand agent as sub-agent
        self.stagehand_agent = GovernmentServicesAgent()
        
        # Create specialist web automation agent
        self.web_automation_agent = self._create_web_automation_agent()
        
        # Initialize main coordinator agent with memory and delegation
        self.main_agent = self._create_main_agent()
        
        # Rate limiting - increased interval to prevent AWS throttling
        self.last_request_time = 0
        self.min_request_interval = 3.0  # 3 seconds between requests
        
        # Request tracking
        self.request_count = 0
        self.successful_requests = 0
        
        logger.info("Intelligent coordinator agent with memory initialized successfully")
    
    def _create_short_term_memory(self) -> None:
        """Create short-term memory for recent conversation context."""
        # Disabled to avoid ChromaDB dependency
        return None
    
    def _create_entity_memory(self) -> None:
        """Create entity memory for user-specific information."""
        # Disabled to avoid ChromaDB dependency
        return None
    
    def _rate_limit(self):
        """Apply conservative rate limiting to prevent API throttling."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _retry_with_backoff(self, func, *args, max_retries=2, base_delay=2.0, **kwargs):
        """Retry a function with exponential backoff for rate limiting."""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if "RateLimitError" in str(e) or "Too many requests" in str(e):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + 1  # Add extra second
                        logger.warning(f"Rate limit hit, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                raise e
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def _initialize_llm(self) -> LLM:
        """Initialize Bedrock LLM for the coordinator with streaming enabled."""
        try:
            # Use CrewAI's LLM class with proper provider format and streaming enabled
            return LLM(
                model="bedrock/amazon.nova-lite-v1:0",
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_region_name=os.getenv('AWS_DEFAULT_REGION', 'ap-southeast-2'),
                stream=True  # Enable streaming for real-time responses
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    def _create_main_agent(self) -> Agent:
        """Create the main intelligent coordinator agent with LLM-based reasoning and delegation."""
        tools = [self.tavily_tool] if self.tavily_tool else []
        
        return Agent(
            role="Malaysian Government Service Manager",
            goal="Coordinate and execute Malaysian government service requests using intelligent delegation to specialized agents",
            backstory=(
                "You are an intelligent coordinator for Malaysian government services. You understand user requests, "
                "analyze what needs to be done, and delegate tasks to the appropriate specialist agents. "
                "You have access to a web automation specialist who can handle browser tasks like logging into "
                "government portals, filling forms, and extracting data.\n\n"
                
                "Your process:\n"
                "1. Understand the user's government service request\n"
                "2. Determine what information is needed\n"
                "3. If you have enough information, delegate browser automation tasks to the web specialist\n"
                "4. If you need more information, ask the user directly\n"
                "5. Coordinate the overall process and provide updates\n\n"
                
                "You can handle any Malaysian government service including JPJ, LHDN, JPN, EPF, MyEG, and more."
            ),
            tools=tools,
            llm=self.llm,
            memory=False,
            verbose=True,
            allow_delegation=True,  # Enable delegation to specialist agents
            reasoning=True,  # Enable LLM-based reasoning
            max_reasoning_attempts=3,  # Limit reasoning attempts
            max_iter=10,  # Allow more iterations for complex coordination
            max_execution_time=600  # 10 minute timeout for complex tasks
        )
    
    def _create_web_automation_agent(self) -> Agent:
        """Create a specialist web automation agent for browser tasks."""
        return Agent(
            role="Web Automation Specialist",
            goal="Execute browser automation tasks for Malaysian government portals with precision and efficiency",
            backstory=(
                "You are an expert web automation specialist for Malaysian government services. "
                "You excel at navigating complex government portals and performing precise browser actions.\n\n"
                
                "Your expertise includes:\n"
                "- MyEG portal navigation and summons checking\n"
                "- JPJ services (summons, licenses, vehicle registration)\n"
                "- LHDN tax services and e-filing\n"
                "- JPN identity services\n"
                "- EPF and SOCSO services\n"
                "- Other Malaysian government e-services\n\n"
                
                "When you receive delegation from the coordinator:\n"
                "1. Follow the specific instructions exactly\n"
                "2. Use natural language commands for browser actions\n"
                "3. Navigate step by step through the process\n"
                "4. Extract and report all relevant information found\n"
                "5. Handle any errors or issues encountered\n\n"
                
                "You work independently and efficiently, reporting back detailed results to the coordinator."
            ),
            tools=[self.stagehand_agent.stagehand_tool],
            llm=self.llm,
            memory=False,
            verbose=True,
            allow_delegation=False,  # Specialist doesn't delegate further
            reasoning=True,  # Enable reasoning for complex tasks
            max_reasoning_attempts=2,
            max_iter=20,  # Allow more iterations for complex browser tasks
            max_execution_time=600  # 10 minute timeout for complex tasks
        )
    
    async def process_user_request(self, user_message: str, user_context: Dict[str, Any] = None, 
                                 session_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Intelligently process user request using LLM-based reasoning with memory.
        
        Args:
            user_message: User's message/request
            user_context: Additional user context (IC, plate number, etc.)
            session_id: Session ID for conversation tracking
            user_id: User ID for personalization
            
        Returns:
            Response dictionary with status, message, and next steps
        """
        start_time = datetime.utcnow()
        self.request_count += 1
        
        try:
            # Apply rate limiting before processing
            self._rate_limit()
            
            # No complex human interaction setup needed - using simple prompting
            
            # Get conversation history if session_id provided
            conversation_history = []
            if session_id:
                conversation_history = await self.memory_manager.get_conversation_history(session_id)
            
            # Get user entity memory if user_id provided
            user_entity_memory = None
            if user_id:
                user_entity_memory = await self.memory_manager.get_user_entity_memory(user_id)
            
            # Single intelligent processing task with memory context
            result = await self._retry_with_backoff(
                self._intelligent_process_request, 
                user_message, 
                user_context or {},
                conversation_history,
                user_entity_memory
            )
            
            # Save conversation to memory if session_id provided
            if session_id and user_id and result.get("status") != "error":
                await self.memory_manager.save_conversation_memory(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=user_message,
                    agent_response=result.get("message", ""),
                    context=user_context or {}
                )
            
            self.successful_requests += 1
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Request processed successfully in {response_time:.2f}s")
            
            return result
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Coordinator processing failed after {response_time:.2f}s: {str(e)}")
            
            return {
                "status": "error",
                "message": f"I encountered an issue processing your request: {str(e)}. Please try again or contact support.",
                "requires_human": True,
                "error_details": str(e)
            }
    
    async def _intelligent_process_request(self, user_message: str, user_context: Dict[str, Any], 
                                         conversation_history: List[Dict] = None, 
                                         user_entity_memory: Dict = None) -> Dict[str, Any]:
        """
        Process user request using LLM-based reasoning with proper delegation to specialist agents.
        """
        try:
            # Build memory context string
            memory_context = ""
            if conversation_history:
                memory_context += f"\nCONVERSATION HISTORY:\n"
                for i, conv in enumerate(conversation_history[-5:]):  # Last 5 messages
                    if conv.get('role') == 'user':
                        memory_context += f"User: {conv.get('user_message', conv.get('content', ''))}\n"
                    elif conv.get('role') == 'assistant':
                        memory_context += f"Assistant: {conv.get('agent_response', conv.get('content', ''))}\n"
                memory_context += "\n"
            
            if user_entity_memory:
                memory_context += f"USER ENTITY MEMORY: {user_entity_memory.get('memory_data', {})}\n\n"
            
            # Create a task with explicit delegation instructions
            processing_task = Task(
                description=(
                    f"USER REQUEST: '{user_message}'\n"
                    f"USER CONTEXT: {user_context}\n\n"
                    f"{memory_context}"
                    
                    f"CRITICAL INSTRUCTIONS:\n"
                    f"=====================\n\n"
                    
                    f"For transportation summons payment requests:\n"
                    f"- IC number and plate number are SUFFICIENT to proceed\n"
                    f"- DO NOT ask for summons number or amount - these will be found during the process\n"
                    f"- IMMEDIATELY delegate to Web Automation Specialist with these instructions:\n"
                    f"  'Go to MyEG website, log in, navigate to traffic summons section, "
                    f"  enter IC number {user_context.get('ic_number', 'provided IC')} and plate number {user_context.get('plate_number', 'provided plate')}, "
                    f"  find and display all summons for payment'\n\n"
                    
                    f"For other government services:\n"
                    f"- If you have IC number, credentials, or other essential info, delegate immediately\n"
                    f"- Only ask for more info if truly essential information is missing\n\n"
                    
                    f"DELEGATION RULES:\n"
                    f"- ALWAYS delegate browser tasks to Web Automation Specialist\n"
                    f"- Be specific about what the specialist should do\n"
                    f"- Don't ask users for information you can find through automation\n\n"
                    
                    f"RESPONSE FORMAT:\n"
                    f"- If delegating: 'I'll help you with that. Let me delegate this to our web automation specialist.'\n"
                    f"- If need info: Ask specifically what's missing and why\n"
                    f"- If not government service: Explain you only help with Malaysian government services"
                ),
                expected_output="Clear response with appropriate delegation or information request",
                agent=self.main_agent
            )
            
            # Create sequential crew where coordinator can delegate to web automation agent
            processing_crew = Crew(
                agents=[self.main_agent, self.web_automation_agent],
                tasks=[processing_task],
                process=Process.sequential,  # Sequential process allows delegation
                verbose=True
            )
            
            result = processing_crew.kickoff()
            
            # Return the result as a successful response
            return {
                "status": "success",
                "message": str(result),
                "requires_human": False
            }
                
        except Exception as e:
            logger.error(f"Intelligent processing failed: {str(e)}")
            return {
                "status": "error",
                "message": f"I encountered an issue processing your request: {str(e)}. Please try again.",
                "requires_human": True
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get coordinator agent health status."""
        success_rate = (self.successful_requests / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            "status": "healthy" if success_rate >= 80 else "degraded",
            "request_count": self.request_count,
            "successful_requests": self.successful_requests,
            "success_rate": f"{success_rate:.1f}%",
            "agent_type": "intelligent_coordinator",
            "llm_model": "bedrock/amazon.nova-lite-v1:0"
        }
    
    async def execute_automation_task(self, automation_task: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute automation task using the stagehand agent.
        
        Args:
            automation_task: Task prepared for automation
            session_id: Session ID for human interaction (optional)
            
        Returns:
            Result dictionary with status and details
        """
        try:
            logger.info(f"Executing automation task with stagehand agent: {automation_task.get('task_type', 'unknown')}")
            
            # Delegate to stagehand agent for browser automation
            result = self.stagehand_agent.execute_government_task(automation_task)
            
            return {
                "status": "success",
                "message": "Task completed successfully",
                "details": result,
                "requires_human": False
            }
            
        except Exception as e:
            logger.error(f"Stagehand automation task execution failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Automation execution failed: {str(e)}",
                "requires_human": True
            }
    
    async def process_complete_request(self, user_message: str, user_context: Dict[str, Any] = None, 
                                     session_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process complete user request including automation execution with memory.
        
        Args:
            user_message: User's message/request
            user_context: Additional user context (IC, plate number, etc.)
            session_id: Session ID for human interaction and memory tracking
            user_id: User ID for personalization and memory
            
        Returns:
            Complete response dictionary
        """
        try:
            # First, process the request through coordinator with memory
            coordinator_result = await self.process_user_request(
                user_message, user_context, session_id, user_id
            )
            
            # If ready for automation, execute it
            if coordinator_result.get("status") == "ready_for_automation":
                automation_task = coordinator_result.get("automation_task", {})
                automation_result = await self.execute_automation_task(automation_task, session_id)
                
                # Combine results
                return {
                    "status": automation_result.get("status", "error"),
                    "message": automation_result.get("message", "Automation completed"),
                    "details": automation_result.get("details", ""),
                    "requires_human": automation_result.get("requires_human", True),
                    "coordinator_result": coordinator_result,
                    "automation_result": automation_result
                }
            else:
                # Return coordinator result if not ready for automation
                return coordinator_result
                
        except Exception as e:
            logger.error(f"Complete request processing failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Request processing failed: {str(e)}",
                "requires_human": True
            }
    
    async def save_user_entity_memory(self, user_id: str, memory_data: Dict[str, Any]) -> bool:
        """
        Save user-specific entity memory for personalization.
        
        Args:
            user_id: User identifier
            memory_data: Dictionary containing user preferences, service history, etc.
            
        Returns:
            Boolean indicating success
        """
        try:
            return await self.memory_manager.save_user_entity_memory(user_id, memory_data)
        except Exception as e:
            logger.error(f"Failed to save user entity memory: {e}")
            return False
    
    async def get_user_entity_memory(self, user_id: str) -> Optional[Dict]:
        """
        Get user-specific entity memory.
        
        Args:
            user_id: User identifier
            
        Returns:
            User entity memory dictionary or None
        """
        try:
            return await self.memory_manager.get_user_entity_memory(user_id)
        except Exception as e:
            logger.error(f"Failed to get user entity memory: {e}")
            return None
    
    async def update_user_attributes(self, user_id: str, attributes: Dict[str, Any]) -> bool:
        """
        Update specific user attributes.
        
        Args:
            user_id: User identifier
            attributes: Dictionary of attributes to update
            
        Returns:
            Boolean indicating success
        """
        try:
            return await self.memory_manager.update_user_attributes(user_id, attributes)
        except Exception as e:
            logger.error(f"Failed to update user attributes: {e}")
            return False


# Global coordinator instance
coordinator_agent = CoordinatorAgent()
