'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { GlowingOrb } from '@/components/ui/GlowingOrb';

function CalendarCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('در حال اتصال به گوگل کالندر...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        if (error) {
          setStatus('error');
          setMessage(`خطا در اتصال: ${error.replace(/_/g, ' ')}`);
          setTimeout(() => {
            router.push('/calendar');
          }, 3000);
          return;
        }

        if (!code) {
          setStatus('error');
          setMessage('کد احراز هویت دریافت نشد');
          setTimeout(() => {
            router.push('/calendar');
          }, 3000);
          return;
        }

        // Exchange code for tokens via POST to backend
        try {
          await apiClient.handleCalendarCallback(code, state || undefined);
          
          setStatus('success');
          setMessage('اتصال به گوگل کالندر با موفقیت انجام شد!');

          // Redirect to calendar page after 2 seconds
          setTimeout(() => {
            router.push('/calendar');
          }, 2000);
        } catch (err: any) {
          console.error('Calendar callback token exchange error:', err);
          setStatus('error');
          setMessage(err.response?.data?.detail || 'خطا در تکمیل اتصال به گوگل کالندر');
          setTimeout(() => {
            router.push('/calendar');
          }, 3000);
        }
      } catch (err: any) {
        console.error('Calendar callback error:', err);
        setStatus('error');
        setMessage(err.response?.data?.detail || 'خطا در اتصال به گوگل کالندر');
        setTimeout(() => {
          router.push('/calendar');
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 p-6">
      <div className="text-center space-y-6 max-w-md">
        <GlowingOrb size="large" className="mx-auto" />
        
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-white">
            {status === 'processing' && 'در حال اتصال...'}
            {status === 'success' && 'اتصال موفق!'}
            {status === 'error' && 'خطا در اتصال'}
          </h1>
          <p className="text-gray-400">{message}</p>
        </div>

        {status === 'processing' && (
          <div className="flex justify-center">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {status === 'success' && (
          <div className="text-green-400">
            <svg
              className="w-16 h-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        )}

        {status === 'error' && (
          <div className="text-red-400">
            <svg
              className="w-16 h-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CalendarCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-dark-950 p-6">
        <div className="text-center space-y-6 max-w-md">
          <GlowingOrb size="large" className="mx-auto" />
          <div className="flex justify-center">
            <LoadingSpinner size="lg" />
          </div>
          <p className="text-gray-400">در حال بارگذاری...</p>
        </div>
      </div>
    }>
      <CalendarCallbackContent />
    </Suspense>
  );
}

