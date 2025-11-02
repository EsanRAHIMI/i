"""
SQLAlchemy ORM models for the intelligent AI assistant system.
"""
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, TIMESTAMP, 
    ForeignKey, UniqueConstraint, DECIMAL, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import os

from .base import Base

# Use appropriate types for SQLite (testing) vs PostgreSQL (production)
is_sqlite = os.getenv("DATABASE_URL", "").startswith("sqlite")
JSONType = JSON if is_sqlite else JSONB
UUIDType = String(36) if is_sqlite else UUID(as_uuid=True)
INETType = String(45) if is_sqlite else INET

# UUID default function that returns string for SQLite, UUID for PostgreSQL
def uuid_default():
    return str(uuid.uuid4()) if is_sqlite else uuid.uuid4()


class User(Base):
    """User model for storing user account information."""
    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC")
    language_preference = Column(String(10), default="en-US")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    calendars = relationship("Calendar", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    whatsapp_threads = relationship("WhatsAppThread", back_populates="user", cascade="all, delete-orphan")
    client_updates = relationship("ClientUpdate", back_populates="user", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class UserSettings(Base):
    """User settings and preferences."""
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


class Calendar(Base):
    """Calendar integration information."""
    __tablename__ = "calendars"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_calendar_id = Column(String(255))
    access_token_encrypted = Column(Text)
    refresh_token_encrypted = Column(Text)
    sync_token = Column(String(255))
    last_sync_at = Column(TIMESTAMP)
    webhook_id = Column(String(255))

    # Relationships
    user = relationship("User", back_populates="calendars")
    events = relationship("Event", back_populates="calendar")

    def __repr__(self):
        return f"<Calendar(id={self.id}, user_id={self.user_id}, google_calendar_id={self.google_calendar_id})>"


class Event(Base):
    """Calendar events."""
    __tablename__ = "events"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    calendar_id = Column(UUIDType, ForeignKey("calendars.id"), nullable=True)
    google_event_id = Column(String(255))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    location = Column(Text)
    attendees = Column(JSONType, default=[])
    ai_generated = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="events")
    calendar = relationship("Calendar", back_populates="events")

    def __repr__(self):
        return f"<Event(id={self.id}, title={self.title}, start_time={self.start_time})>"


class Task(Base):
    """AI-generated and user tasks."""
    __tablename__ = "tasks"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    priority = Column(Integer, default=3)
    status = Column(String(20), default="pending")
    due_date = Column(TIMESTAMP)
    context_data = Column(JSONType, default={})
    created_by_ai = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


class WhatsAppThread(Base):
    """WhatsApp conversation threads."""
    __tablename__ = "whatsapp_threads"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    phone_number = Column(String(20), nullable=False)
    thread_status = Column(String(20), default="active")
    last_message_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="whatsapp_threads")
    messages = relationship("WhatsAppMessage", back_populates="thread", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WhatsAppThread(id={self.id}, user_id={self.user_id}, phone_number={self.phone_number})>"


class WhatsAppMessage(Base):
    """Individual WhatsApp messages."""
    __tablename__ = "whatsapp_messages"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    thread_id = Column(UUIDType, ForeignKey("whatsapp_threads.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(String(255), unique=True)
    direction = Column(String(10), nullable=False)  # 'inbound' or 'outbound'
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")
    status = Column(String(20), default="sent")
    sent_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    thread = relationship("WhatsAppThread", back_populates="messages")

    def __repr__(self):
        return f"<WhatsAppMessage(id={self.id}, direction={self.direction}, status={self.status})>"


class FederatedRound(Base):
    """Federated learning training rounds."""
    __tablename__ = "federated_rounds"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    round_number = Column(Integer, nullable=False)
    model_version = Column(String(50), nullable=False)
    aggregation_status = Column(String(20), default="in_progress")
    participant_count = Column(Integer, default=0)
    started_at = Column(TIMESTAMP, server_default=func.now())
    completed_at = Column(TIMESTAMP)

    # Relationships
    client_updates = relationship("ClientUpdate", back_populates="round", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FederatedRound(id={self.id}, round_number={self.round_number}, status={self.aggregation_status})>"


class ClientUpdate(Base):
    """Client model updates for federated learning."""
    __tablename__ = "client_updates"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    round_id = Column(UUIDType, ForeignKey("federated_rounds.id", ondelete="CASCADE"), nullable=False)
    model_delta_encrypted = Column(Text, nullable=False)
    privacy_budget_used = Column(DECIMAL(precision=10, scale=8))
    uploaded_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="client_updates")
    round = relationship("FederatedRound", back_populates="client_updates")

    def __repr__(self):
        return f"<ClientUpdate(id={self.id}, user_id={self.user_id}, round_id={self.round_id})>"


class Consent(Base):
    """User consent records for privacy compliance."""
    __tablename__ = "consents"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type = Column(String(50), nullable=False)
    granted = Column(Boolean, nullable=False)
    consent_text = Column(Text, nullable=False)
    granted_at = Column(TIMESTAMP, server_default=func.now())
    revoked_at = Column(TIMESTAMP)

    # Relationships
    user = relationship("User", back_populates="consents")

    def __repr__(self):
        return f"<Consent(id={self.id}, user_id={self.user_id}, consent_type={self.consent_type}, granted={self.granted})>"


class AuditLog(Base):
    """Audit logs for security and compliance tracking."""
    __tablename__ = "audit_logs"

    id = Column(UUIDType, primary_key=True, default=uuid_default)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(UUIDType)
    details = Column(JSONType, default={})
    ip_address = Column(INETType)
    user_agent = Column(Text)
    correlation_id = Column(UUIDType)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"