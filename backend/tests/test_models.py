"""
Unit tests for database models.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.database.models import (
    User, UserSettings, Calendar, Event, Task, 
    WhatsAppThread, WhatsAppMessage, FederatedRound, 
    ClientUpdate, Consent, AuditLog
)


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self, db_session):
        """Test basic user creation."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            timezone="America/New_York",
            language_preference="en-US"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.timezone == "America/New_York"
        assert user.language_preference == "en-US"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_email_uniqueness(self, db_session):
        """Test that user emails must be unique."""
        user1 = User(email="test@example.com", password_hash="hash1")
        user2 = User(email="test@example.com", password_hash="hash2")
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            db_session.commit()

    def test_user_relationships(self, db_session, sample_user):
        """Test user model relationships."""
        # Test settings relationship
        settings = UserSettings(user_id=sample_user.id, privacy_level="high")
        db_session.add(settings)
        db_session.commit()
        
        db_session.refresh(sample_user)
        assert sample_user.settings is not None
        assert sample_user.settings.privacy_level == "high"

    def test_user_cascade_deletion(self, db_session, sample_user):
        """Test that deleting a user cascades to related records."""
        # Create related records
        settings = UserSettings(user_id=sample_user.id)
        task = Task(user_id=sample_user.id, title="Test Task")
        
        db_session.add_all([settings, task])
        db_session.commit()
        
        # Delete user
        db_session.delete(sample_user)
        db_session.commit()
        
        # Verify related records are deleted
        assert db_session.query(UserSettings).filter_by(user_id=sample_user.id).first() is None
        assert db_session.query(Task).filter_by(user_id=sample_user.id).first() is None


class TestUserSettingsModel:
    """Test UserSettings model functionality."""
    
    def test_user_settings_creation(self, db_session, sample_user):
        """Test user settings creation with defaults."""
        settings = UserSettings(user_id=sample_user.id)
        db_session.add(settings)
        db_session.commit()
        
        assert settings.user_id == sample_user.id
        assert settings.whatsapp_opt_in is False
        assert settings.voice_training_consent is False
        assert settings.calendar_sync_enabled is False
        assert settings.privacy_level == "standard"
        assert settings.notification_preferences == {}

    def test_user_settings_jsonb_field(self, db_session, sample_user):
        """Test JSONB notification preferences field."""
        preferences = {
            "email": True,
            "sms": False,
            "push": True,
            "frequency": "daily"
        }
        
        settings = UserSettings(
            user_id=sample_user.id,
            notification_preferences=preferences
        )
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.notification_preferences == preferences
        assert settings.notification_preferences["email"] is True
        assert settings.notification_preferences["frequency"] == "daily"


class TestCalendarModel:
    """Test Calendar model functionality."""
    
    def test_calendar_creation(self, db_session, sample_user):
        """Test calendar creation."""
        calendar = Calendar(
            user_id=sample_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token",
            sync_token="sync123"
        )
        db_session.add(calendar)
        db_session.commit()
        
        assert calendar.id is not None
        assert calendar.user_id == sample_user.id
        assert calendar.google_calendar_id == "primary"
        assert calendar.access_token_encrypted == "encrypted_token"

    def test_calendar_user_relationship(self, db_session, sample_user):
        """Test calendar-user relationship."""
        calendar = Calendar(user_id=sample_user.id, google_calendar_id="primary")
        db_session.add(calendar)
        db_session.commit()
        
        db_session.refresh(sample_user)
        assert len(sample_user.calendars) == 1
        assert sample_user.calendars[0].google_calendar_id == "primary"


