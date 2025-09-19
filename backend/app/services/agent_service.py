"""Agent service for managing AI agents."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from strands import Agent

from app.models.responses import AgentStatusResponse
from app.models.requests import Language
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """Service for managing AI agents."""
    
    def __init__(self):
        """Initialize agent service."""
        self.agent_instances: Dict[str, Agent] = {}
        self.agents = {
            "coordinator": {
                "name": "Coordinator Agent",
                "status": "active",
                "capabilities": [
                    "Intent recognition",
                    "Task routing",
                    "Session management",
                    "Multi-language support"
                ],
                "agent_type": "strands"
            },
            "website_researcher": {
                "name": "Website Researcher Agent",
                "status": "active",
                "capabilities": [
                    "Government website discovery",
                    "Service requirement analysis",
                    "Website classification",
                    "Multi-language content analysis"
                ],
                "agent_type": "strands"
            },
            "information_gather": {
                "name": "Information Gather Agent",
                "status": "active",
                "capabilities": [
                    "Credential requirement analysis",
                    "Form structure analysis",
                    "Data validation",
                    "Vector RAG operations"
                ],
                "agent_type": "strands"
            },
            "crawler": {
                "name": "Crawler Agent",
                "status": "inactive",  # Will be activated in Phase 3
                "capabilities": [
                    "Website crawling",
                    "UI element mapping",
                    "Change detection",
                    "Layout analysis"
                ],
                "agent_type": "strands"
            },
            "automation": {
                "name": "Automation Agent",
                "status": "active",
                "capabilities": [
                    "Website navigation",
                    "Payment link extraction",
                    "Form filling assistance",
                    "Screenshot capture"
                ],
                "agent_type": "strands"
            }
        }
    
    async def list_all_agents(self) -> List[AgentStatusResponse]:
        """List all available agents and their status."""
        
        agents = []
        for agent_id, agent_info in self.agents.items():
            agents.append(AgentStatusResponse(
                agent_name=agent_id,
                status=agent_info["status"],
                last_updated=datetime.utcnow().isoformat(),
                capabilities=agent_info["capabilities"]
            ))
        
        logger.info(f"Listed {len(agents)} agents")
        return agents
    
    async def get_agent_status(self, agent_name: str) -> Optional[AgentStatusResponse]:
        """Get status of a specific agent."""
        
        if agent_name not in self.agents:
            return None
        
        agent_info = self.agents[agent_name]
        
        return AgentStatusResponse(
            agent_name=agent_name,
            status=agent_info["status"],
            last_updated=datetime.utcnow().isoformat(),
            capabilities=agent_info["capabilities"]
        )
    
    async def restart_agent(self, agent_name: str) -> bool:
        """Restart a specific agent."""
        
        if agent_name not in self.agents:
            return False
        
        # In a real implementation, this would restart the actual agent
        # For now, we just update the status
        self.agents[agent_name]["status"] = "restarting"
        
        # If it's a Strands agent, we could reinitialize it here
        if agent_name in self.agent_instances:
            # Reinitialize the agent instance
            try:
                # This would reinitialize the specific agent
                logger.info(f"Reinitializing Strands agent {agent_name}")
                # For now, just mark as active
                self.agents[agent_name]["status"] = "active"
            except Exception as e:
                logger.error(f"Failed to restart agent {agent_name}: {str(e)}")
                self.agents[agent_name]["status"] = "error"
                return False
        
        logger.info(f"Restarted agent {agent_name}")
        return True
    
    def get_agent_instance(self, agent_name: str) -> Optional[Agent]:
        """Get a Strands agent instance by name."""
        return self.agent_instances.get(agent_name)
    
    def register_agent_instance(self, agent_name: str, agent: Agent) -> None:
        """Register a Strands agent instance."""
        self.agent_instances[agent_name] = agent
        logger.info(f"Registered Strands agent instance: {agent_name}")
    
    def unregister_agent_instance(self, agent_name: str) -> None:
        """Unregister a Strands agent instance."""
        if agent_name in self.agent_instances:
            del self.agent_instances[agent_name]
            logger.info(f"Unregistered Strands agent instance: {agent_name}")
    
    async def get_agent_health(self, agent_name: str) -> Dict[str, Any]:
        """Get health status of a specific agent."""
        if agent_name not in self.agents:
            return {"status": "not_found", "error": "Agent not found"}
        
        agent_info = self.agents[agent_name]
        
        # Check if it's a Strands agent and has an instance
        if agent_info.get("agent_type") == "strands" and agent_name in self.agent_instances:
            try:
                # Test the agent with a simple query
                agent = self.agent_instances[agent_name]
                # This would test the agent's functionality
                return {
                    "status": "healthy",
                    "agent_type": "strands",
                    "capabilities": agent_info["capabilities"]
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "agent_type": "strands"
                }
        
        return {
            "status": agent_info["status"],
            "agent_type": agent_info.get("agent_type", "unknown"),
            "capabilities": agent_info["capabilities"]
        }
    
    async def get_memory_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get memory statistics for a specific agent."""
        if agent_name not in self.agents:
            return {"error": "Agent not found"}
        
        # For coordinator agent, get memory stats
        if agent_name == "coordinator" and agent_name in self.agent_instances:
            try:
                # Import here to avoid circular imports
                from app.agents.coordinator.coordinator_agent import CoordinatorAgent
                coordinator = self.agent_instances[agent_name]
                if hasattr(coordinator, 'get_memory_stats'):
                    return coordinator.get_memory_stats()
            except Exception as e:
                return {"error": f"Failed to get memory stats: {str(e)}"}
        
        return {"error": "Memory stats not available for this agent"}
    
    async def process_automation_request(
        self,
        message: str,
        session_id: str,
        language: Language,
        automation_context: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an automation request through the automation agent."""
        try:
            # Import here to avoid circular imports
            from app.agents.automation.automation_agent import AutomationAgent
            
            # Get or create automation agent instance
            if "automation" not in self.agent_instances:
                automation_agent = AutomationAgent()
                self.register_agent_instance("automation", automation_agent)
            
            automation_agent = self.agent_instances["automation"]
            
            # Process the automation request
            result = await automation_agent.process_automation_request(
                message=message,
                session_id=session_id,
                language=language,
                automation_context=automation_context,
                user_id=user_id
            )
            
            logger.info(f"Processed automation request for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing automation request: {str(e)}")
            raise e
    
    async def validate_automation_request(self, automation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an automation request before processing."""
        try:
            # Import here to avoid circular imports
            from app.agents.automation.automation_agent import AutomationAgent
            
            # Get or create automation agent instance
            if "automation" not in self.agent_instances:
                automation_agent = AutomationAgent()
                self.register_agent_instance("automation", automation_agent)
            
            automation_agent = self.agent_instances["automation"]
            
            # Validate the automation request
            validation_result = await automation_agent.validate_automation_request(automation_context)
            
            logger.info("Validated automation request")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating automation request: {str(e)}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }