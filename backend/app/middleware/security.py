"""
Security headers middleware.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        path = request.url.path
        is_docs_path = path.startswith("/api/v1/docs") or path.startswith("/api/v1/redoc") or path.startswith("/api/v1/openapi.json")
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Allow framing for documentation pages (Swagger UI needs it)
        response.headers["X-Frame-Options"] = "SAMEORIGIN" if is_docs_path else "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        # Allow CDN resources for Swagger UI documentation
        # Relax CSP for documentation endpoints to allow external resources
        if is_docs_path:
            # More permissive CSP for API documentation
            csp = (
                "default-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self' wss: ws:; "
                "frame-ancestors 'self';"
            )
        else:
            # Strict CSP for other endpoints
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: ws:; "
                "frame-ancestors 'none';"
            )
        response.headers["Content-Security-Policy"] = csp
        
        return response