'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { DigitalAvatar } from '@/components/avatar/DigitalAvatar';
import { AvatarCustomization } from '@/components/avatar/AvatarCustomization';
import { VoiceInterface } from '@/components/voice/VoiceInterface';
import { VoiceActivityIndicator } from '@/components/voice/VoiceActivityIndicator';
import { TaskTimeline } from '@/components/dashboard/TaskTimeline';
import { AIInsightsDashboard } from '@/components/dashboard/AIInsightsDashboard';
import { CalendarIntegrationView } from '@/components/dashboard/CalendarIntegrationView';
import FloatingGlassDock from '@/components/voice/FloatingGlassDock';
import { formatTime, getRelativeTime } from '@/lib/utils';
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">
              Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}
            </h1>
            <p className="text-gray-400 mt-1">
              Welcome back, {user?.email?.split('@')[0]}
            </p>
          </div>
          
          <div className="flex items-center space-x-6">
            <VoiceActivityIndicator size="md" />
            <button
              onClick={() => setShowAvatarCustomization(true)}
              className="text-xs text-primary-400 hover:text-primary-300 underline"
            >
              Customize Avatar
            </button>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-primary-600 rounded-lg">
              <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 8l2 2 4-4" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Today's Tasks</p>
              <p className="text-2xl font-bold text-white">{todayTasks.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-green-600 rounded-lg">
              <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Upcoming Events</p>
              <p className="text-2xl font-bold text-white">{upcomingEvents.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-600 rounded-lg">
              <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Pending Tasks</p>
              <p className="text-2xl font-bold text-white">{pendingTasks.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Voice Interface Section */}
      <div className="mb-8 bg-dark-800 rounded-lg border border-gray-700 p-6">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-4">Voice Assistant</h2>
          <VoiceInterface
            onTranscript={(text) => logger.debug('Transcript:', text)}
            onResponse={(response) => logger.debug('Response:', response)}
          />
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Task Timeline */}
        <div className="xl:col-span-1">
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-6">
            <TaskTimeline maxItems={8} />
          </div>
        </div>

        {/* Calendar Integration */}
        <div className="xl:col-span-2">
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-6">
            <CalendarIntegrationView />
          </div>
        </div>
      </div>

      {/* AI Insights Section */}
      <div className="mt-8 bg-dark-800 rounded-lg border border-gray-700 p-6">
        <AIInsightsDashboard />
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
    </div>
  );
}