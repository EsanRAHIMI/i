'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { getLocaleConfig } from '@/lib/utils';

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAppStore();
  const locale = getLocaleConfig(user?.language_preference || 'en-US');

  useEffect(() => {
    // Update document direction based on language
    document.documentElement.dir = locale.direction;
    document.documentElement.lang = locale.code;
  }, [locale]);

  return <>{children}</>;
}
