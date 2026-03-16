"""
Database base configuration for auth service.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

from ..config import settings
from .models import Base

# Create database engine
if os.getenv("TESTING"):
    # Use SQLite for testing
    engine = create_engine(
        "sqlite:///./test_auth.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Use PostgreSQL for production
    database_url = settings.get_database_url()
    engine = create_engine(database_url)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
