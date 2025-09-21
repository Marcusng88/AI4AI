"""
Nova Act Agent for browser automation using AWS Bedrock Agent Core Browser.
This agent executes Nova Act instructions directly with BOOL_SCHEMA error detection
and structured output for CrewAI integration.
"""

import os
import time
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional, List
from datetime import datetime

from nova_act import NovaAct, BOOL_SCHEMA
from bedrock_agentcore.tools.browser_client import browser_session

from app.core.logging import get_logger

logger = get_logger(__name__)


class NovaActExecutionResult:
    """Data class for Nova Act execution results."""
    def __init__(self, instruction: str, status: str, result_text: str, 
                 error_message: str = None, execution_time: float = 0.0, 
                 retry_count: int = 0, browser_state: Dict[str, Any] = None):
        self.instruction = instruction
        self.status = status  # "success", "failed", "timeout", "blackhole_detected"
        self.result_text = result_text
        self.error_message = error_message
        self.execution_time = execution_time
        self.retry_count = retry_count
        self.browser_state = browser_state or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instruction": self.instruction,
            "status": self.status,
            "result_text": self.result_text,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "retry_count": self.retry_count,
            "browser_state": self.browser_state
        }


class NovaActErrorDetection:
    """Data class for error detection results."""
    def __init__(self, has_difficulties: bool, is_stuck_in_loop: bool, can_proceed: bool,
                 error_type: str = None, suggestions: List[str] = None):
        self.has_difficulties = has_difficulties
        self.is_stuck_in_loop = is_stuck_in_loop
        self.can_proceed = can_proceed
        self.error_type = error_type
        self.suggestions = suggestions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_difficulties": self.has_difficulties,
            "is_stuck_in_loop": self.is_stuck_in_loop,
            "can_proceed": self.can_proceed,
            "error_type": self.error_type,
            "suggestions": self.suggestions
        }


