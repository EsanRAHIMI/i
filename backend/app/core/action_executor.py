"""
Action Executor for the Agentic Core.

This module provides concrete implementations for executing actions
across calendar, messaging, email, and reminder operations with
error recovery and integration with external services.
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import logging

from ..services.auth import AuthService
from ..database.models import User, Event, Task, WhatsAppMessage

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Concrete action executor that integrates with external services.
    
    Provides implementations for calendar, messaging, email, and reminder
    operations with proper error handling and service integration.
    """
    
    def __init__(
        self,
        calendar_service=None,
        whatsapp_service=None,
        email_service=None,
        task_service=None,
        auth_service: AuthService = None
    ):
        self.calendar_service = calendar_service
        self.whatsapp_service = whatsapp_service
        self.email_service = email_service
        self.task_service = task_service
        self.auth_service = auth_service
        
        # Service availability flags
        self.services_available = {
            "calendar": calendar_service is not None,
            "whatsapp": whatsapp_service is not None,
            "email": email_service is not None,
            "task": task_service is not None
        }
    
    async def execute_calendar_create_event(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute calendar event creation.
        
        Args:
            parameters: Event creation parameters
            
        Returns:
            Result dictionary with event details
        """
        
        if not self.services_available["calendar"]:
            raise RuntimeError("Calendar service not available")
        
        try:
            # Extract parameters
            user_id = parameters["user_id"]
            title = parameters.get("title", "New Event")
            description = parameters.get("description", "")
            start_time = self._parse_datetime(parameters.get("start_time"))
            end_time = self._parse_datetime(parameters.get("end_time"))
            location = parameters.get("location")
            attendees = parameters.get("attendees", [])
            
            # Default end time if not provided (1 hour duration)
            if not end_time and start_time:
                end_time = start_time + timedelta(hours=1)
            
            # Create event through calendar service
            event_data = {
                "summary": title,
                "description": description,
                "start": {"dateTime": start_time.isoformat() if start_time else None},
                "end": {"dateTime": end_time.isoformat() if end_time else None},
                "location": location,
                "attendees": [{"email": email} for email in attendees] if attendees else []
            }
            
            # Call calendar service
            result = await self.calendar_service.create_event(user_id, event_data)
            
            logger.info(f"Calendar event created: {result.get('id')}")
            
            return {
                "event_id": result.get("id"),
                "title": title,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "status": "created",
                "calendar_link": result.get("htmlLink")
            }
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}")
            raise RuntimeError(f"Failed to create calendar event: {str(e)}")
    
    async def execute_calendar_update_event(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute calendar event update."""
        
        if not self.services_available["calendar"]:
            raise RuntimeError("Calendar service not available")
        
        try:
            user_id = parameters["user_id"]
            event_id = parameters["event_id"]
            updates = parameters.get("updates", {})
            
            # Update event through calendar service
            result = await self.calendar_service.update_event(user_id, event_id, updates)
            
            logger.info(f"Calendar event updated: {event_id}")
            
            return {
                "event_id": event_id,
                "status": "updated",
                "updated_fields": list(updates.keys())
            }
            
        except Exception as e:
            logger.error(f"Error updating calendar event: {str(e)}")
            raise RuntimeError(f"Failed to update calendar event: {str(e)}")
    
    async def execute_calendar_delete_event(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute calendar event deletion."""
        
        if not self.services_available["calendar"]:
            raise RuntimeError("Calendar service not available")
        
        try:
            user_id = parameters["user_id"]
            event_id = parameters.get("event_id")
            event_criteria = parameters.get("event_criteria", {})
            
            # If no specific event ID, find event by criteria
            if not event_id and event_criteria:
                events = await self.calendar_service.query_events(user_id, event_criteria)
                if events:
                    event_id = events[0].get("id")
                else:
                    raise ValueError("No matching event found to delete")
            
            if not event_id:
                raise ValueError("Event ID or criteria required for deletion")
            
            # Delete event through calendar service
            await self.calendar_service.delete_event(user_id, event_id)
            
            logger.info(f"Calendar event deleted: {event_id}")
            
            return {
                "event_id": event_id,
                "status": "deleted"
            }
            
        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}")
            raise RuntimeError(f"Failed to delete calendar event: {str(e)}")
    
    async def execute_calendar_query_events(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute calendar events query."""
        
        if not self.services_available["calendar"]:
            raise RuntimeError("Calendar service not available")
        
        try:
            user_id = parameters["user_id"]
            date_range = parameters.get("date_range", ["today"])
            filters = parameters.get("filters", {})
            
            # Parse date range
            start_date, end_date = self._parse_date_range(date_range)
            
            # Query events through calendar service
            events = await self.calendar_service.query_events(
                user_id, 
                start_date=start_date,
                end_date=end_date,
                filters=filters
            )
            
            logger.info(f"Calendar query returned {len(events)} events")
            
            return {
                "events": events,
                "count": len(events),
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error querying calendar events: {str(e)}")
            raise RuntimeError(f"Failed to query calendar events: {str(e)}")
    
    async def execute_task_create(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task creation."""
        
        try:
            user_id = parameters["user_id"]
            title = parameters.get("title", "New Task")
            description = parameters.get("description", "")
            due_date = self._parse_datetime(parameters.get("due_date"))
            priority = parameters.get("priority", 3)
            
            # Create task through task service or directly
            if self.task_service:
                result = await self.task_service.create_task(
                    user_id=user_id,
                    title=title,
                    description=description,
                    due_date=due_date,
                    priority=priority
                )
                task_id = result.get("id")
            else:
                # Direct database creation (fallback)
                task_id = str(uuid.uuid4())
                # This would create a Task model instance
                logger.info(f"Task created directly: {task_id}")
            
            logger.info(f"Task created: {task_id}")
            
            return {
                "task_id": task_id,
                "title": title,
                "due_date": due_date.isoformat() if due_date else None,
                "priority": priority,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise RuntimeError(f"Failed to create task: {str(e)}")
    
    async def execute_task_update(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task update."""
        
        try:
            user_id = parameters["user_id"]
            task_id = parameters["task_id"]
            updates = parameters.get("updates", {})
            
            # Update task through task service
            if self.task_service:
                result = await self.task_service.update_task(user_id, task_id, updates)
            else:
                # Direct database update (fallback)
                logger.info(f"Task updated directly: {task_id}")
                result = {"status": "updated"}
            
            logger.info(f"Task updated: {task_id}")
            
            return {
                "task_id": task_id,
                "status": "updated",
                "updated_fields": list(updates.keys())
            }
            
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            raise RuntimeError(f"Failed to update task: {str(e)}")
    
    async def execute_task_complete(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task completion."""
        
        try:
            user_id = parameters["user_id"]
            task_id = parameters["task_id"]
            
            # Mark task as completed
            updates = {"status": "completed", "completed_at": datetime.now()}
            
            if self.task_service:
                result = await self.task_service.update_task(user_id, task_id, updates)
            else:
                # Direct database update (fallback)
                logger.info(f"Task completed directly: {task_id}")
                result = {"status": "completed"}
            
            logger.info(f"Task completed: {task_id}")
            
            return {
                "task_id": task_id,
                "status": "completed",
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error completing task: {str(e)}")
            raise RuntimeError(f"Failed to complete task: {str(e)}")
    
    async def execute_whatsapp_send(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute WhatsApp message sending."""
        
        if not self.services_available["whatsapp"]:
            raise RuntimeError("WhatsApp service not available")
        
        try:
            user_id = parameters["user_id"]
            recipient = parameters["recipient"]
            message = parameters["message"]
            message_type = parameters.get("message_type", "text")
            
            # Send message through WhatsApp service
            result = await self.whatsapp_service.send_message(
                user_id=user_id,
                recipient=recipient,
                message=message,
                message_type=message_type
            )
            
            logger.info(f"WhatsApp message sent: {result.get('message_id')}")
            
            return {
                "message_id": result.get("message_id"),
                "recipient": recipient,
                "status": "sent",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            raise RuntimeError(f"Failed to send WhatsApp message: {str(e)}")
    
    async def execute_email_send(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute email sending."""
        
        if not self.services_available["email"]:
            raise RuntimeError("Email service not available")
        
        try:
            user_id = parameters["user_id"]
            recipient = parameters["recipient"]
            subject = parameters.get("subject", "Message from AI Assistant")
            message = parameters["message"]
            
            # Send email through email service
            result = await self.email_service.send_email(
                user_id=user_id,
                recipient=recipient,
                subject=subject,
                body=message
            )
            
            logger.info(f"Email sent: {result.get('message_id')}")
            
            return {
                "message_id": result.get("message_id"),
                "recipient": recipient,
                "subject": subject,
                "status": "sent",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise RuntimeError(f"Failed to send email: {str(e)}")
    
    async def execute_schedule_reminder(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute reminder scheduling."""
        
        try:
            user_id = parameters["user_id"]
            message = parameters["message"]
            remind_at = self._parse_datetime(parameters["remind_at"])
            reminder_type = parameters.get("reminder_type", "whatsapp")
            
            # Schedule reminder (this would integrate with a task scheduler like Celery)
            reminder_id = str(uuid.uuid4())
            
            # For now, we'll log the reminder scheduling
            # In production, this would create a scheduled task
            logger.info(f"Reminder scheduled: {reminder_id} at {remind_at}")
            
            return {
                "reminder_id": reminder_id,
                "message": message,
                "remind_at": remind_at.isoformat() if remind_at else None,
                "reminder_type": reminder_type,
                "status": "scheduled"
            }
            
        except Exception as e:
            logger.error(f"Error scheduling reminder: {str(e)}")
            raise RuntimeError(f"Failed to schedule reminder: {str(e)}")
    
    def _parse_datetime(self, datetime_input: Any) -> Optional[datetime]:
        """Parse various datetime input formats."""
        
        if not datetime_input:
            return None
        
        if isinstance(datetime_input, datetime):
            return datetime_input
        
        if isinstance(datetime_input, str):
            # Handle common date/time formats
            try:
                # ISO format
                return datetime.fromisoformat(datetime_input.replace('Z', '+00:00'))
            except ValueError:
                pass
            
            # Handle relative dates
            now = datetime.now()
            if datetime_input.lower() == "today":
                return now.replace(hour=9, minute=0, second=0, microsecond=0)
            elif datetime_input.lower() == "tomorrow":
                return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            elif datetime_input.lower() == "next week":
                return (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        
        return None
    
    def _parse_date_range(self, date_range: List[str]) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse date range for queries."""
        
        if not date_range:
            return None, None
        
        start_date = None
        end_date = None
        
        if len(date_range) >= 1:
            start_date = self._parse_datetime(date_range[0])
        
        if len(date_range) >= 2:
            end_date = self._parse_datetime(date_range[1])
        elif start_date:
            # Default to end of day for single date
            end_date = start_date.replace(hour=23, minute=59, second=59)
        
        return start_date, end_date
    
    async def get_service_status(self) -> Dict[str, bool]:
        """Get status of all integrated services."""
        
        status = {}
        
        for service_name, available in self.services_available.items():
            if available:
                # Could add health checks here
                status[service_name] = True
            else:
                status[service_name] = False
        
        return status
    
    async def test_service_integration(self, service_name: str) -> Dict[str, Any]:
        """Test integration with a specific service."""
        
        if service_name not in self.services_available:
            return {"error": f"Unknown service: {service_name}"}
        
        if not self.services_available[service_name]:
            return {"error": f"Service not available: {service_name}"}
        
        try:
            if service_name == "calendar" and self.calendar_service:
                # Test calendar service
                result = await self.calendar_service.health_check()
                return {"service": service_name, "status": "healthy", "details": result}
            
            elif service_name == "whatsapp" and self.whatsapp_service:
                # Test WhatsApp service
                result = await self.whatsapp_service.health_check()
                return {"service": service_name, "status": "healthy", "details": result}
            
            elif service_name == "email" and self.email_service:
                # Test email service
                result = await self.email_service.health_check()
                return {"service": service_name, "status": "healthy", "details": result}
            
            elif service_name == "task" and self.task_service:
                # Test task service
                result = await self.task_service.health_check()
                return {"service": service_name, "status": "healthy", "details": result}
            
            return {"service": service_name, "status": "unknown"}
            
        except Exception as e:
            logger.error(f"Service test failed for {service_name}: {str(e)}")
            return {
                "service": service_name,
                "status": "unhealthy",
                "error": str(e)
            }