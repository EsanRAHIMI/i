"""
WhatsApp Business Cloud API endpoints for messaging integration.
"""
import logging
import hmac
import hashlib
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ...database.base import get_db
from ...middleware.auth import get_current_user
from ...database.models import User, WhatsAppThread, WhatsAppMessage
from ...schemas.whatsapp import (
    WhatsAppMessageCreate, WhatsAppMessageResponse,
    WhatsAppThreadResponse, WhatsAppWebhookPayload,
    ConfirmationMessage, UserResponse, OptInRequest, OptInResponse,
    DailySummary
)
from ...services.whatsapp import whatsapp_service
from ...config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify WhatsApp webhook signature."""
    if not settings.WHATSAPP_WEBHOOK_SECRET:
        logger.warning("WhatsApp webhook secret not configured")
        return True  # Allow in development
    
    expected_signature = hmac.new(
        settings.WHATSAPP_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # WhatsApp sends signature as "sha256=<hash>"
    if signature.startswith("sha256="):
        signature = signature[7:]
    
    return hmac.compare_digest(expected_signature, signature)


@router.post("/send", response_model=WhatsAppMessageResponse)
async def send_whatsapp_message(
    message_data: WhatsAppMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a WhatsApp message to a recipient.
    
    Requires user authentication and valid WhatsApp Business API configuration.
    """
    try:
        # Check if user has WhatsApp opt-in
        if not await whatsapp_service.check_user_opt_in(db, str(current_user.id)):
            raise HTTPException(
                status_code=403,
                detail="User has not opted in to WhatsApp notifications"
            )
        
        response = await whatsapp_service.send_message(
            db, str(current_user.id), message_data
        )
        
        logger.info(f"WhatsApp message sent: {response.id}")
        return response
        
    except ValueError as e:
        logger.error(f"WhatsApp send error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error sending WhatsApp message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming WhatsApp webhook events.
    
    Processes message delivery status updates and incoming messages.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        # Verify webhook signature
        if not verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook payload
        payload = await request.json()
        
        # Process webhook in background
        background_tasks.add_task(
            process_webhook_payload, db, payload
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/webhook")
async def verify_whatsapp_webhook(
    request: Request
):
    """
    Verify WhatsApp webhook endpoint during setup.
    
    WhatsApp sends a GET request with verification parameters.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(challenge)
    else:
        logger.warning("WhatsApp webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.get("/threads", response_model=List[WhatsAppThreadResponse])
async def get_user_whatsapp_threads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all WhatsApp threads for the current user.
    """
    try:
        result = await db.execute(
            select(WhatsAppThread)
            .where(WhatsAppThread.user_id == current_user.id)
            .order_by(desc(WhatsAppThread.last_message_at))
        )
        threads = result.scalars().all()
        
        thread_responses = []
        for thread in threads:
            # Count messages in thread
            message_count_result = await db.execute(
                select(WhatsAppMessage)
                .where(WhatsAppMessage.thread_id == thread.id)
            )
            message_count = len(message_count_result.scalars().all())
            
            thread_response = WhatsAppThreadResponse(
                id=str(thread.id),
                user_id=str(thread.user_id),
                phone_number=thread.phone_number,
                thread_status=thread.thread_status,
                last_message_at=thread.last_message_at,
                message_count=message_count
            )
            thread_responses.append(thread_response)
        
        return thread_responses
        
    except Exception as e:
        logger.error(f"Error fetching WhatsApp threads: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch threads")


@router.get("/threads/{thread_id}/messages", response_model=List[WhatsAppMessageResponse])
async def get_thread_messages(
    thread_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get messages from a specific WhatsApp thread.
    """
    try:
        # Verify thread belongs to user
        thread_result = await db.execute(
            select(WhatsAppThread).where(
                and_(
                    WhatsAppThread.id == thread_id,
                    WhatsAppThread.user_id == current_user.id
                )
            )
        )
        thread = thread_result.scalar_one_or_none()
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Get messages
        result = await db.execute(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.thread_id == thread_id)
            .order_by(desc(WhatsAppMessage.sent_at))
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()
        
        return [
            WhatsAppMessageResponse(
                id=str(msg.id),
                thread_id=str(msg.thread_id),
                message_id=msg.message_id,
                direction=msg.direction,
                content=msg.content,
                message_type=msg.message_type,
                status=msg.status,
                sent_at=msg.sent_at
            )
            for msg in messages
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching thread messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.post("/confirmation", response_model=WhatsAppMessageResponse)
async def send_confirmation_request(
    confirmation: ConfirmationMessage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a confirmation request to the user via WhatsApp.
    
    Used by AI system to request user confirmation for actions.
    """
    try:
        response = await whatsapp_service.send_confirmation_request(
            db, str(current_user.id), confirmation
        )
        
        logger.info(f"Confirmation request sent: {response.id}")
        return response
        
    except ValueError as e:
        logger.error(f"Confirmation request error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error sending confirmation: {e}")
        raise HTTPException(status_code=500, detail="Failed to send confirmation")


@router.post("/response", response_model=Dict[str, Any])
async def process_user_response(
    user_response: UserResponse,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process user response to a confirmation request.
    
    Handles Y/N/Cancel responses and updates related tasks/actions.
    """
    try:
        result = await whatsapp_service.process_user_response(db, user_response)
        
        logger.info(f"User response processed: {result['action']}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing user response: {e}")
        raise HTTPException(status_code=500, detail="Failed to process response")


@router.post("/opt-in", response_model=OptInResponse)
async def handle_whatsapp_opt_in(
    opt_in_request: OptInRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle WhatsApp opt-in request from user.
    
    Creates consent record and enables WhatsApp notifications.
    """
    try:
        response = await whatsapp_service.handle_opt_in_request(db, opt_in_request)
        
        if response.success:
            logger.info(f"User opted in to WhatsApp: {opt_in_request.phone_number}")
        else:
            logger.warning(f"Opt-in failed: {response.message}")
        
        return response
        
    except Exception as e:
        logger.error(f"Opt-in processing error: {e}")
        raise HTTPException(status_code=500, detail="Opt-in processing failed")


@router.post("/daily-summary", response_model=Optional[WhatsAppMessageResponse])
async def send_daily_summary(
    summary: DailySummary,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send daily summary to user via WhatsApp.
    
    Only sends if user has opted in to notifications.
    """
    try:
        response = await whatsapp_service.send_daily_summary(
            db, str(current_user.id), summary
        )
        
        if response:
            logger.info(f"Daily summary sent: {response.id}")
        else:
            logger.info("Daily summary not sent - user not opted in")
        
        return response
        
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to send daily summary")


@router.post("/workflow/execute", response_model=Dict[str, Any])
async def execute_workflow_action(
    action_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a workflow action with optional confirmation.
    
    Used by AI system to execute actions that may require user confirmation.
    """
    try:
        from ...services.workflow_manager import workflow_manager
        
        action_type = action_data.get("action_type")
        action_description = action_data.get("action_description")
        action_params = action_data.get("action_params", {})
        require_confirmation = action_data.get("require_confirmation", True)
        timeout_minutes = action_data.get("timeout_minutes", 30)
        
        if not action_type or not action_description:
            raise HTTPException(
                status_code=400,
                detail="action_type and action_description are required"
            )
        
        result = await workflow_manager.execute_with_confirmation(
            db,
            str(current_user.id),
            action_type,
            action_description,
            action_params,
            require_confirmation,
            timeout_minutes
        )
        
        logger.info(f"Workflow action executed: {action_type} - {result['status']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow action: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute workflow action")


@router.post("/workflow/confirm/{confirmation_id}", response_model=Dict[str, Any])
async def confirm_workflow_action(
    confirmation_id: str,
    response_data: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm or deny a pending workflow action.
    
    Typically called automatically when processing WhatsApp responses.
    """
    try:
        from ...services.workflow_manager import workflow_manager
        
        user_response = response_data.get("response", "").upper()
        if not user_response:
            raise HTTPException(status_code=400, detail="response is required")
        
        result = await workflow_manager.handle_confirmation_response(
            db, confirmation_id, user_response
        )
        
        logger.info(f"Workflow confirmation processed: {confirmation_id} - {result['status']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing workflow confirmation: {e}")
        raise HTTPException(status_code=500, detail="Failed to process confirmation")


@router.get("/workflow/pending", response_model=List[Dict[str, Any]])
async def get_pending_confirmations(
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending confirmations for the current user.
    """
    try:
        from ...services.workflow_manager import workflow_manager
        
        # Clean up expired confirmations first
        workflow_manager.cleanup_expired_confirmations()
        
        pending = workflow_manager.get_pending_confirmations(str(current_user.id))
        
        return pending
        
    except Exception as e:
        logger.error(f"Error fetching pending confirmations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending confirmations")


async def process_webhook_payload(db: AsyncSession, payload: Dict[str, Any]):
    """
    Background task to process WhatsApp webhook payload.
    """
    try:
        if payload.get("object") != "whatsapp_business_account":
            logger.warning(f"Unknown webhook object type: {payload.get('object')}")
            return
        
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})
                
                if field == "messages":
                    # Process incoming messages
                    for message in value.get("messages", []):
                        await process_incoming_message(db, message, value)
                
                elif field == "message_status":
                    # Process message status updates
                    for status in value.get("statuses", []):
                        await process_message_status(db, status)
        
    except Exception as e:
        logger.error(f"Error processing webhook payload: {e}")


async def process_incoming_message(
    db: AsyncSession, 
    message: Dict[str, Any], 
    value: Dict[str, Any]
):
    """Process a single incoming WhatsApp message."""
    try:
        from_number = message.get("from")
        message_id = message.get("id")
        message_type = message.get("type", "text")
        
        # Extract message content based on type
        content = ""
        if message_type == "text":
            content = message.get("text", {}).get("body", "")
        elif message_type == "interactive":
            # Handle button responses
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                content = interactive.get("button_reply", {}).get("title", "")
        
        if content and from_number and message_id:
            await whatsapp_service.process_incoming_message(
                db, from_number, message_id, content, message_type
            )
            
            logger.info(f"Processed incoming message: {message_id}")
        
    except Exception as e:
        logger.error(f"Error processing incoming message: {e}")


async def process_message_status(db: AsyncSession, status: Dict[str, Any]):
    """Process WhatsApp message status update."""
    try:
        message_id = status.get("id")
        status_value = status.get("status")
        
        if message_id and status_value:
            # Update message status in database
            result = await db.execute(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.message_id == message_id
                )
            )
            message = result.scalar_one_or_none()
            
            if message:
                message.status = status_value
                await db.commit()
                logger.info(f"Updated message status: {message_id} -> {status_value}")
        
    except Exception as e:
        logger.error(f"Error processing message status: {e}")