"""
Unit tests for Celery tasks.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

from app.tasks.ai_processing import (
    process_voice_input, generate_task_plan, execute_task_step, generate_tts_audio
)
from app.tasks.calendar_sync import (
    sync_user_calendar, sync_all_calendars, create_calendar_event, process_calendar_webhook
)
from app.tasks.messaging import (
    send_whatsapp_message, send_confirmation_message, process_whatsapp_response, send_daily_summary
)
from app.tasks.federated_learning import (
    train_local_model, aggregate_model_updates, process_federated_round, cleanup_old_rounds
)
from app.database.models import User, Calendar, Event, Task, WhatsAppThread, FederatedRound, ClientUpdate


class TestAIProcessingTasks:
    """Test AI processing tasks."""
    
    @patch('app.tasks.ai_processing.SessionLocal')
    @patch('app.tasks.ai_processing.current_task')
    def test_process_voice_input_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful voice input processing."""
        # Mock current task
        mock_current_task.request.id = "task_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        # Test voice processing
        result = process_voice_input("user_123", b"audio_data", "session_456")
        
        # Verify result structure
        assert result["text"] == "Schedule a meeting tomorrow at 3 PM"
        assert result["intent"]["type"] == "calendar_create"
        assert result["intent"]["confidence"] == 0.95
        assert result["session_id"] == "session_456"
        assert result["task_id"] == "task_123"
        
        # Verify audit log was created
        from app.database.models import AuditLog
        audit_logs = db_session.query(AuditLog).filter_by(action="voice_processed").all()
        assert len(audit_logs) == 1
    
    @patch('app.tasks.ai_processing.SessionLocal')
    @patch('app.tasks.ai_processing.current_task')
    def test_generate_task_plan_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful task plan generation."""
        # Mock current task
        mock_current_task.request.id = "plan_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        # Test intent
        intent = {
            "type": "calendar_create",
            "entities": {"title": "meeting", "date": "tomorrow"}
        }
        
        # Generate task plan
        result = generate_task_plan(str(user.id), intent, {})
        
        # Verify result structure
        assert result["id"] == "plan_plan_123"
        assert result["title"] == "Execute calendar_create action"
        assert len(result["steps"]) == 3
        assert result["requires_confirmation"] is True
        assert "database_id" in result
        
        # Verify task was stored in database
        tasks = db_session.query(Task).filter_by(user_id=user.id).all()
        assert len(tasks) == 1
        assert tasks[0].created_by_ai is True
    
    @patch('app.tasks.ai_processing.SessionLocal')
    @patch('app.tasks.ai_processing.current_task')
    def test_execute_task_step_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful task step execution."""
        # Mock current task
        mock_current_task.request.id = "step_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user and task
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        task = Task(
            user_id=user.id,
            title="Test Task",
            context_data={"task_plan": {"id": "plan_123"}}
        )
        db_session.add(task)
        db_session.commit()
        
        # Execute task step
        result = execute_task_step(str(user.id), "plan_123", 0)
        
        # Verify result
        assert result["step_index"] == 0
        assert result["status"] == "completed"
        assert "result" in result
        assert "duration" in result
        
        # Verify task was updated
        db_session.refresh(task)
        assert "execution_results" in task.context_data
        assert len(task.context_data["execution_results"]) == 1
    
    @patch('app.tasks.ai_processing.current_task')
    def test_generate_tts_audio_success(self, mock_current_task):
        """Test successful TTS audio generation."""
        # Mock current task
        mock_current_task.request.id = "tts_123"
        
        # Generate TTS audio
        result = generate_tts_audio("Hello, this is a test message", "user_123")
        
        # Verify result
        assert result["audio_url"] == "/audio/tts/tts_123.wav"
        assert result["format"] == "wav"
        assert result["sample_rate"] == 22050
        assert result["duration"] > 0
        assert result["voice_id"] == "default"


