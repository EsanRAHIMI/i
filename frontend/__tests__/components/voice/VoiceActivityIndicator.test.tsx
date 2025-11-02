import { render, screen } from '@testing-library/react';
import { VoiceActivityIndicator } from '@/components/voice/VoiceActivityIndicator';
import { useAppStore } from '@/store/useAppStore';

// Mock the store
vi.mock('@/store/useAppStore');
const mockUseAppStore = useAppStore as any;

const createMockStore = (voiceSession: any = null) => ({
  voiceSession,
  user: null,
  settings: null,
  tasks: [],
  events: [],
  isLoading: false,
  error: null,
  setUser: vi.fn(),
  updateUser: vi.fn(),
  setSettings: vi.fn(),
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
  setLoading: vi.fn(),
  setError: vi.fn(),
  setLanguage: vi.fn(),
  reset: vi.fn(),
});

describe('VoiceActivityIndicator', () => {
  beforeEach(() => {
    mockUseAppStore.mockReturnValue(createMockStore());
  });

  it('renders with default idle state', () => {
    render(<VoiceActivityIndicator />);
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });

  it('shows listening state correctly', () => {
    mockUseAppStore.mockReturnValue(createMockStore({
      id: '1',
      user_id: 'user1',
      status: 'listening',
      created_at: new Date().toISOString()
    }));

    render(<VoiceActivityIndicator />);
    expect(screen.getByText('Listening')).toBeInTheDocument();
  });

  it('shows processing state correctly', () => {
    mockUseAppStore.mockReturnValue(createMockStore({
      id: '1',
      user_id: 'user1',
      status: 'processing',
      created_at: new Date().toISOString()
    }));

    render(<VoiceActivityIndicator />);
    expect(screen.getByText('Processing')).toBeInTheDocument();
  });

  it('shows speaking state correctly', () => {
    mockUseAppStore.mockReturnValue(createMockStore({
      id: '1',
      user_id: 'user1',
      status: 'speaking',
      created_at: new Date().toISOString()
    }));

    render(<VoiceActivityIndicator />);
    expect(screen.getByText('Speaking')).toBeInTheDocument();
  });

  it('can hide status text', () => {
    render(<VoiceActivityIndicator showStatus={false} />);
    expect(screen.queryByText('Idle')).not.toBeInTheDocument();
  });

  it('shows confidence when available', () => {
    mockUseAppStore.mockReturnValue(createMockStore({
      id: '1',
      user_id: 'user1',
      status: 'listening',
      confidence: 0.85,
      created_at: new Date().toISOString()
    }));

    render(<VoiceActivityIndicator />);
    expect(screen.getByText('85%')).toBeInTheDocument();
  });
});