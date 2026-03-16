"""
JWT Authentication middleware for auth service.
"""
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException
import structlog

from ..config import settings
from ..auth_utils import jwt_manager

logger = structlog.get_logger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""

    # Routes that don't require authentication
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/metrics",
        "/favicon.ico",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/docs",
        "/v1/redoc",
        "/v1/openapi.json",
        "/v1/auth/register",
        "/v1/auth/login",
        "/v1/auth/refresh",
        "/v1/auth/logout",
        "/v1/auth/forgot-password",
        "/v1/auth/reset-password",
    }

    # Path prefixes that don't require authentication
    EXCLUDED_PREFIXES = [
        "/static/",
        "/favicon"
    ]

    # Public GET paths (avatar images)
    PUBLIC_GET_PATHS = [
        "/v1/auth/avatar/"
    ]

    def __init__(self, app):
        super().__init__(app)
        self.public_key = jwt_manager.get_public_key()
        self.algorithm = settings.JWT_ALGORITHM

    def extract_token(self, request: Request) -> Optional[str]:
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

    def validate_token(self, token: str) -> Optional[dict]:
        """Validate JWT token."""
        try:
            payload = jwt_manager.verify_token(token)
            return payload
        except Exception as e:
            logger.warning("Token validation failed", error=str(e))
            return None

    def should_authenticate(self, request: Request) -> bool:
        """Check if request should be authenticated."""
        path = request.url.path
        
        # Check excluded paths
        if path in self.EXCLUDED_PATHS:
            return False
        
        # Check excluded prefixes
        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return False
        
        # Check public GET paths
        if request.method == "GET":
            # Avatar management endpoints must remain authenticated
            if path in {"/v1/auth/avatar/list", "/v1/auth/avatar/list/"}:
                return True

            # Only the actual avatar file endpoint should be public
            for public_path in self.PUBLIC_GET_PATHS:
                if path.startswith(public_path):
                    suffix = path[len(public_path):]
                    if suffix and "/" not in suffix:
                        return False

        return True

    async def dispatch(self, request: Request, call_next):
        """Process request through middleware."""
        if request.method == "OPTIONS":
            return await call_next(request)

        if not self.should_authenticate(request):
            return await call_next(request)
        
        # Extract and validate token
        token = self.extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
        
        payload = self.validate_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )
        
        # Add user info to request state
        request.state.user_id = payload.get("sub")
        request.state.user_email = payload.get("email")
        
        return await call_next(request)
