"""Authentication routes for AWS Cognito OAuth flow."""

import secrets
from typing import Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

from app.services.cognito_service import cognito_service, CognitoTokens, CognitoUser
from app.middleware.auth_middleware import get_current_user, get_user_id
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AuthUrlResponse(BaseModel):
    """Response model for authorization URL."""
    auth_url: str
    state: str


class TokenResponse(BaseModel):
    """Response model for token exchange."""
    access_token: str
    id_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: CognitoUser


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    user_id: str
    email: str
    email_verified: bool
    name: str = None
    given_name: str = None
    family_name: str = None
    picture: str = None
    phone_number: str = None
    phone_number_verified: bool = False


@router.get("/login", response_model=AuthUrlResponse)
async def get_login_url(
    redirect_uri: str = Query(..., description="Frontend callback URL"),
    request: Request = None
):
    """Generate Cognito authorization URL for login."""
    try:
        # Generate secure random state
        state = secrets.token_urlsafe(32)
        
        # Generate authorization URL
        auth_url = cognito_service.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )
        
        logger.info(f"Generated login URL for redirect_uri: {redirect_uri}")
        
        return AuthUrlResponse(
            auth_url=auth_url,
            state=state
        )
        
    except Exception as e:
        logger.error(f"Error generating login URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate login URL"
        )


@router.post("/callback", response_model=TokenResponse)
async def handle_callback(
    code: str = Query(..., description="Authorization code from Cognito"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    redirect_uri: str = Query(..., description="Original redirect URI")
):
    """Handle OAuth callback and exchange code for tokens."""
    try:
        # Exchange authorization code for tokens
        tokens = cognito_service.exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri
        )
        
        # Get user information using access token
        user_info = cognito_service.get_user_info(tokens.access_token)
        
        logger.info(f"Successfully authenticated user: {user_info.user_id}")
        
        return TokenResponse(
            access_token=tokens.access_token,
            id_token=tokens.id_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=CognitoTokens)
async def refresh_access_token(request: RefreshTokenRequest):
    """Refresh access and ID tokens using refresh token."""
    try:
        tokens = cognito_service.refresh_tokens(request.refresh_token)
        
        logger.info("Successfully refreshed tokens")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing tokens: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: CognitoUser = Depends(get_current_user)):
    """Get current user profile information."""
    try:
        return UserProfileResponse(
            user_id=current_user.user_id,
            email=current_user.email,
            email_verified=current_user.email_verified,
            name=current_user.name,
            given_name=current_user.given_name,
            family_name=current_user.family_name,
            picture=current_user.picture,
            phone_number=current_user.phone_number,
            phone_number_verified=current_user.phone_number_verified
        )
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.post("/logout")
async def logout(
    redirect_uri: str = Query(..., description="Post-logout redirect URI"),
    current_user_id: str = Depends(get_user_id)
):
    """Generate logout URL and invalidate session."""
    try:
        # Generate Cognito logout URL
        logout_url = cognito_service.get_logout_url(redirect_uri)
        
        logger.info(f"User {current_user_id} initiated logout")
        
        return {
            "logout_url": logout_url,
            "message": "Logout initiated"
        }
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/status")
async def get_auth_status(current_user: CognitoUser = Depends(get_current_user)):
    """Check authentication status."""
    return {
        "authenticated": True,
        "user_id": current_user.user_id,
        "email": current_user.email
    }


@router.get("/health")
async def auth_health_check():
    """Health check for authentication service."""
    try:
        # Test Cognito service connectivity
        # This could include checking JWKS endpoint availability
        jwks_url = cognito_service.jwks_url
        
        return {
            "status": "healthy",
            "service": "cognito-auth",
            "region": cognito_service.region,
            "user_pool_id": cognito_service.user_pool_id,
            "jwks_url": jwks_url
        }
        
    except Exception as e:
        logger.error(f"Auth health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unhealthy"
        )


# Legacy compatibility endpoints (for gradual migration)
@router.post("/signin", deprecated=True)
async def legacy_signin():
    """Legacy signin endpoint - redirects to new OAuth flow."""
    raise HTTPException(
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
        detail="Please use /auth/login endpoint for OAuth flow"
    )


@router.post("/signup", deprecated=True)
async def legacy_signup():
    """Legacy signup endpoint - redirects to Cognito hosted UI."""
    raise HTTPException(
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
        detail="Please use Cognito hosted UI for user registration"
    )
