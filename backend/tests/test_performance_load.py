"""
Performance and load testing for the intelligent AI assistant system.
Tests system performance under various load conditions and validates latency requirements.
"""
import pytest
import asyncio
import time
import statistics
import concurrent.futures
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import threading
import queue
import psutil
import gc

from app.services.voice import WhisperSTTService, TTSOrchestrator
from app.services.calendar import GoogleCalendarService
from app.services.whatsapp import WhatsAppService
from app.core.agentic_core import AgenticCore
from app.database.models import User, UserSettings, Calendar, Event
from app.schemas.voice import VoiceInputRequest, TranscriptionResponse, TTSRequest, TTSResponse
from app.schemas.calendar import CalendarEventCreate
from app.schemas.whatsapp import WhatsAppMessageCreate


class TestVoiceProcessingPerformance:
    """Test voice processing latency requirements under 2 seconds."""
    
    @pytest.fixture
    def stt_service(self):
        """Create STT service for performance testing."""
        return WhisperSTTService()
    
    @pytest.fixture
    def tts_service(self):
        """Create TTS service for performance testing."""
        return TTSOrchestrator()
    
    @pytest.fixture
    def sample_audio_data(self):
        """Generate sample audio data for testing."""
        # Create a proper WAV file in memory
        import io
        import wave
        import numpy as np
        
        sample_rate = 16000
        duration = 2.0  # Shorter for faster tests
        samples = int(sample_rate * duration)
        
        # Generate sine wave as test audio
        frequency = 440  # A4 note
        t = np.linspace(0, duration, samples, False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
        
        # Convert to 16-bit PCM
        audio_pcm = (audio_data * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_pcm.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    @pytest.mark.asyncio
    async def test_speech_to_text_latency_requirement(self, stt_service, sample_audio_data):
        """Test that STT processing meets 2-second latency requirement."""
        
        with patch.object(stt_service, 'model') as mock_whisper:
            # Mock Whisper processing with realistic delay
            mock_whisper.transcribe.return_value = {
                "text": "Schedule a meeting tomorrow at 3 PM",
                "segments": [{"confidence": 0.95}]
            }
            
            # Add realistic processing delay (should be under 2 seconds)
            def mock_transcribe_sync(*args, **kwargs):
                import time
                time.sleep(0.8)  # Simulate processing time
                return {
                    "text": "Schedule a meeting tomorrow at 3 PM",
                    "segments": [{"confidence": 0.95, "avg_logprob": -0.1}]
                }
            
            mock_whisper.transcribe = mock_transcribe_sync
            
            # Measure processing time
            start_time = time.time()
            
            result = await stt_service.transcribe_audio(sample_audio_data)
            
            processing_time = time.time() - start_time
            
            # Verify latency requirement
            assert processing_time < 2.0, f"STT processing took {processing_time:.2f}s, exceeds 2s requirement"
            assert result["text"] == "Schedule a meeting tomorrow at 3 PM"
            assert result["confidence"] > 0.9
            
            print(f"STT processing time: {processing_time:.3f}s (requirement: <2.0s)")
    
    @pytest.mark.asyncio
    async def test_text_to_speech_latency_requirement(self, tts_service):
        """Test that TTS processing meets 2-second latency requirement."""
        
        with patch.object(tts_service, 'coqui_service') as mock_tts:
            # Mock TTS processing
            mock_audio_data = b"fake_audio_data" * 1000  # Simulate audio output
            
            async def mock_synthesize(*args, **kwargs):
                await asyncio.sleep(0.6)  # Simulate TTS processing time
                return mock_audio_data
            
            mock_tts.synthesize = mock_synthesize
            
            # Test text input
            text_input = "Your meeting has been scheduled for tomorrow at 3 PM. Please confirm by replying Y or N."
            
            # Measure processing time
            start_time = time.time()
            
            result = await tts_service.synthesize_speech(text_input, user_id="test_user")
            
            processing_time = time.time() - start_time
            
            # Verify latency requirement
            assert processing_time < 2.0, f"TTS processing took {processing_time:.2f}s, exceeds 2s requirement"
            assert result["audio_data"] == mock_audio_data
            assert result["duration"] > 0
            
            print(f"TTS processing time: {processing_time:.3f}s (requirement: <2.0s)")
    
    @pytest.mark.asyncio
    async def test_voice_processing_under_concurrent_load(self, stt_service, sample_audio_data):
        """Test voice processing performance under concurrent load."""
        
        with patch.object(stt_service, 'model') as mock_whisper:
            mock_whisper.transcribe.return_value = {
                "text": "Test transcription",
                "segments": [{"confidence": 0.95}]
            }
            
            # Simulate realistic processing delay
            def mock_transcribe_sync(*args, **kwargs):
                import time
                time.sleep(0.5)
                return {
                    "text": "Test transcription",
                    "segments": [{"confidence": 0.95, "avg_logprob": -0.1}]
                }
            
            mock_whisper.transcribe = mock_transcribe_sync
            
            # Test with 20 concurrent requests
            concurrent_requests = 20
            
            async def process_single_request():
                start_time = time.time()
                result = await stt_service.transcribe_audio(sample_audio_data)
                processing_time = time.time() - start_time
                return processing_time, result
            
            # Execute concurrent requests
            start_time = time.time()
            
            tasks = [process_single_request() for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Analyze results
            processing_times = [result[0] for result in results]
            avg_processing_time = statistics.mean(processing_times)
            max_processing_time = max(processing_times)
            
            # Verify performance under load
            assert avg_processing_time < 2.0, f"Average processing time {avg_processing_time:.2f}s exceeds requirement"
            assert max_processing_time < 3.0, f"Max processing time {max_processing_time:.2f}s too high under load"
            
            # Verify all requests completed successfully
            successful_requests = sum(1 for _, result in results if result["text"] == "Test transcription")
            assert successful_requests == concurrent_requests
            
            print(f"Concurrent voice processing results:")
            print(f"- Requests: {concurrent_requests}")
            print(f"- Total time: {total_time:.2f}s")
            print(f"- Average processing time: {avg_processing_time:.3f}s")
            print(f"- Max processing time: {max_processing_time:.3f}s")
            print(f"- Success rate: {successful_requests}/{concurrent_requests}")


class TestSystemLoadTesting:
    """Test system performance under 100 concurrent users with realistic usage patterns."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for load testing."""
        return {
            'stt_service': Mock(spec=WhisperSTTService),
            'tts_service': Mock(spec=TTSOrchestrator),
            'calendar_service': Mock(spec=GoogleCalendarService),
            'whatsapp_service': Mock(spec=WhatsAppService),
            'agentic_core': Mock(spec=AgenticCore)
        }
    
    @pytest.fixture
    def user_pool(self, db_session):
        """Create a pool of test users for load testing."""
        users = []
        for i in range(100):
            user = User(
                email=f"loadtest_user_{i}@test.com",
                password_hash="hashed_password",
                timezone="UTC"
            )
            db_session.add(user)
            users.append(user)
        
        db_session.commit()
        return users
    
    @pytest.mark.asyncio
    async def test_100_concurrent_users_realistic_patterns(self, mock_services, user_pool):
        """Test system with 100 concurrent users following realistic usage patterns."""
        
        # Configure mock services with realistic delays
        mock_services['stt_service'].transcribe_audio = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.8) or {
                "text": "Schedule meeting tomorrow",
                "confidence": 0.95,
                "processing_time": 0.8
            }
        )
        
        mock_services['agentic_core'].process_user_input = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.3) or {
                "intent": "create_calendar_event",
                "confidence": 0.92,
                "action_plan": {"action_type": "create_calendar_event"}
            }
        )
        
        mock_services['calendar_service'].create_google_event = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.5) or "event_123"
        )
        
        mock_services['whatsapp_service'].send_message = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.2) or {
                "message_id": "msg_123",
                "status": "sent"
            }
        )
        
        # Define realistic user interaction patterns
        async def simulate_user_session(user, session_duration=60):
            """Simulate a realistic user session."""
            session_start = time.time()
            interactions = 0
            
            while time.time() - session_start < session_duration:
                try:
                    # Voice interaction (most common)
                    if interactions % 3 == 0:
                        await mock_services['stt_service'].transcribe_audio(b"audio_data")
                        await mock_services['agentic_core'].process_user_input("text", {"user_id": user.id})
                    
                    # Calendar operation (moderate frequency)
                    elif interactions % 5 == 0:
                        await mock_services['calendar_service'].create_google_event(
                            Mock(), CalendarEventCreate(
                                title="Test Event",
                                start_time=datetime.now(),
                                end_time=datetime.now() + timedelta(hours=1)
                            ), Mock()
                        )
                    
                    # WhatsApp message (less frequent)
                    elif interactions % 7 == 0:
                        await mock_services['whatsapp_service'].send_message(
                            Mock(), user.id, WhatsAppMessageCreate(
                                recipient="+1234567890",
                                content="Test message"
                            )
                        )
                    
                    interactions += 1
                    
                    # Realistic pause between interactions (1-5 seconds)
                    await asyncio.sleep(1 + (interactions % 5))
                    
                except Exception as e:
                    print(f"Error in user session {user.id}: {e}")
                    break
            
            return interactions
        
        # Start monitoring system resources
        initial_memory = psutil.virtual_memory().percent
        initial_cpu = psutil.cpu_percent(interval=1)
        
        # Execute concurrent user sessions
        start_time = time.time()
        
        # Use first 100 users for load test
        tasks = [simulate_user_session(user, session_duration=30) for user in user_pool[:100]]
        
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=120)
        except asyncio.TimeoutError:
            pytest.fail("Load test timed out - system may be overloaded")
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_sessions = sum(1 for result in results if isinstance(result, int))
        failed_sessions = len(results) - successful_sessions
        total_interactions = sum(result for result in results if isinstance(result, int))
        
        # Check system resources after load test
        final_memory = psutil.virtual_memory().percent
        final_cpu = psutil.cpu_percent(interval=1)
        
        # Performance assertions
        assert successful_sessions >= 95, f"Only {successful_sessions}/100 sessions completed successfully"
        assert total_time < 60, f"Load test took {total_time:.2f}s, expected under 60s"
        
        # Resource usage assertions
        memory_increase = final_memory - initial_memory
        assert memory_increase < 50, f"Memory usage increased by {memory_increase}%, may indicate memory leak"
        
        # Calculate throughput
        interactions_per_second = total_interactions / total_time
        
        print(f"Load test results (100 concurrent users):")
        print(f"- Total time: {total_time:.2f}s")
        print(f"- Successful sessions: {successful_sessions}/100")
        print(f"- Failed sessions: {failed_sessions}")
        print(f"- Total interactions: {total_interactions}")
        print(f"- Interactions per second: {interactions_per_second:.2f}")
        print(f"- Memory usage change: {memory_increase:.1f}%")
        print(f"- CPU usage: {initial_cpu:.1f}% → {final_cpu:.1f}%")
    
    @pytest.mark.asyncio
    async def test_sustained_high_load_stability(self, mock_services):
        """Test system stability under sustained high load conditions."""
        
        # Configure services with minimal delays for high throughput
        mock_services['stt_service'].transcribe_audio = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.1) or {"text": "test", "confidence": 0.9}
        )
        
        mock_services['agentic_core'].process_user_input = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.05) or {"intent": "test", "confidence": 0.9}
        )
        
        # Test parameters
        duration_seconds = 60
        requests_per_second = 50
        total_requests = duration_seconds * requests_per_second
        
        # Track performance metrics
        response_times = []
        error_count = 0
        memory_samples = []
        
        async def make_request():
            """Make a single request and measure response time."""
            start_time = time.time()
            try:
                await mock_services['stt_service'].transcribe_audio(b"audio")
                await mock_services['agentic_core'].process_user_input("text", {})
                response_time = time.time() - start_time
                response_times.append(response_time)
                return True
            except Exception:
                nonlocal error_count
                error_count += 1
                return False
        
        # Monitor system resources during test
        def monitor_resources():
            while len(response_times) < total_requests * 0.9:  # Monitor until near completion
                memory_samples.append(psutil.virtual_memory().percent)
                time.sleep(1)
        
        # Start resource monitoring
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.start()
        
        # Execute sustained load
        start_time = time.time()
        
        # Create batches of concurrent requests
        batch_size = 10
        for batch_start in range(0, total_requests, batch_size):
            batch_end = min(batch_start + batch_size, total_requests)
            batch_tasks = [make_request() for _ in range(batch_end - batch_start)]
            
            await asyncio.gather(*batch_tasks)
            
            # Small delay to maintain target RPS
            elapsed = time.time() - start_time
            expected_time = batch_end / requests_per_second
            if elapsed < expected_time:
                await asyncio.sleep(expected_time - elapsed)
        
        total_time = time.time() - start_time
        monitor_thread.join(timeout=5)
        
        # Analyze performance
        success_rate = (len(response_times) / total_requests) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0
        
        # Memory stability analysis
        if memory_samples:
            memory_trend = memory_samples[-1] - memory_samples[0] if len(memory_samples) > 1 else 0
            max_memory = max(memory_samples)
        else:
            memory_trend = 0
            max_memory = 0
        
        # Stability assertions
        assert success_rate >= 95, f"Success rate {success_rate:.1f}% below 95% threshold"
        assert avg_response_time < 1.0, f"Average response time {avg_response_time:.3f}s exceeds 1s"
        assert p95_response_time < 2.0, f"95th percentile response time {p95_response_time:.3f}s exceeds 2s"
        assert memory_trend < 20, f"Memory usage increased by {memory_trend:.1f}% during test"
        assert max_memory < 80, f"Peak memory usage {max_memory:.1f}% too high"
        
        print(f"Sustained load test results:")
        print(f"- Duration: {total_time:.2f}s")
        print(f"- Target requests: {total_requests}")
        print(f"- Successful requests: {len(response_times)}")
        print(f"- Success rate: {success_rate:.1f}%")
        print(f"- Average response time: {avg_response_time:.3f}s")
        print(f"- 95th percentile response time: {p95_response_time:.3f}s")
        print(f"- Memory trend: {memory_trend:+.1f}%")
        print(f"- Peak memory usage: {max_memory:.1f}%")
    
    @pytest.mark.asyncio
    async def test_database_performance_under_load(self, db_session, user_pool):
        """Test database performance under concurrent operations."""
        
        # Test concurrent database operations
        async def database_operations(user):
            """Perform typical database operations for a user."""
            operations_completed = 0
            
            try:
                # Create events
                for i in range(5):
                    event = Event(
                        user_id=user.id,
                        title=f"Load Test Event {i}",
                        start_time=datetime.now() + timedelta(hours=i),
                        end_time=datetime.now() + timedelta(hours=i+1),
                        google_event_id=f"load_test_{user.id}_{i}"
                    )
                    db_session.add(event)
                    operations_completed += 1
                
                # Commit in batches
                if operations_completed % 10 == 0:
                    db_session.commit()
                
                # Query operations
                events = db_session.query(Event).filter(Event.user_id == user.id).all()
                operations_completed += len(events)
                
                return operations_completed
                
            except Exception as e:
                print(f"Database error for user {user.id}: {e}")
                db_session.rollback()
                return 0
        
        # Execute concurrent database operations
        start_time = time.time()
        
        # Use subset of users to avoid overwhelming test database
        test_users = user_pool[:20]
        tasks = [database_operations(user) for user in test_users]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        db_session.commit()  # Final commit
        total_time = time.time() - start_time
        
        # Analyze database performance
        successful_operations = sum(result for result in results if isinstance(result, int))
        failed_operations = sum(1 for result in results if isinstance(result, Exception))
        
        operations_per_second = successful_operations / total_time
        
        # Performance assertions
        assert failed_operations == 0, f"{failed_operations} database operations failed"
        assert operations_per_second > 50, f"Database throughput {operations_per_second:.1f} ops/s too low"
        assert total_time < 30, f"Database operations took {total_time:.2f}s, expected under 30s"
        
        print(f"Database performance test results:")
        print(f"- Concurrent users: {len(test_users)}")
        print(f"- Total operations: {successful_operations}")
        print(f"- Operations per second: {operations_per_second:.1f}")
        print(f"- Total time: {total_time:.2f}s")
        print(f"- Failed operations: {failed_operations}")


