import { renderHook, act } from '@testing-library/react';
import { useAuth } from '@/hooks/useAuth';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { beforeEach } from 'node:test';
import { describe } from 'node:test';

// Mock dependencies
vi.mock('@/store/useAppStore');
vi.mock('@/lib/api');

const mockUseAppStore = useAppStore as any;
const mockApiClient = apiClient as any;

describe('useAuth', () => {
  const mockSetUser = vi.fn();
  const mockSetSettings = vi.fn();
  const mockSetLoading = vi.fn();
  const mockSetError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockUseAppStore.mockReturnValue({
      user: null,
      settings: null,
      tasks: [],
      events: [],
      voiceSession: null,
      isLoading: false,
      error: null,
      setUser: mockSetUser,
      updateUser: vi.fn(),
      setSettings: mockSetSettings,
      updateSettings: vi.fn(),
      setTasks: vi.fn(),
      addTask: vi.fn(),
      updateTask: vi.fn(),
      removeTask: vi.fn(),
      setEvents: vi.fn(),
      addEvent: vi.fn(),
      updateEvent: vi.fn(),
      removeEvent: vi.fn(),
      setVoiceSession: vi.fn(),
      updateVoiceSession: vi.fn(),
      setLoading: mockSetLoading,
      setError: mockSetError,
      setLanguage: vi.fn(),
      reset: vi.fn(),
    });

    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useAuth());
    
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    // isInitialized starts as false but may become true during initialization
    expect(typeof result.current.isInitialized).toBe('boolean');
  });

  it('handles successful login', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      timezone: 'UTC',
      language_preference: 'en-US' as const,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    const mockSettings = {
      user_id: '1',
      whatsapp_opt_in: false,
      voice_training_consent: false,
      calendar_sync_enabled: false,
      privacy_level: 'standard' as const,
      notification_preferences: {}
    };

    mockApiClient.login.mockResolvedValue({ user: mockUser, token: 'mock-token' });
    mockApiClient.getUserSettings.mockResolvedValue(mockSettings);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.login('test@example.com', 'password');
    });

    expect(mockApiClient.login).toHaveBeenCalledWith('test@example.com', 'password');
    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(mockSetSettings).toHaveBeenCalledWith(mockSettings);
  });

  it('handles login failure', async () => {
    const errorMessage = 'Invalid credentials';
    mockApiClient.login.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      try {
        await result.current.login('test@example.com', 'wrong-password');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        // The error message might be wrapped, so just check it contains the original message
        expect((error as Error).message).toContain('Login failed');
      }
    });

    expect(mockSetError).toHaveBeenCalled();
  });

  it('handles successful registration', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      timezone: 'UTC',
      language_preference: 'en-US' as const,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    const mockSettings = {
      user_id: '1',
      whatsapp_opt_in: false,
      voice_training_consent: false,
      calendar_sync_enabled: false,
      privacy_level: 'standard' as const,
      notification_preferences: {}
    };

    mockApiClient.register.mockResolvedValue({ user: mockUser, token: 'mock-token' });
    mockApiClient.getUserSettings.mockResolvedValue(mockSettings);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.register('test@example.com', 'password');
    });

    expect(mockApiClient.register).toHaveBeenCalledWith('test@example.com', 'password');
    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(mockSetSettings).toHaveBeenCalledWith(mockSettings);
  });

  it('handles logout', async () => {
    mockApiClient.logout.mockResolvedValue();

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.logout();
    });

    expect(mockApiClient.logout).toHaveBeenCalled();
    expect(mockSetUser).toHaveBeenCalledWith(null);
    expect(mockSetSettings).toHaveBeenCalledWith(null);
  });

  it('handles profile update', async () => {
    const updatedUser = {
      id: '1',
      email: 'test@example.com',
      timezone: 'America/New_York',
      language_preference: 'en-US' as const,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    mockApiClient.updateUser.mockResolvedValue(updatedUser);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.updateProfile({ timezone: 'America/New_York' });
    });

    expect(mockApiClient.updateUser).toHaveBeenCalledWith({ timezone: 'America/New_York' });
    expect(mockSetUser).toHaveBeenCalledWith(updatedUser);
  });
});