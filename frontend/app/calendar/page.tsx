'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { CalendarConnection, CalendarEvent } from '@/types';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { GlassCard } from '@/components/ui/GlassCard';
import { AppPageShell } from '@/components/layout/AppPageShell';

export default function CalendarPage() {
  const [connection, setConnection] = useState<CalendarConnection | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCalendarData();
  }, []);

  const loadCalendarData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load connection status
      const conn = await apiClient.getCalendarConnection();
      setConnection(conn);

      // Load events if connected
      if (conn?.connected) {
        const calendarEvents = await apiClient.getEvents();
        setEvents(calendarEvents);
      }
    } catch (err: any) {
      console.error('Failed to load calendar data:', err);
      setError(err.response?.data?.detail || 'خطا در بارگذاری اطلاعات کالندر');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnect = async () => {
    try {
      setIsConnecting(true);
      setError(null);

      // Start OAuth flow - Backend will use its own configured GOOGLE_REDIRECT_URI
      const { authorization_url } = await apiClient.connectCalendar();

      // Redirect to Google OAuth
      window.location.href = authorization_url;
    } catch (err: any) {
      console.error('Failed to initiate calendar connection:', err);
      setError(err.response?.data?.detail || 'خطا در اتصال به گوگل کالندر');
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('آیا مطمئن هستید که می‌خواهید اتصال کالندر را قطع کنید؟')) {
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      await apiClient.disconnectCalendar();
      setConnection(null);
      setEvents([]);
      await loadCalendarData();
    } catch (err: any) {
      console.error('Failed to disconnect calendar:', err);
      setError(err.response?.data?.detail || 'خطا در قطع اتصال');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setIsSyncing(true);
      setError(null);
      await apiClient.syncCalendar();
      await loadCalendarData();
    } catch (err: any) {
      console.error('Failed to sync calendar:', err);
      setError(err.response?.data?.detail || 'خطا در همگام‌سازی کالندر');
    } finally {
      setIsSyncing(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  if (isLoading && !connection) {
    return (
      <AppPageShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="relative">
            <div className="absolute inset-0 bg-primary-500/20 blur-3xl rounded-full animate-pulse"></div>
            <LoadingSpinner size="lg" className="relative z-10" />
          </div>
        </div>
      </AppPageShell>
    );
  }

  return (
    <AppPageShell>
      <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto">
        <GlassCard className="overflow-hidden p-6 sm:p-8">
          <div className="space-y-3">
            <span className="inline-flex items-center rounded-full bg-blue-500/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-blue-400 border border-blue-500/20">
              Calendar Integration
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Google <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">Events</span>
            </h1>
            <p className="max-w-2xl text-sm leading-relaxed text-white/50">
              همگام‌سازی و مدیریت رویدادهای تقویم گوگل (Google Calendar) با دستیار هوشمند شما.
            </p>
          </div>
        </GlassCard>

        {error && (
          <GlassCard className="bg-red-500/5 border-red-500/30 p-4">
            <p className="text-red-400 font-medium text-sm">{error}</p>
          </GlassCard>
        )}

        {!connection || !connection.connected ? (
          <GlassCard className="p-8 sm:p-12 relative overflow-hidden group border-white/5 transition-all duration-700">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
            <div className="text-center relative z-10">
              <div className="relative mb-6">
                <div className="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full animate-pulse"></div>
                <GlowingOrb size="large" className="mx-auto" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-4">
                اتصال به گوگل کالندر
              </h2>
              <p className="text-white/60 max-w-md mx-auto mb-8 leading-relaxed text-sm">
                برای همگام‌سازی رویدادهای گوگل کالندر و استفاده از برنامه‌ریزی هوشمند، 
                لطفاً به حساب گوگل خود متصل شوید و اجازه دسترسی بدهید.
              </p>
              <button
                onClick={handleConnect}
                disabled={isConnecting}
                className="inline-flex items-center gap-3 px-8 py-4 bg-white/5 border border-white/10 hover:border-blue-500/50 text-white font-medium rounded-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(59,130,246,0.15)] hover:shadow-[0_0_30px_rgba(59,130,246,0.25)] hover:bg-white/10 backdrop-blur-md"
              >
                {isConnecting ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span>در حال اتصال...</span>
                  </>
                ) : (
                  <>
                    <svg
                      className="w-6 h-6"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                    <span>اتصال به Google Calendar</span>
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        ) : (
          <div className="space-y-6">
            {/* Connection Status */}
            <GlassCard className="p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.15)] rounded-2xl flex items-center justify-center text-emerald-400">
                    <svg
                      className="w-6 h-6"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">
                      متصل به Google Calendar
                    </h3>
                    {connection.last_sync_at && (
                      <p className="text-sm font-medium text-white/40 mt-1">
                        آخرین همگام‌سازی: {formatDate(connection.last_sync_at)}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleSync}
                    disabled={isSyncing}
                    className="px-5 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white text-sm font-medium transition-all focus:outline-none shadow-lg disabled:opacity-50"
                  >
                    {isSyncing ? (
                      <span className="flex items-center gap-2">
                        <LoadingSpinner size="sm" />
                        در حال بارگذاری...
                      </span>
                    ) : (
                      'Sync Now'
                    )}
                  </button>
                  <button
                    onClick={handleDisconnect}
                    className="px-5 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/30 text-red-400 text-sm font-medium transition-all focus:outline-none shadow-lg"
                  >
                    Disconnect
                  </button>
                </div>
              </div>
            </GlassCard>

            {/* Events List */}
            <GlassCard className="p-6 min-h-[400px]">
              <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                رویدادهای اخیر
              </h2>
              
              {events.length === 0 ? (
                <div className="text-center py-16 flex flex-col items-center">
                  <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center border border-white/10 mb-4 opacity-50">
                    <svg className="h-8 w-8 text-white/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-white/80 font-medium">هیچ رویدادی یافت نشد</p>
                  <p className="text-sm text-white/40 mt-2">
                    جهت دریافت رویدادها دکمه Sync Now را بزنید
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {events.map((event) => (
                    <div
                      key={event.id}
                      className="group relative bg-white/5 rounded-2xl p-5 border border-white/10 hover:border-blue-500/30 hover:bg-white/10 transition-all duration-300 shadow-lg overflow-hidden"
                    >
                      <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-blue-500 to-purple-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>

                    <div className="relative z-10">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0 pr-4">
                          <h3 className="text-lg font-bold text-white mb-2 truncate">
                            {event.title}
                          </h3>
                          {event.description && (
                            <p className="text-white/50 text-sm mb-4 line-clamp-2">{event.description}</p>
                          )}
                          <div className="flex flex-col gap-2 text-xs text-white/60 font-medium">
                            <div className="flex items-center gap-2">
                              <div className="w-5 h-5 rounded bg-white/10 flex items-center justify-center shrink-0">
                                <svg
                                  className="w-3 h-3 text-blue-400"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                              </div>
                              <span className="truncate">{formatDate(event.start_time)}</span>
                            </div>
                            {event.location && (
                              <div className="flex items-center gap-2">
                                <div className="w-5 h-5 rounded bg-white/10 flex items-center justify-center shrink-0">
                                  <svg
                                    className="w-3 h-3 text-red-400"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                  </svg>
                                </div>
                                <span className="truncate text-red-100/60">{event.location}</span>
                              </div>
                            )}
                          </div>
                          {event.attendees.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-white/5 text-xs text-white/40">
                              شرکت‌کنندگان: {event.attendees.join(', ')}
                            </div>
                          )}
                        </div>
                        {event.ai_generated && (
                          <span className="shrink-0 px-2 py-1 bg-purple-500/20 border border-purple-500/30 text-purple-300 text-[10px] font-bold uppercase tracking-wider rounded-md">
                            AI
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>
        </div>
      )}
      </div>
    </AppPageShell>
  );
}
