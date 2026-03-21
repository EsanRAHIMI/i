'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/store/useAppStore';

export default function GoogleCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const { setUser } = useAppStore();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code) {
      setError('No authorization code received from Google');
      return;
    }

    const handleCallback = async () => {
      try {
        const { user, token } = await apiClient.handleGoogleCallback(code, state || undefined);
        setUser(user);
        
        // Ensure token is saved
        localStorage.setItem('auth_token', token);
        
        // Small delay to ensure state is updated
        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 500);
      } catch (err: any) {
        console.error('Google callback error:', err);
        setError(err.response?.data?.detail || 'Authentication failed');
      }
    };

    handleCallback();
  }, [searchParams, router, setUser]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-[#0a0a0b]">
        <div className="max-w-md w-full text-center space-y-4">
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-red-400 mb-2">Authentication Error</h2>
            <p className="text-gray-400">{error}</p>
          </div>
          <button 
            onClick={() => router.push('/auth/login')}
            className="text-primary-400 hover:text-primary-300 font-medium"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-[#0a0a0b]">
      <div className="space-y-6 text-center">
        <LoadingSpinner size="lg" />
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white italic">Verifying with Google</h2>
          <p className="text-gray-400">Please wait while we secure your session...</p>
        </div>
      </div>
    </div>
  );
}
