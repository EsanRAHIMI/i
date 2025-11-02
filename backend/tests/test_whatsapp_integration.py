"""
Unit tests for WhatsApp Business Cloud API integration.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.whatsapp import WhatsAppService, WhatsAppBusinessAPI, MessageTemplateManager
from app.services.workflow_manager import WorkflowManager
from app.schemas.whatsapp import (
    WhatsAppMessageCreate, ConfirmationMessage, OptInRequest,
    DailySummary, UserResponse, MessageType, MessageDirection, MessageStatus
)
from app.database.models import (
    User, UserSettings, WhatsAppThread, WhatsAppMessage, 
    Task, Event, Consent, AuditLog
)


class TestWhatsAppBusinessAPI:
    """Test WhatsApp Business Cloud API client."""
    
    @pytest.fixture
    def api_client(self):
        """Create API client for testing."""
        with patch('app.services.whatsapp.settings') as mock_settings:
            mock_settings.WHATSAPP_ACCESS_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "123456789"
            mock_settings.WHATSAPP_VERIFY_TOKEN = "verify_token"
            return WhatsAppBusinessAPI()
    
    @pytest.mark.asyncio
    async def test_send_text_message(self, api_client):
        """Test sending a text message."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messages": [{"id": "msg_123"}]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await api_client.send_text_message("+1234567890", "Hello World")
            
            assert result["messages"][0]["id"] == "msg_123"
    
    @pytest.mark.asyncio
    async def test_send_template_message(self, api_client):
        """Test sending a template message."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messages": [{"id": "template_msg_123"}]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await api_client.send_template_message(
                "+1234567890", 
                "confirmation_request",
                parameters=[{"type": "text", "text": "Test action"}]
            )
            
            assert result["messages"][0]["id"] == "template_msg_123"
    
    @pytest.mark.asyncio
    async def test_send_interactive_message(self, api_client):
        """Test sending an interactive message with buttons."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messages": [{"id": "interactive_msg_123"}]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            buttons = [
                {"id": "yes", "title": "Yes"},
                {"id": "no", "title": "No"}
            ]
            
            result = await api_client.send_interactive_message(
                "+1234567890", 
                "Please confirm this action",
                buttons
            )
            
            assert result["messages"][0]["id"] == "interactive_msg_123"


class TestMessageTemplateManager:
    """Test message template management."""
    
    @pytest.fixture
    def template_manager(self):
        """Create template manager for testing."""
        return MessageTemplateManager()
    
    def test_get_template(self, template_manager):
        """Test getting a template by name."""
        template = template_manager.get_template("confirmation_request")
        
        assert template is not None
        assert template["name"] == "confirmation_request"
        assert "{{1}}" in template["body"]
    
    def test_format_confirmation_message(self, template_manager):
        """Test formatting confirmation message."""
        message = template_manager.format_confirmation_message("Create calendar event")
        
        assert "Create calendar event" in message
        assert "Y - Yes" in message
        assert "N - No" in message
        assert "C - Cancel" in message
    
    def test_format_daily_summary(self, template_manager):
        """Test formatting daily summary message."""
        insights = ["Great productivity today!", "Consider scheduling buffer time"]
        preview = ["9:00 AM - Team meeting", "2:00 PM - Client call"]
        
        message = template_manager.format_daily_summary(
            "January 15, 2024",
            5,  # tasks completed
            3,  # events attended
            insights,
            preview
        )
        
        assert "January 15, 2024" in message
        assert "Tasks completed: 5" in message
        assert "Events attended: 3" in message
        assert "Great productivity today!" in message
        assert "9:00 AM - Team meeting" in message


