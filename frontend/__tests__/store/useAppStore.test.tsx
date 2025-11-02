import { renderHook, act } from '@testing-library/react';
import { useAppStore } from '@/store/useAppStore';

describe('useAppStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useAppStore());
    act(() => {
      result.current.reset();
    });
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useAppStore());
    
    expect(result.current.user).toBeNull();
    expect(result.current.settings).toBeNull();
    expect(result.current.tasks).toEqual([]);
    expect(result.current.events).toEqual([]);
    expect(result.current.voiceSession).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('sets and updates user', () => {
    const { result } = renderHook(() => useAppStore());
    
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      timezone: 'UTC',
      language_preference: 'en-US' as const,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    act(() => {
      result.current.setUser(mockUser);
    });

    expect(result.current.user).toEqual(mockUser);

    act(() => {
      result.current.updateUser({ timezone: 'America/New_York' });
    });

    expect(result.current.user?.timezone).toBe('America/New_York');
  });

  it('manages tasks correctly', () => {
    const { result } = renderHook(() => useAppStore());
    
    const mockTask = {
      id: '1',
      user_id: 'user1',
      title: 'Test Task',
      description: 'Test Description',
      priority: 3,
      status: 'pending' as const,
      due_date: '2023-12-31T23:59:59Z',
      context_data: {},
      created_by_ai: false,
      created_at: '2023-01-01T00:00:00Z'
    };

    // Add task
    act(() => {
      result.current.addTask(mockTask);
    });

    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0]).toEqual(mockTask);

    // Update task
    act(() => {
      result.current.updateTask('1', { status: 'completed' });
    });

    expect(result.current.tasks[0].status).toBe('completed');

    // Remove task
    act(() => {
      result.current.removeTask('1');
    });

    expect(result.current.tasks).toHaveLength(0);
  });

  it('manages events correctly', () => {
    const { result } = renderHook(() => useAppStore());
    
    const mockEvent = {
      id: '1',
      user_id: 'user1',
      title: 'Test Event',
      description: 'Test Description',
      start_time: '2023-12-31T10:00:00Z',
      end_time: '2023-12-31T11:00:00Z',
      location: 'Test Location',
      attendees: ['test@example.com'],
      ai_generated: false,
      created_at: '2023-01-01T00:00:00Z'
    };

    // Add event
    act(() => {
      result.current.addEvent(mockEvent);
    });

    expect(result.current.events).toHaveLength(1);
    expect(result.current.events[0]).toEqual(mockEvent);

    // Update event
    act(() => {
      result.current.updateEvent('1', { location: 'Updated Location' });
    });

    expect(result.current.events[0].location).toBe('Updated Location');

    // Remove event
    act(() => {
      result.current.removeEvent('1');
    });

    expect(result.current.events).toHaveLength(0);
  });

  it('manages voice session correctly', () => {
    const { result } = renderHook(() => useAppStore());
    
    const mockVoiceSession = {
      id: '1',
      user_id: 'user1',
      status: 'listening' as const,
      transcript: 'Hello world',
      confidence: 0.95,
      created_at: '2023-01-01T00:00:00Z'
    };

    act(() => {
      result.current.setVoiceSession(mockVoiceSession);
    });

    expect(result.current.voiceSession).toEqual(mockVoiceSession);

    act(() => {
      result.current.updateVoiceSession({ status: 'processing' });
    });

    expect(result.current.voiceSession?.status).toBe('processing');
  });

  it('manages loading and error states', () => {
    const { result } = renderHook(() => useAppStore());
    
    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.setError('Test error');
    });

    expect(result.current.error).toBe('Test error');

    act(() => {
      result.current.setLoading(false);
      result.current.setError(null);
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('sets language correctly', () => {
    const { result } = renderHook(() => useAppStore());
    
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      timezone: 'UTC',
      language_preference: 'en-US' as const,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    act(() => {
      result.current.setUser(mockUser);
    });

    act(() => {
      result.current.setLanguage('fa-IR');
    });

    expect(result.current.user?.language_preference).toBe('fa-IR');
  });

  it('resets state correctly', () => {
    const { result } = renderHook(() => useAppStore());
    
    // Set some state
    act(() => {
      result.current.setUser({
        id: '1',
        email: 'test@example.com',
        timezone: 'UTC',
        language_preference: 'en-US',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      });
      result.current.setLoading(true);
      result.current.setError('Test error');
    });

    // Reset
    act(() => {
      result.current.reset();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });
});