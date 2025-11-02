"""
Pydantic schemas for WhatsApp Business Cloud API integration.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class MessageDirection(str, Enum):
    """Message direction enum."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageType(str, Enum):
    """WhatsApp message type enum."""
    TEXT = "text"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class MessageStatus(str, Enum):
    """WhatsApp message status enum."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    PENDING = "pending"


class ThreadStatus(str, Enum):
    """WhatsApp thread status enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class WhatsAppMessageCreate(BaseModel):
    """Schema for creating a WhatsApp message."""
    recipient: str = Field(..., description="Recipient phone number in international format")
    content: str = Field(..., max_length=4096, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    template_name: Optional[str] = Field(None, description="Template name for template messages")
    template_params: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")
    
    @field_validator('recipient')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        
        # Must start with + and have 10-15 digits
        if not cleaned.startswith('+') or len(cleaned) < 11 or len(cleaned) > 16:
            raise ValueError('Phone number must be in international format (+1234567890)')
        
        return cleaned


class WhatsAppMessageResponse(BaseModel):
    """Schema for WhatsApp message response."""
    id: str
    thread_id: str
    message_id: Optional[str] = None
    direction: MessageDirection
    content: str
    message_type: MessageType
    status: MessageStatus
    sent_at: datetime
    
    model_config = {"from_attributes": True}


class WhatsAppThreadCreate(BaseModel):
    """Schema for creating a WhatsApp thread."""
    phone_number: str = Field(..., description="Phone number in international format")
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        if not cleaned.startswith('+') or len(cleaned) < 11 or len(cleaned) > 16:
            raise ValueError('Phone number must be in international format (+1234567890)')
        return cleaned


class WhatsAppThreadResponse(BaseModel):
    """Schema for WhatsApp thread response."""
    id: str
    user_id: str
    phone_number: str
    thread_status: ThreadStatus
    last_message_at: datetime
    message_count: Optional[int] = None
    
    model_config = {"from_attributes": True}


class WhatsAppWebhookMessage(BaseModel):
    """Schema for incoming WhatsApp webhook message."""
    from_: str = Field(..., alias="from", description="Sender phone number")
    id: str = Field(..., description="Message ID from WhatsApp")
    timestamp: str = Field(..., description="Message timestamp")
    type: str = Field(..., description="Message type")
    text: Optional[Dict[str, str]] = Field(None, description="Text message content")
    interactive: Optional[Dict[str, Any]] = Field(None, description="Interactive message content")
    
    model_config = {"populate_by_name": True}


class WhatsAppWebhookEntry(BaseModel):
    """Schema for WhatsApp webhook entry."""
    id: str = Field(..., description="WhatsApp Business Account ID")
    changes: List[Dict[str, Any]] = Field(..., description="Changes in the webhook")


class WhatsAppWebhookPayload(BaseModel):
    """Schema for complete WhatsApp webhook payload."""
    object: str = Field(..., description="Object type (should be 'whatsapp_business_account')")
    entry: List[WhatsAppWebhookEntry] = Field(..., description="Webhook entries")


class MessageTemplate(BaseModel):
    """Schema for WhatsApp message template."""
    name: str = Field(..., description="Template name")
    language: str = Field(default="en_US", description="Template language")
    category: str = Field(..., description="Template category")
    components: List[Dict[str, Any]] = Field(..., description="Template components")
    status: str = Field(default="PENDING", description="Template status")


class ConfirmationMessage(BaseModel):
    """Schema for AI action confirmation messages."""
    action_type: str = Field(..., description="Type of action requiring confirmation")
    action_description: str = Field(..., description="Human-readable action description")
    confirmation_options: List[str] = Field(default=["Y", "N", "Cancel"], description="Available response options")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the action")
    expires_at: Optional[datetime] = Field(None, description="When the confirmation expires")


class UserResponse(BaseModel):
    """Schema for processing user responses to confirmations."""
    response: str = Field(..., description="User response (Y/N/Cancel)")
    message_id: str = Field(..., description="Original message ID being responded to")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Context from original confirmation")
    
    @field_validator('response')
    @classmethod
    def validate_response(cls, v):
        """Validate response format."""
        normalized = v.upper().strip()
        valid_responses = ['Y', 'YES', 'N', 'NO', 'CANCEL', 'C']
        if normalized not in valid_responses:
            raise ValueError(f'Response must be one of: {", ".join(valid_responses)}')
        return normalized


class OptInRequest(BaseModel):
    """Schema for WhatsApp opt-in request."""
    phone_number: str = Field(..., description="Phone number to opt in")
    consent_text: str = Field(..., description="Consent text shown to user")
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        if not cleaned.startswith('+') or len(cleaned) < 11 or len(cleaned) > 16:
            raise ValueError('Phone number must be in international format (+1234567890)')
        return cleaned


class OptInResponse(BaseModel):
    """Schema for WhatsApp opt-in response."""
    success: bool
    message: str
    consent_id: Optional[str] = None


class DailySummary(BaseModel):
    """Schema for daily summary messages."""
    user_id: str
    summary_date: datetime
    tasks_completed: int
    events_attended: int
    ai_suggestions: List[str]
    insights: List[str]
    next_day_preview: List[str]