class TestWhatsAppService:
    """Test WhatsApp service functionality."""
    
    @pytest.fixture
    def whatsapp_service(self):
        """Create WhatsApp service for testing."""
        with patch('app.services.whatsapp.WhatsAppBusinessAPI'):
            return WhatsAppService()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        user = User(
            id="user_123",
            email="test@example.com",
            password_hash="hashed",
            timezone="UTC"
        )
        return user
    
    @pytest.fixture
    def sample_thread(self, sample_user):
        """Create sample WhatsApp thread."""
        thread = WhatsAppThread(
            id="thread_123",
            user_id=sample_user.id,
            phone_number="+1234567890",
            thread_status="active"
        )
        return thread
    
    @pytest.mark.asyncio
    async def test_get_or_create_thread_existing(self, whatsapp_service, mock_db, sample_user, sample_thread):
        """Test getting existing thread."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_thread
        
        result = await whatsapp_service.get_or_create_thread(
            mock_db, sample_user.id, "+1234567890"
        )
        
        assert result == sample_thread
        mock_db.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_or_create_thread_new(self, whatsapp_service, mock_db, sample_user):
        """Test creating new thread."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await whatsapp_service.get_or_create_thread(
            mock_db, sample_user.id, "+1234567890"
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_message(self, whatsapp_service, mock_db, sample_user, sample_thread):
        """Test sending a WhatsApp message."""
        # Mock thread creation
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_thread
        
        # Mock API response
        whatsapp_service.api.send_text_message = AsyncMock(
            return_value={"messages": [{"id": "msg_123"}]}
        )
        
        message_data = WhatsAppMessageCreate(
            recipient="+1234567890",
            content="Test message",
            message_type=MessageType.TEXT
        )
        
        result = await whatsapp_service.send_message(mock_db, sample_user.id, message_data)
        
        assert result.content == "Test message"
        assert result.direction == MessageDirection.OUTBOUND
        assert result.message_type == MessageType.TEXT
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_incoming_message(self, whatsapp_service, mock_db, sample_user, sample_thread):
        """Test processing incoming WhatsApp message."""
        # Mock user lookup
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_user,  # User lookup
            sample_thread,  # Thread lookup
            None  # Duplicate message check
        ]
        
        result = await whatsapp_service.process_incoming_message(
            mock_db, "+1234567890", "msg_456", "Hello AI", "text"
        )
        
        assert result.content == "Hello AI"
        assert result.direction == MessageDirection.INBOUND
        assert result.status == MessageStatus.DELIVERED
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_user_opt_in_true(self, whatsapp_service, mock_db):
        """Test checking user opt-in status - opted in."""
        mock_settings = UserSettings(user_id="user_123", whatsapp_opt_in=True)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_settings
        
        result = await whatsapp_service.check_user_opt_in(mock_db, "user_123")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_user_opt_in_false(self, whatsapp_service, mock_db):
        """Test checking user opt-in status - not opted in."""
        mock_settings = UserSettings(user_id="user_123", whatsapp_opt_in=False)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_settings
        
        result = await whatsapp_service.check_user_opt_in(mock_db, "user_123")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_opt_in_request_success(self, whatsapp_service, mock_db, sample_user, sample_thread):
        """Test successful opt-in request."""
        # Mock user lookup
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_user,  # User lookup
            None,  # Settings lookup (doesn't exist)
            sample_thread  # Thread lookup for welcome message
        ]
        
        # Mock message sending
        whatsapp_service.send_message = AsyncMock()
        
        opt_in_request = OptInRequest(
            phone_number="+1234567890",
            consent_text="I agree to receive WhatsApp notifications"
        )
        
        result = await whatsapp_service.handle_opt_in_request(mock_db, opt_in_request)
        
        assert result.success is True
        assert "Successfully opted in" in result.message
        mock_db.add.assert_called()  # Consent and settings added
        mock_db.commit.assert_called()
        whatsapp_service.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_confirmation_request(self, whatsapp_service, mock_db, sample_user, sample_thread):
        """Test sending confirmation request."""
        # Mock thread lookup
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_thread
        
        # Mock send_message
        whatsapp_service.send_message = AsyncMock(
            return_value=MagicMock(id="msg_123")
        )
        
        confirmation = ConfirmationMessage(
            action_type="create_event",
            action_description="Create meeting with John at 3 PM"
        )
        
        result = await whatsapp_service.send_confirmation_request(
            mock_db, sample_user.id, confirmation
        )
        
        whatsapp_service.send_message.assert_called_once()
        call_args = whatsapp_service.send_message.call_args[0]
        message_data = call_args[2]  # Third argument is message_data
        assert "Create meeting with John at 3 PM" in message_data.content


