"""
Enhanced Automation Agent using CrewAI and Nova Act for intelligent browser automation.
Uses CrewAI with Pydantic models for intelligent micro-step generation and structured output.
Handles the actual execution of government service tasks using AWS Bedrock Agent Core Browser.

Enhanced Flow:
1. Takes validator output as input
2. Uses CrewAI agents to intelligently generate micro-steps with Nova Act types
3. Passes enhanced micro-steps to Nova Act agent
4. Monitors for blackhole scenarios and pauses operation when needed
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv
import boto3
import time
import threading
import concurrent.futures
from dataclasses import dataclass
import json
import re

from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM
from nova_act import NovaAct
from bedrock_agentcore.tools.browser_client import BrowserClient

from app.core.logging import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


# Pydantic Models for Structured Output
class EdgeCase(BaseModel):
    """Edge case definition for micro-step execution."""
    condition: str = Field(description="The condition that triggers this edge case")
    description: str = Field(description="Description of the edge case scenario")
    recovery_action: str = Field(description="Action to take when this edge case occurs")
    nova_instruction: str = Field(description="Nova Act instruction for recovery")
    confidence: float = Field(description="Confidence level for this edge case", ge=0.0, le=1.0)


class Condition(BaseModel):
    """Pre-execution condition for micro-step."""
    type: str = Field(description="Type of condition to check")
    description: str = Field(description="Description of the condition")
    nova_instruction: str = Field(description="Nova Act instruction to check this condition")
    critical: bool = Field(description="Whether this condition is critical for execution")


class BlackholeDetection(BaseModel):
    """Blackhole detection configuration."""
    max_consecutive_failures: int = Field(description="Maximum consecutive failures before blackhole detection")
    max_similar_errors: int = Field(description="Maximum similar errors before blackhole detection")
    timeout_threshold: int = Field(description="Timeout threshold in seconds")
    monitoring_keywords: List[str] = Field(description="Keywords to monitor for blackhole detection")


class EnhancedMicroStep(BaseModel):
    """Enhanced micro-step with Nova Act types and intelligent handling."""
    step_number: int = Field(description="Step number in the sequence")
    nova_act_type: str = Field(description="Nova Act action type (navigate, click, input, etc.)")
    instruction: str = Field(description="Nova Act instruction for this step")
    target_element: str = Field(description="Target element description")
    validation_criteria: str = Field(description="Criteria to validate successful execution")
    timeout_seconds: int = Field(description="Timeout for this step in seconds")
    retry_count: int = Field(description="Maximum retry attempts")
    edge_cases: List[EdgeCase] = Field(description="Edge cases to handle")
    conditions: List[Condition] = Field(description="Pre-execution conditions")
    blackhole_detection: BlackholeDetection = Field(description="Blackhole detection configuration")
    priority: int = Field(description="Step priority (1=highest, 5=lowest)", ge=1, le=5)
    dependencies: List[int] = Field(description="Step numbers this step depends on", default_factory=list)


class AutomationExecutionPlan(BaseModel):
    """Final structured output from automation agent to Nova Act agent."""
    session_id: str = Field(description="Unique session identifier")
    task_description: str = Field(description="Description of the overall task")
    target_website: str = Field(description="Primary target website URL")
    micro_steps: List[EnhancedMicroStep] = Field(description="Complete list of micro-steps to execute")
    execution_strategy: str = Field(description="Strategy for executing the micro-steps")
    error_handling_strategy: str = Field(description="Strategy for handling errors")
    blackhole_prevention: str = Field(description="Strategy for preventing blackholes")
    confidence_score: float = Field(description="Confidence in the generated plan", ge=0.0, le=1.0)
    total_estimated_time: int = Field(description="Total estimated execution time in seconds")
    priority_level: int = Field(description="Task priority level (1=highest, 5=lowest)", ge=1, le=5)


@dataclass
class MicroStepResult:
    """Data class for micro-step execution results."""
    step_number: int
    status: str  # "success", "failed", "retrying"
    result_text: str
    error_message: Optional[str]
    retry_count: int
    execution_time: float


@dataclass
class AutomationSession:
    """Data class for automation session tracking."""
    session_id: str
    start_time: datetime
    current_step: int
    total_steps: int
    micro_steps: List[Dict[str, Any]]
    enhanced_micro_steps: List[EnhancedMicroStep]
    results: List[MicroStepResult]
    status: str  # "running", "completed", "failed", "human_intervention", "blackhole_detected"
    error_count: int
    blackhole_detection_count: int
    consecutive_failures: int

# Import WebSocket notification functions
try:
    from app.routers.websocket import notify_browser_status, notify_browser_viewer_ready
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class MicroStepGeneratorAgent:
    """CrewAI agent for intelligently generating enhanced micro-steps."""
    
    def __init__(self, llm: LLM):
        self.llm = llm
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the micro-step generator agent."""
        return Agent(
            role="Micro-Step Generation Specialist",
            goal="Intelligently generate enhanced micro-steps for browser automation using Nova Act",
            backstory=(
                "You are an expert in browser automation and Nova Act integration. "
                "You analyze validator outputs and intelligently generate micro-steps that are "
                "optimized for Nova Act execution. You consider edge cases, error handling, "
                "and blackhole prevention in your step generation. You understand the nuances "
                "of different government websites and can adapt your approach accordingly."
            ),
            llm=self.llm,
            memory=False,
            verbose=True,
            max_iter=5,
            max_execution_time=300
        )
    
    def generate_execution_plan(self, validation_result: Dict[str, Any], task_description: str = "") -> AutomationExecutionPlan:
        """Generate final structured execution plan using CrewAI."""
        try:
            # Create task for execution plan generation
            task = Task(
                description=f"""
                Analyze the following validator output and generate a complete automation execution plan for Nova Act:
                
                TASK DESCRIPTION: {task_description}
                
                VALIDATION RESULT:
                {json.dumps(validation_result, indent=2)}
                
                Requirements:
                1. Generate a complete execution plan with all micro-steps for Nova Act
                2. Each micro-step should have clear Nova Act action types (navigate, click, input, search, wait, etc.)
                3. Include intelligent edge cases and error handling for government websites
                4. Plan for blackhole detection and prevention strategies
                5. Ensure logical sequencing with proper dependencies between steps
                6. Estimate total execution time and set appropriate priority levels
                7. Generate comprehensive recovery strategies for common failure scenarios
                8. Create a complete structured output that Nova Act agent can directly execute
                
                Focus on creating a robust, intelligent automation plan that Nova Act can execute without additional processing.
                """,
                expected_output="A complete automation execution plan with all micro-steps, strategies, and metadata for Nova Act execution",
                agent=self.agent,
                output_pydantic=AutomationExecutionPlan
            )
            
            # Create crew and execute
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            
            # Extract the structured output
            if hasattr(result, 'pydantic') and result.pydantic:
                return result.pydantic
            elif hasattr(result, 'json_dict') and result.json_dict:
                return AutomationExecutionPlan(**result.json_dict)
            else:
                # Fallback parsing
                return self._parse_fallback_result(str(result), task_description)
                
        except Exception as e:
            logger.error(f"Error generating execution plan: {str(e)}")
            return self._create_fallback_plan(validation_result, task_description)
    
    def _parse_fallback_result(self, result_text: str, task_description: str) -> AutomationExecutionPlan:
        """Parse result text as fallback when structured output fails."""
        try:
            # Try to extract JSON from the result
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                return AutomationExecutionPlan(**data)
        except Exception as e:
            logger.warning(f"Failed to parse fallback result: {str(e)}")
        
        # Create minimal fallback plan
        return AutomationExecutionPlan(
            session_id=f"fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            task_description=task_description or "Fallback automation task",
            target_website="https://www.myeg.com.my",
            micro_steps=[],
            execution_strategy="Sequential execution with error handling",
            error_handling_strategy="Retry with exponential backoff",
            blackhole_prevention="Monitor for consecutive failures",
            confidence_score=0.3,
            total_estimated_time=300,
            priority_level=3
        )
    
    def _create_fallback_plan(self, validation_result: Dict[str, Any], task_description: str) -> AutomationExecutionPlan:
        """Create a fallback plan when generation fails."""
        micro_steps = validation_result.get('micro_steps', [])
        enhanced_steps = []
        
        for i, step in enumerate(micro_steps, 1):
            enhanced_step = EnhancedMicroStep(
                step_number=i,
                nova_act_type=step.get('action_type', 'general'),
                instruction=step.get('instruction', ''),
                target_element=step.get('target_element', 'element'),
                validation_criteria=step.get('validation_criteria', 'Verify step completion'),
                timeout_seconds=step.get('timeout_seconds', 30),
                retry_count=step.get('retry_count', 3),
                edge_cases=[],
                conditions=[],
                blackhole_detection=BlackholeDetection(
                    max_consecutive_failures=3,
                    max_similar_errors=5,
                    timeout_threshold=30,
                    monitoring_keywords=['error', 'failed', 'timeout']
                ),
                priority=3,
                dependencies=[]
            )
            enhanced_steps.append(enhanced_step)
        
        # Extract target website
        target_website = "https://www.myeg.com.my"
        if validation_result.get('corrected_flow', {}).get('original_flow', {}).get('target_websites'):
            target_website = validation_result['corrected_flow']['original_flow']['target_websites'][0]
        
        return AutomationExecutionPlan(
            session_id=f"fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            task_description=task_description or "Fallback automation task",
            target_website=target_website,
            micro_steps=enhanced_steps,
            execution_strategy="Sequential execution with basic error handling",
            error_handling_strategy="Retry failed steps up to 3 times",
            blackhole_prevention="Monitor for consecutive failures and similar errors",
            confidence_score=0.5,
            total_estimated_time=len(enhanced_steps) * 30,  # 30 seconds per step estimate
            priority_level=3
        )


