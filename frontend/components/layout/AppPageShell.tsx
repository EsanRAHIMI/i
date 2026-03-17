'use client';

import type React from 'react';
import { cn } from '@/lib/utils';

type AppPageShellProps = {
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
};

export function AppPageShell({ children, className, contentClassName }: AppPageShellProps) {
  return (
    <div
      className={cn(
        'px-4 pb-36 pt-4 sm:px-6 sm:pb-40 sm:pt-6 lg:px-8 xl:px-10 xl:pb-32',
        className
      )}
    >
      <div className={cn('mx-auto flex w-full max-w-6xl flex-col gap-6 sm:gap-8', contentClassName)}>
        {children}
      </div>
    </div>
  );
}
