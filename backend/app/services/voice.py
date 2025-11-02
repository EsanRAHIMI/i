"""
Voice processing services for STT and TTS functionality.
"""

import asyncio
import io
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import uuid
import base64
import os

import torch
import whisper
import librosa
import soundfile as sf
import noisereduce as nr
import numpy as np
from pydub import AudioSegment
import webrtcvad
from TTS.api import TTS
from elevenlabs import generate, Voice, VoiceSettings
import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AudioProcessor:
    """Audio preprocessing and enhancement utilities."""
    
    def __init__(self):
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2
        self.sample_rate = 16000  # Whisper's expected sample rate
        
    def preprocess_audio(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """
        Preprocess audio data for optimal STT performance.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Tuple of (processed_audio_array, sample_rate)
        """
        try:
            # Convert bytes to AudioSegment
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to mono and resample to 16kHz
            audio_segment = audio_segment.set_channels(1).set_frame_rate(self.sample_rate)
            
            # Convert to numpy array
            audio_array = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
            audio_array = audio_array / np.max(np.abs(audio_array))  # Normalize
            
            # Apply noise reduction
            audio_array = nr.reduce_noise(y=audio_array, sr=self.sample_rate)
            
            # Apply VAD to remove silence
            audio_array = self._apply_vad(audio_array)
            
            return audio_array, self.sample_rate
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            raise
    
    def _apply_vad(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply Voice Activity Detection to remove silence."""
        try:
            # Convert to 16-bit PCM for VAD
            pcm_data = (audio_array * 32767).astype(np.int16).tobytes()
            
            # Process in 30ms frames (480 samples at 16kHz)
            frame_duration = 30  # ms
            frame_size = int(self.sample_rate * frame_duration / 1000)
            
            voiced_frames = []
            for i in range(0, len(audio_array), frame_size):
                frame = audio_array[i:i + frame_size]
                if len(frame) < frame_size:
                    # Pad the last frame
                    frame = np.pad(frame, (0, frame_size - len(frame)))
                
                frame_bytes = (frame * 32767).astype(np.int16).tobytes()
                
                # Check if frame contains speech
                if self.vad.is_speech(frame_bytes, self.sample_rate):
                    voiced_frames.extend(frame)
            
            return np.array(voiced_frames, dtype=np.float32) if voiced_frames else audio_array
            
        except Exception as e:
            logger.warning(f"VAD processing failed, using original audio: {e}")
            return audio_array


class WhisperSTTService:
    """Whisper Speech-to-Text service with offline capabilities."""
    
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        self.audio_processor = AudioProcessor()
        self.offline_buffer = []
        self._model_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the Whisper model."""
        async with self._model_lock:
            if self.model is None:
                logger.info(f"Loading Whisper model: {self.model_size}")
                # Run model loading in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, whisper.load_model, self.model_size
                )
                logger.info("Whisper model loaded successfully")
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text using Whisper.
        
        Args:
            audio_data: Raw audio bytes
            language: Optional language hint (e.g., 'en', 'fa')
            user_id: User ID for offline buffering
            
        Returns:
            Dictionary with transcription results
        """
        start_time = time.time()
        
        try:
            # Ensure model is loaded
            await self.initialize()
            
            # Preprocess audio
            audio_array, sample_rate = self.audio_processor.preprocess_audio(audio_data)
            
            # Create temporary file for Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                sf.write(temp_file.name, audio_array, sample_rate)
                temp_path = temp_file.name
            
            try:
                # Run transcription in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self._transcribe_file, 
                    temp_path, 
                    language
                )
                
                processing_time = time.time() - start_time
                
                # Calculate confidence score based on Whisper's internal metrics
                confidence = self._calculate_confidence(result)
                
                transcription_result = {
                    "text": result["text"].strip(),
                    "language": result.get("language", "unknown"),
                    "confidence": confidence,
                    "processing_time": processing_time,
                    "segments": result.get("segments", []),
                    "user_id": user_id,
                    "timestamp": time.time()
                }
                
                logger.info(f"Transcription completed in {processing_time:.2f}s: {result['text'][:50]}...")
                return transcription_result
                
            finally:
                # Clean up temporary file
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            
            # Add to offline buffer if user_id provided
            if user_id:
                await self._buffer_offline_audio(audio_data, user_id)
            
            raise
    
    def _transcribe_file(self, file_path: str, language: Optional[str] = None) -> Dict:
        """Synchronous transcription method for thread pool execution."""
        options = {
            "fp16": torch.cuda.is_available(),
            "language": language,
            "task": "transcribe"
        }
        
        return self.model.transcribe(file_path, **options)
    
    def _calculate_confidence(self, whisper_result: Dict) -> float:
        """Calculate confidence score from Whisper result."""
        try:
            if "segments" in whisper_result and whisper_result["segments"]:
                # Average confidence from segments
                confidences = []
                for segment in whisper_result["segments"]:
                    if "avg_logprob" in segment:
                        # Convert log probability to confidence (0-1)
                        confidence = np.exp(segment["avg_logprob"])
                        confidences.append(confidence)
                
                if confidences:
                    return float(np.mean(confidences))
            
            # Fallback: estimate based on text length and no_speech_prob
            text_length = len(whisper_result.get("text", "").strip())
            if text_length == 0:
                return 0.0
            
            # Simple heuristic: longer text generally means better recognition
            base_confidence = min(0.9, 0.5 + (text_length / 100))
            
            return base_confidence
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {e}")
            return 0.5  # Default moderate confidence
    
    async def _buffer_offline_audio(self, audio_data: bytes, user_id: str):
        """Buffer audio for offline processing."""
        try:
            buffer_entry = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "audio_data": audio_data,
                "timestamp": time.time(),
                "processed": False
            }
            
            self.offline_buffer.append(buffer_entry)
            logger.info(f"Audio buffered for offline processing: user {user_id}")
            
            # Limit buffer size to prevent memory issues
            if len(self.offline_buffer) > 100:
                self.offline_buffer = self.offline_buffer[-50:]  # Keep last 50
                
        except Exception as e:
            logger.error(f"Failed to buffer offline audio: {e}")
    
    async def process_offline_buffer(self) -> int:
        """Process buffered audio when connectivity is restored."""
        processed_count = 0
        
        try:
            unprocessed = [entry for entry in self.offline_buffer if not entry["processed"]]
            
            for entry in unprocessed:
                try:
                    result = await self.transcribe_audio(
                        entry["audio_data"], 
                        user_id=entry["user_id"]
                    )
                    
                    entry["processed"] = True
                    entry["result"] = result
                    processed_count += 1
                    
                    logger.info(f"Processed offline audio for user {entry['user_id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to process offline audio {entry['id']}: {e}")
            
            # Clean up old processed entries
            current_time = time.time()
            self.offline_buffer = [
                entry for entry in self.offline_buffer 
                if current_time - entry["timestamp"] < 3600  # Keep for 1 hour
            ]
            
        except Exception as e:
            logger.error(f"Offline buffer processing failed: {e}")
        
        return processed_count
    
    async def get_buffer_status(self) -> Dict[str, Any]:
        """Get status of offline buffer."""
        unprocessed = len([entry for entry in self.offline_buffer if not entry["processed"]])
        total = len(self.offline_buffer)
        
        return {
            "total_buffered": total,
            "unprocessed": unprocessed,
            "processed": total - unprocessed
        }


class VoiceProfile:
    """User voice profile for personalized TTS."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.voice_characteristics = {}
        self.elevenlabs_voice_id = None
        self.coqui_speaker_embedding = None
        
    def update_characteristics(self, characteristics: Dict[str, Any]):
        """Update voice characteristics from user samples."""
        self.voice_characteristics.update(characteristics)
        
    def get_coqui_settings(self) -> Dict[str, Any]:
        """Get Coqui TTS settings for this profile."""
        return {
            "speaker_embedding": self.coqui_speaker_embedding,
            "speed": self.voice_characteristics.get("speed", 1.0),
            "pitch": self.voice_characteristics.get("pitch", 0.0)
        }
        
    def get_elevenlabs_settings(self) -> VoiceSettings:
        """Get ElevenLabs settings for this profile."""
        return VoiceSettings(
            stability=self.voice_characteristics.get("stability", 0.75),
            similarity_boost=self.voice_characteristics.get("similarity_boost", 0.75),
            style=self.voice_characteristics.get("style", 0.0),
            use_speaker_boost=self.voice_characteristics.get("use_speaker_boost", True)
        )


class CoquiTTSService:
    """Coqui TTS service for local voice synthesis."""
    
    def __init__(self):
        self.model = None
        self.model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self._model_lock = asyncio.Lock()
        self.voice_profiles = {}
        
    async def initialize(self):
        """Initialize the Coqui TTS model."""
        async with self._model_lock:
            if self.model is None:
                logger.info(f"Loading Coqui TTS model: {self.model_name}")
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, TTS, self.model_name
                )
                logger.info("Coqui TTS model loaded successfully")
    
    async def synthesize_speech(
        self, 
        text: str, 
        user_id: str,
        language: str = "en",
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Synthesize speech from text using Coqui TTS.
        
        Args:
            text: Text to synthesize
            user_id: User ID for voice profile
            language: Language code (en, fa, etc.)
            output_path: Optional output file path
            
        Returns:
            Audio data as bytes
        """
        start_time = time.time()
        
        try:
            await self.initialize()
            
            # Get or create voice profile
            voice_profile = self._get_voice_profile(user_id)
            
            # Create temporary output file if not provided
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                output_path = temp_file.name
                temp_file.close()
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._synthesize_file,
                text,
                output_path,
                language,
                voice_profile
            )
            
            # Read audio data
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            # Clean up temporary file
            if output_path.startswith(tempfile.gettempdir()):
                Path(output_path).unlink(missing_ok=True)
            
            processing_time = time.time() - start_time
            logger.info(f"Coqui TTS synthesis completed in {processing_time:.2f}s")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Coqui TTS synthesis failed: {e}")
            raise
    
    def _synthesize_file(
        self, 
        text: str, 
        output_path: str, 
        language: str,
        voice_profile: VoiceProfile
    ):
        """Synchronous synthesis method for thread pool execution."""
        settings = voice_profile.get_coqui_settings()
        
        # Use default speaker if no custom embedding
        speaker_wav = settings.get("speaker_embedding")
        
        self.model.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=speaker_wav,
            language=language,
            speed=settings.get("speed", 1.0)
        )
    
    def _get_voice_profile(self, user_id: str) -> VoiceProfile:
        """Get or create voice profile for user."""
        if user_id not in self.voice_profiles:
            self.voice_profiles[user_id] = VoiceProfile(user_id)
        return self.voice_profiles[user_id]
    
    async def create_voice_profile(
        self, 
        user_id: str, 
        sample_audio_path: str,
        characteristics: Optional[Dict[str, Any]] = None
    ):
        """Create personalized voice profile from user sample."""
        try:
            voice_profile = self._get_voice_profile(user_id)
            voice_profile.coqui_speaker_embedding = sample_audio_path
            
            if characteristics:
                voice_profile.update_characteristics(characteristics)
            
            logger.info(f"Voice profile created for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create voice profile for user {user_id}: {e}")
            raise


class ElevenLabsTTSService:
    """ElevenLabs TTS service for enhanced voice quality."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'ELEVENLABS_API_KEY', None)
        self.voice_profiles = {}
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        
    async def synthesize_speech(
        self, 
        text: str, 
        user_id: str,
        voice_id: Optional[str] = None
    ) -> bytes:
        """
        Synthesize speech using ElevenLabs API.
        
        Args:
            text: Text to synthesize
            user_id: User ID for voice profile
            voice_id: Optional specific voice ID
            
        Returns:
            Audio data as bytes
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        start_time = time.time()
        
        try:
            # Get voice profile and settings
            voice_profile = self._get_voice_profile(user_id)
            voice_settings = voice_profile.get_elevenlabs_settings()
            
            # Use custom voice ID or profile voice ID or default
            target_voice_id = (
                voice_id or 
                voice_profile.elevenlabs_voice_id or 
                self.default_voice_id
            )
            
            # Run synthesis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                self._synthesize_with_elevenlabs,
                text,
                target_voice_id,
                voice_settings
            )
            
            processing_time = time.time() - start_time
            logger.info(f"ElevenLabs TTS synthesis completed in {processing_time:.2f}s")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS synthesis failed: {e}")
            raise
    
    def _synthesize_with_elevenlabs(
        self, 
        text: str, 
        voice_id: str,
        voice_settings: VoiceSettings
    ) -> bytes:
        """Synchronous ElevenLabs synthesis for thread pool execution."""
        audio = generate(
            text=text,
            voice=Voice(
                voice_id=voice_id,
                settings=voice_settings
            ),
            api_key=self.api_key
        )
        return audio
    
    def _get_voice_profile(self, user_id: str) -> VoiceProfile:
        """Get or create voice profile for user."""
        if user_id not in self.voice_profiles:
            self.voice_profiles[user_id] = VoiceProfile(user_id)
        return self.voice_profiles[user_id]
    
    async def clone_voice(
        self, 
        user_id: str, 
        name: str,
        sample_files: List[str],
        description: Optional[str] = None
    ) -> str:
        """
        Clone user voice using ElevenLabs voice cloning.
        
        Args:
            user_id: User ID
            name: Voice name
            sample_files: List of sample audio file paths
            description: Optional voice description
            
        Returns:
            Voice ID of cloned voice
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        try:
            # This would require ElevenLabs voice cloning API
            # For now, we'll store the intent and return a placeholder
            voice_profile = self._get_voice_profile(user_id)
            
            # In a real implementation, you would:
            # 1. Upload sample files to ElevenLabs
            # 2. Create voice clone
            # 3. Store the returned voice_id
            
            # Placeholder implementation
            cloned_voice_id = f"cloned_{user_id}_{int(time.time())}"
            voice_profile.elevenlabs_voice_id = cloned_voice_id
            
            logger.info(f"Voice cloned for user {user_id}: {cloned_voice_id}")
            return cloned_voice_id
            
        except Exception as e:
            logger.error(f"Voice cloning failed for user {user_id}: {e}")
            raise


class TTSOrchestrator:
    """Orchestrates TTS services with fallback logic."""
    
    def __init__(self):
        self.coqui_service = CoquiTTSService()
        self.elevenlabs_service = ElevenLabsTTSService()
        self.use_elevenlabs_fallback = True
        
    async def synthesize_speech(
        self, 
        text: str, 
        user_id: str,
        language: str = "en",
        prefer_quality: bool = False
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Synthesize speech with automatic fallback.
        
        Args:
            text: Text to synthesize
            user_id: User ID for personalization
            language: Language code
            prefer_quality: If True, prefer ElevenLabs over Coqui
            
        Returns:
            Tuple of (audio_data, metadata)
        """
        start_time = time.time()
        metadata = {
            "user_id": user_id,
            "text_length": len(text),
            "language": language,
            "timestamp": time.time()
        }
        
        # Determine primary and fallback services
        if prefer_quality and self.elevenlabs_service.api_key:
            primary_service = "elevenlabs"
            fallback_service = "coqui"
        else:
            primary_service = "coqui"
            fallback_service = "elevenlabs" if self.use_elevenlabs_fallback else None
        
        # Try primary service
        try:
            if primary_service == "coqui":
                audio_data = await self.coqui_service.synthesize_speech(
                    text, user_id, language
                )
            else:
                audio_data = await self.elevenlabs_service.synthesize_speech(
                    text, user_id
                )
            
            metadata.update({
                "service_used": primary_service,
                "processing_time": time.time() - start_time,
                "fallback_used": False
            })
            
            return audio_data, metadata
            
        except Exception as e:
            logger.warning(f"Primary TTS service ({primary_service}) failed: {e}")
            
            # Try fallback service
            if fallback_service:
                try:
                    if fallback_service == "coqui":
                        audio_data = await self.coqui_service.synthesize_speech(
                            text, user_id, language
                        )
                    else:
                        audio_data = await self.elevenlabs_service.synthesize_speech(
                            text, user_id
                        )
                    
                    metadata.update({
                        "service_used": fallback_service,
                        "processing_time": time.time() - start_time,
                        "fallback_used": True,
                        "primary_error": str(e)
                    })
                    
                    return audio_data, metadata
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback TTS service ({fallback_service}) also failed: {fallback_error}")
                    metadata["fallback_error"] = str(fallback_error)
            
            # Both services failed
            metadata.update({
                "service_used": None,
                "processing_time": time.time() - start_time,
                "fallback_used": True,
                "error": str(e)
            })
            
            raise Exception(f"All TTS services failed. Primary: {e}")


# Global service instances
stt_service = WhisperSTTService(model_size=getattr(settings, 'WHISPER_MODEL_SIZE', 'base'))
tts_orchestrator = TTSOrchestrator()