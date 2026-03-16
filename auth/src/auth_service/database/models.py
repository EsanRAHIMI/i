"""
Database models for auth service.
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, TIMESTAMP, 
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import os

try:
    from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB as PGJSONB
except Exception:  # pragma: no cover
    PGUUID = None
    PGJSONB = None

# Use appropriate types for SQLite (testing) vs PostgreSQL (production)
is_sqlite = os.getenv("DATABASE_URL", "").startswith("sqlite")
JSONType = JSON if is_sqlite or PGJSONB is None else PGJSONB
UUIDType = String(36) if is_sqlite or PGUUID is None else PGUUID(as_uuid=True)

# UUID default function
def uuid_default():
    if is_sqlite:
        return str(uuid.uuid4())
    return uuid.uuid4()


Base = declarative_base()


class TimestampMixin:
    """Timestamps mixin for all models."""
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class IdMixin:
    """UUID primary key mixin."""
    id = Column(UUIDType, primary_key=True, default=uuid_default)


class User(Base, IdMixin, TimestampMixin):
    """User model."""
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC")
    language_preference = Column(String(10), default="en-US")

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    avatars = relationship("UserAvatar", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class UserSettings(Base):
    """User settings."""
    __tablename__ = "user_settings"

    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    whatsapp_opt_in = Column(Boolean, default=False)
    voice_training_consent = Column(Boolean, default=False)
    calendar_sync_enabled = Column(Boolean, default=False)
    privacy_level = Column(String(20), default="standard")
    notification_preferences = Column(JSONType, default={})

    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, privacy_level={self.privacy_level})>"


class PasswordResetToken(Base):
    """Password reset tokens."""
    __tablename__ = "password_reset_tokens"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    used_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at}, used={self.used_at is not None})>"


class UserAvatar(Base, IdMixin, TimestampMixin):
    """User avatar metadata (S3 key, filename, etc.)."""

    __tablename__ = "user_avatars"

    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False, index=True)
    s3_key = Column(Text, nullable=True)
    public_url = Column(Text, nullable=True)
    content_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=True)

    user = relationship("User", back_populates="avatars")



