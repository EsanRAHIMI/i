import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { User, UserSettings, Task, CalendarEvent, CalendarConnection, AgentResponse } from '@/types';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      const errorMsg = 'NEXT_PUBLIC_API_URL environment variable is not set. Please create a .env.local file in the frontend directory with NEXT_PUBLIC_API_URL=http://localhost:8000';
      console.error(errorMsg);
      throw new Error(errorMsg);
    }
    
    this.client = axios.create({
      baseURL: apiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        // Don't redirect on 401 for login/register pages or OAuth callback (they handle it themselves)
        if (error.response?.status === 401 && typeof window !== 'undefined') {
          const path = window.location.pathname;
          const requestUrl = error.config?.url || '';
          
          // Don't clear token or redirect if we're on auth pages or in auth flow
          const isAuthPage = path.startsWith('/auth/login') || 
                            path.startsWith('/auth/register') ||
                            path.startsWith('/calendar/callback');
          
          // Don't clear token for auth endpoints that might return 401 during normal flow
          // Also don't clear token if the request was made during initialization
          // (check if we just logged in by seeing if token exists)
          const isAuthEndpoint = requestUrl.includes('/auth/login') || 
                                requestUrl.includes('/auth/register');
          
          // Check if we have a token - if yes, it might be valid and we shouldn't clear it
          // This prevents clearing token during initialization right after login
          const hasToken = this.getAuthToken();
          const isInitializationRequest = requestUrl.includes('/auth/me') || 
                                         requestUrl.includes('/auth/settings');
          
          // Check if this is a calendar/tasks request that might fail during initialization
          const isCalendarOrTaskRequest = requestUrl.includes('/calendar/') || 
                                         requestUrl.includes('/tasks/');
          
          // Don't clear token if:
          // 1. We're on an auth page
          // 2. It's an auth endpoint request
          // 3. We have a token AND it's an initialization request (might be timing issue)
          // 4. We're on dashboard and just logged in (give it time to initialize)
          // 5. We're on dashboard and it's a calendar/tasks request (these might fail if calendar not connected)
          const isDashboardInitialization = path === '/dashboard' && hasToken && isInitializationRequest;
          const isDashboardCalendarRequest = path === '/dashboard' && hasToken && isCalendarOrTaskRequest;
          const shouldPreserveToken = isAuthPage || isAuthEndpoint || isDashboardInitialization || isDashboardCalendarRequest;
          
          if (!shouldPreserveToken) {
            // Clear token only if we're not in an auth flow and not during initialization
            this.clearAuthToken();
            
            // Only redirect if not already on auth pages
            if (!path.startsWith('/auth/') && !path.startsWith('/calendar/callback')) {
              // Use setTimeout to avoid redirect loops
              setTimeout(() => {
                if (window.location.pathname === path) {
                  window.location.href = '/auth/login';
                }
              }, 100);
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  private setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('auth_token', token);
        // Verify it was saved
        const saved = localStorage.getItem('auth_token');
        if (saved !== token) {
          console.error('Failed to save token to localStorage. Token mismatch.');
        }
      } catch (error) {
        console.error('Failed to save token to localStorage:', error);
        throw error;
      }
    }
  }

  private clearAuthToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    const response = await this.client.post('/auth/login', { email, password });
    const { user, access_token } = response.data;
    
    // Ensure we have a token
    if (!access_token) {
      throw new Error('No access token received from server');
    }
    
    // Save token to localStorage
    this.setAuthToken(access_token);
    
    // Verify token was saved
    const savedToken = this.getAuthToken();
    if (!savedToken || savedToken !== access_token) {
      console.error('Token was not saved correctly to localStorage');
      throw new Error('Failed to save authentication token');
    }
    
    return { user, token: access_token };
  }

  async register(email: string, password: string): Promise<{ user: User; token: string }> {
    try {
      const response = await this.client.post('/auth/register', { email, password });
      const { user, access_token } = response.data;
      this.setAuthToken(access_token);
      return { user, token: access_token };
    } catch (error: any) {
      // Log error for debugging
      console.error('Registration API error:', error);
      console.error('Response:', error.response?.data);
      console.error('Status:', error.response?.status);
      throw error;
    }
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    this.clearAuthToken();
  }

  // User endpoints
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async updateUser(updates: Partial<User>): Promise<User> {
    const response = await this.client.patch('/auth/me', updates);
    return response.data;
  }

  async uploadAvatar(file: File): Promise<User> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await this.client.post('/auth/avatar/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  // Settings endpoints
  async getUserSettings(): Promise<UserSettings> {
    const response = await this.client.get('/auth/settings');
    return response.data;
  }

  async updateUserSettings(updates: Partial<UserSettings>): Promise<UserSettings> {
    const response = await this.client.patch('/auth/settings', updates);
    return response.data;
  }

  // Voice endpoints
  async speechToText(audioBlob: Blob): Promise<{ text: string; confidence: number }> {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    
    const response = await this.client.post('/voice/stt', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async textToSpeech(text: string): Promise<{ audio_url: string }> {
    const response = await this.client.post('/voice/tts', { text });
    return response.data;
  }

  // Agent endpoints
  async processIntent(text: string, context?: Record<string, any>): Promise<AgentResponse> {
    const response = await this.client.post('/agent/intent', { text, context });
    return response.data;
  }

  async executeTask(taskId: string, params?: Record<string, any>): Promise<{ success: boolean; result: any }> {
    const response = await this.client.post('/agent/execute', { task_id: taskId, params });
    return response.data;
  }

  // Task endpoints
  async getTasks(): Promise<Task[]> {
    const response = await this.client.get('/tasks');
    return response.data;
  }

  async getTodayTasks(): Promise<Task[]> {
    const response = await this.client.get('/tasks/today');
    return response.data;
  }

  async createTask(task: Omit<Task, 'id' | 'user_id' | 'created_at'>): Promise<Task> {
    const response = await this.client.post('/tasks', task);
    return response.data;
  }

  async updateTask(id: string, updates: Partial<Task>): Promise<Task> {
    const response = await this.client.patch(`/tasks/${id}`, updates);
    return response.data;
  }

  async deleteTask(id: string): Promise<void> {
    await this.client.delete(`/tasks/${id}`);
  }

  // Calendar endpoints
  async getEvents(startDate?: string, endDate?: string): Promise<CalendarEvent[]> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await this.client.get(`/calendar/events?${params}`);
    return response.data;
  }

  async createEvent(event: Omit<CalendarEvent, 'id' | 'user_id' | 'created_at'>): Promise<CalendarEvent> {
    const response = await this.client.post('/calendar/events', event);
    return response.data;
  }

  async connectCalendar(redirectUri?: string): Promise<{ authorization_url: string; state: string; redirect_uri: string }> {
    const response = await this.client.post('/calendar/connect', {
      redirect_uri: redirectUri
    });
    return response.data;
  }

  async getCalendarConnection(): Promise<CalendarConnection | null> {
    const response = await this.client.get('/calendar/connection');
    return response.data;
  }

  async disconnectCalendar(): Promise<{ message: string }> {
    const response = await this.client.delete('/calendar/connection');
    return response.data;
  }

  async syncCalendar(): Promise<{ events_synced: number; events_created: number; events_updated: number; events_deleted: number }> {
    const response = await this.client.post('/calendar/sync');
    return response.data;
  }

  async handleCalendarCallback(code: string, state?: string): Promise<CalendarConnection> {
    const response = await this.client.post('/calendar/oauth/callback', {
      code,
      state
    });
    return response.data;
  }

  // WhatsApp endpoints
  async sendWhatsAppMessage(recipient: string, message: string): Promise<{ success: boolean }> {
    const response = await this.client.post('/whatsapp/send', { recipient, message });
    return response.data;
  }
}

export const apiClient = new ApiClient();