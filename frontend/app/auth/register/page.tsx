'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { isValidEmail } from '@/lib/utils';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { register, isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isInitialized && isAuthenticated) {
      // Use window.location for reliable redirect
      window.location.href = '/dashboard';
    }
  }, [isAuthenticated, isInitialized]);

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

    // Get form data directly from form elements for better browser automation compatibility
    const formData = new FormData(e.currentTarget);
    const emailInput = e.currentTarget.querySelector('input[name="email"]') as HTMLInputElement;
    const passwordInput = e.currentTarget.querySelector('input[name="password"]') as HTMLInputElement;
    const confirmPasswordInput = e.currentTarget.querySelector('input[name="confirmPassword"]') as HTMLInputElement;
    
    const emailValue = emailInput?.value || formData.get('email') as string || email;
    const passwordValue = passwordInput?.value || formData.get('password') as string || password;
    const confirmPasswordValue = confirmPasswordInput?.value || formData.get('confirmPassword') as string || confirmPassword;

    if (!emailValue || !passwordValue || !confirmPasswordValue) {
      setError('لطفاً همه فیلدها را پر کنید');
      return;
    }

    if (!isValidEmail(emailValue)) {
      setError('لطفاً یک آدرس ایمیل معتبر وارد کنید');
      return;
    }

    const passwordError = validatePassword(passwordValue);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (passwordValue !== confirmPasswordValue) {
      setError('رمزهای عبور با هم مطابقت ندارند');
      return;
    }

    try {
      setIsLoading(true);
      await register(emailValue, passwordValue);
      // Redirect immediately after successful registration
      // Don't wait for state update - redirect based on successful API call
      window.location.href = '/dashboard';
    } catch (err: any) {
      // Error is already set in the register function via useAuth
      setError(err.message || 'ثبت نام ناموفق بود');
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-6">
          <GlowingOrb size="large" className="mx-auto" />
          <div>
            <h1 className="text-3xl font-bold text-white">Create your account</h1>
            <p className="text-gray-400 mt-2">Join i Assistant today</p>
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-white placeholder-gray-400"
                placeholder="Create a password"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-white placeholder-gray-400"
                placeholder="Confirm your password"
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
                <span>Creating account...</span>
              </>
            ) : (
              <span>Create account</span>
            )}
          </button>

          <div className="text-center">
            <p className="text-gray-400">
              Already have an account?{' '}
              <Link href="/auth/login" className="text-primary-400 hover:text-primary-300 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </form>
      </div>
    </main>
  );
}