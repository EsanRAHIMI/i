import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { AppState, User, UserSettings, Task, CalendarEvent, VoiceSession, Language } from '@/types';

interface AppStore extends AppState {
  // User actions
  setUser: (user: User | null) => void;
  updateUser: (updates: Partial<User>) => void;
  
  // Settings actions
  setSettings: (settings: UserSettings | null) => void;
  updateSettings: (updates: Partial<UserSettings>) => void;
  
  // Task actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  
  // Calendar actions
  setEvents: (events: CalendarEvent[]) => void;
  addEvent: (event: CalendarEvent) => void;
  updateEvent: (id: string, updates: Partial<CalendarEvent>) => void;
  removeEvent: (id: string) => void;
  
  // Voice session actions
  setVoiceSession: (session: VoiceSession | null) => void;
  updateVoiceSession: (updates: Partial<VoiceSession>) => void;
  
  // UI state actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Language actions
  setLanguage: (language: Language) => void;
  
  // Reset actions
  reset: () => void;
}

const initialState: AppState = {
  user: null,
  settings: null,
  tasks: [],
  events: [],
  voiceSession: null,
  isLoading: false,
  error: null,
};

// Helper to check if we're in browser environment
const isBrowser = typeof window !== 'undefined';

// Create store factory that works with SSR
const storeFactory = (set: any, get: any) => ({
  ...initialState,
  
  // User actions
  setUser: (user: User | null) => set({ user }, false, 'setUser'),
  updateUser: (updates: Partial<User>) => set(
    (state: AppStore) => ({
      user: state.user ? { ...state.user, ...updates } : null
    }),
    false,
    'updateUser'
  ),
  
  // Settings actions
  setSettings: (settings: UserSettings | null) => set({ settings }, false, 'setSettings'),
  updateSettings: (updates: Partial<UserSettings>) => set(
    (state: AppStore) => ({
      settings: state.settings ? { ...state.settings, ...updates } : null
    }),
    false,
    'updateSettings'
  ),
  
  // Task actions
  setTasks: (tasks: Task[]) => set({ tasks }, false, 'setTasks'),
  addTask: (task: Task) => set(
    (state: AppStore) => ({ tasks: [...state.tasks, task] }),
    false,
    'addTask'
  ),
  updateTask: (id: string, updates: Partial<Task>) => set(
    (state: AppStore) => ({
      tasks: state.tasks.map(task => 
        task.id === id ? { ...task, ...updates } : task
      )
    }),
    false,
    'updateTask'
  ),
  removeTask: (id: string) => set(
    (state: AppStore) => ({ tasks: state.tasks.filter(task => task.id !== id) }),
    false,
    'removeTask'
  ),
  
  // Calendar actions
  setEvents: (events: CalendarEvent[]) => set({ events }, false, 'setEvents'),
  addEvent: (event: CalendarEvent) => set(
    (state: AppStore) => ({ events: [...state.events, event] }),
    false,
    'addEvent'
  ),
  updateEvent: (id: string, updates: Partial<CalendarEvent>) => set(
    (state: AppStore) => ({
      events: state.events.map(event => 
        event.id === id ? { ...event, ...updates } : event
      )
    }),
    false,
    'updateEvent'
  ),
  removeEvent: (id: string) => set(
    (state: AppStore) => ({ events: state.events.filter(event => event.id !== id) }),
    false,
    'removeEvent'
  ),
  
  // Voice session actions
  setVoiceSession: (voiceSession: VoiceSession | null) => set({ voiceSession }, false, 'setVoiceSession'),
  updateVoiceSession: (updates: Partial<VoiceSession>) => set(
    (state: AppStore) => ({
      voiceSession: state.voiceSession ? { ...state.voiceSession, ...updates } : null
    }),
    false,
    'updateVoiceSession'
  ),
  
  // UI state actions
  setLoading: (isLoading: boolean) => set({ isLoading }, false, 'setLoading'),
  setError: (error: string | null) => set({ error }, false, 'setError'),
  
  // Language actions
  setLanguage: (language: Language) => set(
    (state: AppStore) => ({
      user: state.user ? { ...state.user, language_preference: language } : null
    }),
    false,
    'setLanguage'
  ),
  
  // Reset actions
  reset: () => set(initialState, false, 'reset'),
});

// Create store with proper SSR handling
export const useAppStore = create<AppStore>()(
  devtools(
    isBrowser
      ? persist(storeFactory, {
          name: 'i-assistant-store',
          partialize: (state) => ({
            // Only persist settings, not user (user is tied to auth_token)
            // This prevents having stale user data when token is invalid
            settings: state.settings,
          }),
        })
      : storeFactory,
    {
      name: 'i-assistant-store',
      enabled: isBrowser, // Only enable devtools in browser
    }
  )
);