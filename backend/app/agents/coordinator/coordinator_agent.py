"""
Enhanced Coordinator Agent using CrewAI for government service automation.
Implements Phase 1 of the 3-agent architecture with:
- Chain-of-thought prompting for dynamic intent detection
- Enhanced Tavily research capabilities
- Memory management integration
- Foundation for Validator and Automation agent handoffs
"""

import asyncio
import os
import time
import json
import uuid
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError
from crewai import Agent, Task, Crew, Process, LLM
from crewai.memory.short_term.short_term_memory import ShortTermMemory
from crewai.memory.entity.entity_memory import EntityMemory
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.config import settings
from .tavily_tool import TavilySearchTool
from ..validator.validator_agent import ValidatorAgent, validator_agent
from ..automation.automation_agent import AutomationAgent, automation_agent
from ..automation.nova_act_agent import NovaActAgent, nova_act_agent

logger = get_logger(__name__)


@dataclass
class IntentAnalysis:
    """Data class for intent analysis results."""
    intent_type: str
    service_category: str
    confidence_score: float
    requires_research: bool
    requires_credentials: bool
    missing_information: List[str]
    suggested_next_steps: List[str]
    reasoning: str


@dataclass
class ResearchResults:
    """Data class for research results."""
    target_websites: List[str]
    process_steps: List[str]
    required_credentials: List[str]
    required_information: List[str]
    research_confidence: float
    research_summary: str


