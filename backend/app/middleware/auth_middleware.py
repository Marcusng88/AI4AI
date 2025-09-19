"""Authentication middleware for FastAPI with AWS Cognito JWT validation."""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.cognito_service import cognito_service, CognitoUser
from app.core.logging import get_logger

logger = get_logger(__name__)

# Security scheme for FastAPI docs
security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle JWT authentication for protected routes."""

    def __init__(self, app):
        super().__init__(app)
        self.protected_paths = {
            "/api/v1/chat",
            "/api/v1/agents", 
            "/api/v1/websocket",
            "/ws"
        }
        self.excluded_paths = {
            "/api/v1/health",
            "/api/v1/auth",
            "/docs",
            "/redoc",
            "/openapi.json"
        }

    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware."""
        path = request.url.path
        
        # Skip authentication for excluded paths
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)
        
        # Check if path requires authentication
        if any(path.startswith(protected) for protected in self.protected_paths):
            try:
                # Extract and validate token
                token = self._extract_token(request)
                if token:
                    user_claims = cognito_service.verify_token(token)
                    # Add user info to request state
                    request.state.user_claims = user_claims
                    request.state.user_id = user_claims.get("sub")
                else:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required"}
                    )
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
            except Exception as e:
                logger.error(f"Authentication middleware error: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Authentication service error"}
                )
        
        return await call_next(request)

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None


# Dependency functions for FastAPI route protection
async def get_current_user_claims(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency to get current user claims from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_claims = cognito_service.verify_token(credentials.credentials)
        return user_claims
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(user_claims: Dict[str, Any] = Depends(get_current_user_claims)) -> CognitoUser:
    """FastAPI dependency to get current user information."""
    try:
        # Extract user info from token claims
        user = CognitoUser(
            user_id=user_claims["sub"],
            email=user_claims.get("email", ""),
            email_verified=user_claims.get("email_verified", False),
            name=user_claims.get("name"),
            given_name=user_claims.get("given_name"),
            family_name=user_claims.get("family_name"),
            phone_number=user_claims.get("phone_number"),
            phone_number_verified=user_claims.get("phone_number_verified", False)
        )
        return user
    except Exception as e:
        logger.error(f"Error creating user from claims: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user information in token"
        )


async def get_user_id(user_claims: Dict[str, Any] = Depends(get_current_user_claims)) -> str:
    """FastAPI dependency to get current user ID."""
    user_id = user_claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    return user_id


# Optional dependency that doesn't raise errors if no authentication
async def get_optional_user_claims(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to optionally get user claims without requiring authentication."""
    if not credentials:
        return None
    
    try:
        user_claims = cognito_service.verify_token(credentials.credentials)
        return user_claims
    except Exception as e:
        logger.warning(f"Optional authentication failed: {str(e)}")
        return None


async def get_optional_user_id(user_claims: Optional[Dict[str, Any]] = Depends(get_optional_user_claims)) -> Optional[str]:
    """FastAPI dependency to optionally get user ID without requiring authentication."""
    if not user_claims:
        return None
    return user_claims.get("sub")


# Request state helpers
def get_request_user_id(request: Request) -> Optional[str]:
    """Get user ID from request state (set by middleware)."""
    return getattr(request.state, "user_id", None)


def get_request_user_claims(request: Request) -> Optional[Dict[str, Any]]:
    """Get user claims from request state (set by middleware)."""
    return getattr(request.state, "user_claims", None)
