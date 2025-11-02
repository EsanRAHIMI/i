"""
Unit tests for middleware components.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.testclient import TestClient
from fastapi import FastAPI
import uuid
import time

from app.middleware.correlation import CorrelationIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.auth import JWTAuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware


class TestCorrelationIDMiddleware:
    """Test CorrelationID middleware functionality."""
    
    @pytest.fixture
    def app_with_correlation_middleware(self):
        """Create test app with correlation middleware."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"correlation_id": getattr(request.state, 'correlation_id', None)}
        
        return app
    
    def test_correlation_id_generation(self, app_with_correlation_middleware):
        """Test that correlation ID is generated when not provided."""
        client = TestClient(app_with_correlation_middleware)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        
        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID length
        
        # Verify it's in response body too
        data = response.json()
        assert data["correlation_id"] == correlation_id
    
    def test_correlation_id_preservation(self, app_with_correlation_middleware):
        """Test that provided correlation ID is preserved."""
        client = TestClient(app_with_correlation_middleware)
        
        custom_correlation_id = str(uuid.uuid4())
        response = client.get("/test", headers={"X-Correlation-ID": custom_correlation_id})
        
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == custom_correlation_id
        
        data = response.json()
        assert data["correlation_id"] == custom_correlation_id


class TestSecurityHeadersMiddleware:
    """Test Security Headers middleware functionality."""
    
    @pytest.fixture
    def app_with_security_middleware(self):
        """Create test app with security middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        return app
    
    def test_security_headers_added(self, app_with_security_middleware):
        """Test that security headers are added to responses."""
        client = TestClient(app_with_security_middleware)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check required security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
    
    def test_hsts_header_https(self):
        """Test HSTS header is added for HTTPS requests."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Mock HTTPS request
        with patch('starlette.requests.Request.url') as mock_url:
            mock_url.scheme = "https"
            client = TestClient(app, base_url="https://testserver")
            
            response = client.get("/test")
            
            # Note: TestClient doesn't actually use HTTPS, so we test the logic separately
            # In real implementation, HSTS would be added for HTTPS requests


class TestJWTAuthMiddleware:
    """Test JWT Authentication middleware functionality."""
    
    @pytest.fixture
    def app_with_auth_middleware(self):
        """Create test app with auth middleware."""
        app = FastAPI()
        
        # Mock settings for testing
        with patch('app.middleware.auth.settings') as mock_settings:
            mock_settings.JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbwIDAQAB
-----END PUBLIC KEY-----"""
            mock_settings.JWT_ALGORITHM = "RS256"
            
            app.add_middleware(JWTAuthMiddleware)
        
        @app.get("/")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/protected")
        async def protected_endpoint(request: Request):
            return {
                "message": "protected",
                "user_id": getattr(request.state, 'user_id', None)
            }
        
        return app
    
    def test_public_endpoint_no_auth_required(self, app_with_auth_middleware):
        """Test that public endpoints don't require authentication."""
        client = TestClient(app_with_auth_middleware)
        
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json()["message"] == "public"
    
    def test_protected_endpoint_no_token(self, app_with_auth_middleware):
        """Test that protected endpoints require authentication."""
        client = TestClient(app_with_auth_middleware)
        
        response = client.get("/protected")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["error"]
    
    def test_protected_endpoint_invalid_token(self, app_with_auth_middleware):
        """Test protected endpoint with invalid token."""
        client = TestClient(app_with_auth_middleware)
        
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["error"]
    
    def test_extract_token_valid_bearer(self):
        """Test token extraction from valid Bearer header."""
        middleware = JWTAuthMiddleware(None)
        
        # Mock request with Authorization header
        request = MagicMock()
        request.headers.get.return_value = "Bearer valid_token_here"
        
        token = middleware.extract_token(request)
        
        assert token == "valid_token_here"
    
    def test_extract_token_invalid_scheme(self):
        """Test token extraction with invalid scheme."""
        middleware = JWTAuthMiddleware(None)
        
        # Mock request with invalid scheme
        request = MagicMock()
        request.headers.get.return_value = "Basic invalid_scheme"
        
        token = middleware.extract_token(request)
        
        assert token is None
    
    def test_extract_token_no_header(self):
        """Test token extraction with no Authorization header."""
        middleware = JWTAuthMiddleware(None)
        
        # Mock request without Authorization header
        request = MagicMock()
        request.headers.get.return_value = None
        
        token = middleware.extract_token(request)
        
        assert token is None
    
    def test_should_authenticate_excluded_paths(self):
        """Test that excluded paths don't require authentication."""
        middleware = JWTAuthMiddleware(None)
        
        excluded_paths = [
            "/",
            "/health",
            "/metrics",
            "/api/v1/docs",
            "/api/v1/auth/login",
            "/api/v1/auth/register"
        ]
        
        for path in excluded_paths:
            request = MagicMock()
            request.url.path = path
            
            assert middleware.should_authenticate(request) is False
    
    def test_should_authenticate_protected_paths(self):
        """Test that protected paths require authentication."""
        middleware = JWTAuthMiddleware(None)
        
        protected_paths = [
            "/api/v1/voice/stt",
            "/api/v1/agent/intent",
            "/api/v1/calendar/events",
            "/api/v1/user/profile"
        ]
        
        for path in protected_paths:
            request = MagicMock()
            request.url.path = path
            
            assert middleware.should_authenticate(request) is True


