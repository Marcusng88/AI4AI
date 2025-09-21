"""AWS Cognito authentication service for AI4AI backend."""

import os
import json
import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

import requests
import jwt
from jose import jwk, jwt as jose_jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class CognitoTokens(BaseModel):
    """Cognito token response model."""
    access_token: str
    id_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class CognitoUser(BaseModel):
    """Cognito user information model."""
    user_id: str
    email: str
    email_verified: bool
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    phone_number: Optional[str] = None
    phone_number_verified: bool = False


class CognitoService:
    """AWS Cognito authentication service."""
    
    def __init__(self):
        """Initialize Cognito service with configuration from environment."""
        # Cognito configuration for ap-southeast-5
        self.region = "ap-southeast-5"
        self.user_pool_id = "ap-southeast-5_nuC0or8vA"
        self.client_id = "1djcgis021homk7vjhaoamfuek"
        self.client_secret = None  # SPA client doesn't have a secret
        
        # OAuth URLs
        self.authority = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        # OAuth URLs
        self.oauth_base_url = f"https://ap-southeast-5nuc0or8va.auth.{self.region}.amazoncognito.com"
        
        # JWT verification
        self.jwks_url = f"{self.authority}/.well-known/jwks.json"
        self.jwks_client = None
        self._jwks_cache = None
        self._jwks_cache_time = None
        
        logger.info(f"Initialized Cognito service for region {self.region}")

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate authorization URL for OAuth flow."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile"
        }
        
        if state:
            params["state"] = state
            
        query_string = "&".join([f"{k}={quote_plus(v)}" for k, v in params.items()])
        auth_url = f"{self.oauth_base_url}/oauth2/authorize?{query_string}"
        
        logger.info(f"Generated authorization URL for redirect_uri: {redirect_uri}")
        return auth_url

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> CognitoTokens:
        """Exchange authorization code for tokens."""
        try:
            # Prepare token request
            token_url = f"{self.oauth_base_url}/oauth2/token"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # For SPA clients, include client_id in the body, not in Authorization header
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": code,
                "redirect_uri": redirect_uri
            }
            
            logger.info(f"Exchanging code for tokens with redirect_uri: {redirect_uri}")
            
            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {response.text}"
                )
            
            token_data = response.json()
            
            return CognitoTokens(
                access_token=token_data["access_token"],
                id_token=token_data["id_token"],
                refresh_token=token_data["refresh_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600)
            )
            
        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims."""
        try:
            # Get JWT header to find key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing key ID"
                )
            
            # Get JWKS and find matching key
            jwks = self._get_jwks()
            key = None
            
            for jwk_key in jwks["keys"]:
                if jwk_key["kid"] == kid:
                    key = jwk_key
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: key not found"
                )
            
            # Use jose library for better JWKS handling
            try:
                logger.info(f"Verifying token with key ID: {kid}")
                logger.info(f"Token audience: {self.client_id}, issuer: {self.authority}")
                
                # jose handles JWKS conversion automatically
                payload = jose_jwt.decode(
                    token,
                    key,
                    algorithms=["RS256"],
                    audience=self.client_id,
                    issuer=self.authority
                )
                logger.info(f"Token verification successful for user: {payload.get('sub', 'unknown')}")
            except Exception as e:
                logger.error(f"JWT verification error: {str(e)}")
                logger.error(f"Key details: {key}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token verification failed"
                )
            
            # Verify token expiration
            if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )
            
            logger.info(f"Successfully verified token for user: {payload.get('sub', 'unknown')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )

    def get_user_info(self, access_token: str) -> CognitoUser:
        """Get user information using access token."""
        try:
            userinfo_url = f"{self.oauth_base_url}/oauth2/userInfo"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(userinfo_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"UserInfo request failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user information"
                )
            
            user_data = response.json()
            
            return CognitoUser(
                user_id=user_data["sub"],
                email=user_data.get("email", ""),
                email_verified=user_data.get("email_verified", False),
                name=user_data.get("name"),
                given_name=user_data.get("given_name"),
                family_name=user_data.get("family_name"),
                picture=user_data.get("picture"),
                phone_number=user_data.get("phone_number"),
                phone_number_verified=user_data.get("phone_number_verified", False)
            )
            
        except requests.RequestException as e:
            logger.error(f"Network error getting user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User information service unavailable"
            )
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user information"
            )

    def refresh_tokens(self, refresh_token: str) -> CognitoTokens:
        """Refresh access and ID tokens using refresh token."""
        try:
            token_url = f"{self.oauth_base_url}/oauth2/token"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # For SPA clients, include client_id in the body, not in Authorization header
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": refresh_token
            }
            
            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token refresh failed"
                )
            
            token_data = response.json()
            
            return CognitoTokens(
                access_token=token_data["access_token"],
                id_token=token_data["id_token"],
                refresh_token=refresh_token,  # Refresh token doesn't change
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600)
            )
            
        except requests.RequestException as e:
            logger.error(f"Network error during token refresh: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
        except Exception as e:
            logger.error(f"Error refreshing tokens: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )

    def _create_basic_auth_header(self) -> str:
        """Create Basic auth header for client authentication."""
        if self.client_secret:
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            return f"Basic {encoded_credentials}"
        else:
            # For SPA clients without client secret, use client_id only
            encoded_client_id = base64.b64encode(self.client_id.encode()).decode()
            return f"Basic {encoded_client_id}"

    def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS (JSON Web Key Set) with caching."""
        current_time = datetime.now(timezone.utc).timestamp()
        
        # Cache JWKS for 5 minutes
        if (self._jwks_cache is None or 
            self._jwks_cache_time is None or 
            current_time - self._jwks_cache_time > 300):
            
            try:
                logger.info(f"Fetching JWKS from: {self.jwks_url}")
                response = requests.get(self.jwks_url, timeout=10)
                response.raise_for_status()
                
                self._jwks_cache = response.json()
                self._jwks_cache_time = current_time
                
                logger.info(f"Updated JWKS cache with {len(self._jwks_cache.get('keys', []))} keys")
                
            except requests.RequestException as e:
                logger.error(f"Failed to fetch JWKS: {str(e)}")
                if self._jwks_cache is None:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Authentication service unavailable"
                    )
        
        return self._jwks_cache

    def get_logout_url(self, redirect_uri: str) -> str:
        """Generate logout URL."""
        params = {
            "client_id": self.client_id,
            "logout_uri": redirect_uri
        }
        
        query_string = "&".join([f"{k}={quote_plus(v)}" for k, v in params.items()])
        logout_url = f"{self.oauth_base_url}/logout?{query_string}"
        
        logger.info(f"Generated logout URL for redirect_uri: {redirect_uri}")
        return logout_url


# Global service instance
cognito_service = CognitoService()
