'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { Surface } from '@/components/ui/Surface';
import { Button } from '@/components/ui/Button';

export default function HomePage() {
  const { isAuthenticated, isInitialized } = useAuth();

  if (!isInitialized) {
    return (
      <main className="min-h-screen px-4 py-10 sm:px-6">
        <div className="mx-auto flex w-full max-w-2xl flex-col items-center justify-center gap-8">
          <div className="text-center space-y-6">
            <GlowingOrb size="large" />
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Ai Department</h1>
              <p className="text-white/60">Initializing your intelligent assistant…</p>
            </div>
            <LoadingSpinner />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center gap-8">
        <div className="text-center space-y-6">
          <GlowingOrb size="large" />
          <div className="space-y-3">
            <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-5xl">Ai Department</h1>
            <p className="mx-auto max-w-2xl text-sm leading-6 text-white/60 sm:text-base">
              Your intelligent life assistant with voice, planning, calendar integration, and actionable insights.
            </p>
          </div>
        </div>

        <Surface material="regular" className="w-full p-5 sm:p-7">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-white">Get started</p>
              <p className="text-sm text-white/60">
                {isAuthenticated ? 'Continue to your dashboard.' : 'Sign in to access your dashboard.'}
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              {isAuthenticated ? (
                <Link href="/dashboard">
                  <Button variant="primary" size="lg" className="w-full sm:w-auto">
                    Open Dashboard
                  </Button>
                </Link>
              ) : (
                <Link href="/auth/login">
                  <Button variant="primary" size="lg" className="w-full sm:w-auto">
                    Sign in
                  </Button>
                </Link>
              )}
              <Link href="/auth/register">
                <Button variant="secondary" size="lg" className="w-full sm:w-auto">
                  Create account
                </Button>
              </Link>
            </div>
          </div>
        </Surface>

        <footer className="w-full text-center text-xs text-white/45">
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
            <Link href="/privacy" className="hover:text-white/70 transition-colors">
              Privacy Policy
            </Link>
            <span className="text-white/20">•</span>
            <Link href="/terms" className="hover:text-white/70 transition-colors">
              Terms of Service
            </Link>
          </div>
        </footer>
      </div>
    </main>
  );
}
