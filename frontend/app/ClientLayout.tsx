'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { getLocaleConfig } from '@/lib/utils';
import type { Language } from '@/types';

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAppStore();
  const locale = getLocaleConfig(user?.language_preference || 'en-US');

  useEffect(() => {
    // Optional debug switch: allow setting locale via `?lang=fa-IR|ar-UA|en-US`
    // Useful when auth-gated routes prevent reaching Settings.
    const urlLang = new URLSearchParams(window.location.search).get('lang');
    const safeLang: Language | null =
      urlLang === 'fa-IR' || urlLang === 'ar-UA' || urlLang === 'en-US' ? urlLang : null;

    const applied = safeLang ? getLocaleConfig(safeLang) : locale;

    // Update document direction based on language
    document.documentElement.dir = applied.direction;
    document.documentElement.lang = applied.code;
    document.cookie = `i_locale=${encodeURIComponent(applied.code)}; path=/; max-age=31536000; samesite=lax`;
  }, [locale]);

  return <>{children}</>;
}
