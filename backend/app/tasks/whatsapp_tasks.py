"""
Celery tasks for WhatsApp messaging and workflow automation.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from ..celery_app import celery_app
from ..database.base import get_async_session
from ..database.models import (
    User, UserSettings, WhatsAppThread, WhatsAppMessage,
    Task, Event, AuditLog
)
from ..schemas.whatsapp import (
    DailySummary, ConfirmationMessage, WhatsAppMessageCreate,
    MessageType
)
from ..services.whatsapp import whatsapp_service

logger = logging.getLogger(__name__)


@celery_app.task(name="send_daily_summaries")
def send_daily_summaries_task():
    """
    Celery task to send daily summaries to all opted-in users.
    
    Runs daily at a scheduled time (typically evening).
    """
    import asyncio
    
    async def _send_summaries():
        async with get_async_session() as db:
            try:
                # Get all users with WhatsApp opt-in
                result = await db.execute(
                    select(User)
                    .join(UserSettings)
                    .where(UserSettings.whatsapp_opt_in == True)
                    .options(selectinload(User.settings))
                )
                users = result.scalars().all()
                
                logger.info(f"Sending daily summaries to {len(users)} users")
                
                for user in users:
                    try:
                        summary = await generate_daily_summary(db, str(user.id))
                        if summary:
                            await whatsapp_service.send_daily_summary(
                                db, str(user.id), summary
                            )
                            logger.info(f"Daily summary sent to user {user.id}")
                    except Exception as e:
                        logger.error(f"Failed to send summary to user {user.id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in daily summaries task: {e}")
    
    # Run the async function
    asyncio.run(_send_summaries())


@celery_app.task(name="process_confirmation_timeout")
def process_confirmation_timeout_task(confirmation_id: str, user_id: str):
    """
    Celery task to handle confirmation timeouts.
    
    Automatically cancels actions that haven't been confirmed within the timeout period.
    """
    import asyncio
    
    async def _process_timeout():
        async with get_async_session() as db:
            try:
                # Log timeout event
                audit_log = AuditLog(
                    user_id=user_id,
                    action="confirmation_timeout",
                    resource_type="confirmation",
                    resource_id=confirmation_id,
                    details={
                        "reason": "User did not respond within timeout period",
                        "timeout_at": datetime.utcnow().isoformat()
                    }
                )
                db.add(audit_log)
                await db.commit()
                
                # Send timeout notification
                message = WhatsAppMessageCreate(
                    recipient="",  # Will be filled by service
                    content="⏰ Confirmation timeout: The previous action has been automatically cancelled due to no response.",
                    message_type=MessageType.TEXT
                )
                
                # Get user's thread and send notification
                result = await db.execute(
                    select(WhatsAppThread).where(
                        and_(
                            WhatsAppThread.user_id == user_id,
                            WhatsAppThread.thread_status == "active"
                        )
                    ).order_by(desc(WhatsAppThread.last_message_at))
                )
                thread = result.scalar_one_or_none()
                
                if thread:
                    message.recipient = thread.phone_number
                    await whatsapp_service.send_message(db, user_id, message)
                
                logger.info(f"Processed confirmation timeout for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error processing confirmation timeout: {e}")
    
    asyncio.run(_process_timeout())


@celery_app.task(name="send_task_reminders")
def send_task_reminders_task():
    """
    Celery task to send task reminders via WhatsApp.
    
    Runs periodically to check for upcoming task deadlines.
    """
    import asyncio
    
    async def _send_reminders():
        async with get_async_session() as db:
            try:
                # Get tasks due within next 2 hours for opted-in users
                reminder_time = datetime.utcnow() + timedelta(hours=2)
                
                result = await db.execute(
                    select(Task)
                    .join(User)
                    .join(UserSettings)
                    .where(
                        and_(
                            Task.due_date <= reminder_time,
                            Task.due_date > datetime.utcnow(),
                            Task.status == "pending",
                            UserSettings.whatsapp_opt_in == True
                        )
                    )
                    .options(selectinload(Task.user))
                )
                tasks = result.scalars().all()
                
                logger.info(f"Sending reminders for {len(tasks)} tasks")
                
                for task in tasks:
                    try:
                        reminder_text = f"⏰ Task Reminder: {task.title}\n\nDue: {task.due_date.strftime('%I:%M %p')}\n\nReply DONE when completed."
                        
                        message = WhatsAppMessageCreate(
                            recipient="",  # Will be filled by service
                            content=reminder_text,
                            message_type=MessageType.TEXT
                        )
                        
                        # Get user's thread
                        thread_result = await db.execute(
                            select(WhatsAppThread).where(
                                and_(
                                    WhatsAppThread.user_id == task.user_id,
                                    WhatsAppThread.thread_status == "active"
                                )
                            ).order_by(desc(WhatsAppThread.last_message_at))
                        )
                        thread = thread_result.scalar_one_or_none()
                        
                        if thread:
                            message.recipient = thread.phone_number
                            await whatsapp_service.send_message(
                                db, str(task.user_id), message
                            )
                            logger.info(f"Reminder sent for task {task.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to send reminder for task {task.id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in task reminders: {e}")
    
    asyncio.run(_send_reminders())


async def generate_daily_summary(db: AsyncSession, user_id: str) -> Optional[DailySummary]:
    """
    Generate daily summary for a user based on their activities.
    """
    try:
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        # Get today's completed tasks
        tasks_result = await db.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    func.date(Task.created_at) == today,
                    Task.status == "completed"
                )
            )
        )
        completed_tasks = tasks_result.scalars().all()
        
        # Get today's events
        events_result = await db.execute(
            select(Event).where(
                and_(
                    Event.user_id == user_id,
                    func.date(Event.start_time) == today
                )
            )
        )
        events = events_result.scalars().all()
        
        # Get tomorrow's events for preview
        tomorrow_events_result = await db.execute(
            select(Event).where(
                and_(
                    Event.user_id == user_id,
                    func.date(Event.start_time) == tomorrow
                )
            ).order_by(Event.start_time)
        )
        tomorrow_events = tomorrow_events_result.scalars().all()
        
        # Generate AI insights (simplified for now)
        insights = []
        if len(completed_tasks) > 3:
            insights.append("Great productivity today! You completed more tasks than usual.")
        if len(events) > 5:
            insights.append("Busy day with many meetings. Consider scheduling buffer time.")
        if not completed_tasks:
            insights.append("No tasks completed today. Tomorrow is a fresh start!")
        
        # Generate tomorrow preview
        next_day_preview = []
        for event in tomorrow_events[:3]:  # Show max 3 events
            time_str = event.start_time.strftime("%I:%M %p")
            next_day_preview.append(f"{time_str} - {event.title}")
        
        if not next_day_preview:
            next_day_preview.append("No scheduled events tomorrow")
        
        return DailySummary(
            user_id=user_id,
            summary_date=datetime.combine(today, datetime.min.time()),
            tasks_completed=len(completed_tasks),
            events_attended=len(events),
            ai_suggestions=[],  # Could be enhanced with ML recommendations
            insights=insights,
            next_day_preview=next_day_preview
        )
        
    except Exception as e:
        logger.error(f"Error generating daily summary for user {user_id}: {e}")
        return None


class ConfirmationWorkflow:
    """
    Manages confirmation workflows for AI actions.
    """
    
    @staticmethod
    async def request_confirmation(
        db: AsyncSession,
        user_id: str,
        action_type: str,
        action_description: str,
        context_data: Dict[str, Any],
        timeout_minutes: int = 30
    ) -> str:
        """
        Request confirmation from user for an AI action.
        
        Returns confirmation ID for tracking.
        """
        try:
            confirmation = ConfirmationMessage(
                action_type=action_type,
                action_description=action_description,
                context_data=context_data,
                expires_at=datetime.utcnow() + timedelta(minutes=timeout_minutes)
            )
            
            # Send confirmation request
            response = await whatsapp_service.send_confirmation_request(
                db, user_id, confirmation
            )
            
            # Schedule timeout task
            process_confirmation_timeout_task.apply_async(
                args=[str(response.id), user_id],
                countdown=timeout_minutes * 60
            )
            
            # Log confirmation request
            audit_log = AuditLog(
                user_id=user_id,
                action="confirmation_requested",
                resource_type="confirmation",
                resource_id=str(response.id),
                details={
                    "action_type": action_type,
                    "action_description": action_description,
                    "expires_at": confirmation.expires_at.isoformat(),
                    "context": context_data
                }
            )
            db.add(audit_log)
            await db.commit()
            
            logger.info(f"Confirmation requested: {response.id}")
            return str(response.id)
            
        except Exception as e:
            logger.error(f"Error requesting confirmation: {e}")
            raise
    
    @staticmethod
    async def process_confirmation_response(
        db: AsyncSession,
        confirmation_id: str,
        user_response: str,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user response to confirmation request.
        """
        try:
            from ..schemas.whatsapp import UserResponse
            
            response = UserResponse(
                response=user_response,
                message_id=confirmation_id,
                context_data=context_data
            )
            
            result = await whatsapp_service.process_user_response(db, response)
            
            # Execute or cancel action based on response
            if result["action"] == "confirmed":
                await ConfirmationWorkflow._execute_confirmed_action(
                    db, context_data
                )
            elif result["action"] in ["denied", "cancelled"]:
                await ConfirmationWorkflow._cancel_action(
                    db, context_data
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing confirmation response: {e}")
            raise
    
    @staticmethod
    async def _execute_confirmed_action(
        db: AsyncSession,
        context_data: Dict[str, Any]
    ):
        """Execute the confirmed action."""
        action_type = context_data.get("action_type")
        
        if action_type == "create_calendar_event":
            # Handle calendar event creation
            pass
        elif action_type == "send_message":
            # Handle message sending
            pass
        elif action_type == "create_task":
            # Handle task creation
            pass
        
        logger.info(f"Executed confirmed action: {action_type}")
    
    @staticmethod
    async def _cancel_action(
        db: AsyncSession,
        context_data: Dict[str, Any]
    ):
        """Cancel the denied/cancelled action."""
        action_type = context_data.get("action_type")
        
        # Log cancellation
        audit_log = AuditLog(
            action="action_cancelled",
            resource_type="confirmation",
            details={
                "action_type": action_type,
                "reason": "User denied/cancelled",
                "context": context_data
            }
        )
        db.add(audit_log)
        await db.commit()
        
        logger.info(f"Cancelled action: {action_type}")


# Export workflow class for use in other modules
confirmation_workflow = ConfirmationWorkflow()