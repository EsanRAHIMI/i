'use client';

import { AppPageShell } from '@/components/layout/AppPageShell';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { CheckCircle2 } from 'lucide-react';

export default function TasksPage() {
  return (
    <AppPageShell>
      <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto">
        
        {/* Page Header */}
        <GlassCard className="overflow-hidden p-6 sm:p-8">
          <div className="space-y-3">
            <span className="inline-flex items-center rounded-full bg-primary-500/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-primary-400 border border-primary-500/20">
              Task Manager
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400">Action Items</span>
            </h1>
            <p className="max-w-2xl text-sm leading-relaxed text-white/50">
              Manage your AI-powered task list, set priorities, and track your daily productivity seamlessly.
            </p>
          </div>
        </GlassCard>

        {/* Content Area */}
        <GlassCard className="p-8 sm:p-16 relative overflow-hidden group border-white/5 hover:border-white/10 transition-all duration-700">
           <div className="absolute inset-0 bg-gradient-to-br from-primary-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
          
          <div className="text-center relative z-10 flex flex-col items-center justify-center min-h-[40vh]">
            <div className="relative mb-8">
              <div className="absolute inset-0 bg-primary-500/20 blur-3xl rounded-full animate-pulse"></div>
              <GlowingOrb size="large" className="relative z-10" />
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20 text-white/80">
                <CheckCircle2 className="w-10 h-10" />
              </div>
            </div>
            
            <h2 className="text-2xl font-bold text-white mb-4">Intelligent Task Management <br/> Coming Soon</h2>
            <p className="text-white/50 max-w-md mx-auto leading-relaxed text-sm">
              This will be your central hub for managing tasks generated directly by your voice AI. Organized magically, synced everywhere.
            </p>
            
            <button className="mt-8 rounded-xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-white shadow-lg backdrop-blur-md transition-all hover:bg-white/10 hover:border-white/20 active:scale-95">
              Notify Me
            </button>
          </div>
        </GlassCard>

      </div>
    </AppPageShell>
  );
}
