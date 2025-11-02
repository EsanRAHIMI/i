"""
Unit tests for authentication service.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import jwt

from app.services.auth import AuthService, auth_service
from app.schemas.auth import UserCreate, UserLogin
from app.database.models import User, UserSettings, AuditLog


class TestAuthService:
    """Test AuthService functionality."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        service = AuthService()
        password = "TestPassword123!"
        
        # Test hashing
        hashed = service.hash_password(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        
        # Test verification
        assert service.verify_password(password, hashed) is True
        assert service.verify_password("wrong_password", hashed) is False

    @patch('app.services.auth.settings')
    def test_create_access_token(self, mock_settings):
        """Test JWT access token creation."""
        # Mock settings
        mock_settings.JWT_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbw==
-----END RSA PRIVATE KEY-----"""
        mock_settings.JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbwIDAQAB
-----END PUBLIC KEY-----"""
        mock_settings.JWT_ALGORITHM = "RS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
        
        service = AuthService()
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = service.create_access_token(user_id, email)
        
        # Verify token structure
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
        
        # Decode and verify payload
        payload = jwt.decode(token, mock_settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    @patch('app.services.auth.settings')
    def test_create_refresh_token(self, mock_settings):
        """Test JWT refresh token creation."""
        # Mock settings with test keys
        mock_settings.JWT_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbw==
-----END RSA PRIVATE KEY-----"""
        mock_settings.JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbwIDAQAB
-----END PUBLIC KEY-----"""
        mock_settings.JWT_ALGORITHM = "RS256"
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
        
        service = AuthService()
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = service.create_refresh_token(user_id, email)
        
        # Verify token structure
        assert isinstance(token, str)
        
        # Decode and verify payload
        payload = jwt.decode(token, mock_settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "refresh"

    def test_get_user_by_email(self, db_session):
        """Test getting user by email."""
        service = AuthService()
        
        # Create test user
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            timezone="UTC"
        )
        db_session.add(user)
        db_session.commit()
        
        # Test finding existing user
        found_user = service.get_user_by_email(db_session, "test@example.com")
        assert found_user is not None
        assert found_user.email == "test@example.com"
        
        # Test non-existent user
        not_found = service.get_user_by_email(db_session, "nonexistent@example.com")
        assert not_found is None

    def test_create_user_success(self, db_session):
        """Test successful user creation."""
        service = AuthService()
        
        user_create = UserCreate(
            email="newuser@example.com",
            password="SecurePassword123!",
            timezone="America/New_York",
            language_preference="en-US"
        )
        
        created_user = service.create_user(db_session, user_create, "192.168.1.1")
        
        # Verify user creation
        assert created_user.id is not None
        assert created_user.email == "newuser@example.com"
        assert created_user.timezone == "America/New_York"
        assert created_user.language_preference == "en-US"
        assert hasattr(created_user, 'password_hash')
        assert created_user.password_hash != "SecurePassword123!"
        
        # Verify user settings were created
        db_session.refresh(created_user)
        assert created_user.settings is not None
        
        # Verify audit log was created
        audit_logs = db_session.query(AuditLog).filter_by(
            user_id=created_user.id,
            action="user_created"
        ).all()
        assert len(audit_logs) == 1

    def test_create_user_duplicate_email(self, db_session):
        """Test user creation with duplicate email."""
        service = AuthService()
        
        # Create first user
        user1 = User(
            email="duplicate@example.com",
            password_hash="hash1"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same email
        user_create = UserCreate(
            email="duplicate@example.com",
            password="Password123!"
        )
        
        with pytest.raises(ValueError, match="User with this email already exists"):
            service.create_user(db_session, user_create)

    def test_authenticate_user_success(self, db_session):
        """Test successful user authentication."""
        service = AuthService()
        
        # Create user with known password
        password = "TestPassword123!"
        hashed_password = service.hash_password(password)
        
        user = User(
            email="auth@example.com",
            password_hash=hashed_password
        )
        db_session.add(user)
        db_session.commit()
        
        # Test authentication
        authenticated_user = service.authenticate_user(
            db_session, "auth@example.com", password, "192.168.1.1"
        )
        
        assert authenticated_user is not None
        assert authenticated_user.email == "auth@example.com"
        
        # Verify audit log
        audit_logs = db_session.query(AuditLog).filter_by(
            user_id=user.id,
            action="login_success"
        ).all()
        assert len(audit_logs) == 1

    def test_authenticate_user_invalid_email(self, db_session):
        """Test authentication with invalid email."""
        service = AuthService()
        
        result = service.authenticate_user(
            db_session, "nonexistent@example.com", "password"
        )
        
        assert result is None

    def test_authenticate_user_invalid_password(self, db_session):
        """Test authentication with invalid password."""
        service = AuthService()
        
        # Create user
        user = User(
            email="test@example.com",
            password_hash=service.hash_password("correct_password")
        )
        db_session.add(user)
        db_session.commit()
        
        # Test with wrong password
        result = service.authenticate_user(
            db_session, "test@example.com", "wrong_password", "192.168.1.1"
        )
        
        assert result is None
        
        # Verify failed login audit log
        audit_logs = db_session.query(AuditLog).filter_by(
            user_id=user.id,
            action="login_failed"
        ).all()
        assert len(audit_logs) == 1

    def test_create_token_response(self, db_session):
        """Test token response creation."""
        service = AuthService()
        
        user = User(
            email="token@example.com",
            timezone="UTC",
            language_preference="en-US"
        )
        db_session.add(user)
        db_session.commit()
        
        with patch.object(service, 'create_access_token', return_value="access_token"):
            with patch.object(service, 'create_refresh_token', return_value="refresh_token"):
                token_response = service.create_token_response(user)
                
                assert token_response.access_token == "access_token"
                assert token_response.refresh_token == "refresh_token"
                assert token_response.token_type == "bearer"
                assert token_response.user.email == "token@example.com"
                assert token_response.user.id == str(user.id)

    @patch('app.services.auth.settings')
    def test_verify_token_valid(self, mock_settings):
        """Test token verification with valid token."""
        # Mock settings
        mock_settings.JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbwIDAQAB
-----END PUBLIC KEY-----"""
        mock_settings.JWT_ALGORITHM = "RS256"
        
        service = AuthService()
        
        # Create a valid token
        private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNjcIBFRQdaKtQWiOqI5u+4QK99AahqYKTNx9siIkLGAOkOdOwImamSjCb6VdEOyJSN/UpOSGxvr4aeZTwAoOqKKqmp6lvFZhtl1Hy7oGiQo+FelwtGWx1hAig6EAaOHNmrCQCa4RQUdpkrvNFWw5pDUKBqDqy6hdZBsV9FtUOIdVJ7PRcKhu8qhfHtVJMCThp/0E2hLoOuFBdX/iuinehd5RWXZF+s+XziHwaCEo9N/lshKNaFIx4XYpAoXqmjllVHvA8X7IpAOUbaIQn1jV+Ps6d0sQ4s2nmHhbw==
-----END RSA PRIVATE KEY-----"""
        
        payload = {
            "sub": "user123",
            "email": "test@example.com",
            "type": "access",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        token = jwt.encode(payload, private_key, algorithm="RS256")
        
        # Verify token
        decoded_payload = service.verify_token(token)
        
        assert decoded_payload is not None
        assert decoded_payload["sub"] == "user123"
        assert decoded_payload["email"] == "test@example.com"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        service = AuthService()
        
        # Test with invalid token
        result = service.verify_token("invalid.token.here")
        assert result is None
        
        # Test with None token
        result = service.verify_token(None)
        assert result is None