'use client';

import type React from 'react';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost' | 'destructive';
type Size = 'sm' | 'md' | 'lg';

const sizeStyles: Record<Size, string> = {
  sm: 'h-(--tap-target) px-3 text-sm',
  md: 'h-(--tap-target) px-4 text-sm',
  lg: 'h-[calc(var(--tap-target)+6px)] px-5 text-base',
};

const variantStyles: Record<Variant, string> = {
  primary:
    'bg-linear-to-b from-primary-500 to-primary-700 text-white shadow-[0_10px_28px_rgba(79,70,229,0.35)] hover:from-primary-400 hover:to-primary-700 focus-visible:ring-primary-500/60',
  secondary:
    'bg-white/7 text-white hover:bg-white/10 focus-visible:ring-white/20 border border-white/12',
  ghost:
    'bg-transparent text-white/85 hover:bg-white/8 focus-visible:ring-white/20',
  destructive:
    'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500/60',
};

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

export function Button({ className, variant = 'secondary', size = 'md', type = 'button', ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2',
        'rounded-control',
        'font-medium tracking-[-0.01em]',
        'transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0',
        'disabled:pointer-events-none disabled:opacity-50',
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

