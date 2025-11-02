"""
Unit tests for voice processing services and API endpoints.
"""

import asyncio
import base64
import io
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Only import numpy and pydub if available
try:
    import numpy as np
    from pydub import AudioSegment
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    np = None
    AudioSegment = None

from app.services.voice import (
    VoiceProfile, WhisperSTTService, CoquiTTSService, 
    ElevenLabsTTSService, TTSOrchestrator
)
from app.schemas.voice import VoiceInputRequest, TTSRequest


@pytest.mark.skipif(not AUDIO_LIBS_AVAILABLE, reason="Audio processing libraries not available")
class TestAudioProcessor:
    """Test AudioProcessor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from app.services.voice import AudioProcessor
        self.processor = AudioProcessor()
        
    def create_test_audio(self, duration_ms=1000, frequency=440):
        """Create test audio data."""
        # Generate sine wave
        sample_rate = 16000
        samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples, False)
        audio_array = np.sin(2 * np.pi * frequency * t)
        
        # Convert to AudioSegment
        audio_segment = AudioSegment(
            audio_array.tobytes(), 
            frame_rate=sample_rate,
            sample_width=audio_array.dtype.itemsize,
            channels=1
        )
        
        # Export to bytes
        buffer = io.BytesIO()
        audio_segment.export(buffer, format="wav")
        return buffer.getvalue()
    
    def test_preprocess_audio_basic(self):
        """Test basic audio preprocessing."""
        audio_data = self.create_test_audio(duration_ms=2000)
        
        processed_audio, sample_rate = self.processor.preprocess_audio(audio_data)
        
        assert isinstance(processed_audio, np.ndarray)
        assert sample_rate == 16000
        assert len(processed_audio) > 0
        assert np.max(np.abs(processed_audio)) <= 1.0  # Normalized
    
    def test_preprocess_audio_empty(self):
        """Test preprocessing with empty audio."""
        with pytest.raises(Exception):
            self.processor.preprocess_audio(b"")
    
    def test_preprocess_audio_invalid_format(self):
        """Test preprocessing with invalid audio format."""
        with pytest.raises(Exception):
            self.processor.preprocess_audio(b"invalid audio data")


class TestWhisperSTTService:
    """Test WhisperSTTService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.stt_service = WhisperSTTService(model_size="tiny")  # Use smallest model for tests
        
    def create_test_audio_bytes(self):
        """Create test audio bytes."""
        # Return mock audio data for testing
        return b"fake_audio_data_for_testing"
    
    @pytest.mark.asyncio
    async def test_initialize_model(self):
        """Test Whisper model initialization."""
        await self.stt_service.initialize()
        assert self.stt_service.model is not None
    
    @pytest.mark.asyncio
    @patch('whisper.load_model')
    async def test_transcribe_audio_success(self, mock_load_model):
        """Test successful audio transcription."""
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Hello, this is a test.",
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Hello, this is a test.",
                    "avg_logprob": -0.1
                }
            ]
        }
        mock_load_model.return_value = mock_model
        
        # Create test audio
        audio_data = self.create_test_audio_bytes()
        
        # Test transcription
        result = await self.stt_service.transcribe_audio(
            audio_data=audio_data,
            language="en",
            user_id="test_user"
        )
        
        # Verify result
        assert result["text"] == "Hello, this is a test."
        assert result["language"] == "en"
        assert result["confidence"] > 0
        assert result["processing_time"] > 0
        assert result["user_id"] == "test_user"
        assert len(result["segments"]) == 1
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_empty(self):
        """Test transcription with empty audio."""
        with pytest.raises(Exception):
            await self.stt_service.transcribe_audio(b"", user_id="test_user")
    
    @pytest.mark.asyncio
    async def test_offline_buffer_functionality(self):
        """Test offline audio buffering."""
        audio_data = self.create_test_audio_bytes()
        user_id = "test_user"
        
        # Buffer audio
        await self.stt_service._buffer_offline_audio(audio_data, user_id)
        
        # Check buffer status
        status = await self.stt_service.get_buffer_status()
        assert status["total_buffered"] >= 1
        assert status["unprocessed"] >= 1
    
    def test_calculate_confidence_with_segments(self):
        """Test confidence calculation from segments."""
        whisper_result = {
            "text": "Test text",
            "segments": [
                {"avg_logprob": -0.1},
                {"avg_logprob": -0.2}
            ]
        }
        
        confidence = self.stt_service._calculate_confidence(whisper_result)
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # Should be reasonably high for good log probs
    
    def test_calculate_confidence_without_segments(self):
        """Test confidence calculation without segments."""
        whisper_result = {"text": "Test text with reasonable length"}
        
        confidence = self.stt_service._calculate_confidence(whisper_result)
        assert 0 <= confidence <= 1


