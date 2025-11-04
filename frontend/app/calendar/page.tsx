'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { CalendarConnection, CalendarEvent } from '@/types';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

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

      // Use frontend callback URL - backend will handle OAuth and redirect back to frontend
      const redirectUri = `${typeof window !== 'undefined' ? window.location.origin : 'http://localhost'}/calendar/callback`;

      // Start OAuth flow
      const { authorization_url } = await apiClient.connectCalendar(redirectUri);

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
      <div className="p-6 lg:p-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">تقویم گوگل</h1>
        <p className="text-gray-400 mt-1">همگام‌سازی و مدیریت رویدادهای گوگل کالندر شما</p>
      </div>

      {error && (
        <div className="mb-6 bg-red-900/20 border border-red-500 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {!connection || !connection.connected ? (
        <div className="bg-dark-800 rounded-lg border border-gray-700 p-8">
          <div className="text-center">
            <GlowingOrb size="large" className="mx-auto mb-6" />
            <h2 className="text-xl font-semibold text-white mb-2">
              اتصال به گوگل کالندر
            </h2>
            <p className="text-gray-400 max-w-md mx-auto mb-6">
              برای همگام‌سازی رویدادهای گوگل کالندر و استفاده از پیشنهادات هوشمند برنامه‌ریزی، 
              لطفاً به حساب گوگل خود متصل شوید.
            </p>
            <button
              onClick={handleConnect}
              disabled={isConnecting}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isConnecting ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>در حال اتصال...</span>
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  <span>اتصال به گوگل کالندر</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Connection Status */}
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-green-400"
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
                  <h3 className="text-lg font-semibold text-white">
                    متصل به گوگل کالندر
                  </h3>
                  {connection.last_sync_at && (
                    <p className="text-sm text-gray-400">
                      آخرین همگام‌سازی: {formatDate(connection.last_sync_at)}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleSync}
                  disabled={isSyncing}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSyncing ? (
                    <span className="flex items-center gap-2">
                      <LoadingSpinner size="sm" />
                      در حال همگام‌سازی...
                    </span>
                  ) : (
                    'همگام‌سازی'
                  )}
                </button>
                <button
                  onClick={handleDisconnect}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  قطع اتصال
                </button>
              </div>
            </div>
          </div>

          {/* Events List */}
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">رویدادهای اخیر</h2>
            
            {events.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400">هیچ رویدادی یافت نشد</p>
                <p className="text-sm text-gray-500 mt-2">
                  رویدادهای گوگل کالندر شما پس از همگام‌سازی نمایش داده می‌شوند
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {events.map((event) => (
                  <div
                    key={event.id}
                    className="bg-dark-700 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-white mb-1">
                          {event.title}
                        </h3>
                        {event.description && (
                          <p className="text-gray-400 text-sm mb-2">{event.description}</p>
                        )}
                        <div className="flex flex-wrap gap-4 text-sm text-gray-400">
                          <div className="flex items-center gap-1">
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                              />
                            </svg>
                            <span>{formatDate(event.start_time)}</span>
                          </div>
                          {event.location && (
                            <div className="flex items-center gap-1">
                              <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                                />
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                                />
                              </svg>
                              <span>{event.location}</span>
                            </div>
                          )}
                        </div>
                        {event.attendees.length > 0 && (
                          <div className="mt-2 text-sm text-gray-400">
                            شرکت‌کنندگان: {event.attendees.join(', ')}
                          </div>
                        )}
                      </div>
                      {event.ai_generated && (
                        <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded">
                          AI
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
