'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Navigation } from '@/components/layout/Navigation';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      // Check if we have a token - if yes, it's invalid, clear it
      const token = localStorage.getItem('auth_token');
      if (token) {
        // Token exists but user is not authenticated - token is invalid
        localStorage.removeItem('auth_token');
      }
      // Only redirect if we're not already on login page
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/auth/')) {
        router.push('/auth/login');
      }
    }
  }, [isAuthenticated, isInitialized, router]);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Return loading spinner instead of null to avoid flash
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-950">
      <Navigation />
      
      {/* Main content */}
      <div className="lg:pl-64 w-full">
        <main className="min-h-screen w-full flex justify-center">
          <div className="w-full max-w-[1920px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}