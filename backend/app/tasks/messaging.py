"""
Messaging tasks for WhatsApp integration and notifications.
"""
from typing import Dict, Any, List, Optional
import structlog
from celery import current_task

from ..celery_app import celery_app
from ..database.base import SessionLocal
from ..database.models import User, WhatsAppThread, WhatsAppMessage, AuditLog

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, queue="messaging")
def send_whatsapp_message(self, user_id: str, message_content: str, message_type: str = "text", template_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Send WhatsApp message to user.
    
    Args:
        user_id: User ID
        message_content: Message content to send
        message_type: Type of message (text, template, etc.)
        template_data: Optional template data for structured messages
    
    Returns:
        Dict containing message delivery result
    """
    try:
        logger.info("Sending WhatsApp message", user_id=user_id, message_type=message_type)
        
        with SessionLocal() as db:
            # Get or create WhatsApp thread for user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get user's WhatsApp thread (placeholder - would need phone number)
            thread = db.query(WhatsAppThread).filter(
                WhatsAppThread.user_id == user_id,
                WhatsAppThread.thread_status == "active"
            ).first()
            
            if not thread:
                # Create new thread (placeholder phone number)
                thread = WhatsAppThread(
                    user_id=user_id,
                    phone_number="+1234567890",  # Would be retrieved from user settings
                    thread_status="active"
                )
                db.add(thread)
                db.flush()
            
            # Placeholder for actual WhatsApp Business API call
            # In real implementation, this would use WhatsApp Business Cloud API
            delivery_result = {
                "message_id": f"whatsapp_msg_{current_task.request.id}",
                "status": "sent",
                "recipient": thread.phone_number,
                "sent_at": "2024-01-01T12:00:00Z",
                "delivery_status": "delivered"
            }
            
            # Store message in database
            message = WhatsAppMessage(
                thread_id=thread.id,
                message_id=delivery_result["message_id"],
                direction="outbound",
                content=message_content,
                message_type=message_type,
                status="sent"
            )
            
            db.add(message)
            
            # Update thread last message time
            thread.last_message_at = delivery_result["sent_at"]
            
            # Log message sending
            audit_log = AuditLog(
                user_id=user_id,
                action="whatsapp_message_sent",
                resource_type="whatsapp_message",
                resource_id=delivery_result["message_id"],
                details={
                    "message_type": message_type,
                    "delivery_result": delivery_result,
                    "task_id": current_task.request.id
                }
            )
            db.add(audit_log)
            db.commit()
        
        logger.info("WhatsApp message sent successfully", user_id=user_id, message_id=delivery_result["message_id"])
        
        return delivery_result
        
    except Exception as exc:
        logger.error("WhatsApp message sending failed", user_id=user_id, error=str(exc))
        self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True, queue="messaging")
def send_confirmation_message(self, user_id: str, action_description: str, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send confirmation message for AI actions.
    
    Args:
        user_id: User ID
        action_description: Description of action requiring confirmation
        confirmation_data: Data needed for confirmation processing
    
    Returns:
        Dict containing confirmation message result
    """
    try:
        logger.info("Sending confirmation message", user_id=user_id, action=action_description)
        
        # Format confirmation message
        confirmation_message = f"""
🤖 AI Assistant Confirmation

Action: {action_description}

Please reply with:
• Y - Yes, proceed
• N - No, cancel
• C - Cancel and don't ask again

Details: {confirmation_data.get('details', 'No additional details')}
        """.strip()
        
        # Send via WhatsApp
        delivery_result = send_whatsapp_message.delay(
            user_id=user_id,
            message_content=confirmation_message,
            message_type="confirmation"
        ).get()
        
        # Store confirmation state
        with SessionLocal() as db:
            audit_log = AuditLog(
                user_id=user_id,
                action="confirmation_sent",
                resource_type="confirmation",
                resource_id=delivery_result["message_id"],
                details={
                    "action_description": action_description,
                    "confirmation_data": confirmation_data,
                    "awaiting_response": True,
                    "task_id": current_task.request.id
                }
            )
            db.add(audit_log)
            db.commit()
        
        logger.info("Confirmation message sent", user_id=user_id, message_id=delivery_result["message_id"])
        
        return {
            "confirmation_id": delivery_result["message_id"],
            "status": "sent",
            "awaiting_response": True
        }
        
    except Exception as exc:
        logger.error("Confirmation message sending failed", user_id=user_id, error=str(exc))
        self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True, queue="messaging")
