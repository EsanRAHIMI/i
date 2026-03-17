'use client';

import type React from 'react';
import { cn } from '@/lib/utils';
import { Surface } from '@/components/ui/Surface';

type GlassCardProps = {
  className?: string;
  children: React.ReactNode;
};

export function GlassCard({ className, children }: GlassCardProps) {
  return (
    <Surface material="regular" className={cn(className)}>
      {children}
    </Surface>
  );
}
