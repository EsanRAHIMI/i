'use client';

import { useEffect, useState } from 'react';
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
import { logger } from '@/lib/logger';

export default function DashboardPage() {
  const { user, tasks, events, setTasks, setEvents, voiceSession } = useAppStore();
  const [isLoading, setIsLoading] = useState(true);
  const [todayTasks, setTodayTasks] = useState<any[]>([]);
  const [showAvatarCustomization, setShowAvatarCustomization] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setIsLoading(true);
        
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
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <AppPageShell contentClassName="xl:max-w-none">
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

              <button
                onClick={() => setShowAvatarCustomization(true)}
                className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 hover:text-white"
              >
                Customize Avatar
              </button>
            </div>
          </div>
        </GlassCard>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 xl:gap-6">
          <GlassCard className="min-h-[132px] p-5 sm:p-6">
            <div className="flex h-full flex-col justify-between gap-6">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium tracking-[0.24em] text-white/45">TODAY</span>
                <div className="rounded-2xl bg-white/10 p-3">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 8l2 2 4-4" />
                  </svg>
                </div>
              </div>
              <div>
                <p className="text-4xl font-semibold text-white">{todayTasks.length}</p>
                <p className="mt-2 text-sm text-white/60">Tasks planned for today</p>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="min-h-[132px] p-5 sm:p-6">
            <div className="flex h-full flex-col justify-between gap-6">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium tracking-[0.24em] text-white/45">NEXT</span>
                <div className="rounded-2xl bg-white/10 p-3">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div>
                <p className="text-4xl font-semibold text-white">{upcomingEvents.length}</p>
                <p className="mt-2 text-sm text-white/60">Upcoming calendar events</p>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="min-h-[132px] p-5 sm:p-6 md:col-span-2 xl:col-span-1">
            <div className="flex h-full flex-col justify-between gap-6">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium tracking-[0.24em] text-white/45">PENDING</span>
                <div className="rounded-2xl bg-white/10 p-3">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div>
                <p className="text-4xl font-semibold text-white">{pendingTasks.length}</p>
                <p className="mt-2 text-sm text-white/60">Items waiting for action</p>
              </div>
            </div>
          </GlassCard>
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
