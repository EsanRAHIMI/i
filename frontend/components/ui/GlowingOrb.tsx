'use client';

import { cn } from '@/lib/utils';

interface GlowingOrbProps {
  size?: 'sm' | 'md' | 'large';
  isActive?: boolean;
  className?: string;
}

export function GlowingOrb({ size = 'md', isActive = true, className }: GlowingOrbProps) {
  const sizeClasses = {
    sm: 'w-16 h-16',
    md: 'w-24 h-24',
    large: 'w-36 h-36',
  };

  return (
    <div
      className={cn(
        'rounded-full bg-gradient-to-br from-purple-400 via-primary-500 to-gray-800',
        'shadow-lg',
        sizeClasses[size],
        isActive && 'animate-pulse-glow',
        className
      )}
      style={{
        background: 'radial-gradient(circle at 30% 30%, #a78bfa, #6366f1 60%, #111827 100%)',
        boxShadow: isActive 
          ? '0 0 40px rgba(99, 102, 241, 0.6) inset, 0 0 60px rgba(99, 102, 241, 0.4)'
          : '0 0 20px rgba(99, 102, 241, 0.3) inset, 0 0 30px rgba(99, 102, 241, 0.2)',
      }}
    />
  );
}