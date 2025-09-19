"""Response models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class ResponseStatus(str, Enum):
    """Response status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str = Field(..., description="AI response message")
    session_id: str = Field(..., description="Session ID")
    status: ResponseStatus = Field(..., description="Response status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    payment_links: Optional[List[str]] = Field(None, description="Payment links if applicable")
    screenshots: Optional[List[str]] = Field(None, description="Screenshot URLs if applicable")


class GovernmentServiceResponse(BaseModel):
    """Government service response model."""
    service_type: str = Field(..., description="Type of government service")
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Service-specific data")
    next_steps: Optional[List[str]] = Field(None, description="Next steps for user")
    payment_links: Optional[List[str]] = Field(None, description="Payment links if applicable")


class AgentStatusResponse(BaseModel):
    """Agent status response model."""
    agent_name: str = Field(..., description="Agent name")
    status: str = Field(..., description="Agent status")
    last_updated: str = Field(..., description="Last update timestamp")
    capabilities: List[str] = Field(..., description="Agent capabilities")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment")
    timestamp: str = Field(..., description="Response timestamp")
    services: Dict[str, str] = Field(..., description="Dependent services status")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: str = Field(..., description="Error timestamp")
