"""
Database base configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..config import get_settings

# Get database URL from settings
settings = get_settings()
DATABASE_URL = settings.get_database_url()

# Create SQLAlchemy engine with connection pooling and pre-ping
# pool_pre_ping ensures connections are verified before use (handles stale connections)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Maintain 5 connections in the pool
    max_overflow=10,  # Allow up to 10 additional connections
    pool_recycle=3600  # Recycle connections after 1 hour
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()