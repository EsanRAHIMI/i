import {
  cn,
  getLocaleConfig,
  formatDate,
  formatTime,
  formatDateTime,
  getRelativeTime,
  debounce,
  throttle,
  generateId,
  isValidEmail,
  truncateText,
  capitalizeFirst,
  getInitials
} from '@/lib/utils';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { afterEach } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { afterEach } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { describe } from 'node:test';
import { describe } from 'node:test';

describe('utils', () => {
  describe('cn', () => {
    it('combines class names correctly', () => {
      expect(cn('class1', 'class2')).toBe('class1 class2');
    });

    it('handles conditional classes', () => {
      expect(cn('class1', false && 'class2', 'class3')).toBe('class1 class3');
    });
  });

  describe('getLocaleConfig', () => {
    it('returns correct config for English', () => {
      const config = getLocaleConfig('en-US');
      expect(config.code).toBe('en-US');
      expect(config.name).toBe('English');
      expect(config.direction).toBe('ltr');
      expect(config.flag).toBe('🇺🇸');
    });

    it('returns correct config for Persian', () => {
      const config = getLocaleConfig('fa-IR');
      expect(config.code).toBe('fa-IR');
      expect(config.name).toBe('فارسی');
      expect(config.direction).toBe('rtl');
      expect(config.flag).toBe('🇮🇷');
    });

    it('returns default config for invalid language', () => {
      const config = getLocaleConfig('invalid' as any);
      expect(config.code).toBe('en-US');
    });
  });

  describe('formatDate', () => {
    it('formats date correctly', () => {
      const date = new Date('2023-12-25T10:30:00Z');
      const formatted = formatDate(date);
      expect(formatted).toContain('December');
      expect(formatted).toContain('25');
      expect(formatted).toContain('2023');
    });

    it('formats date string correctly', () => {
      const formatted = formatDate('2023-12-25T10:30:00Z');
      expect(formatted).toContain('December');
    });
  });

  describe('formatTime', () => {
    it('formats time correctly', () => {
      const date = new Date('2023-12-25T10:30:00Z');
      const formatted = formatTime(date);
      expect(formatted).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe('formatDateTime', () => {
    it('formats date and time correctly', () => {
      const date = new Date('2023-12-25T10:30:00Z');
      const formatted = formatDateTime(date);
      expect(formatted).toContain('Dec');
      expect(formatted).toContain('25');
      expect(formatted).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe('getRelativeTime', () => {
    it('returns relative time for recent date', () => {
      const now = new Date();
      const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
      const relative = getRelativeTime(fiveMinutesAgo);
      expect(relative).toContain('minute');
    });
  });

  describe('debounce', () => {
    vi.useFakeTimers();

    it('debounces function calls', () => {
      const mockFn = vi.fn();
      const debouncedFn = debounce(mockFn, 100);

      debouncedFn();
      debouncedFn();
      debouncedFn();

      expect(mockFn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);
      expect(mockFn).toHaveBeenCalledTimes(1);
    });

    afterEach(() => {
      vi.clearAllTimers();
    });
  });

  describe('throttle', () => {
    vi.useFakeTimers();

    it('throttles function calls', () => {
      const mockFn = vi.fn();
      const throttledFn = throttle(mockFn, 100);

      throttledFn();
      throttledFn();
      throttledFn();

      expect(mockFn).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(100);
      throttledFn();
      expect(mockFn).toHaveBeenCalledTimes(2);
    });

    afterEach(() => {
      vi.clearAllTimers();
    });
  });

  describe('generateId', () => {
    it('generates unique IDs', () => {
      const id1 = generateId();
      const id2 = generateId();
      expect(id1).not.toBe(id2);
      expect(typeof id1).toBe('string');
      expect(id1.length).toBeGreaterThan(0);
    });
  });

  describe('isValidEmail', () => {
    it('validates correct email addresses', () => {
      expect(isValidEmail('test@example.com')).toBe(true);
      expect(isValidEmail('user.name@domain.co.uk')).toBe(true);
    });

    it('rejects invalid email addresses', () => {
      expect(isValidEmail('invalid-email')).toBe(false);
      expect(isValidEmail('test@')).toBe(false);
      expect(isValidEmail('@example.com')).toBe(false);
      expect(isValidEmail('')).toBe(false);
    });
  });

  describe('truncateText', () => {
    it('truncates long text', () => {
      const longText = 'This is a very long text that should be truncated';
      const truncated = truncateText(longText, 20);
      expect(truncated).toBe('This is a very long ...');
      expect(truncated.length).toBe(23); // 20 + '...'
    });

    it('does not truncate short text', () => {
      const shortText = 'Short text';
      const result = truncateText(shortText, 20);
      expect(result).toBe(shortText);
    });
  });

  describe('capitalizeFirst', () => {
    it('capitalizes first letter', () => {
      expect(capitalizeFirst('hello world')).toBe('Hello world');
      expect(capitalizeFirst('test')).toBe('Test');
    });

    it('handles empty string', () => {
      expect(capitalizeFirst('')).toBe('');
    });
  });

  describe('getInitials', () => {
    it('gets initials from full name', () => {
      expect(getInitials('John Doe')).toBe('JD');
      expect(getInitials('Jane Mary Smith')).toBe('JM');
    });

    it('handles single name', () => {
      expect(getInitials('John')).toBe('J');
    });

    it('limits to 2 characters', () => {
      expect(getInitials('John Mary Jane Doe')).toBe('JM');
    });
  });
});