class TestCalendarSyncTasks:
    """Test calendar synchronization tasks."""
    
    @patch('app.tasks.calendar_sync.SessionLocal')
    @patch('app.tasks.calendar_sync.current_task')
    def test_sync_user_calendar_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful user calendar sync."""
        # Mock current task
        mock_current_task.request.id = "sync_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user and calendar
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        calendar = Calendar(
            user_id=user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token"
        )
        db_session.add(calendar)
        db_session.commit()
        
        # Sync calendar
        result = sync_user_calendar(str(user.id), str(calendar.id))
        
        # Verify result
        assert result["calendar_id"] == str(calendar.id)
        assert result["events_added"] == 3
        assert result["events_updated"] == 1
        assert result["events_deleted"] == 0
        assert "sync_token" in result
        
        # Verify calendar was updated
        db_session.refresh(calendar)
        assert calendar.sync_token == result["sync_token"]
    
    @patch('app.tasks.calendar_sync.SessionLocal')
    @patch('app.tasks.calendar_sync.sync_user_calendar.delay')
    def test_sync_all_calendars_success(self, mock_sync_delay, mock_session_local, db_session):
        """Test bulk calendar sync."""
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test calendars
        user1 = User(email="user1@example.com")
        user2 = User(email="user2@example.com")
        db_session.add_all([user1, user2])
        db_session.commit()
        
        calendar1 = Calendar(user_id=user1.id, access_token_encrypted="token1")
        calendar2 = Calendar(user_id=user2.id, access_token_encrypted="token2")
        db_session.add_all([calendar1, calendar2])
        db_session.commit()
        
        # Mock successful task dispatch
        mock_sync_delay.return_value = MagicMock()
        
        # Sync all calendars
        result = sync_all_calendars()
        
        # Verify result
        assert result["total_calendars"] == 2
        assert result["successful_syncs"] == 2
        assert result["failed_syncs"] == 0
        
        # Verify individual sync tasks were dispatched
        assert mock_sync_delay.call_count == 2
    
    @patch('app.tasks.calendar_sync.SessionLocal')
    @patch('app.tasks.calendar_sync.current_task')
    def test_create_calendar_event_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful calendar event creation."""
        # Mock current task
        mock_current_task.request.id = "event_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user and calendar
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        calendar = Calendar(user_id=user.id, google_calendar_id="primary")
        db_session.add(calendar)
        db_session.commit()
        
        # Event data
        event_data = {
            "title": "Test Meeting",
            "description": "A test meeting",
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=1),
            "location": "Conference Room",
            "attendees": ["user@example.com"]
        }
        
        # Create event
        result = create_calendar_event(str(user.id), event_data)
        
        # Verify result
        assert result["title"] == "Test Meeting"
        assert result["google_event_id"] == "google_event_event_123"
        assert "local_event_id" in result
        
        # Verify event was stored in database
        events = db_session.query(Event).filter_by(user_id=user.id).all()
        assert len(events) == 1
        assert events[0].title == "Test Meeting"


