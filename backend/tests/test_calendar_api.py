"""
Unit tests for Calendar API endpoints.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api.v1.calendar import router as calendar_router
from app.database.models import User, Calendar, Event
from app.schemas.calendar import CalendarConnection, CalendarSyncResult


@pytest.fixture
def app():
    """Create FastAPI test app."""
    app = FastAPI()
    app.include_router(calendar_router, prefix="/calendar")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_current_user(sample_user):
    """Mock current user dependency."""
    with patch('app.api.v1.calendar.get_current_user', return_value=sample_user):
        yield sample_user


@pytest.fixture
def mock_db_session(db_session):
    """Mock database session dependency."""
    with patch('app.api.v1.calendar.get_db', return_value=db_session):
        yield db_session


class TestCalendarAPI:
    """Test cases for Calendar API endpoints."""
    
    def test_initiate_calendar_connection(self, client, mock_current_user, mock_db_session):
        """Test initiating OAuth connection."""
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_service.get_authorization_url.return_value = "https://auth.google.com/oauth"
            
            response = client.post(
                "/calendar/connect",
                json={"redirect_uri": "http://localhost:8000/callback"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert data["authorization_url"] == "https://auth.google.com/oauth"
    
    def test_oauth_callback_success(self, client, mock_current_user, mock_db_session):
        """Test successful OAuth callback processing."""
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_connection = CalendarConnection(
                id="calendar_123",
                user_id=str(mock_current_user.id),
                google_calendar_id="primary",
                connected=True,
                last_sync_at=datetime.utcnow()
            )
            mock_service.exchange_code_for_tokens = AsyncMock(return_value=mock_connection)
            
            response = client.post(
                "/calendar/oauth/callback",
                json={"code": "auth_code_123", "state": "csrf_state"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "calendar_123"
            assert data["connected"] is True
    
    def test_get_calendar_connection_exists(self, client, mock_current_user, mock_db_session):
        """Test getting existing calendar connection."""
        # Create calendar connection in database
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token",
            last_sync_at=datetime.utcnow()
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        response = client.get("/calendar/connection")
        
        assert response.status_code == 200
        data = response.json()
        assert data["google_calendar_id"] == "primary"
        assert data["connected"] is True
    
    def test_get_calendar_connection_not_exists(self, client, mock_current_user, mock_db_session):
        """Test getting calendar connection when none exists."""
        response = client.get("/calendar/connection")
        
        assert response.status_code == 200
        assert response.json() is None
    
    def test_disconnect_calendar(self, client, mock_current_user, mock_db_session):
        """Test disconnecting calendar."""
        # Create calendar connection
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        response = client.delete("/calendar/connection")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Calendar disconnected successfully"
        
        # Verify calendar was deleted
        deleted_calendar = mock_db_session.query(Calendar).filter(
            Calendar.user_id == mock_current_user.id
        ).first()
        assert deleted_calendar is None
    
    def test_sync_calendar(self, client, mock_current_user, mock_db_session):
        """Test manual calendar sync."""
        # Create calendar connection
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token",
            sync_token="sync_123"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_sync_result = CalendarSyncResult(
                events_synced=5,
                events_created=2,
                events_updated=2,
                events_deleted=1,
                sync_token="new_sync_123"
            )
            mock_service.sync_events = AsyncMock(return_value=mock_sync_result)
            
            response = client.post("/calendar/sync")
            
            assert response.status_code == 200
            data = response.json()
            assert data["events_synced"] == 5
            assert data["events_created"] == 2
            assert data["events_updated"] == 2
            assert data["events_deleted"] == 1
    
    def test_get_calendar_events(self, client, mock_current_user, mock_db_session):
        """Test getting calendar events."""
        # Create sample events
        events = [
            Event(
                user_id=mock_current_user.id,
                title="Meeting 1",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=1),
                ai_generated=False
            ),
            Event(
                user_id=mock_current_user.id,
                title="Meeting 2",
                start_time=datetime.utcnow() + timedelta(hours=2),
                end_time=datetime.utcnow() + timedelta(hours=3),
                ai_generated=True
            )
        ]
        
        for event in events:
            mock_db_session.add(event)
        mock_db_session.commit()
        
        response = client.get("/calendar/events")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Meeting 1"
        assert data[1]["title"] == "Meeting 2"
    
    def test_create_calendar_event(self, client, mock_current_user, mock_db_session):
        """Test creating a calendar event."""
        # Create calendar connection
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_service.create_google_event = AsyncMock(return_value="google_event_123")
            
            event_data = {
                "title": "New Meeting",
                "description": "Meeting description",
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T11:00:00Z",
                "location": "Conference Room",
                "attendees": ["attendee@example.com"]
            }
            
            response = client.post("/calendar/events", json=event_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "New Meeting"
            assert data["google_event_id"] == "google_event_123"
            assert data["ai_generated"] is True
    
    def test_get_calendar_event(self, client, mock_current_user, mock_db_session):
        """Test getting a specific calendar event."""
        # Create event
        event = Event(
            user_id=mock_current_user.id,
            title="Test Event",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            description="Test description"
        )
        mock_db_session.add(event)
        mock_db_session.commit()
        mock_db_session.refresh(event)
        
        response = client.get(f"/calendar/events/{event.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Event"
        assert data["description"] == "Test description"
    
    def test_update_calendar_event(self, client, mock_current_user, mock_db_session):
        """Test updating a calendar event."""
        # Create event
        event = Event(
            user_id=mock_current_user.id,
            title="Original Title",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            google_event_id="google_123"
        )
        mock_db_session.add(event)
        mock_db_session.commit()
        mock_db_session.refresh(event)
        
        # Create calendar connection
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_service.update_google_event = AsyncMock()
            
            update_data = {
                "title": "Updated Title",
                "description": "Updated description"
            }
            
            response = client.put(f"/calendar/events/{event.id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated Title"
            assert data["description"] == "Updated description"
    
    def test_delete_calendar_event(self, client, mock_current_user, mock_db_session):
        """Test deleting a calendar event."""
        # Create event
        event = Event(
            user_id=mock_current_user.id,
            title="Event to Delete",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            google_event_id="google_123"
        )
        mock_db_session.add(event)
        mock_db_session.commit()
        mock_db_session.refresh(event)
        
        # Create calendar connection
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_service.delete_google_event = AsyncMock()
            
            response = client.delete(f"/calendar/events/{event.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Event deleted successfully"
            
            # Verify event was deleted
            deleted_event = mock_db_session.query(Event).filter(
                Event.id == event.id
            ).first()
            assert deleted_event is None
    
    def test_get_scheduling_suggestions(self, client, mock_current_user, mock_db_session):
        """Test getting scheduling suggestions."""
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            from app.schemas.calendar import SchedulingSuggestion, TimeSlot
            
            mock_suggestions = SchedulingSuggestion(
                suggested_slots=[
                    TimeSlot(
                        start_time=datetime.utcnow().replace(hour=10),
                        end_time=datetime.utcnow().replace(hour=11),
                        confidence_score=0.9,
                        reason="Available morning slot"
                    ),
                    TimeSlot(
                        start_time=datetime.utcnow().replace(hour=14),
                        end_time=datetime.utcnow().replace(hour=15),
                        confidence_score=0.8,
                        reason="Available afternoon slot"
                    )
                ],
                preferences_applied={"work_hours": "9AM-6PM"},
                conflicts_avoided=["Existing Meeting"]
            )
            mock_service.suggest_optimal_scheduling = AsyncMock(return_value=mock_suggestions)
            
            response = client.get("/calendar/suggestions?duration_minutes=60")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["suggested_slots"]) == 2
            assert data["suggested_slots"][0]["confidence_score"] == 0.9
            assert data["preferences_applied"]["work_hours"] == "9AM-6PM"
    
    def test_handle_calendar_webhook(self, client, mock_db_session):
        """Test handling calendar webhook notifications."""
        # Create calendar with webhook ID
        user = User(email="webhook@example.com", password_hash="hash")
        mock_db_session.add(user)
        mock_db_session.commit()
        
        calendar = Calendar(
            user_id=user.id,
            google_calendar_id="primary",
            webhook_id="webhook_123",
            access_token_encrypted="encrypted_token"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        webhook_data = {
            "channel_id": "webhook_123",
            "resource_state": "exists",
            "resource_id": "resource_456",
            "resource_uri": "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        }
        
        with patch('app.api.v1.calendar.BackgroundTasks') as mock_bg_tasks:
            response = client.post("/calendar/webhook", json=webhook_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["sync_triggered"] is True
    
    def test_setup_calendar_watch(self, client, mock_current_user, mock_db_session):
        """Test setting up calendar watch."""
        # Create calendar connection
        calendar = Calendar(
            user_id=mock_current_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_token"
        )
        mock_db_session.add(calendar)
        mock_db_session.commit()
        
        with patch('app.api.v1.calendar.calendar_service') as mock_service:
            mock_service.setup_webhook = AsyncMock(return_value={
                'channel_id': 'channel_123',
                'resource_id': 'resource_456'
            })
            
            watch_data = {
                "calendar_id": "primary",
                "webhook_url": "https://example.com/webhook"
            }
            
            response = client.post("/calendar/watch", json=watch_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["channel_id"] == "channel_123"
            assert data["resource_id"] == "resource_456"
    
    def test_error_handling_no_calendar_connection(self, client, mock_current_user, mock_db_session):
        """Test error handling when no calendar connection exists."""
        # Test sync without connection
        response = client.post("/calendar/sync")
        assert response.status_code == 404
        assert "No calendar connection found" in response.json()["detail"]
        
        # Test disconnect without connection
        response = client.delete("/calendar/connection")
        assert response.status_code == 404
        assert "No calendar connection found" in response.json()["detail"]
    
    def test_error_handling_event_not_found(self, client, mock_current_user, mock_db_session):
        """Test error handling when event is not found."""
        # Test get non-existent event
        response = client.get("/calendar/events/non-existent-id")
        assert response.status_code == 404
        assert "Event not found" in response.json()["detail"]
        
        # Test update non-existent event
        response = client.put("/calendar/events/non-existent-id", json={"title": "New Title"})
        assert response.status_code == 404
        assert "Event not found" in response.json()["detail"]
        
        # Test delete non-existent event
        response = client.delete("/calendar/events/non-existent-id")
        assert response.status_code == 404
        assert "Event not found" in response.json()["detail"]