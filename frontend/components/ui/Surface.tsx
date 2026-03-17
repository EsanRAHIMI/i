'use client';

import type React from 'react';
import { cn } from '@/lib/utils';

type Material = 'ultraThin' | 'thin' | 'regular' | 'thick' | 'ultraThick';

const materialStyles: Record<Material, { bg: string; blur: string }> = {
  ultraThin: { bg: 'bg-[color:var(--glass-ultraThin)]', blur: 'backdrop-blur-lg' },
  thin: { bg: 'bg-[color:var(--glass-thin)]', blur: 'backdrop-blur-xl' },
  regular: { bg: 'bg-[color:var(--glass-regular)]', blur: 'backdrop-blur-2xl' },
  thick: { bg: 'bg-[color:var(--glass-thick)]', blur: 'backdrop-blur-2xl' },
  ultraThick: { bg: 'bg-[color:var(--glass-ultraThick)]', blur: 'backdrop-blur-3xl' },
};

type SurfaceProps = {
  as?: 'div' | 'section' | 'article' | 'header' | 'main' | 'aside' | 'nav';
  material?: Material;
  className?: string;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLElement>;

export function Surface({ as: Comp = 'div', material = 'regular', className, children, ...props }: SurfaceProps) {
  const m = materialStyles[material];

  return (
    <Comp
      className={cn(
        'relative',
        'rounded-surface',
        'border border-(--glass-border)',
        m.bg,
        m.blur,
        'shadow-(--glass-shadow-soft)',
        className
      )}
      {...props}
    >
      {/* subtle highlight to mimic vibrancy edge */}
      <div className="pointer-events-none absolute inset-0 rounded-[inherit] ring-1 ring-inset ring-(--glass-highlight)" />
      {children}
    </Comp>
  );
}

