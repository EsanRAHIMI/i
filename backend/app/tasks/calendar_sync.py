"""
Celery tasks for calendar synchronization.
"""
from typing import Optional
from celery import Celery
from sqlalchemy.orm import Session
import structlog

from ..database.base import SessionLocal
from ..database.models import Calendar
from ..services.calendar import calendar_service

logger = structlog.get_logger(__name__)


def sync_calendar_events(calendar_id: str, sync_token: Optional[str] = None):
    """
    Background task to sync calendar events.
    
    Args:
        calendar_id: The calendar connection ID to sync
        sync_token: Optional sync token for incremental sync
    """
    db = SessionLocal()
    try:
        # Get calendar connection
        calendar_conn = db.query(Calendar).filter(Calendar.id == calendar_id).first()
        
        if not calendar_conn:
            logger.error("Calendar connection not found", calendar_id=calendar_id)
            return
        
        # Perform sync
        sync_result = calendar_service.sync_events(
            calendar_conn=calendar_conn,
            db=db,
            sync_token=sync_token or calendar_conn.sync_token
        )
        
        logger.info(
            "Background calendar sync completed",
            calendar_id=calendar_id,
            events_synced=sync_result.events_synced,
            events_created=sync_result.events_created,
            events_updated=sync_result.events_updated,
            events_deleted=sync_result.events_deleted
        )
        
        return {
            "status": "success",
            "events_synced": sync_result.events_synced,
            "events_created": sync_result.events_created,
            "events_updated": sync_result.events_updated,
            "events_deleted": sync_result.events_deleted
        }
        
    except Exception as e:
        logger.error("Background calendar sync failed", error=str(e), calendar_id=calendar_id)
        raise
    finally:
        db.close()


def setup_calendar_webhook(calendar_id: str, webhook_url: str):
    """
    Background task to set up calendar webhook.
    
    Args:
        calendar_id: The calendar connection ID
        webhook_url: The webhook URL to register
    """
    db = SessionLocal()
    try:
        # Get calendar connection
        calendar_conn = db.query(Calendar).filter(Calendar.id == calendar_id).first()
        
        if not calendar_conn:
            logger.error("Calendar connection not found", calendar_id=calendar_id)
            return
        
        # Set up webhook
        webhook_result = calendar_service.setup_webhook(
            calendar_conn=calendar_conn,
            webhook_url=webhook_url,
            db=db
        )
        
        logger.info(
            "Calendar webhook set up successfully",
            calendar_id=calendar_id,
            channel_id=webhook_result['channel_id']
        )
        
        return {
            "status": "success",
            "channel_id": webhook_result['channel_id'],
            "resource_id": webhook_result['resource_id']
        }
        
    except Exception as e:
        logger.error("Failed to set up calendar webhook", error=str(e), calendar_id=calendar_id)
        raise
    finally:
        db.close()


def periodic_calendar_sync():
    """
    Periodic task to sync all connected calendars.
    This should be scheduled to run every 15-30 minutes.
    """
    db = SessionLocal()
    try:
        # Get all calendar connections that need syncing
        calendar_connections = db.query(Calendar).filter(
            Calendar.access_token_encrypted.isnot(None)
        ).all()
        
        sync_results = []
        
        for calendar_conn in calendar_connections:
            try:
                sync_result = calendar_service.sync_events(
                    calendar_conn=calendar_conn,
                    db=db,
                    sync_token=calendar_conn.sync_token
                )
                
                sync_results.append({
                    "calendar_id": str(calendar_conn.id),
                    "user_id": str(calendar_conn.user_id),
                    "status": "success",
                    "events_synced": sync_result.events_synced
                })
                
            except Exception as e:
                logger.error(
                    "Failed to sync calendar in periodic task",
                    error=str(e),
                    calendar_id=calendar_conn.id
                )
                sync_results.append({
                    "calendar_id": str(calendar_conn.id),
                    "user_id": str(calendar_conn.user_id),
                    "status": "error",
                    "error": str(e)
                })
        
        logger.info(
            "Periodic calendar sync completed",
            calendars_processed=len(calendar_connections),
            successful_syncs=len([r for r in sync_results if r["status"] == "success"])
        )
        
        return sync_results
        
    except Exception as e:
        logger.error("Periodic calendar sync failed", error=str(e))
        raise
    finally:
        db.close()