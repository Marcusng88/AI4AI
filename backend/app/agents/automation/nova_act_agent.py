"""
Nova Act Agent for browser automation using AWS Bedrock Agent Core Browser.
This agent operates separately from the automation agent and executes Nova Act instructions
on the agentcore browser with advanced monitoring and error handling.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import time
import threading
import concurrent.futures
from dataclasses import dataclass
import json

from nova_act import NovaAct
from bedrock_agentcore.tools.browser_client import BrowserClient

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NovaActExecutionResult:
    """Data class for Nova Act execution results."""
    instruction: str
    status: str  # "success", "failed", "timeout", "blackhole_detected"
    result_text: str
    error_message: Optional[str]
    execution_time: float
    retry_count: int
    browser_state: Dict[str, Any]


@dataclass
class NovaActSession:
    """Data class for Nova Act session tracking."""
    session_id: str
    start_time: datetime
    browser_client: BrowserClient
    nova_act: NovaAct
    current_instruction: str
    execution_history: List[NovaActExecutionResult]
    status: str  # "active", "paused", "blackhole_detected", "completed", "failed"
    blackhole_detection_count: int
    consecutive_failures: int


class NovaActAgent:
    """Nova Act agent for browser automation with advanced monitoring."""
    
    def __init__(self):
        # Configuration
        self.nova_act_api_key = os.getenv("NOVA_ACT_API_KEY")
        self.aws_region = "us-east-1"
        self.iam_role_arn = os.getenv("IAM_ROLE_ARN", "arn:aws:iam::791493234575:role/BedrockAgentCoreBrowserRole")
        
        # AWS credentials
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Session tracking
        self.active_sessions: Dict[str, NovaActSession] = {}
        
        # Blackhole detection configuration
        self.max_consecutive_failures = 3
        self.max_similar_errors = 5
        self.blackhole_timeout_seconds = 300  # 5 minutes
        
        logger.info("Nova Act agent initialized successfully")
    
    async def create_session(self, starting_page: str = "https://www.myeg.com.my", session_id: Optional[str] = None) -> str:
        """
        Create a new Nova Act session with browser client.
        
        Args:
            starting_page: URL to start the browser session
            session_id: Optional session ID
            
        Returns:
            Session ID for the created session
        """
        try:
            session_id = session_id or f"nova_act_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Initialize browser client
            browser_client = await self._initialize_browser_client()
            if not browser_client:
                raise Exception("Failed to initialize browser client")
            
            # Initialize Nova Act
            nova_act = await self._initialize_nova_act(browser_client, starting_page)
            if not nova_act:
                raise Exception("Failed to initialize Nova Act")
            
            # Create session
            session = NovaActSession(
                session_id=session_id,
                start_time=datetime.utcnow(),
                browser_client=browser_client,
                nova_act=nova_act,
                current_instruction="",
                execution_history=[],
                status="active",
                blackhole_detection_count=0,
                consecutive_failures=0
            )
            
            self.active_sessions[session_id] = session
            logger.info(f"Created Nova Act session {session_id} with starting page: {starting_page}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create Nova Act session: {str(e)}")
            raise
    
    async def execute_instruction(self, session_id: str, instruction: str, 
                                timeout_seconds: int = 60) -> NovaActExecutionResult:
        """
        Execute a Nova Act instruction in the specified session.
        
        Args:
            session_id: Session ID
            instruction: Nova Act instruction to execute
            timeout_seconds: Timeout for execution
            
        Returns:
            Nova Act execution result
        """
        try:
            if session_id not in self.active_sessions:
                raise Exception(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            if session.status != "active":
                raise Exception(f"Session {session_id} is not active (status: {session.status})")
            
            logger.info(f"Executing Nova Act instruction in session {session_id}: {instruction[:50]}...")
            
            # Update session state
            session.current_instruction = instruction
            
            # Execute instruction with timeout
            start_time = time.time()
            result = await self._execute_with_timeout(session, instruction, timeout_seconds)
            execution_time = time.time() - start_time
            
            # Parse result
            result_text = ""
            error_message = None
            status = "success"
            
            if hasattr(result, 'response') and result.response:
                result_text = str(result.response)
            elif hasattr(result, 'parsed_response') and result.parsed_response:
                result_text = str(result.parsed_response)
            else:
                result_text = str(result)
            
            # Check for errors
            if hasattr(result, 'error') and result.error:
                error_message = str(result.error)
                status = "failed"
            elif "error" in result_text.lower() or "failed" in result_text.lower():
                error_message = result_text
                status = "failed"
            
            # Check for blackhole detection
            if self._detect_blackhole(session, instruction, result_text, error_message):
                status = "blackhole_detected"
                session.status = "blackhole_detected"
                session.blackhole_detection_count += 1
                logger.warning(f"Blackhole detected in session {session_id}")
            
            # Create execution result
            execution_result = NovaActExecutionResult(
                instruction=instruction,
                status=status,
                result_text=result_text,
                error_message=error_message,
                execution_time=execution_time,
                retry_count=0,
                browser_state=self._get_browser_state(session)
            )
            
            # Update session
            session.execution_history.append(execution_result)
            if status == "failed":
                session.consecutive_failures += 1
            else:
                session.consecutive_failures = 0
            
            logger.info(f"Nova Act instruction completed in {execution_time:.2f}s with status: {status}")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Failed to execute Nova Act instruction: {str(e)}")
            return NovaActExecutionResult(
                instruction=instruction,
                status="failed",
                result_text="",
                error_message=str(e),
                execution_time=0.0,
                retry_count=0,
                browser_state={}
            )
    
    async def execute_execution_plan(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete automation execution plan from the automation agent.
        Uses the correct browser_session context manager pattern.
        
        Args:
            execution_plan: Complete execution plan from automation agent
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Extract plan details
            session_id = execution_plan.get('session_id', f"nova_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
            task_description = execution_plan.get('task_description', '')
            target_website = execution_plan.get('target_website', 'https://www.myeg.com.my')
            micro_steps = execution_plan.get('micro_steps', [])
            execution_strategy = execution_plan.get('execution_strategy', 'sequential')
            
            logger.info(f"Executing automation plan: {task_description}")
            logger.info(f"Target website: {target_website}")
            logger.info(f"Micro-steps count: {len(micro_steps)}")
            logger.info(f"Execution strategy: {execution_strategy}")
            
            # Use the correct browser_session context manager pattern
            from bedrock_agentcore.tools.browser_client import browser_session
            
            results = []
            success_count = 0
            failed_count = 0
            
            try:
                # Use browser_session context manager (correct pattern)
                with browser_session(self.aws_region) as client:
                    ws_url, headers = client.generate_ws_headers()
                    
                    # Initialize Nova Act with the browser session
                    with NovaAct(
                        cdp_endpoint_url=ws_url,
                        cdp_headers=headers,
                        nova_act_api_key=self.nova_act_api_key,
                        starting_page=target_website,
                    ) as nova_act:
                        
                        # Execute micro-steps
                        for step in micro_steps:
                            try:
                                instruction = step.get('instruction', '')
                                timeout_seconds = step.get('timeout_seconds', 60)
                                nova_act_type = step.get('nova_act_type', 'general')
                                
                                logger.info(f"Executing step {step.get('step_number', 0)}: {nova_act_type} - {instruction[:50]}...")
                                
                                # Execute the step using Nova Act
                                result = nova_act.act(instruction)
                                
                                # Parse result
                                result_text = ""
                                if hasattr(result, 'response') and result.response:
                                    result_text = str(result.response)
                                elif hasattr(result, 'parsed_response') and result.parsed_response:
                                    result_text = str(result.parsed_response)
                                else:
                                    result_text = str(result)
                                
                                # Create execution result
                                execution_result = NovaActExecutionResult(
                                    instruction=instruction,
                                    status="success",
                                    result_text=result_text,
                                    error_message=None,
                                    execution_time=0.0,  # Would need to measure actual time
                                    retry_count=0,
                                    browser_state={}
                                )
                                
                                results.append(execution_result)
                                success_count += 1
                                
                                logger.info(f"Step {step.get('step_number', 0)} completed successfully")
                                
                                # Small delay between steps
                                await asyncio.sleep(1)
                                
                            except Exception as e:
                                logger.error(f"Error executing step {step.get('step_number', 0)}: {str(e)}")
                                
                                execution_result = NovaActExecutionResult(
                                    instruction=step.get('instruction', ''),
                                    status="failed",
                                    result_text="",
                                    error_message=str(e),
                                    execution_time=0.0,
                                    retry_count=0,
                                    browser_state={}
                                )
                                
                                results.append(execution_result)
                                failed_count += 1
                                
                                # Check for blackhole detection
                                blackhole_detection = step.get('blackhole_detection', {})
                                if self._detect_blackhole_from_step(step, execution_result, blackhole_detection):
                                    logger.warning("Blackhole detected, stopping execution")
                                    break
                        
            except Exception as e:
                logger.error(f"Browser session error: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Browser session failed: {str(e)}",
                    "requires_human": True
                }
            
            return {
                "status": "success" if failed_count == 0 else "partial" if success_count > 0 else "failed",
                "message": f"Executed {len(micro_steps)} micro-steps: {success_count} successful, {failed_count} failed",
                "session_id": session_id,
                "results": [r.__dict__ for r in results],
                "success_count": success_count,
                "failed_count": failed_count,
                "requires_human": failed_count > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to execute execution plan: {str(e)}")
            return {
                "status": "error",
                "message": f"Execution plan failed: {str(e)}",
                "requires_human": True
            }
    
    async def _execute_sequential(self, micro_steps: List[Dict[str, Any]], session_id: str) -> List[NovaActExecutionResult]:
        """Execute micro-steps sequentially."""
        results = []
        
        for step in micro_steps:
            try:
                # Extract step details
                instruction = step.get('instruction', '')
                timeout_seconds = step.get('timeout_seconds', 60)
                nova_act_type = step.get('nova_act_type', 'general')
                
                logger.info(f"Executing step {step.get('step_number', 0)}: {nova_act_type} - {instruction[:50]}...")
                
                # Execute the step
                result = await self.execute_instruction(session_id, instruction, timeout_seconds)
                results.append(result)
                
                # Check for blackhole detection
                if result.status == "failed":
                    blackhole_detection = step.get('blackhole_detection', {})
                    if self._detect_blackhole_from_step(step, result, blackhole_detection):
                        logger.warning("Blackhole detected, pausing execution")
                        break
                
                # Small delay between steps
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error executing step: {str(e)}")
                results.append(NovaActExecutionResult(
                    instruction=step.get('instruction', ''),
                    status="failed",
                    result_text="",
                    error_message=str(e),
                    execution_time=0.0,
                    retry_count=0,
                    browser_state={}
                ))
        
        return results
    
    async def _execute_parallel(self, micro_steps: List[Dict[str, Any]], session_id: str) -> List[NovaActExecutionResult]:
        """Execute micro-steps in parallel (where possible)."""
        # For now, fallback to sequential execution
        # Parallel execution would require more complex dependency management
        return await self._execute_sequential(micro_steps, session_id)
    
    def _detect_blackhole_from_step(self, step: Dict[str, Any], result: NovaActExecutionResult, blackhole_config: Dict[str, Any]) -> bool:
        """Detect blackhole based on step configuration."""
        try:
            max_failures = blackhole_config.get('max_consecutive_failures', 3)
            max_errors = blackhole_config.get('max_similar_errors', 5)
            
            # Simple blackhole detection based on step configuration
            if result.status == "failed":
                # This would need to track consecutive failures per step
                # For now, return False as a placeholder
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in blackhole detection: {str(e)}")
            return False
    
    async def pause_session(self, session_id: str) -> bool:
        """Pause a Nova Act session."""
        try:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            session.status = "paused"
            logger.info(f"Paused Nova Act session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause session {session_id}: {str(e)}")
            return False
    
    async def resume_session(self, session_id: str) -> bool:
        """Resume a paused Nova Act session."""
        try:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            if session.status == "paused":
                session.status = "active"
                logger.info(f"Resumed Nova Act session {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {str(e)}")
            return False
    
    async def close_session(self, session_id: str) -> bool:
        """Close a Nova Act session and cleanup resources."""
        try:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Cleanup Nova Act
            if session.nova_act:
                await self._cleanup_nova_act(session.nova_act)
            
            # Cleanup browser client
            if session.browser_client:
                await self._cleanup_browser_client(session.browser_client)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"Closed Nova Act session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {str(e)}")
            return False
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a Nova Act session."""
        if session_id not in self.active_sessions:
            return {"status": "not_found"}
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "status": session.status,
            "start_time": session.start_time.isoformat(),
            "current_instruction": session.current_instruction,
            "execution_count": len(session.execution_history),
            "consecutive_failures": session.consecutive_failures,
            "blackhole_detection_count": session.blackhole_detection_count,
            "browser_state": self._get_browser_state(session)
        }
    
    async def _initialize_browser_client(self) -> Optional[BrowserClient]:
        """Initialize AWS Bedrock Agent Core Browser client using browser_session context manager."""
        try:
            logger.info("Initializing browser client for Nova Act agent...")
            
            # Use the correct browser_session context manager approach
            from bedrock_agentcore.tools.browser_client import browser_session
            
            # Create browser session using the context manager
            # This is the correct way according to the documentation
            browser_client = browser_session(self.aws_region)
            browser_client.__enter__()  # Start the session
            
            logger.info("Browser client initialized successfully for Nova Act agent")
            return browser_client
            
        except Exception as e:
            logger.error(f"Failed to initialize browser client: {str(e)}")
            return None
    
    async def _initialize_nova_act(self, browser_client: BrowserClient, starting_page: str) -> Optional[NovaAct]:
        """Initialize Nova Act with browser client using the correct pattern."""
        try:
            logger.info(f"Initializing Nova Act with starting page: {starting_page}")
            
            # Generate WebSocket URL and headers from browser client
            ws_url, headers = browser_client.generate_ws_headers()
            
            # Initialize Nova Act with the correct parameters
            nova_act = NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                preview={"playwright_actuation": True},
                nova_act_api_key=self.nova_act_api_key,
                starting_page=starting_page
            )
            
            # Start Nova Act (following the documentation pattern)
            nova_act.start()
            
            logger.info("Nova Act initialized and started successfully")
            return nova_act
            
        except Exception as e:
            logger.error(f"Failed to initialize Nova Act: {str(e)}")
            return None
    
    async def _execute_with_timeout(self, session: NovaActSession, instruction: str, timeout_seconds: int) -> Any:
        """Execute Nova Act instruction with timeout."""
        try:
            # Run Nova Act in a thread pool to avoid asyncio conflicts
            loop = asyncio.get_event_loop()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the Nova Act execution to the thread pool
                future = executor.submit(self._run_nova_act_sync, session.nova_act, instruction)
                
                # Wait for the result with timeout
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: future.result()),
                    timeout=timeout_seconds
                )
                
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"Nova Act instruction timed out after {timeout_seconds} seconds")
            raise Exception(f"Instruction timed out after {timeout_seconds} seconds")
        except Exception as e:
            logger.error(f"Failed to execute Nova Act instruction: {str(e)}")
            raise e
    
    def _run_nova_act_sync(self, nova_act: NovaAct, instruction: str) -> Any:
        """Run Nova Act synchronously in a separate thread."""
        try:
            # Execute the instruction using the correct Nova Act pattern
            result = nova_act.act(instruction)
            logger.info(f"Nova Act executed instruction: {instruction[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Nova Act execution failed in thread: {str(e)}")
            raise e
    
    def _detect_blackhole_from_step(self, step: Dict[str, Any], execution_result: NovaActExecutionResult, blackhole_detection: Dict[str, Any]) -> bool:
        """Detect blackhole from step execution result."""
        try:
            # Check for consecutive failures
            max_consecutive_failures = blackhole_detection.get('max_consecutive_failures', 3)
            max_similar_errors = blackhole_detection.get('max_similar_errors', 2)
            monitoring_keywords = blackhole_detection.get('monitoring_keywords', [])
            
            # Simple blackhole detection based on error patterns
            if execution_result.status == "failed" and execution_result.error_message:
                error_lower = execution_result.error_message.lower()
                
                # Check for monitoring keywords
                for keyword in monitoring_keywords:
                    if keyword.lower() in error_lower:
                        logger.warning(f"Blackhole keyword detected: {keyword}")
                        return True
                
                # Check for repetitive error patterns
                if "timeout" in error_lower or "not found" in error_lower:
                    logger.warning("Potential blackhole detected: repetitive error pattern")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in blackhole detection: {str(e)}")
            return False
    
    def _detect_blackhole(self, session: NovaActSession, instruction: str, result_text: str, error_message: Optional[str]) -> bool:
        """Detect if the session is stuck in a blackhole."""
        try:
            # Check for consecutive failures
            if session.consecutive_failures >= self.max_consecutive_failures:
                logger.warning(f"Blackhole detected: {session.consecutive_failures} consecutive failures")
                return True
            
            # Check for similar errors repeating
            recent_results = session.execution_history[-self.max_similar_errors:]
            similar_errors = [r for r in recent_results if r.status == "failed" and r.error_message]
            
            if len(similar_errors) >= self.max_similar_errors:
                logger.warning(f"Blackhole detected: {len(similar_errors)} similar errors")
                return True
            
            # Check for timeout scenarios
            if error_message and "timeout" in error_message.lower():
                if len([r for r in recent_results if "timeout" in (r.error_message or "").lower()]) >= 3:
                    logger.warning("Blackhole detected: Multiple timeout errors")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in blackhole detection: {str(e)}")
            return False
    
    def _get_browser_state(self, session: NovaActSession) -> Dict[str, Any]:
        """Get current browser state."""
        try:
            return {
                "session_active": session.status == "active",
                "current_url": "unknown",  # Would need to get from browser
                "execution_count": len(session.execution_history),
                "last_instruction": session.current_instruction,
                "consecutive_failures": session.consecutive_failures
            }
        except Exception as e:
            logger.error(f"Error getting browser state: {str(e)}")
            return {}
    
    async def _check_step_conditions(self, session_id: str, enhanced_step: Any) -> bool:
        """Check if step conditions are met before execution."""
        try:
            # This would implement condition checking logic
            # For now, return True as a placeholder
            return True
        except Exception as e:
            logger.error(f"Error checking step conditions: {str(e)}")
            return False
    
    async def _apply_edge_case_recovery(self, session_id: str, enhanced_step: Any, failed_result: NovaActExecutionResult) -> NovaActExecutionResult:
        """Apply edge case recovery to a failed execution."""
        try:
            # Find applicable edge case
            applicable_edge_case = None
            for edge_case in enhanced_step.edge_cases:
                condition = edge_case.get('condition', '')
                if condition in (failed_result.error_message or "").lower():
                    applicable_edge_case = edge_case
                    break
            
            if applicable_edge_case:
                # Apply the edge case recovery action
                recovery_instruction = applicable_edge_case.get('nova_instruction', '')
                if recovery_instruction:
                    logger.info(f"Applying edge case recovery: {recovery_instruction}")
                    return await self.execute_instruction(session_id, recovery_instruction)
            
            return failed_result
            
        except Exception as e:
            logger.error(f"Error applying edge case recovery: {str(e)}")
            return failed_result
    
    async def _cleanup_nova_act(self, nova_act: NovaAct):
        """Cleanup Nova Act resources."""
        try:
            if nova_act:
                # Stop Nova Act
                nova_act.stop()
                logger.info("Nova Act cleaned up successfully")
        except Exception as e:
            logger.warning(f"Error cleaning up Nova Act: {str(e)}")
    
    async def _cleanup_browser_client(self, browser_client: BrowserClient):
        """Cleanup browser client resources."""
        try:
            if browser_client:
                # Use the context manager exit method
                browser_client.__exit__(None, None, None)
                logger.info("Browser client cleaned up successfully")
        except Exception as e:
            logger.warning(f"Error cleaning up browser client: {str(e)}")


# Global Nova Act agent instance
nova_act_agent = NovaActAgent()
