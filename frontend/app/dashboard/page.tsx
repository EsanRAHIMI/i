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
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      }).format(now));
    };
    updateTime();
    const interval = setInterval(updateTime, 60000);
    return () => clearInterval(interval);
  }, []);

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

  const pendingTasks = todayTasks.filter(task => task.status === 'pending' || !task.completed).slice(0, 5);
  const completedTasksCount = todayTasks.length - pendingTasks.length; // Approximate since we sliced it above? Wait, the above slice(0,5) will mess up count.

  // Correct calculation for progress:
  const allPending = todayTasks.filter(task => task.status === 'pending' || task.status === 'in_progress' || !task.status);
  const actualCompletedCount = todayTasks.length - allPending.length;
  
  const todayProgress = todayTasks.length > 0 ? Math.round((actualCompletedCount / todayTasks.length) * 100) : 0;
  const pendingProgress = todayTasks.length > 0 ? Math.round((allPending.length / todayTasks.length) * 100) : 0;

  // Visual decoration for Next events (since it's a future timeline)
  const eventsSparkline = [30, 45, 60, 50, 80, 40, 95];

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

  const currentHour = new Date().getHours();
  const greetingText = currentHour < 12 ? 'Good morning' : currentHour < 18 ? 'Good afternoon' : 'Good evening';
  const greetingIcon = currentHour < 12 ? '🌤️' : currentHour < 18 ? '☀️' : '🌙';

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <AppPageShell contentClassName="xl:max-w-none relative overflow-hidden">
        {/* AI Global Presence - Apple Intelligence / Gemini Style Glow */}
        <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden mix-blend-screen opacity-80">
          {/* Top Left Blob */}
          <div className={`absolute -left-[10%] -top-[10%] h-[40vw] w-[40vw] rounded-full blur-[120px] transition-all duration-[2000ms] ease-in-out ${
            voiceSession?.status === 'listening' ? 'bg-emerald-500/40 translate-x-[5%] translate-y-[5%] scale-110' : 
            voiceSession?.status === 'processing' ? 'bg-purple-500/40 translate-x-[15%] opacity-80 scale-125 animate-pulse' :
            voiceSession?.status === 'speaking' ? 'bg-blue-500/40 translate-y-[5%] scale-105' : 'bg-transparent opacity-0 scale-50'
          }`} />
          
          {/* Bottom Right Blob */}
          <div className={`absolute -bottom-[10%] -right-[10%] h-[50vw] w-[50vw] rounded-full blur-[140px] transition-all duration-[2000ms] ease-in-out delay-75 ${
            voiceSession?.status === 'listening' ? 'bg-teal-500/30 -translate-x-[5%] -translate-y-[5%] scale-110' : 
            voiceSession?.status === 'processing' ? 'bg-fuchsia-500/30 -translate-x-[15%] opacity-80 scale-125 animate-[pulse_3s_ease-in-out_infinite]' :
            voiceSession?.status === 'speaking' ? 'bg-indigo-500/30 -translate-y-[5%] scale-105' : 'bg-transparent opacity-0 scale-50'
          }`} />

          {/* Inset Screen Edge Glow */}
          <div className={`absolute inset-0 transition-all duration-[1500ms] ${
            voiceSession?.status === 'listening' ? 'shadow-[inset_0_0_150px_rgba(16,185,129,0.15)] opacity-100' : 
            voiceSession?.status === 'processing' ? 'shadow-[inset_0_0_150px_rgba(168,85,247,0.15)] opacity-100' :
            voiceSession?.status === 'speaking' ? 'shadow-[inset_0_0_150px_rgba(59,130,246,0.15)] opacity-100' : 'opacity-0'
          }`} />
        </div>

        <div className="relative z-10 w-full">
        {loadError && (
          <GlassCard className="border border-red-500/20 bg-red-500/10 p-5 sm:p-6 mb-6">
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

        {/* Header (Responsive, compact on mobile) */}
        <GlassCard className="overflow-hidden p-4 sm:p-6 xl:p-8">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            
            {/* Left side: Greeting text and Mobile Avatar */}
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 sm:space-y-3">
                <div className="hidden sm:inline-flex items-center rounded-full border border-white/5 bg-black/20 p-1 pr-4 backdrop-blur-md shadow-inner">
                  <span className="inline-flex items-center rounded-full bg-primary-500/20 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-primary-300">
                    Dashboard
                  </span>
                  <span className="ml-3 text-[11px] font-medium text-white/45 tracking-wider flex items-center gap-1.5 opacity-80">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {currentTime}
                  </span>
                </div>
                <div className="space-y-1 sm:space-y-2">
                  <h1 className="flex items-center gap-2 sm:gap-3 text-2xl font-semibold tracking-tight text-white sm:text-4xl xl:text-[2.8rem]">
                    <span className="text-3xl sm:text-5xl">{greetingIcon}</span>
                    <span className="truncate max-w-[200px] min-[400px]:max-w-[260px] sm:max-w-none">{greetingText}, <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400">{displayName}</span></span>
                  </h1>
                  <p className="hidden max-w-2xl text-xs leading-5 text-white/50 sm:block sm:text-sm sm:leading-6">
                    Keep track of your schedule, pending tasks, and AI recommendations from one calm control panel.
                  </p>
                </div>
              </div>

              {/* Mobile Avatar (Visible only < xl) */}
              <div className="flex xl:hidden shrink-0 mt-1 sm:mt-0">
                <button
                  onClick={() => setShowAvatarCustomization(true)}
                  className="group relative h-10 w-10 sm:h-12 sm:w-12 shrink-0 overflow-hidden rounded-full border-2 border-white/10 transition-all hover:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-bg shadow-lg hover:shadow-primary-500/30"
                  title="Customize Avatar"
                >
                  {user?.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img 
                      src={user.avatar_url} 
                       alt="User Avatar" 
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary-500/20 to-accent-500/20 text-base sm:text-lg font-bold uppercase text-primary-200">
                      {displayName.charAt(0)}
                    </div>
                  )}
                  {/* Hover Edit Overlay */}
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100">
                    <svg className="h-4 w-4 sm:h-5 sm:w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </div>
                </button>
              </div>
            </div>

            {/* Right Side: Actions & Voice Agent Indicator */}
            <div className="flex flex-row flex-nowrap items-center gap-2 sm:gap-3 xl:justify-end">
              <div className="flex-1 sm:flex-none flex items-center justify-between sm:justify-start gap-3 rounded-xl sm:rounded-2xl border border-white/10 bg-black/20 px-3 py-2.5 sm:px-4 sm:py-3 overflow-hidden">
                <div className="flex items-center gap-2 sm:gap-3">
                  <VoiceActivityIndicator size="sm" showStatus={false} />
                  <p className="text-[10px] sm:text-xs uppercase tracking-[0.1em] sm:tracking-[0.2em] text-white/45 hidden min-[360px]:block">Voice Agent</p>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-2 border-l border-white/10 pl-2 sm:pl-3 ml-auto">
                  <span className="relative flex h-2 w-2 sm:h-2.5 sm:w-2.5">
                    {voiceSession?.status && voiceSession.status !== 'idle' && (
                      <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${voiceStatus.dot}`}></span>
                    )}
                    <span className={`relative inline-flex h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full ${voiceStatus.dot} ${voiceSession?.status !== 'idle' ? 'shadow-[0_0_8px_currentColor]' : ''}`} />
                  </span>
                  <span className={`text-[11px] sm:text-sm font-medium ${voiceStatus.tone}`}>{voiceStatus.label}</span>
                </div>
              </div>

              <Link
                href="/tasks"
                className="inline-flex h-10 sm:h-12 shrink-0 items-center justify-center rounded-xl sm:rounded-2xl bg-primary-600 px-4 sm:px-5 text-xs sm:text-sm font-medium text-white transition-all hover:bg-primary-500 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)]"
              >
                Tasks
              </Link>
              
              <button
                onClick={() => setIsFocusMode(!isFocusMode)}
                className={`inline-flex h-10 sm:h-12 shrink-0 items-center justify-center rounded-xl sm:rounded-2xl border-2 px-3 sm:px-4 text-xs sm:text-sm font-medium transition-all focus:outline-none shadow-lg ${
                  isFocusMode 
                    ? 'border-accent-500 bg-accent-500 text-white shadow-accent-500/40 hover:bg-accent-600 hover:border-accent-600' 
                    : 'border-white/10 bg-white/5 text-white/80 hover:bg-white/10 hover:text-white'
                }`}
                title="Toggle Focus Mode"
              >
                <svg className="mr-0 sm:mr-2 h-4 w-4 sm:h-5 sm:w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <circle cx="12" cy="12" r="6"></circle>
                  <circle cx="12" cy="12" r="2"></circle>
                </svg>
                <span className="hidden sm:inline-block">{isFocusMode ? 'Exit Zen' : 'Zen Mode'}</span>
              </button>
              
              {/* Desktop Avatar (Visible only >= xl) */}
              <div className="hidden xl:flex shrink-0 ml-2">
                <button
                  onClick={() => setShowAvatarCustomization(true)}
                  className="group relative h-12 w-12 shrink-0 overflow-hidden rounded-full border-2 border-white/10 transition-all hover:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-bg shadow-lg hover:shadow-primary-500/30"
                  title="Customize Avatar"
                >
                  {user?.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img 
                      src={user.avatar_url} 
                       alt="User Avatar" 
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary-500/20 to-accent-500/20 text-lg font-bold uppercase text-primary-200">
                      {displayName.charAt(0)}
                    </div>
                  )}
                  {/* Hover Edit Overlay */}
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100">
                    <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Bento Box Grid Dashboard */}
        <div className={`mt-6 grid gap-4 sm:gap-6 transition-all duration-700 ease-in-out relative ${
          isFocusMode ? 'grid-cols-1 max-w-4xl mx-auto' : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-4 xl:auto-rows-[minmax(130px,1fr)]'
        }`}>
          
          {/* Quick Stats - Top on mobile, Left on large screens */}
          <div className={`grid grid-cols-2 sm:grid-cols-3 xl:flex xl:flex-col gap-4 sm:gap-6 transition-all duration-500 ease-in-out origin-top ${
            isFocusMode ? 'opacity-0 scale-95 pointer-events-none absolute -z-10 w-0 h-0 overflow-hidden' : 'md:col-span-2 xl:col-span-1 xl:row-span-3 opacity-100 scale-100 relative z-10'
          }`}>
            <DashboardStatCard
              title="Today"
              value={todayTasks.length}
              subtitle="Tasks planned for today"
              tone="primary"
              progress={todayProgress}
              className="col-span-1 h-full xl:flex-1 flex flex-col justify-center shadow-lg hover:shadow-primary-500/10 transition-shadow"
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 8l2 2 4-4" />
                </svg>
              }
            />
            <DashboardStatCard
              title="Next"
              value={upcomingEvents.length}
              subtitle="Upcoming calendar events"
              tone="blue"
              sparklineData={eventsSparkline}
              className="col-span-1 h-full xl:flex-1 flex flex-col justify-center shadow-lg hover:shadow-blue-500/10 transition-shadow"
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              }
            />
            <DashboardStatCard
              title="Pending"
              value={pendingTasks.length}
              subtitle="Items waiting for action"
              tone="amber"
              progress={pendingProgress}
              className="col-span-2 sm:col-span-1 h-full xl:flex-1 flex flex-col justify-center shadow-lg hover:shadow-amber-500/10 transition-shadow"
              icon={
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
          </div>

          {/* Timeline - Tall */}
          <div className={`min-w-0 flex flex-col transition-all duration-700 ease-in-out ${
            isFocusMode ? 'col-span-1 h-[75vh] min-h-[500px]' : 'md:col-span-1 xl:col-span-1 xl:row-span-3'
          }`}>
            <GlassCard className={`flex-1 p-5 sm:p-6 overflow-hidden flex flex-col shadow-lg transition-all duration-700 ${
              isFocusMode ? 'border-accent-500/40 ring-1 ring-accent-500/20 shadow-[0_0_30px_rgba(34,211,238,0.15)] bg-slate-900/40' : 'border-white/5 hover:border-white/10'
            }`}>
              {isFocusMode && (
                <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-accent-500"></span>
                    </span>
                    <span className="text-sm font-bold uppercase tracking-widest text-accent-400">Deep Work Mode Activated</span>
                  </div>
                </div>
              )}
              <TaskTimeline maxItems={isFocusMode ? 15 : 8} />
            </GlassCard>
          </div>

          {/* Calendar - Wide & Tall */}
          <div className={`min-w-0 flex flex-col transition-all duration-500 ease-in-out origin-center ${
            isFocusMode ? 'opacity-0 scale-95 pointer-events-none absolute -z-10 w-0 h-0 overflow-hidden' : 'md:col-span-1 xl:col-span-2 xl:row-span-3 opacity-100 scale-100 relative z-10'
          }`}>
            <GlassCard className="flex-1 p-5 sm:p-6 overflow-hidden flex flex-col shadow-lg border-white/5 hover:border-white/10 transition-colors">
              <CalendarIntegrationView />
            </GlassCard>
          </div>

          {/* AI Insights - Very Wide Bottom */}
          <div className={`min-w-0 flex flex-col transition-all duration-500 ease-in-out origin-bottom ${
            isFocusMode ? 'opacity-0 scale-95 pointer-events-none absolute -z-10 w-0 h-0 overflow-hidden text-transparent' : 'md:col-span-2 xl:col-span-4 xl:row-span-2 opacity-100 scale-100 relative z-10'
          }`}>
            <GlassCard className="flex-1 p-5 sm:p-6 shadow-xl border-accent-500/10 relative overflow-hidden group">
              <div className="absolute inset-x-0 -top-px h-px w-full bg-gradient-to-r from-transparent via-accent-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
              <AIInsightsDashboard />
            </GlassCard>
          </div>
        </div>

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

      </div>

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
