/**
 * Centralized logging utility
 * Only logs in development mode to avoid console spam in production
 */

const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';

type LogLevel = 'log' | 'warn' | 'error' | 'info' | 'debug';

class Logger {
  private shouldLog(level: LogLevel): boolean {
    // In production, only log errors
    if (isProduction) {
      return level === 'error';
    }
    // In development, log everything
    return isDevelopment;
  }

  log(...args: any[]): void {
    if (this.shouldLog('log')) {
      console.log('[LOG]', ...args);
    }
  }

  info(...args: any[]): void {
    if (this.shouldLog('info')) {
      console.info('[INFO]', ...args);
    }
  }

  warn(...args: any[]): void {
    if (this.shouldLog('warn')) {
      console.warn('[WARN]', ...args);
    }
  }

  error(...args: any[]): void {
    // Always log errors, but with better formatting
    console.error('[ERROR]', ...args);
  }

  debug(...args: any[]): void {
    if (this.shouldLog('debug')) {
      console.debug('[DEBUG]', ...args);
    }
  }

  // Silent - never logs (for removing console.logs)
  silent(...args: any[]): void {
    // Do nothing
  }
}

export const logger = new Logger();


