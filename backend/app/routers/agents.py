"""Agent management endpoints."""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
import datetime
from app.models.responses import AgentStatusResponse
from app.services.agent_service import AgentService
from app.models.requests import Language

router = APIRouter()


@router.get("/agents", response_model=List[AgentStatusResponse])
async def list_agents(fastapi_request: Request):
    """List all available agents and their status."""
    try:
        # Get agent service from app state
        agent_service = getattr(fastapi_request.app.state, 'agent_service', None)
        if not agent_service:
            agent_service = AgentService()
        
        agents = await agent_service.list_all_agents()
        
        return agents
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing agents: {str(e)}"
        )


@router.get("/agents/{agent_name}", response_model=AgentStatusResponse)
async def get_agent_status(agent_name: str, fastapi_request: Request):
    """Get status of a specific agent."""
    try:
        # Get agent service from app state
        agent_service = getattr(fastapi_request.app.state, 'agent_service', None)
        if not agent_service:
            agent_service = AgentService()
        
        agent = await agent_service.get_agent_status(agent_name)
        
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found"
            )
        
        return agent
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting agent status: {str(e)}"
        )


@router.get("/agents/{agent_name}/health")
async def get_agent_health(agent_name: str):
    """Get detailed health status of a specific agent."""
    try:
        if agent_name == "coordinator":
            from app.agents.coordinator.monitoring import agent_monitor, circuit_breaker
            
            health_status = agent_monitor.get_health_status()
            circuit_status = circuit_breaker.get_status()
            
            return {
                "agent_name": agent_name,
                "health_status": health_status,
                "circuit_breaker": circuit_status,
                "is_healthy": agent_monitor.check_health(),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Health monitoring not available for agent '{agent_name}'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting agent health: {str(e)}"
        )


@router.get("/agents/{agent_name}/memory")
async def get_agent_memory_stats(agent_name: str, fastapi_request: Request):
    """Get memory statistics for a specific agent."""
    try:
        # Get agent service from app state
        agent_service = getattr(fastapi_request.app.state, 'agent_service', None)
        if not agent_service:
            agent_service = AgentService()
        
        stats = await agent_service.get_memory_stats(agent_name)
        
        if "error" in stats:
            raise HTTPException(
                status_code=404,
                detail=stats["error"]
            )
        
        return {
            "agent_name": agent_name,
            "memory_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting memory stats: {str(e)}"
        )


@router.post("/agents/{agent_name}/restart")
async def restart_agent(agent_name: str, fastapi_request: Request):
    """Restart a specific agent."""
    try:
        # Get agent service from app state
        agent_service = getattr(fastapi_request.app.state, 'agent_service', None)
        if not agent_service:
            agent_service = AgentService()
        
        result = await agent_service.restart_agent(agent_name)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found"
            )
        
        return {
            "message": f"Agent '{agent_name}' restarted successfully",
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error restarting agent: {str(e)}"
        )


@router.post("/agents/automation/process")
async def process_automation_request(
    fastapi_request: Request,
    automation_request: Dict[str, Any]
):
    """Process an automation request through the automation agent."""
    try:
        # Extract required fields
        message = automation_request.get("message", "")
        session_id = automation_request.get("session_id", "")
        language = automation_request.get("language", "english")
        automation_context = automation_request.get("automation_context", {})
        user_id = automation_request.get("user_id")
        
        if not message or not session_id:
            raise HTTPException(
                status_code=400,
                detail="Message and session_id are required"
            )
        
        # Convert language string to enum
        lang_enum = Language.ENGLISH if language.lower() == "english" else Language.BAHASA_MALAYSIA
        
        # Get agent service from app state
        agent_service = getattr(fastapi_request.app.state, 'agent_service', None)
        if not agent_service:
            agent_service = AgentService()
        
        # Process automation request
        result = await agent_service.process_automation_request(
            message=message,
            session_id=session_id,
            language=lang_enum,
            automation_context=automation_context,
            user_id=user_id
        )
        
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing automation request: {str(e)}"
        )


@router.post("/agents/automation/validate")
async def validate_automation_request(
    fastapi_request: Request,
    automation_context: Dict[str, Any]
):
    """Validate an automation request before processing."""
    try:
        # Get agent service from app state
        agent_service = getattr(fastapi_request.app.state, 'agent_service', None)
        if not agent_service:
            agent_service = AgentService()
        
        # Validate automation request
        validation_result = await agent_service.validate_automation_request(automation_context)
        
        return {
            "validation_result": validation_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating automation request: {str(e)}"
        )
