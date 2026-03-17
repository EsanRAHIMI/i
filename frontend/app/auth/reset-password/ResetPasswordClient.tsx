'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { apiClient } from '@/lib/api';

export default function ResetPasswordClient() {
  const searchParams = useSearchParams();
  const token = useMemo(() => (searchParams ? searchParams.get('token') : null), [searchParams]);

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmPasswordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setError('');
    setMessage('');
  }, [token]);

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) {
      return 'رمز عبور باید حداقل ۸ کاراکتر باشد';
    }

    const hasUpper = /[A-Z]/.test(pwd);
    const hasLower = /[a-z]/.test(pwd);
    const hasDigit = /[0-9]/.test(pwd);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(pwd);

    if (!hasUpper || !hasLower || !hasDigit || !hasSpecial) {
      return 'رمز عبور باید حداقل شامل یک حرف بزرگ، یک حرف کوچک، یک عدد و یک کاراکتر خاص باشد';
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!token) {
      setError('توکن بازیابی معتبر نیست');
      return;
    }

    const passwordValue = passwordRef.current?.value?.trim() || password || '';
    const confirmValue = confirmPasswordRef.current?.value?.trim() || confirmPassword || '';

    if (!passwordValue || !confirmValue) {
      setError('لطفاً همه فیلدها را پر کنید');
      return;
    }

    const passwordError = validatePassword(passwordValue);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (passwordValue !== confirmValue) {
      setError('رمزهای عبور با هم مطابقت ندارند');
      return;
    }

    try {
      setIsLoading(true);
      const res = await apiClient.resetPassword(token, passwordValue);
      setMessage(res?.message || 'رمز عبور با موفقیت تغییر کرد');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'تغییر رمز عبور ناموفق بود');
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
            <h1 className="text-3xl font-bold text-white">Reset password</h1>
            <p className="text-gray-400 mt-2">رمز عبور جدید خود را وارد کنید</p>
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
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                New password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                ref={passwordRef}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-white placeholder-gray-400"
                placeholder="Enter new password"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                Confirm new password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                ref={confirmPasswordRef}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-white placeholder-gray-400"
                placeholder="Confirm new password"
                disabled={isLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Saving...</span>
              </>
            ) : (
              <span>Reset password</span>
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