class TestVoiceProfile:
    """Test VoiceProfile functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.profile = VoiceProfile("test_user")
    
    def test_voice_profile_initialization(self):
        """Test voice profile initialization."""
        assert self.profile.user_id == "test_user"
        assert self.profile.voice_characteristics == {}
        assert self.profile.elevenlabs_voice_id is None
        assert self.profile.coqui_speaker_embedding is None
    
    def test_update_characteristics(self):
        """Test updating voice characteristics."""
        characteristics = {
            "speed": 1.2,
            "pitch": 0.1,
            "stability": 0.8
        }
        
        self.profile.update_characteristics(characteristics)
        
        assert self.profile.voice_characteristics["speed"] == 1.2
        assert self.profile.voice_characteristics["pitch"] == 0.1
        assert self.profile.voice_characteristics["stability"] == 0.8
    
    def test_get_coqui_settings(self):
        """Test getting Coqui TTS settings."""
        self.profile.update_characteristics({"speed": 1.5, "pitch": 0.2})
        
        settings = self.profile.get_coqui_settings()
        
        assert settings["speed"] == 1.5
        assert settings["pitch"] == 0.2
        assert "speaker_embedding" in settings
    
    def test_get_elevenlabs_settings(self):
        """Test getting ElevenLabs settings."""
        self.profile.update_characteristics({
            "stability": 0.9,
            "similarity_boost": 0.8,
            "style": 0.1
        })
        
        settings = self.profile.get_elevenlabs_settings()
        
        assert settings.stability == 0.9
        assert settings.similarity_boost == 0.8
        assert settings.style == 0.1


class TestCoquiTTSService:
    """Test CoquiTTSService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tts_service = CoquiTTSService()
    
    @pytest.mark.asyncio
    @patch('TTS.api.TTS')
    async def test_initialize_model(self, mock_tts_class):
        """Test Coqui TTS model initialization."""
        mock_model = Mock()
        mock_tts_class.return_value = mock_model
        
        await self.tts_service.initialize()
        
        assert self.tts_service.model == mock_model
        mock_tts_class.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('TTS.api.TTS')
    async def test_synthesize_speech_success(self, mock_tts_class):
        """Test successful speech synthesis."""
        # Mock TTS model
        mock_model = Mock()
        mock_model.tts_to_file = Mock()
        mock_tts_class.return_value = mock_model
        
        # Create mock audio file
        test_audio_data = b"fake_audio_data"
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = test_audio_data
            
            result = await self.tts_service.synthesize_speech(
                text="Hello world",
                user_id="test_user",
                language="en"
            )
        
        assert result == test_audio_data
        mock_model.tts_to_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_voice_profile(self):
        """Test voice profile creation."""
        user_id = "test_user"
        sample_path = "/path/to/sample.wav"
        characteristics = {"speed": 1.1, "pitch": 0.05}
        
        await self.tts_service.create_voice_profile(
            user_id=user_id,
            sample_audio_path=sample_path,
            characteristics=characteristics
        )
        
        # Verify profile was created
        assert user_id in self.tts_service.voice_profiles
        profile = self.tts_service.voice_profiles[user_id]
        assert profile.coqui_speaker_embedding == sample_path
        assert profile.voice_characteristics["speed"] == 1.1


