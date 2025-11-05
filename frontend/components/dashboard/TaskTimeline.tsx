'use client';

import { useState, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { formatTime, formatDate, getRelativeTime } from '@/lib/utils';
import { Task, CalendarEvent } from '@/types';

interface TimelineItem {
  id: string;
  type: 'task' | 'event';
  title: string;
  description?: string;
  time: string;
  status: string;
  priority?: number;
  ai_generated?: boolean;
  completed?: boolean;
}

interface TaskTimelineProps {
  className?: string;
  showDate?: string; // ISO date string, defaults to today
  maxItems?: number;
}

export function TaskTimeline({ className, showDate, maxItems = 10 }: TaskTimelineProps) {
  const { tasks, events } = useAppStore();
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'task' | 'event'>('all');
  const [selectedPriority, setSelectedPriority] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const targetDate = showDate || new Date().toISOString().split('T')[0];

  // Combine and filter timeline items
  const timelineItems = useMemo(() => {
    const items: TimelineItem[] = [];

    // Add tasks
    tasks.forEach(task => {
      const taskDate = task.due_date ? new Date(task.due_date).toISOString().split('T')[0] : targetDate;
      if (taskDate === targetDate) {
        items.push({
          id: task.id,
          type: 'task',
          title: task.title,
          description: task.description,
          time: task.due_date || new Date().toISOString(),
          status: task.status,
          priority: task.priority,
          ai_generated: task.created_by_ai,
          completed: task.status === 'completed'
        });
      }
    });

    // Add events
    events.forEach(event => {
      const eventDate = new Date(event.start_time).toISOString().split('T')[0];
      if (eventDate === targetDate) {
        items.push({
          id: event.id,
          type: 'event',
          title: event.title,
          description: event.description,
          time: event.start_time,
          status: 'scheduled',
          ai_generated: event.ai_generated
        });
      }
    });

    // Filter by type
    let filteredItems = items;
    if (selectedFilter !== 'all') {
      filteredItems = items.filter(item => item.type === selectedFilter);
    }

    // Filter by priority (tasks only)
    if (selectedPriority !== 'all') {
      filteredItems = filteredItems.filter(item => {
        if (item.type !== 'task') return true;
        
        const priority = item.priority || 3;
        switch (selectedPriority) {
          case 'high':
            return priority >= 4;
          case 'medium':
            return priority === 3;
          case 'low':
            return priority <= 2;
          default:
            return true;
        }
      });
    }

    // Sort by time
    filteredItems.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

    return filteredItems.slice(0, maxItems);
  }, [tasks, events, targetDate, selectedFilter, selectedPriority, maxItems]);

  const getItemIcon = (item: TimelineItem) => {
    if (item.type === 'task') {
      return item.completed ? (
        <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 8l2 2 4-4" />
        </svg>
      );
    } else {
      return (
        <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    }
  };

  const getPriorityColor = (priority?: number) => {
    if (!priority) return 'bg-gray-500';
    
    if (priority >= 4) return 'bg-red-500';
    if (priority === 3) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusColor = (item: TimelineItem) => {
    if (item.type === 'task') {
      switch (item.status) {
        case 'completed':
          return 'border-green-500 bg-green-500/10';
        case 'in_progress':
          return 'border-blue-500 bg-blue-500/10';
        case 'pending':
          return 'border-yellow-500 bg-yellow-500/10';
        default:
          return 'border-gray-500 bg-gray-500/10';
      }
    } else {
      return 'border-blue-500 bg-blue-500/10';
    }
  };

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Timeline</h2>
          <p className="text-gray-400 text-sm">{formatDate(targetDate)}</p>
        </div>
        
        {/* Filters */}
        <div className="flex space-x-2">
          <select
            value={selectedFilter}
            onChange={(e) => setSelectedFilter(e.target.value as any)}
            className="bg-dark-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
          >
            <option value="all" className="bg-dark-800 text-gray-200">All Items</option>
            <option value="task" className="bg-dark-800 text-gray-200">Tasks Only</option>
            <option value="event" className="bg-dark-800 text-gray-200">Events Only</option>
          </select>
          
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value as any)}
            className="bg-dark-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
          >
            <option value="all" className="bg-dark-800 text-gray-200">All Priorities</option>
            <option value="high" className="bg-dark-800 text-gray-200">High Priority</option>
            <option value="medium" className="bg-dark-800 text-gray-200">Medium Priority</option>
            <option value="low" className="bg-dark-800 text-gray-200">Low Priority</option>
          </select>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-4">
        {timelineItems.length > 0 ? (
          timelineItems.map((item, index) => (
            <div key={item.id} className="relative">
              {/* Timeline line */}
              {index < timelineItems.length - 1 && (
                <div className="absolute left-6 top-12 w-0.5 h-8 bg-gray-600" />
              )}
              
              {/* Timeline item */}
              <div className={`flex items-start space-x-4 p-4 rounded-lg border ${getStatusColor(item)}`}>
                {/* Icon */}
                <div className="flex-shrink-0 w-8 h-8 bg-dark-700 rounded-full flex items-center justify-center">
                  {getItemIcon(item)}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className={`text-sm font-medium ${item.completed ? 'line-through text-gray-400' : 'text-white'}`}>
                        {item.title}
                      </h3>
                      
                      {item.description && (
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                          {item.description}
                        </p>
                      )}
                      
                      <div className="flex items-center space-x-2 mt-2">
                        <span className="text-xs text-gray-500">
                          {formatTime(item.time)}
                        </span>
                        
                        {item.ai_generated && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800">
                            AI
                          </span>
                        )}
                        
                        {item.type === 'task' && item.priority && (
                          <div className="flex items-center space-x-1">
                            <div className={`w-2 h-2 rounded-full ${getPriorityColor(item.priority)}`} />
                            <span className="text-xs text-gray-500">
                              P{item.priority}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Status badge */}
                    <span className={`
                      inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                      ${item.type === 'task' 
                        ? item.completed 
                          ? 'bg-green-100 text-green-800'
                          : item.status === 'in_progress'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-yellow-100 text-yellow-800'
                        : 'bg-blue-100 text-blue-800'
                      }
                    `}>
                      {item.type === 'task' ? item.status.replace('_', ' ') : 'scheduled'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-700 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-gray-400">No items for this day</p>
            <p className="text-gray-500 text-sm mt-1">Your schedule is clear</p>
          </div>
        )}
      </div>

      {/* Summary */}
      {timelineItems.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-white">
                {timelineItems.filter(item => item.type === 'task').length}
              </p>
              <p className="text-xs text-gray-400">Tasks</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {timelineItems.filter(item => item.type === 'event').length}
              </p>
              <p className="text-xs text-gray-400">Events</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {timelineItems.filter(item => item.ai_generated).length}
              </p>
              <p className="text-xs text-gray-400">AI Generated</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}