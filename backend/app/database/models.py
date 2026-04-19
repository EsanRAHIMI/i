"""
Modernized Database models for the core AI service. 
Optimized for scalability, search performance, and AI-driven insights.
"""
import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, TIMESTAMP, 
    ForeignKey, UniqueConstraint, DECIMAL, JSON, Enum, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base

class PriorityEnum(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class StatusEnum(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"

class TimestampMixin:
    """Timestamps mixin for consistency."""
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class User(Base, TimestampMixin):
    """
    Local User representation. 
    Synchronized with Auth Service via UUID.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)  # Matches ID from Auth Service
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Global AI preferences for this user
    ai_settings = Column(JSONB, default={
        "voice_enabled": True,
        "auto_task_creation": True,
        "privacy_level": "standard"
    })

    # Relationships
    calendars = relationship("Calendar", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    whatsapp_threads = relationship("WhatsAppThread", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

class Calendar(Base, TimestampMixin):
    """Integrated calendars (Google, Outlook, etc.)."""
    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider = Column(String(50), default="google", index=True)
    provider_calendar_id = Column(String(255), index=True)
    
    # Encrypted tokens and sync state
    access_token_enc = Column(Text)
    refresh_token_enc = Column(Text)
    sync_token = Column(String(255))
    last_sync_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="calendars")
    events = relationship("Event", back_populates="calendar", cascade="all, delete-orphan")

class Event(Base, TimestampMixin):
    """Calendar events with AI-enhanced context."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="CASCADE"), nullable=True, index=True)
    
    external_event_id = Column(String(255), index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    
    start_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    end_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    
    location = Column(Text)
    attendees = Column(JSONB, default=[])
    
    # AI Metadata (Summaries, suggested actions, etc.)
    ai_context = Column(JSONB, default={})
    is_ai_generated = Column(Boolean, default=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="events")
    calendar = relationship("Calendar", back_populates="events")

class Task(Base, TimestampMixin):
    """Smart tasks with priority and status management."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM, index=True)
    status = Column(Enum(StatusEnum), default=StatusEnum.PENDING, index=True)
    
    due_date = Column(TIMESTAMP(timezone=True), index=True)
    completed_at = Column(TIMESTAMP(timezone=True))
    
    tags = Column(JSONB, default=[])
    ai_suggestions = Column(JSONB, default={})
    
    # Relationships
    user = relationship("User", back_populates="tasks")

class WhatsAppThread(Base, TimestampMixin):
    """Conversations via WhatsApp."""
    __tablename__ = "whatsapp_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    
    status = Column(String(20), default="active", index=True)
    last_message_at = Column(TIMESTAMP(timezone=True), index=True)
    
    # Relationships
    user = relationship("User", back_populates="whatsapp_threads")
    messages = relationship("WhatsAppMessage", back_populates="thread", cascade="all, delete-orphan")

class WhatsAppMessage(Base):
    """Individual messages within a thread."""
    __tablename__ = "whatsapp_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    
    external_msg_id = Column(String(255), unique=True, index=True)
    direction = Column(String(10), nullable=False, index=True)  # 'inbound' or 'outbound'
    content = Column(Text, nullable=False)
    msg_type = Column(String(20), default="text") # text, image, audio, etc.
    
    status = Column(String(20), default="sent") # sent, delivered, read, failed
    sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    thread = relationship("WhatsAppThread", back_populates="messages")

class FederatedRound(Base, TimestampMixin):
    """Federated Learning rounds tracking."""
    __tablename__ = "federated_rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_number = Column(Integer, nullable=False, index=True)
    model_version = Column(String(50), nullable=False, index=True)
    
    status = Column(String(20), default="in_progress", index=True)
    metrics = Column(JSONB, default={})
    
    completed_at = Column(TIMESTAMP(timezone=True))

class ClientUpdate(Base):
    """Individual client updates for Federated Learning."""
    __tablename__ = "client_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    round_id = Column(UUID(as_uuid=True), ForeignKey("federated_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    
    delta_location = Column(Text, nullable=False) # Path to the encrypted delta file
    privacy_budget = Column(DECIMAL(10, 8))
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)

class AuditLog(Base):
    """Comprehensive audit logs for security and debugging."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(50), index=True)
    resource_id = Column(UUID(as_uuid=True))
    
    details = Column(JSONB, default={})
    ip_address = Column(INET)
    user_agent = Column(Text)
    correlation_id = Column(UUID(as_uuid=True), index=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")