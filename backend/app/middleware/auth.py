"""
JWT Authentication middleware with RS256 token validation.
"""
import jwt
import os
import base64
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import structlog

from ..config import settings
from ..database.base import get_db
from ..database.models import User

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logger = structlog.get_logger(__name__)


def _normalize_pem_input(value: str) -> bytes:
    if not value:
        return b""
    
    # 1. Clean basic wrapping and literal escapes
    raw = value.strip()
    if (raw.startswith("\"") and raw.endswith("\"")) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1].strip()
    raw = raw.replace("\\n", "\n")
    
    # 2. Extract and rebuild PEM structure
    if "-----BEGIN" in raw and "-----END" in raw:
        import re
        header_match = re.search(r"-----BEGIN [^-]+-----", raw)
        footer_match = re.search(r"-----END [^-]+-----", raw)
        
        if header_match and footer_match:
            header = header_match.group(0)
            footer = footer_match.group(0)
            
            start_idx = raw.find(header) + len(header)
            end_idx = raw.find(footer)
            body = raw[start_idx:end_idx]
            
            # REMOVE ALL WHITESPACE from the base64 body
            clean_body = "".join(body.split())
            
            return f"{header}\n{clean_body}\n{footer}".encode("utf-8")
            
    return raw.encode("utf-8")


def _load_public_key() -> Optional[str]:
    """Load JWT public key from settings/env or files (compatible with auth-service)."""
    if settings.JWT_PUBLIC_KEY:
        try:
            serialization.load_pem_public_key(_normalize_pem_input(settings.JWT_PUBLIC_KEY), backend=default_backend())
            return settings.JWT_PUBLIC_KEY
        except Exception:
            if settings.JWT_KEYS_REQUIRED:
                raise

    if settings.JWT_PUBLIC_KEY_FILE and os.path.exists(settings.JWT_PUBLIC_KEY_FILE):
        try:
            key_text = open(settings.JWT_PUBLIC_KEY_FILE, "r", encoding="utf-8").read()
            serialization.load_pem_public_key(_normalize_pem_input(key_text), backend=default_backend())
            return key_text
        except Exception:
            if settings.JWT_KEYS_REQUIRED:
                raise

    keys_dir = settings.JWT_KEYS_DIR or "keys"
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    keys_dir_path = keys_dir if os.path.isabs(keys_dir) else os.path.join(project_root, keys_dir)
    for filename in ("jwt_public_key.pem", "public.pem"):
        candidate = os.path.join(keys_dir_path, filename)
        if os.path.exists(candidate):
            try:
                key_text = open(candidate, "r", encoding="utf-8").read()
                serialization.load_pem_public_key(_normalize_pem_input(key_text), backend=default_backend())
                return key_text
            except Exception:
                if settings.JWT_KEYS_REQUIRED:
                    raise

    return None


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware for protected routes."""
    
    # Routes that don't require authentication
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/metrics",
        "/favicon.ico",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/backend/docs",
        "/backend/redoc",
        "/backend/openapi.json",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
    }
    
    # Path prefixes that don't require authentication
    EXCLUDED_PREFIXES = [
        "/static/",
        "/favicon"
    ]
    
    # Paths that should be public (GET requests only, not POST/PUT/DELETE)
    PUBLIC_GET_PATHS = []
    
    # Auth endpoints are handled by the dedicated auth service, not the backend
    PUBLIC_AUTH_ENDPOINTS = []
    
    # OAuth callback doesn't require token (both GET and POST)
    OAUTH_CALLBACK_PATHS = [
        "/api/v1/calendar/oauth/callback"
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.public_key = _load_public_key()
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
        # Normalize path to avoid auth issues with trailing slashes added by proxies
        if path != "/":
            path = path.rstrip("/")
        
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
        
        # Validate token using configured public key
        public_key = _load_public_key()
        if not public_key:
            logger.error("JWT public key is not available")
            raise HTTPException(
                status_code=500,
                detail="Authentication service unavailable"
            )
        
        try:
            payload = jwt.decode(
                token,
                public_key,
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
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    return user