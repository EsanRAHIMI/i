'use client';

import { createContext, useContext, ReactNode } from 'react';
import { invariant } from './invariant';

/**
 * Creates a context with automatic invariant checking
 * This ensures that hooks using this context throw a helpful error
 * if used outside the Provider
 * 
 * @param name - The name of the context (for error messages)
 * @param defaultValue - Default value (should never be used in production)
 * @returns Context object with Provider and use hook
 * 
 * @example
 * ```tsx
 * const { Provider: ThemeProvider, useTheme } = createContextWithInvariant<Theme>(
 *   'Theme',
 *   null
 * );
 * 
 * function App() {
 *   return (
 *     <ThemeProvider value={theme}>
 *       <MyComponent />
 *     </ThemeProvider>
 *   );
 * }
 * 
 * function MyComponent() {
 *   const theme = useTheme(); // Will throw if outside ThemeProvider
 *   return <div>{theme}</div>;
 * }
 * ```
 */
export function createContextWithInvariant<T>(
  name: string,
  defaultValue: T | null = null
) {
  const Context = createContext<T | null>(defaultValue);

  function useContextValue(): T {
    const value = useContext(Context);
    invariant(
      value !== null,
      `${name}Context must be used within ${name}Provider. ` +
      `Make sure ${name}Provider wraps your component tree.`
    );
    return value;
  }

  function Provider({ children, value }: { children: ReactNode; value: T }) {
    return <Context.Provider value={value}>{children}</Context.Provider>;
  }

  return {
    Provider,
    Context,
    useContextValue,
    // Alias for convenience
    [`use${name}` as const]: useContextValue,
  } as {
    Provider: typeof Provider;
    Context: typeof Context;
    useContextValue: typeof useContextValue;
    [K in `use${string}`]: typeof useContextValue;
  };
}

/**
 * Helper to create a hook that uses context with invariant check
 * Use this if you already have a context created
 * 
 * @param context - The React Context
 * @param contextName - Name of the context (for error messages)
 * @returns Hook that throws if used outside Provider
 * 
 * @example
 * ```tsx
 * const MyContext = createContext<MyType | null>(null);
 * export const useMyContext = createContextHook(MyContext, 'MyContext');
 * ```
 */
export function createContextHook<T>(
  context: React.Context<T | null>,
  contextName: string
) {
  return function useContextWithInvariant(): T {
    const value = useContext(context);
    invariant(
      value !== null,
      `${contextName} must be used within ${contextName}Provider. ` +
      `Make sure your component is wrapped with the appropriate Provider.`
    );
    return value;
  };
}