def process_whatsapp_response(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process incoming WhatsApp message responses.
    
    Args:
        webhook_data: WhatsApp webhook payload
    
    Returns:
        Dict containing processing result
    """
    try:
        logger.info("Processing WhatsApp response", from_number=webhook_data.get("from"))
        
        message_content = webhook_data.get("text", {}).get("body", "").strip().upper()
        from_number = webhook_data.get("from")
        
        with SessionLocal() as db:
            # Find user by phone number
            thread = db.query(WhatsAppThread).filter(
                WhatsAppThread.phone_number == from_number
            ).first()
            
            if not thread:
                logger.warning("WhatsApp thread not found", from_number=from_number)
                return {"status": "ignored", "reason": "thread_not_found"}
            
            # Store incoming message
            incoming_message = WhatsAppMessage(
                thread_id=thread.id,
                message_id=webhook_data.get("id"),
                direction="inbound",
                content=webhook_data.get("text", {}).get("body", ""),
                message_type="text",
                status="received"
            )
            db.add(incoming_message)
            
            # Process confirmation responses
            processing_result = {"status": "processed", "action": None}
            
            if message_content in ["Y", "YES"]:
                processing_result["action"] = "confirmed"
                # Trigger confirmed action execution
                # This would dispatch to appropriate task based on pending confirmation
                
            elif message_content in ["N", "NO"]:
                processing_result["action"] = "cancelled"
                # Cancel pending action
                
            elif message_content in ["C", "CANCEL"]:
                processing_result["action"] = "cancelled_permanently"
                # Cancel and update user preferences
            
            else:
                # Handle general message or forward to AI processing
                processing_result["action"] = "forward_to_ai"
                # This would trigger AI processing for general conversation
            
            # Log response processing
            audit_log = AuditLog(
                user_id=thread.user_id,
                action="whatsapp_response_processed",
                resource_type="whatsapp_message",
                resource_id=webhook_data.get("id"),
                details={
                    "message_content": message_content,
                    "processing_result": processing_result,
                    "task_id": current_task.request.id
                }
            )
            db.add(audit_log)
            db.commit()
        
        logger.info("WhatsApp response processed", action=processing_result["action"])
        
        return processing_result
        
    except Exception as exc:
        logger.error("WhatsApp response processing failed", error=str(exc))
        self.retry(exc=exc, countdown=30, max_retries=3)


@celery_app.task(bind=True, queue="messaging")
def send_daily_summary(self, user_id: str) -> Dict[str, Any]:
    """
    Send daily summary and insights to user.
    
    Args:
        user_id: User ID
    
    Returns:
        Dict containing summary delivery result
    """
    try:
        logger.info("Sending daily summary", user_id=user_id)
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Generate summary content (placeholder)
            summary_content = f"""
📊 Daily Summary - {user.email}

Today's Highlights:
• 3 tasks completed
• 2 calendar events attended
• 1 AI suggestion implemented

Tomorrow's Schedule:
• 9:00 AM - Team meeting
• 2:00 PM - Project review
• 4:00 PM - Client call

AI Insights:
• You're most productive between 10-12 PM
• Consider scheduling focused work during this time
• 85% task completion rate this week

Have a great day! 🌟
            """.strip()
            
            # Send summary via WhatsApp
            delivery_result = send_whatsapp_message.delay(
                user_id=user_id,
                message_content=summary_content,
                message_type="summary"
            ).get()
        
        logger.info("Daily summary sent successfully", user_id=user_id)
        
        return delivery_result
        
    except Exception as exc:
        logger.error("Daily summary sending failed", user_id=user_id, error=str(exc))
        self.retry(exc=exc, countdown=300, max_retries=2)  # 5 minute delay