class TestElevenLabsTTSService:
    """Test ElevenLabsTTSService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tts_service = ElevenLabsTTSService()
        self.tts_service.api_key = "test_api_key"  # Mock API key
    
    @pytest.mark.asyncio
    @patch('elevenlabs.generate')
    async def test_synthesize_speech_success(self, mock_generate):
        """Test successful ElevenLabs synthesis."""
        mock_audio_data = b"fake_elevenlabs_audio"
        mock_generate.return_value = mock_audio_data
        
        result = await self.tts_service.synthesize_speech(
            text="Hello from ElevenLabs",
            user_id="test_user"
        )
        
        assert result == mock_audio_data
        mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_no_api_key(self):
        """Test synthesis without API key."""
        self.tts_service.api_key = None
        
        with pytest.raises(ValueError, match="ElevenLabs API key not configured"):
            await self.tts_service.synthesize_speech(
                text="Hello",
                user_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_clone_voice(self):
        """Test voice cloning functionality."""
        user_id = "test_user"
        name = "Test Voice"
        sample_files = ["/path/to/sample1.wav", "/path/to/sample2.wav"]
        
        voice_id = await self.tts_service.clone_voice(
            user_id=user_id,
            name=name,
            sample_files=sample_files
        )
        
        # Verify voice was cloned (placeholder implementation)
        assert voice_id.startswith("cloned_")
        assert user_id in self.tts_service.voice_profiles
        profile = self.tts_service.voice_profiles[user_id]
        assert profile.elevenlabs_voice_id == voice_id


class TestTTSOrchestrator:
    """Test TTSOrchestrator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = TTSOrchestrator()
    
    @pytest.mark.asyncio
    @patch.object(CoquiTTSService, 'synthesize_speech')
    async def test_synthesize_speech_coqui_primary(self, mock_coqui_synth):
        """Test synthesis with Coqui as primary service."""
        mock_audio_data = b"coqui_audio_data"
        mock_coqui_synth.return_value = mock_audio_data
        
        audio_data, metadata = await self.orchestrator.synthesize_speech(
            text="Test text",
            user_id="test_user",
            prefer_quality=False
        )
        
        assert audio_data == mock_audio_data
        assert metadata["service_used"] == "coqui"
        assert metadata["fallback_used"] is False
        mock_coqui_synth.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(ElevenLabsTTSService, 'synthesize_speech')
    @patch.object(CoquiTTSService, 'synthesize_speech')
    async def test_synthesize_speech_with_fallback(self, mock_coqui_synth, mock_elevenlabs_synth):
        """Test synthesis with fallback when primary fails."""
        # Make Coqui fail
        mock_coqui_synth.side_effect = Exception("Coqui failed")
        
        # Make ElevenLabs succeed
        mock_audio_data = b"elevenlabs_fallback_audio"
        mock_elevenlabs_synth.return_value = mock_audio_data
        
        # Set API key to enable ElevenLabs
        self.orchestrator.elevenlabs_service.api_key = "test_key"
        
        audio_data, metadata = await self.orchestrator.synthesize_speech(
            text="Test text",
            user_id="test_user",
            prefer_quality=False
        )
        
        assert audio_data == mock_audio_data
        assert metadata["service_used"] == "elevenlabs"
        assert metadata["fallback_used"] is True
        assert "primary_error" in metadata
    
    @pytest.mark.asyncio
    @patch.object(ElevenLabsTTSService, 'synthesize_speech')
    @patch.object(CoquiTTSService, 'synthesize_speech')
    async def test_synthesize_speech_all_fail(self, mock_coqui_synth, mock_elevenlabs_synth):
        """Test synthesis when all services fail."""
        # Make both services fail
        mock_coqui_synth.side_effect = Exception("Coqui failed")
        mock_elevenlabs_synth.side_effect = Exception("ElevenLabs failed")
        
        # Set API key to enable ElevenLabs
        self.orchestrator.elevenlabs_service.api_key = "test_key"
        
        with pytest.raises(Exception, match="All TTS services failed"):
            await self.orchestrator.synthesize_speech(
                text="Test text",
                user_id="test_user"
            )


