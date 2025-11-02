"""
Voice processing API endpoints for STT and TTS functionality.
"""

import asyncio
import base64
import io
import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer

from ...services.voice import stt_service, tts_orchestrator
from ...schemas.voice import (
    VoiceInputRequest, TranscriptionResponse, TTSRequest, TTSResponse,
    VoiceProfileRequest, VoiceProfileResponse, BufferStatusResponse,
    WebSocketMessage, ErrorResponse
)
from ...middleware.auth import get_current_user
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter(prefix="/voice", tags=["voice"])

# Store for temporary audio files
TEMP_AUDIO_DIR = Path(tempfile.gettempdir()) / "voice_api"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message to {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()


@router.post("/stt", response_model=TranscriptionResponse)
async def speech_to_text(
    request: VoiceInputRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert speech to text using Whisper STT.
    
    - **audio_data**: Base64 encoded audio data
    - **language**: Optional language hint (e.g., 'en', 'fa')
    - **session_id**: Optional session ID for context
    """
    try:
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(request.audio_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 audio data: {str(e)}"
            )
        
        # Validate audio data
        if len(audio_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty audio data"
            )
        
        if len(audio_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=400,
                detail="Audio file too large (max 50MB)"
            )
        
        # Process transcription
        result = await stt_service.transcribe_audio(
            audio_data=audio_bytes,
            language=request.language,
            user_id=current_user.get("user_id")
        )
        
        return TranscriptionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-text processing failed: {str(e)}"
        )


@router.post("/stt/file", response_model=TranscriptionResponse)
async def speech_to_text_file(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert uploaded audio file to text using Whisper STT.
    
    - **file**: Audio file (WAV, MP3, M4A, etc.)
    - **language**: Optional language hint
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=400,
                detail="Audio file too large (max 50MB)"
            )
        
        # Process transcription
        result = await stt_service.transcribe_audio(
            audio_data=content,
            language=language,
            user_id=current_user.get("user_id")
        )
        
        return TranscriptionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT file processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-text processing failed: {str(e)}"
        )


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert text to speech using TTS services.
    
    - **text**: Text to synthesize (max 5000 characters)
    - **language**: Language code (default: 'en')
    - **voice_id**: Optional specific voice ID
    - **prefer_quality**: Prefer quality over speed
    - **speed**: Speech speed multiplier (0.5-2.0)
    """
    try:
        # Validate text length
        if len(request.text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Empty text provided")
        
        if len(request.text) > 5000:
            raise HTTPException(
                status_code=400,
                detail="Text too long (max 5000 characters)"
            )
        
        # Synthesize speech
        audio_data, metadata = await tts_orchestrator.synthesize_speech(
            text=request.text,
            user_id=current_user.get("user_id"),
            language=request.language,
            prefer_quality=request.prefer_quality
        )
        
        # Save audio to temporary file
        audio_id = str(uuid.uuid4())
        audio_filename = f"{audio_id}.wav"
        audio_path = TEMP_AUDIO_DIR / audio_filename
        
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        
        # Schedule cleanup after 1 hour
        asyncio.create_task(cleanup_temp_file(audio_path, delay=3600))
        
        # Prepare response
        audio_url = f"/api/v1/voice/audio/{audio_filename}"
        
        # Optionally include base64 data for small files
        audio_data_b64 = None
        if len(audio_data) < 1024 * 1024:  # Include for files < 1MB
            audio_data_b64 = base64.b64encode(audio_data).decode()
        
        return TTSResponse(
            audio_url=audio_url,
            audio_data=audio_data_b64,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Text-to-speech processing failed: {str(e)}"
        )


@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """
    Download generated audio file.
    
    - **filename**: Audio file name
    """
    try:
        audio_path = TEMP_AUDIO_DIR / filename
        
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=audio_path,
            media_type="audio/wav",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio file retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve audio file"
        )


@router.post("/profile", response_model=VoiceProfileResponse)
async def create_voice_profile(
    request: VoiceProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create personalized voice profile from user sample.
    
    - **name**: Voice profile name
    - **sample_audio**: Base64 encoded sample audio
    - **characteristics**: Voice characteristics
    """
    try:
        user_id = current_user.get("user_id")
        
        # Decode sample audio
        try:
            sample_audio_bytes = base64.b64decode(request.sample_audio)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 sample audio: {str(e)}"
            )
        
        # Save sample audio to temporary file
        sample_path = TEMP_AUDIO_DIR / f"sample_{user_id}_{int(time.time())}.wav"
        with open(sample_path, "wb") as f:
            f.write(sample_audio_bytes)
        
        # Create voice profiles in both services
        await tts_orchestrator.coqui_service.create_voice_profile(
            user_id=user_id,
            sample_audio_path=str(sample_path),
            characteristics=request.characteristics
        )
        
        # For ElevenLabs, we would clone the voice (placeholder implementation)
        if tts_orchestrator.elevenlabs_service.api_key:
            try:
                cloned_voice_id = await tts_orchestrator.elevenlabs_service.clone_voice(
                    user_id=user_id,
                    name=request.name,
                    sample_files=[str(sample_path)]
                )
            except Exception as e:
                logger.warning(f"ElevenLabs voice cloning failed: {e}")
        
        # Clean up sample file
        asyncio.create_task(cleanup_temp_file(sample_path, delay=60))
        
        return VoiceProfileResponse(
            profile_id=f"profile_{user_id}",
            name=request.name,
            status="ready",
            created_at=time.time()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice profile creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice profile creation failed: {str(e)}"
        )


@router.get("/buffer/status", response_model=BufferStatusResponse)
async def get_buffer_status(current_user: dict = Depends(get_current_user)):
    """
    Get status of offline audio buffer.
    """
    try:
        status = await stt_service.get_buffer_status()
        return BufferStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Buffer status retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve buffer status"
        )


@router.post("/buffer/process")
async def process_offline_buffer(current_user: dict = Depends(get_current_user)):
    """
    Process buffered offline audio when connectivity is restored.
    """
    try:
        processed_count = await stt_service.process_offline_buffer()
        
        return {
            "message": f"Processed {processed_count} buffered audio items",
            "processed_count": processed_count
        }
        
    except Exception as e:
        logger.error(f"Offline buffer processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process offline buffer"
        )


@router.websocket("/stream/{session_id}")
async def voice_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice streaming.
    
    - **session_id**: Unique session identifier
    """
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = WebSocketMessage(**data)
            
            if message.type == "audio_chunk":
                # Process audio chunk
                try:
                    audio_data = base64.b64decode(message.data.get("audio_data", ""))
                    
                    if message.data.get("is_final", False):
                        # Process complete audio
                        result = await stt_service.transcribe_audio(
                            audio_data=audio_data,
                            user_id=message.data.get("user_id")
                        )
                        
                        # Send transcription result
                        await manager.send_message(session_id, {
                            "type": "transcription_result",
                            "data": result,
                            "session_id": session_id,
                            "timestamp": time.time()
                        })
                    else:
                        # Send acknowledgment for chunk
                        await manager.send_message(session_id, {
                            "type": "chunk_received",
                            "data": {"chunk_id": message.data.get("chunk_id")},
                            "session_id": session_id,
                            "timestamp": time.time()
                        })
                        
                except Exception as e:
                    # Send error message
                    await manager.send_message(session_id, {
                        "type": "error",
                        "data": {
                            "error": str(e),
                            "error_code": "PROCESSING_ERROR"
                        },
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
            
            elif message.type == "tts_request":
                # Process TTS request
                try:
                    text = message.data.get("text", "")
                    user_id = message.data.get("user_id")
                    
                    audio_data, metadata = await tts_orchestrator.synthesize_speech(
                        text=text,
                        user_id=user_id
                    )
                    
                    # Send TTS result
                    await manager.send_message(session_id, {
                        "type": "tts_result",
                        "data": {
                            "audio_data": base64.b64encode(audio_data).decode(),
                            "metadata": metadata
                        },
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    # Send error message
                    await manager.send_message(session_id, {
                        "type": "error",
                        "data": {
                            "error": str(e),
                            "error_code": "TTS_ERROR"
                        },
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)


async def cleanup_temp_file(file_path: Path, delay: int = 3600):
    """Clean up temporary file after delay."""
    try:
        await asyncio.sleep(delay)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to clean up temporary file {file_path}: {e}")