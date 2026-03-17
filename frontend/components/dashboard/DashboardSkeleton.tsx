'use client';

import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';

function SkeletonBlock({ className }: { className: string }) {
  return <div className={cn('animate-pulse rounded-xl bg-white/10', className)} />;
}

export function DashboardSkeleton() {
  return (
    <div className="px-4 pb-36 pt-4 sm:px-6 sm:pb-40 sm:pt-6 lg:px-8 xl:px-10 xl:pb-32">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 sm:gap-8 xl:max-w-none">
        <GlassCard className="overflow-hidden p-5 sm:p-7 xl:p-8">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
            <div className="space-y-4">
              <SkeletonBlock className="h-6 w-40 rounded-full" />
              <div className="space-y-3">
                <SkeletonBlock className="h-10 w-[min(520px,85vw)]" />
                <SkeletonBlock className="h-5 w-[min(440px,80vw)]" />
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
              <SkeletonBlock className="h-14 w-[min(240px,80vw)] rounded-2xl" />
              <SkeletonBlock className="h-14 w-[min(190px,65vw)] rounded-2xl" />
            </div>
          </div>
        </GlassCard>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 xl:gap-6">
          {Array.from({ length: 3 }).map((_, idx) => (
            <GlassCard key={idx} className="p-5 sm:p-6">
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  <SkeletonBlock className="h-6 w-28 rounded-full" />
                  <SkeletonBlock className="h-11 w-11 rounded-2xl" />
                </div>
                <div>
                  <SkeletonBlock className="h-10 w-16" />
                  <SkeletonBlock className="mt-3 h-4 w-44" />
                </div>
              </div>
            </GlassCard>
          ))}
        </div>

        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
          <GlassCard className="min-h-[360px] p-5 sm:p-6">
            <SkeletonBlock className="h-7 w-40" />
            <SkeletonBlock className="mt-4 h-4 w-56" />
            <div className="mt-6 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonBlock key={i} className="h-16 w-full rounded-2xl" />
              ))}
            </div>
          </GlassCard>
          <GlassCard className="min-h-[360px] p-5 sm:p-6">
            <SkeletonBlock className="h-7 w-56" />
            <SkeletonBlock className="mt-4 h-4 w-64" />
            <div className="mt-6 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonBlock key={i} className="h-20 w-full rounded-2xl" />
              ))}
            </div>
          </GlassCard>
        </div>

        <GlassCard className="min-h-[320px] p-5 sm:p-6">
          <SkeletonBlock className="h-7 w-40" />
          <SkeletonBlock className="mt-4 h-4 w-64" />
          <div className="mt-6 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <SkeletonBlock key={i} className="h-20 w-full rounded-2xl" />
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