class TestMessagingTasks:
    """Test messaging tasks."""
    
    @patch('app.tasks.messaging.SessionLocal')
    @patch('app.tasks.messaging.current_task')
    def test_send_whatsapp_message_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful WhatsApp message sending."""
        # Mock current task
        mock_current_task.request.id = "msg_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        # Send message
        result = send_whatsapp_message(str(user.id), "Hello, this is a test message")
        
        # Verify result
        assert result["message_id"] == "whatsapp_msg_msg_123"
        assert result["status"] == "sent"
        assert result["recipient"] == "+1234567890"
        assert result["delivery_status"] == "delivered"
        
        # Verify thread and message were created
        from app.database.models import WhatsAppThread, WhatsAppMessage
        threads = db_session.query(WhatsAppThread).filter_by(user_id=user.id).all()
        assert len(threads) == 1
        
        messages = db_session.query(WhatsAppMessage).filter_by(thread_id=threads[0].id).all()
        assert len(messages) == 1
        assert messages[0].content == "Hello, this is a test message"
        assert messages[0].direction == "outbound"
    
    @patch('app.tasks.messaging.send_whatsapp_message.delay')
    def test_send_confirmation_message_success(self, mock_send_delay, db_session):
        """Test successful confirmation message sending."""
        # Mock WhatsApp message sending
        mock_result = MagicMock()
        mock_result.get.return_value = {
            "message_id": "conf_123",
            "status": "sent"
        }
        mock_send_delay.return_value = mock_result
        
        # Create test user
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        # Send confirmation
        result = send_confirmation_message(
            str(user.id),
            "Schedule meeting with John",
            {"details": "Tomorrow at 3 PM"}
        )
        
        # Verify result
        assert result["confirmation_id"] == "conf_123"
        assert result["status"] == "sent"
        assert result["awaiting_response"] is True
        
        # Verify WhatsApp message was dispatched
        mock_send_delay.assert_called_once()
    
    @patch('app.tasks.messaging.SessionLocal')
    @patch('app.tasks.messaging.current_task')
    def test_process_whatsapp_response_confirmation(self, mock_current_task, mock_session_local, db_session):
        """Test processing WhatsApp confirmation response."""
        # Mock current task
        mock_current_task.request.id = "resp_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user and thread
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        thread = WhatsAppThread(user_id=user.id, phone_number="+1234567890")
        db_session.add(thread)
        db_session.commit()
        
        # Process "Yes" response
        webhook_data = {
            "from": "+1234567890",
            "text": {"body": "Y"},
            "id": "msg_456"
        }
        
        result = process_whatsapp_response(webhook_data)
        
        # Verify result
        assert result["status"] == "processed"
        assert result["action"] == "confirmed"
        
        # Verify message was stored
        from app.database.models import WhatsAppMessage
        messages = db_session.query(WhatsAppMessage).filter_by(thread_id=thread.id).all()
        assert len(messages) == 1
        assert messages[0].direction == "inbound"
        assert messages[0].content == "Y"


class TestFederatedLearningTasks:
    """Test federated learning tasks."""
    
    @patch('app.tasks.federated_learning.SessionLocal')
    @patch('app.tasks.federated_learning.current_task')
    def test_train_local_model_success(self, mock_current_task, mock_session_local, db_session):
        """Test successful local model training."""
        # Mock current task
        mock_current_task.request.id = "train_123"
        
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test user
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        # Training data
        training_data = {
            "sample_count": 100,
            "features": ["feature1", "feature2"]
        }
        
        # Train model
        result = train_local_model(str(user.id), training_data)
        
        # Verify result
        assert result["user_id"] == str(user.id)
        assert result["model_version"] == "v1.0.0"
        assert result["training_samples"] == 100
        assert result["privacy_budget_used"] == 0.001
        assert "model_delta_encrypted" in result
        assert "training_metrics" in result
        
        # Verify federated round and client update were created
        rounds = db_session.query(FederatedRound).all()
        assert len(rounds) == 1
        
        updates = db_session.query(ClientUpdate).filter_by(user_id=user.id).all()
        assert len(updates) == 1
        assert updates[0].privacy_budget_used == Decimal("0.001")
    
    @patch('app.tasks.federated_learning.SessionLocal')
    def test_aggregate_model_updates_success(self, mock_session_local, db_session):
        """Test successful model aggregation."""
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Create test federated round
        fed_round = FederatedRound(
            round_number=1,
            model_version="v1.0.0",
            aggregation_status="in_progress"
        )
        db_session.add(fed_round)
        db_session.commit()
        
        # Create test users and client updates
        users = []
        for i in range(3):
            user = User(email=f"user{i}@example.com")
            db_session.add(user)
            users.append(user)
        db_session.commit()
        
        for user in users:
            update = ClientUpdate(
                user_id=user.id,
                round_id=fed_round.id,
                model_delta_encrypted=f"encrypted_data_{user.id}",
                privacy_budget_used=Decimal("0.001")
            )
            db_session.add(update)
        db_session.commit()
        
        # Aggregate models
        result = aggregate_model_updates(str(fed_round.id))
        
        # Verify result
        assert result["round_id"] == str(fed_round.id)
        assert result["participant_count"] == 3
        assert result["aggregation_method"] == "FedAvg"
        assert result["privacy_preserved"] is True
        assert "global_model_metrics" in result
        assert "differential_privacy" in result
        
        # Verify round status was updated
        db_session.refresh(fed_round)
        assert fed_round.aggregation_status == "completed"
    
    @patch('app.tasks.federated_learning.SessionLocal')
    @patch('app.tasks.federated_learning.aggregate_model_updates.delay')
    def test_process_federated_round_aggregation(self, mock_aggregate_delay, mock_session_local, db_session):
        """Test federated round processing with aggregation."""
        # Mock database session
        mock_session_local.return_value.__enter__.return_value = db_session
        
        # Mock aggregation result
        mock_result = MagicMock()
        mock_result.get.return_value = {
            "participant_count": 5,
            "aggregation_method": "FedAvg"
        }
        mock_aggregate_delay.return_value = mock_result
        
        # Create test round with enough participants
        fed_round = FederatedRound(
            round_number=1,
            model_version="v1.0.0",
            aggregation_status="in_progress"
        )
        db_session.add(fed_round)
        db_session.commit()
        
        # Create client updates (5 participants)
        for i in range(5):
            user = User(email=f"user{i}@example.com")
            db_session.add(user)
            db_session.commit()
            
            update = ClientUpdate(
                user_id=user.id,
                round_id=fed_round.id,
                model_delta_encrypted=f"data_{i}"
            )
            db_session.add(update)
        db_session.commit()
        
        # Process round
        result = process_federated_round()
        
        # Verify result
        assert result["current_round_processed"] is True
        assert result["new_round_started"] is True
        assert result["participant_count"] == 5
        
        # Verify aggregation was triggered
        mock_aggregate_delay.assert_called_once_with(str(fed_round.id))
        
        # Verify new round was created
        new_rounds = db_session.query(FederatedRound).filter_by(round_number=2).all()
        assert len(new_rounds) == 1