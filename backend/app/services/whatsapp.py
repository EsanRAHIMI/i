"""
WhatsApp Business Cloud API service for message handling and integration.
"""
import asyncio
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database.models import (
    User, UserSettings, WhatsAppThread, WhatsAppMessage, 
    Consent, AuditLog
)
from ..schemas.whatsapp import (
    WhatsAppMessageCreate, WhatsAppMessageResponse,
    WhatsAppThreadCreate, WhatsAppThreadResponse,
    MessageTemplate, ConfirmationMessage, UserResponse,
    OptInRequest, OptInResponse, DailySummary,
    MessageDirection, MessageType, MessageStatus, ThreadStatus
)

logger = logging.getLogger(__name__)


class WhatsAppBusinessAPI:
    """WhatsApp Business Cloud API client."""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.verify_token = settings.WHATSAPP_VERIFY_TOKEN
        
    async def send_message(self, recipient: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message via WhatsApp Business API."""
        if not self.access_token or not self.phone_number_id:
            raise ValueError("WhatsApp API credentials not configured")
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            **message
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"WhatsApp API error: {e}")
                raise
    
    async def send_text_message(self, recipient: str, text: str) -> Dict[str, Any]:
        """Send a text message."""
        message = {
            "type": "text",
            "text": {"body": text}
        }
        return await self.send_message(recipient, message)
    
    async def send_template_message(
        self, 
        recipient: str, 
        template_name: str, 
        language: str = "en_US",
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a template message."""
        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": parameters
            })
        
        message = {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components
            }
        }
        return await self.send_message(recipient, message)
    
    async def send_interactive_message(
        self, 
        recipient: str, 
        body_text: str,
        buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Send an interactive message with buttons."""
        interactive_buttons = []
        for i, button in enumerate(buttons[:3]):  # WhatsApp allows max 3 buttons
            interactive_buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"btn_{i}_{button.get('id', i)}",
                    "title": button["title"][:20]  # Max 20 chars
                }
            })
        
        message = {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": interactive_buttons}
            }
        }
        return await self.send_message(recipient, message)


class MessageTemplateManager:
    """Manages WhatsApp message templates."""
    
    def __init__(self):
        self.templates = {
            "confirmation_request": {
                "name": "confirmation_request",
                "language": "en_US",
                "category": "UTILITY",
                "body": "🤖 AI Assistant needs confirmation:\n\n{{1}}\n\nReply with:\n• Y - Yes, proceed\n• N - No, cancel\n• C - Cancel action"
            },
            "daily_summary": {
                "name": "daily_summary", 
                "language": "en_US",
                "category": "UTILITY",
                "body": "📊 Daily Summary for {{1}}:\n\n✅ Tasks completed: {{2}}\n📅 Events attended: {{3}}\n\n💡 AI Insights:\n{{4}}\n\n🔮 Tomorrow's preview:\n{{5}}"
            },
            "task_reminder": {
                "name": "task_reminder",
                "language": "en_US", 
                "category": "UTILITY",
                "body": "⏰ Reminder: {{1}}\n\nDue: {{2}}\n\nReply DONE when completed."
            },
            "welcome_optin": {
                "name": "welcome_optin",
                "language": "en_US",
                "category": "UTILITY", 
                "body": "Welcome to your AI Assistant! 🤖\n\nI can help you manage your calendar, tasks, and daily activities through WhatsApp.\n\nReply Y to opt-in to notifications, or N to decline."
            }
        }
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a message template by name."""
        return self.templates.get(template_name)
    
    def format_confirmation_message(self, action_description: str) -> str:
        """Format a confirmation message."""
        template = self.get_template("confirmation_request")
        if template:
            return template["body"].replace("{{1}}", action_description)
        return f"Confirm action: {action_description}\n\nReply Y/N/Cancel"
    
    def format_daily_summary(
        self, 
        date: str, 
        tasks_completed: int,
        events_attended: int, 
        insights: List[str],
        tomorrow_preview: List[str]
    ) -> str:
        """Format a daily summary message."""
        template = self.get_template("daily_summary")
        if template:
            insights_text = "\n".join(f"• {insight}" for insight in insights[:3])
            preview_text = "\n".join(f"• {item}" for item in tomorrow_preview[:3])
            
            return template["body"].replace("{{1}}", date)\
                                  .replace("{{2}}", str(tasks_completed))\
                                  .replace("{{3}}", str(events_attended))\
                                  .replace("{{4}}", insights_text)\
                                  .replace("{{5}}", preview_text)
        return f"Daily summary for {date}"


class WhatsAppService:
    """Main WhatsApp service for handling messaging operations."""
    
    def __init__(self):
        self.api = WhatsAppBusinessAPI()
        self.template_manager = MessageTemplateManager()
    
    async def get_or_create_thread(
        self, 
        db: AsyncSession, 
        user_id: str, 
        phone_number: str
    ) -> WhatsAppThread:
        """Get existing thread or create new one."""
        # Clean phone number
        cleaned_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Try to find existing thread
        result = await db.execute(
            select(WhatsAppThread).where(
                and_(
                    WhatsAppThread.user_id == user_id,
                    WhatsAppThread.phone_number == cleaned_phone
                )
            )
        )
        thread = result.scalar_one_or_none()
        
        if not thread:
            # Create new thread
            thread = WhatsAppThread(
                user_id=user_id,
                phone_number=cleaned_phone,
                thread_status=ThreadStatus.ACTIVE
            )
            db.add(thread)
            await db.commit()
            await db.refresh(thread)
        
        return thread
    
    async def send_message(
        self,
        db: AsyncSession,
        user_id: str,
        message_data: WhatsAppMessageCreate
    ) -> WhatsAppMessageResponse:
        """Send a WhatsApp message and store in database."""
        # Get or create thread
        thread = await self.get_or_create_thread(db, user_id, message_data.recipient)
        
        try:
            # Send via WhatsApp API
            if message_data.message_type == MessageType.TEMPLATE:
                api_response = await self.api.send_template_message(
                    message_data.recipient,
                    message_data.template_name,
                    parameters=message_data.template_params.get("parameters", [])
                )
            else:
                api_response = await self.api.send_text_message(
                    message_data.recipient,
                    message_data.content
                )
            
            # Store message in database
            whatsapp_message_id = api_response.get("messages", [{}])[0].get("id")
            
            message = WhatsAppMessage(
                thread_id=thread.id,
                message_id=whatsapp_message_id,
                direction=MessageDirection.OUTBOUND,
                content=message_data.content,
                message_type=message_data.message_type,
                status=MessageStatus.SENT
            )
            
            db.add(message)
            
            # Update thread last message time
            thread.last_message_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(message)
            
            return WhatsAppMessageResponse(
                id=str(message.id),
                thread_id=str(thread.id),
                message_id=whatsapp_message_id,
                direction=message.direction,
                content=message.content,
                message_type=message.message_type,
                status=message.status,
                sent_at=message.sent_at
            )
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            await db.rollback()
            raise
    
    async def process_incoming_message(
        self,
        db: AsyncSession,
        from_number: str,
        message_id: str,
        content: str,
        message_type: str = "text"
    ) -> Optional[WhatsAppMessageResponse]:
        """Process incoming WhatsApp message."""
        try:
            # Find user by phone number
            result = await db.execute(
                select(User).join(WhatsAppThread).where(
                    WhatsAppThread.phone_number == from_number
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Received message from unknown number: {from_number}")
                return None
            
            # Get or create thread
            thread = await self.get_or_create_thread(db, str(user.id), from_number)
            
            # Check if message already exists (duplicate webhook)
            existing = await db.execute(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.message_id == message_id
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Duplicate message ignored: {message_id}")
                return None
            
            # Store incoming message
            message = WhatsAppMessage(
                thread_id=thread.id,
                message_id=message_id,
                direction=MessageDirection.INBOUND,
                content=content,
                message_type=MessageType(message_type),
                status=MessageStatus.DELIVERED
            )
            
            db.add(message)
            
            # Update thread
            thread.last_message_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(message)
            
            return WhatsAppMessageResponse(
                id=str(message.id),
                thread_id=str(thread.id),
                message_id=message_id,
                direction=message.direction,
                content=message.content,
                message_type=message.message_type,
                status=message.status,
                sent_at=message.sent_at
            )
            
        except Exception as e:
            logger.error(f"Failed to process incoming message: {e}")
            await db.rollback()
            raise
    
    async def send_confirmation_request(
        self,
        db: AsyncSession,
        user_id: str,
        confirmation: ConfirmationMessage
    ) -> WhatsAppMessageResponse:
        """Send a confirmation request to user."""
        # Get user's WhatsApp thread
        result = await db.execute(
            select(WhatsAppThread).where(
                and_(
                    WhatsAppThread.user_id == user_id,
                    WhatsAppThread.thread_status == ThreadStatus.ACTIVE
                )
            ).order_by(desc(WhatsAppThread.last_message_at))
        )
        thread = result.scalar_one_or_none()
        
        if not thread:
            raise ValueError("No active WhatsApp thread found for user")
        
        # Format confirmation message
        message_text = self.template_manager.format_confirmation_message(
            confirmation.action_description
        )
        
        # Send message
        message_data = WhatsAppMessageCreate(
            recipient=thread.phone_number,
            content=message_text,
            message_type=MessageType.TEXT
        )
        
        return await self.send_message(db, user_id, message_data)
    
    async def process_user_response(
        self,
        db: AsyncSession,
        user_response: UserResponse
    ) -> Dict[str, Any]:
        """Process user response to confirmation."""
        # Normalize response
        response = user_response.response.upper().strip()
        
        # Map responses
        response_mapping = {
            'Y': 'confirmed',
            'YES': 'confirmed', 
            'N': 'denied',
            'NO': 'denied',
            'CANCEL': 'cancelled',
            'C': 'cancelled'
        }
        
        action = response_mapping.get(response, 'unknown')
        
        # Log the response
        audit_log = AuditLog(
            action="whatsapp_response_processed",
            resource_type="confirmation",
            resource_id=user_response.message_id,
            details={
                "response": response,
                "action": action,
                "context": user_response.context_data
            }
        )
        db.add(audit_log)
        await db.commit()
        
        return {
            "action": action,
            "response": response,
            "context": user_response.context_data,
            "processed_at": datetime.utcnow()
        }
    
    async def check_user_opt_in(self, db: AsyncSession, user_id: str) -> bool:
        """Check if user has opted in to WhatsApp notifications."""
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        return settings.whatsapp_opt_in if settings else False
    
    async def handle_opt_in_request(
        self,
        db: AsyncSession,
        opt_in_request: OptInRequest
    ) -> OptInResponse:
        """Handle WhatsApp opt-in request."""
        try:
            # Find user by phone number or create placeholder
            result = await db.execute(
                select(User).join(WhatsAppThread).where(
                    WhatsAppThread.phone_number == opt_in_request.phone_number
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return OptInResponse(
                    success=False,
                    message="User not found. Please register first."
                )
            
            # Create consent record
            consent = Consent(
                user_id=user.id,
                consent_type="whatsapp_notifications",
                granted=True,
                consent_text=opt_in_request.consent_text
            )
            db.add(consent)
            
            # Update user settings
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user.id)
            )
            settings = result.scalar_one_or_none()
            
            if settings:
                settings.whatsapp_opt_in = True
            else:
                settings = UserSettings(
                    user_id=user.id,
                    whatsapp_opt_in=True
                )
                db.add(settings)
            
            await db.commit()
            
            # Send welcome message
            welcome_message = WhatsAppMessageCreate(
                recipient=opt_in_request.phone_number,
                content="✅ You've successfully opted in to AI Assistant notifications! I'll help you stay organized and productive.",
                message_type=MessageType.TEXT
            )
            
            await self.send_message(db, str(user.id), welcome_message)
            
            return OptInResponse(
                success=True,
                message="Successfully opted in to WhatsApp notifications",
                consent_id=str(consent.id)
            )
            
        except Exception as e:
            logger.error(f"Opt-in request failed: {e}")
            await db.rollback()
            return OptInResponse(
                success=False,
                message=f"Opt-in failed: {str(e)}"
            )
    
    async def send_daily_summary(
        self,
        db: AsyncSession,
        user_id: str,
        summary: DailySummary
    ) -> Optional[WhatsAppMessageResponse]:
        """Send daily summary to user."""
        # Check if user opted in
        if not await self.check_user_opt_in(db, user_id):
            return None
        
        # Format summary message
        summary_text = self.template_manager.format_daily_summary(
            summary.summary_date.strftime("%B %d, %Y"),
            summary.tasks_completed,
            summary.events_attended,
            summary.insights,
            summary.next_day_preview
        )
        
        # Get user's thread
        result = await db.execute(
            select(WhatsAppThread).where(
                and_(
                    WhatsAppThread.user_id == user_id,
                    WhatsAppThread.thread_status == ThreadStatus.ACTIVE
                )
            ).order_by(desc(WhatsAppThread.last_message_at))
        )
        thread = result.scalar_one_or_none()
        
        if not thread:
            logger.warning(f"No active WhatsApp thread for user {user_id}")
            return None
        
        # Send summary
        message_data = WhatsAppMessageCreate(
            recipient=thread.phone_number,
            content=summary_text,
            message_type=MessageType.TEXT
        )
        
        return await self.send_message(db, user_id, message_data)


# Global service instance
whatsapp_service = WhatsAppService()