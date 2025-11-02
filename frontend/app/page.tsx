'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { GlowingOrb } from '@/components/ui/GlowingOrb';

export default function HomePage() {
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isInitialized) {
      if (isAuthenticated) {
        router.push('/dashboard');
      } else {
        router.push('/auth/login');
      }
    }
  }, [isAuthenticated, isInitialized, router]);

  if (!isInitialized) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-6">
          <GlowingOrb size="large" />
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-white">i Assistant</h1>
            <p className="text-gray-400">Initializing your intelligent assistant...</p>
          </div>
          <LoadingSpinner />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-6">
        <GlowingOrb size="large" />
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-white">i Assistant</h1>
          <p className="text-gray-400">Redirecting...</p>
        </div>
      </div>
    </main>
  );
}
