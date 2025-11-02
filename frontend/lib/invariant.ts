/**
 * Invariant utility for better debugging
 * Throws an error with a helpful message if the condition is false
 * 
 * @param condition - The condition to check
 * @param message - Error message to display if condition is false
 * @throws Error if condition is false
 * 
 * @example
 * ```ts
 * const context = useContext(MyContext);
 * invariant(context, 'MyComponent must be used within MyProvider');
 * ```
 */
export function invariant(
  condition: unknown,
  message: string
): asserts condition {
  if (!condition) {
    throw new Error(
      `Invariant violation: ${message}\n\n` +
      `This usually means a component is being used outside its required Provider.\n` +
      `Check the component stack trace above to find where this hook/component is being called.`
    );
  }
}

