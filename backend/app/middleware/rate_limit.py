"""
Rate limiting middleware using Redis.
"""
import time
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import redis.asyncio as redis
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm."""
    
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self.requests_per_window = settings.RATE_LIMIT_REQUESTS
        self.window_size = settings.RATE_LIMIT_WINDOW
    
    async def get_redis_client(self):
        """Get Redis client with connection pooling."""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=10
                )
                # Test connection
                await self.redis_client.ping()
            except Exception as e:
                logger.warning("Redis connection failed, rate limiting disabled", error=str(e))
                return None
        return self.redis_client
    
    async def is_rate_limited(self, client_id: str) -> tuple[bool, dict]:
        """Check if client is rate limited using sliding window."""
        redis_client = await self.get_redis_client()
        if not redis_client:
            # If Redis is unavailable, allow requests
            return False, {}
        
        try:
            current_time = int(time.time())
            window_start = current_time - self.window_size
            
            # Use Redis sorted set for sliding window
            key = f"rate_limit:{client_id}"
            
            # Remove old entries
            await redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_requests = await redis_client.zcard(key)
            
            if current_requests >= self.requests_per_window:
                # Get oldest request time for retry-after calculation
                oldest_request = await redis_client.zrange(key, 0, 0, withscores=True)
                retry_after = int(oldest_request[0][1]) + self.window_size - current_time if oldest_request else self.window_size
                
                return True, {
                    "retry_after": max(retry_after, 1),
                    "requests_remaining": 0,
                    "window_reset": current_time + retry_after
                }
            
            # Add current request
            await redis_client.zadd(key, {str(current_time): current_time})
            await redis_client.expire(key, self.window_size)
            
            return False, {
                "requests_remaining": self.requests_per_window - current_requests - 1,
                "window_reset": current_time + self.window_size
            }
            
        except Exception as e:
            logger.error("Rate limiting check failed", error=str(e))
            # On error, allow request
            return False, {}
    
    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, 'user_id') and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        client_id = self.get_client_identifier(request)
        is_limited, rate_info = await self.is_rate_limited(client_id)
        
        if is_limited:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=request.url.path,
                correlation_id=getattr(request.state, 'correlation_id', None)
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {rate_info.get('retry_after', 60)} seconds.",
                    "retry_after": rate_info.get('retry_after', 60)
                },
                headers={
                    "Retry-After": str(rate_info.get('retry_after', 60)),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": str(rate_info.get('requests_remaining', 0)),
                    "X-RateLimit-Reset": str(rate_info.get('window_reset', int(time.time()) + 60))
                }
            )
        
        # Add rate limit headers to successful responses
        response = await call_next(request)
        
        if rate_info:
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
            response.headers["X-RateLimit-Remaining"] = str(rate_info.get('requests_remaining', 0))
            response.headers["X-RateLimit-Reset"] = str(rate_info.get('window_reset', int(time.time()) + 60))
        
        return response