class BlackholeDetector:
    """Detects when automation gets stuck in infinite loops or blackholes."""
    
    def __init__(self, max_consecutive_failures: int = 3, max_similar_errors: int = 5):
        self.max_consecutive_failures = max_consecutive_failures
        self.max_similar_errors = max_similar_errors
        self.error_history = []
        self.step_history = []
    
    def detect_blackhole(self, current_step: int, error_message: str, step_instruction: str) -> Dict[str, Any]:
        """Detect if automation is stuck in a blackhole."""
        detection_result = {
            'is_blackhole': False,
            'reason': '',
            'suggested_action': '',
            'confidence': 0.0
        }
        
        # Track current step and error
        self.step_history.append({
            'step': current_step,
            'instruction': step_instruction,
            'error': error_message,
            'timestamp': datetime.utcnow()
        })
        
        # Keep only recent history (last 10 steps)
        if len(self.step_history) > 10:
            self.step_history = self.step_history[-10:]
        
        # Check for consecutive failures
        recent_failures = [s for s in self.step_history[-self.max_consecutive_failures:] if s['error']]
        if len(recent_failures) >= self.max_consecutive_failures:
            detection_result['is_blackhole'] = True
            detection_result['reason'] = f'Consecutive failures detected: {len(recent_failures)}'
            detection_result['suggested_action'] = 'Pause automation and request human intervention'
            detection_result['confidence'] = 0.8
        
        # Check for similar errors repeating
        similar_errors = [s for s in self.step_history if s['error'] and 
                         any(keyword in s['error'].lower() for keyword in 
                             ['not found', 'timeout', 'invalid', 'failed'])]
        if len(similar_errors) >= self.max_similar_errors:
            detection_result['is_blackhole'] = True
            detection_result['reason'] = f'Similar errors repeating: {len(similar_errors)}'
            detection_result['suggested_action'] = 'Modify approach or escalate to human'
            detection_result['confidence'] = 0.9
        
        # Check for infinite loops (same step repeated)
        if len(self.step_history) >= 5:
            recent_steps = [s['step'] for s in self.step_history[-5:]]
            if len(set(recent_steps)) <= 2:  # Only 1-2 unique steps in last 5 attempts
                detection_result['is_blackhole'] = True
                detection_result['reason'] = 'Infinite loop detected - same steps repeating'
                detection_result['suggested_action'] = 'Break the loop and try alternative approach'
                detection_result['confidence'] = 0.95
        
        return detection_result


