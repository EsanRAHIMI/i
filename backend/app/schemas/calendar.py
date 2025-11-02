"""
Pydantic schemas for calendar operations.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class CalendarOAuthInitiate(BaseModel):
    """Schema for initiating OAuth flow."""
    redirect_uri: Optional[str] = Field(None, description="Custom redirect URI")


class CalendarOAuthCallback(BaseModel):
    """Schema for OAuth callback data."""
    code: str = Field(..., description="Authorization code from Google")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")


class CalendarConnection(BaseModel):
    """Schema for calendar connection status."""
    id: str
    user_id: str
    google_calendar_id: Optional[str] = None
    connected: bool
    last_sync_at: Optional[datetime] = None
    webhook_id: Optional[str] = None


class CalendarEvent(BaseModel):
    """Schema for calendar events."""
    id: Optional[str] = None
    google_event_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    ai_generated: bool = False


class CalendarEventCreate(BaseModel):
    """Schema for creating calendar events."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)


class CalendarEventUpdate(BaseModel):
    """Schema for updating calendar events."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


class CalendarSyncResult(BaseModel):
    """Schema for calendar sync results."""
    events_synced: int
    events_created: int
    events_updated: int
    events_deleted: int
    sync_token: Optional[str] = None
    next_sync_at: Optional[datetime] = None


class CalendarWebhookNotification(BaseModel):
    """Schema for Google Calendar webhook notifications."""
    channel_id: str
    channel_token: Optional[str] = None
    channel_expiration: Optional[str] = None
    resource_id: str
    resource_uri: str
    resource_state: str


class TimeSlot(BaseModel):
    """Schema for available time slots."""
    start_time: datetime
    end_time: datetime
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = None


class SchedulingSuggestion(BaseModel):
    """Schema for intelligent scheduling suggestions."""
    suggested_slots: List[TimeSlot]
    preferences_applied: Dict[str, Any] = Field(default_factory=dict)
    conflicts_avoided: List[str] = Field(default_factory=list)


class CalendarWatchRequest(BaseModel):
    """Schema for setting up calendar watch."""
    calendar_id: str
    webhook_url: HttpUrl
    expiration_time: Optional[datetime] = None


class CalendarWatchResponse(BaseModel):
    """Schema for calendar watch response."""
    channel_id: str
    resource_id: str
    expiration_time: datetime
    webhook_url: str