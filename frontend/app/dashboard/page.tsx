'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AvatarCustomization } from '@/components/avatar/AvatarCustomization';
import { VoiceActivityIndicator } from '@/components/voice/VoiceActivityIndicator';
import { TaskTimeline } from '@/components/dashboard/TaskTimeline';
import { AIInsightsDashboard } from '@/components/dashboard/AIInsightsDashboard';
import { CalendarIntegrationView } from '@/components/dashboard/CalendarIntegrationView';
import FloatingGlassDock from '@/components/voice/FloatingGlassDock';
import { AppPageShell } from '@/components/layout/AppPageShell';
import { GlassCard } from '@/components/ui/GlassCard';
import { DashboardStatCard } from '@/components/dashboard/DashboardStatCard';
import { DashboardSkeleton } from '@/components/dashboard/DashboardSkeleton';
import { logger } from '@/lib/logger';

export default function DashboardPage() {
  const { user, tasks, events, setTasks, setEvents, voiceSession } = useAppStore();
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [todayTasks, setTodayTasks] = useState<any[]>([]);
  const [showAvatarCustomization, setShowAvatarCustomization] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);
        
        // Load today's tasks and upcoming events
        // Use catch to handle errors gracefully - don't fail entire dashboard load if calendar/tasks fail
        const [tasksData, eventsData] = await Promise.all([
          apiClient.getTodayTasks().catch((err) => {
            // Log but don't throw - tasks might not be available yet
            logger.debug('Failed to load tasks (this is OK if backend is not ready):', err);
            return [];
          }),
          apiClient.getEvents(
            new Date().toISOString().split('T')[0],
            new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
          ).catch((err) => {
            // Log but don't throw - calendar might not be connected yet
            logger.debug('Failed to load calendar events (this is OK if calendar is not connected):', err);
            return [];
          })
        ]);
        
        setTodayTasks(tasksData);
        setTasks(tasksData);
        setEvents(eventsData);
      } catch (error) {
        logger.error('Failed to load dashboard data:', error);
        setLoadError('We could not load your dashboard right now. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, [setTasks, setEvents]);

  const upcomingEvents = events
    .filter(event => new Date(event.start_time) > new Date())
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
    .slice(0, 3);

  const pendingTasks = todayTasks.filter(task => task.status === 'pending').slice(0, 5);
  const displayName = user?.email?.split('@')[0] || 'there';

  const voiceStatus = (() => {
    switch (voiceSession?.status) {
      case 'listening':
        return { label: 'Listening', tone: 'text-green-300', dot: 'bg-green-400' };
      case 'processing':
        return { label: 'Processing', tone: 'text-yellow-300', dot: 'bg-yellow-400' };
      case 'speaking':
        return { label: 'Speaking', tone: 'text-blue-300', dot: 'bg-blue-400' };
      default:
        return { label: 'Idle', tone: 'text-white/70', dot: 'bg-white/40' };
    }
  })();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <AppPageShell contentClassName="xl:max-w-none">
        {loadError && (
          <GlassCard className="border border-red-500/20 bg-red-500/10 p-5 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-red-200">Something went wrong</p>
                <p className="mt-1 text-sm leading-6 text-red-200/70">{loadError}</p>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="w-full rounded-xl bg-red-500/20 px-4 py-2.5 text-sm font-medium text-red-100 transition-colors hover:bg-red-500/30 sm:w-auto"
              >
                Retry
              </button>
            </div>
          </GlassCard>
        )}

        {/* Header */}
        <GlassCard className="overflow-hidden p-5 sm:p-7 xl:p-8">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
            <div className="space-y-3">
              <span className="inline-flex w-fit items-center rounded-full border border-primary-500/20 bg-primary-500/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.24em] text-primary-200">
                Dashboard Overview
              </span>
              <div className="space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl xl:text-[2.8rem]">
                  Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {displayName}
                </h1>
                <p className="max-w-2xl text-sm leading-6 text-white/60 sm:text-base">
                  Keep track of your schedule, pending tasks, and AI recommendations from one calm control panel.
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center xl:justify-end">
              <div className="inline-flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                <VoiceActivityIndicator size="sm" showStatus={false} />
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/45">Voice Agent</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${voiceStatus.dot}`} />
                    <span className={`text-sm font-medium ${voiceStatus.tone}`}>{voiceStatus.label}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  onClick={() => setShowAvatarCustomization(true)}
                  className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 hover:text-white"
                >
                  Customize Avatar
                </button>
                <Link
                  href="/tasks"
                  className="inline-flex items-center justify-center rounded-2xl bg-primary-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-primary-700"
                >
                  Open Tasks
                </Link>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-3 xl:gap-6">
          <DashboardStatCard
            title="Today"
            value={todayTasks.length}
            subtitle="Tasks planned for today"
            tone="primary"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 8l2 2 4-4"
                />
              </svg>
            }
          />
          <DashboardStatCard
            title="Next"
            value={upcomingEvents.length}
            subtitle="Upcoming calendar events"
            tone="blue"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            }
          />
          <DashboardStatCard
            title="Pending"
            value={pendingTasks.length}
            subtitle="Items waiting for action"
            tone="amber"
            className="col-span-2 md:col-span-2 xl:col-span-1"
            icon={
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            }
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
          <div className="min-w-0">
            <GlassCard className="min-h-[300px] p-5 sm:p-6 xl:min-h-[360px]">
              <TaskTimeline maxItems={8} />
            </GlassCard>
          </div>

          <div className="min-w-0">
            <GlassCard className="min-h-[300px] p-5 sm:p-6 xl:min-h-[360px]">
              <CalendarIntegrationView />
            </GlassCard>
          </div>
        </div>

        {/* AI Insights Section */}
        <GlassCard className="min-h-[260px] p-5 sm:p-6 xl:min-h-[320px]">
          <AIInsightsDashboard />
        </GlassCard>

      {/* Avatar Customization Modal */}
      {showAvatarCustomization && (
        <AvatarCustomization
          onClose={() => setShowAvatarCustomization(false)}
          onSave={(avatarData) => {
            logger.info('Avatar saved successfully');
            setShowAvatarCustomization(false);
          }}
        />
      )}

      {/* Floating Glass Dock - Voice Agent Interface */}
      <FloatingGlassDock
        agentOpen={agentOpen}
        onToggleAgent={setAgentOpen}
        onLeftAction={() => {
          // Navigate to calendar or open calendar view
          logger.debug('Calendar action clicked');
        }}
        onRightAction={() => {
          // AI suggestions action
          logger.debug('AI suggestions clicked');
        }}
      />
    </AppPageShell>
  );
}
