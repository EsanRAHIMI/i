// Core types for the i Assistant application

export interface User {
  id: string;
  email: string;
  avatar_url?: string;
  timezone: string;
  language_preference: 'en-US' | 'fa-IR' | 'ar-UA';
  created_at: string;
  updated_at: string;
}

export interface UserSettings {
  user_id: string;
  whatsapp_opt_in: boolean;
  voice_training_consent: boolean;
  calendar_sync_enabled: boolean;
  privacy_level: 'minimal' | 'standard' | 'enhanced';
  notification_preferences: Record<string, any>;
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  priority: number;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  due_date?: string;
  context_data: Record<string, any>;
  created_by_ai: boolean;
  created_at: string;
}

export interface CalendarEvent {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  location?: string;
  attendees: string[];
  ai_generated: boolean;
  created_at: string;
}

export interface CalendarConnection {
  id: string;
  user_id: string;
  google_calendar_id?: string;
  connected: boolean;
  last_sync_at?: string;
  webhook_id?: string;
}

export interface VoiceSession {
  id: string;
  user_id: string;
  status: 'idle' | 'listening' | 'processing' | 'speaking';
  transcript?: string;
  confidence?: number;
  created_at: string;
}

export interface AgentResponse {
  text: string;
  audio_url?: string;
  actions: Array<{
    type: string;
    params: Record<string, any>;
  }>;
  confidence_score: number;
  requires_confirmation: boolean;
}

export interface AppState {
  user: User | null;
  settings: UserSettings | null;
  tasks: Task[];
  events: CalendarEvent[];
  voiceSession: VoiceSession | null;
  isLoading: boolean;
  error: string | null;
}

export interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  current?: boolean;
}

export type Language = 'en-US' | 'fa-IR' | 'ar-UA';

export interface LocaleConfig {
  code: Language;
  name: string;
  direction: 'ltr' | 'rtl';
  flag: string;
}