class ChainOfThoughtPrompting:
    """Chain-of-thought prompting utilities for enhanced reasoning."""
    
    @staticmethod
    def create_intent_detection_prompt(user_message: str, context: Dict[str, Any] = None) -> str:
        """Create a chain-of-thought prompt for intent detection."""
        context_str = ""
        if context:
            context_items = [f"{k}: {v}" for k, v in context.items() if v]
            if context_items:
                context_str = f"\n\nUser Context:\n" + "\n".join(context_items)
        
        return f"""You are an expert coordinator for Malaysian government services. Analyze the user request using chain-of-thought reasoning.

USER REQUEST: "{user_message}"{context_str}

Think step by step:

1. **Intent Analysis**:
   - What is the user trying to accomplish?
   - What type of government service is involved?
   - Is this a payment, inquiry, registration, renewal, or other type of request?
   
2. **Service Categorization**:
   - Which government department/agency is involved? (JPJ, LHDN, JPN, EPF, MyEG, etc.)
   - What specific service or process is being requested?
   
3. **Information Requirements**:
   - What information does the user need to provide?
   - What credentials (login, IC, etc.) are required?
   - What information is missing that needs to be requested?
   
4. **Process Complexity**:
   - How complex is this request?
   - Does it require research to understand the process?
   - Can it be handled directly or needs delegation?
   
5. **Next Steps Planning**:
   - Should this be researched first using web search?
   - Should credentials be requested from the user?
   - Should this be delegated to a specialist agent?

Based on your analysis, provide a structured response in JSON format:
{{
    "intent_type": "payment|inquiry|registration|renewal|other",
    "service_category": "jpj|lhdn|jpn|epf|myeg|other",
    "confidence_score": 0.95,
    "requires_research": true/false,
    "requires_credentials": true/false,
    "missing_information": ["list of missing info"],
    "suggested_next_steps": ["list of next actions"],
    "reasoning": "your detailed reasoning process"
}}"""
    
    @staticmethod
    def create_research_prompt(user_message: str, intent_analysis: IntentAnalysis, 
                              context: Dict[str, Any] = None) -> str:
        """Create a research-focused prompt for Tavily integration."""
        context_str = ""
        if context:
            context_items = [f"{k}: {v}" for k, v in context.items() if v]
            if context_items:
                context_str = f"\n\nUser Context:\n" + "\n".join(context_items)
        
        return f"""You are a research specialist for Malaysian government services. Based on the intent analysis, research the specific process.

USER REQUEST: "{user_message}"
INTENT ANALYSIS: {intent_analysis.reasoning}{context_str}

Research Requirements:
1. **Target Website Identification**:
   - Find the official website(s) for this service
   - Verify the correct URL and service path
   - Identify any portal or login requirements
   
2. **Process Documentation**:
   - Find step-by-step instructions
   - Identify required forms or documents
   - Understand payment methods and requirements
   
3. **Prerequisites and Requirements**:
   - What credentials are needed (login, IC, etc.)
   - What information must be provided
   - Any fees or payment requirements
   
4. **Common Issues and Solutions**:
   - Typical problems users face
   - Troubleshooting steps
   - Alternative approaches if needed

Use the tavily_search tool to research this information. Focus on official government websites and trusted sources.

After research, provide a comprehensive summary in JSON format:
{{
    "target_websites": ["list of official websites"],
    "process_steps": ["step-by-step process"],
    "required_credentials": ["list of needed credentials"],
    "required_information": ["list of needed information"],
    "research_confidence": 0.95,
    "research_summary": "detailed summary of findings"
}}"""
    
    @staticmethod
    def create_delegation_prompt(intent_analysis: IntentAnalysis, research_results: ResearchResults,
                               user_message: str, context: Dict[str, Any] = None) -> str:
        """Create a delegation prompt for passing to validator agent."""
        context_str = ""
        if context:
            context_items = [f"{k}: {v}" for k, v in context.items() if v]
            if context_items:
                context_str = f"\n\nUser Context:\n" + "\n".join(context_items)
        
        return f"""You are coordinating a Malaysian government service request. Based on your analysis and research, prepare instructions for the Validator Agent.

USER REQUEST: "{user_message}"
INTENT: {intent_analysis.intent_type} - {intent_analysis.service_category}
CONFIDENCE: {intent_analysis.confidence_score}{context_str}

RESEARCH FINDINGS:
{research_results.research_summary}

VALIDATION REQUIREMENTS:
1. **URL Validation**:
   - Verify target websites are correct and accessible
   - Check if URLs lead to the right service pages
   - Validate SSL certificates and security
   
2. **Process Validation**:
   - Verify the step-by-step process is complete
   - Check for any missing steps or information
   - Validate credential requirements
   
3. **Automation Readiness**:
   - Determine if this can be automated
   - Identify potential automation challenges
   - Plan micro-step breakdown for Nova Act

4. **Missing Information**:
   - Identify what still needs to be requested from user
   - Plan credential collection if needed
   - Determine human intervention requirements

Provide clear instructions for the Validator Agent to process this request."""


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
        """Retrieve conversation history for context from the crewai-memory table."""
        try:
            from boto3.dynamodb.conditions import Key
            
            response = self.table.query(
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
                    
                    user_message = safe_get(item, 'user_message')
                    agent_response = safe_get(item, 'agent_response')
                    timestamp = safe_get(item, 'timestamp')
                    user_id = safe_get(item, 'user_id')
                    
                    # Convert DynamoDB format to our expected format
                    conv_item = {
                        'user_message': user_message,
                        'agent_response': agent_response,
                        'role': 'conversation',  # Combined user/agent conversation
                        'timestamp': timestamp,
                        'user_id': user_id
                    }
                    
                    # Only add if there's actual content
                    if conv_item['user_message'] or conv_item['agent_response']:
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
    """Enhanced coordinator agent with chain-of-thought prompting and 3-agent architecture support."""
    
    def __init__(self):
        # Initialize LLM with enhanced settings for reasoning
        self.llm = self._initialize_llm()
        
        # Initialize memory manager
        self.memory_manager = DynamoDBMemoryManager()
        
        # Initialize chain-of-thought prompting utilities
        self.cot_prompting = ChainOfThoughtPrompting()
        
        # Initialize tools
        try:
            self.tavily_tool = TavilySearchTool()
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily tool: {str(e)}")
            self.tavily_tool = None
        
        # Initialize stagehand agent for direct delegation (temporary)
        
        # Initialize validator agent
        self.validator_agent = validator_agent
        
        # Initialize automation agent
        self.automation_agent = automation_agent
        
        # Initialize Nova Act agent
        self.nova_act_agent = nova_act_agent
        
        # Initialize coordinator agent with enhanced prompting
        self.main_agent = self._create_enhanced_agent()
        
        # Initialize intent detection agent
        self.intent_agent = self._create_intent_agent()
        
        # Initialize research agent
        self.research_agent = self._create_research_agent()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 3.0
        
        # Request tracking
        self.request_count = 0
        self.successful_requests = 0
        
        logger.info("Enhanced coordinator agent with chain-of-thought prompting initialized successfully")
    
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
                aws_region_name=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),  # Use Bedrock region
                stream=True  # Enable streaming for real-time responses
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    def _create_enhanced_agent(self) -> Agent:
        """Create the enhanced coordinator agent with chain-of-thought capabilities."""
        tools = [self.tavily_tool] if self.tavily_tool else []
        
        return Agent(
            role="Malaysian Government Service Coordinator",
            goal="Intelligently coordinate Malaysian government service requests using chain-of-thought reasoning and dynamic intent detection",
            backstory=(
                "You are an advanced coordinator for Malaysian government services with enhanced reasoning capabilities. "
                "You use chain-of-thought prompting to deeply understand user requests and dynamically detect their intent "
                "without relying on predefined categories. You think step-by-step to analyze requests, determine "
                "information needs, and coordinate with specialist agents.\n\n"
                
                "Your enhanced process:\n"
                "1. **Intent Detection**: Use chain-of-thought reasoning to analyze user requests\n"
                "2. **Research Coordination**: Delegate research tasks when needed using Tavily\n"
                "3. **Information Gathering**: Identify and request missing information or credentials\n"
                "4. **Task Delegation**: Coordinate with Validator and Automation agents\n"
                "5. **Process Monitoring**: Track progress and handle escalations\n\n"
                
                "You excel at understanding complex government service requests and breaking them down into "
                "manageable tasks for specialist agents while maintaining context and ensuring accuracy."
            ),
            tools=tools,
            llm=self.llm,
            memory=False,
            verbose=True,
            allow_delegation=True,
            max_iter=15,
            max_execution_time=900
        )
    
    def _create_intent_agent(self) -> Agent:
        """Create a specialized agent for intent detection using chain-of-thought reasoning."""
        return Agent(
            role="Intent Analysis Specialist",
            goal="Analyze user requests using chain-of-thought reasoning to dynamically detect intent and requirements",
            backstory=(
                "You are a specialist in understanding user intent for Malaysian government services. "
                "You use advanced reasoning techniques to analyze requests without relying on predefined categories. "
                "You think step-by-step to understand what users really want and what they need to accomplish "
                "their goals. You excel at identifying missing information and determining the best next steps."
            ),
            llm=self.llm,
            memory=False,
            verbose=True,
            max_iter=5,
            max_execution_time=300
        )
    
    def _create_research_agent(self) -> Agent:
        """Create a specialized agent for research using Tavily integration."""
        tools = [self.tavily_tool] if self.tavily_tool else []
        
        return Agent(
            role="Government Service Research Specialist",
            goal="Research Malaysian government services using web search to gather accurate process information",
            backstory=(
                "You are a research specialist focused on Malaysian government services. "
                "You use web search to find accurate, up-to-date information about government processes, "
                "requirements, and procedures. You focus on official government websites and trusted sources "
                "to ensure the information you provide is reliable and current."
            ),
            tools=tools,
            llm=self.llm,
            memory=False,
            verbose=True,
            max_iter=8,
            max_execution_time=600
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
                user_entity_memory,
                session_id
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
                                         user_entity_memory: Dict = None,
                                         session_id: str = None) -> Dict[str, Any]:
        """
        Enhanced request processing using chain-of-thought reasoning and 3-agent architecture.
        """
        try:
            # Build memory context
            memory_context = self._build_memory_context(conversation_history, user_entity_memory)
            
            # Step 1: Intent Detection using Chain-of-Thought
            intent_analysis = await self._detect_intent(user_message, user_context, memory_context)
            
            # Step 2: AI-Driven Decision Making for Request Handling
            if self._should_handle_directly(intent_analysis, user_message):
                return await self._handle_casual_request(intent_analysis, user_message, memory_context)
            
            # Step 3: Research if needed
            research_results = None
            if intent_analysis.requires_research:
                research_results = await self._conduct_research(user_message, intent_analysis, user_context, memory_context)
            
            # Step 4: Handle missing information
            if intent_analysis.missing_information:
                return await self._handle_missing_information(intent_analysis, research_results)
            
            # Step 5: Extract credentials from user message for automation
            extracted_credentials = await self._extract_credentials_from_message(user_message, user_context)
            
            # Step 6: Validate task flow using Validator Agent (only for government service requests)
            validation_result = await self.validator_agent.validate_task_flow(
                coordinator_instructions="",
                intent_analysis=intent_analysis.__dict__,
                research_results=research_results.__dict__ if research_results else None
            )
            
            # Step 7: Prepare for delegation to Automation Agent
            delegation_instructions = await self._prepare_delegation(intent_analysis, research_results, validation_result, user_message, user_context)
            
            # Step 8: Execute automation task using Automation Agent with extracted credentials
            automation_task = {
                'delegation_instructions': delegation_instructions,
                'micro_steps': validation_result.micro_steps,
                'error_handling_plan': validation_result.error_handling_plan,
                'monitoring_points': validation_result.monitoring_points,
                'user_context': user_context,
                'user_message': user_message,  # Pass user message directly
                'extracted_credentials': extracted_credentials,  # Pass extracted credentials
                'intent_analysis': intent_analysis.__dict__,
                'research_results': research_results.__dict__ if research_results else None,
                'validation_result': validation_result.__dict__
            }
            
            # Stage 1: Generate execution plan using Automation Agent
            logger.info("Stage 1: Generating execution plan with Automation Agent...")
            execution_plan_result = self.automation_agent.generate_execution_plan(automation_task)
            
            if execution_plan_result["status"] != "success":
                logger.error(f"Failed to generate execution plan: {execution_plan_result['message']}")
                return {
                    "status": "error",
                    "message": f"Failed to generate automation plan: {execution_plan_result['message']}",
                    "intent_analysis": intent_analysis,
                    "research_results": research_results,
                    "validation_result": validation_result,
                    "requires_human": True
                }
            
            # Stage 2: Execute the plan using Nova Act Agent
            logger.info("Stage 2: Executing plan with Nova Act Agent...")
            execution_plan = execution_plan_result["execution_plan"]
            nova_act_result = self.nova_act_agent.execute_execution_plan(execution_plan)
            
            # Stage 3: Process Nova Act result and determine next action
            logger.info("Stage 3: Processing Nova Act result...")
            automation_task = {
                "task_description": automation_task.get("task_description", ""),
                "target_website": execution_plan.get("target_website", ""),
                "validation_result": validation_result
            }
            
            processed_result = self.automation_agent.process_nova_act_result(nova_act_result, automation_task)
            
            # Handle different actions based on processed result
            action = processed_result.get("action", "inform_user")
            
            if action == "improve_and_retry":
                # Automation agent has improved the plan, retry with improved execution plan
                logger.info("Retrying with improved execution plan from automation agent...")
                
                improved_execution_plan = processed_result.get("improved_execution_plan")
                if not improved_execution_plan:
                    logger.error("No improved execution plan provided by automation agent")
                    return {
                        "status": "error",
                        "message": "Failed to get improved execution plan from automation agent",
                        "intent_analysis": intent_analysis,
                        "research_results": research_results,
                        "validation_result": validation_result,
                        "nova_act_result": nova_act_result,
                        "processed_result": processed_result,
                        "requires_human": True
                    }
                
                # Execute the improved plan with Nova Act Agent
                logger.info("Executing improved plan with Nova Act Agent...")
                retry_nova_act_result = self.nova_act_agent.execute_execution_plan(improved_execution_plan)
                
                # Process the retry result
                retry_processed_result = self.automation_agent.process_nova_act_result(retry_nova_act_result, automation_task)
                
                # Handle the retry result
                retry_action = retry_processed_result.get("action", "inform_user")
                
                if retry_action == "inform_user":
                    return {
                        "status": "success",
                        "message": "Automation completed successfully after plan improvement!",
                        "intent_analysis": intent_analysis,
                        "research_results": research_results,
                        "validation_result": validation_result,
                        "nova_act_result": retry_nova_act_result,
                        "processed_result": retry_processed_result,
                        "improvement_applied": True,
                        "requires_human": False
                    }
                elif retry_action == "return_tutorial":
                    return {
                        "status": "tutorial",
                        "message": "Automation failed even after plan improvement. Here's a tutorial to help you:",
                        "tutorial": retry_processed_result.get("tutorial", "No tutorial available"),
                        "intent_analysis": intent_analysis,
                        "research_results": research_results,
                        "validation_result": validation_result,
                        "nova_act_result": retry_nova_act_result,
                        "processed_result": retry_processed_result,
                        "improvement_applied": True,
                        "requires_human": True
                    }
                else:
                    # If retry also suggests improvement, we'll stop here to avoid infinite loops
                    logger.warning("Retry also suggests improvement, stopping to avoid infinite loops")
                    return {
                        "status": "partial",
                        "message": "Automation partially completed after one improvement attempt. Further improvement needed.",
                        "intent_analysis": intent_analysis,
                        "research_results": research_results,
                        "validation_result": validation_result,
                        "nova_act_result": retry_nova_act_result,
                        "processed_result": retry_processed_result,
                        "improvement_applied": True,
                        "requires_human": True
                    }
            elif action == "return_tutorial":
                return {
                    "status": "tutorial",
                    "message": processed_result.get("message", "Here's a tutorial to help you:"),
                    "tutorial": processed_result.get("tutorial", "No tutorial available"),
                    "intent_analysis": intent_analysis,
                    "research_results": research_results,
                    "validation_result": validation_result,
                    "nova_act_result": nova_act_result,
                    "requires_human": True
                }
            else:  # inform_user
                return {
                    "status": processed_result.get("status", "success"),
                    "message": processed_result.get("message", "Automation completed successfully"),
                    "intent_analysis": intent_analysis,
                    "research_results": research_results,
                    "validation_result": validation_result,
                    "nova_act_result": nova_act_result,
                    "processed_result": processed_result,
                    "requires_human": processed_result.get("requires_human", False)
                }
                
        except Exception as e:
            logger.error(f"Enhanced processing failed: {str(e)}")
            return {
                "status": "error",
                "message": f"I encountered an issue processing your request: {str(e)}. Please try again.",
                "requires_human": True
            }
    
    def _build_memory_context(self, conversation_history: List[Dict] = None, 
                            user_entity_memory: Dict = None) -> str:
        """Build memory context string from conversation history and entity memory."""
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
            
        return memory_context
    
    async def _extract_credentials_from_message(self, user_message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract credentials from user message using AI-powered analysis.
        
        Args:
            user_message: User's natural language message
            user_context: Additional context information
            
        Returns:
            Dictionary with extracted credentials
        """
        try:
            # Create a specialized AI agent for credential extraction
            credential_agent = self._create_credential_extraction_agent()
            
            # Create task for credential extraction
            task = Task(
                description=f"""
                Analyze the following user message and context to extract any credentials or personal information that might be needed for government service automation.
                
                USER MESSAGE: "{user_message}"
                
                ADDITIONAL CONTEXT: {user_context}
                
                CREDENTIAL TYPES TO LOOK FOR:
                1. Email addresses (login credentials)
                2. Passwords (login credentials) 
                3. IC numbers (Malaysian identity card numbers)
                4. Phone numbers
                5. Names (full names, usernames)
                6. Any other personal information that might be needed for authentication
                
                EXTRACTION RULES:
                - Look for Malaysian IC numbers in formats: 123456-12-1234 or 123456121234
                - Look for email addresses in standard format
                - Look for phone numbers (Malaysian format preferred)
                - Extract names and usernames
                - Be conservative - only extract information that is clearly provided
                - If information is mentioned but not provided, don't extract it
                
                IMPORTANT: Only extract information that is explicitly provided in the message or context. Do not make assumptions.
                
                Return your response as a JSON object with the following structure:
                {{
                    "email": "extracted email if found",
                    "password": "extracted password if found", 
                    "ic_number": "extracted IC number if found",
                    "phone": "extracted phone number if found",
                    "name": "extracted name if found",
                    "confidence": 0.95,
                    "extraction_notes": "brief notes about what was found"
                }}
                
                If no credentials are found, return an empty object: {{}}
                """,
                expected_output="JSON object with extracted credentials or empty object if none found",
                agent=credential_agent
            )
            
            # Execute the task
            crew = Crew(
                agents=[credential_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False  # Keep quiet for production
            )
            
            result = crew.kickoff()
            
            # Parse the JSON response
            import json
            import re
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', str(result), re.DOTALL)
            if json_match:
                json_str = json_match.group()
                credentials = json.loads(json_str)
                
                # Remove empty values and confidence/notes fields
                credentials = {k: v for k, v in credentials.items() 
                             if v and k not in ['confidence', 'extraction_notes']}
                
                logger.info(f"Extracted credentials from user message: {list(credentials.keys())}")
                return credentials
            else:
                logger.warning("Could not parse JSON from credential extraction")
                return {}
                
        except Exception as e:
            logger.error(f"Error in credential extraction: {str(e)}")
            return {}
    
    def _create_credential_extraction_agent(self) -> Agent:
        """Create a specialized AI agent for credential extraction."""
        return Agent(
            role="Credential Extraction Specialist",
            goal="Intelligently extract personal information and credentials from natural language text for government service automation",
            backstory="""You are an expert at analyzing natural language text to extract personal information and credentials. 
            You understand various formats of personal information including Malaysian IC numbers, email addresses, 
            phone numbers, and names. You are conservative in your extraction - only extracting information that is 
            clearly and explicitly provided. You understand the context of government service automation and know 
            what types of information are typically needed for authentication and service access.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
    
    def _should_handle_directly(self, intent_analysis: IntentAnalysis, user_message: str) -> bool:
        """
        Use AI-driven decision making to determine if request should be handled directly.
        This replaces rule-based logic with intelligent analysis.
        """
        # Create an AI agent to make this decision intelligently
        decision_agent = Agent(
            role="Request Classification Specialist",
            goal="Intelligently classify user requests to determine the best handling approach",
            backstory=(
                "You are an expert at analyzing user requests and determining whether they should be "
                "handled directly with a simple response or require deeper processing through the "
                "government service workflow. You consider context, intent, and user needs."
            ),
            llm=self.llm,
            memory=False,
            verbose=False,
            max_iter=3,
            max_execution_time=30
        )
        
        # Create a task for intelligent decision making
        decision_task = Task(
            description=f"""
            Analyze this user request and intent analysis to determine if it should be handled directly:
            
            USER MESSAGE: "{user_message}"
            
            INTENT ANALYSIS:
            - Type: {intent_analysis.intent_type}
            - Category: {intent_analysis.service_category}
            - Confidence: {intent_analysis.confidence_score}
            - Requires Research: {intent_analysis.requires_research}
            - Requires Credentials: {intent_analysis.requires_credentials}
            - Missing Information: {intent_analysis.missing_information}
            - Reasoning: {intent_analysis.reasoning}
            
            DECISION CRITERIA:
            - Handle directly if: Simple greeting, basic question, or non-government request
            - Process through workflow if: Government service request, requires research, or needs credentials
            
            Respond with only "DIRECT" or "PROCESS" based on your analysis.
            """,
            expected_output="Either 'DIRECT' or 'PROCESS'",
            agent=decision_agent
        )
        
        # Execute the decision
        decision_crew = Crew(
            agents=[decision_agent],
            tasks=[decision_task],
            process=Process.sequential,
            verbose=False
        )
        
        try:
            result = decision_crew.kickoff()
            decision = str(result).strip().upper()
            logger.info(f"AI Decision for '{user_message}': {decision}")
            return decision == "DIRECT"
        except Exception as e:
            logger.error(f"AI decision making failed: {e}")
            # Fallback to intent analysis
            return (intent_analysis.intent_type == "other" and 
                   intent_analysis.service_category == "other" and
                   intent_analysis.confidence_score < 0.5)
    
    async def _handle_casual_request(self, intent_analysis: IntentAnalysis, user_message: str, memory_context: str) -> Dict[str, Any]:
        """
        Handle casual greetings and non-government requests with intelligent AI-driven responses.
        """
        # Create an AI agent for intelligent casual response generation
        casual_agent = Agent(
            role="Friendly Government Service Assistant",
            goal="Provide warm, helpful responses to casual greetings while guiding users toward government services",
            backstory=(
                "You are a friendly and professional assistant for Malaysian government services. "
                "You respond warmly to casual greetings while naturally guiding users toward "
                "government service assistance. You're helpful, knowledgeable, and encouraging."
            ),
            llm=self.llm,
            memory=False,
            verbose=False,
            max_iter=2,
            max_execution_time=20
        )
        
        # Create a task for intelligent response generation
        response_task = Task(
            description=f"""
            Generate a warm, helpful response to this user message. The user seems to be making casual conversation.
            
            USER MESSAGE: "{user_message}"
            INTENT ANALYSIS: {intent_analysis.reasoning}
            
            GUIDELINES:
            - Be warm and friendly
            - Acknowledge their message appropriately
            - Gently guide them toward government service assistance
            - Keep it conversational but professional
            - If they mentioned government services (even casually), acknowledge that interest
            - Keep response concise (1-2 sentences)
            
            Generate a natural, helpful response.
            """,
            expected_output="A warm, helpful response that acknowledges the user and guides them toward government services",
            agent=casual_agent
        )
        
        # Execute the response generation
        response_crew = Crew(
            agents=[casual_agent],
            tasks=[response_task],
            process=Process.sequential,
            verbose=False
        )
        
        try:
            result = response_crew.kickoff()
            response = str(result).strip()
            logger.info(f"Generated casual response: {response}")
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            # Fallback response
            response = "Hello! I'm here to assist you with Malaysian government service requests. How can I help you today?"
        
        return {
            "status": "success",
            "message": response,
            "intent_analysis": intent_analysis,
            "research_results": None,
            "validation_result": None,
            "requires_human": False,
            "response_type": "casual_greeting"
        }
    
    async def _detect_intent(self, user_message: str, user_context: Dict[str, Any], 
                           memory_context: str) -> IntentAnalysis:
        """Detect user intent using chain-of-thought reasoning."""
        try:
            # Create chain-of-thought prompt
            prompt = self.cot_prompting.create_intent_detection_prompt(user_message, user_context)
            
            # Create intent detection task
            intent_task = Task(
                description=prompt,
                expected_output="JSON response with intent analysis including reasoning",
                agent=self.intent_agent
            )
            
            # Execute intent detection
            intent_crew = Crew(
                agents=[self.intent_agent],
                tasks=[intent_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = intent_crew.kickoff()
            
            # Parse the JSON response
            intent_data = self._parse_intent_response(str(result))
            
            # Create IntentAnalysis object
            return IntentAnalysis(
                intent_type=intent_data.get('intent_type', 'unknown'),
                service_category=intent_data.get('service_category', 'unknown'),
                confidence_score=float(intent_data.get('confidence_score', 0.0)),
                requires_research=bool(intent_data.get('requires_research', False)),
                requires_credentials=bool(intent_data.get('requires_credentials', False)),
                missing_information=intent_data.get('missing_information', []),
                suggested_next_steps=intent_data.get('suggested_next_steps', []),
                reasoning=intent_data.get('reasoning', '')
            )
            
        except Exception as e:
            logger.error(f"Intent detection failed: {str(e)}")
            # Return default intent analysis
            return IntentAnalysis(
                intent_type='unknown',
                service_category='unknown',
                confidence_score=0.0,
                requires_research=True,
                requires_credentials=False,
                missing_information=['Unable to analyze intent'],
                suggested_next_steps=['Please provide more details'],
                reasoning=f'Intent detection failed: {str(e)}'
            )
    
    async def _conduct_research(self, user_message: str, intent_analysis: IntentAnalysis, 
                              user_context: Dict[str, Any], memory_context: str) -> ResearchResults:
        """Conduct research using Tavily integration."""
        try:
            # Create research prompt
            prompt = self.cot_prompting.create_research_prompt(user_message, intent_analysis, user_context)
            
            # Create research task
            research_task = Task(
                description=prompt,
                expected_output="JSON response with research findings and process details",
                agent=self.research_agent
            )
            
            # Execute research
            research_crew = Crew(
                agents=[self.research_agent],
                tasks=[research_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = research_crew.kickoff()
            
            # Parse the JSON response
            research_data = self._parse_research_response(str(result))
            
            # Create ResearchResults object
            return ResearchResults(
                target_websites=research_data.get('target_websites', []),
                process_steps=research_data.get('process_steps', []),
                required_credentials=research_data.get('required_credentials', []),
                required_information=research_data.get('required_information', []),
                research_confidence=float(research_data.get('research_confidence', 0.0)),
                research_summary=research_data.get('research_summary', '')
            )
            
        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            # Return default research results
            return ResearchResults(
                target_websites=[],
                process_steps=[],
                required_credentials=[],
                required_information=[],
                research_confidence=0.0,
                research_summary=f'Research failed: {str(e)}'
            )
    
    async def _handle_missing_information(self, intent_analysis: IntentAnalysis, 
                                        research_results: ResearchResults = None) -> Dict[str, Any]:
        """Handle requests that need additional information from the user."""
        missing_info = intent_analysis.missing_information
        
        # Build response message
        response_parts = []
        response_parts.append("I understand you want to proceed with this government service request.")
        
        if research_results and research_results.research_summary:
            response_parts.append(f"\nBased on my research: {research_results.research_summary}")
        
        if missing_info:
            response_parts.append("\nTo proceed, I need the following information:")
            for info in missing_info:
                response_parts.append(f"• {info}")
        
        if intent_analysis.requires_credentials:
            response_parts.append("\nI will also need your login credentials for the relevant government portal.")
        
        response_parts.append("\nPlease provide this information so I can assist you with your request.")
        
        return {
            "status": "information_required",
            "message": "\n".join(response_parts),
            "missing_information": missing_info,
            "requires_credentials": intent_analysis.requires_credentials,
            "intent_analysis": intent_analysis,
            "research_results": research_results,
                "requires_human": False
            }
                
    async def _prepare_delegation(self, intent_analysis: IntentAnalysis, 
                                research_results: ResearchResults,
                                validation_result, user_message: str, user_context: Dict[str, Any]) -> str:
        """Prepare delegation instructions for the Automation Agent."""
        # Create enhanced delegation prompt with validation results
        prompt = f"""
You are coordinating a Malaysian government service request. Based on your analysis, research, and validation, prepare instructions for the Automation Agent.

USER REQUEST: "{user_message}"
INTENT: {intent_analysis.intent_type} - {intent_analysis.service_category}
CONFIDENCE: {intent_analysis.confidence_score}

RESEARCH FINDINGS:
{research_results.research_summary if research_results else 'No research conducted'}

VALIDATION RESULTS:
Status: {validation_result.validation_status}
Confidence: {validation_result.confidence_score}
Details: {validation_result.validation_details}

MICRO-STEPS PREPARED:
{len(validation_result.micro_steps)} micro-steps have been prepared for automation

AUTOMATION INSTRUCTIONS:
1. Execute the prepared micro-steps in sequence
2. Monitor each step for success/failure
3. Handle errors according to the error handling plan
4. Escalate to human intervention if needed

Provide clear, actionable instructions for the Automation Agent to execute this government service request.
"""
        
        # Create delegation task
        delegation_task = Task(
            description=prompt,
            expected_output="Clear instructions for the Automation Agent to execute the government service request",
            agent=self.main_agent
        )
        
        # Execute delegation preparation
        delegation_crew = Crew(
            agents=[self.main_agent],
            tasks=[delegation_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = delegation_crew.kickoff()
        return str(result)
    
    def _parse_intent_response(self, response_text: str) -> Dict[str, Any]:
        """Parse intent detection response from JSON."""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback parsing
                return self._fallback_parse_intent(response_text)
        except Exception as e:
            logger.error(f"Failed to parse intent response: {str(e)}")
            return self._fallback_parse_intent(response_text)
    
    def _parse_research_response(self, response_text: str) -> Dict[str, Any]:
        """Parse research response from JSON."""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback parsing
                return self._fallback_parse_research(response_text)
        except Exception as e:
            logger.error(f"Failed to parse research response: {str(e)}")
            return self._fallback_parse_research(response_text)
    
    def _fallback_parse_intent(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing for intent response."""
        return {
            'intent_type': 'unknown',
            'service_category': 'unknown',
            'confidence_score': 0.5,
            'requires_research': True,
            'requires_credentials': False,
            'missing_information': ['Unable to parse intent'],
            'suggested_next_steps': ['Manual analysis required'],
            'reasoning': response_text[:500]
        }
    
    def _fallback_parse_research(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing for research response."""
        return {
            'target_websites': [],
            'process_steps': [],
            'required_credentials': [],
            'required_information': [],
            'research_confidence': 0.5,
            'research_summary': response_text[:500]
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
    
    
    async def process_complete_request(self, user_message: str, user_context: Dict[str, Any] = None, 
                                     session_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process complete user request with CrewAI delegation handling everything internally.
        
        Args:
            user_message: User's message/request
            user_context: Additional user context (IC, plate number, etc.)
            session_id: Session ID for human interaction and memory tracking
            user_id: User ID for personalization and memory
            
        Returns:
            Complete response dictionary
        """
        try:
            # Process the request through coordinator with CrewAI delegation
            # The coordinator now handles delegation internally via CrewAI
            return await self.process_user_request(
                user_message, user_context, session_id, user_id
            )
                
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
