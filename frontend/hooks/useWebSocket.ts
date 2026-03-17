// i/app/frontend/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

interface UseWebSocketOptions {
  url?: string;
  protocols?: string | string[];
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  enabled?: boolean; // New: allow disabling WebSocket
  autoConnect?: boolean; // New: allow manual connect (recommended for voice)
}

const isDevelopment = process.env.NODE_ENV === 'development';
const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_INTERVAL = 1000; // 1 second
const MAX_RECONNECT_INTERVAL = 30000; // 30 seconds
const CIRCUIT_BREAKER_THRESHOLD = 3; // After 3 failures, wait longer

function normalizeVoiceWsUrl(rawUrl: string | undefined, sessionId: string): string | undefined {
  if (!rawUrl) return undefined;

  const trimmed = rawUrl.trim();
  if (!trimmed) return undefined;

  // Replace common placeholders
  const placeholderNormalized = trimmed
    .replace(/\{session_id\}/g, sessionId)
    .replace(/%7Bsession_id%7D/gi, sessionId);

  // If already points to the expected endpoint, just ensure session id exists.
  if (placeholderNormalized.includes('/api/v1/voice/stream/')) {
    if (placeholderNormalized.endsWith('/api/v1/voice/stream') || placeholderNormalized.endsWith('/api/v1/voice/stream/')) {
      return `${placeholderNormalized.replace(/\/$/, '')}/${sessionId}`;
    }
    return placeholderNormalized;
  }

  // Common misconfiguration: setting it to /ws (HTTP or WS).
  if (placeholderNormalized.endsWith('/ws')) {
    return `${placeholderNormalized.replace(/\/ws$/, '')}/api/v1/voice/stream/${sessionId}`;
  }

  // If it's a base URL (host only or with a different path), append the expected endpoint.
  if (placeholderNormalized.startsWith('ws://') || placeholderNormalized.startsWith('wss://')) {
    return `${placeholderNormalized.replace(/\/$/, '')}/api/v1/voice/stream/${sessionId}`;
  }

  // Allow passing http(s) base and convert to ws(s)
  if (placeholderNormalized.startsWith('https://')) {
    return `wss://${placeholderNormalized.slice('https://'.length).replace(/\/$/, '')}/api/v1/voice/stream/${sessionId}`;
  }
  if (placeholderNormalized.startsWith('http://')) {
    return `ws://${placeholderNormalized.slice('http://'.length).replace(/\/$/, '')}/api/v1/voice/stream/${sessionId}`;
  }

  return placeholderNormalized;
}

function getBrowserAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

function withWsAuthQuery(url: string, token: string | null): string {
  if (!token) return url;
  try {
    const u = new URL(url);
    if (!u.searchParams.get('token')) {
      u.searchParams.set('token', token);
    }
    return u.toString();
  } catch {
    // If URL parsing fails (shouldn't for ws://...), fallback to original
    return url;
  }
}

function createSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const [sessionId] = useState(createSessionId);

  // ✅ تنظیم URL پیش‌فرض
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
  const defaultWsUrl = useMemo(() => {
    return (
      normalizeVoiceWsUrl(wsUrl, sessionId) ||
      `ws://localhost:8000/api/v1/voice/stream/${sessionId}`
    );
  }, [sessionId, wsUrl]);
  
  const {
    url = defaultWsUrl,
    protocols,
    onMessage,
    onError,
    onOpen,
    onClose,
    reconnectAttempts = MAX_RECONNECT_ATTEMPTS,
    reconnectInterval = INITIAL_RECONNECT_INTERVAL,
    enabled = true,
    autoConnect = true
  } = options;

  const { user } = useAppStore();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);
  const consecutiveFailuresRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const lastErrorTimeRef = useRef<number | null>(null);
  const connectRef = useRef<() => void>(() => {});

  // Calculate exponential backoff delay
  const getReconnectDelay = useCallback((attempt: number): number => {
    const baseDelay = reconnectInterval;
    const exponentialDelay = Math.min(
      baseDelay * Math.pow(2, attempt),
      MAX_RECONNECT_INTERVAL
    );
    
    // Add jitter to prevent thundering herd
    const jitter = Math.random() * 1000;
    return exponentialDelay + jitter;
  }, [reconnectInterval]);

  // Log errors only in development or if explicitly enabled
  const logError = useCallback((message: string, error?: any) => {
    if (isDevelopment) {
      console.warn(`[WebSocket] ${message}`, error || '');
    }
  }, []);

  const effectiveUrl = useMemo(() => {
    const token = getBrowserAuthToken();
    return withWsAuthQuery(url, token);
  }, [url]);

  const connect = useCallback(() => {
    const isAuthRoute = typeof window !== 'undefined' && window.location.pathname.startsWith('/auth');
    if (isAuthRoute) {
      return;
    }

    // ✅ بررسی URL قبل از اتصال
    if (!enabled || !effectiveUrl) {
      logError('WebSocket URL not configured or disabled');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Circuit breaker: if too many failures, wait longer before retrying
    if (consecutiveFailuresRef.current >= CIRCUIT_BREAKER_THRESHOLD) {
      const lastError = lastErrorTimeRef.current;
      const timeSinceLastError = lastError ? Date.now() - lastError : Infinity;
      const circuitBreakerDelay = 60000; // 1 minute circuit breaker delay
      
      if (timeSinceLastError < circuitBreakerDelay) {
        logError(`Circuit breaker active. Waiting ${Math.ceil((circuitBreakerDelay - timeSinceLastError) / 1000)}s before retry`);
        return;
      }
      
      // Reset circuit breaker after delay
      consecutiveFailuresRef.current = 0;
    }

    // Don't reconnect if we've exceeded max attempts
    if (reconnectCountRef.current >= reconnectAttempts) {
      logError(`Max reconnection attempts (${reconnectAttempts}) reached. WebSocket disabled.`);
      shouldReconnectRef.current = false;
      return;
    }

    try {
      setConnectionState('connecting');
      
      wsRef.current = new WebSocket(effectiveUrl, protocols);

      wsRef.current.onopen = (event) => {
        console.log('✅ WebSocket connected successfully!');
        setIsConnected(true);
        setConnectionState('connected');
        reconnectCountRef.current = 0;
        consecutiveFailuresRef.current = 0;
        lastErrorTimeRef.current = null;
        shouldReconnectRef.current = true;
        onOpen?.(event);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📩 WebSocket message received:', message);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          logError('Failed to parse WebSocket message', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        setConnectionState('disconnected');
        onClose?.(event);

        // Only attempt reconnection if it wasn't a clean close and we haven't exceeded attempts
        if (!event.wasClean && shouldReconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          consecutiveFailuresRef.current++;
          lastErrorTimeRef.current = Date.now();
          
          const delay = getReconnectDelay(reconnectCountRef.current - 1);
          console.log(`Reconnecting in ${Math.ceil(delay / 1000)}s...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (shouldReconnectRef.current && enabled) {
              connectRef.current();
            }
          }, delay);
        } else if (!event.wasClean && reconnectCountRef.current >= reconnectAttempts) {
          logError('Max reconnection attempts reached. Stopping reconnection attempts.');
          shouldReconnectRef.current = false;
        }
      };

      wsRef.current.onerror = (event) => {
        console.error('❌ WebSocket error:', event);
        setConnectionState('error');
        consecutiveFailuresRef.current++;
        lastErrorTimeRef.current = Date.now();
        
        onError?.(event);
      };

    } catch (error) {
      logError('Failed to create WebSocket connection', error);
      setConnectionState('error');
      consecutiveFailuresRef.current++;
      lastErrorTimeRef.current = Date.now();
    }
  }, [effectiveUrl, protocols, onOpen, onMessage, onClose, onError, reconnectAttempts, enabled, getReconnectDelay, logError]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionState('disconnected');
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const wsMessage: WebSocketMessage = {
        type: message.type || 'message',
        data: message.data || message,
        timestamp: new Date().toISOString()
      };
      
      wsRef.current.send(JSON.stringify(wsMessage));
      return true;
    }
    
    console.warn('WebSocket is not connected');
    return false;
  }, []);

  const sendVoiceData = useCallback((audioData: ArrayBuffer, sampleRate: number = 16000) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'voice_data',
        data: {
          audio: Array.from(new Uint8Array(audioData)),
          sample_rate: sampleRate,
          timestamp: Date.now()
        }
      };
      
      return sendMessage(message);
    }
    
    return false;
  }, [sendMessage]);

  const sendVoiceStart = useCallback(() => {
    return sendMessage({
      type: 'voice_start',
      data: { timestamp: Date.now() }
    });
  }, [sendMessage]);

  const sendVoiceEnd = useCallback(() => {
    return sendMessage({
      type: 'voice_end',
      data: { timestamp: Date.now() }
    });
  }, [sendMessage]);

  // Auto-connect when user is authenticated and enabled
  useEffect(() => {
    // Don't try to connect if URL is not configured
    if (!effectiveUrl && !wsUrl) {
      return;
    }

    const isAuthRoute = typeof window !== 'undefined' && window.location.pathname.startsWith('/auth');
    if (isAuthRoute) {
      const disconnectFrame = requestAnimationFrame(() => {
        disconnect();
      });
      return () => cancelAnimationFrame(disconnectFrame);
    }
    
    if (!autoConnect) {
      return;
    }

    const token = getBrowserAuthToken();
    if (enabled && token && effectiveUrl) {
      const connectFrame = requestAnimationFrame(() => {
        connect();
      });
      return () => cancelAnimationFrame(connectFrame);
    } else {
      const disconnectFrame = requestAnimationFrame(() => {
        disconnect();
      });
      return () => cancelAnimationFrame(disconnectFrame);
    }
  }, [autoConnect, enabled, effectiveUrl, wsUrl, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    connectionState,
    lastMessage,
    sendMessage,
    sendVoiceStart,
    sendVoiceData,
    sendVoiceEnd,
    connect,
    disconnect
  };
}
