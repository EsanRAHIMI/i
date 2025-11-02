'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';

interface VoiceActivityIndicatorProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showStatus?: boolean;
}

export function VoiceActivityIndicator({ 
  size = 'md', 
  className, 
  showStatus = true 
}: VoiceActivityIndicatorProps) {
  const { voiceSession } = useAppStore();
  const [animationKey, setAnimationKey] = useState(0);

  // Reset animation when status changes
  useEffect(() => {
    setAnimationKey(prev => prev + 1);
  }, [voiceSession?.status]);

  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  };

  const getIndicatorStyle = () => {
    switch (voiceSession?.status) {
      case 'listening':
        return {
          background: 'radial-gradient(circle, #10b981, #059669)',
          animation: 'pulse 1.5s ease-in-out infinite',
          boxShadow: '0 0 20px rgba(16, 185, 129, 0.5)'
        };
      
      case 'processing':
        return {
          background: 'radial-gradient(circle, #f59e0b, #d97706)',
          animation: 'spin 1s linear infinite',
          boxShadow: '0 0 20px rgba(245, 158, 11, 0.5)'
        };
      
      case 'speaking':
        return {
          background: 'radial-gradient(circle, #3b82f6, #2563eb)',
          animation: 'bounce 0.8s ease-in-out infinite',
          boxShadow: '0 0 20px rgba(59, 130, 246, 0.5)'
        };
      
      default:
        return {
          background: 'radial-gradient(circle, #6b7280, #4b5563)',
          boxShadow: '0 0 10px rgba(107, 114, 128, 0.3)'
        };
    }
  };

  const getStatusText = () => {
    switch (voiceSession?.status) {
      case 'listening':
        return 'Listening';
      case 'processing':
        return 'Processing';
      case 'speaking':
        return 'Speaking';
      default:
        return 'Idle';
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
    <div className={cn('flex flex-col items-center space-y-2', className)}>
      {/* Main Indicator */}
      <div
        key={animationKey}
        className={cn(
          'rounded-full transition-all duration-300',
          sizeClasses[size]
        )}
        style={getIndicatorStyle()}
      >
        {/* Inner dot */}
        <div className="w-full h-full rounded-full flex items-center justify-center">
          <div className="w-1/3 h-1/3 bg-white rounded-full opacity-80" />
        </div>
      </div>

      {/* Status Text */}
      {showStatus && (
        <div className="text-center">
          <p className={cn('text-xs font-medium', getStatusColor())}>
            {getStatusText()}
          </p>
          
          {voiceSession?.confidence && (
            <p className="text-xs text-gray-500 mt-1">
              {Math.round(voiceSession.confidence * 100)}%
            </p>
          )}
        </div>
      )}

      {/* Waveform Animation for Speaking */}
      {voiceSession?.status === 'speaking' && (
        <div className="flex items-center space-x-1">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="w-1 bg-blue-400 rounded-full animate-pulse"
              style={{
                height: `${Math.random() * 20 + 10}px`,
                animationDelay: `${i * 0.1}s`,
                animationDuration: '0.6s'
              }}
            />
          ))}
        </div>
      )}

      {/* Processing Dots */}
      {voiceSession?.status === 'processing' && (
        <div className="flex space-x-1">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce"
              style={{
                animationDelay: `${i * 0.2}s`,
                animationDuration: '1s'
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}