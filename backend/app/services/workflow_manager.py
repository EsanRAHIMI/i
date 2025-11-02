"""
Workflow manager for coordinating AI actions with user confirmations via WhatsApp.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..database.models import User, Task, Event, AuditLog
from ..schemas.whatsapp import ConfirmationMessage
from ..tasks.whatsapp_tasks import confirmation_workflow
from .whatsapp import whatsapp_service

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Manages complex workflows that require user confirmation and multi-step execution.
    """
    
    def __init__(self):
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
    
    async def execute_with_confirmation(
        self,
        db: AsyncSession,
        user_id: str,
        action_type: str,
        action_description: str,
        action_params: Dict[str, Any],
        require_confirmation: bool = True,
        timeout_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Execute an action with optional user confirmation via WhatsApp.
        
        Args:
            db: Database session
            user_id: User ID
            action_type: Type of action (e.g., 'create_calendar_event')
            action_description: Human-readable description for confirmation
            action_params: Parameters needed to execute the action
            require_confirmation: Whether to require user confirmation
            timeout_minutes: Timeout for confirmation in minutes
        
        Returns:
            Dict with execution result and status
        """
        try:
            if not require_confirmation:
                # Execute immediately without confirmation
                return await self._execute_action(db, user_id, action_type, action_params)
            
            # Check if user has WhatsApp opt-in
            if not await whatsapp_service.check_user_opt_in(db, user_id):
                logger.warning(f"User {user_id} not opted in to WhatsApp - executing without confirmation")
                return await self._execute_action(db, user_id, action_type, action_params)
            
            # Request confirmation
            context_data = {
                "action_type": action_type,
                "action_params": action_params,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            confirmation_id = await confirmation_workflow.request_confirmation(
                db, user_id, action_type, action_description, context_data, timeout_minutes
            )
            
            # Store pending confirmation
            self.pending_confirmations[confirmation_id] = {
                "user_id": user_id,
                "action_type": action_type,
                "action_params": action_params,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=timeout_minutes)
            }
            
            return {
                "status": "pending_confirmation",
                "confirmation_id": confirmation_id,
                "message": f"Confirmation request sent via WhatsApp: {action_description}",
                "expires_at": (datetime.utcnow() + timedelta(minutes=timeout_minutes)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}")
            return {
                "status": "error",
                "message": f"Failed to execute workflow: {str(e)}"
            }
    
    async def handle_confirmation_response(
        self,
        db: AsyncSession,
        confirmation_id: str,
        user_response: str
    ) -> Dict[str, Any]:
        """
        Handle user response to confirmation request.
        """
        try:
            pending = self.pending_confirmations.get(confirmation_id)
            if not pending:
                return {
                    "status": "error",
                    "message": "Confirmation not found or expired"
                }
            
            # Check if confirmation has expired
            if datetime.utcnow() > pending["expires_at"]:
                del self.pending_confirmations[confirmation_id]
                return {
                    "status": "expired",
                    "message": "Confirmation has expired"
                }
            
            # Process response
            result = await confirmation_workflow.process_confirmation_response(
                db, confirmation_id, user_response, pending
            )
            
            if result["action"] == "confirmed":
                # Execute the action
                execution_result = await self._execute_action(
                    db,
                    pending["user_id"],
                    pending["action_type"],
                    pending["action_params"]
                )
                
                # Clean up pending confirmation
                del self.pending_confirmations[confirmation_id]
                
                return {
                    "status": "confirmed_and_executed",
                    "execution_result": execution_result,
                    "message": "Action confirmed and executed successfully"
                }
            
            elif result["action"] in ["denied", "cancelled"]:
                # Clean up pending confirmation
                del self.pending_confirmations[confirmation_id]
                
                return {
                    "status": "cancelled",
                    "message": "Action cancelled by user"
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown response action: {result['action']}"
                }
            
        except Exception as e:
            logger.error(f"Error handling confirmation response: {e}")
            return {
                "status": "error",
                "message": f"Failed to process confirmation: {str(e)}"
            }
    
    async def _execute_action(
        self,
        db: AsyncSession,
        user_id: str,
        action_type: str,
        action_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the actual action based on type and parameters.
        """
        try:
            if action_type == "create_calendar_event":
                return await self._create_calendar_event(db, user_id, action_params)
            
            elif action_type == "create_task":
                return await self._create_task(db, user_id, action_params)
            
            elif action_type == "send_whatsapp_message":
                return await self._send_whatsapp_message(db, user_id, action_params)
            
            elif action_type == "update_task_status":
                return await self._update_task_status(db, user_id, action_params)
            
            elif action_type == "schedule_reminder":
                return await self._schedule_reminder(db, user_id, action_params)
            
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return {
                "status": "error",
                "message": f"Failed to execute {action_type}: {str(e)}"
            }
    
    async def _create_calendar_event(
        self,
        db: AsyncSession,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        try:
            event = Event(
                user_id=user_id,
                title=params["title"],
                description=params.get("description"),
                start_time=datetime.fromisoformat(params["start_time"]),
                end_time=datetime.fromisoformat(params["end_time"]),
                location=params.get("location"),
                attendees=params.get("attendees", []),
                ai_generated=True
            )
            
            db.add(event)
            await db.commit()
            await db.refresh(event)
            
            # Log action
            audit_log = AuditLog(
                user_id=user_id,
                action="calendar_event_created",
                resource_type="event",
                resource_id=str(event.id),
                details=params
            )
            db.add(audit_log)
            await db.commit()
            
            return {
                "status": "success",
                "event_id": str(event.id),
                "message": f"Calendar event '{event.title}' created successfully"
            }
            
        except Exception as e:
            await db.rollback()
            raise
    
    async def _create_task(
        self,
        db: AsyncSession,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a task."""
        try:
            task = Task(
                user_id=user_id,
                title=params["title"],
                description=params.get("description"),
                priority=params.get("priority", 3),
                due_date=datetime.fromisoformat(params["due_date"]) if params.get("due_date") else None,
                context_data=params.get("context_data", {}),
                created_by_ai=True
            )
            
            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            # Log action
            audit_log = AuditLog(
                user_id=user_id,
                action="task_created",
                resource_type="task",
                resource_id=str(task.id),
                details=params
            )
            db.add(audit_log)
            await db.commit()
            
            return {
                "status": "success",
                "task_id": str(task.id),
                "message": f"Task '{task.title}' created successfully"
            }
            
        except Exception as e:
            await db.rollback()
            raise
    
    async def _send_whatsapp_message(
        self,
        db: AsyncSession,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a WhatsApp message."""
        try:
            from ..schemas.whatsapp import WhatsAppMessageCreate, MessageType
            
            message_data = WhatsAppMessageCreate(
                recipient=params["recipient"],
                content=params["content"],
                message_type=MessageType(params.get("message_type", "text"))
            )
            
            response = await whatsapp_service.send_message(db, user_id, message_data)
            
            return {
                "status": "success",
                "message_id": response.id,
                "message": "WhatsApp message sent successfully"
            }
            
        except Exception as e:
            raise
    
    async def _update_task_status(
        self,
        db: AsyncSession,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update task status."""
        try:
            task_id = params["task_id"]
            new_status = params["status"]
            
            result = await db.execute(
                select(Task).where(
                    and_(Task.id == task_id, Task.user_id == user_id)
                )
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return {
                    "status": "error",
                    "message": "Task not found"
                }
            
            old_status = task.status
            task.status = new_status
            
            await db.commit()
            
            # Log action
            audit_log = AuditLog(
                user_id=user_id,
                action="task_status_updated",
                resource_type="task",
                resource_id=str(task.id),
                details={
                    "old_status": old_status,
                    "new_status": new_status
                }
            )
            db.add(audit_log)
            await db.commit()
            
            return {
                "status": "success",
                "message": f"Task status updated from '{old_status}' to '{new_status}'"
            }
            
        except Exception as e:
            await db.rollback()
            raise
    
    async def _schedule_reminder(
        self,
        db: AsyncSession,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Schedule a reminder."""
        try:
            from ..tasks.whatsapp_tasks import send_task_reminders_task
            
            reminder_time = datetime.fromisoformat(params["reminder_time"])
            delay_seconds = (reminder_time - datetime.utcnow()).total_seconds()
            
            if delay_seconds > 0:
                # Schedule the reminder task
                send_task_reminders_task.apply_async(countdown=int(delay_seconds))
                
                return {
                    "status": "success",
                    "message": f"Reminder scheduled for {reminder_time.strftime('%Y-%m-%d %H:%M')}"
                }
            else:
                return {
                    "status": "error",
                    "message": "Reminder time must be in the future"
                }
            
        except Exception as e:
            raise
    
    def get_pending_confirmations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all pending confirmations for a user."""
        user_confirmations = []
        current_time = datetime.utcnow()
        
        for conf_id, conf_data in self.pending_confirmations.items():
            if conf_data["user_id"] == user_id and current_time < conf_data["expires_at"]:
                user_confirmations.append({
                    "confirmation_id": conf_id,
                    "action_type": conf_data["action_type"],
                    "created_at": conf_data["created_at"].isoformat(),
                    "expires_at": conf_data["expires_at"].isoformat()
                })
        
        return user_confirmations
    
    def cleanup_expired_confirmations(self):
        """Clean up expired confirmations."""
        current_time = datetime.utcnow()
        expired_ids = [
            conf_id for conf_id, conf_data in self.pending_confirmations.items()
            if current_time > conf_data["expires_at"]
        ]
        
        for conf_id in expired_ids:
            del self.pending_confirmations[conf_id]
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired confirmations")


# Global workflow manager instance
workflow_manager = WorkflowManager()