'use client';

import { Providers } from './providers';

/**
 * ClientLayout - wraps the entire app in client-side providers
 * This component ensures all providers are always rendered (never conditional)
 * to avoid useContext errors during SSR and hydration
 * 
 * Server Component (layout.tsx) can safely import and use this Client Component
 * because it's only used in JSX, not for importing code/logic
 */
export function ClientLayout({ children }: { children: React.ReactNode }) {
  // Always render Providers - never conditionally render
  // If you need mount checks, use them in effects inside Providers, not for rendering
  return <Providers>{children}</Providers>;
}
