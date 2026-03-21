'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useAppStore } from '@/store/useAppStore';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { isValidEmail } from '@/lib/utils';
import { useT } from '@/i18n/useT';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';

export default function LoginPage() {
  const t = useT();
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

  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const handleGoogleLogin = async () => {
    setIsGoogleLoading(true);
    setError('');
    try {
      const { apiClient } = await import('@/lib/api');
      const { authorization_url } = await apiClient.initiateGoogleAuth();
      window.location.href = authorization_url;
    } catch (err: any) {
      console.error('Google login error:', err);
      setError('خطا در برقراری ارتباط با گوگل');
      setIsGoogleLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="relative text-center">
          {/* Take orb out of flow to prevent layout shift / gradient overlap */}
          <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-center">
            <GlowingOrb size="large" className="opacity-95" />
          </div>
          <div className="relative z-10 pt-40 space-y-2">
            <h1 className="text-3xl font-bold text-white">{t('auth.welcomeBack')}</h1>
            <p className="text-gray-400 mt-2">Sign in to your Ai Department</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <TextField
              id="email"
              name="email"
              type="email"
              ref={emailRef}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              label={t('auth.email')}
              placeholder="Enter your email"
              disabled={isLoading}
              autoComplete="email"
              inputMode="email"
            />

            <TextField
              id="password"
              name="password"
              type="password"
              ref={passwordRef}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              label={t('auth.password')}
              placeholder="Enter your password"
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          <div className="flex items-center justify-end">
            <Link href="/auth/forgot-password" className="text-sm text-primary-400 hover:text-primary-300 font-medium">
              {t('auth.forgotPassword')}
            </Link>
          </div>
          <Button type="submit" disabled={isLoading} variant="primary" size="lg" className="w-full">
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>{t('auth.signingIn')}</span>
              </>
            ) : (
              <span>{t('auth.signIn')}</span>
            )}
          </Button>

          <div className="relative flex items-center py-4">
            <div className="flex-grow border-t border-white/10"></div>
            <span className="flex-shrink mx-4 text-gray-500 text-xs uppercase tracking-widest">{t('auth.orContinueWith')}</span>
            <div className="flex-grow border-t border-white/10"></div>
          </div>

          <Button 
            type="button" 
            variant="secondary" 
            className="w-full bg-white/5 border-white/10 hover:bg-white/10 text-white flex items-center justify-center gap-3 py-6"
            onClick={handleGoogleLogin}
            disabled={isLoading || isGoogleLoading}
          >
            {isGoogleLoading ? (
               <LoadingSpinner size="sm" />
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 12-4.53z"
                  style={{ transformOrigin: '0px 0px' }}
                />
              </svg>
            )}
            <span>Sign in with Google</span>
          </Button>

          <div className="text-center">
            <p className="text-gray-400">
              Don&apos;t have an account?{' '}
              <Link href="/auth/register" className="text-primary-400 hover:text-primary-300 font-medium">
                Sign up
              </Link>
            </p>
            <p className="mt-4 text-xs text-white/45">
              <Link href="/privacy" className="hover:text-white/70 transition-colors">
                Privacy Policy
              </Link>{' '}
              <span className="text-white/20">•</span>{' '}
              <Link href="/terms" className="hover:text-white/70 transition-colors">
                Terms of Service
              </Link>
            </p>
          </div>
        </form>
      </div>
    </main>
  );
}
