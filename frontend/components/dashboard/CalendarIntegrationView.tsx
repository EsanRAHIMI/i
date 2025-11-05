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
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [suggestions, setSuggestions] = useState<SchedulingSuggestion[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false);

  // Check if calendar is connected
  useEffect(() => {
    // In a real implementation, this would check the user's calendar connection status
    setIsConnected(!!user?.email); // Mock: assume connected if user exists
  }, [user]);

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
        setIsConnected(true);
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Calendar Integration</h2>
          <p className="text-gray-400 text-sm">Smart scheduling and calendar management</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="bg-dark-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
          />
          
          {isConnected ? (
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full" />
              <span className="text-sm text-green-400">Connected</span>
            </div>
          ) : (
            <button
              onClick={connectCalendar}
              disabled={isConnecting}
              className="px-3 py-1 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white text-sm rounded transition-colors"
            >
              {isConnecting ? 'Connecting...' : 'Connect Google Calendar'}
            </button>
          )}
        </div>
      </div>

      {isConnected ? (
        <div className="space-y-6">
          {/* Today's Schedule */}
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white">
                Schedule for {formatDate(selectedDate)}
              </h3>
              <span className="text-sm text-gray-400">
                {dayEvents.length} event{dayEvents.length !== 1 ? 's' : ''}
              </span>
            </div>
            
            {dayEvents.length > 0 ? (
              <div className="space-y-2">
                {dayEvents
                  .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
                  .map((event) => (
                    <div key={event.id} className="flex items-center space-x-3 p-2 bg-dark-900 rounded">
                      <div className="w-2 h-8 bg-blue-500 rounded" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-white">{event.title}</p>
                        <p className="text-xs text-gray-400">
                          {formatTime(event.start_time)} - {formatTime(event.end_time)}
                        </p>
                      </div>
                      {event.ai_generated && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
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
          <div className="bg-dark-800 rounded-lg border border-gray-700 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white">AI Scheduling Suggestions</h3>
              <button
                onClick={generateSuggestions}
                disabled={isGeneratingSuggestions}
                className="px-3 py-1 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white text-sm rounded transition-colors"
              >
                {isGeneratingSuggestions ? 'Analyzing...' : 'Generate Suggestions'}
              </button>
            </div>
            
            {suggestions.length > 0 ? (
              <div className="space-y-3">
                {suggestions.map((suggestion) => (
                  <div key={suggestion.id} className="p-3 bg-dark-900 rounded-lg border border-gray-600">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        <div className="p-1 bg-dark-700 rounded">
                          {getSuggestionIcon(suggestion.type)}
                        </div>
                        <div className="flex-1">
                          <h4 className="text-sm font-medium text-white">{suggestion.title}</h4>
                          <p className="text-xs text-gray-400 mt-1">{suggestion.reason}</p>
                          <div className="flex items-center space-x-4 mt-2">
                            <span className="text-xs text-gray-500">
                              {formatTime(suggestion.suggestedTime)} ({suggestion.duration}min)
                            </span>
                            <span className="text-xs text-primary-400">
                              {Math.round(suggestion.confidence * 100)}% confidence
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex space-x-2">
                        <button
                          onClick={() => acceptSuggestion(suggestion)}
                          className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded transition-colors"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => setSuggestions(prev => prev.filter(s => s.id !== suggestion.id))}
                          className="px-2 py-1 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded transition-colors"
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
                <svg className="w-12 h-12 text-gray-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <p className="text-gray-400">No suggestions available</p>
                <p className="text-gray-500 text-sm">Click "Generate Suggestions" to get AI-powered scheduling recommendations</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <h3 className="text-lg font-medium text-white mb-2">Connect Your Calendar</h3>
          <p className="text-gray-400 max-w-md mx-auto mb-6">
            Connect your Google Calendar to enable intelligent scheduling suggestions, 
            automatic event creation, and seamless calendar management through voice commands.
          </p>
          <button
            onClick={connectCalendar}
            disabled={isConnecting}
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            {isConnecting ? 'Connecting...' : 'Connect Google Calendar'}
          </button>
        </div>
      )}
    </div>
  );
}