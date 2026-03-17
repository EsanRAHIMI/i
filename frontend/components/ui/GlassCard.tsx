'use client';

import type React from 'react';
import { cn } from '@/lib/utils';

type GlassCardProps = {
  className?: string;
  children: React.ReactNode;
};

export function GlassCard({ className, children }: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-white/10 bg-white/5 shadow-[0_8px_30px_rgba(0,0,0,0.35)] backdrop-blur-xl',
        className
      )}
    >
      {children}
    </div>
  );
}