class TestEventModel:
    """Test Event model functionality."""
    
    def test_event_creation(self, db_session, sample_user):
        """Test event creation."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        event = Event(
            user_id=sample_user.id,
            title="Test Meeting",
            description="A test meeting",
            start_time=start_time,
            end_time=end_time,
            location="Conference Room A",
            attendees=["user1@example.com", "user2@example.com"],
            ai_generated=True
        )
        db_session.add(event)
        db_session.commit()
        
        assert event.id is not None
        assert event.title == "Test Meeting"
        assert event.start_time == start_time
        assert event.end_time == end_time
        assert event.attendees == ["user1@example.com", "user2@example.com"]
        assert event.ai_generated is True

    def test_event_calendar_relationship(self, db_session, sample_user):
        """Test event-calendar relationship."""
        calendar = Calendar(user_id=sample_user.id, google_calendar_id="primary")
        db_session.add(calendar)
        db_session.commit()
        
        event = Event(
            user_id=sample_user.id,
            calendar_id=calendar.id,
            title="Test Event",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1)
        )
        db_session.add(event)
        db_session.commit()
        
        db_session.refresh(calendar)
        assert len(calendar.events) == 1
        assert calendar.events[0].title == "Test Event"


class TestTaskModel:
    """Test Task model functionality."""
    
    def test_task_creation(self, db_session, sample_user):
        """Test task creation with defaults."""
        task = Task(
            user_id=sample_user.id,
            title="Complete project",
            description="Finish the AI assistant project"
        )
        db_session.add(task)
        db_session.commit()
        
        assert task.id is not None
        assert task.title == "Complete project"
        assert task.priority == 3  # Default priority
        assert task.status == "pending"  # Default status
        assert task.created_by_ai is True  # Default value
        assert task.context_data == {}

    def test_task_context_data_jsonb(self, db_session, sample_user):
        """Test task context_data JSONB field."""
        context = {
            "source": "voice_command",
            "confidence": 0.95,
            "related_events": ["event1", "event2"]
        }
        
        task = Task(
            user_id=sample_user.id,
            title="Schedule meeting",
            context_data=context
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        assert task.context_data == context
        assert task.context_data["confidence"] == 0.95


class TestWhatsAppModels:
    """Test WhatsApp-related models."""
    
    def test_whatsapp_thread_creation(self, db_session, sample_user):
        """Test WhatsApp thread creation."""
        thread = WhatsAppThread(
            user_id=sample_user.id,
            phone_number="+1234567890",
            thread_status="active"
        )
        db_session.add(thread)
        db_session.commit()
        
        assert thread.id is not None
        assert thread.phone_number == "+1234567890"
        assert thread.thread_status == "active"
        assert thread.last_message_at is not None

    def test_whatsapp_message_creation(self, db_session, sample_user):
        """Test WhatsApp message creation."""
        thread = WhatsAppThread(
            user_id=sample_user.id,
            phone_number="+1234567890"
        )
        db_session.add(thread)
        db_session.commit()
        
        message = WhatsAppMessage(
            thread_id=thread.id,
            message_id="msg_123",
            direction="outbound",
            content="Hello, this is a test message",
            message_type="text",
            status="delivered"
        )
        db_session.add(message)
        db_session.commit()
        
        assert message.id is not None
        assert message.direction == "outbound"
        assert message.content == "Hello, this is a test message"
        assert message.status == "delivered"

    def test_whatsapp_thread_message_relationship(self, db_session, sample_user):
        """Test thread-message relationship and cascade deletion."""
        thread = WhatsAppThread(user_id=sample_user.id, phone_number="+1234567890")
        db_session.add(thread)
        db_session.commit()
        
        message1 = WhatsAppMessage(
            thread_id=thread.id,
            direction="inbound",
            content="Message 1"
        )
        message2 = WhatsAppMessage(
            thread_id=thread.id,
            direction="outbound",
            content="Message 2"
        )
        db_session.add_all([message1, message2])
        db_session.commit()
        
        db_session.refresh(thread)
        assert len(thread.messages) == 2
        
        # Test cascade deletion
        db_session.delete(thread)
        db_session.commit()
        
        assert db_session.query(WhatsAppMessage).filter_by(thread_id=thread.id).count() == 0


class TestFederatedLearningModels:
    """Test federated learning models."""
    
    def test_federated_round_creation(self, db_session):
        """Test federated round creation."""
        round_obj = FederatedRound(
            round_number=1,
            model_version="v1.0.0",
            aggregation_status="in_progress",
            participant_count=5
        )
        db_session.add(round_obj)
        db_session.commit()
        
        assert round_obj.id is not None
        assert round_obj.round_number == 1
        assert round_obj.model_version == "v1.0.0"
        assert round_obj.participant_count == 5
        assert round_obj.started_at is not None

    def test_client_update_creation(self, db_session, sample_user):
        """Test client update creation."""
        round_obj = FederatedRound(
            round_number=1,
            model_version="v1.0.0"
        )
        db_session.add(round_obj)
        db_session.commit()
        
        update = ClientUpdate(
            user_id=sample_user.id,
            round_id=round_obj.id,
            model_delta_encrypted="encrypted_model_data",
            privacy_budget_used=Decimal("0.00001234")
        )
        db_session.add(update)
        db_session.commit()
        
        assert update.id is not None
        assert update.model_delta_encrypted == "encrypted_model_data"
        assert update.privacy_budget_used == Decimal("0.00001234")

    def test_federated_round_client_updates_relationship(self, db_session, sample_user):
        """Test round-updates relationship."""
        round_obj = FederatedRound(round_number=1, model_version="v1.0.0")
        db_session.add(round_obj)
        db_session.commit()
        
        update1 = ClientUpdate(
            user_id=sample_user.id,
            round_id=round_obj.id,
            model_delta_encrypted="data1"
        )
        update2 = ClientUpdate(
            user_id=sample_user.id,
            round_id=round_obj.id,
            model_delta_encrypted="data2"
        )
        db_session.add_all([update1, update2])
        db_session.commit()
        
        db_session.refresh(round_obj)
        assert len(round_obj.client_updates) == 2


class TestPrivacyComplianceModels:
    """Test privacy and compliance models."""
    
    def test_consent_creation(self, db_session, sample_user):
        """Test consent record creation."""
        consent = Consent(
            user_id=sample_user.id,
            consent_type="data_processing",
            granted=True,
            consent_text="I agree to data processing for AI training purposes."
        )
        db_session.add(consent)
        db_session.commit()
        
        assert consent.id is not None
        assert consent.consent_type == "data_processing"
        assert consent.granted is True
        assert consent.granted_at is not None
        assert consent.revoked_at is None

    def test_consent_revocation(self, db_session, sample_user):
        """Test consent revocation."""
        consent = Consent(
            user_id=sample_user.id,
            consent_type="marketing",
            granted=True,
            consent_text="Marketing consent"
        )
        db_session.add(consent)
        db_session.commit()
        
        # Revoke consent
        consent.granted = False
        consent.revoked_at = datetime.now()
        db_session.commit()
        
        assert consent.granted is False
        assert consent.revoked_at is not None

    def test_audit_log_creation(self, db_session, sample_user):
        """Test audit log creation."""
        audit_log = AuditLog(
            user_id=sample_user.id,
            action="user_login",
            resource_type="authentication",
            resource_id=sample_user.id,
            details={"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Test Browser)"
        )
        db_session.add(audit_log)
        db_session.commit()
        
        assert audit_log.id is not None
        assert audit_log.action == "user_login"
        assert audit_log.details["ip"] == "192.168.1.1"
        assert audit_log.created_at is not None

    def test_audit_log_without_user(self, db_session):
        """Test audit log creation without associated user."""
        audit_log = AuditLog(
            action="system_startup",
            resource_type="system",
            details={"version": "1.0.0"}
        )
        db_session.add(audit_log)
        db_session.commit()
        
        assert audit_log.id is not None
        assert audit_log.user_id is None
        assert audit_log.action == "system_startup"