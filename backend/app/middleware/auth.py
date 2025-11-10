"""
JWT Authentication middleware with RS256 token validation.
"""
import jwt
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import structlog

from ..config import settings
from ..services.auth import auth_service
from ..database.base import get_db
from ..database.models import User

logger = structlog.get_logger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware for protected routes."""
    
    # Routes that don't require authentication
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/metrics",
        "/favicon.ico",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh"
    }
    
    # Path prefixes that don't require authentication
    EXCLUDED_PREFIXES = [
        "/static/",
        "/favicon"
    ]
    
    # Paths that should be public (GET requests only, not POST/PUT/DELETE)
    PUBLIC_GET_PATHS = [
        "/api/v1/auth/avatar/"  # Avatar images should be publicly accessible (GET only)
    ]
    
    # Auth endpoints that don't require authentication (public endpoints)
    PUBLIC_AUTH_ENDPOINTS = [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh"
    ]
    
    # OAuth callback doesn't require token (both GET and POST)
    OAUTH_CALLBACK_PATHS = [
        "/api/v1/calendar/oauth/callback"
    ]
    
    def __init__(self, app):
        super().__init__(app)
        # Use public key from auth_service which loads keys from files if needed
        self.public_key = auth_service.public_key
        self.algorithm = settings.JWT_ALGORITHM
        
        if not self.public_key:
            logger.error("JWT public key is not available! Authentication will fail.")
    
    def extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        authorization = request.headers.get("Authorization")
        logger.debug(
            "🔑 Extracting token",
            has_authorization=bool(authorization),
            authorization_preview=authorization[:50] + "..." if authorization else None,
            authorization_type=type(authorization).__name__ if authorization else None
        )
        if not authorization:
            logger.debug("❌ No Authorization header found")
            return None
        
        try:
            scheme, token = authorization.split(" ", 1)
            logger.debug(
                "✅ Token extracted",
                scheme=scheme,
                token_preview=token[:30] + "..." if token else None,
                token_length=len(token) if token else 0
            )
            if scheme.lower() != "bearer":
                logger.warning(f"⚠️ Invalid scheme: {scheme}")
                return None
            return token
        except ValueError as e:
            logger.warning(f"⚠️ Error splitting Authorization header: {e}")
            return None
    
    def validate_token(self, token: str) -> Optional[dict]:
        """Validate JWT token and return payload."""
        if not self.public_key:
            logger.error("JWT public key is not available for token validation")
            return None
        
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token", error=str(e))
            return None
        except Exception as e:
            logger.error("JWT validation error", error=str(e), exc_info=True)
            return None
    
    def should_authenticate(self, request: Request) -> bool:
        """Check if request path requires authentication."""
        path = request.url.path
        
        # Skip authentication for excluded paths
        if path in self.EXCLUDED_PATHS:
            return False
        
        # Skip authentication for excluded prefixes
        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return False
        
        # Skip authentication for public GET requests (e.g., avatar images)
        # But require authentication for POST/PUT/DELETE requests
        if request.method == "GET":
            for public_path in self.PUBLIC_GET_PATHS:
                if path.startswith(public_path):
                    return False
        
        # Skip authentication for public auth endpoints (login, register, refresh)
        if path in self.PUBLIC_AUTH_ENDPOINTS:
            return False
        
        # Skip authentication for OAuth callback (both GET and POST)
        if path in self.OAUTH_CALLBACK_PATHS:
            return False
        
        # All other paths require authentication
        return True
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip authentication for certain paths
        if not self.should_authenticate(request):
            return await call_next(request)
        
        # Log request details for debugging
        auth_header = request.headers.get("Authorization")
        all_headers = dict(request.headers)
        logger.info(
            "🔍 Auth middleware processing request",
            path=request.url.path,
            method=request.method,
            has_auth_header=bool(auth_header),
            auth_header_preview=auth_header[:50] + "..." if auth_header else None,
            content_type=request.headers.get("Content-Type"),
            all_header_keys=list(all_headers.keys()),
            authorization_header_full=auth_header if auth_header else "NOT FOUND"
        )
        
        # Extract and validate token
        token = self.extract_token(request)
        if not token:
            logger.warning(
                "❌ No token found in request after extraction",
                path=request.url.path,
                authorization_header=auth_header,
                authorization_header_type=type(auth_header).__name__ if auth_header else None,
                all_headers=list(all_headers.keys())
            )
            response = JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "message": "Missing or invalid authorization header"
                }
            )
            # Add CORS headers for 401 responses
            origin = request.headers.get("origin")
            if origin and origin in settings.ALLOWED_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        payload = self.validate_token(token)
        if not payload:
            response = JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid token",
                    "message": "Token is expired or invalid"
                }
            )
            # Add CORS headers for 401 responses
            origin = request.headers.get("origin")
            if origin and origin in settings.ALLOWED_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        # Add user information to request state
        request.state.user_id = payload.get("sub")
        request.state.user_email = payload.get("email")
        request.state.token_payload = payload
        
        # Log authenticated request
        logger.info(
            "Authenticated request",
            user_id=request.state.user_id,
            path=request.url.path,
            correlation_id=getattr(request.state, 'correlation_id', None)
        )
        
        return await call_next(request)


# FastAPI dependency for getting current user
security = HTTPBearer()


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency to get current authenticated user from database.
    
    Returns:
        User model object from database
    """
    
    # Check if user information is available in request state (set by middleware)
    user_id = None
    if hasattr(request.state, 'user_id') and request.state.user_id:
        user_id = request.state.user_id
    else:
        # If middleware didn't set user info, try to extract from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme"
                )
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )
        
        # Validate token using auth_service public key
        if not auth_service.public_key:
            logger.error("JWT public key is not available")
            raise HTTPException(
                status_code=500,
                detail="Authentication service unavailable"
            )
        
        try:
            payload = jwt.decode(
                token,
                auth_service.public_key,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            
            user_id = payload.get("sub")
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error("JWT validation error", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )
    
    # Get user from database
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    return user