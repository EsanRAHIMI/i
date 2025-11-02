#!/usr/bin/env python3
"""
Simple test runner for backend tests.
"""
import os
import sys
import unittest
from unittest.mock import patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock environment variables for testing
test_env = {
    'DATABASE_URL': 'sqlite:///:memory:',
    'SECRET_KEY': 'test_secret_key_for_testing_only',
    'JWT_PRIVATE_KEY': '''-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjc
IBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/
UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrC
QCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0
E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHv
A8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbwIDAQABAoIBAQCBg7kCmtTmF5BqbzYr
7w8RxjokJDAXduNh3EWcS5WrBqwNcs6USGwXx2f1AMN/xhEiUBcm+a0XQOp5CPYF
-----END RSA PRIVATE KEY-----''',
    'JWT_PUBLIC_KEY': '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41
fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siI
kLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7o
GiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9Ft
UOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCE
o9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbwID
AQAB
-----END PUBLIC KEY-----''',
    'REDIS_URL': 'redis://localhost:6379/0',
    'CELERY_BROKER_URL': 'redis://localhost:6379/1',
    'CELERY_RESULT_BACKEND': 'redis://localhost:6379/2'
}

def run_basic_tests():
    """Run basic tests without external dependencies."""
    print("Running basic backend foundation tests...")
    
    with patch.dict(os.environ, test_env):
        try:
            # Test imports
            print("✓ Testing imports...")
            from app.config import settings
            from app.services.auth import AuthService
            from app.middleware.correlation import CorrelationIDMiddleware
            from app.middleware.security import SecurityHeadersMiddleware
            print("✓ All imports successful")
            
            # Test configuration
            print("✓ Testing configuration...")
            assert settings.SECRET_KEY == test_env['SECRET_KEY']
            assert settings.DATABASE_URL == test_env['DATABASE_URL']
            print("✓ Configuration loaded successfully")
            
            # Test auth service
            print("✓ Testing auth service...")
            auth_service = AuthService()
            
            # Test password hashing
            password = "TestPassword123!"
            hashed = auth_service.hash_password(password)
            assert auth_service.verify_password(password, hashed)
            assert not auth_service.verify_password("wrong_password", hashed)
            print("✓ Password hashing works correctly")
            
            # Test middleware instantiation
            print("✓ Testing middleware...")
            correlation_middleware = CorrelationIDMiddleware(None)
            security_middleware = SecurityHeadersMiddleware(None)
            print("✓ Middleware instantiation successful")
            
            print("\n🎉 All basic tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)