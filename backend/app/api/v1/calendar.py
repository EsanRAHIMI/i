"""
Calendar API endpoints for Google Calendar integration.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
import structlog

from ...database.base import get_db
from ...database.models import User, Calendar
from ...middleware.auth import get_current_user
from ...services.calendar import calendar_service
from ...config import settings
from ...schemas.calendar import (
    CalendarOAuthInitiate, CalendarOAuthCallback, CalendarConnection,
    CalendarEvent, CalendarEventCreate, CalendarEventUpdate,
    CalendarSyncResult, CalendarWebhookNotification,
    SchedulingSuggestion, CalendarWatchRequest, CalendarWatchResponse
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/connect", response_model=dict)
async def initiate_calendar_connection(
    request: Request,
    oauth_data: CalendarOAuthInitiate,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate Google Calendar OAuth2 connection flow.
    
    This endpoint generates the authorization URL that users need to visit
    to grant calendar access permissions.
    """
    try:
        # Use GOOGLE_REDIRECT_URI from settings (must match Google Cloud Console)
        # If not set, construct from request URL
        if settings.GOOGLE_REDIRECT_URI:
            redirect_uri = settings.GOOGLE_REDIRECT_URI
        else:
            # Construct callback URL from request as fallback
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            redirect_uri = f"{base_url}/api/v1/calendar/oauth/callback"
        
        # Generate state for CSRF protection
        import uuid
        state = str(uuid.uuid4())
        
        # Get authorization URL
        auth_url = calendar_service.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state
        )
        
        logger.info(
            "Calendar OAuth flow initiated",
            user_id=current_user.id,
            redirect_uri=redirect_uri,
            state=state
        )
        
        return {
            "authorization_url": auth_url,
            "state": state,
            "redirect_uri": redirect_uri
        }
        
    except Exception as e:
        logger.error("Failed to initiate calendar connection", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to initiate calendar connection")


@router.get("/oauth/callback")
async def handle_oauth_callback_get(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google Calendar OAuth2 callback via GET (redirect from Google).
    
    This endpoint just redirects to the frontend callback page with the code/error.
    The frontend will then call the POST endpoint to complete the OAuth flow.
    """
    from fastapi.responses import RedirectResponse
    
    # Get frontend URL from settings
    frontend_url = settings.FRONTEND_URL or 'http://localhost:3000'
    
    try:
        if error:
            logger.warning("OAuth callback received error", error=error)
            redirect_url = f"{frontend_url}/calendar/callback?error={error.replace(' ', '_')}"
            return RedirectResponse(url=redirect_url)
        
        if not code:
            logger.warning("OAuth callback received without code")
            redirect_url = f"{frontend_url}/calendar/callback?error=missing_code"
            return RedirectResponse(url=redirect_url)
        
        # Redirect to frontend callback page with code and state
        # Frontend will handle the actual token exchange via POST
        redirect_url = f"{frontend_url}/calendar/callback?code={code}&state={state or ''}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error("Failed to process OAuth callback redirect", error=str(e))
        error_msg = str(e).replace(' ', '_')
        redirect_url = f"{frontend_url}/calendar/callback?error={error_msg}"
        return RedirectResponse(url=redirect_url)


@router.post("/oauth/callback", response_model=CalendarConnection)
async def handle_oauth_callback_post(
    callback_data: CalendarOAuthCallback,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Handle Google Calendar OAuth2 callback via POST (from frontend).
    
    This endpoint processes the authorization code returned by Google
    and exchanges it for access tokens.
    """
    try:
        # Use GOOGLE_REDIRECT_URI from settings (must match the one used in initiation)
        if settings.GOOGLE_REDIRECT_URI:
            redirect_uri = settings.GOOGLE_REDIRECT_URI
        else:
            # Construct callback URL from request as fallback
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            redirect_uri = f"{base_url}/api/v1/calendar/oauth/callback"
        
        # Exchange code for tokens and create calendar connection
        connection = await calendar_service.exchange_code_for_tokens(
            code=callback_data.code,
            redirect_uri=redirect_uri,
            db=db,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "Calendar OAuth callback processed successfully",
            user_id=current_user.id,
            calendar_id=connection.id
        )
        
        return connection
        
    except Exception as e:
        logger.error("Failed to process OAuth callback", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=400, detail="Failed to process OAuth callback")


@router.get("/connection", response_model=Optional[CalendarConnection])
async def get_calendar_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's calendar connection status.
    """
    try:
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        if not calendar_conn:
            return None
        
        return CalendarConnection(
            id=str(calendar_conn.id),
            user_id=str(current_user.id),
            google_calendar_id=calendar_conn.google_calendar_id,
            connected=bool(calendar_conn.access_token_encrypted),
            last_sync_at=calendar_conn.last_sync_at,
            webhook_id=calendar_conn.webhook_id
        )
        
    except Exception as e:
        logger.error("Failed to get calendar connection", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get calendar connection")


@router.delete("/connection")
async def disconnect_calendar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Disconnect the user's Google Calendar integration.
    """
    try:
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        if not calendar_conn:
            raise HTTPException(status_code=404, detail="No calendar connection found")
        
        # Delete the calendar connection and associated events
        db.delete(calendar_conn)
        db.commit()
        
        logger.info("Calendar disconnected successfully", user_id=current_user.id)
        
        return {"message": "Calendar disconnected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect calendar", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to disconnect calendar")


@router.post("/sync", response_model=CalendarSyncResult)
async def sync_calendar(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger calendar synchronization.
    """
    try:
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        if not calendar_conn:
            raise HTTPException(status_code=404, detail="No calendar connection found")
        
        # Perform sync
        sync_result = await calendar_service.sync_events(
            calendar_conn=calendar_conn,
            db=db,
            sync_token=calendar_conn.sync_token
        )
        
        logger.info(
            "Manual calendar sync completed",
            user_id=current_user.id,
            events_synced=sync_result.events_synced
        )
        
        return sync_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to sync calendar", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to sync calendar")


@router.get("/events", response_model=List[CalendarEvent])
async def get_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get calendar events for the current user.
    """
    try:
        from datetime import datetime, timedelta
        from ...database.models import Event
        
        # Parse date filters
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_dt = datetime.utcnow() - timedelta(days=7)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_dt = datetime.utcnow() + timedelta(days=30)
        
        # Query events
        events = db.query(Event).filter(
            Event.user_id == current_user.id,
            Event.start_time >= start_dt,
            Event.end_time <= end_dt
        ).order_by(Event.start_time).limit(limit).all()
        
        # Convert to response format
        calendar_events = []
        for event in events:
            calendar_events.append(CalendarEvent(
                id=str(event.id),
                google_event_id=event.google_event_id,
                title=event.title,
                description=event.description,
                start_time=event.start_time,
                end_time=event.end_time,
                location=event.location,
                attendees=event.attendees or [],
                ai_generated=event.ai_generated
            ))
        
        return calendar_events
        
    except Exception as e:
        logger.error("Failed to get calendar events", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get calendar events")


@router.post("/events", response_model=CalendarEvent)
async def create_calendar_event(
    event_data: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new calendar event.
    """
    try:
        from ...database.models import Event
        
        # Get calendar connection if available
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        # Create event in Google Calendar if connected
        google_event_id = None
        if calendar_conn and calendar_conn.access_token_encrypted:
            google_event_id = await calendar_service.create_google_event(
                calendar_conn=calendar_conn,
                event_data=event_data,
                db=db
            )
        
        # Create event in database
        new_event = Event(
            user_id=current_user.id,
            calendar_id=calendar_conn.id if calendar_conn else None,
            google_event_id=google_event_id,
            title=event_data.title,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            location=event_data.location,
            attendees=event_data.attendees,
            ai_generated=True  # Assume AI-generated for API-created events
        )
        
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        
        logger.info(
            "Calendar event created",
            user_id=current_user.id,
            event_id=new_event.id,
            title=event_data.title,
            google_event_id=google_event_id
        )
        
        return CalendarEvent(
            id=str(new_event.id),
            google_event_id=new_event.google_event_id,
            title=new_event.title,
            description=new_event.description,
            start_time=new_event.start_time,
            end_time=new_event.end_time,
            location=new_event.location,
            attendees=new_event.attendees or [],
            ai_generated=new_event.ai_generated
        )
        
    except Exception as e:
        logger.error("Failed to create calendar event", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to create calendar event")


@router.get("/events/{event_id}", response_model=CalendarEvent)
async def get_calendar_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific calendar event by ID.
    """
    try:
        from ...database.models import Event
        
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.user_id == current_user.id
        ).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return CalendarEvent(
            id=str(event.id),
            google_event_id=event.google_event_id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            attendees=event.attendees or [],
            ai_generated=event.ai_generated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get calendar event", error=str(e), user_id=current_user.id, event_id=event_id)
        raise HTTPException(status_code=500, detail="Failed to get calendar event")


@router.put("/events/{event_id}", response_model=CalendarEvent)
async def update_calendar_event(
    event_id: str,
    event_data: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing calendar event.
    """
    try:
        from ...database.models import Event
        
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.user_id == current_user.id
        ).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update Google Calendar event if connected
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        if calendar_conn and event.google_event_id:
            await calendar_service.update_google_event(
                calendar_conn=calendar_conn,
                google_event_id=event.google_event_id,
                event_data=event_data,
                db=db
            )
        
        # Update local event
        if event_data.title is not None:
            event.title = event_data.title
        if event_data.description is not None:
            event.description = event_data.description
        if event_data.start_time is not None:
            event.start_time = event_data.start_time
        if event_data.end_time is not None:
            event.end_time = event_data.end_time
        if event_data.location is not None:
            event.location = event_data.location
        if event_data.attendees is not None:
            event.attendees = event_data.attendees
        
        db.commit()
        db.refresh(event)
        
        logger.info(
            "Calendar event updated",
            user_id=current_user.id,
            event_id=event_id,
            title=event.title
        )
        
        return CalendarEvent(
            id=str(event.id),
            google_event_id=event.google_event_id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            attendees=event.attendees or [],
            ai_generated=event.ai_generated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update calendar event", error=str(e), user_id=current_user.id, event_id=event_id)
        raise HTTPException(status_code=500, detail="Failed to update calendar event")


@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a calendar event.
    """
    try:
        from ...database.models import Event
        
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.user_id == current_user.id
        ).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Delete from Google Calendar if connected
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        if calendar_conn and event.google_event_id:
            await calendar_service.delete_google_event(
                calendar_conn=calendar_conn,
                google_event_id=event.google_event_id,
                db=db
            )
        
        # Delete local event
        db.delete(event)
        db.commit()
        
        logger.info(
            "Calendar event deleted",
            user_id=current_user.id,
            event_id=event_id,
            title=event.title
        )
        
        return {"message": "Event deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete calendar event", error=str(e), user_id=current_user.id, event_id=event_id)
        raise HTTPException(status_code=500, detail="Failed to delete calendar event")


@router.get("/suggestions", response_model=SchedulingSuggestion)
async def get_scheduling_suggestions(
    duration_minutes: int = 60,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get intelligent scheduling suggestions based on user's calendar and preferences.
    """
    try:
        suggestions = await calendar_service.suggest_optimal_scheduling(
            user_id=str(current_user.id),
            duration_minutes=duration_minutes,
            db=db
        )
        
        logger.info(
            "Scheduling suggestions generated",
            user_id=current_user.id,
            duration_minutes=duration_minutes,
            suggestions_count=len(suggestions.suggested_slots)
        )
        
        return suggestions
        
    except Exception as e:
        logger.error("Failed to generate scheduling suggestions", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to generate scheduling suggestions")


@router.post("/webhook")
async def handle_calendar_webhook(
    notification: CalendarWebhookNotification,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handle Google Calendar webhook notifications for real-time updates.
    """
    try:
        logger.info(
            "Calendar webhook received",
            channel_id=notification.channel_id,
            resource_state=notification.resource_state,
            resource_id=notification.resource_id
        )
        
        # Find the calendar connection by webhook channel ID
        calendar_conn = db.query(Calendar).filter(
            Calendar.webhook_id == notification.channel_id
        ).first()
        
        if not calendar_conn:
            logger.warning("Webhook received for unknown channel", channel_id=notification.channel_id)
            return {"status": "ignored", "reason": "unknown_channel"}
        
        # Trigger background sync if this is a data change notification
        if notification.resource_state in ['exists', 'not_exists']:
            from ...tasks.calendar_sync import sync_calendar_events
            
            # Use Celery task for background processing
            background_tasks.add_task(
                sync_calendar_events,
                calendar_id=str(calendar_conn.id),
                sync_token=calendar_conn.sync_token
            )
            
            logger.info(
                "Background sync triggered by webhook",
                calendar_id=calendar_conn.id,
                channel_id=notification.channel_id
            )
        
        return {
            "status": "processed",
            "calendar_id": str(calendar_conn.id),
            "sync_triggered": notification.resource_state in ['exists', 'not_exists']
        }
        
    except Exception as e:
        logger.error("Failed to process calendar webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.post("/watch", response_model=CalendarWatchResponse)
async def setup_calendar_watch(
    watch_request: CalendarWatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Set up Google Calendar push notifications (webhook).
    """
    try:
        calendar_conn = db.query(Calendar).filter(
            Calendar.user_id == current_user.id
        ).first()
        
        if not calendar_conn:
            raise HTTPException(status_code=404, detail="No calendar connection found")
        
        # Set up webhook using the calendar service
        webhook_result = await calendar_service.setup_webhook(
            calendar_conn=calendar_conn,
            webhook_url=str(watch_request.webhook_url),
            db=db
        )
        
        # Calculate expiration time (Google Calendar webhooks expire after some time)
        from datetime import datetime, timedelta
        expiration_time = datetime.utcnow() + timedelta(hours=24)
        if watch_request.expiration_time:
            expiration_time = watch_request.expiration_time
        
        logger.info(
            "Calendar watch set up successfully",
            user_id=current_user.id,
            channel_id=webhook_result['channel_id'],
            webhook_url=str(watch_request.webhook_url)
        )
        
        return CalendarWatchResponse(
            channel_id=webhook_result['channel_id'],
            resource_id=webhook_result['resource_id'],
            expiration_time=expiration_time,
            webhook_url=str(watch_request.webhook_url)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to set up calendar watch", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to set up calendar watch")