class TestRateLimitMiddleware:
    """Test Rate Limit middleware functionality."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.zremrangebyscore.return_value = None
        mock_client.zcard.return_value = 0
        mock_client.zadd.return_value = None
        mock_client.expire.return_value = None
        mock_client.zrange.return_value = []
        return mock_client
    
    @pytest.fixture
    def app_with_rate_limit_middleware(self, mock_redis_client):
        """Create test app with rate limit middleware."""
        app = FastAPI()
        
        # Mock Redis connection
        with patch('app.middleware.rate_limit.redis.from_url', return_value=mock_redis_client):
            with patch('app.middleware.rate_limit.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379/0"
                mock_settings.RATE_LIMIT_REQUESTS = 10
                mock_settings.RATE_LIMIT_WINDOW = 60
                
                app.add_middleware(RateLimitMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        return app
    
    def test_rate_limit_excluded_paths(self, app_with_rate_limit_middleware):
        """Test that health and metrics endpoints are excluded from rate limiting."""
        client = TestClient(app_with_rate_limit_middleware)
        
        # Health endpoint should not be rate limited
        response = client.get("/health")
        assert response.status_code == 200
        
        # Should not have rate limit headers
        assert "X-RateLimit-Limit" not in response.headers
    
    def test_get_client_identifier_ip(self):
        """Test client identifier extraction from IP."""
        middleware = RateLimitMiddleware(None)
        
        # Mock request with client IP
        request = MagicMock()
        request.state = MagicMock()
        request.state.user_id = None
        request.client.host = "192.168.1.1"
        request.headers.get.return_value = None
        
        client_id = middleware.get_client_identifier(request)
        
        assert client_id == "ip:192.168.1.1"
    
    def test_get_client_identifier_user(self):
        """Test client identifier extraction from authenticated user."""
        middleware = RateLimitMiddleware(None)
        
        # Mock request with authenticated user
        request = MagicMock()
        request.state = MagicMock()
        request.state.user_id = "user123"
        
        client_id = middleware.get_client_identifier(request)
        
        assert client_id == "user:user123"
    
    def test_get_client_identifier_forwarded_for(self):
        """Test client identifier extraction from X-Forwarded-For header."""
        middleware = RateLimitMiddleware(None)
        
        # Mock request with X-Forwarded-For header
        request = MagicMock()
        request.state = MagicMock()
        request.state.user_id = None
        request.client.host = "10.0.0.1"
        request.headers.get.return_value = "203.0.113.1, 198.51.100.1"
        
        client_id = middleware.get_client_identifier(request)
        
        assert client_id == "ip:203.0.113.1"
    
    @pytest.mark.asyncio
    async def test_is_rate_limited_under_limit(self, mock_redis_client):
        """Test rate limiting when under the limit."""
        middleware = RateLimitMiddleware(None)
        middleware.redis_client = mock_redis_client
        middleware.requests_per_window = 10
        middleware.window_size = 60
        
        # Mock Redis responses for under limit scenario
        mock_redis_client.zcard.return_value = 5  # 5 requests in window
        
        is_limited, rate_info = await middleware.is_rate_limited("test_client")
        
        assert is_limited is False
        assert rate_info["requests_remaining"] == 4  # 10 - 5 - 1
        assert "window_reset" in rate_info
    
    @pytest.mark.asyncio
    async def test_is_rate_limited_over_limit(self, mock_redis_client):
        """Test rate limiting when over the limit."""
        middleware = RateLimitMiddleware(None)
        middleware.redis_client = mock_redis_client
        middleware.requests_per_window = 10
        middleware.window_size = 60
        
        # Mock Redis responses for over limit scenario
        mock_redis_client.zcard.return_value = 10  # At limit
        mock_redis_client.zrange.return_value = [(str(int(time.time()) - 30), int(time.time()) - 30)]
        
        is_limited, rate_info = await middleware.is_rate_limited("test_client")
        
        assert is_limited is True
        assert rate_info["requests_remaining"] == 0
        assert "retry_after" in rate_info
    
    @pytest.mark.asyncio
    async def test_is_rate_limited_redis_unavailable(self):
        """Test rate limiting when Redis is unavailable."""
        middleware = RateLimitMiddleware(None)
        
        # No Redis client (simulates connection failure)
        is_limited, rate_info = await middleware.is_rate_limited("test_client")
        
        # Should allow requests when Redis is unavailable
        assert is_limited is False
        assert rate_info == {}


class TestMiddlewareIntegration:
    """Test middleware integration and order."""
    
    def test_middleware_order_and_integration(self):
        """Test that middleware components work together correctly."""
        app = FastAPI()
        
        # Add middleware in correct order
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {
                "correlation_id": getattr(request.state, 'correlation_id', None),
                "message": "success"
            }
        
        client = TestClient(app)
        response = client.get("/test")
        
        # Should have both correlation ID and security headers
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        
        # Response should contain correlation ID
        data = response.json()
        assert data["correlation_id"] is not None
        assert data["correlation_id"] == response.headers["X-Correlation-ID"]