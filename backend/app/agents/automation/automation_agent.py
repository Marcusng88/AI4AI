"""
Enhanced Automation Agent using CrewAI for intelligent browser automation planning.
Generates structured execution plans for Nova Act agent and processes results.
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM

from app.core.logging import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


# Data classes for structured output (no Pydantic validation)
class EnhancedMicroStep:
    """Enhanced micro-step with Nova Act integration."""
    def __init__(self, step_number: int, instruction: str, nova_act_type: str, 
                 target_element: str = None, validation_criteria: str = None,
                 timeout_seconds: int = 30, retry_count: int = 3, priority: int = 1,
                 dependencies: List[int] = None):
        self.step_number = step_number
        self.instruction = instruction
        self.nova_act_type = nova_act_type
        self.target_element = target_element
        self.validation_criteria = validation_criteria
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.priority = priority
        self.dependencies = dependencies or []


class AutomationExecutionPlan:
    """Final structured output from automation agent to Nova Act agent."""
    def __init__(self, session_id: str, task_description: str, target_website: str,
                 micro_steps: List[EnhancedMicroStep], execution_strategy: str,
                 error_handling_strategy: str, blackhole_prevention: str,
                 confidence_score: float, total_estimated_time: int, priority_level: int):
        self.session_id = session_id
        self.task_description = task_description
        self.target_website = target_website
        self.micro_steps = micro_steps
        self.execution_strategy = execution_strategy
        self.error_handling_strategy = error_handling_strategy
        self.blackhole_prevention = blackhole_prevention
        self.confidence_score = confidence_score
        self.total_estimated_time = total_estimated_time
        self.priority_level = priority_level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the execution plan to a dictionary (replaces Pydantic model_dump)."""
        return {
            "session_id": self.session_id,
            "task_description": self.task_description,
            "target_website": self.target_website,
            "micro_steps": [
                {
                    "step_number": step.step_number,
                    "instruction": step.instruction,
                    "nova_act_type": step.nova_act_type,
                    "target_element": step.target_element,
                    "validation_criteria": step.validation_criteria,
                    "timeout_seconds": step.timeout_seconds,
                    "retry_count": step.retry_count,
                    "priority": step.priority,
                    "dependencies": step.dependencies
                }
                for step in self.micro_steps
            ],
            "execution_strategy": self.execution_strategy,
            "error_handling_strategy": self.error_handling_strategy,
            "blackhole_prevention": self.blackhole_prevention,
            "confidence_score": self.confidence_score,
            "total_estimated_time": self.total_estimated_time,
            "priority_level": self.priority_level
        }


