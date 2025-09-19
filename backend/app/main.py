"""Main FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import health, chat, agents, auth, websocket
from app.core.logging import setup_logging
from app.middleware.auth_middleware import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    setup_logging()
    
    # Initialize DynamoDB tables
    from app.services.dynamodb_service import dynamodb_service
    try:
        await dynamodb_service.create_tables_if_not_exist()
        print("✅ DynamoDB initialization completed successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize DynamoDB tables: {e}")
        print("   The server will continue without DynamoDB. Chat data will not persist.")
        print("   To fix: Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
    
    # Initialize services
    from app.services.agent_service import AgentService
    from app.agents.coordinator.coordinator_agent import coordinator_agent
    from app.agents.automation.automation_agent import automation_agent
    
    agent_service = AgentService()
    agent_service.register_agent_instance("coordinator", coordinator_agent)
    agent_service.register_agent_instance("automation", automation_agent)
    
    # Store in app state for access in routes
    app.state.agent_service = agent_service
    
    yield
    
    # Shutdown
    # Clean up browser sessions
    try:
        await automation_agent.close_browser()
    except Exception as e:
        print(f"Error closing browser session: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Enhanced Government Services API for Malaysian citizens",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Authentication middleware
app.add_middleware(AuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-frontend-domain.com", "https://d84l1y8p4kdic.cloudfront.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "Something went wrong"
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI-Enhanced Government Services API",
        "version": settings.app_version,
        "status": "active",
        "environment": settings.environment
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1
    )