class TestVoiceProcessingPerformance:
    """Test voice processing performance requirements."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.stt_service = WhisperSTTService(model_size="tiny")
        self.orchestrator = TTSOrchestrator()
    
    @pytest.mark.asyncio
    @patch('whisper.load_model')
    async def test_stt_latency_requirement(self, mock_load_model):
        """Test STT processing meets 2-second latency requirement."""
        # Mock Whisper model for fast response
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Quick test",
            "language": "en",
            "segments": []
        }
        mock_load_model.return_value = mock_model
        
        # Create small test audio
        audio_data = b"fake_audio_data"
        
        start_time = time.time()
        
        with patch.object(self.stt_service.audio_processor, 'preprocess_audio') as mock_preprocess:
            if AUDIO_LIBS_AVAILABLE:
                mock_preprocess.return_value = (np.array([0.1, 0.2, 0.3]), 16000)
            else:
                mock_preprocess.return_value = ([0.1, 0.2, 0.3], 16000)
            
            result = await self.stt_service.transcribe_audio(
                audio_data=audio_data,
                user_id="test_user"
            )
        
        processing_time = time.time() - start_time
        
        # Verify latency requirement (should be well under 2 seconds for mocked processing)
        assert processing_time < 2.0
        assert result["processing_time"] < 2.0
    
    @pytest.mark.asyncio
    @patch.object(CoquiTTSService, 'synthesize_speech')
    async def test_tts_latency_requirement(self, mock_coqui_synth):
        """Test TTS processing meets 2-second latency requirement."""
        # Mock fast TTS response
        mock_coqui_synth.return_value = b"fast_audio_data"
        
        start_time = time.time()
        
        audio_data, metadata = await self.orchestrator.synthesize_speech(
            text="Short test message",
            user_id="test_user"
        )
        
        processing_time = time.time() - start_time
        
        # Verify latency requirement
        assert processing_time < 2.0
        assert metadata["processing_time"] < 2.0
    
    @pytest.mark.skipif(not AUDIO_LIBS_AVAILABLE, reason="Audio processing libraries not available")
    def test_audio_quality_metrics(self):
        """Test audio quality and accuracy metrics."""
        from app.services.voice import AudioProcessor
        processor = AudioProcessor()
        
        # Create test audio with known characteristics
        sample_rate = 16000
        duration = 2.0
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        original_audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        # Convert to bytes and back through processor
        audio_segment = AudioSegment(
            original_audio.tobytes(),
            frame_rate=sample_rate,
            sample_width=original_audio.dtype.itemsize,
            channels=1
        )
        
        buffer = io.BytesIO()
        audio_segment.export(buffer, format="wav")
        audio_bytes = buffer.getvalue()
        
        processed_audio, processed_sr = processor.preprocess_audio(audio_bytes)
        
        # Verify audio quality preservation
        assert processed_sr == sample_rate
        assert len(processed_audio) > 0
        
        # Check that audio is properly normalized
        assert np.max(np.abs(processed_audio)) <= 1.0
        
        # Verify noise reduction didn't destroy the signal
        # (For a clean sine wave, most energy should be preserved)
        original_energy = np.sum(original_audio ** 2)
        processed_energy = np.sum(processed_audio ** 2)
        
        # Allow some energy loss due to processing, but not too much
        energy_ratio = processed_energy / original_energy
        assert 0.5 < energy_ratio <= 1.0  # At least 50% energy preserved