class NovaActExecutionSummary:
    """Data class for complete execution summary."""
    def __init__(self, status: str, message: str, session_id: str, 
                 completed_steps: List[NovaActExecutionResult], 
                 failed_step: NovaActExecutionResult = None,
                 error_detection: NovaActErrorDetection = None,
                 success_count: int = 0, failed_count: int = 0,
                 requires_human: bool = False, suggestions: List[str] = None):
        self.status = status  # "success", "partial", "failed", "error"
        self.message = message
        self.session_id = session_id
        self.completed_steps = completed_steps
        self.failed_step = failed_step
        self.error_detection = error_detection
        self.success_count = success_count
        self.failed_count = failed_count
        self.requires_human = requires_human
        self.suggestions = suggestions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (replaces Pydantic model_dump)."""
        return {
            "status": self.status,
            "message": self.message,
            "session_id": self.session_id,
            "completed_steps": [step.to_dict() for step in self.completed_steps],
            "failed_step": self.failed_step.to_dict() if self.failed_step else None,
            "error_detection": self.error_detection.to_dict() if self.error_detection else None,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "requires_human": self.requires_human,
            "suggestions": self.suggestions
        }


class NovaActAgent:
    """Nova Act agent for browser automation with intelligent error detection."""
    
    def __init__(self):
        # Configuration
        self.nova_act_api_key = os.getenv("NOVA_ACT_API_KEY")
        self.aws_region = "us-east-1"
        
        logger.info("Nova Act agent initialized successfully with direct execution")
    
    def _check_asyncio_context(self) -> bool:
        """Check if we're running in an asyncio event loop."""
        try:
            loop = asyncio.get_running_loop()
            logger.warning(f"🚨 DIAGNOSTIC: Nova Act called from asyncio loop: {loop}")
            logger.warning(f"   This will cause Playwright Sync API to fail!")
            logger.warning(f"   Loop is running: {loop.is_running()}")
            return True
        except RuntimeError:
            logger.info("✅ DIAGNOSTIC: Nova Act called from sync context - safe!")
            return False
    
    def _execute_nova_act_sync(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Nova Act in synchronous context (for thread isolation)."""
        try:
            # Extract plan details
            task_description = execution_plan.get('task_description', 'Automation task')
            session_id = execution_plan.get('session_id', f"session_{int(time.time())}")
            target_website = execution_plan.get('target_website', 'https://www.myeg.com.my')
            micro_steps = execution_plan.get('micro_steps', [])
            credentials = execution_plan.get('credentials', {})
            
            logger.info(f"Executing automation plan: {task_description}")
            logger.info(f"Target website: {target_website}")
            logger.info(f"Micro-steps count: {len(micro_steps)}")
            
            # Start fresh session each time
            with browser_session(self.aws_region) as client:
                ws_url, headers = client.generate_ws_headers()
                
                # # Create and start the BrowserViewerServer to get live view URL
                # # This is the correct pattern from AWS documentation
                # viewer_server = None
                # live_view_url = None
                
                # try:
                #     # Import BrowserViewerServer from our implementation
                #     # Following the exact pattern from AWS official samples
                #     from .browser_viewer import BrowserViewerServer
                    
                #     # Create BrowserViewerServer instance
                #     viewer_server = BrowserViewerServer(client, port=8000)
                    
                #     # Start the viewer server and get the live view URL
                #     # According to AWS docs: viewer.start() returns the viewer_url
                #     live_view_url = viewer_server.start(open_browser=False)
                    
                #     if live_view_url:
                #         logger.info(f"Live view URL available: {live_view_url}")
                        
                #         # Register the session with the browser router
                #         from app.routers.browser import register_browser_session
                #         register_browser_session(session_id, live_view_url)
                        
                #         # Broadcast live view availability via WebSocket
                #         from app.routers.websocket import manager
                #         import asyncio
                        
                #         # Helper function to safely broadcast async messages
                #         def safe_broadcast(coro):
                #             try:
                #                 loop = asyncio.get_event_loop()
                #                 if loop.is_running():
                #                     # Create a task if we're already in an event loop
                #                     asyncio.create_task(coro)
                #                 else:
                #                     loop.run_until_complete(coro)
                #             except RuntimeError:
                #                 # No event loop, create one
                #                 asyncio.run(coro)
                        
                #         # Broadcast live view availability via WebSocket
                #         safe_broadcast(manager.broadcast_live_view_available(
                #             session_id, live_view_url
                #         ))
                        
                #         # Also broadcast browser viewer ready event
                #         safe_broadcast(manager.broadcast_browser_viewer_ready(
                #             session_id, live_view_url, True, True
                #         ))
                #     else:
                #         logger.warning("BrowserViewerServer did not return a live view URL")
                        
                # except ImportError:
                #     logger.error("BrowserViewerServer not available. Please ensure the interactive_tools module is properly installed.")
                # except Exception as e:
                #     logger.warning(f"Could not start BrowserViewerServer: {e}")
                
                # Initialize Nova Act with the browser session (following Context7 pattern exactly)
                with NovaAct(
                    cdp_endpoint_url=ws_url,
                    cdp_headers=headers,
                    nova_act_api_key=self.nova_act_api_key,
                    starting_page=target_website,
                ) as nova_act:
                    
                    # Execute micro-steps with error detection and credentials
                    execution_summary = self._execute_steps_with_error_detection(
                        nova_act, micro_steps, session_id, credentials
                    )
                    
                    # Convert to dictionary for return
                    result = execution_summary.to_dict()
                    
                    # # Clean up the viewer server when done
                    # if viewer_server:
                    #     try:
                    #         viewer_server.stop()
                    #         logger.info("BrowserViewerServer stopped successfully")
                    #     except Exception as e:
                    #         logger.warning(f"Error stopping BrowserViewerServer: {e}")
                    
                    return result
                    
        except KeyboardInterrupt:
            logger.warning("Nova Act execution interrupted by user (KeyboardInterrupt)")
            return {
                'status': 'interrupted',
                'message': 'Execution was interrupted by user',
                'session_id': execution_plan.get('session_id', 'unknown'),
                'completed_steps': [],
                'failed_step': None,
                'error_detection': None,
                'success_count': 0,
                'failed_count': 1,
                'requires_human': True,
                'suggestions': ['Execution was interrupted, please try again']
            }
        except Exception as e:
            logger.error(f"Failed to execute Nova Act plan: {str(e)}")
            return {
                'status': 'error',
                'message': f'Execution failed: {str(e)}',
                'session_id': execution_plan.get('session_id', 'unknown'),
                'completed_steps': [],
                'failed_step': None,
                'error_detection': None,
                'success_count': 0,
                'failed_count': 1,
                'requires_human': True,
                'suggestions': ['Check browser connection and try again']
            }
    
    def execute_execution_plan(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete automation execution plan from the automation agent.
        Uses thread isolation to avoid asyncio/Playwright conflicts.
        
        Args:
            execution_plan: Complete execution plan from automation agent
            
        Returns:
            Dictionary with execution results
        """
        # Check if we're in an asyncio context
        is_async_context = self._check_asyncio_context()
        
        if is_async_context:
            # Run in separate thread to avoid asyncio/Playwright conflict
            logger.info("🔄 Running Nova Act in separate thread to avoid asyncio conflict")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._execute_nova_act_sync, execution_plan)
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    logger.info("✅ Nova Act execution completed successfully in thread")
                    return result
                except concurrent.futures.TimeoutError:
                    logger.error("❌ Nova Act execution timed out")
                    return {
                        'status': 'error',
                        'message': 'Execution timed out after 5 minutes',
                        'session_id': execution_plan.get('session_id', 'unknown'),
                        'completed_steps': [],
                        'failed_step': None,
                        'error_detection': None,
                        'success_count': 0,
                        'failed_count': 1,
                        'requires_human': True,
                        'suggestions': ['Task took too long, try with simpler steps']
                    }
                except Exception as e:
                    logger.error(f"❌ Nova Act execution failed in thread: {str(e)}")
                    return {
                        'status': 'error',
                        'message': f'Thread execution failed: {str(e)}',
                        'session_id': execution_plan.get('session_id', 'unknown'),
                        'completed_steps': [],
                        'failed_step': None,
                        'error_detection': None,
                        'success_count': 0,
                        'failed_count': 1,
                        'requires_human': True,
                        'suggestions': ['Check browser connection and try again']
                    }
        else:
            # Run directly in sync context (like test script)
            logger.info("✅ Running Nova Act directly in sync context")
            return self._execute_nova_act_sync(execution_plan)
    
    def _execute_steps_with_error_detection(
        self, 
        nova_act: NovaAct, 
        micro_steps: List[Dict[str, Any]], 
        session_id: str,
        credentials: Dict[str, Any] = None
    ) -> NovaActExecutionSummary:
        """Execute micro-steps with intelligent error detection using BOOL_SCHEMA."""
        
        completed_steps = []
        success_count = 0
        failed_count = 0
        failed_step = None
        
        for step in micro_steps:
            try:
                instruction = step.get('instruction', '')
                step_number = step.get('step_number', 0)
                nova_act_type = step.get('nova_act_type', 'general')
                timeout_seconds = step.get('timeout_seconds', 30)
                retry_count = step.get('retry_count', 3)
                
                logger.info(f"Executing step {step_number}: {nova_act_type} - {instruction[:50]}...")
                
                # Execute the step with retry logic and credentials
                execution_result = self._execute_step_with_retry(
                    nova_act, instruction, step_number, nova_act_type, timeout_seconds, retry_count, credentials
                )
                
                completed_steps.append(execution_result)
                
                if execution_result.status == "success":
                    success_count += 1
                    logger.info(f"Step {step_number} completed successfully")
                else:
                    failed_count += 1
                    failed_step = execution_result
                    logger.warning(f"Step {step_number} failed: {execution_result.error_message}")
                    
                    # If step failed, try error detection to understand why
                    try:
                        error_detection = self._detect_errors_with_bool_schema(nova_act)
                        if error_detection.has_difficulties or error_detection.is_stuck_in_loop:
                            logger.warning(f"Error detected after step {step_number}: {error_detection.error_type}")
                            
                            # Return with error detection results
                            return NovaActExecutionSummary(
                                status="failed",
                                message=f"Execution stopped due to error detection at step {step_number}",
                                session_id=session_id,
                                completed_steps=completed_steps,
                                failed_step=failed_step,
                                error_detection=error_detection,
                                success_count=success_count,
                                failed_count=failed_count,
                                requires_human=True,
                                suggestions=error_detection.suggestions
                            )
                    except Exception as e:
                        logger.warning(f"Error detection failed after step {step_number}: {str(e)}")
                
                # Small delay between steps
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error executing step {step_number}: {str(e)}")
                
                execution_result = NovaActExecutionResult(
                    instruction=instruction,
                    status="failed",
                    result_text="",
                    error_message=str(e),
                    execution_time=0.0,
                    retry_count=0,
                    browser_state={}
                )
                
                completed_steps.append(execution_result)
                failed_count += 1
                failed_step = execution_result
                
                # Check for blackhole detection
                error_detection = self._detect_errors_with_bool_schema(nova_act)
                
                if error_detection.is_stuck_in_loop:
                    logger.warning(f"Blackhole detected at step {step_number}")
                    break
        
        # Determine final status
        if failed_count == 0:
            status = "success"
            message = f"Successfully executed all {len(micro_steps)} micro-steps"
            requires_human = False
        elif success_count > 0:
            status = "partial"
            message = f"Executed {len(micro_steps)} micro-steps: {success_count} successful, {failed_count} failed"
            requires_human = True
        else:
            status = "failed"
            message = f"Failed to execute any of the {len(micro_steps)} micro-steps"
            requires_human = True
        
        return NovaActExecutionSummary(
            status=status,
            message=message,
            session_id=session_id,
            completed_steps=completed_steps,
            failed_step=failed_step,
            success_count=success_count,
            failed_count=failed_count,
            requires_human=requires_human,
            suggestions=[]
        )
    
    def _detect_errors_with_bool_schema(self, nova_act: NovaAct) -> NovaActErrorDetection:
        """Detect errors using multiple BOOL_SCHEMA questions with improved prompts."""
        
        try:
            # Question 1: Check for general difficulties with more specific prompt
            difficulties_result = self._safe_act_with_bool_schema(
                nova_act,
                "Look at the current page. Are there any error messages, broken elements, or issues that would prevent me from continuing? If the page looks normal and functional, return false. If you see any errors, problems, or broken elements, return true."
            )
            has_difficulties = difficulties_result
            
            # Question 2: Check if stuck in a loop with more specific prompt
            loop_result = self._safe_act_with_bool_schema(
                nova_act,
                "Am I repeating the same action or seeing the same error multiple times? If I'm making progress or this is the first time seeing this, return false. If I'm stuck repeating the same thing, return true."
            )
            is_stuck_in_loop = loop_result
            
            # Question 3: Check if can proceed with more specific prompt
            proceed_result = self._safe_act_with_bool_schema(
                nova_act,
                "Can I see the next element I need to interact with or the next step I need to take? If yes, return true. If the page is blank, broken, or I can't see what to do next, return false."
            )
            can_proceed = proceed_result
            
            # Determine error type and suggestions
            error_type = None
            suggestions = []
            
            if has_difficulties:
                error_type = "general_difficulties"
                suggestions.append("Check for page errors or unexpected elements")
                suggestions.append("Try refreshing the page or waiting for it to load completely")
            
            if is_stuck_in_loop:
                error_type = "infinite_loop"
                suggestions.append("Stop execution to prevent infinite loops")
                suggestions.append("Review the current step and try a different approach")
                suggestions.append("Check if the page requires different interaction")
            
            if not can_proceed:
                error_type = "cannot_proceed"
                suggestions.append("Current state prevents proceeding to next step")
                suggestions.append("Check for missing elements or blocked actions")
                suggestions.append("Wait for page to load completely before proceeding")
            
            return NovaActErrorDetection(
                has_difficulties=has_difficulties,
                is_stuck_in_loop=is_stuck_in_loop,
                can_proceed=can_proceed,
                error_type=error_type,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error in error detection: {str(e)}")
            return NovaActErrorDetection(
                has_difficulties=True,
                is_stuck_in_loop=False,
                can_proceed=False,
                error_type="detection_error",
                suggestions=[f"Error detection failed: {str(e)}"]
            )
    
    def _execute_step_with_retry(self, nova_act: NovaAct, instruction: str, step_number: int, 
                                nova_act_type: str, timeout_seconds: int, retry_count: int, 
                                credentials: Dict[str, Any] = None) -> NovaActExecutionResult:
        """Execute a single step with retry logic and proper error handling."""
        
        for attempt in range(retry_count + 1):
            try:
                logger.info(f"Step {step_number} attempt {attempt + 1}/{retry_count + 1}")
                
                # Execute the step with secure credential handling
                start_time = time.time()
                
                # Check if this is an input step that needs credentials
                if nova_act_type == "input" and credentials:
                    result = self._execute_input_step_with_credentials(nova_act, instruction, credentials)
                else:
                    result = nova_act.act(instruction)
                
                execution_time = time.time() - start_time
                
                # Parse result
                result_text = ""
                if hasattr(result, 'response') and result.response:
                    result_text = str(result.response)
                elif hasattr(result, 'parsed_response') and result.parsed_response:
                    result_text = str(result.parsed_response)
                else:
                    result_text = str(result)
                
                # Check if the result indicates success
                if self._is_step_successful(result, result_text, nova_act_type):
                    return NovaActExecutionResult(
                        instruction=instruction,
                        status="success",
                        result_text=result_text,
                        error_message=None,
                        execution_time=execution_time,
                        retry_count=attempt,
                        browser_state={}
                    )
                else:
                    # Step didn't succeed, try again if we have retries left
                    if attempt < retry_count:
                        logger.warning(f"Step {step_number} attempt {attempt + 1} didn't succeed, retrying...")
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        # Final attempt failed
                        return NovaActExecutionResult(
                            instruction=instruction,
                            status="failed",
                            result_text=result_text,
                            error_message=f"Step failed after {retry_count + 1} attempts",
                            execution_time=execution_time,
                            retry_count=attempt,
                            browser_state={}
                        )
                        
            except Exception as e:
                logger.warning(f"Step {step_number} attempt {attempt + 1} failed with exception: {str(e)}")
                
                if attempt < retry_count:
                    time.sleep(2)  # Wait before retry
                    continue
                else:
                    # Final attempt failed with exception
                    return NovaActExecutionResult(
                        instruction=instruction,
                        status="failed",
                        result_text="",
                        error_message=f"Step failed with exception after {retry_count + 1} attempts: {str(e)}",
                        execution_time=0.0,
                        retry_count=attempt,
                        browser_state={}
                    )
        
        # This should never be reached, but just in case
        return NovaActExecutionResult(
            instruction=instruction,
            status="failed",
            result_text="",
            error_message="Step failed after all retry attempts",
            execution_time=0.0,
            retry_count=retry_count,
            browser_state={}
        )
    
    def _is_step_successful(self, result, result_text: str, nova_act_type: str) -> bool:
        """Determine if a step was successful based on the result and type."""
        try:
            # Check for explicit success indicators in the result
            if hasattr(result, 'response') and result.response:
                response_lower = str(result.response).lower()
                if any(success_word in response_lower for success_word in ['success', 'completed', 'done', 'finished']):
                    return True
                if any(error_word in response_lower for error_word in ['error', 'failed', 'cannot', 'unable']):
                    return False
            
            # For navigation steps, success is usually just reaching the page
            if nova_act_type == "navigate":
                return True
            
            # For click steps, success is usually if no error occurred
            if nova_act_type == "click":
                return "error" not in result_text.lower()
            
            # For input steps, success is usually if text was entered
            if nova_act_type == "input":
                return "entered" in result_text.lower() or "filled" in result_text.lower()
            
            # For other steps, assume success if no explicit error
            return "error" not in result_text.lower() and "failed" not in result_text.lower()
            
        except Exception as e:
            logger.warning(f"Error checking step success: {str(e)}")
            return True  # Default to success if we can't determine
    
    def _safe_act_with_bool_schema(self, nova_act: NovaAct, prompt: str) -> bool:
        """Safely execute a BOOL_SCHEMA act with fallback handling."""
        try:
            result = nova_act.act(prompt, schema=BOOL_SCHEMA)
            
            # Check if the result is valid
            if hasattr(result, 'matches_schema') and result.matches_schema:
                if hasattr(result, 'parsed_response'):
                    return bool(result.parsed_response)
                elif hasattr(result, 'response'):
                    # Try to parse the response as boolean
                    response_str = str(result.response).lower().strip()
                    if response_str in ['true', 'yes', '1', 'on']:
                        return True
                    elif response_str in ['false', 'no', '0', 'off']:
                        return False
            
            # If schema doesn't match or no parsed response, default to False (no error)
            logger.warning(f"BOOL_SCHEMA result not valid, defaulting to False: {result}")
            return False
            
        except Exception as e:
            logger.warning(f"Error in safe_act_with_bool_schema: {str(e)}, defaulting to False")
            return False
    
    def _execute_input_step_with_credentials(self, nova_act: NovaAct, instruction: str, credentials: Dict[str, Any]) -> Any:
        """
        Execute input step with secure credential handling using Playwright's API.
        
        Args:
            nova_act: Nova Act instance
            instruction: The instruction for the input step
            credentials: User credentials dictionary
            
        Returns:
            Result from Nova Act execution
        """
        try:
            # First, let Nova Act identify the input field
            field_identification_result = nova_act.act(instruction)
            
            # Determine which credential to use based on the instruction
            credential_value = None
            if "username" in instruction.lower() or "email" in instruction.lower():
                credential_value = credentials.get('email', '')
            elif "password" in instruction.lower():
                credential_value = credentials.get('password', '')
            elif "ic" in instruction.lower() or "identity" in instruction.lower():
                credential_value = credentials.get('ic_number', '')
            elif "phone" in instruction.lower():
                credential_value = credentials.get('phone', '')
            
            if credential_value:
                # Use Playwright's API to securely type the credential
                logger.info(f"Securely entering credential for: {instruction[:50]}...")
                nova_act.page.keyboard.type(credential_value)
                
                # Return success result
                return type('Result', (), {
                    'response': f"Successfully entered {len(credential_value)} characters securely",
                    'parsed_response': f"Successfully entered {len(credential_value)} characters securely",
                    'valid_json': True,
                    'matches_schema': True
                })()
            else:
                # No matching credential found, use regular Nova Act
                logger.warning(f"No matching credential found for instruction: {instruction}")
                return field_identification_result
                
        except Exception as e:
            logger.error(f"Error in secure credential input: {str(e)}")
            # Fallback to regular Nova Act execution
            return nova_act.act(instruction)


# Global Nova Act agent instance
nova_act_agent = NovaActAgent()
