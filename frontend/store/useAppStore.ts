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

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        // User actions
        setUser: (user) => set({ user }, false, 'setUser'),
        updateUser: (updates) => set(
          (state) => ({
            user: state.user ? { ...state.user, ...updates } : null
          }),
          false,
          'updateUser'
        ),
        
        // Settings actions
        setSettings: (settings) => set({ settings }, false, 'setSettings'),
        updateSettings: (updates) => set(
          (state) => ({
            settings: state.settings ? { ...state.settings, ...updates } : null
          }),
          false,
          'updateSettings'
        ),
        
        // Task actions
        setTasks: (tasks) => set({ tasks }, false, 'setTasks'),
        addTask: (task) => set(
          (state) => ({ tasks: [...state.tasks, task] }),
          false,
          'addTask'
        ),
        updateTask: (id, updates) => set(
          (state) => ({
            tasks: state.tasks.map(task => 
              task.id === id ? { ...task, ...updates } : task
            )
          }),
          false,
          'updateTask'
        ),
        removeTask: (id) => set(
          (state) => ({ tasks: state.tasks.filter(task => task.id !== id) }),
          false,
          'removeTask'
        ),
        
        // Calendar actions
        setEvents: (events) => set({ events }, false, 'setEvents'),
        addEvent: (event) => set(
          (state) => ({ events: [...state.events, event] }),
          false,
          'addEvent'
        ),
        updateEvent: (id, updates) => set(
          (state) => ({
            events: state.events.map(event => 
              event.id === id ? { ...event, ...updates } : event
            )
          }),
          false,
          'updateEvent'
        ),
        removeEvent: (id) => set(
          (state) => ({ events: state.events.filter(event => event.id !== id) }),
          false,
          'removeEvent'
        ),
        
        // Voice session actions
        setVoiceSession: (voiceSession) => set({ voiceSession }, false, 'setVoiceSession'),
        updateVoiceSession: (updates) => set(
          (state) => ({
            voiceSession: state.voiceSession ? { ...state.voiceSession, ...updates } : null
          }),
          false,
          'updateVoiceSession'
        ),
        
        // UI state actions
        setLoading: (isLoading) => set({ isLoading }, false, 'setLoading'),
        setError: (error) => set({ error }, false, 'setError'),
        
        // Language actions
        setLanguage: (language) => set(
          (state) => ({
            user: state.user ? { ...state.user, language_preference: language } : null
          }),
          false,
          'setLanguage'
        ),
        
        // Reset actions
        reset: () => set(initialState, false, 'reset'),
      }),
      {
        name: 'i-assistant-store',
        partialize: (state) => ({
          // Only persist settings, not user (user is tied to auth_token)
          // This prevents having stale user data when token is invalid
          settings: state.settings,
        }),
      }
    ),
    {
      name: 'i-assistant-store',
    }
  )
);