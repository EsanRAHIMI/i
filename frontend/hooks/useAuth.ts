import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { User } from '@/types';

export function useAuth() {
  const { user, setUser, setSettings, setLoading, setError, isLoading } = useAppStore();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let hasInitialized = false;
    
    const initializeAuth = async () => {
      // Prevent multiple initializations
      if (hasInitialized) {
        return;
      }
      hasInitialized = true;
      
      try {
        setLoading(true);
        
        // Check if user is already authenticated
        // Only access localStorage in browser environment
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
        if (token) {
          try {
            const currentUser = await apiClient.getCurrentUser();
            
            // Only set user if component is still mounted and we got a valid user
            if (isMounted && currentUser) {
              setUser(currentUser);
              
              // Try to get settings in background - don't wait for it or fail on error
              // This is non-critical and should not block initialization
              apiClient.getUserSettings()
                .then((settings) => {
                  if (isMounted) {
                    setSettings(settings);
                  }
                })
                .catch((settingsError: any) => {
                  // Settings might not exist or there might be a temporary error
                  // Only log if it's not an auth error
                  if (settingsError.response?.status !== 401 && 
                      settingsError.response?.status !== 403) {
                    console.warn('Could not fetch user settings during initialization:', settingsError);
                  }
                });
            }
          } catch (authError: any) {
            // Token is invalid - clear everything only if it's a real auth error
            // Don't clear on network errors or temporary issues
            if (authError.response?.status === 401 || authError.response?.status === 403) {
              console.error('Auth token is invalid:', authError);
              if (isMounted && typeof window !== 'undefined') {
                localStorage.removeItem('auth_token');
                setUser(null);
              }
            } else {
              // Network error or other issue - don't clear token, just log
              console.warn('Failed to verify token (non-auth error):', authError);
              // Don't clear user state on network errors
            }
          }
        } else {
          // No token - make sure user is cleared
          if (isMounted) {
            setUser(null);
          }
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        // Only clear token if it's definitely invalid
        // Don't clear on general errors
      } finally {
        if (isMounted) {
          setLoading(false);
          setIsInitialized(true);
        }
      }
    };

    initializeAuth();
    
    return () => {
      isMounted = false;
    };
  }, [setUser, setSettings, setLoading]);

  const login = async (email: string, password: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      const { user: loggedInUser, token } = await apiClient.login(email, password);
      
      // Ensure token is saved - apiClient.login already saves it, but verify it's there
      if (!token) {
        throw new Error('Token not received from login response');
      }
      
      // Double-check token is in localStorage (it should be set by apiClient.login)
      // Only access localStorage in browser environment
      if (typeof window !== 'undefined') {
        const storedToken = localStorage.getItem('auth_token');
        if (!storedToken || storedToken !== token) {
          // Token not saved properly, save it now
          localStorage.setItem('auth_token', token);
        }
      }
      
      // Set user immediately - this triggers isAuthenticated to become true
      setUser(loggedInUser);
      
      // Don't fetch settings immediately - let the dashboard page handle it after redirect
      // This prevents race conditions and 401 errors
    } catch (error: any) {
      let message = 'ورود ناموفق بود';
      
      if (error.response?.data) {
        const data = error.response.data;
        if (data.detail) {
          if (typeof data.detail === 'string') {
            message = data.detail;
          } else if (Array.isArray(data.detail)) {
            message = data.detail
              .map((err: any) => err.msg || err.message || JSON.stringify(err))
              .filter(Boolean)
              .join('؛ ');
          }
        }
        
        if (data.errors && Array.isArray(data.errors)) {
          message = data.errors
            .map((err: any) => err.message || err.msg || JSON.stringify(err))
            .filter(Boolean)
            .join('؛ ');
        }
        
        // Handle specific status codes
        if (error.response.status === 500) {
          message = 'خطای سرور. لطفاً بعداً تلاش کنید.';
        } else if (error.response.status === 401) {
          message = 'ایمیل یا رمز عبور اشتباه است.';
        }
      } else if (error.message) {
        if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
          message = 'خطای اتصال به سرور. لطفاً اتصال اینترنت خود را بررسی کنید.';
        } else {
          message = error.message;
        }
      }
      
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      const { user: newUser } = await apiClient.register(email, password);
      
      // Set user immediately - this triggers isAuthenticated to become true
      setUser(newUser);
      
      // Try to get settings, but don't fail if it doesn't exist yet
      // This runs in background - redirect happens from page component
      try {
        const settings = await apiClient.getUserSettings();
        setSettings(settings);
      } catch (settingsError: any) {
        // Settings might not exist immediately after registration
        // This is not a critical error
        console.warn('Could not fetch user settings:', settingsError);
      }
    } catch (error: any) {
      // Handle validation errors (422) with better message extraction
      let message = 'ثبت نام ناموفق بود';
      
      if (error.response?.data) {
        const data = error.response.data;
        
        // FastAPI validation errors return detail as string or errors array
        if (data.detail) {
          if (typeof data.detail === 'string') {
            message = data.detail;
          } else if (Array.isArray(data.detail)) {
            // Pydantic validation format
            message = data.detail
              .map((err: any) => {
                if (err.msg) return err.msg;
                if (err.message) return err.message;
                return JSON.stringify(err);
              })
              .filter(Boolean)
              .join('؛ ');
          }
        }
        
        // Our custom validation error format
        if (data.errors && Array.isArray(data.errors)) {
          message = data.errors
            .map((err: any) => err.message || err.msg || JSON.stringify(err))
            .filter(Boolean)
            .join('؛ ');
        }
        
        // Handle specific status codes
        if (error.response.status === 500) {
          message = 'خطای سرور. لطفاً بعداً تلاش کنید.';
        } else if (error.response.status === 422) {
          if (message === 'ثبت نام ناموفق بود') {
            message = 'اطلاعات وارد شده معتبر نیست. لطفاً دوباره تلاش کنید.';
          }
        }
      } else if (error.message) {
        if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
          message = 'خطای اتصال به سرور. لطفاً اتصال اینترنت خود را بررسی کنید.';
        } else {
          message = error.message;
        }
      }
      
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await apiClient.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setSettings(null);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
      }
    }
  };

  const updateProfile = async (updates: Partial<User>): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      const updatedUser = await apiClient.updateUser(updates);
      setUser(updatedUser);
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Profile update failed';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  // Ensure isAuthenticated is computed from user state
  const isAuthenticated = !!user;

  return {
    user,
    isAuthenticated,
    isInitialized,
    isLoading,
    login,
    register,
    logout,
    updateProfile,
  };
}