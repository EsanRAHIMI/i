"""
Auth service main application.
"""
import os
import time
import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import structlog

from .config import settings
from .database.base import engine
from .database.models import Base
from .middleware.auth import JWTAuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware

# Configure structured logging
if os.getenv("TESTING"):
    log_file = None
elif os.path.exists("/app") and os.access("/app", os.W_OK):
    log_file = "/app/logs/auth-service.log"
else:
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "auth-service.log")

# Import after log file is configured
from .core.logging_config import configure_logging, LoggingContext

configure_logging(
    log_level=settings.LOG_LEVEL,
    service_name="auth-service",
    version="1.0.0",
    enable_json=True,
    log_file=log_file,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 Starting Auth Service")
    logger.info("=" * 60)
    logger.info(f"📍 Service URL: http://0.0.0.0:8001")
    logger.info(f"📚 API Docs: http://0.0.0.0:8001/v1/docs")
    logger.info("=" * 60)
    
    logger.info("✅ Startup complete")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Auth Service")


# Create FastAPI application
app = FastAPI(
    title="I App Auth Service",
    description="Authentication microservice for I App",
    version="1.0.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
    lifespan=lifespan
)


# Rate limit middleware (apply before auth so even unauth endpoints are protected)
app.add_middleware(RateLimitMiddleware)

# Auth middleware
app.add_middleware(JWTAuthMiddleware)


class RequestLoggingMiddleware:
    """Middleware for request/response logging."""
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        start_time = time.time()
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        with LoggingContext(correlation_id=correlation_id, request_id=request_id):
            logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else None,
            )

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-correlation-id", correlation_id.encode("utf-8")))
                    headers.append((b"x-request-id", request_id.encode("utf-8")))
                    message["headers"] = headers
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
                duration = time.time() - start_time
                logger.info(
                    "Request completed",
                    method=request.method,
                    url=str(request.url),
                    duration_ms=round(duration * 1000, 2),
                )
            except Exception as exc:
                duration = time.time() - start_time
                logger.error(
                    "Request failed",
                    method=request.method,
                    url=str(request.url),
                    duration_ms=round(duration * 1000, 2),
                    error=str(exc),
                    error_type=type(exc).__name__,
                    exc_info=True,
                )
                response = JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal server error",
                        "correlation_id": correlation_id,
                        "request_id": request_id,
                        "timestamp": time.time()
                    },
                )
                await response(scope, receive, send_wrapper)


app.add_middleware(RequestLoggingMiddleware)

# CORS middleware (MUST BE LAST to be outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "auth-service",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "I App Auth Service",
        "version": "1.0.0",
        "docs": "/v1/docs"
    }


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    errors = []
    error_messages = []
    
    for error in exc.errors():
        loc = error.get("loc", [])
        field_parts = [str(loc_item) for loc_item in loc if loc_item != "body"]
        field = ".".join(field_parts) if field_parts else ".".join(str(loc_item) for loc_item in loc)
        message = error.get("msg", "Validation error")
        error_type = error.get("type", "")
        
        errors.append({
            "field": field,
            "message": message,
            "type": error_type
        })
        error_messages.append(message)
    
    combined_message = "؛ ".join(error_messages) if len(error_messages) > 1 else (error_messages[0] if error_messages else "Validation error")
    
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    
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
from .api.v1.auth import router as auth_router
app.include_router(auth_router, prefix="/v1/auth")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "auth_service.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_config=None
    )
