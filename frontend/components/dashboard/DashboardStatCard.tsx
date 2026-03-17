'use client';

import type React from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';

type Tone = 'primary' | 'blue' | 'green' | 'amber';

const toneStyles: Record<Tone, { chip: string; iconWrap: string }> = {
  primary: {
    chip: 'border-primary-500/20 bg-primary-500/10 text-primary-200',
    iconWrap: 'bg-primary-500/10 text-primary-200 border-primary-500/20',
  },
  blue: {
    chip: 'border-blue-500/20 bg-blue-500/10 text-blue-200',
    iconWrap: 'bg-blue-500/10 text-blue-200 border-blue-500/20',
  },
  green: {
    chip: 'border-green-500/20 bg-green-500/10 text-green-200',
    iconWrap: 'bg-green-500/10 text-green-200 border-green-500/20',
  },
  amber: {
    chip: 'border-amber-500/20 bg-amber-500/10 text-amber-200',
    iconWrap: 'bg-amber-500/10 text-amber-200 border-amber-500/20',
  },
};

type DashboardStatCardProps = {
  title: string;
  value: React.ReactNode;
  subtitle: string;
  icon: React.ReactNode;
  tone?: Tone;
  className?: string;
};

export function DashboardStatCard({
  title,
  value,
  subtitle,
  icon,
  tone = 'primary',
  className,
}: DashboardStatCardProps) {
  const styles = toneStyles[tone];

  return (
    <GlassCard className={cn('relative overflow-hidden p-5 sm:p-6', className)}>
      <div className="absolute inset-0 opacity-80 mask-[radial-gradient(70%_60%_at_20%_0%,black,transparent)]">
        <div className="h-full w-full bg-[radial-gradient(circle_at_20%_0%,rgba(99,102,241,0.18),transparent_55%)]" />
      </div>

      <div className="relative flex h-full flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <span
            className={cn(
              'inline-flex w-fit items-center rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.22em]',
              styles.chip
            )}
          >
            {title}
          </span>
          <div className={cn('inline-flex items-center justify-center rounded-2xl border p-3', styles.iconWrap)}>
            {icon}
          </div>
        </div>

        <div className="mt-auto">
          <div className="text-4xl font-semibold tracking-tight text-white">{value}</div>
          <p className="mt-2 text-sm leading-6 text-white/60">{subtitle}</p>
        </div>
      </div>
    </GlassCard>
  );
}