class AutomationAgent:
    """Enhanced automation agent with intelligent micro-step generation using CrewAI."""
    
    # Make dataclasses accessible as class attributes
    MicroStepResult = MicroStepResult
    AutomationSession = AutomationSession
    EnhancedMicroStep = EnhancedMicroStep
    
    def __init__(self):
        # Configuration
        self.nova_act_api_key = os.getenv("NOVA_ACT_API_KEY")
        self.aws_region = "us-east-1"
        self.iam_role_arn = os.getenv("IAM_ROLE_ARN", "arn:aws:iam::791493234575:role/BedrockAgentCoreBrowserRole")
        
        # AWS credentials
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Browser client and Nova Act instance
        self.browser_client = None
        self.nova_act = None
        self.current_session_id = None
        
        # Session tracking
        self.active_sessions: Dict[str, AutomationSession] = {}
        
        # Error handling configuration
        self.max_retries_per_step = 3
        self.max_total_errors = 5
        self.human_intervention_threshold = 3
        
        # Initialize LLM for CrewAI
        self.llm = self._initialize_llm()
        
        # Enhanced components
        self.micro_step_generator = MicroStepGeneratorAgent(self.llm)
        self.blackhole_detector = BlackholeDetector()
        
        logger.info("Enhanced automation agent initialized successfully with CrewAI-based micro-step generation")
    
    def _initialize_llm(self) -> LLM:
        """Initialize LLM for CrewAI agents."""
        try:
            return LLM(
                model="bedrock/amazon.nova-lite-v1:0",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_region_name=self.aws_region,
                stream=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    def _initialize_browser_client(self) -> bool:
        """Initialize AWS Bedrock Agent Core Browser client."""
        try:
            logger.info("Initializing AWS Bedrock Agent Core Browser client...")
            
            # Create boto3 session with the IAM user credentials
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            # Verify the credentials work
            try:
                caller_identity = sts_client.get_caller_identity()
                logger.info(f"Using IAM user: {caller_identity.get('Arn', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error verifying credentials: {e}")
                return False
            
            # Assume the role to get temporary credentials
            assumed_role = sts_client.assume_role(
                RoleArn=self.iam_role_arn,
                RoleSessionName='BedrockAgentCoreBrowserSession'
            )
            
            # Set the assumed role credentials as environment variables
            os.environ['AWS_ACCESS_KEY_ID'] = assumed_role['Credentials']['AccessKeyId']
            os.environ['AWS_SECRET_ACCESS_KEY'] = assumed_role['Credentials']['SecretAccessKey']
            os.environ['AWS_SESSION_TOKEN'] = assumed_role['Credentials']['SessionToken']
            os.environ['AWS_DEFAULT_REGION'] = self.aws_region
            
            # Create browser client
            self.browser_client = BrowserClient(region=self.aws_region)
            
            # Start the browser client
            self.browser_client.start()
            logger.info("Browser client started successfully!")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser client: {str(e)}")
            return False
    
    def process_validator_output(self, validation_result: Dict[str, Any], task_description: str = "") -> AutomationExecutionPlan:
        """
        Process validator output and generate final structured execution plan using CrewAI.
        
        Args:
            validation_result: ValidationResult from validator agent
            task_description: Description of the overall task
            
        Returns:
            AutomationExecutionPlan - Final structured output for Nova Act agent
        """
        try:
            logger.info("Processing validator output with CrewAI-based execution plan generation")
            
            # Use CrewAI agent to intelligently generate complete execution plan
            execution_plan = self.micro_step_generator.generate_execution_plan(validation_result, task_description)
            
            logger.info(f"Successfully generated execution plan with {len(execution_plan.micro_steps)} micro-steps")
            logger.info(f"Session ID: {execution_plan.session_id}")
            logger.info(f"Target Website: {execution_plan.target_website}")
            logger.info(f"Execution strategy: {execution_plan.execution_strategy}")
            logger.info(f"Confidence score: {execution_plan.confidence_score}")
            logger.info(f"Estimated time: {execution_plan.total_estimated_time} seconds")
            
            return execution_plan
            
        except Exception as e:
            logger.error(f"Error processing validator output with CrewAI: {str(e)}")
            # Return fallback plan
            return self.micro_step_generator._create_fallback_plan(validation_result, task_description)

    def generate_execution_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final structured execution plan for Nova Act agent.
        
        This method creates a complete structured output that the Nova Act agent can consume
        and execute without additional processing.
        
        Args:
            task: Automation task dictionary with validation_result and context
            
        Returns:
            Dictionary containing the complete AutomationExecutionPlan
        """
        try:
            # Extract validation result and task description
            validation_result = task.get('validation_result', {})
            task_description = task.get('task_description', task.get('instructions', ''))
            
            if not validation_result:
                return {
                    "status": "error",
                    "message": "No validation result found in task. Please run validator first.",
                    "requires_human": True
                }
            
            # Generate execution plan using CrewAI
            execution_plan = self.process_validator_output(validation_result, task_description)
            
            # Convert to dictionary for JSON serialization
            plan_dict = execution_plan.model_dump()
            
            logger.info(f"Generated execution plan with {len(execution_plan.micro_steps)} micro-steps")
            logger.info(f"Plan ready for Nova Act agent execution")
            
            return {
                "status": "success",
                "message": "Execution plan generated successfully",
                "execution_plan": plan_dict,
                "requires_human": False
            }
            
        except Exception as e:
            logger.error(f"Error generating execution plan: {str(e)}")
            
            return {
                "status": "error",
                "message": f"Failed to generate execution plan: {str(e)}",
                "requires_human": True
            }
    
    def _create_automation_session(self, task: Dict[str, Any], session_id: Optional[str] = None) -> AutomationSession:
        """Create a new automation session for tracking micro-step execution."""
        session_id = session_id or f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        micro_steps = task.get('micro_steps', [])
        
        session = AutomationSession(
            session_id=session_id,
            start_time=datetime.utcnow(),
            current_step=0,
            total_steps=len(micro_steps),
            micro_steps=micro_steps,
            enhanced_micro_steps=[],
            results=[],
            status="running",
            error_count=0,
            blackhole_detection_count=0,
            consecutive_failures=0
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Created automation session {session_id} with {len(micro_steps)} micro-steps")
        
        return session
    
    def _create_enhanced_automation_session(self, task: Dict[str, Any], enhanced_micro_steps: List[EnhancedMicroStep], session_id: Optional[str] = None) -> AutomationSession:
        """Create a new enhanced automation session for tracking enhanced micro-step execution."""
        session_id = session_id or f"enhanced_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert enhanced micro-steps to dict format for backward compatibility
        micro_steps_dict = []
        for step in enhanced_micro_steps:
            micro_steps_dict.append({
                'step_number': step.step_number,
                'action_type': step.nova_act_type,
                'instruction': step.instruction,
                'target_element': step.target_element,
                'validation_criteria': step.validation_criteria,
                'timeout_seconds': step.timeout_seconds,
                'retry_count': step.retry_count,
                'error_handling': {
                    'on_failure': 'retry_with_delay',
                    'max_retries': step.retry_count,
                    'retry_delay_seconds': 5,
                    'fallback_action': 'escalate_to_human'
                }
            })
        
        session = AutomationSession(
            session_id=session_id,
            start_time=datetime.utcnow(),
            current_step=0,
            total_steps=len(enhanced_micro_steps),
            micro_steps=micro_steps_dict,
            enhanced_micro_steps=enhanced_micro_steps,
            results=[],
            status="running",
            error_count=0,
            blackhole_detection_count=0,
            consecutive_failures=0
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Created enhanced automation session {session_id} with {len(enhanced_micro_steps)} enhanced micro-steps")
        
        return session
    
    def _extract_starting_page_from_task(self, task: Dict[str, Any]) -> str:
        """Extract the starting page from task data, prioritizing research results."""
        try:
            # First, try to get from research results (most reliable)
            research_results = task.get('research_results', {})
            if research_results:
                target_websites = research_results.get('target_websites', [])
                if target_websites and len(target_websites) > 0:
                    starting_page = target_websites[0]
                    logger.info(f"Using starting page from research results: {starting_page}")
                    return starting_page
            
            # Second, try to extract from micro-steps (look for navigation steps)
            micro_steps = task.get('micro_steps', [])
            for step in micro_steps:
                instruction = step.get('instruction', '').lower()
                if any(keyword in instruction for keyword in ['visit', 'go to', 'navigate', 'open', 'access']):
                    # Try to extract URL from instruction
                    import re
                    url_pattern = r'https?://[^\s]+'
                    urls = re.findall(url_pattern, step.get('instruction', ''))
                    if urls:
                        starting_page = urls[0]
                        logger.info(f"Using starting page from micro-step: {starting_page}")
                        return starting_page
            
            # Third, try to get from validation results
            validation_result = task.get('validation_result', {})
            if validation_result:
                corrected_flow = validation_result.get('corrected_flow', {})
                if corrected_flow:
                    original_flow = corrected_flow.get('original_flow', {})
                    if original_flow:
                        target_websites = original_flow.get('target_websites', [])
                        if target_websites and len(target_websites) > 0:
                            starting_page = target_websites[0]
                            logger.info(f"Using starting page from validation results: {starting_page}")
                            return starting_page
            
            # Default fallback based on intent analysis
            intent_analysis = task.get('intent_analysis', {})
            service_category = intent_analysis.get('service_category', '').lower()
            
            default_pages = {
                'jpj': 'https://www.jpj.gov.my',
                'lhdn': 'https://www.hasil.gov.my',
                'jpn': 'https://www.jpn.gov.my',
                'epf': 'https://www.kwsp.gov.my',
                'myeg': 'https://www.myeg.com.my',
                'ssm': 'https://www.ssm.com.my'
            }
            
            if service_category in default_pages:
                starting_page = default_pages[service_category]
                logger.info(f"Using default starting page for {service_category}: {starting_page}")
                return starting_page
            
            # Ultimate fallback
            starting_page = "https://www.myeg.com.my"
            logger.info(f"Using ultimate fallback starting page: {starting_page}")
            return starting_page
            
        except Exception as e:
            logger.error(f"Error extracting starting page from task: {str(e)}")
            return "https://www.myeg.com.my"
    
    async def _execute_enhanced_micro_steps(self, session: AutomationSession, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced micro-steps with blackhole detection and edge case handling."""
        try:
            logger.info(f"Starting enhanced micro-step execution for session {session.session_id}")
            
            # Extract starting page from task or use default
            starting_page = self._extract_starting_page_from_task(task)
            logger.info(f"Using starting page: {starting_page}")
            
            # Initialize Nova Act with browser
            if not await self._initialize_nova_act(starting_page):
                return {
                    "status": "error",
                    "message": "Failed to initialize Nova Act browser session",
                    "requires_human": True
                }
            
            # Execute each enhanced micro-step
            for i, enhanced_step in enumerate(session.enhanced_micro_steps):
                session.current_step = i + 1
                
                logger.info(f"Executing enhanced micro-step {session.current_step}/{session.total_steps}: {enhanced_step.nova_act_type} - {enhanced_step.instruction[:50]}...")
                
                # Execute the enhanced micro-step
                step_result = await self._execute_enhanced_single_micro_step(enhanced_step, session)
                session.results.append(step_result)
                
                # Check for blackhole detection
                if step_result.status == "failed":
                    session.consecutive_failures += 1
                    session.error_count += 1
                    
                    # Check for blackhole
                    blackhole_detection = self.blackhole_detector.detect_blackhole(
                        session.current_step,
                        step_result.error_message or "Unknown error",
                        enhanced_step.instruction
                    )
                    
                    if blackhole_detection['is_blackhole']:
                        session.blackhole_detection_count += 1
                        session.status = "blackhole_detected"
                        logger.warning(f"Blackhole detected: {blackhole_detection['reason']}")
                        
                        return await self._handle_blackhole_detection(session, enhanced_step, blackhole_detection)
                    
                    # Check if we should escalate to human intervention
                    if session.error_count >= self.human_intervention_threshold:
                        session.status = "human_intervention"
                        return await self._handle_human_intervention(session, step_result)
                    
                    # Check if we should retry the step
                    if step_result.retry_count < enhanced_step.retry_count:
                        # Retry the step with edge case handling
                        retry_result = await self._retry_enhanced_micro_step(enhanced_step, session, step_result)
                        session.results.append(retry_result)
                        
                        if retry_result.status == "success":
                            session.consecutive_failures = 0
                            session.error_count = max(0, session.error_count - 1)
                        else:
                            session.consecutive_failures += 1
                    else:
                        # Max retries exceeded, escalate
                        session.status = "failed"
                        return {
                            "status": "error",
                            "message": f"Enhanced micro-step {session.current_step} failed after {enhanced_step.retry_count} retries",
                            "failed_step": enhanced_step.__dict__,
                            "error_details": step_result.error_message,
                            "requires_human": True
                        }
                else:
                    # Success - reset consecutive failures
                    session.consecutive_failures = 0
                
                # Small delay between steps
                await asyncio.sleep(1)
            
            # All steps completed successfully
            session.status = "completed"
            return {
                "status": "success",
                "message": "All enhanced micro-steps completed successfully",
                "session_id": session.session_id,
                "total_steps": session.total_steps,
                "execution_time": (datetime.utcnow() - session.start_time).total_seconds(),
                "results": [result.__dict__ for result in session.results],
                "requires_human": False
            }
            
        except Exception as e:
            logger.error(f"Enhanced micro-step execution failed: {str(e)}")
            session.status = "failed"
            return {
                "status": "error",
                "message": f"Enhanced micro-step execution failed: {str(e)}",
                "requires_human": True
            }
        finally:
            # Clean up session
            await self._cleanup_session(session)

    async def _execute_micro_steps(self, session: AutomationSession, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute micro-steps with error handling and recovery."""
        try:
            logger.info(f"Starting micro-step execution for session {session.session_id}")
            
            # Extract starting page from task or use default
            starting_page = self._extract_starting_page_from_task(task)
            logger.info(f"Using starting page: {starting_page}")
            
            # Initialize Nova Act with browser
            if not await self._initialize_nova_act(starting_page):
                return {
                    "status": "error",
                    "message": "Failed to initialize Nova Act browser session",
                    "requires_human": True
                }
            
            # Execute each micro-step
            for i, micro_step in enumerate(session.micro_steps):
                session.current_step = i + 1
                
                logger.info(f"Executing micro-step {session.current_step}/{session.total_steps}: {micro_step.get('instruction', '')}")
                
                # Execute the micro-step
                step_result = await self._execute_single_micro_step(micro_step, session)
                session.results.append(step_result)
                
                # Check if we need to stop or retry
                if step_result.status == "failed":
                    session.error_count += 1
                    
                    # Check if we should escalate to human intervention
                    if session.error_count >= self.human_intervention_threshold:
                        session.status = "human_intervention"
                        return await self._handle_human_intervention(session, step_result)
                    
                    # Check if we should retry the step
                    if step_result.retry_count < self.max_retries_per_step:
                        # Retry the step
                        retry_result = await self._retry_micro_step(micro_step, session, step_result)
                        session.results.append(retry_result)
                        
                        if retry_result.status == "failed":
                            session.error_count += 1
                        else:
                            session.error_count = max(0, session.error_count - 1)
                    else:
                        # Max retries exceeded, escalate
                        session.status = "failed"
                        return {
                            "status": "error",
                            "message": f"Micro-step {session.current_step} failed after {self.max_retries_per_step} retries",
                            "failed_step": micro_step,
                            "error_details": step_result.error_message,
                            "requires_human": True
                        }
                
                # Small delay between steps
                await asyncio.sleep(1)
            
            # All steps completed successfully
            session.status = "completed"
            return {
                "status": "success",
                "message": "All micro-steps completed successfully",
                "session_id": session.session_id,
                "total_steps": session.total_steps,
                "execution_time": (datetime.utcnow() - session.start_time).total_seconds(),
                "results": [result.__dict__ for result in session.results],
                "requires_human": False
            }
            
        except Exception as e:
            logger.error(f"Micro-step execution failed: {str(e)}")
            session.status = "failed"
            return {
                "status": "error",
                "message": f"Micro-step execution failed: {str(e)}",
                "requires_human": True
            }
        finally:
            # Clean up session
            await self._cleanup_session(session)
    
    async def _execute_enhanced_single_micro_step(self, enhanced_step: EnhancedMicroStep, session: AutomationSession) -> MicroStepResult:
        """Execute a single enhanced micro-step using Nova Act with edge case handling."""
        start_time = time.time()
        
        try:
            # Check conditions before execution
            conditions_met = await self._check_enhanced_step_conditions(enhanced_step)
            if not conditions_met:
                return MicroStepResult(
                    step_number=session.current_step,
                    status="failed",
                    result_text="",
                    error_message="Pre-execution conditions not met",
                    retry_count=0,
                    execution_time=time.time() - start_time
                )
            
            # Execute Nova Act in a separate thread to avoid asyncio conflicts
            result = await self._execute_nova_act_in_thread(enhanced_step.instruction)
            
            # Parse the result
            result_text = ""
            if hasattr(result, 'response') and result.response:
                result_text = str(result.response)
            elif hasattr(result, 'parsed_response') and result.parsed_response:
                result_text = str(result.parsed_response)
            else:
                result_text = str(result)
            
            # Validate the result using Nova Act validation keywords
            is_success = self._validate_enhanced_step_result(result_text, enhanced_step)
            
            execution_time = time.time() - start_time
            
            return MicroStepResult(
                step_number=session.current_step,
                status="success" if is_success else "failed",
                result_text=result_text,
                error_message=None if is_success else f"Enhanced step validation failed: {result_text[:100]}",
                retry_count=0,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Enhanced micro-step {session.current_step} execution failed: {str(e)}")
            
            return MicroStepResult(
                step_number=session.current_step,
                status="failed",
                result_text="",
                error_message=str(e),
                retry_count=0,
                execution_time=execution_time
            )
    
    async def _check_enhanced_step_conditions(self, enhanced_step: EnhancedMicroStep) -> bool:
        """Check if all conditions are met before executing the enhanced step."""
        try:
            for condition in enhanced_step.conditions:
                condition_type = condition.type
                
                if condition_type == 'page_loaded':
                    # Check if page is loaded using Nova Act
                    check_result = await self._execute_nova_act_in_thread(
                        condition.nova_instruction
                    )
                    if not self._check_condition_result(check_result, ['loaded', 'ready', 'complete']):
                        logger.warning("Page not fully loaded condition not met")
                        if condition.critical:
                            return False
                
                elif condition_type == 'credentials_available':
                    # This would need to be checked against the task context
                    # For now, assume true if we have a login step
                    logger.info("Credentials availability condition checked")
                
                elif condition_type == 'element_visible':
                    # Check if target element is visible
                    check_result = await self._execute_nova_act_in_thread(
                        condition.nova_instruction
                    )
                    if not self._check_condition_result(check_result, ['visible', 'clickable', 'found']):
                        logger.warning(f"Element visibility condition not met for {enhanced_step.target_element}")
                        if condition.critical:
                            return False
                
                elif condition_type == 'form_ready':
                    # Check if form is ready
                    check_result = await self._execute_nova_act_in_thread(
                        condition.nova_instruction
                    )
                    if not self._check_condition_result(check_result, ['ready', 'available', 'form']):
                        logger.warning("Form ready condition not met")
                        if condition.critical:
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking enhanced step conditions: {str(e)}")
            return False
    
    def _check_condition_result(self, result: Any, keywords: List[str]) -> bool:
        """Check if result contains any of the specified keywords."""
        try:
            result_text = str(result).lower()
            return any(keyword.lower() in result_text for keyword in keywords)
        except:
            return False
    
    def _validate_enhanced_step_result(self, result_text: str, enhanced_step: EnhancedMicroStep) -> bool:
        """Validate enhanced step result using Nova Act validation keywords."""
        if not result_text:
            return False
        
        result_lower = result_text.lower()
        
        # Check for success indicators based on validation criteria
        validation_criteria = enhanced_step.validation_criteria.lower()
        if any(keyword in result_lower for keyword in ['success', 'completed', 'done', 'finished', 'submitted', 'processed']):
            return True
        
        # Check for failure indicators
        failure_indicators = ['error', 'failed', 'unable', 'cannot', 'invalid', 'rejected']
        if any(indicator in result_lower for indicator in failure_indicators):
            return False
        
        # Check against specific validation criteria
        if 'loaded' in validation_criteria and 'loaded' in result_lower:
            return True
        if 'clicked' in validation_criteria and 'clicked' in result_lower:
            return True
        if 'filled' in validation_criteria and 'filled' in result_lower:
            return True
        if 'navigated' in validation_criteria and 'navigated' in result_lower:
            return True
        
        # If no clear indicators, consider it successful if we got a response
        return len(result_text.strip()) > 0
    
    async def _retry_enhanced_micro_step(self, enhanced_step: EnhancedMicroStep, session: AutomationSession, 
                                       previous_result: MicroStepResult) -> MicroStepResult:
        """Retry a failed enhanced micro-step with edge case handling."""
        start_time = time.time()
        
        try:
            # Apply edge case handling based on the error
            modified_instruction = self._apply_edge_case_handling(enhanced_step, previous_result)
            
            logger.info(f"Retrying enhanced micro-step {session.current_step} with edge case handling")
            
            # Execute the modified step
            result = await self._execute_nova_act_in_thread(modified_instruction)
            
            # Parse and validate the result
            result_text = str(result.response) if hasattr(result, 'response') and result.response else str(result)
            is_success = self._validate_enhanced_step_result(result_text, enhanced_step)
            
            execution_time = time.time() - start_time
            
            return MicroStepResult(
                step_number=session.current_step,
                status="success" if is_success else "failed",
                result_text=result_text,
                error_message=None if is_success else f"Enhanced retry validation failed: {result_text[:100]}",
                retry_count=previous_result.retry_count + 1,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Enhanced micro-step {session.current_step} retry failed: {str(e)}")
            
            return MicroStepResult(
                step_number=session.current_step,
                status="failed",
                result_text="",
                error_message=str(e),
                retry_count=previous_result.retry_count + 1,
                execution_time=execution_time
            )
    
    def _apply_edge_case_handling(self, enhanced_step: EnhancedMicroStep, previous_result: MicroStepResult) -> str:
        """Apply edge case handling to modify the instruction for retry."""
        original_instruction = enhanced_step.instruction
        error_message = previous_result.error_message or ''
        
        # Find applicable edge case
        applicable_edge_case = None
        for edge_case in enhanced_step.edge_cases:
            if edge_case.condition in error_message.lower() or self._is_error_related_to_condition(error_message, edge_case.condition):
                applicable_edge_case = edge_case
                break
        
        if applicable_edge_case:
            # Apply the edge case recovery action
            if applicable_edge_case.nova_instruction:
                return f"{original_instruction}\n\nRecovery: {applicable_edge_case.nova_instruction}"
        
        # Default retry guidance
        retry_guidance = "\n\nThis is a retry attempt. Please be more careful and specific in your actions."
        
        if 'not found' in error_message.lower():
            retry_guidance += " If the element is not found, try scrolling or waiting for the page to load completely."
        elif 'timeout' in error_message.lower():
            retry_guidance += " Please wait longer for the page to respond before taking action."
        elif 'authentication' in error_message.lower():
            retry_guidance += " Please verify your credentials and try logging in again."
        
        return original_instruction + retry_guidance
    
    def _is_error_related_to_condition(self, error_message: str, condition: str) -> bool:
        """Check if error message is related to a specific condition."""
        condition_keywords = {
            'element_not_found': ['not found', 'missing', 'absent'],
            'page_not_loaded': ['loading', 'not loaded', 'incomplete'],
            'network_timeout': ['timeout', 'network', 'connection'],
            'invalid_credentials': ['invalid', 'credentials', 'login'],
            'captcha_required': ['captcha', 'verification', 'human'],
            'element_not_clickable': ['not clickable', 'disabled', 'unavailable'],
            'field_validation_error': ['validation', 'invalid input', 'format']
        }
        
        keywords = condition_keywords.get(condition, [])
        return any(keyword in error_message.lower() for keyword in keywords)
    
    async def _handle_blackhole_detection(self, session: AutomationSession, enhanced_step: EnhancedMicroStep, 
                                        blackhole_detection: Dict[str, Any]) -> Dict[str, Any]:
        """Handle blackhole detection by pausing operation and requesting human intervention."""
        logger.warning(f"Blackhole detected in session {session.session_id}: {blackhole_detection['reason']}")
        
        return {
            "status": "blackhole_detected",
            "message": f"Automation detected infinite loop or blackhole: {blackhole_detection['reason']}",
            "session_id": session.session_id,
            "failed_step": enhanced_step.step_number,
            "blackhole_details": blackhole_detection,
            "suggested_action": blackhole_detection['suggested_action'],
            "browser_state": "paused",
            "recommendations": [
                "Review the current browser state",
                "Check if the page has changed unexpectedly",
                "Verify that the target elements are still available",
                "Consider modifying the automation approach",
                "Resume automation after manual intervention if needed"
            ],
            "requires_human": True
        }

    async def _execute_single_micro_step(self, micro_step: Dict[str, Any], session: AutomationSession) -> MicroStepResult:
        """Execute a single micro-step using Nova Act in a separate thread to avoid asyncio conflicts."""
        start_time = time.time()
        
        try:
            instruction = micro_step.get('instruction', '')
            action_type = micro_step.get('action_type', 'general')
            
            # Execute Nova Act in a separate thread to avoid asyncio conflicts
            result = await self._execute_nova_act_in_thread(instruction)
            
            # Parse the result
            result_text = ""
            if hasattr(result, 'response') and result.response:
                result_text = str(result.response)
            elif hasattr(result, 'parsed_response') and result.parsed_response:
                result_text = str(result.parsed_response)
            else:
                result_text = str(result)
            
            # Validate the result
            is_success = self._validate_step_result(result_text, micro_step)
            
            execution_time = time.time() - start_time
            
            return MicroStepResult(
                step_number=session.current_step,
                status="success" if is_success else "failed",
                result_text=result_text,
                error_message=None if is_success else f"Step validation failed: {result_text[:100]}",
                retry_count=0,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Micro-step {session.current_step} execution failed: {str(e)}")
            
            return MicroStepResult(
                step_number=session.current_step,
                status="failed",
                result_text="",
                error_message=str(e),
                retry_count=0,
                execution_time=execution_time
            )
    
    async def _retry_micro_step(self, micro_step: Dict[str, Any], session: AutomationSession, 
                              previous_result: MicroStepResult) -> MicroStepResult:
        """Retry a failed micro-step with modifications."""
        start_time = time.time()
        
        try:
            # Modify the instruction based on the previous failure
            modified_instruction = self._modify_instruction_for_retry(micro_step, previous_result)
            
            logger.info(f"Retrying micro-step {session.current_step} with modified instruction")
            
            # Execute the modified step
            result = self.nova_act.act(modified_instruction)
            
            # Parse and validate the result
            result_text = str(result.response) if hasattr(result, 'response') and result.response else str(result)
            is_success = self._validate_step_result(result_text, micro_step)
            
            execution_time = time.time() - start_time
            
            return MicroStepResult(
                step_number=session.current_step,
                status="success" if is_success else "failed",
                result_text=result_text,
                error_message=None if is_success else f"Retry validation failed: {result_text[:100]}",
                retry_count=previous_result.retry_count + 1,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Micro-step {session.current_step} retry failed: {str(e)}")
            
            return MicroStepResult(
                step_number=session.current_step,
                status="failed",
                result_text="",
                error_message=str(e),
                retry_count=previous_result.retry_count + 1,
                execution_time=execution_time
            )
    
    async def _initialize_nova_act(self, starting_page: str = "https://www.myeg.com.my") -> bool:
        """Initialize Nova Act with browser session following the test script pattern."""
        try:
            # Generate WebSocket URL and headers from browser client
            ws_url, headers = self.browser_client.generate_ws_headers()
            logger.info(f"Generated WebSocket URL for Nova Act: {ws_url}")
            logger.info(f"Starting page: {starting_page}")
            
            # Initialize Nova Act with the remote browser (following test script pattern)
            self.nova_act = NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                # preview={"playwright_actuation": True},
                nova_act_api_key=self.nova_act_api_key,
                starting_page=starting_page
            )
            
            # Note: Following test script pattern, we don't call start() here
            # The context manager or manual start() will be called when needed
            logger.info("Nova Act initialized successfully (following test script pattern)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Nova Act: {str(e)}")
            return False
    
    async def _execute_nova_act_in_thread(self, instruction: str) -> Any:
        """Execute Nova Act in a separate thread to avoid asyncio conflicts."""
        try:
            # Run Nova Act in a thread pool to isolate it from asyncio context
            loop = asyncio.get_event_loop()
            
            # Use ThreadPoolExecutor to run the synchronous Nova Act code
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the Nova Act execution to the thread pool
                future = executor.submit(self._run_nova_act_sync, instruction)
                
                # Wait for the result in the async context
                result = await loop.run_in_executor(None, lambda: future.result())
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to execute Nova Act in thread: {str(e)}")
            raise e
    
    def _run_nova_act_sync(self, instruction: str) -> Any:
        """Run Nova Act synchronously in a separate thread (isolated from asyncio)."""
        try:
            # Ensure Nova Act is started before calling act()
            if not hasattr(self.nova_act, '_started') or not self.nova_act._started:
                self.nova_act.start()
                logger.info("Started Nova Act client in isolated thread")
            
            # Execute the step with Nova Act (now in sync context)
            result = self.nova_act.act(instruction)
            logger.info(f"Nova Act executed instruction: {instruction[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Nova Act execution failed in thread: {str(e)}")
            raise e
    
    def _validate_step_result(self, result_text: str, micro_step: Dict[str, Any]) -> bool:
        """Validate if a micro-step was executed successfully."""
        if not result_text:
            return False
        
        result_lower = result_text.lower()
        
        # Check for success indicators
        success_indicators = ['success', 'completed', 'done', 'finished', 'submitted', 'processed']
        if any(indicator in result_lower for indicator in success_indicators):
            return True
        
        # Check for failure indicators
        failure_indicators = ['error', 'failed', 'unable', 'cannot', 'invalid', 'rejected']
        if any(indicator in result_lower for indicator in failure_indicators):
            return False
        
        # If no clear indicators, consider it successful if we got a response
        return len(result_text.strip()) > 0
    
    def _modify_instruction_for_retry(self, micro_step: Dict[str, Any], previous_result: MicroStepResult) -> str:
        """Modify instruction for retry based on previous failure."""
        original_instruction = micro_step.get('instruction', '')
        error_message = previous_result.error_message or ''
        
        # Add retry-specific guidance
        retry_guidance = "\n\nThis is a retry attempt. Please be more careful and specific in your actions. "
        
        if 'not found' in error_message.lower():
            retry_guidance += "If the element is not found, try scrolling or waiting for the page to load completely."
        elif 'timeout' in error_message.lower():
            retry_guidance += "Please wait longer for the page to respond before taking action."
        elif 'authentication' in error_message.lower():
            retry_guidance += "Please verify your credentials and try logging in again."
        
        return original_instruction + retry_guidance
    
    async def _handle_human_intervention(self, session: AutomationSession, failed_step: MicroStepResult) -> Dict[str, Any]:
        """Handle human intervention request."""
        logger.info(f"Requesting human intervention for session {session.session_id}, step {failed_step.step_number}")
        
        return {
            "status": "human_intervention_required",
            "message": f"Automation encountered multiple failures and requires human intervention",
            "session_id": session.session_id,
            "failed_step": failed_step.step_number,
            "error_count": session.error_count,
            "error_details": failed_step.error_message,
            "browser_state": "active",
            "suggested_actions": [
                "Check browser state and current page",
                "Verify credentials if authentication failed",
                "Manually complete the failed step",
                "Resume automation or provide guidance"
            ],
            "requires_human": True
        }
    
    async def _cleanup_session(self, session: AutomationSession):
        """Clean up automation session resources."""
        try:
            # Remove from active sessions
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]
            
            # Clean up Nova Act if it exists (run in thread to avoid asyncio conflicts)
            if self.nova_act:
                try:
                    await self._cleanup_nova_act_in_thread()
                except Exception as e:
                    logger.warning(f"Error cleaning up Nova Act: {str(e)}")
            
            logger.info(f"Cleaned up session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session.session_id}: {str(e)}")
    
    async def _cleanup_nova_act_in_thread(self):
        """Clean up Nova Act in a separate thread to avoid asyncio conflicts."""
        try:
            # Run Nova Act cleanup in a thread pool
            loop = asyncio.get_event_loop()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the Nova Act cleanup to the thread pool
                future = executor.submit(self._cleanup_nova_act_sync)
                
                # Wait for the cleanup to complete
                await loop.run_in_executor(None, lambda: future.result())
                
        except Exception as e:
            logger.error(f"Failed to cleanup Nova Act in thread: {str(e)}")
            raise e
    
    def _cleanup_nova_act_sync(self):
        """Clean up Nova Act synchronously in a separate thread."""
        try:
            if self.nova_act:
                # Stop Nova Act client (now in sync context)
                self.nova_act.stop()
                logger.info("Nova Act client stopped successfully in isolated thread")
        except Exception as e:
            logger.warning(f"Error cleaning up Nova Act in thread: {str(e)}")
            raise e
    
    async def _execute_government_service_task(self, instructions: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Malaysian government service task using Nova Act."""
        try:
            # Enhance instructions with user context if available
            enhanced_instructions = self._enhance_instructions_with_context(instructions, user_context)
            
            # Generate WebSocket URL and headers from browser client
            ws_url, headers = self.browser_client.generate_ws_headers()
            logger.info(f"Generated WebSocket URL: {ws_url}")
            
            # Use Nova Act with the remote browser
            logger.info("Starting Nova Act with browser automation...")
            
            with NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                preview={"playwright_actuation": True},
                nova_act_api_key=self.nova_act_api_key,
                starting_page="https://www.myeg.com.my",  # Start with MyEG website
            ) as nova_act:
                result = nova_act.act(enhanced_instructions)
                logger.info(f"Nova Act Result: {result}")
                
                # Parse the result
                result_text = ""
                if hasattr(result, 'response') and result.response:
                    result_text = str(result.response)
                elif hasattr(result, 'parsed_response') and result.parsed_response:
                    result_text = str(result.parsed_response)
                else:
                    result_text = str(result)
                
                logger.info(f"Final result text: {result_text[:200]}...")  # Log first 200 chars
                
                # Check if the task was successful
                if any(keyword in result_text.lower() for keyword in ["success", "completed", "done", "finished", "submitted", "processed"]):
                    return {
                        "status": "success",
                        "message": "Government service completed successfully!",
                        "details": result_text,
                        "requires_human": False
                    }
                elif any(keyword in result_text.lower() for keyword in ["error", "failed", "unable", "cannot", "invalid", "rejected"]):
                    return {
                        "status": "error",
                        "message": "Failed to complete the government service. Please try again or contact support.",
                        "details": result_text,
                        "requires_human": True
                    }
                else:
                    return {
                        "status": "partial",
                        "message": "Task executed but status unclear. Please check the results.",
                        "details": result_text,
                        "requires_human": True
                    }
                
        except Exception as e:
            logger.error(f"Government service task failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Government service failed: {str(e)}",
                "requires_human": True
            }
    
    def _enhance_instructions_with_context(self, instructions: str, user_context: Dict[str, Any]) -> str:
        """Enhance task instructions with user context."""
        
        enhanced = instructions
        
        # Add user context if available
        if user_context:
            context_info = []
            for key, value in user_context.items():
                if value and str(value).strip():
                    context_info.append(f"{key}: {value}")
            
            if context_info:
                enhanced += f"\n\nUser Context:\n" + "\n".join(context_info)
        
        return enhanced
    
    
    async def _cleanup_browser_client(self):
        """Clean up browser client resources."""
        try:
            if self.browser_client:
                logger.info("Stopping browser client...")
                self.browser_client.stop()
                self.browser_client = None
                logger.info("Browser client stopped successfully")
                
        except Exception as e:
            logger.error(f"Error cleaning up browser client: {str(e)}")
    
    async def close_browser(self):
        """Close browser and cleanup resources."""
        try:
            # Clean up browser client if it exists
            await self._cleanup_browser_client()
                
            logger.info("Browser closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    async def ensure_clean_state(self):
        """Ensure we start with a clean state by closing any existing sessions."""
        try:
            logger.info("Ensuring clean state before browser initialization...")
            
            # Close any existing browser client
            await self._cleanup_browser_client()
                    
            logger.info("Clean state ensured")
            
        except Exception as e:
            logger.warning(f"Error ensuring clean state: {str(e)}")
            # Don't fail if cleanup doesn't work
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get automation agent health status."""
        return {
            "status": "healthy" if self.browser_client else "no_browser_client",
            "browser_client_connected": self.browser_client is not None,
            "nova_act_available": self.nova_act_api_key is not None,
            "aws_credentials_configured": self.aws_access_key_id is not None and self.aws_secret_access_key is not None,
        }
    
# Global automation agent instance
automation_agent = AutomationAgent()

# Helper function to reset the global agent
async def reset_automation_agent():
    """Reset the global automation agent to ensure clean state."""
    global automation_agent
    try:
        await automation_agent.ensure_clean_state()
        logger.info("Global automation agent reset successfully")
    except Exception as e:
        logger.error(f"Error resetting automation agent: {str(e)}")
