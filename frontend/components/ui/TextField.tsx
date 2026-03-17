'use client';

import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

type TextFieldProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { className, label, hint, error, id, ...props },
  ref
) {
  const inputId = id || props.name;

  return (
    <div className="space-y-2">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-white/80">
          {label}
        </label>
      )}
      <input
        id={inputId}
        ref={ref}
        className={cn(
          'h-(--tap-target) w-full',
          'rounded-control',
          'border border-white/12 bg-white/5',
          'px-4 text-sm text-white placeholder:text-white/40',
          'backdrop-blur-xl',
          'transition-colors',
          'focus:border-white/18 focus:outline-none focus:ring-2 focus:ring-primary-500/50',
          error && 'border-red-500/30 focus:ring-red-500/40',
          className
        )}
        {...props}
      />
      {(error || hint) && (
        <p className={cn('text-xs leading-5', error ? 'text-red-200/80' : 'text-white/45')}>
          {error || hint}
        </p>
      )}
    </div>
  );
});

