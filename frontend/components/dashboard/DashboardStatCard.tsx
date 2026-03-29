'use client';

import type React from 'react';
import { Surface } from '@/components/ui/Surface';
import { cn } from '@/lib/utils';

type Tone = 'primary' | 'blue' | 'green' | 'amber';

const toneStyles: Record<Tone, { chip: string; iconWrap: string; ring: string }> = {
  primary: {
    chip: 'border-primary-500/20 bg-primary-500/10 text-primary-200',
    iconWrap: 'bg-primary-500/10 text-primary-200 border-primary-500/20',
    ring: 'text-primary-400 stroke-primary-500',
  },
  blue: {
    chip: 'border-blue-500/20 bg-blue-500/10 text-blue-200',
    iconWrap: 'bg-blue-500/10 text-blue-200 border-blue-500/20',
    ring: 'text-blue-400 stroke-blue-500',
  },
  green: {
    chip: 'border-green-500/20 bg-green-500/10 text-green-200',
    iconWrap: 'bg-green-500/10 text-green-200 border-green-500/20',
    ring: 'text-green-400 stroke-green-500',
  },
  amber: {
    chip: 'border-amber-500/20 bg-amber-500/10 text-amber-200',
    iconWrap: 'bg-amber-500/10 text-amber-200 border-amber-500/20',
    ring: 'text-amber-400 stroke-amber-500',
  },
};

type DashboardStatCardProps = {
  title: string;
  value: React.ReactNode;
  subtitle: string;
  icon: React.ReactNode;
  tone?: Tone;
  className?: string;
  progress?: number;
  sparklineData?: number[];
};

export function DashboardStatCard({
  title,
  value,
  subtitle,
  icon,
  tone = 'primary',
  className,
  progress,
  sparklineData,
}: DashboardStatCardProps) {
  const styles = toneStyles[tone];

  return (
    <Surface material="regular" className={cn('relative overflow-hidden p-4 sm:p-6', className)}>
      <div className="absolute inset-0 opacity-80 mask-[radial-gradient(70%_60%_at_20%_0%,black,transparent)]">
        <div className="h-full w-full bg-[radial-gradient(circle_at_20%_0%,rgba(99,102,241,0.18),transparent_55%)]" />
      </div>

      <div className="relative flex h-full flex-col gap-4 sm:gap-6">
        <div className="flex items-center justify-between gap-3">
          <span
            className={cn(
              'inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.22em] sm:px-3 sm:text-[11px]',
              styles.chip
            )}
          >
            {title}
          </span>
          <div
            className={cn(
              'inline-flex items-center justify-center rounded-2xl border p-2.5 sm:p-3',
              styles.iconWrap
            )}
          >
            {icon}
          </div>
        </div>

        <div className="mt-auto flex items-end justify-between gap-4">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">{value}</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-white/60 sm:text-sm sm:leading-6">{subtitle}</p>
          </div>
          
          {/* Progress Ring or Visuals */}
          <div className="flex flex-col items-center justify-center shrink-0">
            {progress !== undefined && (
              <div className="relative flex h-14 w-14 items-center justify-center sm:h-16 sm:w-16">
                <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 36 36">
                  {/* Background Circle */}
                  <path
                    className="stroke-white/10"
                    fill="none"
                    strokeWidth="3"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  {/* Progress Circle - using dasharray to determine percentage drawn */}
                  <path
                    className={cn('transition-all duration-1000 ease-in-out', styles.ring)}
                    fill="none"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    strokeDasharray={`${progress}, 100`}
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center text-center">
                  <span className="text-[10px] font-bold text-white sm:text-xs">{progress}%</span>
                </div>
              </div>
            )}
            
            {/* Simple Sparkline Bars for Next Events (decorative to add visual weight) */}
            {sparklineData && !progress && (
              <div className="flex h-10 items-end gap-1 opacity-80 sm:h-12">
                {sparklineData.map((val, i) => (
                  <div
                    key={i}
                    className={cn("w-1.5 sm:w-2 rounded-t-sm bg-current", styles.ring)}
                    style={{ height: `${Math.max(15, val)}%`, opacity: 0.4 + (i / sparklineData.length) * 0.6 }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Surface>
  );
}

