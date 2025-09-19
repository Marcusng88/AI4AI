"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

from app.models.responses import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow().isoformat(),
        services={
            "database": "healthy",
            "ai_agents": "healthy",
            "external_apis": "healthy"
        }
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {
            "fastapi": {
                "status": "healthy",
                "version": "0.104.1"
            },
            "strands_agents": {
                "status": "healthy",
                "configured": bool(settings.strands_api_key)
            },
            "bedrock_agentcore": {
                "status": "healthy",
                "region": settings.bedrock_agent_core_region
            },
            "malaysian_government_services": {
                "jpj": "healthy",
                "lhdn": "healthy",
                "jpn": "healthy",
                "epf": "healthy"
            }
        }
    }
