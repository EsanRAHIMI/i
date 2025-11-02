"""
Test configuration and fixtures.
"""
import pytest
import sys
import os
from unittest.mock import patch

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Mock the database configuration to avoid connection issues
with patch.dict(os.environ, {
    'DATABASE_URL': 'sqlite:///:memory:',
    'SECRET_KEY': 'test_secret_key',
    'JWT_PRIVATE_KEY': 'test_private_key',
    'JWT_PUBLIC_KEY': 'test_public_key',
    'ENCRYPTION_MASTER_KEY': 'test_encryption_master_key_12345'
}):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    # Import the actual Base and models
    from app.database.base import Base
    from app.database.models import *


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        timezone="UTC",
        language_preference="en-US"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_user_with_settings(db_session, sample_user):
    """Create a sample user with settings."""
    settings = UserSettings(
        user_id=sample_user.id,
        whatsapp_opt_in=True,
        voice_training_consent=True,
        calendar_sync_enabled=True,
        privacy_level="high",
        notification_preferences={"email": True, "sms": False}
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return sample_user