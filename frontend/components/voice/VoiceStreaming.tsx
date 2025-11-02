'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAppStore } from '@/store/useAppStore';
import { DigitalAvatar } from '@/components/avatar/DigitalAvatar';

interface VoiceStreamingProps {
  className?: string;
  onTranscript?: (text: string, isFinal: boolean) => void;
  onResponse?: (response: any) => void;
}

export function VoiceStreaming({ className, onTranscript, onResponse }: VoiceStreamingProps) {
  const { voiceSession, setVoiceSession, updateVoiceSession } = useAppStore();
  const [isStreaming, setIsStreaming] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  // WebSocket connection for real-time streaming
  const {
    isConnected,
    connectionState,
    sendVoiceData,
    sendVoiceStart,
    sendVoiceEnd,
    lastMessage
  } = useWebSocket({
    onMessage: (message) => {
      switch (message.type) {
        case 'transcript_partial':
          setPartialTranscript(message.data.text);
          onTranscript?.(message.data.text, false);
          break;
          
        case 'transcript_final':
          setFinalTranscript(message.data.text);
          setPartialTranscript('');
          onTranscript?.(message.data.text, true);
          updateVoiceSession({ 
            transcript: message.data.text,
            confidence: message.data.confidence 
          });
          break;
          
        case 'agent_response':
          onResponse?.(message.data);
          if (message.data.audio_url) {
            updateVoiceSession({ status: 'speaking' });
            playAudioResponse(message.data.audio_url);
          } else {
            updateVoiceSession({ status: 'idle' });
          }
          break;
          
        case 'error':
          console.error('Voice streaming error:', message.data);
          stopStreaming();
          break;
      }
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    }
  });

  // Initialize audio context and analyser
  const initAudioContext = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000
      });
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      microphone.connect(analyser);
      analyserRef.current = analyser;

      return stream;
    } catch (error) {
      console.error('Failed to initialize audio context:', error);
      throw error;
    }
  }, []);

  // Monitor audio levels
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current || !isStreaming) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    const sum = dataArray.reduce((acc, value) => acc + value, 0);
    const average = sum / dataArray.length;
    setAudioLevel(average / 255);

    animationFrameRef.current = requestAnimationFrame(monitorAudioLevel);
  }, [isStreaming]);

  // Start streaming
  const startStreaming = useCallback(async () => {
    if (!isConnected) {
      console.error('WebSocket not connected');
      return;
    }

    try {
      setIsStreaming(true);
      setPartialTranscript('');
      setFinalTranscript('');
      
      setVoiceSession({
        id: Date.now().toString(),
        user_id: 'current-user',
        status: 'listening',
        created_at: new Date().toISOString()
      });

      const stream = await initAudioContext();
      
      // Start WebSocket voice session
      sendVoiceStart();

      // Create MediaRecorder for streaming
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && isConnected) {
          // Convert blob to ArrayBuffer and send via WebSocket
          const arrayBuffer = await event.data.arrayBuffer();
          sendVoiceData(arrayBuffer);
        }
      };

      // Start recording with small time slices for real-time streaming
      mediaRecorder.start(100); // 100ms chunks
      
      // Start audio level monitoring
      monitorAudioLevel();

    } catch (error) {
      console.error('Failed to start streaming:', error);
      setIsStreaming(false);
      updateVoiceSession({ status: 'idle' });
    }
  }, [isConnected, initAudioContext, sendVoiceStart, sendVoiceData, monitorAudioLevel, setVoiceSession, updateVoiceSession]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    sendVoiceEnd();
    updateVoiceSession({ status: 'processing' });
  }, [sendVoiceEnd, updateVoiceSession]);

  // Play audio response
  const playAudioResponse = useCallback(async (audioUrl: string) => {
    try {
      const audio = new Audio(audioUrl);
      audio.onended = () => {
        updateVoiceSession({ status: 'idle' });
      };
      await audio.play();
    } catch (error) {
      console.error('Failed to play audio response:', error);
      updateVoiceSession({ status: 'idle' });
    }
  }, [updateVoiceSession]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const getConnectionStatus = () => {
    switch (connectionState) {
      case 'connecting':
        return { text: 'Connecting...', color: 'text-yellow-400' };
      case 'connected':
        return { text: 'Connected', color: 'text-green-400' };
      case 'error':
        return { text: 'Connection Error', color: 'text-red-400' };
      default:
        return { text: 'Disconnected', color: 'text-gray-400' };
    }
  };

  const status = getConnectionStatus();

  return (
    <div className={`flex flex-col items-center space-y-6 ${className}`}>
      {/* Digital Avatar */}
      <div className="w-32 h-32">
        <DigitalAvatar
          isActive={voiceSession?.status === 'listening' || voiceSession?.status === 'processing'}
          isSpeaking={voiceSession?.status === 'speaking'}
        />
      </div>

      {/* Streaming Controls */}
      <div className="flex flex-col items-center space-y-4">
        {/* Connection Status */}
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className={`text-xs ${status.color}`}>{status.text}</span>
        </div>

        {/* Stream Button */}
        <button
          onClick={isStreaming ? stopStreaming : startStreaming}
          disabled={!isConnected || voiceSession?.status === 'processing' || voiceSession?.status === 'speaking'}
          className={`
            relative w-20 h-20 rounded-full border-4 transition-all duration-200
            ${isStreaming 
              ? 'bg-red-500 border-red-400 shadow-lg shadow-red-500/50 animate-pulse' 
              : 'bg-primary-600 border-primary-500 hover:bg-primary-700 hover:shadow-lg hover:shadow-primary-500/50'
            }
            ${!isConnected || voiceSession?.status === 'processing' || voiceSession?.status === 'speaking'
              ? 'opacity-50 cursor-not-allowed' 
              : 'cursor-pointer'
            }
          `}
        >
          {isStreaming ? (
            <div className="flex items-center justify-center">
              <div className="w-6 h-6 bg-white rounded-sm" />
            </div>
          ) : (
            <svg className="w-8 h-8 text-white mx-auto" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          )}

          {/* Audio level indicator */}
          {isStreaming && (
            <div 
              className="absolute inset-0 rounded-full border-4 border-white/30"
              style={{
                transform: `scale(${1 + audioLevel * 0.5})`,
                opacity: audioLevel
              }}
            />
          )}
        </button>

        {/* Status and Transcript */}
        <div className="text-center max-w-xs">
          <p className="text-sm font-medium text-primary-400 mb-2">
            {isStreaming ? 'Streaming...' : 'Tap to start streaming'}
          </p>
          
          {(partialTranscript || finalTranscript) && (
            <div className="bg-dark-800 rounded-lg p-3 border border-gray-700">
              {partialTranscript && (
                <p className="text-gray-400 text-sm italic">
                  {partialTranscript}
                </p>
              )}
              {finalTranscript && (
                <p className="text-white text-sm font-medium">
                  "{finalTranscript}"
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}