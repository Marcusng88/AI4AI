"""
Automation Agent using Browser-Use for browser automation with Context7 integration.
Handles the actual execution of government service tasks using remote browser capabilities.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

from browser_use import Agent as BrowserAgent, Browser, BrowserProfile , ChatGoogle
from boto3.session import Session

# HyperBrowser integration
try:
    from hyperbrowser import AsyncHyperbrowser
    HYPERBROWSER_AVAILABLE = True
except ImportError:
    HYPERBROWSER_AVAILABLE = False

# Removed human-in-the-loop integration - using simple chat-based approach

from app.core.logging import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Import WebSocket notification functions
try:
    from app.routers.websocket import notify_browser_status, notify_browser_viewer_ready
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class AutomationAgent:
    """Automation agent using Browser-Use with remote browser capabilities."""
    
    def __init__(self):
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Browser instance will be initialized when needed
        self.browser = None
        
        # HyperBrowser client and session
        self.hyperbrowser_client = None
        self.hyperbrowser_session = None
        
        logger.info("Automation agent initialized successfully with Browser-Use")
    
    def _initialize_llm(self) -> ChatGoogle:
        """Initialize Anthropic LLM for the automation agent."""
        try:
            # Use direct Anthropic API instead of Bedrock for browser-use
            return ChatGoogle(
                model="gemini-2.5-pro",
                temperature=0.0,
                api_key=os.getenv('GEMINI_API_KEY')
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    async def execute_automation_task(self, task: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute automation task using Browser-Use with remote browser capabilities.
        
        Args:
            task: Automation task dictionary with instructions and context
            session_id: Session ID for browser viewer events (optional)
            
        Returns:
            Result dictionary with status and details
        """
        start_time = datetime.utcnow()
        
        try:
            # Store current session ID for browser viewer events
            self.current_session_id = session_id
            
            # Initialize browser if not already done
            if not self.browser:
                await self._initialize_browser(session_id)
            
            if not self.browser:
                return {
                    "status": "error",
                    "message": "Failed to initialize browser. Please try again later.",
                    "requires_human": False
                }
            
            # Execute the automation task
            result = await self._execute_browser_task(task)
            
            # Add browser viewer information to the result if browser is active
            if self.browser and hasattr(self, 'hyperbrowser_session') and self.hyperbrowser_session:
                # Try both camelCase and snake_case for live URL
                live_url = getattr(self.hyperbrowser_session, 'liveUrl', None)
                if not live_url:
                    live_url = getattr(self.hyperbrowser_session, 'live_url', None)
                
                if live_url:
                    result['browser_viewer'] = {
                        'live_url': live_url,
                        'is_available': True,
                        'session_id': self.hyperbrowser_session.id if hasattr(self.hyperbrowser_session, 'id') else None
                    }
                    logger.info(f"Added browser viewer info to response: {live_url}")
            
            # Record successful execution
            response_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Automation task completed in {response_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            # Record failed execution
            response_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Automation execution failed: {str(e)}")
            
            return {
                "status": "error",
                "message": f"Task execution failed: {str(e)}",
                "requires_human": True
            }
    
    async def _initialize_browser(self, session_id: Optional[str] = None) -> bool:
        """Initialize browser with remote capabilities using Browser-Use + HyperBrowser."""
        try:
            logger.info("Initializing browser with Browser-Use...")
            
            # Ensure clean state before initializing
            await self.ensure_clean_state()
            
            # Check for HyperBrowser API key first
            hyperbrowser_api_key = os.getenv('HYPERBROWSER_API_KEY')
            
            if hyperbrowser_api_key and HYPERBROWSER_AVAILABLE:
                # Use HyperBrowser to create remote browser session
                logger.info("Using HyperBrowser for remote browser session...")
                return await self._initialize_hyperbrowser(session_id)
                
            # Check for remote browser configuration
            remote_cdp_url = os.getenv('REMOTE_BROWSER_CDP_URL')
            
            if remote_cdp_url:
                # Use remote browser via CDP
                logger.info(f"Connecting to remote browser at: {remote_cdp_url}")
                self.browser = Browser(cdp_url=remote_cdp_url)
                logger.info("Successfully connected to remote browser!")
                return True
                
            else:
                # Fallback to local browser
                logger.info("Using local browser...")
                return await self._initialize_local_browser(session_id)
                
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            return False
    
    async def _initialize_hyperbrowser(self, session_id: Optional[str] = None) -> bool:
        """Initialize HyperBrowser remote session and connect Browser-Use to it."""
        try:
            if not HYPERBROWSER_AVAILABLE:
                logger.error("HyperBrowser SDK not available. Please install: pip install hyperbrowser")
                return False
                
            hyperbrowser_api_key = os.getenv('HYPERBROWSER_API_KEY')
            if not hyperbrowser_api_key:
                logger.error("HYPERBROWSER_API_KEY environment variable not set")
                return False
            
            # Initialize HyperBrowser client
            logger.info("Initializing HyperBrowser client...")
            self.hyperbrowser_client = AsyncHyperbrowser(api_key=hyperbrowser_api_key)
            
            # Clean up any existing sessions first
            await self._cleanup_existing_sessions()
            
            # Create a new browser session with HyperBrowser
            logger.info("Creating new HyperBrowser session...")
            from hyperbrowser.models import CreateSessionParams
            
            # Configure session parameters for better automation
            session_params = CreateSessionParams(
                use_stealth=True,  # Enable stealth mode to avoid detection
                solve_captchas=False,  # Auto-solve captchas when possible
                adblock=True  # Block ads for faster loading
            )
            
            self.hyperbrowser_session = await self.hyperbrowser_client.sessions.create(
                params=session_params
            )
            
            logger.info(f"HyperBrowser session created with ID: {self.hyperbrowser_session.id}")
            
            # Get the CDP URL from HyperBrowser session
            # According to HyperBrowser docs, wsEndpoint is the CDP URL
            ws_endpoint = getattr(self.hyperbrowser_session, 'wsEndpoint', None)
            if not ws_endpoint:
                # Fallback to ws_endpoint (lowercase) if wsEndpoint not available
                ws_endpoint = getattr(self.hyperbrowser_session, 'ws_endpoint', None)
            
            if not ws_endpoint:
                logger.error("No WebSocket endpoint (CDP URL) found in HyperBrowser session")
                logger.info(f"Available session attributes: {dir(self.hyperbrowser_session)}")
                return await self._initialize_local_browser(session_id)
            
            logger.info(f"Using HyperBrowser CDP URL: {ws_endpoint}")
            
            # Initialize Browser-Use with the WebSocket endpoint as CDP URL
            # This is the correct way to connect browser-use to HyperBrowser
            try:
                self.browser = Browser(cdp_url=ws_endpoint)
                logger.info("Successfully connected Browser-Use to HyperBrowser via CDP")
            except Exception as e:
                logger.error(f"Failed to connect Browser-Use to HyperBrowser: {e}")
                logger.info("Falling back to local browser")
                return await self._initialize_local_browser(session_id)
            
            # Emit browser viewer event with live URL
            # Try both camelCase and snake_case for live URL
            live_url = getattr(self.hyperbrowser_session, 'liveUrl', None)
            if not live_url:
                live_url = getattr(self.hyperbrowser_session, 'live_url', None)
            
            if live_url:
                logger.info(f"Browser live URL available: {live_url}")
                # Notify WebSocket clients about browser viewer ready
                if WEBSOCKET_AVAILABLE and session_id:
                    try:
                        await notify_browser_viewer_ready(
                            session_id=session_id,
                            live_url=live_url,
                            browser_connected=True,
                            hyperbrowser_session_active=True
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify WebSocket clients: {e}")
            
            logger.info("Successfully connected Browser-Use to HyperBrowser!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize HyperBrowser: {str(e)}")
            # Clean up on failure
            await self._cleanup_hyperbrowser_session()
            return False
    
    async def _initialize_local_browser(self, session_id: Optional[str] = None) -> bool:
        """Initialize local browser as fallback."""
        try:
            # Create local browser with optimized profile
            browser_profile = BrowserProfile(
                headless=False,  # Set to True for headless mode
                minimum_wait_page_load_time=0.5,
                wait_between_actions=0.3,
                keep_alive=True
            )
            
            # Initialize local browser
            local_browser = Browser(
                browser_profile=browser_profile,
                keep_alive=True
            )
            
            # Start local browser
            await local_browser.start()
            self.browser = local_browser
            
            logger.info("Local browser initialized successfully")
            
            # Notify WebSocket clients about local browser status
            if WEBSOCKET_AVAILABLE and session_id:
                try:
                    await notify_browser_status(
                        session_id=session_id,
                        status={
                            "status": "active",
                            "browser_connected": True,
                            "hyperbrowser_session_active": False
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to notify WebSocket clients: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize local browser: {str(e)}")
            return False
    
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
    
    async def _execute_browser_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser automation task."""
        try:
            task_type = task.get("task_type", "unknown")
            instructions = task.get("instructions", "")
            user_context = task.get("user_context", {})
            
            logger.info(f"Executing automation task: {task_type}")
            
            if task_type == "malaysian_government_service":
                return await self._execute_government_service_task(instructions, user_context)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported task type: {task_type}",
                    "requires_human": True
                }
                
        except Exception as e:
            logger.error(f"Browser task execution failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Task execution failed: {str(e)}",
                "requires_human": True
            }
    
    async def _execute_government_service_task(self, instructions: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute any Malaysian government service task using Browser-Use."""
        try:
            # Enhance instructions with human context if available
            enhanced_instructions = self._enhance_instructions_with_context(instructions, user_context)
            
            # Create browser agent with the instructions
            browser_agent = BrowserAgent(
                task=enhanced_instructions,
                llm=self.llm,
                browser=self.browser,
            )
            
            # Execute the task
            logger.info("Starting browser automation for government service...")
            
            result = await browser_agent.run(max_steps=20)
            
            # Parse the result - agent.run() returns AgentHistoryList
            # Extract meaningful information from the history
            result_text = ""
            
            logger.info(f"Processing agent result of type: {type(result)}")
            
            # Get the final result if available
            if hasattr(result, 'final_result') and result.final_result():
                final_result = result.final_result()
                logger.info(f"Found final result: {final_result}")
                result_text = str(final_result)
            elif hasattr(result, 'extracted_content'):
                # Get all extracted content
                extracted_content = result.extracted_content()
                logger.info(f"Found extracted content: {extracted_content}")
                if extracted_content:
                    result_text = " ".join([str(content) for content in extracted_content if content])
            
            # If no extracted content, try to get action results
            if not result_text and hasattr(result, 'action_results'):
                action_results = result.action_results()
                logger.info(f"Found action results: {len(action_results) if action_results else 0} actions")
                if action_results:
                    result_text = " ".join([str(action.extracted_content) for action in action_results if hasattr(action, 'extracted_content') and action.extracted_content])
            
            # Fallback to string representation if nothing else works
            if not result_text:
                logger.warning("No meaningful content found, using string representation of result")
                try:
                    result_text = str(result)
                except Exception as str_error:
                    logger.error(f"Failed to convert result to string: {str_error}")
                    result_text = f"Result processing failed: {str(str_error)}"
            
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
    
    async def _cleanup_existing_sessions(self):
        """Clean up any existing HyperBrowser sessions before creating a new one."""
        try:
            if not self.hyperbrowser_client:
                return
                
            logger.info("Checking for existing HyperBrowser sessions...")
            
            # List all sessions - returns SessionListResponse with sessions property
            response = await self.hyperbrowser_client.sessions.list()
            all_sessions = response.sessions if hasattr(response, 'sessions') else []
            
            # Filter for active sessions only
            sessions = [session for session in all_sessions if hasattr(session, 'status') and session.status == 'active']
            
            if sessions and len(sessions) > 0:
                logger.info(f"Found {len(sessions)} existing session(s), cleaning up...")
                
                # Stop all existing sessions
                for session in sessions:
                    try:
                        logger.info(f"Stopping existing session: {session.id}")
                        await self.hyperbrowser_client.sessions.stop(session.id)
                    except Exception as e:
                        logger.warning(f"Failed to stop session {session.id}: {str(e)}")
                        
                logger.info("All existing sessions cleaned up")
            else:
                logger.info("No existing sessions found")
                
        except Exception as e:
            logger.warning(f"Error cleaning up existing sessions: {str(e)}")
            # Don't fail initialization if cleanup fails

    async def _cleanup_hyperbrowser_session(self):
        """Clean up HyperBrowser session resources."""
        try:
            if self.hyperbrowser_session and self.hyperbrowser_client:
                logger.info(f"Stopping HyperBrowser session: {self.hyperbrowser_session.id}")
                await self.hyperbrowser_client.sessions.stop(self.hyperbrowser_session.id)
                self.hyperbrowser_session = None
                
            if self.hyperbrowser_client:
                self.hyperbrowser_client = None
                
        except Exception as e:
            logger.error(f"Error cleaning up HyperBrowser session: {str(e)}")
    
    async def close_browser(self):
        """Close browser and cleanup resources."""
        try:
            if self.browser:
                logger.info("Closing browser...")
                await self.browser.close()
                self.browser = None
                
            # Clean up HyperBrowser session if it exists
            await self._cleanup_hyperbrowser_session()
                
            logger.info("Browser closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    async def ensure_clean_state(self):
        """Ensure we start with a clean state by closing any existing sessions."""
        try:
            logger.info("Ensuring clean state before browser initialization...")
            
            # Close any existing browser
            if self.browser:
                await self.close_browser()
            
            # Initialize HyperBrowser client for cleanup if needed
            hyperbrowser_api_key = os.getenv('HYPERBROWSER_API_KEY')
            if hyperbrowser_api_key and HYPERBROWSER_AVAILABLE:
                temp_client = AsyncHyperbrowser(api_key=hyperbrowser_api_key)
                try:
                    response = await temp_client.sessions.list()
                    all_sessions = response.sessions if hasattr(response, 'sessions') else []
                    
                    # Filter for active sessions only
                    sessions = [session for session in all_sessions if hasattr(session, 'status') and session.status == 'active']
                    if sessions and len(sessions) > 0:
                        logger.info(f"Found {len(sessions)} existing session(s) during cleanup...")
                        for session in sessions:
                            try:
                                await temp_client.sessions.stop(session.id)
                                logger.info(f"Stopped session: {session.id}")
                            except Exception as e:
                                logger.warning(f"Failed to stop session {session.id}: {str(e)}")
                except Exception as e:
                    logger.warning(f"Error during cleanup: {str(e)}")
                finally:
                    # Don't keep the temp client
                    pass
                    
            logger.info("Clean state ensured")
            
        except Exception as e:
            logger.warning(f"Error ensuring clean state: {str(e)}")
            # Don't fail if cleanup doesn't work
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get automation agent health status."""
        return {
            "status": "healthy" if self.browser else "no_browser",
            "browser_connected": self.browser is not None,
            "hyperbrowser_available": HYPERBROWSER_AVAILABLE,
            "hyperbrowser_session_active": self.hyperbrowser_session is not None,
            "hyperbrowser_live_url": getattr(self.hyperbrowser_session, 'live_url', None) if self.hyperbrowser_session else None,
        }
    
    # Removed human intervention methods - using simple chat-based approach
    
    # Removed browser viewer event method - using simple chat-based approach


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