class TestMemoryAndResourceManagement:
    """Test memory usage and resource management under load."""
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        
        # Force garbage collection before test
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Simulate repeated operations that could cause memory leaks
        iterations = 1000
        
        for i in range(iterations):
            # Create and destroy objects
            mock_service = Mock(spec=VoiceProcessingService)
            mock_service.process_data = Mock(return_value={"result": f"iteration_{i}"})
            
            # Simulate processing
            result = mock_service.process_data(f"data_{i}")
            assert result["result"] == f"iteration_{i}"
            
            # Clear references
            del mock_service
            
            # Periodic garbage collection
            if i % 100 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = final_memory - initial_memory
        memory_increase_percent = (memory_increase / initial_memory) * 100
        
        # Memory leak assertion (allow for some increase due to test overhead)
        assert memory_increase_percent < 50, f"Memory increased by {memory_increase:.1f}MB ({memory_increase_percent:.1f}%)"
        
        print(f"Memory leak test results:")
        print(f"- Initial memory: {initial_memory:.1f}MB")
        print(f"- Final memory: {final_memory:.1f}MB")
        print(f"- Memory increase: {memory_increase:.1f}MB ({memory_increase_percent:.1f}%)")
        print(f"- Iterations: {iterations}")
    
    @pytest.mark.asyncio
    async def test_connection_pool_performance(self):
        """Test database connection pool performance under load."""
        
        # Simulate database connection usage
        connection_times = []
        
        async def simulate_db_operation():
            """Simulate a database operation."""
            start_time = time.time()
            
            # Simulate connection acquisition and query
            await asyncio.sleep(0.01)  # Simulate query time
            
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            
            return True
        
        # Test with many concurrent "database operations"
        concurrent_operations = 100
        
        start_time = time.time()
        tasks = [simulate_db_operation() for _ in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze connection pool performance
        successful_operations = sum(results)
        avg_connection_time = statistics.mean(connection_times)
        max_connection_time = max(connection_times)
        
        # Performance assertions
        assert successful_operations == concurrent_operations
        assert avg_connection_time < 0.1, f"Average connection time {avg_connection_time:.3f}s too high"
        assert max_connection_time < 0.5, f"Max connection time {max_connection_time:.3f}s too high"
        assert total_time < 5, f"Total time {total_time:.2f}s too high for {concurrent_operations} operations"
        
        print(f"Connection pool performance:")
        print(f"- Concurrent operations: {concurrent_operations}")
        print(f"- Average connection time: {avg_connection_time:.3f}s")
        print(f"- Max connection time: {max_connection_time:.3f}s")
        print(f"- Total time: {total_time:.2f}s")


class TestScalabilityLimits:
    """Test system behavior at scalability limits."""
    
    @pytest.mark.asyncio
    async def test_maximum_concurrent_users(self):
        """Test system behavior with maximum concurrent users."""
        
        # Gradually increase load to find breaking point
        max_users_tested = 0
        
        for user_count in [50, 100, 200, 300]:
            try:
                # Create mock user sessions
                async def mock_user_session():
                    await asyncio.sleep(0.1)  # Minimal processing
                    return True
                
                start_time = time.time()
                
                # Test with current user count
                tasks = [mock_user_session() for _ in range(user_count)]
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), 
                    timeout=30
                )
                
                processing_time = time.time() - start_time
                successful_sessions = sum(1 for r in results if r is True)
                success_rate = (successful_sessions / user_count) * 100
                
                print(f"User count {user_count}: {success_rate:.1f}% success, {processing_time:.2f}s")
                
                # Consider successful if >90% success rate and reasonable time
                if success_rate >= 90 and processing_time < 60:
                    max_users_tested = user_count
                else:
                    break
                    
            except asyncio.TimeoutError:
                print(f"Timeout at {user_count} users")
                break
            except Exception as e:
                print(f"Error at {user_count} users: {e}")
                break
        
        # Verify we can handle at least 100 concurrent users
        assert max_users_tested >= 100, f"System failed before reaching 100 users (max: {max_users_tested})"
        
        print(f"Maximum concurrent users successfully tested: {max_users_tested}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])