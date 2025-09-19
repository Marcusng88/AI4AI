"""Request models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class Language(str, Enum):
    """Supported languages."""
    BAHASA_MALAYSIA = "ms"
    ENGLISH = "en"


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    language: Language = Field(Language.BAHASA_MALAYSIA, description="Preferred language")
    user_id: Optional[str] = Field(None, description="User identifier")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context (IC, plate number, etc.)")


class GovernmentServiceRequest(BaseModel):
    """Government service request model."""
    service_type: str = Field(..., description="Type of government service")
    service_data: Dict[str, Any] = Field(default_factory=dict, description="Service-specific data")
    session_id: Optional[str] = Field(None, description="Session ID")
    language: Language = Field(Language.BAHASA_MALAYSIA, description="Preferred language")


class JPJRequest(BaseModel):
    """JPJ-specific request model."""
    ic_number: Optional[str] = Field(None, description="IC number")
    license_plate: Optional[str] = Field(None, description="License plate number")
    service_type: str = Field(..., description="JPJ service type (summons, license_renewal, etc.)")
    session_id: Optional[str] = Field(None, description="Session ID")


class LHDNRequest(BaseModel):
    """LHDN-specific request model."""
    ic_number: Optional[str] = Field(None, description="IC number")
    tax_year: Optional[int] = Field(None, description="Tax year")
    service_type: str = Field(..., description="LHDN service type (tax_filing, payment, etc.)")
    session_id: Optional[str] = Field(None, description="Session ID")


class AddMessageRequest(BaseModel):
    """Add message request model."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")