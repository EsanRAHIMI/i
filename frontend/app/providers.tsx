'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { getLocaleConfig } from '@/lib/utils';

/**
 * Providers component - wraps all context providers
 * Never conditionally render providers - they must always be rendered
 * to avoid useContext errors in SSR
 * 
 * To add a new Context Provider:
 * 1. Use createContextWithInvariant from '@/lib/context-helpers'
 * 2. Add the Provider here, wrapping children
 * 3. Export the use hook for consumers
 * 
 * @example
 * ```tsx
 * import { createContextWithInvariant } from '@/lib/context-helpers';
 * const { Provider: ThemeProvider, useTheme } = createContextWithInvariant('Theme', null);
 * 
 * export function Providers({ children }: { children: ReactNode }) {
 *   return (
 *     <ThemeProvider value={theme}>
 *       {children}
 *     </ThemeProvider>
 *   );
 * }
 * ```
 */
export function Providers({ children }: { children: ReactNode }) {
  const { user } = useAppStore();
  const [isMounted, setIsMounted] = useState(false);
  const locale = getLocaleConfig(user?.language_preference || 'en-US');

  // Ensure component is mounted on client before accessing DOM
  // This is only for effects, not for conditional rendering of providers
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Update document direction based on language
  // This effect runs only on client side after mount
  useEffect(() => {
    // Only update document direction if we're in the browser and mounted
    if (isMounted && typeof document !== 'undefined') {
      document.documentElement.dir = locale.direction;
      document.documentElement.lang = locale.code;
    }
  }, [locale, isMounted]);

  // Always render children - never conditionally render providers
  // All providers must be available during SSR and hydration
  return <>{children}</>;
}

