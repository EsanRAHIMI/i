'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Navigation } from '@/components/layout/Navigation';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      const token = localStorage.getItem('auth_token');
      if (token) {
        localStorage.removeItem('auth_token');
      }

      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/auth/')) {
        router.push('/auth/login');
      }
    }
  }, [isAuthenticated, isInitialized, router]);

  if (!isInitialized || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-950">
      <Navigation />
      <div className="app-shell-offset">
        <main className="min-h-screen">{children}</main>
      </div>
    </div>
  );
}
