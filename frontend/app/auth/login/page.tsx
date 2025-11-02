'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useAppStore } from '@/store/useAppStore';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { isValidEmail } from '@/lib/utils';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  
  const { login, isAuthenticated, isInitialized, isLoading } = useAuth();
  const { setUser } = useAppStore();
  const router = useRouter();

  // Redirect to dashboard if already authenticated
  // But only if we're sure the user is really authenticated (has valid token and user object)
  useEffect(() => {
    // Don't redirect during loading or if not initialized
    if (!isInitialized || isLoading) {
      return;
    }
    
    // Only redirect if we have both token AND user state
    if (isAuthenticated) {
      const token = localStorage.getItem('auth_token');
      if (token) {
        // Small delay to avoid immediate redirect on page load
        const timeoutId = setTimeout(() => {
          // Double-check we're still authenticated before redirecting
          if (localStorage.getItem('auth_token')) {
            window.location.href = '/dashboard';
          }
        }, 200);
        return () => clearTimeout(timeoutId);
      } else {
        // Token missing but user state exists - clear user state
        // This means we had stale state from persist
        setUser(null);
      }
    }
  }, [isAuthenticated, isInitialized, isLoading, setUser]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    // Get form data directly from refs for better browser automation compatibility
    // This ensures we read actual values even if React state hasn't updated
    const emailValue = emailRef.current?.value?.trim() || email || '';
    const passwordValue = passwordRef.current?.value?.trim() || password || '';

    if (!emailValue || !passwordValue) {
      setError('Please fill in all fields');
      return;
    }

    if (!isValidEmail(emailValue)) {
      setError('Please enter a valid email address');
      return;
    }

    try {
      await login(emailValue, passwordValue);
      
      // Wait longer to ensure token is saved to localStorage
      // and all async operations complete
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Verify token is in localStorage before redirecting
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.error('Token verification failed. Token not found in localStorage.');
        setError('خطا در ذخیره اطلاعات احراز هویت. لطفاً دوباره تلاش کنید.');
        return;
      }
      
      // Use window.location.href for a full page reload to ensure clean state
      // This ensures localStorage is properly available
      window.location.href = '/dashboard';
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.message || 'ورود ناموفق بود');
      // isLoading is managed by useAuth hook, no need to set it manually
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-6">
          <GlowingOrb size="large" className="mx-auto" />
          <div>
            <h1 className="text-3xl font-bold text-white">Welcome back</h1>
            <p className="text-gray-400 mt-2">Sign in to your i Assistant</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                ref={emailRef}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-white placeholder-gray-400"
                placeholder="Enter your email"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                ref={passwordRef}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-white placeholder-gray-400"
                placeholder="Enter your password"
                disabled={isLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Signing in...</span>
              </>
            ) : (
              <span>Sign in</span>
            )}
          </button>

          <div className="text-center">
            <p className="text-gray-400">
              Don't have an account?{' '}
              <Link href="/auth/register" className="text-primary-400 hover:text-primary-300 font-medium">
                Sign up
              </Link>
            </p>
          </div>
        </form>
      </div>
    </main>
  );
}