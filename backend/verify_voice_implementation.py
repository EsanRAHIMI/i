#!/usr/bin/env python3
"""
Verification script for voice processing implementation.
"""

import sys
import traceback

def test_voice_schemas():
    """Test voice processing schemas."""
    try:
        from app.schemas.voice import (
            VoiceInputRequest, TTSRequest, TranscriptionResponse, 
            TTSResponse, VoiceProfileRequest
        )
        
        # Test VoiceInputRequest
        request = VoiceInputRequest(audio_data="dGVzdA==", language="en")
        assert request.audio_data == "dGVzdA=="
        assert request.language == "en"
        
        # Test TTSRequest
        tts_request = TTSRequest(text="Hello world", language="en")
        assert tts_request.text == "Hello world"
        assert tts_request.language == "en"
        
        print("✓ Voice schemas working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Voice schemas test failed: {e}")
        traceback.print_exc()
        return False

def test_voice_service_imports():
    """Test voice service imports."""
    try:
        # Test basic imports without initializing heavy ML models
        from app.services.voice import VoiceProfile
        
        # Test VoiceProfile
        profile = VoiceProfile("test_user")
        assert profile.user_id == "test_user"
        
        profile.update_characteristics({"speed": 1.2})
        assert profile.voice_characteristics["speed"] == 1.2
        
        print("✓ Voice service basic functionality working")
        return True
        
    except Exception as e:
        print(f"✗ Voice service test failed: {e}")
        traceback.print_exc()
        return False

def test_api_structure():
    """Test API structure without starting server."""
    try:
        # Test that the voice API module can be imported
        import app.api.v1.voice as voice_api
        
        # Check that required functions exist
        assert hasattr(voice_api, 'speech_to_text')
        assert hasattr(voice_api, 'text_to_speech')
        assert hasattr(voice_api, 'voice_stream')
        
        print("✓ Voice API structure is correct")
        return True
        
    except Exception as e:
        print(f"✗ Voice API structure test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all verification tests."""
    print("Voice Processing Implementation Verification")
    print("=" * 50)
    
    tests = [
        test_voice_schemas,
        test_voice_service_imports,
        test_api_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All voice processing components implemented successfully!")
        return 0
    else:
        print("❌ Some voice processing components need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())