'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { Surface } from '@/components/ui/Surface';
import { Button } from '@/components/ui/Button';
import { Mic, CalendarDays, Focus, Sparkles, ArrowRight } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';

export default function HomePage() {
  const { isAuthenticated, isInitialized } = useAuth();

  if (!isInitialized) {
    return (
      <main className="min-h-screen px-4 py-10 sm:px-6 relative overflow-hidden flex items-center justify-center">
        <div className="absolute inset-0 z-0 bg-slate-950">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary-500/20 rounded-full blur-[120px] mix-blend-screen animate-pulse"></div>
        </div>
        <div className="relative z-10 flex w-full max-w-2xl flex-col items-center justify-center gap-8">
          <div className="text-center space-y-6">
            <GlowingOrb size="large" />
            <div className="space-y-4">
              <h1 className="text-3xl font-bold tracking-tight text-white sm:text-5xl">Ai Department</h1>
              <p className="text-white/60 text-lg">Initializing your intelligent workspace…</p>
            </div>
            <LoadingSpinner className="mx-auto" />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden selection:bg-primary-500/30">

      {/* Dynamic Background Glows */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute top-[-10%] left-[-10%] h-[50vw] w-[50vw] rounded-full bg-primary-600/20 blur-[140px] mix-blend-screen opacity-70 animate-[pulse_8s_ease-in-out_infinite]" />
        <div className="absolute bottom-[-10%] right-[-10%] h-[40vw] w-[40vw] rounded-full bg-accent-500/20 blur-[130px] mix-blend-screen opacity-60 animate-[pulse_10s_ease-in-out_infinite_alternate]" />
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center px-4 pt-20 pb-16 sm:px-6 lg:pt-32">
        {/* HERO SECTION */}
        <div className="mx-auto flex w-full max-w-4xl flex-col items-center justify-center text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 shadow-lg backdrop-blur-md mb-8">
            <Sparkles className="h-4 w-4 text-accent-400" />
            <span className="bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent">System Online V2.0</span>
          </div>

          <h1 className="text-5xl font-extrabold tracking-tight text-white sm:text-7xl lg:text-[5.5rem] leading-[1.1]">
            Your Personal <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-primary-300 to-accent-500">
              Ai Department
            </span>
          </h1>

          <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-white/60 sm:text-xl">
            Seamlessly integrate proactive voice intelligence, smart scheduling, and deep work focus into one incredibly calm, futuristic workspace.
          </p>

          <div className="mt-10 flex flex-col gap-4 sm:flex-row items-center justify-center w-full max-w-md mx-auto">
            {isAuthenticated ? (
              <Link href="/dashboard" className="w-full">
                <Button variant="primary" size="lg" className="w-full group rounded-2xl h-14 text-base shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-all hover:shadow-[0_0_45px_rgba(99,102,241,0.5)]">
                  Open your workspace
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Button>
              </Link>
            ) : (
              <>
                <Link href="/auth/register" className="w-full">
                  <Button variant="primary" size="lg" className="w-full group rounded-2xl h-14 text-base shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-all hover:shadow-[0_0_45px_rgba(99,102,241,0.5)]">
                    Create Account
                  </Button>
                </Link>
                <Link href="/auth/login" className="w-full">
                  <Button variant="secondary" size="lg" className="w-full rounded-2xl h-14 text-base border-white/10 bg-white/5 hover:bg-white/10 text-white shadow-xl backdrop-blur-md">
                    Sign In
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>

        {/* FEATURES BENTO GRID */}
        <div className="mx-auto mt-24 grid w-full max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">

          <GlassCard className="flex flex-col p-8 border-white/10 hover:border-primary-500/30 transition-colors shadow-2xl bg-gradient-to-br from-white/5 to-black/40">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-500/20 border border-primary-500/30 text-primary-300">
              <Mic className="h-7 w-7" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Voice Agent</h3>
            <p className="text-white/60 leading-relaxed text-sm flex-1">
              Talk directly to your AI powered by WebSockets. It listens, processes, and speaks back in real-time, appearing as a magical 3D Genie on your screen.
            </p>
          </GlassCard>

          <GlassCard className="flex flex-col p-8 border-white/10 hover:border-accent-500/30 transition-colors shadow-2xl bg-gradient-to-br from-white/5 to-black/40">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-500/20 border border-accent-500/30 text-accent-300">
              <Focus className="h-7 w-7" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Zen Focus Mode</h3>
            <p className="text-white/60 leading-relaxed text-sm flex-1">
              One click fades away all distractions. Dive into Deep Work Mode where your timeline expands to fill the screen, helping you conquer tasks without noise.
            </p>
          </GlassCard>

          <GlassCard className="flex flex-col p-8 border-white/10 hover:border-emerald-500/30 transition-colors shadow-2xl bg-gradient-to-br from-white/5 to-black/40">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300">
              <CalendarDays className="h-7 w-7" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Google Calendar Sync</h3>
            <p className="text-white/60 leading-relaxed text-sm flex-1">
              Your meetings and events natively flow into the dashboard. The AI knows your schedule and can intelligently plan your day around your availability.
            </p>
          </GlassCard>

        </div>

        {/* FOOTER */}
        <footer className="mt-24 w-full text-center pb-8">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-white/40">
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <span className="text-white/20">•</span>
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <span className="text-white/20">•</span>
            <span>&copy; {new Date().getFullYear()} Ai Department. All rights reserved.</span>
          </div>
        </footer>

      </div>
    </main>
  );
}
