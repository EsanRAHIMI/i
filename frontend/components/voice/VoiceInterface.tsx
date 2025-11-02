'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { DigitalAvatar } from '@/components/avatar/DigitalAvatar';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface VoiceInterfaceProps {
  className?: string;
  onTranscript?: (text: string) => void;
  onResponse?: (response: any) => void;
}

export function VoiceInterface({ className, onTranscript, onResponse }: VoiceInterfaceProps) {
  const { voiceSession, setVoiceSession, updateVoiceSession } = useAppStore();
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Initialize audio context for level monitoring
  const initAudioContext = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      microphone.connect(analyser);
      analyserRef.current = analyser;

      // Monitor audio levels
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      
      const updateAudioLevel = () => {
        if (!analyser || !isRecording) return;
        
        analyser.getByteFrequencyData(dataArray);
        const sum = dataArray.reduce((acc, value) => acc + value, 0);
        const average = sum / dataArray.length;
        setAudioLevel(average / 255);
        
        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      };

      if (isRecording) {
        updateAudioLevel();
      }

      return stream;
    } catch (err) {
      console.error('Failed to initialize audio:', err);
      setError('Microphone access denied');
      return null;
    }
  }, [isRecording]);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      setError(null);
      setIsRecording(true);
      
      // Update voice session
      setVoiceSession({
        id: Date.now().toString(),
        user_id: 'current-user',
        status: 'listening',
        created_at: new Date().toISOString()
      });

      const stream = await initAudioContext();
      if (!stream) return;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await processAudio(audioBlob);
      };

      mediaRecorder.start();
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError('Failed to start recording');
      setIsRecording(false);
    }
  }, [initAudioContext, setVoiceSession]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      updateVoiceSession({ status: 'processing' });

      // Stop audio level monitoring
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      // Stop media stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    }
  }, [isRecording, updateVoiceSession]);

  // Process recorded audio
  const processAudio = useCallback(async (audioBlob: Blob) => {
    try {
      updateVoiceSession({ status: 'processing' });

      // Convert speech to text
      const sttResult = await apiClient.speechToText(audioBlob);
      const transcript = sttResult.text;
      
      updateVoiceSession({ 
        transcript,
        confidence: sttResult.confidence 
      });
      
      onTranscript?.(transcript);

      if (transcript.trim()) {
        // Process with AI agent
        const agentResponse = await apiClient.processIntent(transcript);
        
        // Generate TTS if response has text
        if (agentResponse.text) {
          updateVoiceSession({ status: 'speaking' });
          
          const ttsResult = await apiClient.textToSpeech(agentResponse.text);
          setCurrentAudioUrl(ttsResult.audio_url);
          
          // Play audio
          const audio = new Audio(ttsResult.audio_url);
          audio.onended = () => {
            updateVoiceSession({ status: 'idle' });
            setCurrentAudioUrl(null);
          };
          await audio.play();
        } else {
          updateVoiceSession({ status: 'idle' });
        }

        onResponse?.(agentResponse);
      } else {
        updateVoiceSession({ status: 'idle' });
      }
    } catch (err: any) {
      console.error('Failed to process audio:', err);
      setError(err.message || 'Failed to process audio');
      updateVoiceSession({ status: 'idle' });
    }
  }, [updateVoiceSession, onTranscript, onResponse]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const getStatusText = () => {
    switch (voiceSession?.status) {
      case 'listening':
        return 'Listening...';
      case 'processing':
        return 'Processing...';
      case 'speaking':
        return 'Speaking...';
      default:
        return 'Tap to speak';
    }
  };

  const getStatusColor = () => {
    switch (voiceSession?.status) {
      case 'listening':
        return 'text-green-400';
      case 'processing':
        return 'text-yellow-400';
      case 'speaking':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className={`flex flex-col items-center space-y-6 ${className}`}>
      {/* Digital Avatar */}
      <div className="w-32 h-32">
        <DigitalAvatar
          isActive={voiceSession?.status === 'listening' || voiceSession?.status === 'processing'}
          isSpeaking={voiceSession?.status === 'speaking'}
          audioUrl={currentAudioUrl || undefined}
        />
      </div>

      {/* Voice Controls */}
      <div className="flex flex-col items-center space-y-4">
        {/* Main Voice Button */}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={voiceSession?.status === 'processing' || voiceSession?.status === 'speaking'}
          className={`
            relative w-20 h-20 rounded-full border-4 transition-all duration-200
            ${isRecording 
              ? 'bg-red-500 border-red-400 shadow-lg shadow-red-500/50' 
              : 'bg-primary-600 border-primary-500 hover:bg-primary-700 hover:shadow-lg hover:shadow-primary-500/50'
            }
            ${voiceSession?.status === 'processing' || voiceSession?.status === 'speaking' 
              ? 'opacity-50 cursor-not-allowed' 
              : 'cursor-pointer'
            }
          `}
        >
          {voiceSession?.status === 'processing' ? (
            <LoadingSpinner size="md" className="text-white" />
          ) : isRecording ? (
            <div className="w-6 h-6 bg-white rounded-sm mx-auto" />
          ) : (
            <svg className="w-8 h-8 text-white mx-auto" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          )}

          {/* Audio level indicator */}
          {isRecording && (
            <div 
              className="absolute inset-0 rounded-full border-4 border-white/30"
              style={{
                transform: `scale(${1 + audioLevel * 0.5})`,
                opacity: audioLevel
              }}
            />
          )}
        </button>

        {/* Status Text */}
        <div className="text-center">
          <p className={`text-sm font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </p>
          
          {voiceSession?.transcript && (
            <p className="text-xs text-gray-500 mt-1 max-w-xs">
              "{voiceSession.transcript}"
            </p>
          )}
          
          {voiceSession?.confidence && (
            <p className="text-xs text-gray-600 mt-1">
              Confidence: {Math.round(voiceSession.confidence * 100)}%
            </p>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 max-w-xs">
            <p className="text-red-400 text-sm text-center">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}