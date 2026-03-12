'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { isValidEmail } from '@/lib/utils';
import { apiClient } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setMessage('');

    const emailValue = emailRef.current?.value?.trim() || email || '';
    if (!emailValue) {
      setError('لطفاً ایمیل را وارد کنید');
      return;
    }

    if (!isValidEmail(emailValue)) {
      setError('لطفاً یک آدرس ایمیل معتبر وارد کنید');
      return;
    }

    try {
      setIsLoading(true);
      const res = await apiClient.forgotPassword(emailValue);
      setMessage(res?.message || 'اگر ایمیل وجود داشته باشد، لینک بازیابی ارسال می‌شود.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'ارسال لینک بازیابی ناموفق بود');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-6">
          <GlowingOrb size="large" className="mx-auto" />
          <div>
            <h1 className="text-3xl font-bold text-white">Forgot password</h1>
            <p className="text-gray-400 mt-2">ایمیل خود را وارد کنید تا لینک بازیابی ارسال شود</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {message && (
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
              <p className="text-green-300 text-sm">{message}</p>
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
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Sending...</span>
              </>
            ) : (
              <span>Send reset link</span>
            )}
          </button>

          <div className="text-center">
            <Link href="/auth/login" className="text-primary-400 hover:text-primary-300 font-medium">
              Back to sign in
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