class TestWorkflowManager:
    """Test workflow management functionality."""
    
    @pytest.fixture
    def workflow_manager(self):
        """Create workflow manager for testing."""
        return WorkflowManager()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_execute_with_confirmation_immediate(self, workflow_manager, mock_db):
        """Test executing action without confirmation."""
        with patch.object(workflow_manager, '_execute_action') as mock_execute:
            mock_execute.return_value = {"status": "success", "message": "Action completed"}
            
            result = await workflow_manager.execute_with_confirmation(
                mock_db,
                "user_123",
                "create_task",
                "Create a new task",
                {"title": "Test task"},
                require_confirmation=False
            )
            
            assert result["status"] == "success"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_confirmation_pending(self, workflow_manager, mock_db):
        """Test executing action with confirmation required."""
        with patch('app.services.whatsapp.whatsapp_service') as mock_whatsapp:
            mock_whatsapp.check_user_opt_in.return_value = True
            
            with patch('app.tasks.whatsapp_tasks.confirmation_workflow') as mock_workflow:
                mock_workflow.request_confirmation.return_value = "conf_123"
                
                result = await workflow_manager.execute_with_confirmation(
                    mock_db,
                    "user_123",
                    "create_task",
                    "Create a new task",
                    {"title": "Test task"},
                    require_confirmation=True
                )
                
                assert result["status"] == "pending_confirmation"
                assert result["confirmation_id"] == "conf_123"
                assert "conf_123" in workflow_manager.pending_confirmations
    
    @pytest.mark.asyncio
    async def test_handle_confirmation_response_confirmed(self, workflow_manager, mock_db):
        """Test handling confirmed response."""
        # Set up pending confirmation
        workflow_manager.pending_confirmations["conf_123"] = {
            "user_id": "user_123",
            "action_type": "create_task",
            "action_params": {"title": "Test task"},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        
        with patch('app.tasks.whatsapp_tasks.confirmation_workflow') as mock_workflow:
            mock_workflow.process_confirmation_response.return_value = {"action": "confirmed"}
            
            with patch.object(workflow_manager, '_execute_action') as mock_execute:
                mock_execute.return_value = {"status": "success"}
                
                result = await workflow_manager.handle_confirmation_response(
                    mock_db, "conf_123", "Y"
                )
                
                assert result["status"] == "confirmed_and_executed"
                assert "conf_123" not in workflow_manager.pending_confirmations
    
    @pytest.mark.asyncio
    async def test_handle_confirmation_response_denied(self, workflow_manager, mock_db):
        """Test handling denied response."""
        # Set up pending confirmation
        workflow_manager.pending_confirmations["conf_123"] = {
            "user_id": "user_123",
            "action_type": "create_task",
            "action_params": {"title": "Test task"},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        
        with patch('app.tasks.whatsapp_tasks.confirmation_workflow') as mock_workflow:
            mock_workflow.process_confirmation_response.return_value = {"action": "denied"}
            
            result = await workflow_manager.handle_confirmation_response(
                mock_db, "conf_123", "N"
            )
            
            assert result["status"] == "cancelled"
            assert "conf_123" not in workflow_manager.pending_confirmations
    
    @pytest.mark.asyncio
    async def test_execute_create_task_action(self, workflow_manager, mock_db):
        """Test executing create task action."""
        params = {
            "title": "Test Task",
            "description": "Test description",
            "priority": 2,
            "due_date": "2024-01-15T10:00:00"
        }
        
        result = await workflow_manager._execute_action(
            mock_db, "user_123", "create_task", params
        )
        
        assert result["status"] == "success"
        assert "Task 'Test Task' created successfully" in result["message"]
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_create_calendar_event_action(self, workflow_manager, mock_db):
        """Test executing create calendar event action."""
        params = {
            "title": "Test Meeting",
            "description": "Test meeting description",
            "start_time": "2024-01-15T10:00:00",
            "end_time": "2024-01-15T11:00:00",
            "location": "Conference Room A"
        }
        
        result = await workflow_manager._execute_action(
            mock_db, "user_123", "create_calendar_event", params
        )
        
        assert result["status"] == "success"
        assert "Calendar event 'Test Meeting' created successfully" in result["message"]
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    def test_get_pending_confirmations(self, workflow_manager):
        """Test getting pending confirmations for user."""
        # Add some pending confirmations
        workflow_manager.pending_confirmations["conf_1"] = {
            "user_id": "user_123",
            "action_type": "create_task",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        workflow_manager.pending_confirmations["conf_2"] = {
            "user_id": "user_456",
            "action_type": "create_event",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        
        pending = workflow_manager.get_pending_confirmations("user_123")
        
        assert len(pending) == 1
        assert pending[0]["confirmation_id"] == "conf_1"
        assert pending[0]["action_type"] == "create_task"
    
    def test_cleanup_expired_confirmations(self, workflow_manager):
        """Test cleaning up expired confirmations."""
        # Add expired and valid confirmations
        workflow_manager.pending_confirmations["expired"] = {
            "user_id": "user_123",
            "action_type": "create_task",
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "expires_at": datetime.utcnow() - timedelta(hours=1)
        }
        workflow_manager.pending_confirmations["valid"] = {
            "user_id": "user_123",
            "action_type": "create_event",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        
        workflow_manager.cleanup_expired_confirmations()
        
        assert "expired" not in workflow_manager.pending_confirmations
        assert "valid" in workflow_manager.pending_confirmations


class TestWhatsAppSchemas:
    """Test WhatsApp Pydantic schemas."""
    
    def test_whatsapp_message_create_valid(self):
        """Test valid WhatsApp message creation."""
        message = WhatsAppMessageCreate(
            recipient="+1234567890",
            content="Hello World",
            message_type=MessageType.TEXT
        )
        
        assert message.recipient == "+1234567890"
        assert message.content == "Hello World"
        assert message.message_type == MessageType.TEXT
    
    def test_whatsapp_message_create_invalid_phone(self):
        """Test invalid phone number validation."""
        with pytest.raises(ValueError, match="Phone number must be in international format"):
            WhatsAppMessageCreate(
                recipient="1234567890",  # Missing +
                content="Hello World"
            )
    
    def test_user_response_valid(self):
        """Test valid user response."""
        response = UserResponse(
            response="Y",
            message_id="msg_123",
            context_data={"action": "create_task"}
        )
        
        assert response.response == "Y"
        assert response.message_id == "msg_123"
    
    def test_user_response_invalid(self):
        """Test invalid user response."""
        with pytest.raises(ValueError, match="Response must be one of"):
            UserResponse(
                response="INVALID",
                message_id="msg_123"
            )
    
    def test_opt_in_request_valid(self):
        """Test valid opt-in request."""
        opt_in = OptInRequest(
            phone_number="+1234567890",
            consent_text="I agree to receive notifications"
        )
        
        assert opt_in.phone_number == "+1234567890"
        assert opt_in.consent_text == "I agree to receive notifications"
    
    def test_daily_summary_creation(self):
        """Test daily summary creation."""
        summary = DailySummary(
            user_id="user_123",
            summary_date=datetime.now(),
            tasks_completed=5,
            events_attended=3,
            ai_suggestions=["Take a break", "Schedule buffer time"],
            insights=["Great productivity today!"],
            next_day_preview=["9:00 AM - Team meeting"]
        )
        
        assert summary.user_id == "user_123"
        assert summary.tasks_completed == 5
        assert summary.events_attended == 3
        assert len(summary.insights) == 1
        assert len(summary.next_day_preview) == 1