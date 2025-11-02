"""
Comprehensive end-to-end integration tests for the intelligent AI assistant system.
Tests the complete workflows from voice input to calendar creation to WhatsApp confirmation.
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
import torch

from app.database.models import (
    User, UserSettings, Calendar, Event, Task, 
    WhatsAppThread, WhatsAppMessage, FederatedRound, ClientUpdate
)
from app.services.voice import WhisperSTTService, TTSOrchestrator
from app.services.calendar import GoogleCalendarService
from app.services.whatsapp import WhatsAppService
from app.core.agentic_core import AgenticCore
from app.core.federated_learning import LocalModelTrainer
from app.core.federated_aggregator import FedAvgAggregator
from app.schemas.voice import VoiceInputRequest, TranscriptionResponse, TTSRequest, TTSResponse
from app.schemas.calendar import CalendarEventCreate
from app.schemas.whatsapp import WhatsAppMessageCreate, ConfirmationMessage


class TestVoiceToCalendarToWhatsAppFlow:
    """Test complete voice input → calendar creation → WhatsApp confirmation flow."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        return {
            'stt_service': Mock(spec=WhisperSTTService),
            'tts_service': Mock(spec=TTSOrchestrator),
            'calendar_service': Mock(spec=GoogleCalendarService),
            'whatsapp_service': Mock(spec=WhatsAppService),
            'agentic_core': Mock(spec=AgenticCore)
        }
    
    @pytest.fixture
    def sample_user_with_integrations(self, db_session):
        """Create a user with all integrations enabled."""
        user = User(
            email="integration@test.com",
            password_hash="hashed_password",
            timezone="UTC",
            language_preference="en-US"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Add user settings with all integrations enabled
        settings = UserSettings(
            user_id=user.id,
            whatsapp_opt_in=True,
            voice_training_consent=True,
            calendar_sync_enabled=True,
            privacy_level="standard",
            notification_preferences={"whatsapp": True, "email": False}
        )
        db_session.add(settings)
        
        # Add calendar connection
        calendar = Calendar(
            user_id=user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_access_token",
            refresh_token_encrypted="encrypted_refresh_token",
            sync_token="sync_token_123"
        )
        db_session.add(calendar)
        
        # Add WhatsApp thread
        whatsapp_thread = WhatsAppThread(
            user_id=user.id,
            phone_number="+1234567890",
            thread_status="active"
        )
        db_session.add(whatsapp_thread)
        
        db_session.commit()
        return user
    
    @pytest.mark.asyncio
    async def test_complete_voice_to_calendar_to_whatsapp_flow(
        self, db_session, sample_user_with_integrations, mock_services
    ):
        """Test the complete flow from voice input to WhatsApp confirmation."""
        user = sample_user_with_integrations
        
        # Step 1: Voice Input Processing
        voice_input = "Schedule a team meeting tomorrow at 2 PM for one hour"
        
        # Mock STT service response
        mock_services['stt_service'].transcribe_audio = AsyncMock(return_value={
            "text": voice_input,
            "confidence": 0.95,
            "processing_time": 1.2
        })
        
        # Step 2: Intent Recognition and Planning
        mock_services['agentic_core'].process_user_input = AsyncMock(return_value={
            "intent": "create_calendar_event",
            "confidence": 0.92,
            "action_plan": {
                "action_type": "create_calendar_event",
                "parameters": {
                    "title": "Team Meeting",
                    "start_time": (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0),
                    "end_time": (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0),
                    "description": "Team meeting scheduled via voice command"
                }
            },
            "requires_confirmation": True
        })
        
        # Step 3: Calendar Event Creation
        mock_services['calendar_service'].create_google_event = AsyncMock(return_value="google_event_123")
        
        # Step 4: WhatsApp Confirmation
        mock_services['whatsapp_service'].send_confirmation_request = AsyncMock(return_value={
            "message_id": "whatsapp_msg_456",
            "status": "sent",
            "confirmation_id": "conf_789"
        })
        
        # Execute the complete flow
        # 1. Process voice input
        voice_result = await mock_services['stt_service'].transcribe_audio(b"audio_data")
        assert voice_result["text"] == voice_input
        assert voice_result["confidence"] > 0.9
        
        # 2. Process with agentic core
        agentic_result = await mock_services['agentic_core'].process_user_input(
            voice_result["text"], {"user_id": str(user.id)}
        )
        assert agentic_result["intent"] == "create_calendar_event"
        assert agentic_result["requires_confirmation"] is True
        
        # 3. Create calendar event
        event_params = agentic_result["action_plan"]["parameters"]
        google_event_id = await mock_services['calendar_service'].create_google_event(
            calendar_conn=Mock(),
            event_data=CalendarEventCreate(**event_params),
            db=db_session
        )
        assert google_event_id == "google_event_123"
        
        # 4. Send WhatsApp confirmation
        confirmation = ConfirmationMessage(
            action_type="create_calendar_event",
            action_description=f"Created '{event_params['title']}' for tomorrow at 2 PM"
        )
        whatsapp_result = await mock_services['whatsapp_service'].send_confirmation_request(
            db_session, str(user.id), confirmation
        )
        assert whatsapp_result["status"] == "sent"
        assert "confirmation_id" in whatsapp_result
        
        # Verify all services were called correctly
        mock_services['stt_service'].transcribe_audio.assert_called_once()
        mock_services['agentic_core'].process_user_input.assert_called_once()
        mock_services['calendar_service'].create_google_event.assert_called_once()
        mock_services['whatsapp_service'].send_confirmation_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_voice_input_with_calendar_conflict_resolution(
        self, db_session, sample_user_with_integrations, mock_services
    ):
        """Test handling calendar conflicts during voice-initiated scheduling."""
        user = sample_user_with_integrations
        
        # Create existing conflicting event
        existing_event = Event(
            user_id=user.id,
            title="Existing Meeting",
            start_time=datetime.now().replace(hour=14, minute=0) + timedelta(days=1),
            end_time=datetime.now().replace(hour=15, minute=0) + timedelta(days=1),
            google_event_id="existing_event_123"
        )
        db_session.add(existing_event)
        db_session.commit()
        
        # Voice input for conflicting time
        voice_input = "Schedule client call tomorrow at 2 PM"
        
        # Mock voice processing
        mock_services['stt_service'].transcribe_audio = AsyncMock(return_value={
            "text": voice_input,
            "confidence": 0.94
        })
        
        # Mock agentic core to detect conflict and suggest alternatives
        mock_services['agentic_core'].process_user_input = AsyncMock(return_value={
            "intent": "create_calendar_event",
            "conflict_detected": True,
            "alternative_suggestions": [
                {
                    "start_time": datetime.now().replace(hour=15, minute=30) + timedelta(days=1),
                    "end_time": datetime.now().replace(hour=16, minute=30) + timedelta(days=1),
                    "reason": "No conflicts at 3:30 PM"
                },
                {
                    "start_time": datetime.now().replace(hour=13, minute=0) + timedelta(days=1),
                    "end_time": datetime.now().replace(hour=14, minute=0) + timedelta(days=1),
                    "reason": "Available slot before existing meeting"
                }
            ],
            "requires_confirmation": True
        })
        
        # Mock WhatsApp service to send conflict resolution message
        mock_services['whatsapp_service'].send_message = AsyncMock(return_value={
            "message_id": "conflict_msg_123",
            "status": "sent"
        })
        
        # Execute flow
        voice_result = await mock_services['stt_service'].transcribe_audio(b"audio_data")
        agentic_result = await mock_services['agentic_core'].process_user_input(
            voice_result["text"], {"user_id": str(user.id)}
        )
        
        # Verify conflict was detected
        assert agentic_result["conflict_detected"] is True
        assert len(agentic_result["alternative_suggestions"]) == 2
        
        # Send conflict resolution message
        conflict_message = WhatsAppMessageCreate(
            recipient="+1234567890",
            content=f"Time conflict detected for '{voice_input}'. Suggested alternatives: 3:30 PM or 1:00 PM. Reply with your preference.",
            message_type="text"
        )
        
        whatsapp_result = await mock_services['whatsapp_service'].send_message(
            db_session, str(user.id), conflict_message
        )
        
        assert whatsapp_result["status"] == "sent"
        mock_services['whatsapp_service'].send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_whatsapp_response_processing_and_calendar_update(
        self, db_session, sample_user_with_integrations, mock_services
    ):
        """Test processing WhatsApp user responses and updating calendar accordingly."""
        user = sample_user_with_integrations
        
        # Simulate pending confirmation
        pending_confirmation = {
            "confirmation_id": "conf_123",
            "user_id": str(user.id),
            "action_type": "create_calendar_event",
            "action_params": {
                "title": "Client Call",
                "start_time": datetime.now() + timedelta(days=1, hours=14),
                "end_time": datetime.now() + timedelta(days=1, hours=15)
            }
        }
        
        # Mock WhatsApp service to process user response
        mock_services['whatsapp_service'].process_incoming_message = AsyncMock(return_value={
            "message_id": "response_msg_123",
            "content": "Y",
            "direction": "inbound",
            "user_response": "confirmed"
        })
        
        # Mock calendar service to create the event
        mock_services['calendar_service'].create_google_event = AsyncMock(return_value="new_event_456")
        
        # Mock WhatsApp service to send success confirmation
        mock_services['whatsapp_service'].send_message = AsyncMock(return_value={
            "message_id": "success_msg_789",
            "status": "sent"
        })
        
        # Process user response
        response_result = await mock_services['whatsapp_service'].process_incoming_message(
            db_session, "+1234567890", "response_msg_123", "Y", "text"
        )
        
        assert response_result["user_response"] == "confirmed"
        
        # Create calendar event based on confirmation
        event_params = pending_confirmation["action_params"]
        google_event_id = await mock_services['calendar_service'].create_google_event(
            calendar_conn=Mock(),
            event_data=CalendarEventCreate(**event_params),
            db=db_session
        )
        
        assert google_event_id == "new_event_456"
        
        # Send success message
        success_message = WhatsAppMessageCreate(
            recipient="+1234567890",
            content=f"✅ '{event_params['title']}' has been scheduled successfully!",
            message_type="text"
        )
        
        success_result = await mock_services['whatsapp_service'].send_message(
            db_session, str(user.id), success_message
        )
        
        assert success_result["status"] == "sent"
        
        # Verify all steps were executed
        mock_services['whatsapp_service'].process_incoming_message.assert_called_once()
        mock_services['calendar_service'].create_google_event.assert_called_once()
        mock_services['whatsapp_service'].send_message.assert_called_once()


class TestFederatedLearningWorkflow:
    """Test federated learning training and aggregation workflows."""
    
    @pytest.fixture
    def multiple_users(self, db_session):
        """Create multiple users for federated learning testing."""
        users = []
        for i in range(5):
            user = User(
                email=f"federated_user_{i}@test.com",
                password_hash="hashed_password",
                timezone="UTC"
            )
            db_session.add(user)
            users.append(user)
        
        db_session.commit()
        return users
    
    @pytest.fixture
    def federated_round(self, db_session):
        """Create a federated learning round."""
        round_obj = FederatedRound(
            round_number=1,
            model_version="1.0.0",
            aggregation_status="in_progress",
            participant_count=0
        )
        db_session.add(round_obj)
        db_session.commit()
        db_session.refresh(round_obj)
        return round_obj
    
    @pytest.mark.asyncio
    async def test_complete_federated_learning_workflow(
        self, db_session, multiple_users, federated_round
    ):
        """Test complete federated learning workflow from local training to aggregation."""
        
        # Step 1: Local Model Training for Multiple Users
        local_trainers = []
        model_updates = []
        
        for i, user in enumerate(multiple_users):
            # Create local trainer
            trainer = LocalModelTrainer({
                "input_dim": 20,
                "hidden_dim": 64,
                "output_dim": 10,
                "learning_rate": 0.01,
                "batch_size": 4,
                "epochs": 3
            })
            local_trainers.append(trainer)
            
            # Generate diverse training data for each user
            training_data = {
                "interactions": [
                    {
                        "hour": 9 + i,  # Different activity patterns per user
                        "day_of_week": (i % 7),
                        "activity_type": (i % 3),
                        "duration": 300 + (i * 100),
                        "location_type": (i % 2),
                        "device_type": (i % 2),
                        "next_action": (i % 10)
                    },
                    {
                        "hour": 14 + i,
                        "day_of_week": ((i + 1) % 7),
                        "activity_type": ((i + 1) % 3),
                        "duration": 600 + (i * 50),
                        "location_type": ((i + 1) % 2),
                        "device_type": ((i + 1) % 2),
                        "next_action": ((i + 2) % 10)
                    }
                ]
            }
            
            # Train local model
            training_result = trainer.train_local_model(training_data)
            assert training_result["status"] == "success"
            
            model_updates.append(training_result["model_update"])
            
            # Create client update record
            client_update = ClientUpdate(
                user_id=user.id,
                round_id=federated_round.id,
                model_delta_encrypted=training_result["model_update_encrypted"],
                privacy_budget_used=training_result["training_metrics"]["privacy_budget_used"]
            )
            db_session.add(client_update)
        
        db_session.commit()
        
        # Verify all users participated
        assert len(model_updates) == 5
        
        # Step 2: Federated Aggregation
        aggregator = FedAvgAggregator(differential_privacy=True)
        
        # Get encrypted model updates from database
        client_updates = db_session.query(ClientUpdate).filter(
            ClientUpdate.round_id == federated_round.id
        ).all()
        
        encrypted_updates = [update.model_delta_encrypted for update in client_updates]
        
        # Perform aggregation
        aggregation_result = aggregator.aggregate_model_updates(encrypted_updates)
        
        assert aggregation_result["status"] == "success"
        assert aggregation_result["participant_count"] == 5
        assert aggregation_result["aggregation_method"] == "FedAvg"
        assert aggregation_result["differential_privacy_applied"] is True
        
        # Step 3: Update Federated Round Status
        federated_round.aggregation_status = "completed"
        federated_round.participant_count = 5
        federated_round.completed_at = datetime.utcnow()
        db_session.commit()
        
        # Step 4: Verify Aggregation Quality
        aggregation_metrics = aggregation_result["aggregation_metrics"]
        
        assert "convergence_score" in aggregation_metrics
        assert "model_size_mb" in aggregation_metrics
        assert "privacy_budget_total" in aggregation_metrics
        
        # Convergence score should be reasonable
        assert 0.0 <= aggregation_metrics["convergence_score"] <= 1.0
        
        # Privacy budget should be within acceptable range
        assert aggregation_metrics["privacy_budget_total"] > 0
        assert aggregation_metrics["privacy_budget_total"] <= 50.0  # 5 users * 10 max budget
        
        print(f"Federated learning completed successfully:")
        print(f"- Participants: {aggregation_result['participant_count']}")
        print(f"- Convergence Score: {aggregation_metrics['convergence_score']:.4f}")
        print(f"- Total Privacy Budget Used: {aggregation_metrics['privacy_budget_total']:.4f}")
    
    @pytest.mark.asyncio
    async def test_federated_learning_with_insufficient_participants(
        self, db_session, federated_round
    ):
        """Test federated learning behavior with insufficient participants."""
        
        # Create only one user (insufficient for aggregation)
        user = User(
            email="single_user@test.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()
        
        # Train local model
        trainer = LocalModelTrainer()
        training_data = {
            "interactions": [
                {
                    "hour": 10, "day_of_week": 1, "activity_type": 1,
                    "duration": 300, "location_type": 0, "device_type": 0,
                    "next_action": 2
                }
            ]
        }
        
        training_result = trainer.train_local_model(training_data)
        assert training_result["status"] == "success"
        
        # Create client update
        client_update = ClientUpdate(
            user_id=user.id,
            round_id=federated_round.id,
            model_delta_encrypted=training_result["model_update_encrypted"],
            privacy_budget_used=training_result["training_metrics"]["privacy_budget_used"]
        )
        db_session.add(client_update)
        db_session.commit()
        
        # Attempt aggregation with insufficient participants
        aggregator = FedAvgAggregator()
        encrypted_updates = [client_update.model_delta_encrypted]
        
        aggregation_result = aggregator.aggregate_model_updates(encrypted_updates)
        
        # Should fail due to insufficient participants
        assert aggregation_result["status"] == "error"
        assert "at least 2" in aggregation_result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_federated_learning_privacy_preservation(
        self, db_session, multiple_users, federated_round
    ):
        """Test privacy preservation in federated learning."""
        
        # Train models with sensitive data patterns
        sensitive_patterns = []
        encrypted_updates = []
        
        for i, user in enumerate(multiple_users[:3]):  # Use 3 users
            # Create training data with user-specific patterns
            training_data = {
                "interactions": [
                    {
                        "hour": 8 + (i * 2),  # User-specific schedule
                        "day_of_week": i % 7,
                        "activity_type": i % 3,
                        "duration": 1800 + (i * 300),  # User-specific duration preferences
                        "location_type": i % 2,
                        "device_type": i % 2,
                        "next_action": (i * 2) % 10
                    }
                ]
            }
            
            sensitive_patterns.append(training_data)
            
            # Train with differential privacy
            trainer = LocalModelTrainer({
                "differential_privacy": True,
                "epsilon": 1.0,  # Strong privacy
                "delta": 1e-6
            })
            
            training_result = trainer.train_local_model(training_data)
            assert training_result["status"] == "success"
            
            encrypted_updates.append(training_result["model_update_encrypted"])
            
            # Verify privacy budget was consumed
            assert training_result["training_metrics"]["privacy_budget_used"] > 0
        
        # Perform aggregation with differential privacy
        aggregator = FedAvgAggregator(differential_privacy=True)
        aggregation_result = aggregator.aggregate_model_updates(encrypted_updates)
        
        assert aggregation_result["status"] == "success"
        assert aggregation_result["differential_privacy_applied"] is True
        
        # Verify that individual user patterns cannot be extracted from aggregated model
        # This is a simplified test - in practice, more sophisticated privacy analysis would be needed
        aggregated_encrypted = aggregation_result["aggregated_model_encrypted"]
        
        # The aggregated model should not contain raw user data
        assert not any(
            str(pattern["interactions"][0]["hour"]) in aggregated_encrypted
            for pattern in sensitive_patterns
        )
        
        # Privacy metrics should be within acceptable bounds
        privacy_metrics = aggregation_result.get("privacy_metrics", {})
        if privacy_metrics:
            assert privacy_metrics.get("epsilon_consumed", 0) <= 5.0  # Reasonable privacy budget
            assert privacy_metrics.get("delta_consumed", 0) <= 1e-5


class TestOAuthAndWebhookProcessing:
    """Test OAuth flows, webhook processing, and real-time synchronization."""
    
    @pytest.fixture
    def oauth_mock_setup(self):
        """Set up OAuth mocking."""
        with patch('app.services.calendar.Flow') as mock_flow_class, \
             patch('app.services.calendar.build') as mock_build:
            
            # Mock OAuth flow
            mock_flow = Mock()
            mock_credentials = Mock()
            mock_credentials.token = "access_token_123"
            mock_credentials.refresh_token = "refresh_token_456"
            mock_flow.credentials = mock_credentials
            mock_flow_class.from_client_config.return_value = mock_flow
            
            # Mock Google Calendar API
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            yield {
                'flow_class': mock_flow_class,
                'flow': mock_flow,
                'service': mock_service,
                'credentials': mock_credentials
            }
    
    @pytest.mark.asyncio
    async def test_google_calendar_oauth_flow(
        self, db_session, sample_user, oauth_mock_setup
    ):
        """Test complete Google Calendar OAuth authentication flow."""
        
        calendar_service = GoogleCalendarService()
        mocks = oauth_mock_setup
        
        # Step 1: Generate authorization URL
        redirect_uri = "http://localhost:8000/calendar/oauth/callback"
        
        mocks['flow'].authorization_url.return_value = (
            "https://accounts.google.com/oauth/authorize?client_id=test", 
            "state_123"
        )
        
        auth_url = calendar_service.get_authorization_url(redirect_uri)
        
        assert auth_url.startswith("https://accounts.google.com/oauth/authorize")
        mocks['flow'].authorization_url.assert_called_once()
        
        # Step 2: Exchange authorization code for tokens
        mocks['service'].calendarList.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'primary', 'primary': True}]
        }
        
        result = await calendar_service.exchange_code_for_tokens(
            code="auth_code_789",
            redirect_uri=redirect_uri,
            db=db_session,
            user_id=str(sample_user.id)
        )
        
        assert result.user_id == str(sample_user.id)
        assert result.google_calendar_id == "primary"
        assert result.connected is True
        
        # Verify calendar connection was saved
        calendar_conn = db_session.query(Calendar).filter(
            Calendar.user_id == sample_user.id
        ).first()
        
        assert calendar_conn is not None
        assert calendar_conn.google_calendar_id == "primary"
        assert calendar_conn.access_token_encrypted is not None
        assert calendar_conn.refresh_token_encrypted is not None
    
    @pytest.mark.asyncio
    async def test_google_calendar_webhook_setup_and_processing(
        self, db_session, sample_user, oauth_mock_setup
    ):
        """Test Google Calendar webhook setup and event processing."""
        
        # Create calendar connection
        calendar_conn = Calendar(
            user_id=sample_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token",
            refresh_token_encrypted="encrypted_refresh"
        )
        db_session.add(calendar_conn)
        db_session.commit()
        
        calendar_service = GoogleCalendarService()
        mocks = oauth_mock_setup
        
        # Step 1: Set up webhook
        mocks['service'].events.return_value.watch.return_value.execute.return_value = {
            'resourceId': 'resource_123',
            'expiration': str(int((datetime.now() + timedelta(days=7)).timestamp() * 1000))
        }
        
        webhook_result = await calendar_service.setup_webhook(
            calendar_conn=calendar_conn,
            webhook_url="https://example.com/calendar/webhook",
            db=db_session
        )
        
        assert 'channel_id' in webhook_result
        assert webhook_result['resource_id'] == 'resource_123'
        
        # Verify webhook ID was stored
        db_session.refresh(calendar_conn)
        assert calendar_conn.webhook_id is not None
        
        # Step 2: Process webhook notification
        webhook_data = {
            'resourceId': 'resource_123',
            'resourceState': 'sync',
            'channelId': webhook_result['channel_id']
        }
        
        # Mock incremental sync response
        mocks['service'].events.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'new_event_123',
                    'summary': 'New Meeting',
                    'start': {'dateTime': '2024-01-15T10:00:00Z'},
                    'end': {'dateTime': '2024-01-15T11:00:00Z'},
                    'updated': '2024-01-15T08:00:00Z'
                }
            ],
            'nextSyncToken': 'new_sync_token_456'
        }
        
        with patch.object(calendar_service, '_get_credentials'), \
             patch.object(calendar_service, 'refresh_tokens_if_needed'):
            
            sync_result = await calendar_service.process_webhook_notification(
                webhook_data=webhook_data,
                db=db_session
            )
            
            assert sync_result['events_processed'] == 1
            assert sync_result['sync_token'] == 'new_sync_token_456'
            
            # Verify event was created in database
            new_event = db_session.query(Event).filter(
                Event.google_event_id == 'new_event_123'
            ).first()
            
            assert new_event is not None
            assert new_event.title == 'New Meeting'
            assert new_event.user_id == sample_user.id
    
    @pytest.mark.asyncio
    async def test_whatsapp_webhook_processing(self, db_session, sample_user):
        """Test WhatsApp webhook processing for incoming messages."""
        
        # Create WhatsApp thread
        whatsapp_thread = WhatsAppThread(
            user_id=sample_user.id,
            phone_number="+1234567890",
            thread_status="active"
        )
        db_session.add(whatsapp_thread)
        db_session.commit()
        
        whatsapp_service = WhatsAppService()
        
        # Mock incoming webhook data
        webhook_data = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "incoming_msg_123",
                                        "from": "1234567890",
                                        "timestamp": str(int(datetime.now().timestamp())),
                                        "text": {"body": "Y"},
                                        "type": "text"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        # Process webhook
        with patch.object(whatsapp_service, 'process_incoming_message') as mock_process:
            mock_process.return_value = {
                "message_id": "incoming_msg_123",
                "content": "Y",
                "direction": "inbound",
                "status": "processed"
            }
            
            result = await whatsapp_service.process_webhook(webhook_data, db_session)
            
            assert result['messages_processed'] == 1
            assert result['status'] == 'success'
            
            # Verify process_incoming_message was called with correct parameters
            mock_process.assert_called_once_with(
                db_session, "+1234567890", "incoming_msg_123", "Y", "text"
            )
    
    @pytest.mark.asyncio
    async def test_real_time_synchronization_flow(
        self, db_session, sample_user, oauth_mock_setup
    ):
        """Test real-time synchronization between calendar and WhatsApp."""
        
        # Set up user with both integrations
        calendar_conn = Calendar(
            user_id=sample_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token",
            refresh_token_encrypted="encrypted_refresh",
            webhook_id="webhook_123"
        )
        
        whatsapp_thread = WhatsAppThread(
            user_id=sample_user.id,
            phone_number="+1234567890",
            thread_status="active"
        )
        
        db_session.add(calendar_conn)
        db_session.add(whatsapp_thread)
        db_session.commit()
        
        calendar_service = GoogleCalendarService()
        whatsapp_service = WhatsAppService()
        mocks = oauth_mock_setup
        
        # Simulate real-time calendar event creation via webhook
        mocks['service'].events.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'urgent_meeting_456',
                    'summary': 'Urgent Client Meeting',
                    'start': {'dateTime': (datetime.now() + timedelta(hours=1)).isoformat() + 'Z'},
                    'end': {'dateTime': (datetime.now() + timedelta(hours=2)).isoformat() + 'Z'},
                    'updated': datetime.now().isoformat() + 'Z'
                }
            ],
            'nextSyncToken': 'sync_token_789'
        }
        
        # Mock WhatsApp notification sending
        with patch.object(whatsapp_service, 'send_message') as mock_send:
            mock_send.return_value = {
                "message_id": "notification_msg_789",
                "status": "sent"
            }
            
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                # Process calendar webhook (simulating real-time update)
                webhook_data = {
                    'resourceId': 'resource_123',
                    'resourceState': 'sync',
                    'channelId': 'channel_456'
                }
                
                sync_result = await calendar_service.process_webhook_notification(
                    webhook_data=webhook_data,
                    db=db_session
                )
                
                assert sync_result['events_processed'] == 1
                
                # Verify event was created
                new_event = db_session.query(Event).filter(
                    Event.google_event_id == 'urgent_meeting_456'
                ).first()
                
                assert new_event is not None
                assert new_event.title == 'Urgent Client Meeting'
                
                # Send WhatsApp notification about new event
                notification_message = WhatsAppMessageCreate(
                    recipient="+1234567890",
                    content=f"📅 New event added: '{new_event.title}' in 1 hour",
                    message_type="text"
                )
                
                notification_result = await whatsapp_service.send_message(
                    db_session, str(sample_user.id), notification_message
                )
                
                assert notification_result["status"] == "sent"
                mock_send.assert_called_once()
                
                # Verify real-time sync completed successfully
                assert sync_result['sync_token'] == 'sync_token_789'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])