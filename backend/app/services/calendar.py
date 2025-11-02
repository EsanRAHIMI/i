"""
Google Calendar integration service.
"""
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
import structlog

from ..config import settings
from ..database.models import Calendar, Event, User
from ..schemas.calendar import (
    CalendarConnection, CalendarEvent, CalendarSyncResult,
    TimeSlot, SchedulingSuggestion
)

logger = structlog.get_logger(__name__)


class GoogleCalendarService:
    """Service for Google Calendar integration."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials not configured")
    
    def _get_oauth_flow(self, redirect_uri: str) -> Flow:
        """Create OAuth2 flow for Google Calendar."""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        return flow
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate Google OAuth authorization URL."""
        try:
            flow = self._get_oauth_flow(redirect_uri)
            
            # Generate state for CSRF protection if not provided
            if not state:
                state = str(uuid.uuid4())
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'  # Force consent to get refresh token
            )
            
            logger.info("Generated OAuth authorization URL", state=state)
            return auth_url
            
        except Exception as e:
            logger.error("Failed to generate authorization URL", error=str(e))
            raise
    
    async def exchange_code_for_tokens(
        self, 
        code: str, 
        redirect_uri: str,
        db: Session,
        user_id: str
    ) -> CalendarConnection:
        """Exchange authorization code for access tokens."""
        try:
            flow = self._get_oauth_flow(redirect_uri)
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            # Get user's primary calendar info
            service = build('calendar', 'v3', credentials=credentials)
            calendar_list = service.calendarList().list().execute()
            
            primary_calendar = None
            for calendar_item in calendar_list.get('items', []):
                if calendar_item.get('primary'):
                    primary_calendar = calendar_item
                    break
            
            if not primary_calendar:
                raise ValueError("No primary calendar found")
            
            # Encrypt tokens (simplified - in production use proper encryption)
            access_token_encrypted = self._encrypt_token(credentials.token)
            refresh_token_encrypted = self._encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
            
            # Store calendar connection in database
            calendar_conn = Calendar(
                user_id=user_id,
                google_calendar_id=primary_calendar['id'],
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                last_sync_at=datetime.utcnow()
            )
            
            db.add(calendar_conn)
            db.commit()
            db.refresh(calendar_conn)
            
            logger.info(
                "Calendar connected successfully",
                user_id=user_id,
                calendar_id=calendar_conn.id,
                google_calendar_id=primary_calendar['id']
            )
            
            return CalendarConnection(
                id=str(calendar_conn.id),
                user_id=user_id,
                google_calendar_id=primary_calendar['id'],
                connected=True,
                last_sync_at=calendar_conn.last_sync_at
            )
            
        except Exception as e:
            logger.error("Failed to exchange code for tokens", error=str(e), user_id=user_id)
            raise
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt token for storage (simplified implementation)."""
        # TODO: Implement proper AES-256 encryption
        # For now, just base64 encode (NOT secure for production)
        import base64
        return base64.b64encode(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt token from storage (simplified implementation)."""
        # TODO: Implement proper AES-256 decryption
        # For now, just base64 decode (NOT secure for production)
        import base64
        return base64.b64decode(encrypted_token.encode()).decode()
    
    def _get_credentials(self, calendar_conn: Calendar) -> Credentials:
        """Get Google credentials from stored tokens."""
        access_token = self._decrypt_token(calendar_conn.access_token_encrypted)
        refresh_token = self._decrypt_token(calendar_conn.refresh_token_encrypted) if calendar_conn.refresh_token_encrypted else None
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES
        )
        
        return credentials
    
    async def refresh_tokens_if_needed(self, calendar_conn: Calendar, db: Session) -> bool:
        """Refresh access tokens if needed."""
        try:
            credentials = self._get_credentials(calendar_conn)
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # Update stored tokens
                calendar_conn.access_token_encrypted = self._encrypt_token(credentials.token)
                if credentials.refresh_token:
                    calendar_conn.refresh_token_encrypted = self._encrypt_token(credentials.refresh_token)
                
                db.commit()
                logger.info("Tokens refreshed successfully", calendar_id=calendar_conn.id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to refresh tokens", error=str(e), calendar_id=calendar_conn.id)
            raise
    
    async def setup_webhook(
        self,
        calendar_conn: Calendar,
        webhook_url: str,
        db: Session
    ) -> Dict[str, Any]:
        """Set up Google Calendar push notifications."""
        try:
            credentials = self._get_credentials(calendar_conn)
            await self.refresh_tokens_if_needed(calendar_conn, db)
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Generate unique channel ID
            channel_id = str(uuid.uuid4())
            
            # Set up watch request
            watch_request = {
                'id': channel_id,
                'type': 'web_hook',
                'address': webhook_url,
                'params': {
                    'ttl': '86400'  # 24 hours
                }
            }
            
            # Execute watch request
            watch_response = service.events().watch(
                calendarId=calendar_conn.google_calendar_id,
                body=watch_request
            ).execute()
            
            # Store webhook info
            calendar_conn.webhook_id = channel_id
            db.commit()
            
            logger.info(
                "Calendar webhook set up successfully",
                calendar_id=calendar_conn.id,
                channel_id=channel_id,
                resource_id=watch_response.get('resourceId')
            )
            
            return {
                'channel_id': channel_id,
                'resource_id': watch_response.get('resourceId'),
                'expiration': watch_response.get('expiration')
            }
            
        except Exception as e:
            logger.error("Failed to set up webhook", error=str(e), calendar_id=calendar_conn.id)
            raise
    
    async def handle_conflict_resolution(
        self,
        local_event: Event,
        google_event: Dict[str, Any],
        db: Session
    ) -> Event:
        """Handle conflicts between local and Google Calendar events."""
        try:
            # Simple conflict resolution strategy: Google Calendar wins
            # In a more sophisticated system, you might consider:
            # - Last modified timestamp
            # - User preferences
            # - Event importance/priority
            
            google_updated = google_event.get('updated')
            if google_updated:
                google_updated_dt = datetime.fromisoformat(google_updated.replace('Z', '+00:00'))
                
                # If Google event is newer, update local event
                if not local_event.updated_at or google_updated_dt > local_event.updated_at:
                    logger.info(
                        "Resolving conflict: Google Calendar event is newer",
                        event_id=local_event.id,
                        google_event_id=google_event['id']
                    )
                    
                    # Update local event with Google data
                    await self._update_event_from_google(local_event, google_event)
                    db.commit()
                    
                    return local_event
            
            # If local event is newer or timestamps are equal, keep local version
            logger.info(
                "Resolving conflict: keeping local event",
                event_id=local_event.id,
                google_event_id=google_event['id']
            )
            
            return local_event
            
        except Exception as e:
            logger.error("Failed to resolve conflict", error=str(e))
            raise
    
    async def _update_event_from_google(self, local_event: Event, google_event: Dict[str, Any]):
        """Update local event with data from Google Calendar event."""
        local_event.title = google_event.get('summary', 'Untitled Event')
        local_event.description = google_event.get('description', '')
        local_event.location = google_event.get('location', '')
        
        # Parse start and end times
        start = google_event.get('start', {})
        end = google_event.get('end', {})
        
        if 'dateTime' in start:
            local_event.start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        else:
            local_event.start_time = datetime.fromisoformat(start['date'] + 'T00:00:00+00:00')
        
        if 'dateTime' in end:
            local_event.end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
        else:
            local_event.end_time = datetime.fromisoformat(end['date'] + 'T23:59:59+00:00')
        
        # Extract attendees
        attendees = []
        for attendee in google_event.get('attendees', []):
            if 'email' in attendee:
                attendees.append(attendee['email'])
        local_event.attendees = attendees

    async def sync_events(
        self, 
        calendar_conn: Calendar, 
        db: Session,
        sync_token: Optional[str] = None
    ) -> CalendarSyncResult:
        """Perform incremental sync of calendar events."""
        try:
            credentials = self._get_credentials(calendar_conn)
            await self.refresh_tokens_if_needed(calendar_conn, db)
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Prepare sync request
            sync_params = {
                'calendarId': calendar_conn.google_calendar_id,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if sync_token:
                sync_params['syncToken'] = sync_token
            else:
                # Initial sync - get events from 30 days ago to 90 days ahead
                time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
                time_max = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
                sync_params['timeMin'] = time_min
                sync_params['timeMax'] = time_max
            
            # Execute sync request
            events_result = service.events().list(**sync_params).execute()
            events = events_result.get('items', [])
            new_sync_token = events_result.get('nextSyncToken')
            
            # Process events
            events_created = 0
            events_updated = 0
            events_deleted = 0
            
            for event in events:
                if event.get('status') == 'cancelled':
                    # Handle deleted events
                    existing_event = db.query(Event).filter(
                        Event.google_event_id == event['id'],
                        Event.user_id == calendar_conn.user_id
                    ).first()
                    
                    if existing_event:
                        db.delete(existing_event)
                        events_deleted += 1
                        logger.info(
                            "Event deleted during sync",
                            event_id=existing_event.id,
                            google_event_id=event['id']
                        )
                else:
                    # Check if event already exists for conflict resolution
                    existing_event = db.query(Event).filter(
                        Event.google_event_id == event['id'],
                        Event.user_id == calendar_conn.user_id
                    ).first()
                    
                    if existing_event:
                        # Handle potential conflict
                        await self.handle_conflict_resolution(existing_event, event, db)
                        events_updated += 1
                    else:
                        # Create new event
                        await self._process_event(event, calendar_conn, db)
                        events_created += 1
            
            # Update sync token
            if new_sync_token:
                calendar_conn.sync_token = new_sync_token
            
            calendar_conn.last_sync_at = datetime.utcnow()
            db.commit()
            
            result = CalendarSyncResult(
                events_synced=len(events),
                events_created=events_created,
                events_updated=events_updated,
                events_deleted=events_deleted,
                sync_token=new_sync_token,
                next_sync_at=datetime.utcnow() + timedelta(minutes=15)
            )
            
            logger.info(
                "Calendar sync completed",
                calendar_id=calendar_conn.id,
                events_synced=len(events),
                events_created=events_created,
                events_updated=events_updated,
                events_deleted=events_deleted
            )
            
            return result
            
        except HttpError as e:
            if e.resp.status == 410:  # Sync token invalid
                logger.warning("Sync token invalid, performing full sync", calendar_id=calendar_conn.id)
                return await self.sync_events(calendar_conn, db, sync_token=None)
            else:
                logger.error("Google API error during sync", error=str(e), calendar_id=calendar_conn.id)
                raise
        except Exception as e:
            logger.error("Failed to sync events", error=str(e), calendar_id=calendar_conn.id)
            raise
    
    async def _process_event(self, google_event: Dict[str, Any], calendar_conn: Calendar, db: Session):
        """Process a single Google Calendar event."""
        try:
            # Extract event data
            event_id = google_event['id']
            title = google_event.get('summary', 'Untitled Event')
            description = google_event.get('description', '')
            location = google_event.get('location', '')
            
            # Parse start and end times
            start = google_event.get('start', {})
            end = google_event.get('end', {})
            
            if 'dateTime' in start:
                start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            else:
                # All-day event
                start_time = datetime.fromisoformat(start['date'] + 'T00:00:00+00:00')
            
            if 'dateTime' in end:
                end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            else:
                # All-day event
                end_time = datetime.fromisoformat(end['date'] + 'T23:59:59+00:00')
            
            # Extract attendees
            attendees = []
            for attendee in google_event.get('attendees', []):
                if 'email' in attendee:
                    attendees.append(attendee['email'])
            
            # Check if event already exists
            existing_event = db.query(Event).filter(
                Event.google_event_id == event_id,
                Event.user_id == calendar_conn.user_id
            ).first()
            
            if existing_event:
                # Update existing event
                existing_event.title = title
                existing_event.description = description
                existing_event.start_time = start_time
                existing_event.end_time = end_time
                existing_event.location = location
                existing_event.attendees = attendees
            else:
                # Create new event
                new_event = Event(
                    user_id=calendar_conn.user_id,
                    calendar_id=calendar_conn.id,
                    google_event_id=event_id,
                    title=title,
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    attendees=attendees,
                    ai_generated=False
                )
                db.add(new_event)
            
        except Exception as e:
            logger.error("Failed to process event", error=str(e), event_id=google_event.get('id'))
            raise
    
    async def create_google_event(
        self,
        calendar_conn: Calendar,
        event_data,  # CalendarEventCreate
        db: Session
    ) -> str:
        """Create an event in Google Calendar."""
        try:
            credentials = self._get_credentials(calendar_conn)
            await self.refresh_tokens_if_needed(calendar_conn, db)
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Prepare event data for Google Calendar API
            google_event = {
                'summary': event_data.title,
                'description': event_data.description or '',
                'location': event_data.location or '',
                'start': {
                    'dateTime': event_data.start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': event_data.end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in event_data.attendees],
            }
            
            # Create event in Google Calendar
            created_event = service.events().insert(
                calendarId=calendar_conn.google_calendar_id,
                body=google_event
            ).execute()
            
            logger.info(
                "Event created in Google Calendar",
                calendar_id=calendar_conn.id,
                google_event_id=created_event['id'],
                title=event_data.title
            )
            
            return created_event['id']
            
        except Exception as e:
            logger.error("Failed to create Google Calendar event", error=str(e))
            raise
    
    async def update_google_event(
        self,
        calendar_conn: Calendar,
        google_event_id: str,
        event_data,  # CalendarEventUpdate
        db: Session
    ):
        """Update an event in Google Calendar."""
        try:
            credentials = self._get_credentials(calendar_conn)
            await self.refresh_tokens_if_needed(calendar_conn, db)
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get existing event
            existing_event = service.events().get(
                calendarId=calendar_conn.google_calendar_id,
                eventId=google_event_id
            ).execute()
            
            # Update only provided fields
            if event_data.title is not None:
                existing_event['summary'] = event_data.title
            if event_data.description is not None:
                existing_event['description'] = event_data.description
            if event_data.location is not None:
                existing_event['location'] = event_data.location
            if event_data.start_time is not None:
                existing_event['start'] = {
                    'dateTime': event_data.start_time.isoformat(),
                    'timeZone': 'UTC',
                }
            if event_data.end_time is not None:
                existing_event['end'] = {
                    'dateTime': event_data.end_time.isoformat(),
                    'timeZone': 'UTC',
                }
            if event_data.attendees is not None:
                existing_event['attendees'] = [{'email': email} for email in event_data.attendees]
            
            # Update event in Google Calendar
            updated_event = service.events().update(
                calendarId=calendar_conn.google_calendar_id,
                eventId=google_event_id,
                body=existing_event
            ).execute()
            
            logger.info(
                "Event updated in Google Calendar",
                calendar_id=calendar_conn.id,
                google_event_id=google_event_id
            )
            
        except Exception as e:
            logger.error("Failed to update Google Calendar event", error=str(e))
            raise
    
    async def delete_google_event(
        self,
        calendar_conn: Calendar,
        google_event_id: str,
        db: Session
    ):
        """Delete an event from Google Calendar."""
        try:
            credentials = self._get_credentials(calendar_conn)
            await self.refresh_tokens_if_needed(calendar_conn, db)
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Delete event from Google Calendar
            service.events().delete(
                calendarId=calendar_conn.google_calendar_id,
                eventId=google_event_id
            ).execute()
            
            logger.info(
                "Event deleted from Google Calendar",
                calendar_id=calendar_conn.id,
                google_event_id=google_event_id
            )
            
        except Exception as e:
            logger.error("Failed to delete Google Calendar event", error=str(e))
            raise

    async def suggest_optimal_scheduling(
        self, 
        user_id: str, 
        duration_minutes: int,
        preferred_times: Optional[List[Dict[str, Any]]] = None,
        db: Session = None
    ) -> SchedulingSuggestion:
        """Generate intelligent scheduling suggestions."""
        try:
            # Get user's existing events for the next 7 days
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
            
            existing_events = db.query(Event).filter(
                Event.user_id == user_id,
                Event.start_time >= start_date,
                Event.end_time <= end_date
            ).all()
            
            # Generate time slots (simplified algorithm)
            suggested_slots = []
            
            # Check each day from 9 AM to 6 PM
            for day_offset in range(7):
                current_date = start_date + timedelta(days=day_offset)
                
                # Skip weekends for now (can be made configurable)
                if current_date.weekday() >= 5:
                    continue
                
                # Check hourly slots from 9 AM to 6 PM
                for hour in range(9, 18):
                    slot_start = current_date.replace(hour=hour)
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    
                    # Check for conflicts
                    has_conflict = False
                    for event in existing_events:
                        if (slot_start < event.end_time and slot_end > event.start_time):
                            has_conflict = True
                            break
                    
                    if not has_conflict:
                        # Calculate confidence score based on preferences
                        confidence = 0.8  # Base confidence
                        
                        # Prefer morning slots
                        if hour < 12:
                            confidence += 0.1
                        
                        # Prefer not too early or too late
                        if 10 <= hour <= 16:
                            confidence += 0.1
                        
                        suggested_slots.append(TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            confidence_score=min(confidence, 1.0),
                            reason=f"Available {duration_minutes}-minute slot"
                        ))
            
            # Sort by confidence score and return top 5
            suggested_slots.sort(key=lambda x: x.confidence_score, reverse=True)
            suggested_slots = suggested_slots[:5]
            
            return SchedulingSuggestion(
                suggested_slots=suggested_slots,
                preferences_applied={"work_hours": "9AM-6PM", "exclude_weekends": True},
                conflicts_avoided=[event.title for event in existing_events]
            )
            
        except Exception as e:
            logger.error("Failed to generate scheduling suggestions", error=str(e), user_id=user_id)
            raise


# Create service instance
calendar_service = GoogleCalendarService()