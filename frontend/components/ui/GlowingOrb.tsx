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
        'rounded-full',
        // Avoid inline styles; use Tailwind classes so gradients behave consistently across viewports.
        'bg-[radial-gradient(circle_at_30%_30%,#a78bfa,#6366f1_60%,#111827_100%)]',
        isActive
          ? 'shadow-[inset_0_0_40px_rgba(99,102,241,0.60),0_0_60px_rgba(99,102,241,0.40)]'
          : 'shadow-[inset_0_0_20px_rgba(99,102,241,0.30),0_0_30px_rgba(99,102,241,0.20)]',
        sizeClasses[size],
        isActive && 'animate-pulse-glow',
        className
      )}
    />
  );
}