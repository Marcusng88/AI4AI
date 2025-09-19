"""
CrewAI Government Services Automation Agent
==========================================

This agent uses CrewAI with Stagehand for automating government service interactions.
It provides intelligent web automation capabilities for various government portals
including MyEG, JPJ, and other Malaysian government services.

Main capabilities:
- Traffic summons checking and payment
- Document verification and downloads
- Form automation for government applications
- Multi-step workflow execution with decision making
- Structured data extraction from government portals
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew, Process
from crewai_tools import StagehandTool
from stagehand.schemas import AvailableModel
from pydantic import BaseModel, Field
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

def apply_stagehand_tool_fix():
    """
    Apply a fix to the StagehandTool to properly handle model_api_key parameter.
    This fixes the issue where model_api_key is not passed correctly to the Stagehand constructor.
    """
    from crewai_tools import StagehandTool
    
    # Store the original method
    original_setup_stagehand = StagehandTool._setup_stagehand
    
    async def fixed_setup_stagehand(self, session_id=None):
        """Fixed version of _setup_stagehand that properly passes model_api_key"""
        # If we're in testing mode, return mock objects
        if self._testing:
            if not self._stagehand:
                # Create mock objects for testing
                class MockPage:
                    async def act(self, options):
                        mock_result = type("MockResult", (), {})()
                        mock_result.model_dump = lambda: {
                            "message": "Action completed successfully"
                        }
                        return mock_result

                    async def extract(self, options):
                        mock_result = type("MockResult", (), {})()
                        mock_result.model_dump = lambda: {
                            "data": "Mock extracted data"
                        }
                        return mock_result

                    async def observe(self, options):
                        mock_result = type("MockResult", (), {})()
                        mock_result.model_dump = lambda: {
                            "elements": [{"description": "Mock element", "method": "click", "selector": "//mock"}]
                        }
                        return mock_result

                    async def goto(self, url):
                        return None

                class MockStagehand:
                    def __init__(self):
                        self.page = MockPage()
                        self.session_id = "test-session-id"

                    async def init(self):
                        return None

                    async def close(self):
                        return None

                self._stagehand = MockStagehand()
                await self._stagehand.init()
                self._page = self._stagehand.page
                self._session_id = self._stagehand.session_id

            return self._stagehand, self._page

        # Normal initialization for non-testing mode
        if not self._stagehand:
            # Get the appropriate API key based on model type
            model_api_key = self._get_model_api_key()

            if not model_api_key:
                raise ValueError(
                    "No appropriate API key found for model. Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY"
                )

            # Build the StagehandConfig with proper parameter names
            from stagehand import StagehandConfig
            config = StagehandConfig(
                env="BROWSERBASE",
                api_key=self.api_key,  # Browserbase API key
                project_id=self.project_id,  # Browserbase project ID
                model_name=self.model_name,
                api_url=self.server_url
                if self.server_url
                else "https://api.stagehand.browserbase.com/v1",
                dom_settle_timeout_ms=self.dom_settle_timeout_ms,
                self_heal=self.self_heal,
                wait_for_captcha_solves=self.wait_for_captcha_solves,
                verbose=self.verbose,
                browserbase_session_id=session_id or self._session_id,
            )

            # Initialize Stagehand with config AND model_api_key as separate parameter
            from stagehand import Stagehand
            self._stagehand = Stagehand(
                config=config,
                model_api_key=model_api_key,  # Pass model_api_key separately!
                server_url=self.server_url or "https://api.stagehand.browserbase.com/v1"
            )

            # Initialize the Stagehand instance
            await self._stagehand.init()
            self._page = self._stagehand.page
            self._session_id = self._stagehand.session_id

        return self._stagehand, self._page
    
    # Apply the patch
    StagehandTool._setup_stagehand = fixed_setup_stagehand
    logger.info("✅ Applied fix to StagehandTool._setup_stagehand")

# Apply the fix when this module is imported
apply_stagehand_tool_fix()

def create_stagehand_tool():
    """
    Create and configure the official StagehandTool from crewai_tools
    """
    # Get API keys from environment variables
    browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
    browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")
    model_api_key = os.getenv("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    
    if not browserbase_api_key:
        logger.warning("BROWSERBASE_API_KEY not found. Using local environment.")
        # For local testing without Browserbase
        return StagehandTool(
            model_api_key=model_api_key,
            model_name=AvailableModel.GPT_4O if os.environ.get("OPENAI_API_KEY") else AvailableModel.CLAUDE_3_5_SONNET_LATEST,
            headless=True,
            verbose=1,
            dom_settle_timeout_ms=5000,
            self_heal=True,
            wait_for_captcha_solves=True
        )
    
    # Configure with Browserbase for production
    return StagehandTool(
        api_key=browserbase_api_key,
        project_id=browserbase_project_id,
        model_api_key=model_api_key,
        model_name=AvailableModel.GPT_4O if os.environ.get("OPENAI_API_KEY") else AvailableModel.CLAUDE_3_5_SONNET_LATEST,
        dom_settle_timeout_ms=5000,  # Wait longer for DOM to settle
        headless=True,  # Run browser in headless mode
        self_heal=True,  # Attempt to recover from errors
        wait_for_captcha_solves=True,  # Wait for CAPTCHA solving
        verbose=1,  # Control logging verbosity (0-3)
    )


class GovernmentServicesAgent:
    """
    CrewAI agent specialized in Malaysian government services automation
    """
    
    def __init__(self):
        self.stagehand_tool = create_stagehand_tool()
        logger.info(f"Stagehand tool created: {self.stagehand_tool}")
        self.setup_agents()
    
    def setup_agents(self):
        """Setup CrewAI agents with specialized roles"""
        
        # Browser Navigation Agent
        self.navigator_agent = Agent(
            role="Government Portal Navigator",
            goal="Navigate and interact with Malaysian government websites to complete tasks",
            backstory=(
                "You are an expert at using web browsers to interact with Malaysian government portals like MyEG, JPJ, "
                "and other official websites. You can navigate websites, fill forms, click buttons, and extract information "
                "using simple, clear instructions. You always describe what you want to do in plain language."
            ),
            tools=[self.stagehand_tool],
            verbose=True,
            memory=True,
            allow_delegation=False  # Prevent delegation for focused execution
        )
        
    
    def create_traffic_summons_task(self, 
                                  ic_number: str, 
                                  username: str = None, 
                                  password: str = None) -> Task:
        """Create a task for checking traffic summons on MyEG"""
        
        return Task(
            description=f"""
            TASK: Check traffic summons for IC number {ic_number} on the MyEG website following the official process.
            
            OFFICIAL MYEG TRAFFIC SUMMONS PROCESS:
            1. Go to the MyEG website: www.myeg.com.my
            2. Register for a new account if you are a first-time user OR log in with existing credentials
            3. Log in with username and password:
               - Username: {username or '[NEEDS_USERNAME]'}
               - Password: {password or '[NEEDS_PASSWORD]'}
            4. Navigate to: Jabatan Pengangkutan Jalan > Check & Pay RTD Summons
            5. Enter the required identification details:
               - IC number: {ic_number}
               - NOTE: Only ID number like MyKad, passport, etc. accepted, NOT vehicle number
            6. View summons details and check if payment options are available
            
            BROWSER AUTOMATION INSTRUCTIONS:
            Use simple, natural language to control the browser:
            - "Go to www.myeg.com.my"
            - "Click the login button"
            - "Enter username in the username field"
            - "Enter password in the password field" 
            - "Click the login submit button"
            - "Click on Jabatan Pengangkutan Jalan menu"
            - "Click on Check & Pay RTD Summons option"
            - "Enter IC number in the identification field"
            - "Click the check or search button"
            - "Extract all summons information displayed"
            
            EXPECTED OUTPUT: Complete details of all traffic summons found including summons number, date of offense, location, offense type, amount due, and payment status.
            """,
            agent=self.navigator_agent,
            expected_output="Complete traffic summons details with summons numbers, dates, locations, offense types, amounts, and payment status for the provided IC number"
        )
    
    def create_government_service_task(self, task_details: Dict[str, Any]) -> Task:
        """
        Create a flexible government service task based on coordinator's detailed flow
        
        Args:
            task_details: Dictionary containing:
                - service_name: Name of the government service
                - department: Government department (JPJ, LHDN, etc.)
                - target_website: Website URL
                - instructions: Detailed step-by-step instructions
                - user_context: User data (IC, credentials, etc.)
                - expected_outcome: What should be achieved
        """
        service_name = task_details.get('service_name', 'Government Service')
        department = task_details.get('department', 'Government Department')
        target_website = task_details.get('target_website', '')
        instructions = task_details.get('instructions', '')
        user_context = task_details.get('user_context', {})
        expected_outcome = task_details.get('expected_outcome', 'Complete the government service task')
        
        return Task(
            description=f"""
            TASK: {service_name} ({department})
            
            TARGET WEBSITE: {target_website}
            
            USER CONTEXT: {user_context}
            
            DETAILED INSTRUCTIONS:
            {instructions}
            
            BROWSER AUTOMATION GUIDELINES:
            - Use simple, natural language commands
            - Be specific about what elements to interact with
            - Examples: "Click the login button", "Enter text in the username field", "Navigate to the menu"
            - Extract information when requested
            - Report any errors or issues encountered
            
            EXPECTED OUTCOME: {expected_outcome}
            """,
            agent=self.navigator_agent,
            expected_output=f"Results of {service_name} task including any extracted information, confirmations, or status updates"
        )
    
    
    def execute_government_task(self, task_details: Dict[str, Any]) -> str:
        """
        Execute a government service automation task using coordinator's detailed flow
        
        Args:
            task_details: Task details from coordinator containing:
                - task_type: Type of task
                - service_name: Name of the service
                - department: Government department
                - user_context: User data and context
                - instructions: Detailed instructions
                - target_website: Target website URL
                - expected_outcome: Expected result
        """
        
        try:
            task_type = task_details.get('task_type', 'government_service')
            
            # Handle specific traffic summons task (backward compatibility)
            if task_type == "traffic_summons":
                user_context = task_details.get('user_context', {})
                task = self.create_traffic_summons_task(
                    ic_number=user_context.get('ic_number'),
                    username=user_context.get('username'),
                    password=user_context.get('password')
                )
            else:
                # Use flexible government service task for all other cases
                task = self.create_government_service_task(task_details)
            
            # Create and execute crew with navigator agent
            crew = Crew(
                agents=[self.navigator_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            try:
                result = crew.kickoff()  # Note: crew.kickoff() is synchronous
                return str(result)
            finally:
                # Clean up resources
                if hasattr(self.stagehand_tool, 'close'):
                    self.stagehand_tool.close()
            
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            return f"Error executing task: {str(e)}"


# Convenience function for backward compatibility
def check_traffic_summons(ic_number: str, username: str = None, password: str = None):
    """Convenience function for checking traffic summons"""
    agent = GovernmentServicesAgent()
    try:
        task_details = {
            "task_type": "traffic_summons",
            "service_name": "Traffic Summons Check",
            "department": "JPJ",
            "user_context": {
                "ic_number": ic_number,
                "username": username,
                "password": password
            },
            "target_website": "www.myeg.com.my",
            "expected_outcome": "Check traffic summons for the provided IC number"
        }
        return agent.execute_government_task(task_details)
    finally:
        # Ensure cleanup
        if hasattr(agent.stagehand_tool, 'close'):
            agent.stagehand_tool.close()
