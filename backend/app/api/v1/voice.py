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
import jwt
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer

from ...services.voice import stt_service, tts_orchestrator
from ...schemas.voice import (
    VoiceInputRequest, TranscriptionResponse, TTSRequest, TTSResponse,
    VoiceProfileRequest, VoiceProfileResponse, BufferStatusResponse,
    WebSocketMessage, ErrorResponse
)
from ...middleware.auth import get_current_user
from ...config import get_settings, settings
from ...services.auth import auth_service

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
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}  # Store user_id, last_ping, etc.
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
        await websocket.accept()
        connected_at = time.time()
        self.active_connections[session_id] = websocket
        self.connection_metadata[session_id] = {
            "user_id": user_id,
            "last_ping": connected_at,
            "connected_at": connected_at,
            "client_ip": websocket.client.host if websocket.client else None
        }
        client_ip = websocket.client.host if websocket.client else None
        active_conns = self.get_active_connections_count()
        logger.info(
            f"WebSocket connected - session_id={session_id}, user_id={user_id}, client_ip={client_ip}, active_connections={active_conns}"
        )
    
    def disconnect(self, session_id: str, close_code: Optional[int] = None, reason: Optional[str] = None):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.connection_metadata:
            metadata = self.connection_metadata[session_id]
            duration = time.time() - metadata.get("connected_at", time.time())
            user_id_log = metadata.get("user_id")
            client_ip_log = metadata.get("client_ip")
            duration_log = round(duration, 2)
            active_conns = self.get_active_connections_count()
            logger.info(
                f"WebSocket disconnected - session_id={session_id}, user_id={user_id_log}, client_ip={client_ip_log}, "
                f"duration_seconds={duration_log}, close_code={close_code}, reason={reason}, active_connections={active_conns}"
            )
            del self.connection_metadata[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message to {session_id}: {e}")
                self.disconnect(session_id)
    
    def update_last_ping(self, session_id: str):
        """Update last ping time for heartbeat."""
        if session_id in self.connection_metadata:
            self.connection_metadata[session_id]["last_ping"] = time.time()
    
    def get_active_connections_count(self) -> int:
        """Get count of active connections."""
        return len(self.active_connections)

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
async def voice_stream(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None, description="JWT token for authentication")
):
    """
    WebSocket endpoint for real-time voice streaming.
    
    - **session_id**: Unique session identifier
    - **token**: JWT token for authentication (optional but recommended)
    """
    # Validate token if provided (for direct access to /api/v1/voice/stream/{session_id})
    user_id = None
    if token:
        if not auth_service.public_key:
            logger.error("JWT public key is not available")
            await websocket.close(code=1011, reason="Authentication service unavailable")
            return
        
        try:
            payload = jwt.decode(
                token,
                auth_service.public_key,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            user_id = payload.get("sub")
            logger.info(
                f"WebSocket authentication successful - user_id={user_id}, session_id={session_id}, endpoint=voice/stream"
            )
        except jwt.ExpiredSignatureError:
            logger.warning(f"JWT token expired for WebSocket - session_id={session_id}")
            await websocket.close(code=1008, reason="Token expired")
            return
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token for WebSocket - session_id={session_id}, error={e}")
            await websocket.close(code=1008, reason="Invalid token")
            return
        except Exception as e:
            logger.error(f"JWT validation error for WebSocket - session_id={session_id}, error={e}", exc_info=True)
            await websocket.close(code=1011, reason="Authentication error")
            return
    
    # Call internal implementation
    await voice_stream_internal(websocket, session_id=session_id, user_id=user_id)


async def voice_stream_internal(
    websocket: WebSocket,
    session_id: str,
    user_id: Optional[str] = None
):
    """
    Internal WebSocket handler for voice streaming.
    This function is called by both /ws alias and /api/v1/voice/stream/{session_id}.
    
    - **websocket**: WebSocket connection
    - **session_id**: Unique session identifier
    - **user_id**: Authenticated user ID (if token was validated)
    """
    # Log connection attempt
    client_ip = websocket.client.host if websocket.client else None
    logger.info(
        f"WebSocket connection attempt - session_id={session_id}, user_id={user_id}, client_ip={client_ip}"
    )
    
    await manager.connect(websocket, session_id, user_id)
    
    # Heartbeat configuration (bidirectional)
    heartbeat_interval = 30  # seconds - send ping every 30s
    heartbeat_timeout = 60  # seconds - timeout if no pong for 60s
    last_ping_sent = time.time()
    last_pong_received = time.time()
    
    async def send_heartbeat():
        """Send ping to client periodically (bidirectional heartbeat)."""
        nonlocal last_ping_sent, last_pong_received
        try:
            await websocket.send_json({
                "type": "ping",
                "timestamp": time.time()
            })
            last_ping_sent = time.time()
            manager.update_last_ping(session_id)
            logger.debug(f"Heartbeat ping sent - session_id={session_id}")
        except Exception as e:
            logger.error(f"Failed to send heartbeat to {session_id}: {e}")
    
    try:
        # Send initial connection confirmation
        await manager.send_message(session_id, {
            "type": "connected",
            "session_id": session_id,
            "timestamp": time.time()
        })
        
        while True:
            # Check for heartbeat timeout (bidirectional)
            time_since_last_pong = time.time() - last_pong_received
            if time_since_last_pong > heartbeat_timeout:
                seconds_log = round(time_since_last_pong, 2)
                logger.warning(
                    f"Heartbeat timeout - session_id={session_id}, seconds_since_last_pong={seconds_log}"
                )
                await websocket.close(code=1000, reason="Heartbeat timeout")
                manager.disconnect(session_id, close_code=1000, reason="Heartbeat timeout")
                return
            
            # Use asyncio.wait_for to handle both messages and timeout
            try:
                # Wait for message with timeout to allow heartbeat checks
                try:
                    message_task = asyncio.create_task(websocket.receive_json())
                except (RuntimeError, WebSocketDisconnect):
                    # Already disconnected
                    break
                    
                timeout_task = asyncio.create_task(asyncio.sleep(heartbeat_interval))
                
                done, pending = await asyncio.wait(
                    [message_task, timeout_task],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=heartbeat_interval + 1  # Safety timeout
                )
                
                # Cancel pending task
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, RuntimeError, WebSocketDisconnect):
                        pass
                
                # If timeout completed, send heartbeat
                if timeout_task in done:
                    try:
                        await send_heartbeat()
                    except (RuntimeError, WebSocketDisconnect):
                        break
                    continue
                
                # If message received, process it
                if message_task in done:
                    try:
                        data = await message_task
                    except (RuntimeError, WebSocketDisconnect) as e:
                        # Client disconnected while waiting for message
                        break
                    
                    # Handle pong response (bidirectional heartbeat)
                    if isinstance(data, dict) and data.get("type") == "pong":
                        last_pong_received = time.time()
                        manager.update_last_ping(session_id)
                        logger.debug(f"Heartbeat pong received - session_id={session_id}")
                        continue
                    
                    try:
                        message = WebSocketMessage(**data)
                    except Exception as parse_error:
                        logger.error(f"Failed to parse message from {session_id}: {parse_error}")
                        await manager.send_message(session_id, {
                            "type": "error",
                            "data": {
                                "error": "Invalid message format",
                                "error_code": "PARSE_ERROR"
                            },
                            "session_id": session_id,
                            "timestamp": time.time()
                        })
                        continue
                    
                    # Process message based on type
                    if message.type == "audio_chunk":
                        # Process audio chunk
                        try:
                            audio_data = base64.b64decode(message.data.get("audio_data", ""))
                            
                            if message.data.get("is_final", False):
                                # Process complete audio
                                result = await stt_service.transcribe_audio(
                                    audio_data=audio_data,
                                    user_id=message.data.get("user_id") or user_id
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
                            message_user_id = message.data.get("user_id") or user_id
                            
                            audio_data, metadata = await tts_orchestrator.synthesize_speech(
                                text=text,
                                user_id=message_user_id
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
                    
                    elif message.type not in ["audio_chunk", "tts_request", "pong"]:
                        logger.warning(f"Unknown message type from {session_id}: {message.type}")
                
            except asyncio.CancelledError:
                # Task was cancelled (timeout or disconnect)
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message from {session_id}: {e}", exc_info=True)
            
    except WebSocketDisconnect as e:
        close_code = getattr(e, 'code', 1000)
        reason = getattr(e, 'reason', 'Client disconnected')
        logger.info(
            f"WebSocket disconnected by client - session_id={session_id}, close_code={close_code}, reason={reason}"
        )
        manager.disconnect(session_id, close_code=close_code, reason=reason)
    except Exception as e:
        logger.error(
            f"WebSocket error - session_id={session_id}, error={str(e)}, error_type={type(e).__name__}",
            exc_info=True
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        manager.disconnect(session_id, close_code=1011, reason="Internal server error")


async def cleanup_temp_file(file_path: Path, delay: int = 3600):
    """Clean up temporary file after delay."""
    try:
        await asyncio.sleep(delay)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to clean up temporary file {file_path}: {e}")