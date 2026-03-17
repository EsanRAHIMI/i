'use client';

import { useState, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { cn, formatTime, formatDate, getRelativeTime } from '@/lib/utils';
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
          return 'border-green-500/20 bg-green-500/5';
        case 'in_progress':
          return 'border-blue-500/20 bg-blue-500/5';
        case 'pending':
          return 'border-yellow-500/20 bg-yellow-500/5';
        default:
          return 'border-white/15 bg-white/3';
      }
    } else {
      return 'border-blue-500/20 bg-blue-500/5';
    }
  };

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight text-white sm:text-xl">Timeline</h2>
          <p className="text-sm leading-6 text-gray-400">{formatDate(targetDate)}</p>
        </div>
        
        {/* Filters */}
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap xl:justify-end">
          <select
            value={selectedFilter}
            onChange={(e) => setSelectedFilter(e.target.value as any)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/80 transition-colors focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-primary-500/60 sm:min-w-40 sm:w-auto"
          >
            <option value="all" className="bg-dark-950 text-white/80">All Items</option>
            <option value="task" className="bg-dark-950 text-white/80">Tasks Only</option>
            <option value="event" className="bg-dark-950 text-white/80">Events Only</option>
          </select>
          
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value as any)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/80 transition-colors focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-primary-500/60 sm:min-w-44 sm:w-auto"
          >
            <option value="all" className="bg-dark-950 text-white/80">All Priorities</option>
            <option value="high" className="bg-dark-950 text-white/80">High Priority</option>
            <option value="medium" className="bg-dark-950 text-white/80">Medium Priority</option>
            <option value="low" className="bg-dark-950 text-white/80">Low Priority</option>
          </select>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {timelineItems.length > 0 ? (
          timelineItems.map((item, index) => (
            <div key={item.id} className="relative">
              {/* Timeline line */}
              {index < timelineItems.length - 1 && (
                <div className="absolute start-5 top-12 h-8 w-px bg-white/10" />
              )}
              
              {/* Timeline item */}
              <div
                className={cn(
                  'flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl transition-colors sm:gap-4 sm:p-5',
                  getStatusColor(item)
                )}
              >
                {/* Icon */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/10">
                  {getItemIcon(item)}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className={`text-sm font-medium leading-6 ${item.completed ? 'line-through text-gray-400' : 'text-white'}`}>
                        {item.title}
                      </h3>
                      
                      {item.description && (
                        <p className="mt-1 text-sm leading-6 text-gray-400 line-clamp-2">
                          {item.description}
                        </p>
                      )}
                      
                      <div className="mt-3 flex flex-wrap items-center gap-2 gap-y-1">
                        <span className="text-xs font-medium text-gray-500">
                          {formatTime(item.time)}
                        </span>
                        
                        {item.ai_generated && (
                          <span className="inline-flex items-center rounded-full border border-primary-500/20 bg-primary-500/15 px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.18em] text-primary-200">
                            AI
                          </span>
                        )}
                        
                        {item.type === 'task' && item.priority && (
                          <div className="flex items-center gap-1.5">
                            <div className={`h-2 w-2 rounded-full ${getPriorityColor(item.priority)}`} />
                            <span className="text-xs text-gray-500">
                              P{item.priority}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Status badge */}
                    <span
                      className={cn(
                        'inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em]',
                        item.type === 'task'
                          ? item.completed
                            ? 'bg-green-500/10 text-green-200 border-green-500/20'
                            : item.status === 'in_progress'
                            ? 'bg-blue-500/10 text-blue-200 border-blue-500/20'
                            : 'bg-yellow-500/10 text-yellow-200 border-yellow-500/20'
                          : 'bg-blue-500/10 text-blue-200 border-blue-500/20'
                      )}
                    >
                      {item.type === 'task' ? item.status.replace('_', ' ') : 'scheduled'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="py-10 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-gray-700/70">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-300">No items for this day</p>
            <p className="mt-1 text-sm text-gray-500">Your schedule is clear</p>
          </div>
        )}
      </div>

      {/* Summary */}
      {timelineItems.length > 0 && (
        <div className="mt-6 border-t border-gray-700 pt-4">
          <div className="grid grid-cols-1 gap-4 text-center sm:grid-cols-3">
            <div>
              <p className="text-2xl font-semibold text-white">
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
