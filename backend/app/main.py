"""Main FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import health, chat, auth, websocket, browser
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
    from app.agents.coordinator.coordinator_agent import coordinator_agent
    from app.agents.automation.automation_agent import automation_agent    
    
    print("🚀 Application startup completed")
    
    # Yield control to FastAPI - this is where the app runs
    yield
    
    # Shutdown
    print("🔄 Starting application shutdown...")
    
    # Clean up browser sessions
    try:
        await automation_agent.close_browser()
    except KeyboardInterrupt:
        print("Shutdown interrupted by user (KeyboardInterrupt)")
        # Still try to close browsers even if interrupted
        try:
            await automation_agent.close_browser()
        except Exception as cleanup_error:
            print(f"Error during cleanup after interrupt: {cleanup_error}")
    except Exception as e:
        print(f"Error closing browser session: {e}")
    
    print("✅ Application shutdown completed")


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
def get_cors_origins():
    """Get CORS origins from environment variable."""
    if settings.debug:
        return ["*"]
    
    # Parse CORS origins from environment variable
    origins = settings.cors_origins.split(",")
    # Strip whitespace and filter out empty strings
    origins = [origin.strip() for origin in origins if origin.strip()]
    
    # Add default CloudFront URL if not already present
    default_cloudfront = "https://d84l1y8p4kdic.cloudfront.net"
    if default_cloudfront not in origins:
        origins.append(default_cloudfront)
    
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(browser.router, prefix="/api/v1/browser", tags=["Browser"])
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
