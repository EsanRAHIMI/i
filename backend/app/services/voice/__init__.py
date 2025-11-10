# backend/app/services/voice/__init__.py
"""
Voice service initialization - Mock services for testing
"""
import logging

logger = logging.getLogger(__name__)

class MockSTTService:
    """Mock STT service for testing"""
    
    async def transcribe_audio(self, audio_data: bytes, language: str = None, user_id: str = None):
        """Mock transcription"""
        return {
            "text": "Mock transcription result",
            "language": language or "en",
            "confidence": 0.95,
            "processing_time": 0.5,
            "segments": [],
            "user_id": user_id,
            "timestamp": 0.0
        }
    
    async def get_buffer_status(self):
        """Mock buffer status"""
        return {
            "total_buffered": 0,
            "unprocessed": 0,
            "processed": 0
        }
    
    async def process_offline_buffer(self):
        """Mock buffer processing"""
        return 0

class MockTTSOrchestrator:
    """Mock TTS orchestrator for testing"""
    
    async def synthesize_speech(self, text: str, user_id: str = None, 
                                language: str = "en", prefer_quality: bool = False):
        """Mock speech synthesis"""
        # Return empty audio data for now
        audio_data = b"RIFF" + b"\x00" * 40  # Minimal WAV header
        metadata = {
            "service_used": "mock",
            "processing_time": 0.3,
            "fallback_used": False,
            "text_length": len(text),
            "language": language
        }
        return audio_data, metadata
    
    @property
    def coqui_service(self):
        """Mock coqui service"""
        return MockCoquiService()
    
    @property
    def elevenlabs_service(self):
        """Mock elevenlabs service"""
        return MockElevenLabsService()

class MockCoquiService:
    """Mock Coqui service"""
    async def create_voice_profile(self, user_id, sample_audio_path, characteristics):
        return {"status": "created"}

class MockElevenLabsService:
    """Mock ElevenLabs service"""
    api_key = None
    
    async def clone_voice(self, user_id, name, sample_files):
        return "mock_voice_id"

# Initialize mock services
stt_service = MockSTTService()
tts_orchestrator = MockTTSOrchestrator()

logger.info("✅ Mock voice services initialized")