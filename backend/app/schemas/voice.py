# backend/app/schemas/voice.py
"""
Voice processing schemas for API requests and responses.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class VoiceInputRequest(BaseModel):
    """Request schema for voice input processing."""
    audio_data: str = Field(..., description="Base64 encoded audio data")
    language: Optional[str] = Field(None, description="Language hint (e.g., 'en', 'fa')")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audio_data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT...",
                "language": "en",
                "session_id": "session_123"
            }
        }
    )


class TranscriptionResponse(BaseModel):
    """Response schema for speech-to-text conversion."""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected language")
    confidence: float = Field(..., description="Confidence score (0-1)")
    processing_time: float = Field(..., description="Processing time in seconds")
    segments: List[Dict[str, Any]] = Field(default=[], description="Detailed segments")
    user_id: Optional[str] = Field(None, description="User ID")
    timestamp: float = Field(..., description="Processing timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Hello, how are you today?",
                "language": "en",
                "confidence": 0.95,
                "processing_time": 1.23,
                "segments": [
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "text": "Hello, how are you today?",
                        "confidence": 0.95
                    }
                ],
                "user_id": "user_123",
                "timestamp": 1699123456.789
            }
        }
    )


class TTSRequest(BaseModel):
    """Request schema for text-to-speech conversion."""
    text: str = Field(..., description="Text to synthesize", max_length=5000)
    language: str = Field(default="en", description="Language code")
    voice_id: Optional[str] = Field(None, description="Specific voice ID to use")
    prefer_quality: bool = Field(default=False, description="Prefer quality over speed")
    speed: Optional[float] = Field(default=1.0, description="Speech speed multiplier", ge=0.5, le=2.0)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Hello, this is a test of the text-to-speech system.",
                "language": "en",
                "voice_id": "custom_voice_123",
                "prefer_quality": True,
                "speed": 1.0
            }
        }
    )


class TTSResponse(BaseModel):
    """Response schema for text-to-speech conversion."""
    audio_url: str = Field(..., description="URL to download audio file")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    metadata: Dict[str, Any] = Field(..., description="Processing metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audio_url": "/api/v1/voice/audio/abc123.wav",
                "audio_data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT...",
                "metadata": {
                    "service_used": "coqui",
                    "processing_time": 0.85,
                    "fallback_used": False,
                    "text_length": 45,
                    "language": "en"
                }
            }
        }
    )


class VoiceProfileRequest(BaseModel):
    """Request schema for creating voice profiles."""
    name: str = Field(..., description="Voice profile name")
    sample_audio: str = Field(..., description="Base64 encoded sample audio")
    characteristics: Optional[Dict[str, Any]] = Field(default={}, description="Voice characteristics")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My Custom Voice",
                "sample_audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT...",
                "characteristics": {
                    "speed": 1.0,
                    "pitch": 0.0,
                    "stability": 0.75,
                    "similarity_boost": 0.75
                }
            }
        }
    )


class VoiceProfileResponse(BaseModel):
    """Response schema for voice profile operations."""
    profile_id: str = Field(..., description="Voice profile ID")
    name: str = Field(..., description="Voice profile name")
    status: str = Field(..., description="Profile status")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile_id": "profile_123",
                "name": "My Custom Voice",
                "status": "ready",
                "created_at": "2023-11-01T12:00:00Z"
            }
        }
    )


class BufferStatusResponse(BaseModel):
    """Response schema for offline buffer status."""
    total_buffered: int = Field(..., description="Total buffered items")
    unprocessed: int = Field(..., description="Unprocessed items")
    processed: int = Field(..., description="Processed items")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_buffered": 15,
                "unprocessed": 3,
                "processed": 12
            }
        }
    )


class WebSocketMessage(BaseModel):
    """WebSocket message schema for real-time voice streaming."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    session_id: str = Field(..., description="Session ID")
    timestamp: float = Field(..., description="Message timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "audio_chunk",
                "data": {
                    "audio_data": "UklGRnoGAABXQVZFZm10...",
                    "is_final": False
                },
                "session_id": "session_123",
                "timestamp": 1699123456.789
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Audio processing failed",
                "error_code": "AUDIO_PROCESSING_ERROR",
                "details": {
                    "processing_time": 1.23,
                    "audio_length": 5.67
                }
            }
        }
    )