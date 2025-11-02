"""
Unit tests for Google Calendar integration.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database.models import User, Calendar, Event
from app.services.calendar import GoogleCalendarService
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate, SchedulingSuggestion


class TestGoogleCalendarService:
    """Test cases for GoogleCalendarService."""
    
    @pytest.fixture
    def calendar_service(self):
        """Create a calendar service instance for testing."""
        with patch('app.services.calendar.settings') as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"
            return GoogleCalendarService()
    
    @pytest.fixture
    def sample_calendar(self, db_session, sample_user):
        """Create a sample calendar connection."""
        calendar = Calendar(
            user_id=sample_user.id,
            google_calendar_id="primary",
            access_token_encrypted="encrypted_access_token",
            refresh_token_encrypted="encrypted_refresh_token",
            sync_token="sync_token_123",
            last_sync_at=datetime.utcnow()
        )
        db_session.add(calendar)
        db_session.commit()
        db_session.refresh(calendar)
        return calendar
    
    def test_get_authorization_url(self, calendar_service):
        """Test OAuth authorization URL generation."""
        with patch('app.services.calendar.Flow') as mock_flow_class:
            mock_flow = Mock()
            mock_flow.authorization_url.return_value = ("https://auth.url", "state")
            mock_flow_class.from_client_config.return_value = mock_flow
            
            redirect_uri = "http://localhost:8000/callback"
            auth_url = calendar_service.get_authorization_url(redirect_uri)
            
            assert auth_url == "https://auth.url"
            mock_flow.authorization_url.assert_called_once_with(
                access_type='offline',
                include_granted_scopes='true',
                state=pytest.any(str),
                prompt='consent'
            )
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self, calendar_service, db_session, sample_user):
        """Test OAuth code exchange for tokens."""
        with patch('app.services.calendar.Flow') as mock_flow_class, \
             patch('app.services.calendar.build') as mock_build:
            
            # Mock OAuth flow
            mock_flow = Mock()
            mock_credentials = Mock()
            mock_credentials.token = "access_token"
            mock_credentials.refresh_token = "refresh_token"
            mock_flow.credentials = mock_credentials
            mock_flow_class.from_client_config.return_value = mock_flow
            
            # Mock Google Calendar API
            mock_service = Mock()
            mock_calendar_list = Mock()
            mock_calendar_list.list.return_value.execute.return_value = {
                'items': [{'id': 'primary', 'primary': True}]
            }
            mock_service.calendarList.return_value = mock_calendar_list
            mock_build.return_value = mock_service
            
            # Test code exchange
            result = await calendar_service.exchange_code_for_tokens(
                code="auth_code",
                redirect_uri="http://localhost:8000/callback",
                db=db_session,
                user_id=str(sample_user.id)
            )
            
            assert result.user_id == str(sample_user.id)
            assert result.google_calendar_id == "primary"
            assert result.connected is True
            
            # Verify calendar was saved to database
            calendar = db_session.query(Calendar).filter(
                Calendar.user_id == sample_user.id
            ).first()
            assert calendar is not None
            assert calendar.google_calendar_id == "primary"
    
    @pytest.mark.asyncio
    async def test_sync_events_initial_sync(self, calendar_service, db_session, sample_calendar):
        """Test initial calendar events synchronization."""
        with patch('app.services.calendar.build') as mock_build:
            # Mock Google Calendar API response
            mock_service = Mock()
            mock_events = Mock()
            mock_events.list.return_value.execute.return_value = {
                'items': [
                    {
                        'id': 'event_1',
                        'summary': 'Test Event 1',
                        'description': 'Test Description',
                        'start': {'dateTime': '2024-01-15T10:00:00Z'},
                        'end': {'dateTime': '2024-01-15T11:00:00Z'},
                        'location': 'Test Location',
                        'attendees': [{'email': 'test@example.com'}]
                    },
                    {
                        'id': 'event_2',
                        'summary': 'Test Event 2',
                        'start': {'dateTime': '2024-01-16T14:00:00Z'},
                        'end': {'dateTime': '2024-01-16T15:00:00Z'},
                    }
                ],
                'nextSyncToken': 'new_sync_token'
            }
            mock_service.events.return_value = mock_events
            mock_build.return_value = mock_service
            
            # Mock credentials and refresh
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                # Perform sync
                result = await calendar_service.sync_events(
                    calendar_conn=sample_calendar,
                    db=db_session,
                    sync_token=None
                )
                
                assert result.events_synced == 2
                assert result.events_created == 2
                assert result.events_updated == 0
                assert result.events_deleted == 0
                assert result.sync_token == 'new_sync_token'
                
                # Verify events were created in database
                events = db_session.query(Event).filter(
                    Event.user_id == sample_calendar.user_id
                ).all()
                assert len(events) == 2
                assert events[0].title == 'Test Event 1'
                assert events[1].title == 'Test Event 2'
    
    @pytest.mark.asyncio
    async def test_sync_events_with_deletions(self, calendar_service, db_session, sample_calendar):
        """Test sync handling deleted events."""
        # Create existing event in database
        existing_event = Event(
            user_id=sample_calendar.user_id,
            calendar_id=sample_calendar.id,
            google_event_id='event_to_delete',
            title='Event to Delete',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(existing_event)
        db_session.commit()
        
        with patch('app.services.calendar.build') as mock_build:
            # Mock Google Calendar API response with cancelled event
            mock_service = Mock()
            mock_events = Mock()
            mock_events.list.return_value.execute.return_value = {
                'items': [
                    {
                        'id': 'event_to_delete',
                        'status': 'cancelled'
                    }
                ],
                'nextSyncToken': 'new_sync_token'
            }
            mock_service.events.return_value = mock_events
            mock_build.return_value = mock_service
            
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                # Perform sync
                result = await calendar_service.sync_events(
                    calendar_conn=sample_calendar,
                    db=db_session,
                    sync_token='old_sync_token'
                )
                
                assert result.events_deleted == 1
                
                # Verify event was deleted from database
                deleted_event = db_session.query(Event).filter(
                    Event.google_event_id == 'event_to_delete'
                ).first()
                assert deleted_event is None
    
    @pytest.mark.asyncio
    async def test_conflict_resolution(self, calendar_service, db_session, sample_calendar):
        """Test conflict resolution between local and Google events."""
        # Create local event
        local_event = Event(
            user_id=sample_calendar.user_id,
            calendar_id=sample_calendar.id,
            google_event_id='conflict_event',
            title='Local Title',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            updated_at=datetime.utcnow() - timedelta(minutes=30)
        )
        db_session.add(local_event)
        db_session.commit()
        
        # Google event data (newer)
        google_event = {
            'id': 'conflict_event',
            'summary': 'Google Title',
            'updated': (datetime.utcnow() - timedelta(minutes=10)).isoformat() + 'Z',
            'start': {'dateTime': datetime.utcnow().isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'}
        }
        
        # Test conflict resolution
        resolved_event = await calendar_service.handle_conflict_resolution(
            local_event=local_event,
            google_event=google_event,
            db=db_session
        )
        
        # Google event should win (it's newer)
        assert resolved_event.title == 'Google Title'
    
    @pytest.mark.asyncio
    async def test_create_google_event(self, calendar_service, db_session, sample_calendar):
        """Test creating an event in Google Calendar."""
        with patch('app.services.calendar.build') as mock_build:
            mock_service = Mock()
            mock_events = Mock()
            mock_events.insert.return_value.execute.return_value = {'id': 'new_event_id'}
            mock_service.events.return_value = mock_events
            mock_build.return_value = mock_service
            
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                event_data = CalendarEventCreate(
                    title="New Event",
                    description="Event Description",
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow() + timedelta(hours=1),
                    location="Test Location",
                    attendees=["test@example.com"]
                )
                
                google_event_id = await calendar_service.create_google_event(
                    calendar_conn=sample_calendar,
                    event_data=event_data,
                    db=db_session
                )
                
                assert google_event_id == 'new_event_id'
                mock_events.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_google_event(self, calendar_service, db_session, sample_calendar):
        """Test updating an event in Google Calendar."""
        with patch('app.services.calendar.build') as mock_build:
            mock_service = Mock()
            mock_events = Mock()
            
            # Mock get existing event
            mock_events.get.return_value.execute.return_value = {
                'id': 'existing_event',
                'summary': 'Old Title',
                'start': {'dateTime': '2024-01-15T10:00:00Z'},
                'end': {'dateTime': '2024-01-15T11:00:00Z'}
            }
            
            # Mock update
            mock_events.update.return_value.execute.return_value = {'id': 'existing_event'}
            mock_service.events.return_value = mock_events
            mock_build.return_value = mock_service
            
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                event_data = CalendarEventUpdate(
                    title="Updated Title",
                    description="Updated Description"
                )
                
                await calendar_service.update_google_event(
                    calendar_conn=sample_calendar,
                    google_event_id='existing_event',
                    event_data=event_data,
                    db=db_session
                )
                
                mock_events.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_google_event(self, calendar_service, db_session, sample_calendar):
        """Test deleting an event from Google Calendar."""
        with patch('app.services.calendar.build') as mock_build:
            mock_service = Mock()
            mock_events = Mock()
            mock_service.events.return_value = mock_events
            mock_build.return_value = mock_service
            
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                await calendar_service.delete_google_event(
                    calendar_conn=sample_calendar,
                    google_event_id='event_to_delete',
                    db=db_session
                )
                
                mock_events.delete.assert_called_once_with(
                    calendarId=sample_calendar.google_calendar_id,
                    eventId='event_to_delete'
                )
    
    @pytest.mark.asyncio
    async def test_suggest_optimal_scheduling(self, calendar_service, db_session, sample_user):
        """Test intelligent scheduling suggestions."""
        # Create some existing events
        existing_events = [
            Event(
                user_id=sample_user.id,
                title='Existing Meeting',
                start_time=datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0),
                end_time=datetime.utcnow().replace(hour=11, minute=0, second=0, microsecond=0)
            ),
            Event(
                user_id=sample_user.id,
                title='Another Meeting',
                start_time=datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0),
                end_time=datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0)
            )
        ]
        
        for event in existing_events:
            db_session.add(event)
        db_session.commit()
        
        # Test scheduling suggestions
        suggestions = await calendar_service.suggest_optimal_scheduling(
            user_id=str(sample_user.id),
            duration_minutes=60,
            db=db_session
        )
        
        assert isinstance(suggestions, SchedulingSuggestion)
        assert len(suggestions.suggested_slots) > 0
        
        # Verify no conflicts with existing events
        for slot in suggestions.suggested_slots:
            for existing_event in existing_events:
                # Check that suggested slot doesn't overlap with existing events
                assert not (slot.start_time < existing_event.end_time and 
                           slot.end_time > existing_event.start_time)
    
    @pytest.mark.asyncio
    async def test_setup_webhook(self, calendar_service, db_session, sample_calendar):
        """Test setting up Google Calendar webhook."""
        with patch('app.services.calendar.build') as mock_build:
            mock_service = Mock()
            mock_events = Mock()
            mock_events.watch.return_value.execute.return_value = {
                'resourceId': 'resource_123',
                'expiration': '1640995200000'  # Unix timestamp in milliseconds
            }
            mock_service.events.return_value = mock_events
            mock_build.return_value = mock_service
            
            with patch.object(calendar_service, '_get_credentials'), \
                 patch.object(calendar_service, 'refresh_tokens_if_needed'):
                
                webhook_result = await calendar_service.setup_webhook(
                    calendar_conn=sample_calendar,
                    webhook_url='https://example.com/webhook',
                    db=db_session
                )
                
                assert 'channel_id' in webhook_result
                assert webhook_result['resource_id'] == 'resource_123'
                
                # Verify webhook ID was stored
                db_session.refresh(sample_calendar)
                assert sample_calendar.webhook_id is not None
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_if_needed(self, calendar_service, db_session, sample_calendar):
        """Test token refresh functionality."""
        with patch('app.services.calendar.Credentials') as mock_credentials_class, \
             patch('app.services.calendar.Request') as mock_request:
            
            # Mock expired credentials
            mock_credentials = Mock()
            mock_credentials.expired = True
            mock_credentials.refresh_token = 'refresh_token'
            mock_credentials.token = 'new_access_token'
            mock_credentials_class.return_value = mock_credentials
            
            with patch.object(calendar_service, '_get_credentials', return_value=mock_credentials), \
                 patch.object(calendar_service, '_encrypt_token', return_value='encrypted_new_token'):
                
                refreshed = await calendar_service.refresh_tokens_if_needed(
                    calendar_conn=sample_calendar,
                    db=db_session
                )
                
                assert refreshed is True
                mock_credentials.refresh.assert_called_once()
    
    def test_token_encryption_decryption(self, calendar_service):
        """Test token encryption and decryption (simplified implementation)."""
        original_token = "test_access_token"
        
        # Test encryption
        encrypted = calendar_service._encrypt_token(original_token)
        assert encrypted != original_token
        
        # Test decryption
        decrypted = calendar_service._decrypt_token(encrypted)
        assert decrypted == original_token