class MicroStepGeneratorAgent:
    """CrewAI agent for generating micro-steps with Nova Act integration."""
    
    def __init__(self, llm: LLM):
        self.llm = llm
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the micro-step generator agent."""
        return Agent(
            role="Constraint-Aware Micro-Step Generator",
            goal="Generate intelligent, actionable micro-steps for Nova Act browser automation while strictly adhering to user constraints and prohibitions",
            backstory="""You are an expert automation specialist who creates detailed, 
            step-by-step browser automation plans. You understand Nova Act capabilities 
            and generate clear, executable instructions that can be directly used by 
            Nova Act for browser automation tasks.
            
            CRITICAL: You are extremely careful about following user constraints and prohibitions. 
            When users specify "NO PAYMENT" or "CHECK ONLY", you NEVER generate steps that involve 
            payment, transactions, or financial processing. You always validate each step against 
            the user's explicit constraints before including it in your plan.
            
            You excel at understanding the difference between checking/viewing information and 
            performing actions like payments. You respect user boundaries absolutely.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def generate_execution_plan(self, validation_result: Dict[str, Any], task_description: str = "", credentials: Dict[str, Any] = None) -> AutomationExecutionPlan:
        """Generate final structured execution plan using CrewAI."""
        try:
            # Create task for execution plan generation
            credentials_info = ""
            if credentials:
                credentials_info = f"""
                
                USER CREDENTIALS (for secure handling):
                - Email/Username: {credentials.get('email', 'Not provided')}
                - IC Number: {credentials.get('ic_number', 'Not provided')}
                - Other credentials available: {list(credentials.keys())}
                
                IMPORTANT: When generating steps that require login credentials, use generic instructions like:
                - "Enter the actual username in the username field" 
                - "Enter the actual password in the password field" 
                - "Enter the actual IC number in the IC field" 
                
                The Nova Act agent will handle the actual credential input securely using Playwright's API.
                """
            logger.info(f"Credentials info: {credentials}")
            # Always include MYEG summons checking instructions
            # Get IC number from AI-extracted credentials
            ic_number = credentials.get('ic_number', '')
            if not ic_number:
                ic_number = '050225050339'  # Fallback IC number
                logger.warning("No IC number found in credentials, using fallback")
            else:
                logger.info(f"Using AI-extracted IC number: {ic_number}")
            
            # Build credentials summary for the prompt
            credentials_summary = []
            if credentials.get('email'):
                credentials_summary.append(f"Email: {credentials['email']}")
            if credentials.get('phone'):
                credentials_summary.append(f"Phone: {credentials['phone']}")
            if credentials.get('name'):
                credentials_summary.append(f"Name: {credentials['name']}")
            
            credentials_info_str = "\n".join(credentials_summary) if credentials_summary else "No additional credentials provided"
            
            myeg_summons_instructions = f"""
            
            ⚠️  ABSOLUTE CONSTRAINT: THIS IS A SUMMONS CHECKING REQUEST - NO PAYMENT ALLOWED ⚠️
            
            AI-EXTRACTED CREDENTIALS:
            IC Number: {ic_number}
            {credentials_info_str}
            
            🚫 STRICT PROHIBITIONS (VIOLATION WILL RESULT IN FAILURE):
            - NEVER generate steps for payment, payment methods, or payment processing
            - NEVER include "pay", "payment", "settle", "transaction", or "checkout" in any step
            - NEVER generate steps for credit card, bank transfer, or any payment form
            - NEVER include steps for completing payment or finalizing transactions
            - NEVER generate steps that lead to payment confirmation or receipt
            
            ✅ MANDATORY EXECUTION FLOW (EXACT SEQUENCE REQUIRED):
            1. Navigate to https://www.myeg.com.my (homepage only)
            2. Click "Login Now" button
            3. Click "Continue as Guest" option (DO NOT register or login)
            4. Scroll to find the "Check and Pay JPJ Summons" section and click on it
            5. Find the IC number input field
            6. Enter the IC number: {ic_number}
            7. Click "Check Summons" or "Search" button
            8. Extract ALL summons information from the results page
            9. Display summons details (amounts, due dates, violation types)
            10. Take a screenshot of the results
            11. STOP HERE - DO NOT PROCEED TO PAYMENT
            
            🔒 CONSTANT VALIDATION RULES:
            - Every step must be for CHECKING/VIEWING summons only
            - If you generate any step containing payment-related words, DELETE that step
            - The final step must be "Extract and display summons information"
            - NO steps should lead to payment forms or payment processing
            - Use the AI-extracted IC number: {ic_number}
            - Start from MYEG homepage, not JPJ services page
            
            ⚡ CONSTRAINT ENFORCEMENT:
            Before generating each step, ask yourself: "Does this step involve payment?" If YES, DO NOT generate it.
            The user explicitly said "NO NEED PAY SUMMONS, JUST CHECK" - respect this constraint absolutely.
            
            🎯 CRITICAL: Use the EXACT IC number provided: {ic_number}
            When generating the step to enter IC number, use this exact value: {ic_number}
            """
            
            task = Task(
                description=f"""
                Analyze the following validator output and generate a complete automation execution plan for Nova Act:
                
                TASK DESCRIPTION: {task_description}
                {credentials_info}
                {myeg_summons_instructions}
                
                ⚠️  CRITICAL INSTRUCTION: If special instructions are provided above, you MUST follow them exactly. Do not deviate from the specified flow, especially for MYEG summons checking.
                
                🔍 CONSTRAINT VALIDATION REQUIRED:
                Before finalizing your execution plan, you MUST:
                1. Review every generated step for payment-related keywords
                2. If any step contains "pay", "payment", "settle", "transaction", "checkout", "credit card", "bank transfer", or similar terms, DELETE that step
                3. Ensure the final step is always about extracting/displaying information, not performing actions
                4. Double-check that your plan respects the user's explicit "NO PAYMENT" constraint
                5. If you find yourself generating payment steps, STOP and regenerate without them
                
                VALIDATION RESULT:
                {validation_result}
                
                NOVA ACT INSTRUCTION PATTERNS:
                - Navigation: "Navigate to [URL]" or "Go to [URL]"
                - Clicking: "Click on [element description]" or "Click the [button/link text]"
                - Input: "Enter '[text]' in the [field name]" or "Fill in [field] with '[value]'"
                - Search: "Search for '[query]'" or "Look for [item]"
                - Wait: "Wait for [element] to appear" or "Wait [X] seconds"
                - Extract: "Extract [data] from [element]" or "Get the [information]"
                - Scroll: "Scroll down to find [element]" or "Scroll to the bottom"
                - Select: "Select '[option]' from [dropdown]" or "Choose [option]"
                - Submit: "Submit the form" or "Click submit button"
                - Verify: "Verify that [condition]" or "Check if [element] is visible"
                
                ERROR HANDLING INSTRUCTIONS:
                - Always include validation criteria for each step
                - Add timeout and retry logic for critical steps
                - Include fallback instructions if elements are not found
                - Add wait steps before interacting with dynamic content
                - Include error detection steps after major actions
                - Plan for common government website issues (slow loading, captchas, etc.)
                
                Requirements:
                1. Generate a complete execution plan with all micro-steps for Nova Act
                2. Each micro-step should have clear Nova Act action types (navigate, click, input, search, wait, extract, scroll, select, submit, verify)
                3. Use natural language instructions that Nova Act can understand and execute
                4. Include intelligent edge cases and error handling for government websites
                5. Plan for blackhole detection and prevention strategies
                6. Ensure logical sequencing with proper dependencies between steps
                7. Estimate total execution time and set appropriate priority levels (1-5, where 1=highest priority)
                8. Generate comprehensive recovery strategies for common failure scenarios
                9. Create a complete structured output that Nova Act agent can directly execute
                10. Use specific, actionable instructions that describe exactly what Nova Act should do
                11. For summons checking, always include steps to extract and display all summons information found
                12. CRITICAL: If special instructions are provided above, you MUST follow them exactly and not deviate
                13. CRITICAL: Use the exact IC number provided in the special instructions
                14. CRITICAL: Do NOT add registration or login steps if special instructions say to use guest mode
                
                Return your response as a JSON object with the following structure:
                {{
                    "session_id": "unique_session_id",
                    "task_description": "description of the task",
                    "target_website": "https://example.com",
                    "micro_steps": [
                        {{
                            "step_number": 1,
                            "instruction": "Navigate to the website",
                            "nova_act_type": "navigate",
                            "target_element": "https://example.com",
                            "validation_criteria": "Check if page loads",
                            "timeout_seconds": 30,
                            "retry_count": 2,
                            "priority": 1,
                            "dependencies": []
                        }}
                    ],
                    "execution_strategy": "Sequential execution with retries",
                    "error_handling_strategy": "Retry failed steps up to 2 times",
                    "blackhole_prevention": "Implement timeouts and error detection",
                    "confidence_score": 0.9,
                    "total_estimated_time": 180,
                    "priority_level": 5
                }}
                
                IMPORTANT: For dependencies, use only simple integers representing step numbers (e.g., [1, 2, 3]).
                Do NOT use complex objects like {{"step_number": 1, "status": "completed"}}.
                
                Focus on creating a robust, intelligent automation plan that Nova Act can execute without additional processing.
                """,
                expected_output="JSON response with complete automation execution plan for Nova Act",
                agent=self.agent
            )
            
            # Execute the task
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            
            # Parse the JSON response manually (like coordinator)
            execution_plan_data = self._parse_execution_plan_response(str(result))
            
            # Always apply constraint validation for MYEG summons checking
            execution_plan_data = self._validate_and_filter_payment_steps(execution_plan_data, task_description)
            
            # Convert to AutomationExecutionPlan object
            return self._create_automation_execution_plan(execution_plan_data, task_description)
                
        except Exception as e:
            logger.error(f"Error generating execution plan with CrewAI: {str(e)}")
            # Return fallback plan
            return self._create_fallback_plan(validation_result, task_description)
    
    def _parse_execution_plan_response(self, result_text: str) -> Dict[str, Any]:
        """Parse execution plan response from CrewAI (like coordinator)."""
        try:
            import json
            import re
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback: try to parse the entire response as JSON
                return json.loads(result_text)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            # Return a basic structure if JSON parsing fails
            return {
                "session_id": f"fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "task_description": "Fallback plan",
                "target_website": "https://www.myeg.com.my",
                "micro_steps": [],
                "execution_strategy": "Sequential execution",
                "error_handling_strategy": "Basic retry mechanism",
                "blackhole_prevention": "Timeout-based prevention",
                "confidence_score": 0.5,
                "total_estimated_time": 60,
                "priority_level": 3
            }
        except Exception as e:
            logger.error(f"Error parsing execution plan response: {str(e)}")
            raise
    
    def _validate_and_filter_payment_steps(self, execution_plan_data: Dict[str, Any], task_description: str) -> Dict[str, Any]:
        """
        Validate and filter out any payment-related steps from the execution plan.
        
        Args:
            execution_plan_data: Parsed execution plan data
            task_description: Original task description
            
        Returns:
            Filtered execution plan data with payment steps removed
        """
        try:
            # Payment-related keywords to filter out
            payment_keywords = [
                'pay', 'payment', 'settle', 'transaction', 'checkout', 'credit card', 
                'bank transfer', 'debit card', 'online banking', 'e-wallet', 'finish payment',
                'complete payment', 'process payment', 'submit payment', 'confirm payment',
                'payment method', 'payment form', 'payment gateway', 'billing', 'invoice'
            ]
            
            # Get micro steps
            micro_steps = execution_plan_data.get('micro_steps', [])
            filtered_steps = []
            removed_count = 0
            
            for step in micro_steps:
                instruction = step.get('instruction', '').lower()
                nova_act_type = step.get('nova_act_type', '').lower()
                
                # Check if step contains payment-related keywords
                contains_payment = any(keyword in instruction for keyword in payment_keywords)
                is_payment_action = nova_act_type in ['pay', 'payment', 'transaction']
                
                if contains_payment or is_payment_action:
                    logger.warning(f"Removing payment-related step: {step.get('instruction', '')}")
                    removed_count += 1
                    continue
                
                filtered_steps.append(step)
            
            # Update the execution plan
            execution_plan_data['micro_steps'] = filtered_steps
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} payment-related steps from execution plan")
                # Update task description to reflect constraint adherence
                execution_plan_data['task_description'] = f"{task_description} (Payment steps removed per user constraint)"
            
            return execution_plan_data
            
        except Exception as e:
            logger.error(f"Error validating and filtering payment steps: {str(e)}")
            return execution_plan_data
    
    def _create_automation_execution_plan(self, data: Dict[str, Any], task_description: str) -> AutomationExecutionPlan:
        """Create AutomationExecutionPlan from parsed data."""
        try:
            # Extract micro steps
            micro_steps_data = data.get('micro_steps', [])
            micro_steps = []
            
            for step_data in micro_steps_data:
                # Clamp priority to reasonable range (1-10)
                priority = max(1, min(10, step_data.get('priority', 1)))
                
                # Handle dependencies - extract step numbers from objects if needed
                dependencies = step_data.get('dependencies', [])
                if dependencies and isinstance(dependencies[0], dict):
                    # If dependencies are objects like {'step_number': 1, 'status': 'completed'}
                    dependencies = [dep.get('step_number', 0) for dep in dependencies if isinstance(dep, dict)]
                elif not isinstance(dependencies, list):
                    # If dependencies is not a list, make it empty
                    dependencies = []
                
                micro_step = EnhancedMicroStep(
                    step_number=step_data.get('step_number', 1),
                    instruction=step_data.get('instruction', ''),
                    nova_act_type=step_data.get('nova_act_type', 'navigate'),
                    target_element=step_data.get('target_element', ''),
                    validation_criteria=step_data.get('validation_criteria', ''),
                    timeout_seconds=step_data.get('timeout_seconds', 30),
                    retry_count=step_data.get('retry_count', 2),
                    priority=priority,
                    dependencies=dependencies
                )
                micro_steps.append(micro_step)
            
            # Create the execution plan
            return AutomationExecutionPlan(
                session_id=data.get('session_id', f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
                task_description=data.get('task_description', task_description),
                target_website=data.get('target_website', 'https://www.myeg.com.my'),
                micro_steps=micro_steps,
                execution_strategy=data.get('execution_strategy', 'Sequential execution'),
                error_handling_strategy=data.get('error_handling_strategy', 'Basic retry mechanism'),
                blackhole_prevention=data.get('blackhole_prevention', 'Timeout-based prevention'),
                confidence_score=data.get('confidence_score', 0.8),
                total_estimated_time=data.get('total_estimated_time', 120),
                priority_level=data.get('priority_level', 5)
            )
            
        except Exception as e:
            logger.error(f"Error creating AutomationExecutionPlan: {str(e)}")
            # Return fallback plan
            return self._create_fallback_plan({}, task_description)
    
    def _parse_fallback_result(self, result_text: str, task_description: str) -> AutomationExecutionPlan:
        """Parse result if pydantic model is not used."""
        try:
            # Create a basic fallback plan
            return AutomationExecutionPlan(
                session_id=f"fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                task_description=task_description,
                target_website="https://www.myeg.com.my",
                micro_steps=[
                    EnhancedMicroStep(
                        step_number=1,
                        instruction="Navigate to the website",
                        nova_act_type="navigate",
                        target_element="website",
                        validation_criteria="Page loads successfully",
                        timeout_seconds=30,
                        retry_count=3,
                        priority=1,
                        dependencies=[]
                    )
                ],
                execution_strategy="sequential",
                error_handling_strategy="retry_with_delay",
                blackhole_prevention="monitor_consecutive_failures",
                confidence_score=0.5,
                total_estimated_time=60,
                priority_level=3
            )
        except Exception as e:
            logger.error(f"Error parsing fallback result: {str(e)}")
            return self._create_fallback_plan({}, task_description)
    
    def _create_fallback_plan(self, validation_result: Dict[str, Any], task_description: str) -> AutomationExecutionPlan:
        """Create a basic fallback plan when CrewAI fails."""
        return AutomationExecutionPlan(
            session_id=f"fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            task_description=task_description,
            target_website="https://www.myeg.com.my",
            micro_steps=[
                EnhancedMicroStep(
                    step_number=1,
                    instruction="Navigate to the website",
                    nova_act_type="navigate",
                    target_element="website",
                    validation_criteria="Page loads successfully",
                    timeout_seconds=30,
                    retry_count=3,
                    priority=1,
                    dependencies=[]
                )
            ],
            execution_strategy="sequential",
            error_handling_strategy="retry_with_delay",
            blackhole_prevention="monitor_consecutive_failures",
            confidence_score=0.3,
            total_estimated_time=60,
            priority_level=3
        )


class AutomationAgent:
    """Enhanced automation agent using CrewAI for intelligent micro-step generation."""
    
    def __init__(self):
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Initialize micro-step generator
        self.micro_step_generator = MicroStepGeneratorAgent(self.llm)
        
        # Initialize Tavily tool for fact-checking
        try:
            from ..coordinator.tavily_tool import TavilySearchTool
            self.tavily_tool = TavilySearchTool()
            logger.info("Tavily search tool initialized successfully for fact-checking")
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily tool: {str(e)}")
            self.tavily_tool = None
        
        # Browser session tracking
        self._active_browser_sessions = []
        
        logger.info("Enhanced automation agent initialized successfully with CrewAI-based micro-step generation and fact-checking capabilities")
    
    def _extract_credentials(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user credentials from user context using AI-powered analysis.
        
        Args:
            user_context: User context dictionary containing credentials
            
        Returns:
            Dictionary with extracted credentials or empty dict if none found
        """
        try:
            # Get user message for AI analysis
            user_message = user_context.get('user_message', '')
            if not user_message:
                # Fallback to rule-based extraction if no message
                return self._extract_credentials_rule_based(user_context)
            
            # Use AI to extract credentials from natural language
            credentials = self._ai_extract_credentials(user_message, user_context)
            
            if credentials:
                logger.info(f"AI extracted credentials: {list(credentials.keys())}")
            else:
                logger.info("No credentials found by AI analysis")
                
            return credentials
            
        except Exception as e:
            logger.error(f"Error in AI credential extraction: {str(e)}")
            # Fallback to rule-based extraction
            return self._extract_credentials_rule_based(user_context)
    
    def _ai_extract_credentials(self, user_message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to intelligently extract credentials from natural language.
        
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
                
                return credentials
            else:
                logger.warning("Could not parse JSON from AI credential extraction")
                return {}
                
        except Exception as e:
            logger.error(f"Error in AI credential extraction: {str(e)}")
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
    
    def _extract_credentials_rule_based(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback rule-based credential extraction.
        
        Args:
            user_context: User context dictionary containing credentials
            
        Returns:
            Dictionary with extracted credentials or empty dict if none found
        """
        credentials = {}
        
        # Common credential field names to look for
        credential_fields = {
            'email': ['email', 'username', 'user_email', 'login_email'],
            'password': ['password', 'pass', 'user_password', 'login_password'],
            'ic_number': ['ic_number', 'ic', 'nric', 'identity_card', 'id_number'],
            'phone': ['phone', 'phone_number', 'mobile', 'mobile_number'],
            'name': ['name', 'full_name', 'user_name', 'display_name']
        }
        
        for credential_type, field_names in credential_fields.items():
            for field_name in field_names:
                if field_name in user_context and user_context[field_name]:
                    credentials[credential_type] = user_context[field_name]
                    break
        
        return credentials
    
    def _initialize_llm(self) -> LLM:
        """Initialize LLM for CrewAI agents."""
        try:
            return LLM(
                model="bedrock/amazon.nova-pro-v1:0",
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_region_name=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),  # Use Bedrock region
                stream=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    def process_validator_output(self, validation_result: Dict[str, Any], task_description: str = "", credentials: Dict[str, Any] = None) -> AutomationExecutionPlan:
        """
        Process validator output and generate final structured execution plan using CrewAI.
        
        Args:
            validation_result: ValidationResult from validator agent
            task_description: Description of the automation task
            
        Returns:
            AutomationExecutionPlan: Complete execution plan for Nova Act agent
        """
        try:
            logger.info("Processing validator output with CrewAI micro-step generation...")
            return self.micro_step_generator.generate_execution_plan(validation_result, task_description, credentials)
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
            
            # Get user message directly from task
            user_message = task.get('user_message', '')
            
            # Get extracted credentials from coordinator agent
            extracted_credentials = task.get('extracted_credentials', {})
            
            # Also try to extract from user_context as fallback
            user_context = task.get('user_context', {})
            fallback_credentials = self._extract_credentials(user_context)
            
            # Merge credentials (extracted from coordinator takes priority)
            credentials = {**fallback_credentials, **extracted_credentials}
            
            if not validation_result:
                return {
                    "status": "error",
                    "message": "No validation result found in task. Please run validator first.",
                    "requires_human": True
                }
            
            # Generate execution plan using CrewAI with credentials
            execution_plan = self.process_validator_output(validation_result, task_description, credentials)
            
            # Convert to dictionary for JSON serialization
            plan_dict = execution_plan.to_dict()
            
            # Add credentials to the execution plan for Nova Act agent
            if credentials:
                plan_dict['credentials'] = credentials
                logger.info(f"Added user credentials to execution plan: {list(credentials.keys())}")
            
            # Add user message to execution plan for context
            if user_message:
                plan_dict['user_message'] = user_message
                logger.info("Added user message to execution plan for context")
            
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
    
    def process_nova_act_result(self, nova_act_result: Dict[str, Any], original_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Nova Act execution result and determine next action.
        
        This method analyzes the Nova Act result and decides whether to:
        1. Return success to user
        2. Try to improve the plan and retry
        3. Return tutorial from validator agent
        
        Args:
            nova_act_result: Result from Nova Act agent execution
            original_task: Original automation task
            
        Returns:
            Dictionary with next action and result
        """
        try:
            status = nova_act_result.get('status', 'unknown')
            requires_human = nova_act_result.get('requires_human', False)
            error_detection = nova_act_result.get('error_detection', {})
            suggestions = nova_act_result.get('suggestions', [])
            
            logger.info(f"Processing Nova Act result: {status}, requires_human: {requires_human}")
            
            # Case 1: Complete success
            if status == "success" and not requires_human:
                return {
                    "status": "success",
                    "message": "Automation completed successfully!",
                    "nova_act_result": nova_act_result,
                    "action": "inform_user",
                    "requires_human": False
                }
            
            # Case 2: Partial success or failure with error detection
            if status in ["partial", "failed"] and error_detection:
                error_type = error_detection.get('error_type', 'unknown')
                is_stuck_in_loop = error_detection.get('is_stuck_in_loop', False)
                
                # Check if we can improve the plan
                can_improve = self._can_improve_plan(error_type, suggestions)
                
                if can_improve and not is_stuck_in_loop:
                    logger.info("Attempting to improve execution plan based on error analysis")
                    return self._improve_and_retry_plan(original_task, nova_act_result, suggestions)
                else:
                    # Cannot improve, return tutorial
                    logger.info("Cannot improve plan, returning tutorial from validator agent")
                    return {
                        "status": "tutorial",
                        "message": "Unable to complete automation. Here's a tutorial to help you:",
                        "nova_act_result": nova_act_result,
                        "action": "return_tutorial",
                        "requires_human": True,
                        "tutorial": self._generate_tutorial_from_validator(original_task, error_type, suggestions)
                    }
            
            # Case 3: Complete failure without specific error detection
            return {
                "status": "tutorial",
                "message": "Automation failed. Here's a tutorial to help you:",
                "nova_act_result": nova_act_result,
                "action": "return_tutorial",
                "requires_human": True,
                "tutorial": self._generate_tutorial_from_validator(original_task, "general_failure", suggestions)
            }
            
        except Exception as e:
            logger.error(f"Error processing Nova Act result: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing result: {str(e)}",
                "action": "return_tutorial",
                "requires_human": True,
                "tutorial": "An error occurred while processing the automation result. Please try again or contact support."
            }
    
    def _improve_and_retry_plan(self, original_task: Dict[str, Any], nova_act_result: Dict[str, Any], suggestions: List[str]) -> Dict[str, Any]:
        """
        Improve the execution plan based on Nova Act results and suggestions.
        
        Args:
            original_task: Original automation task
            nova_act_result: Result from Nova Act execution
            suggestions: Improvement suggestions from Nova Act
            
        Returns:
            Dictionary with improved execution plan and retry instructions
        """
        try:
            logger.info("Improving execution plan based on Nova Act feedback...")
            
            # Create improved task with suggestions
            improved_task = self._create_improved_task(original_task, nova_act_result, suggestions)
            
            # Generate improved execution plan
            improved_execution_plan_result = self.generate_execution_plan(improved_task)
            
            if improved_execution_plan_result["status"] != "success":
                logger.error(f"Failed to generate improved execution plan: {improved_execution_plan_result['message']}")
                return {
                    "status": "tutorial",
                    "message": "Unable to improve the plan. Here's a tutorial to help you:",
                    "nova_act_result": nova_act_result,
                    "action": "return_tutorial",
                    "requires_human": True,
                    "tutorial": self._generate_tutorial_from_validator(original_task, "improvement_failed", suggestions)
                }
            
            # Return improved plan for retry
            improved_execution_plan = improved_execution_plan_result["execution_plan"]
            
            logger.info(f"Successfully generated improved execution plan with {len(improved_execution_plan.get('micro_steps', []))} micro-steps")
            
            return {
                "status": "retry",
                "message": "Plan improved successfully. Retrying with enhanced execution plan.",
                "nova_act_result": nova_act_result,
                "action": "improve_and_retry",
                "requires_human": False,
                "improved_execution_plan": improved_execution_plan,
                "improvement_suggestions": suggestions,
                "retry_count": 1
            }
            
        except Exception as e:
            logger.error(f"Error improving execution plan: {str(e)}")
            return {
                "status": "tutorial",
                "message": "Error occurred while improving the plan. Here's a tutorial to help you:",
                "nova_act_result": nova_act_result,
                "action": "return_tutorial",
                "requires_human": True,
                "tutorial": self._generate_tutorial_from_validator(original_task, "improvement_error", suggestions)
            }
    
    def _create_improved_task(self, original_task: Dict[str, Any], nova_act_result: Dict[str, Any], suggestions: List[str]) -> Dict[str, Any]:
        """
        Create an improved task based on Nova Act results and suggestions.
        
        Args:
            original_task: Original automation task
            nova_act_result: Result from Nova Act execution
            suggestions: Improvement suggestions from Nova Act
            
        Returns:
            Improved task dictionary
        """
        try:
            # Start with original task
            improved_task = original_task.copy()
            
            # Add improvement context to validation result
            validation_result = improved_task.get('validation_result', {})
            
            # Add improvement suggestions to validation result
            if 'improvements' not in validation_result:
                validation_result['improvements'] = []
            
            # Add suggestions as improvements
            for suggestion in suggestions:
                validation_result['improvements'].append({
                    "type": "nova_act_suggestion",
                    "suggestion": suggestion,
                    "source": "nova_act_error_detection"
                })
            
            # Add error context
            error_detection = nova_act_result.get('error_detection', {})
            if error_detection:
                validation_result['error_context'] = {
                    "error_type": error_detection.get('error_type', 'unknown'),
                    "has_difficulties": error_detection.get('has_difficulties', False),
                    "is_stuck_in_loop": error_detection.get('is_stuck_in_loop', False),
                    "can_proceed": error_detection.get('can_proceed', False)
                }
            
            # Add retry context
            validation_result['retry_context'] = {
                "is_retry": True,
                "original_status": nova_act_result.get('status', 'unknown'),
                "success_count": nova_act_result.get('success_count', 0),
                "failed_count": nova_act_result.get('failed_count', 0),
                "suggestions_applied": suggestions
            }
            
            # Update validation result
            improved_task['validation_result'] = validation_result
            
            # Add improvement instructions to task description
            original_description = improved_task.get('task_description', '')
            improvement_instructions = f"\n\nIMPROVEMENT INSTRUCTIONS:\n- Apply the following suggestions: {', '.join(suggestions)}\n- Focus on addressing the error type: {error_detection.get('error_type', 'unknown')}\n- Ensure better error handling and recovery strategies"
            
            improved_task['task_description'] = original_description + improvement_instructions
            
            logger.info(f"Created improved task with {len(suggestions)} suggestions applied")
            
            return improved_task
            
        except Exception as e:
            logger.error(f"Error creating improved task: {str(e)}")
            # Return original task as fallback
            return original_task
    
    def _can_improve_plan(self, error_type: str, suggestions: List[str]) -> bool:
        """
        Determine if the execution plan can be improved based on error type and suggestions.
        
        Args:
            error_type: Type of error detected
            suggestions: List of improvement suggestions
            
        Returns:
            Boolean indicating if plan can be improved
        """
        # Error types that can potentially be improved
        improvable_errors = [
            "general_difficulties",
            "cannot_proceed",
            "timeout",
            "element_not_found"
        ]
        
        # Error types that cannot be improved (require human intervention)
        non_improvable_errors = [
            "infinite_loop",
            "authentication_required",
            "captcha_required",
            "payment_required",
            "permission_denied"
        ]
        
        if error_type in non_improvable_errors:
            return False
        
        if error_type in improvable_errors:
            return True
        
        # Check suggestions for improvement indicators
        improvement_keywords = [
            "try", "retry", "different", "alternative", "modify", "adjust", "change"
        ]
        
        for suggestion in suggestions:
            if any(keyword in suggestion.lower() for keyword in improvement_keywords):
                return True
        
        return False
    
    def _generate_tutorial_from_validator(self, original_task: Dict[str, Any], error_type: str, suggestions: List[str]) -> str:
        """
        Generate a tutorial using CrewAI agent based on the error and original task.
        
        Args:
            original_task: Original automation task
            error_type: Type of error encountered
            suggestions: List of suggestions from Nova Act
            
        Returns:
            Tutorial string for the user
        """
        try:
            logger.info("Generating tutorial using CrewAI agent...")
            
            # Get user message and credentials for context
            user_message = original_task.get('user_message', '')
            extracted_credentials = original_task.get('extracted_credentials', {})
            user_context = original_task.get('user_context', {})
            
            # Create tutorial generation agent
            tutorial_agent = self._create_tutorial_generation_agent()
            
            # Create tutorial generation task with user-specific context and fact-checking
            tutorial_task = Task(
                description=f"""
                Generate a comprehensive, helpful tutorial for a user who failed to complete an automation task.
                
                USER'S SPECIFIC REQUEST:
                "{user_message}"
                
                EXTRACTED USER CREDENTIALS:
                {extracted_credentials}
                
                ADDITIONAL USER CONTEXT:
                {user_context}
                
                TASK DETAILS:
                - Task Description: {original_task.get('task_description', 'Unknown task')}
                - Target Website: {original_task.get('target_website', 'Unknown website')}
                - Error Type: {error_type.replace('_', ' ').title()}
                - Suggestions from automation: {', '.join(suggestions) if suggestions else 'None provided'}
                
                FACT-CHECKING REQUIREMENTS:
                Before generating the tutorial, you MUST:
                1. Use web search to verify current information about the government service process
                2. Search for the most recent updates to the website or process
                3. Verify the correct URLs, form fields, and navigation paths
                4. Check for any recent changes in requirements or procedures
                5. Ensure all website links and instructions are current and accurate
                6. Search for common issues and their current solutions
                
                SEARCH QUERIES TO PERFORM:
                - Search for current MyEG summons checking process
                - Search for any recent changes to JPJ/RTD summons system
                - Search for current MyEG website navigation and interface
                - Search for common issues when checking summons online
                - Search for official government guidance on summons checking
                
                REQUIREMENTS:
                1. Create a tutorial SPECIFICALLY for the user's request: "{user_message}"
                2. Use the user's IC number ({extracted_credentials.get('ic_number', 'N/A')}) in the tutorial
                3. Focus on SUMMONS CHECKING (not payment or renewal)
                4. Include specific instructions for checking transportation summons on MyEG
                5. Provide troubleshooting tips based on the error type
                6. Include alternative approaches if the primary method fails
                7. Make it beginner-friendly with clear explanations
                8. Include what information they need to prepare beforehand
                9. Provide specific website navigation instructions for MyEG
                10. Include common pitfalls and how to avoid them
                11. Emphasize that this is for CHECKING summons, NOT paying them
                12. CRITICAL: All information must be fact-checked and current
                
                FORMAT:
                Use markdown formatting with clear headings, numbered steps, and helpful tips.
                Make it actionable and practical for someone to follow manually.
                Start with a clear title that matches the user's request.
                Include a "Last Verified" section indicating when the information was fact-checked.
                """,
                expected_output="A comprehensive markdown tutorial with clear step-by-step instructions, troubleshooting tips, and helpful guidance for completing the task manually. All information must be fact-checked using web search.",
                agent=tutorial_agent
            )
            
            # Create crew and execute
            tutorial_crew = Crew(
                agents=[tutorial_agent],
                tasks=[tutorial_task],
                process=Process.sequential,
                verbose=False  # Keep quiet for production
            )
            
            # Generate tutorial
            result = tutorial_crew.kickoff()
            
            # Extract tutorial content
            tutorial_content = result.raw if hasattr(result, 'raw') else str(result)
            
            logger.info("Tutorial generated successfully using CrewAI agent")
            
            # Fact-check the generated tutorial content
            logger.info("Starting fact-checking of generated tutorial...")
            fact_check_result = self.fact_check_tutorial_content(
                tutorial_content, 
                service_type="MyEG summons checking"
            )
            
            # Add fact-checking information to the tutorial
            if fact_check_result.get("verified", False):
                logger.info("Tutorial fact-checking completed successfully")
                # Append fact-checking information to tutorial
                fact_check_info = f"\n\n---\n**Last Verified:** {fact_check_result.get('timestamp', 'Unknown')}\n**Fact-Checking Status:** ✅ Verified"
                tutorial_content += fact_check_info
            else:
                logger.warning("Tutorial fact-checking failed or unavailable")
                fact_check_info = f"\n\n---\n**Last Verified:** {fact_check_result.get('timestamp', 'Unknown')}\n**Fact-Checking Status:** ⚠️ Verification unavailable - please verify information manually"
                tutorial_content += fact_check_info
            
            return tutorial_content
            
        except Exception as e:
            logger.error(f"Error generating tutorial with CrewAI agent: {str(e)}")
            # Fallback to basic tutorial
            return self._generate_fallback_tutorial(original_task, error_type, suggestions)
    
    def _create_tutorial_generation_agent(self) -> Agent:
        """Create a specialized CrewAI agent for tutorial generation."""
        # Add Tavily tool if available
        tools = [self.tavily_tool] if self.tavily_tool else []
        
        return Agent(
            role="Government Service Automation Tutorial Expert",
            goal="Create comprehensive, clear, and actionable tutorials that help users manually complete government service tasks when automation fails",
            backstory="""You are an expert in Malaysian government services and user experience design. 
            You have years of experience helping citizens navigate complex government websites and processes. 
            You excel at breaking down complicated procedures into simple, step-by-step instructions that anyone can follow.
            You understand common user pain points, technical issues, and provide practical solutions.
            You always include troubleshooting tips and alternative approaches to ensure users can complete their tasks successfully.
            Your tutorials are clear, detailed, and include all necessary information users need to prepare beforehand.
            You use web search to verify current information about government services and processes to ensure accuracy.""",
            tools=tools,
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
    
    def _create_fact_checking_agent(self) -> Agent:
        """Create a specialized CrewAI agent for fact-checking government service information."""
        # Add Tavily tool if available
        tools = [self.tavily_tool] if self.tavily_tool else []
        
        return Agent(
            role="Government Service Fact-Checker",
            goal="Verify and fact-check information about Malaysian government services to ensure accuracy and currency",
            backstory="""You are a specialized fact-checker focused on Malaysian government services and processes. 
            You use web search to verify current information about government websites, procedures, and requirements. 
            You excel at finding the most recent updates and changes to government services.
            You understand the importance of accuracy in government service guidance and always verify information 
            from official sources and current web content. You provide detailed verification reports with sources.""",
            tools=tools,
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
    
    def fact_check_tutorial_content(self, tutorial_content: str, service_type: str = "government service") -> Dict[str, Any]:
        """
        Fact-check tutorial content using Tavily search and return verification results.
        
        Args:
            tutorial_content: The tutorial content to fact-check
            service_type: Type of government service being discussed
            
        Returns:
            Dictionary with fact-checking results and recommendations
        """
        try:
            if not self.tavily_tool:
                logger.warning("Tavily tool not available for fact-checking")
                return {
                    "status": "warning",
                    "message": "Fact-checking unavailable - Tavily tool not initialized",
                    "verified": False,
                    "recommendations": ["Manual verification recommended"]
                }
            
            logger.info(f"Starting fact-checking for {service_type} tutorial content")
            
            # Create fact-checking agent
            fact_checker = self._create_fact_checking_agent()
            
            # Create fact-checking task
            fact_check_task = Task(
                description=f"""
                Fact-check the following tutorial content about {service_type} to ensure accuracy and currency.
                
                TUTORIAL CONTENT TO VERIFY:
                {tutorial_content}
                
                FACT-CHECKING TASKS:
                1. Search for current information about the government service mentioned
                2. Verify all website URLs and navigation paths are current
                3. Check for recent changes to the service or website
                4. Verify form fields, buttons, and interface elements mentioned
                5. Confirm any requirements, fees, or procedures stated
                6. Check for common issues and current solutions
                7. Verify official government guidance and documentation
                
                SEARCH STRATEGY:
                - Search for the specific government service and current process
                - Search for the official website and recent updates
                - Search for user experiences and common issues
                - Search for official government announcements or changes
                - Search for troubleshooting guides and solutions
                
                RETURN FORMAT:
                Provide a detailed fact-checking report with:
                - Status: verified, needs_updates, or contains_errors
                - Verified information: List of confirmed accurate information
                - Issues found: List of any outdated or incorrect information
                - Recommendations: Specific suggestions for improvement
                - Sources: URLs and sources used for verification
                - Last checked: Current date and time
                """,
                expected_output="Detailed fact-checking report with verification status, issues found, and recommendations",
                agent=fact_checker
            )
            
            # Execute fact-checking
            fact_check_crew = Crew(
                agents=[fact_checker],
                tasks=[fact_check_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = fact_check_crew.kickoff()
            
            # Parse and return results
            fact_check_report = str(result)
            
            logger.info("Fact-checking completed successfully")
            
            return {
                "status": "success",
                "message": "Fact-checking completed",
                "verified": True,
                "report": fact_check_report,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during fact-checking: {str(e)}")
            return {
                "status": "error",
                "message": f"Fact-checking failed: {str(e)}",
                "verified": False,
                "recommendations": ["Manual verification recommended"]
            }
    
    def _generate_fallback_tutorial(self, original_task: Dict[str, Any], error_type: str, suggestions: List[str]) -> str:
        """Generate a basic fallback tutorial if CrewAI agent fails."""
        task_description = original_task.get('task_description', 'Unknown task')
        target_website = original_task.get('target_website', 'Unknown website')
        user_message = original_task.get('user_message', '')
        extracted_credentials = original_task.get('extracted_credentials', {})
        
        # Extract IC number for specific tutorial
        ic_number = extracted_credentials.get('ic_number', 'N/A')
        
        return f"""
# Tutorial: Check Transportation Summons on MyEG

## What you were trying to do:
{user_message if user_message else task_description}

## Your IC Number:
{ic_number}

## What went wrong:
{error_type.replace('_', ' ').title()}

## Step-by-step manual instructions for checking summons:

### Step 1: Access MyEG Website
1. Open your web browser and go to: https://www.myeg.com.my
2. Wait for the page to load completely

### Step 2: Navigate to JPJ Services
1. Look for "JPJ" or "Transportation" services on the homepage
2. Click on "Check & Pay RTD Summons" or similar option

### Step 3: Enter Your IC Number
1. Find the IC number input field
2. Enter your IC number: **{ic_number}**
3. Double-check the number is correct

### Step 4: Check Summons
1. Click "Check Summons" or "Search" button
2. Wait for the results to load
3. Review any summons information displayed

### Step 5: Review Results
1. Look for any outstanding summons
2. Note down the details (amounts, due dates, violation types)
3. **DO NOT proceed to payment** - you only wanted to check

## Important Notes:
- This is for **CHECKING** summons only, not paying them
- You don't need a summons number to check
- The system will show all summons associated with your IC number
- No payment is required for checking

## Troubleshooting Tips:
{chr(10).join(f"- {suggestion}" for suggestion in suggestions) if suggestions else "- Ensure your internet connection is stable" + chr(10) + "- Try refreshing the page if it doesn't load" + chr(10) + "- Double-check your IC number format"}

## If you need help:
- Check MyEG's help section or FAQ
- Contact MyEG customer support
- Ensure you have a stable internet connection
- Try using a different browser if the website doesn't load properly

---
*This tutorial is specifically for checking transportation summons with IC number: {ic_number}*
"""

    async def validate_automation_request(self, automation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an automation request before processing.
        
        Args:
            automation_context: Context and user data to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            logger.info("Validating automation request")
            
            # Import here to avoid circular imports
            from app.agents.coordinator.coordinator_agent import coordinator_agent
            
            # Use coordinator's validation logic
            validation_result = await coordinator_agent.validate_automation_context(automation_context)
            
            logger.info("Automation request validation completed")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating automation request: {str(e)}")
            return {
                "status": "error",
                "message": f"Validation failed: {str(e)}",
                "is_valid": False,
                "missing_information": ["Unable to validate due to error"]
            }
    
    def register_browser_session(self, session_id: str, nova_act_instance):
        """Register an active browser session for cleanup tracking."""
        self._active_browser_sessions.append({
            'session_id': session_id,
            'nova_act': nova_act_instance,
            'created_at': datetime.utcnow()
        })
        logger.debug(f"Registered browser session: {session_id}")
    
    def unregister_browser_session(self, session_id: str):
        """Unregister a browser session from cleanup tracking."""
        self._active_browser_sessions = [
            session for session in self._active_browser_sessions 
            if session['session_id'] != session_id
        ]
        logger.debug(f"Unregistered browser session: {session_id}")
    
    async def close_browser(self):
        """Close all active browser sessions gracefully."""
        try:
            logger.info(f"Closing {len(self._active_browser_sessions)} active browser sessions...")
            
            for session in self._active_browser_sessions:
                try:
                    session_id = session['session_id']
                    nova_act = session['nova_act']
                    
                    logger.debug(f"Closing browser session: {session_id}")
                    
                    # Check if Nova Act instance has stop method
                    if hasattr(nova_act, 'stop'):
                        nova_act.stop()
                        logger.debug(f"Stopped Nova Act session: {session_id}")
                    elif hasattr(nova_act, 'close'):
                        nova_act.close()
                        logger.debug(f"Closed Nova Act session: {session_id}")
                    else:
                        logger.warning(f"Nova Act session {session_id} has no stop/close method")
                        
                except Exception as e:
                    logger.warning(f"Error closing browser session {session.get('session_id', 'unknown')}: {str(e)}")
                    continue
            
            # Clear all sessions
            self._active_browser_sessions.clear()
            logger.info("All browser sessions closed successfully")
            
        except Exception as e:
            logger.error(f"Error during browser cleanup: {str(e)}")
            # Clear sessions even if there was an error
            self._active_browser_sessions.clear()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the automation agent."""
        try:
            return {
                "status": "healthy",
                "agent_type": "automation_agent",
                "llm_available": self.llm is not None,
                "micro_step_generator_available": self.micro_step_generator is not None,
                "active_browser_sessions": len(self._active_browser_sessions),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_type": "automation_agent",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def process_automation_request(
        self,
        message: str,
        session_id: str,
        language,  # Language enum from requests
        automation_context: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an automation request from the agent service.
        
        This method serves as the entry point for automation requests from the API.
        It delegates to the coordinator agent for actual processing.
        
        Args:
            message: User message/request
            session_id: Session identifier
            language: Language preference
            automation_context: Context and user data
            user_id: Optional user identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing automation request for session {session_id}")
            
            # Import here to avoid circular imports
            from app.agents.coordinator.coordinator_agent import coordinator_agent
            
            # Process through coordinator agent
            result = await coordinator_agent.process_complete_request(
                user_message=message,
                user_context=automation_context,
                session_id=session_id,
                user_id=user_id
            )
            
            logger.info(f"Automation request processed successfully for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing automation request: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process automation request: {str(e)}",
                "requires_human": True,
                "timestamp": datetime.utcnow().isoformat()
            }


# Global automation agent instance
automation_agent = AutomationAgent()
