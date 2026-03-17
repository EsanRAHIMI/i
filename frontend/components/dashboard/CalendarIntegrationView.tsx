'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { formatTime, formatDate } from '@/lib/utils';
import { CalendarEvent } from '@/types';

interface CalendarIntegrationViewProps {
  className?: string;
}

interface SchedulingSuggestion {
  id: string;
  title: string;
  suggestedTime: string;
  duration: number; // minutes
  reason: string;
  confidence: number;
  type: 'meeting' | 'focus_time' | 'break' | 'task_block';
}

export function CalendarIntegrationView({ className }: CalendarIntegrationViewProps) {
  const { events, user, setEvents } = useAppStore();
  const [hasConnectedCalendar, setHasConnectedCalendar] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [suggestions, setSuggestions] = useState<SchedulingSuggestion[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false);
  const isConnected = hasConnectedCalendar || !!user?.email;

  // Generate scheduling suggestions
  const generateSuggestions = () => {
    setIsGeneratingSuggestions(true);
    
    // Mock suggestions based on current events
    const dayEvents = events.filter(event => {
      const eventDate = new Date(event.start_time).toISOString().split('T')[0];
      return eventDate === selectedDate;
    });

    const mockSuggestions: SchedulingSuggestion[] = [];

    // Find gaps for focus time
    if (dayEvents.length > 0) {
      const sortedEvents = dayEvents.sort((a, b) => 
        new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      );

      // Suggest focus time in the morning if no early meetings
      const firstEvent = sortedEvents[0];
      const firstEventTime = new Date(firstEvent.start_time).getHours();
      
      if (firstEventTime > 9) {
        mockSuggestions.push({
          id: 'focus-1',
          title: 'Deep Work Session',
          suggestedTime: `${selectedDate}T09:00:00`,
          duration: 120,
          reason: 'You have a 2-hour gap before your first meeting. Perfect for focused work.',
          confidence: 0.9,
          type: 'focus_time'
        });
      }

      // Suggest breaks between back-to-back meetings
      for (let i = 0; i < sortedEvents.length - 1; i++) {
        const currentEnd = new Date(sortedEvents[i].end_time);
        const nextStart = new Date(sortedEvents[i + 1].start_time);
        const gapMinutes = (nextStart.getTime() - currentEnd.getTime()) / (1000 * 60);

        if (gapMinutes < 15 && gapMinutes > 0) {
          mockSuggestions.push({
            id: `break-${i}`,
            title: 'Quick Break',
            suggestedTime: currentEnd.toISOString(),
            duration: Math.floor(gapMinutes),
            reason: 'Short break between meetings to recharge.',
            confidence: 0.7,
            type: 'break'
          });
        }
      }
    } else {
      // No events - suggest a structured day
      mockSuggestions.push(
        {
          id: 'focus-morning',
          title: 'Morning Focus Block',
          suggestedTime: `${selectedDate}T09:00:00`,
          duration: 180,
          reason: 'Your calendar is free. Start with a productive morning session.',
          confidence: 0.8,
          type: 'focus_time'
        },
        {
          id: 'break-lunch',
          title: 'Lunch Break',
          suggestedTime: `${selectedDate}T12:00:00`,
          duration: 60,
          reason: 'Schedule a proper lunch break to maintain energy.',
          confidence: 0.9,
          type: 'break'
        },
        {
          id: 'focus-afternoon',
          title: 'Afternoon Task Block',
          suggestedTime: `${selectedDate}T14:00:00`,
          duration: 120,
          reason: 'Afternoon slot for completing pending tasks.',
          confidence: 0.7,
          type: 'task_block'
        }
      );
    }

    setTimeout(() => {
      setSuggestions(mockSuggestions);
      setIsGeneratingSuggestions(false);
    }, 1500);
  };

  const connectCalendar = async () => {
    try {
      setIsConnecting(true);
      const result = await apiClient.connectCalendar();
      
      // In a real implementation, this would redirect to Google OAuth
      window.open(result.authorization_url, '_blank');
      
      // Mock successful connection after a delay
      setTimeout(() => {
        setHasConnectedCalendar(true);
        setIsConnecting(false);
      }, 3000);
    } catch (error) {
      console.error('Failed to connect calendar:', error);
      setIsConnecting(false);
    }
  };

  const acceptSuggestion = async (suggestion: SchedulingSuggestion) => {
    try {
      const newEvent: Omit<CalendarEvent, 'id' | 'user_id' | 'created_at'> = {
        title: suggestion.title,
        description: `AI Suggested: ${suggestion.reason}`,
        start_time: suggestion.suggestedTime,
        end_time: new Date(
          new Date(suggestion.suggestedTime).getTime() + suggestion.duration * 60000
        ).toISOString(),
        location: '',
        attendees: [],
        ai_generated: true
      };

      const createdEvent = await apiClient.createEvent(newEvent);
      setEvents([...events, createdEvent]);
      
      // Remove the accepted suggestion
      setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
    } catch (error) {
      console.error('Failed to create event:', error);
    }
  };

  const getSuggestionIcon = (type: SchedulingSuggestion['type']) => {
    switch (type) {
      case 'focus_time':
        return (
          <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        );
      case 'meeting':
        return (
          <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        );
      case 'break':
        return (
          <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'task_block':
        return (
          <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 8l2 2 4-4" />
          </svg>
        );
    }
  };

  const dayEvents = events.filter(event => {
    const eventDate = new Date(event.start_time).toISOString().split('T')[0];
    return eventDate === selectedDate;
  });

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight text-white sm:text-xl">Calendar Integration</h2>
          <p className="text-sm leading-6 text-gray-400">Smart scheduling and calendar management</p>
        </div>
        
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/80 transition-colors focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-primary-500/60 sm:min-w-44 sm:w-auto"
          />
          
          {isConnected ? (
            <div className="inline-flex items-center gap-2 rounded-full border border-green-500/20 bg-green-500/10 px-3 py-2 text-sm font-medium text-green-300">
              <div className="h-2 w-2 rounded-full bg-green-400" />
              <span>Connected</span>
            </div>
          ) : (
            <button
              onClick={connectCalendar}
              disabled={isConnecting}
              className="w-full rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50 sm:w-auto"
            >
              {isConnecting ? 'Connecting...' : 'Connect Google Calendar'}
            </button>
          )}
        </div>
      </div>

      {isConnected ? (
        <div className="space-y-6">
          {/* Today's Schedule */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl sm:p-5">
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-base font-semibold tracking-tight text-white sm:text-lg">
                Schedule for {formatDate(selectedDate)}
              </h3>
              <span className="text-sm font-medium text-gray-400">
                {dayEvents.length} event{dayEvents.length !== 1 ? 's' : ''}
              </span>
            </div>
            
            {dayEvents.length > 0 ? (
              <div className="space-y-2">
                {dayEvents
                  .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
                  .map((event) => (
                    <div key={event.id} className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-3 sm:items-center sm:p-4">
                      <div className="h-10 w-1.5 rounded-full bg-blue-500/70" />
                      <div className="flex-1">
                        <p className="text-sm font-medium leading-6 text-white">{event.title}</p>
                        <p className="text-xs text-gray-400">
                          {formatTime(event.start_time)} - {formatTime(event.end_time)}
                        </p>
                      </div>
                      {event.ai_generated && (
                        <span className="inline-flex items-center rounded-full border border-primary-500/20 bg-primary-500/15 px-2 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-primary-200">
                          AI
                        </span>
                      )}
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-gray-400">No events scheduled</p>
              </div>
            )}
          </div>

          {/* Scheduling Suggestions */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl sm:p-5">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-base font-semibold tracking-tight text-white sm:text-lg">AI Scheduling Suggestions</h3>
              <button
                onClick={generateSuggestions}
                disabled={isGeneratingSuggestions}
                className="w-full rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50 sm:w-auto"
              >
                {isGeneratingSuggestions ? 'Analyzing...' : 'Generate Suggestions'}
              </button>
            </div>
            
            {suggestions.length > 0 ? (
              <div className="space-y-3">
                {suggestions.map((suggestion) => (
                  <div key={suggestion.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                      <div className="flex items-start gap-3">
                        <div className="rounded-xl border border-white/10 bg-white/10 p-2">
                          {getSuggestionIcon(suggestion.type)}
                        </div>
                        <div className="flex-1">
                          <h4 className="text-sm font-medium leading-6 text-white">{suggestion.title}</h4>
                          <p className="mt-1 text-sm leading-6 text-gray-400">{suggestion.reason}</p>
                          <div className="mt-2 flex flex-wrap items-center gap-3">
                            <span className="text-xs text-gray-500">
                              {formatTime(suggestion.suggestedTime)} ({suggestion.duration}min)
                            </span>
                            <span className="text-xs text-primary-400">
                              {Math.round(suggestion.confidence * 100)}% confidence
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <button
                          onClick={() => acceptSuggestion(suggestion)}
                          className="w-full rounded-xl bg-green-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-green-700 sm:w-auto"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => setSuggestions(prev => prev.filter(s => s.id !== suggestion.id))}
                          className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-white/15 sm:w-auto"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-gray-400">
                  {isGeneratingSuggestions
                    ? 'Analyzing your calendar...'
                    : 'No suggestions yet. Generate AI suggestions to optimize your schedule.'}
                </p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="py-12 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-gray-700/70">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="mb-2 text-lg font-semibold tracking-tight text-white">Connect Your Calendar</h3>
          <p className="mx-auto max-w-md text-sm leading-6 text-gray-400">
            Connect your Google Calendar to get AI-powered scheduling suggestions and manage your events.
          </p>
          <button
            onClick={connectCalendar}
            disabled={isConnecting}
            className="mt-4 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
          >
            {isConnecting ? 'Connecting...' : 'Connect Google Calendar'}
          </button>
        </div>
      )}
    </div>
  );
}
