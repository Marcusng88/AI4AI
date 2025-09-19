"""
Lifecycle Hooks for Browser-Use Agent
Provides automatic human intervention at key points during task execution.
"""

import asyncio
from typing import Optional, Dict, Any
from browser_use import Agent
from browser_use.browser.events import ScreenshotEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


class AutomationHooks:
    """Lifecycle hooks for automation agent with human intervention capabilities."""
    
    def __init__(self, enable_auto_intervention: bool = True, intervention_threshold: int = 5):
        """
        Initialize automation hooks.
        
        Args:
            enable_auto_intervention: Whether to enable automatic human intervention
            intervention_threshold: Number of failed attempts before requesting human help
        """
        self.enable_auto_intervention = enable_auto_intervention
        self.intervention_threshold = intervention_threshold
        self.failed_attempts = 0
        self.last_url = None
        self.stuck_counter = 0
        self.error_patterns = [
            "error", "failed", "unable", "cannot", "invalid", "rejected", 
            "forbidden", "unauthorized", "blocked", "timeout"
        ]
    
    async def on_step_start(self, agent: Agent) -> None:
        """
        Hook called at the start of each agent step.
        Monitors for potential issues and intervenes when necessary.
        """
        try:
            # Get current browser state
            state = await agent.browser_session.get_browser_state_summary()
            current_url = state.url
            
            # Check if agent is stuck on the same page
            if current_url == self.last_url:
                self.stuck_counter += 1
            else:
                self.stuck_counter = 0
                self.last_url = current_url
            
            # Log current state
            logger.info(f"Step starting - URL: {current_url}, Stuck counter: {self.stuck_counter}")
            
            # Check for intervention conditions
            if self.enable_auto_intervention:
                await self._check_intervention_conditions(agent, state)
                
        except Exception as e:
            logger.error(f"Error in on_step_start hook: {e}")
    
    async def on_step_end(self, agent: Agent) -> None:
        """
        Hook called at the end of each agent step.
        Analyzes step results and provides intervention if needed.
        """
        try:
            # Get the latest action result
            history = agent.history.model_actions()
            if not history:
                return
            
            latest_action = history[-1] if history else None
            
            # Check if the action failed
            if latest_action and self._is_action_failed(latest_action):
                self.failed_attempts += 1
                logger.warning(f"Action may have failed. Failed attempts: {self.failed_attempts}")
                
                if self.enable_auto_intervention and self.failed_attempts >= self.intervention_threshold:
                    await self._request_human_intervention(agent, "Multiple failed attempts detected")
                    self.failed_attempts = 0  # Reset counter after intervention
            else:
                # Reset failed attempts on successful action
                if self.failed_attempts > 0:
                    self.failed_attempts = max(0, self.failed_attempts - 1)
                    
        except Exception as e:
            logger.error(f"Error in on_step_end hook: {e}")
    
    async def _check_intervention_conditions(self, agent: Agent, state: Any) -> None:
        """Check various conditions that might require human intervention."""
        
        # Check if agent is stuck on the same page
        if self.stuck_counter >= 3:
            await self._request_human_intervention(
                agent, 
                f"Agent appears stuck on the same page: {state.url}"
            )
            self.stuck_counter = 0  # Reset after intervention
        
        # Check for error pages
        page_title = await agent.browser_session.get_current_page_title()
        if page_title and any(error in page_title.lower() for error in self.error_patterns):
            await self._request_human_intervention(
                agent,
                f"Detected error page with title: {page_title}"
            )
        
        # Check for authentication or login pages
        if any(keyword in state.url.lower() for keyword in ['login', 'signin', 'auth', 'captcha']):
            await self._request_human_intervention(
                agent,
                f"Detected authentication page: {state.url}"
            )
    
    def _is_action_failed(self, action: Dict[str, Any]) -> bool:
        """Determine if an action likely failed based on its result."""
        
        if not isinstance(action, dict):
            return False
        
        # Check action result for failure indicators
        action_str = str(action).lower()
        return any(error in action_str for error in self.error_patterns)
    
    async def _request_human_intervention(self, agent: Agent, reason: str) -> None:
        """Request human intervention when automated execution encounters issues."""
        
        try:
            logger.info(f"Requesting human intervention: {reason}")
            
            # Pause the agent
            agent.pause()
            
            # Take a screenshot for context
            try:
                screenshot_event = agent.browser_session.event_bus.dispatch(
                    ScreenshotEvent(full_page=False)
                )
                await screenshot_event
                logger.info("Screenshot taken for human review")
            except Exception as e:
                logger.warning(f"Could not take screenshot: {e}")
            
            # Get current page info
            try:
                current_url = await agent.browser_session.get_current_page_url()
                page_title = await agent.browser_session.get_current_page_title()
            except Exception as e:
                logger.warning(f"Could not get page info: {e}")
                current_url = "unknown"
                page_title = "unknown"
            
            # Display intervention request
            print("\n" + "="*70)
            print("🚨 AUTOMATIC INTERVENTION TRIGGERED")
            print("="*70)
            print(f"Reason: {reason}")
            print(f"Current URL: {current_url}")
            print(f"Page Title: {page_title}")
            print("-"*70)
            print("The agent has encountered an issue and needs your help.")
            print("Options:")
            print("1. Press Enter to let the agent continue")
            print("2. Type 'stop' to stop the current task")
            print("3. Type 'debug' to get more information")
            print("4. Provide specific instructions")
            
            # Get human input
            try:
                response = input("\nYour action: ").strip().lower()
                
                if response == "stop":
                    logger.info("Human chose to stop the task")
                    print("Task stopped by human intervention.")
                    return  # Don't resume
                elif response == "debug":
                    await self._provide_debug_info(agent)
                    input("Press Enter to continue...")
                elif response and response != "":
                    logger.info(f"Human provided instructions: {response}")
                    print(f"Instructions noted: {response}")
                    print("Agent will continue with these instructions in mind.")
                
                # Resume the agent
                agent.resume()
                logger.info("Agent resumed after human intervention")
                
            except KeyboardInterrupt:
                logger.info("Human cancelled intervention - stopping task")
                print("\nTask cancelled by human.")
                return  # Don't resume
                
        except Exception as e:
            logger.error(f"Error during human intervention: {e}")
            # Resume agent even if intervention failed
            try:
                agent.resume()
            except:
                pass
    
    async def _provide_debug_info(self, agent: Agent) -> None:
        """Provide debug information to help human understand the current state."""
        
        try:
            print("\n" + "-"*50)
            print("🔍 DEBUG INFORMATION")
            print("-"*50)
            
            # Browser state
            try:
                state = await agent.browser_session.get_browser_state_summary()
                print(f"Current URL: {state.url}")
                print(f"Page loaded: {getattr(state, 'loaded', 'unknown')}")
            except Exception as e:
                print(f"Could not get browser state: {e}")
            
            # Recent actions
            try:
                actions = agent.history.model_actions()
                if actions:
                    print(f"\nRecent actions ({len(actions)} total):")
                    for i, action in enumerate(actions[-3:], 1):  # Show last 3 actions
                        print(f"  {i}. {action}")
                else:
                    print("\nNo actions recorded yet")
            except Exception as e:
                print(f"Could not get action history: {e}")
            
            # Visited URLs
            try:
                urls = agent.history.urls()
                if urls:
                    print(f"\nVisited URLs ({len(urls)} total):")
                    for i, url in enumerate(urls[-3:], 1):  # Show last 3 URLs
                        print(f"  {i}. {url}")
                else:
                    print("\nNo URLs visited yet")
            except Exception as e:
                print(f"Could not get URL history: {e}")
            
            # Current task
            print(f"\nCurrent task: {agent.task}")
            
            # Agent settings
            print(f"Max steps: {getattr(agent.settings, 'max_steps', 'unknown')}")
            print(f"Current step: {getattr(agent, 'current_step', 'unknown')}")
            
            print("-"*50)
            
        except Exception as e:
            print(f"Error providing debug info: {e}")


# Convenience function to create hooks with default settings
def create_automation_hooks(enable_auto_intervention: bool = True, 
                          intervention_threshold: int = 5) -> AutomationHooks:
    """
    Create automation hooks with specified settings.
    
    Args:
        enable_auto_intervention: Whether to enable automatic human intervention
        intervention_threshold: Number of failed attempts before requesting human help
        
    Returns:
        AutomationHooks instance
    """
    return AutomationHooks(enable_auto_intervention, intervention_threshold)


__all__ = ['AutomationHooks', 'create_automation_hooks']
