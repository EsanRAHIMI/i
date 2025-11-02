"""
FastAPI main application with core middleware and configuration.
"""
import uuid
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .config import settings
from .middleware.auth import JWTAuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.correlation import CorrelationIDMiddleware
from .middleware.security import SecurityHeadersMiddleware
from .database.base import engine
from .database import models
from .core.metrics import metrics_collector
from .core.logging_config import configure_logging, LoggingContext, audit_logger
from .core.tracing import init_tracing, TracingConfig

# Configure structured logging and tracing
import os
# Use relative path for logs in local development, absolute path in Docker
if os.getenv("TESTING"):
    log_file = None
elif os.path.exists("/app") and os.access("/app", os.W_OK):
    # Running in Docker container
    log_file = "/app/logs/backend.log"
else:
    # Running locally - use relative path
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "backend.log")
configure_logging(
    log_level="INFO",
    service_name="ai-assistant-backend",
    version="1.0.0",
    enable_json=True,
    log_file=log_file
)

# Initialize distributed tracing
enable_tracing = not os.getenv("TESTING")
init_tracing(TracingConfig(
    service_name="ai-assistant-backend",
    service_version="1.0.0",
    jaeger_endpoint="http://jaeger:14268/api/traces",
    enable_tracing=enable_tracing
))

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up FastAPI application")
    
    # Create database tables
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")


# Create FastAPI application
app = FastAPI(
    title="Intelligent AI Assistant API",
    description="Next-generation Agentic AI Life Assistant API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Security middleware - must be added first
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Trusted host middleware
# Only enable in production mode (when DEBUG is False)
# In development, allow any host to facilitate local testing
is_local_dev = not os.getenv("DOCKER_ENV") and not os.path.exists("/app")
if settings.ALLOWED_HOSTS and not (settings.DEBUG or is_local_dev):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Custom middleware
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging and metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        request_id = str(uuid.uuid4())
        
        # Extract user information if available
        user_id = None
        if hasattr(request.state, 'user') and request.state.user:
            user_id = getattr(request.state.user, 'id', None)
        
        # Set up logging context
        with LoggingContext(
            correlation_id=correlation_id,
            user_id=user_id,
            request_id=request_id
        ):
            # Log request
            logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                user_agent=request.headers.get("user-agent"),
                client_ip=request.client.host if request.client else None,
                request_size=int(request.headers.get("content-length", 0))
            )
            
            try:
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                response_size = len(getattr(response, 'body', b''))
                
                # Update metrics
                metrics_collector.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration=duration,
                    request_size=int(request.headers.get("content-length", 0)),
                    response_size=response_size
                )
                
                # Log response
                logger.info(
                    "Request completed",
                    method=request.method,
                    url=str(request.url),
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                    response_size=response_size
                )
                
                # Log audit event for authenticated requests
                if user_id and request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                    audit_logger.log_user_action(
                        user_id=user_id,
                        action=f"{request.method} {request.url.path}",
                        resource_type="api_endpoint",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
                
                # Add correlation and request IDs to response headers
                response.headers["X-Correlation-ID"] = correlation_id
                response.headers["X-Request-ID"] = request_id
                
                return response
                
            except Exception as exc:
                duration = time.time() - start_time
                
                # Update error metrics
                metrics_collector.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=500,
                    duration=duration
                )
                
                # Log error
                logger.error(
                    "Request failed",
                    method=request.method,
                    url=str(request.url),
                    duration_ms=round(duration * 1000, 2),
                    error=str(exc),
                    error_type=type(exc).__name__,
                    exc_info=True
                )
                
                # Log security event for authentication/authorization errors
                if isinstance(exc, (HTTPException,)) and exc.status_code in [401, 403]:
                    audit_logger.log_security_event(
                        event_type="authentication_failure",
                        severity="warning",
                        user_id=user_id,
                        ip_address=request.client.host if request.client else None,
                        details={
                            "endpoint": request.url.path,
                            "method": request.method,
                            "status_code": exc.status_code
                        }
                    )
                
                # Return structured error response
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal server error",
                        "correlation_id": correlation_id,
                        "request_id": request_id,
                        "timestamp": time.time()
                    },
                    headers={
                        "X-Correlation-ID": correlation_id,
                        "X-Request-ID": request_id
                    }
                )


# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        metrics_collector.get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Intelligent AI Assistant API",
        "version": "1.0.0",
        "docs": "/api/v1/docs"
    }


# Favicon endpoint - return 204 No Content to avoid browser requests
@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint to prevent 404 errors."""
    return Response(status_code=204)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and return user-friendly messages."""
    errors = []
    error_messages = []
    
    for error in exc.errors():
        # Extract field path (skip 'body' prefix for cleaner messages)
        loc = error.get("loc", [])
        field_parts = [str(loc_item) for loc_item in loc if loc_item != "body"]
        field = ".".join(field_parts) if field_parts else ".".join(str(loc_item) for loc_item in loc)
        message = error.get("msg", "Validation error")
        error_type = error.get("type", "")
        
        # Translate common validation messages to user-friendly Persian
        user_message = message
        
        if "value_error" in error_type:
            if "Password must contain" in message or "password" in field.lower():
                user_message = "رمز عبور باید حداقل شامل یک حرف بزرگ، یک حرف کوچک، یک عدد و یک کاراکتر خاص باشد"
            elif "Password must be at least" in message:
                user_message = "رمز عبور باید حداقل ۸ کاراکتر باشد"
            elif "Password is too long" in message:
                user_message = "رمز عبور خیلی طولانی است (حداکثر ۱۲۸ بایت)"
        elif "string_too_short" in error_type:
            if "password" in field.lower():
                user_message = "رمز عبور باید حداقل ۸ کاراکتر باشد"
            else:
                user_message = f"{field}: حداقل طول رعایت نشده است"
        elif "missing" in error_type:
            user_message = f"فیلد '{field}' الزامی است"
        elif "value_error.missing" in error_type:
            user_message = f"فیلد '{field}' الزامی است"
        elif "type_error" in error_type:
            user_message = f"نوع داده برای '{field}' صحیح نیست"
        
        errors.append({
            "field": field,
            "message": user_message,
            "type": error_type
        })
        error_messages.append(user_message)
    
    # Combine all error messages into a single string for detail field
    combined_message = "؛ ".join(error_messages) if len(error_messages) > 1 else error_messages[0] if error_messages else "خطا در اعتبارسنجی داده‌ها"
    
    correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
    
    logger.warning(
        "Validation error",
        correlation_id=correlation_id,
        errors=errors,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": combined_message,
            "errors": errors
        },
        headers={
            "X-Correlation-ID": correlation_id,
            "Content-Type": "application/json"
        }
    )


# Include API routers
from .api.v1 import api_router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use structlog instead
    )