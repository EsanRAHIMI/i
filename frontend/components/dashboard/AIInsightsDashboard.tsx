'use client';

import { useState, useEffect, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { formatDate, getRelativeTime } from '@/lib/utils';

interface Insight {
  id: string;
  type: 'productivity' | 'schedule' | 'recommendation' | 'pattern';
  title: string;
  description: string;
  confidence: number;
  actionable: boolean;
  created_at: string;
  data?: any;
}

interface AIInsightsDashboardProps {
  className?: string;
}

export function AIInsightsDashboard({ className }: AIInsightsDashboardProps) {
  const { tasks, events, user } = useAppStore();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [selectedInsightType, setSelectedInsightType] = useState<'all' | Insight['type']>('all');
  const [isGenerating, setIsGenerating] = useState(false);

  // Generate AI insights based on user data
  const generateInsights = useMemo(() => {
    const newInsights: Insight[] = [];

    // Productivity insights
    const completedTasks = tasks.filter(task => task.status === 'completed');
    const pendingTasks = tasks.filter(task => task.status === 'pending');
    const overdueTasks = tasks.filter(task => 
      task.due_date && new Date(task.due_date) < new Date() && task.status !== 'completed'
    );

    if (completedTasks.length > 0) {
      const completionRate = (completedTasks.length / tasks.length) * 100;
      newInsights.push({
        id: 'productivity-1',
        type: 'productivity',
        title: 'Task Completion Rate',
        description: `You've completed ${completionRate.toFixed(1)}% of your tasks. ${
          completionRate > 80 ? 'Excellent work!' : 
          completionRate > 60 ? 'Good progress, keep it up!' : 
          'Consider breaking down larger tasks into smaller ones.'
        }`,
        confidence: 0.9,
        actionable: completionRate < 60,
        created_at: new Date().toISOString(),
        data: { completionRate, completedCount: completedTasks.length, totalCount: tasks.length }
      });
    }

    if (overdueTasks.length > 0) {
      newInsights.push({
        id: 'productivity-2',
        type: 'productivity',
        title: 'Overdue Tasks Alert',
        description: `You have ${overdueTasks.length} overdue task${overdueTasks.length > 1 ? 's' : ''}. Consider rescheduling or breaking them into smaller, manageable pieces.`,
        confidence: 1.0,
        actionable: true,
        created_at: new Date().toISOString(),
        data: { overdueCount: overdueTasks.length, tasks: overdueTasks }
      });
    }

    // Schedule insights
    const todayEvents = events.filter(event => {
      const eventDate = new Date(event.start_time).toDateString();
      const today = new Date().toDateString();
      return eventDate === today;
    });

    if (todayEvents.length > 5) {
      newInsights.push({
        id: 'schedule-1',
        type: 'schedule',
        title: 'Busy Day Ahead',
        description: `You have ${todayEvents.length} events scheduled today. Consider blocking time for breaks and unexpected tasks.`,
        confidence: 0.8,
        actionable: true,
        created_at: new Date().toISOString(),
        data: { eventCount: todayEvents.length }
      });
    }

    // Pattern insights
    const aiGeneratedTasks = tasks.filter(task => task.created_by_ai);
    if (aiGeneratedTasks.length > 0) {
      const aiTaskCompletionRate = (aiGeneratedTasks.filter(task => task.status === 'completed').length / aiGeneratedTasks.length) * 100;
      newInsights.push({
        id: 'pattern-1',
        type: 'pattern',
        title: 'AI Task Performance',
        description: `AI-generated tasks have a ${aiTaskCompletionRate.toFixed(1)}% completion rate. ${
          aiTaskCompletionRate > 70 ? 'The AI is learning your preferences well!' :
          'The AI is still learning your work patterns.'
        }`,
        confidence: 0.7,
        actionable: false,
        created_at: new Date().toISOString(),
        data: { aiCompletionRate: aiTaskCompletionRate }
      });
    }

    // Recommendation insights
    const highPriorityPending = pendingTasks.filter(task => (task.priority || 3) >= 4);
    if (highPriorityPending.length > 0) {
      newInsights.push({
        id: 'recommendation-1',
        type: 'recommendation',
        title: 'Focus on High Priority',
        description: `You have ${highPriorityPending.length} high-priority task${highPriorityPending.length > 1 ? 's' : ''} pending. Consider tackling these first for maximum impact.`,
        confidence: 0.85,
        actionable: true,
        created_at: new Date().toISOString(),
        data: { highPriorityTasks: highPriorityPending }
      });
    }

    // Time-based recommendations
    const currentHour = new Date().getHours();
    if (currentHour >= 9 && currentHour <= 11 && pendingTasks.length > 0) {
      newInsights.push({
        id: 'recommendation-2',
        type: 'recommendation',
        title: 'Peak Productivity Time',
        description: 'This is typically a high-focus time. Consider working on your most challenging tasks now.',
        confidence: 0.6,
        actionable: true,
        created_at: new Date().toISOString(),
        data: { currentHour, suggestedAction: 'focus_work' }
      });
    }

    return newInsights;
  }, [tasks, events]);

  useEffect(() => {
    setInsights(generateInsights);
  }, [generateInsights]);

  const filteredInsights = selectedInsightType === 'all' 
    ? insights 
    : insights.filter(insight => insight.type === selectedInsightType);

  const getInsightIcon = (type: Insight['type']) => {
    switch (type) {
      case 'productivity':
        return (
          <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        );
      case 'schedule':
        return (
          <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        );
      case 'recommendation':
        return (
          <svg className="w-5 h-5 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        );
      case 'pattern':
        return (
          <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const refreshInsights = async () => {
    setIsGenerating(true);
    // Simulate AI processing time
    await new Promise(resolve => setTimeout(resolve, 2000));
    setInsights(generateInsights);
    setIsGenerating(false);
  };

  const InsightBadge = () => (
    <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary-500/20 bg-primary-500/10">
      <svg className="h-5 w-5 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    </div>
  );

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex items-center gap-3">
          <InsightBadge />
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-white sm:text-xl">AI Insights</h2>
            <p className="text-sm leading-6 text-gray-400">Personalized recommendations and patterns</p>
          </div>
        </div>
        
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <select
            value={selectedInsightType}
            onChange={(e) => setSelectedInsightType(e.target.value as any)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white/80 transition-colors focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-primary-500/60 sm:min-w-40 sm:w-auto"
          >
            <option value="all" className="bg-dark-950 text-white/80">All Insights</option>
            <option value="productivity" className="bg-dark-950 text-white/80">Productivity</option>
            <option value="schedule" className="bg-dark-950 text-white/80">Schedule</option>
            <option value="recommendation" className="bg-dark-950 text-white/80">Recommendations</option>
            <option value="pattern" className="bg-dark-950 text-white/80">Patterns</option>
          </select>
          
          <button
            onClick={refreshInsights}
            disabled={isGenerating}
            className="w-full rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50 sm:w-auto"
          >
            {isGenerating ? 'Generating...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Insights Grid */}
      <div className="space-y-4">
        {filteredInsights.length > 0 ? (
          filteredInsights.map((insight) => (
            <div
              key={insight.id}
              className={`
                rounded-2xl border p-4 transition-all duration-200 hover:shadow-lg backdrop-blur-xl sm:p-5
                ${insight.actionable 
                  ? 'border-primary-500/25 bg-primary-500/[0.08] hover:border-primary-500/40' 
                  : 'border-white/10 bg-white/5 hover:border-white/20'
                }
              `}
            >
              <div className="flex items-start gap-3">
                <div className="shrink-0 rounded-xl border border-white/10 bg-white/10 p-2">
                  {getInsightIcon(insight.type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="mb-1 text-sm font-medium leading-6 text-white">
                        {insight.title}
                      </h3>
                      <p className="text-sm leading-6 text-gray-300">
                        {insight.description}
                      </p>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-2 xl:ms-4 xl:justify-end">
                      {insight.actionable && (
                        <span className="inline-flex items-center rounded-full border border-primary-500/20 bg-primary-500/15 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-primary-200">
                          Actionable
                        </span>
                      )}
                      
                      <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-left xl:text-right">
                        <p className={`text-xs font-medium ${getConfidenceColor(insight.confidence)}`}>
                          {Math.round(insight.confidence * 100)}%
                        </p>
                        <p className="text-xs text-gray-500">confidence</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`
                        inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium
                        border border-white/10
                        ${insight.type === 'productivity' ? 'bg-green-500/10 text-green-200 border-green-500/20' :
                          insight.type === 'schedule' ? 'bg-blue-500/10 text-blue-200 border-blue-500/20' :
                          insight.type === 'recommendation' ? 'bg-yellow-500/10 text-yellow-200 border-yellow-500/20' :
                          'bg-purple-500/10 text-purple-200 border-purple-500/20'
                        }
                      `}>
                        {insight.type}
                      </span>
                      
                      <span className="text-xs text-gray-500">
                        {getRelativeTime(insight.created_at)}
                      </span>
                    </div>
                    
                    {insight.actionable && (
                      <button className="text-xs font-medium text-primary-300 hover:text-primary-200">
                        Take Action →
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.03] px-6 py-12 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl border border-primary-500/20 bg-primary-500/10">
              <svg className="h-8 w-8 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 17v-6a2 2 0 012-2h6m0 0-3-3m3 3-3 3M5 5h6a2 2 0 012 2v6" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold tracking-tight text-white">Learning Your Patterns</h3>
            <p className="mx-auto max-w-md text-sm leading-6 text-gray-400">
              The AI is analyzing your behavior to provide personalized insights. 
              Complete more tasks and events to unlock detailed recommendations.
            </p>
            <button
              onClick={refreshInsights}
              className="mt-4 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700"
            >
              Generate Insights
            </button>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      {filteredInsights.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-700">
          <div className="grid grid-cols-2 gap-4 text-center lg:grid-cols-4">
            <div>
              <p className="text-lg font-semibold text-white">
                {insights.filter(i => i.actionable).length}
              </p>
              <p className="text-xs text-gray-400">Actionable</p>
            </div>
            <div>
              <p className="text-lg font-bold text-white">
                {Math.round(insights.reduce((acc, i) => acc + i.confidence, 0) / insights.length * 100) || 0}%
              </p>
              <p className="text-xs text-gray-400">Avg Confidence</p>
            </div>
            <div>
              <p className="text-lg font-bold text-white">
                {insights.filter(i => i.type === 'recommendation').length}
              </p>
              <p className="text-xs text-gray-400">Recommendations</p>
            </div>
            <div>
              <p className="text-lg font-bold text-white">
                {insights.filter(i => i.type === 'pattern').length}
              </p>
              <p className="text-xs text-gray-400">Patterns</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
