import { useEffect, useRef, useState, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { logger } from '@/lib/logger';

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
}

const MAX_RECONNECT_ATTEMPTS = 3; // Reduced from 5 to minimize spam
const INITIAL_RECONNECT_INTERVAL = 2000; // 2 seconds
const MAX_RECONNECT_INTERVAL = 30000; // 30 seconds
const CIRCUIT_BREAKER_THRESHOLD = 2; // After 2 failures, wait longer
const CIRCUIT_BREAKER_DELAY = 60000; // 1 minute circuit breaker delay


export function useWebSocket(options: UseWebSocketOptions = {}) {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
  
  const {
    url = wsUrl,
    protocols,
    onMessage,
    onError,
    onOpen,
    onClose,
    reconnectAttempts = MAX_RECONNECT_ATTEMPTS,
    reconnectInterval = INITIAL_RECONNECT_INTERVAL,
    enabled = true
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
  const hasLoggedInitialErrorRef = useRef(false); // Track if we've logged the initial error
  const isConnectingRef = useRef(false); // Track if we're currently connecting
  const callbacksRef = useRef({ onMessage, onError, onOpen, onClose }); // Store callbacks in ref
  const urlRef = useRef(url); // Store URL in ref
  const enabledRef = useRef(enabled); // Store enabled in ref
  
  // Update refs when values change
  useEffect(() => {
    callbacksRef.current = { onMessage, onError, onOpen, onClose };
    urlRef.current = url;
    enabledRef.current = enabled;
  }, [onMessage, onError, onOpen, onClose, url, enabled]);

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

  const connect = useCallback(() => {
    const currentUrl = urlRef.current;
    const currentEnabled = enabledRef.current;
    
    // Don't connect if disabled, no URL, already connected, or currently connecting
    if (!currentEnabled || !currentUrl || currentUrl.trim() === '' || 
        wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING ||
        isConnectingRef.current) {
      // If URL is not set, silently disable WebSocket (expected behavior)
      if (!currentUrl || currentUrl.trim() === '') {
        shouldReconnectRef.current = false;
        setConnectionState('disconnected');
      }
      return;
    }

    // Circuit breaker: if too many failures, wait longer before retrying
    if (consecutiveFailuresRef.current >= CIRCUIT_BREAKER_THRESHOLD) {
      const lastError = lastErrorTimeRef.current;
      const timeSinceLastError = lastError ? Date.now() - lastError : Infinity;
      
      if (timeSinceLastError < CIRCUIT_BREAKER_DELAY) {
        // Only log circuit breaker message once per minute
        if (!hasLoggedInitialErrorRef.current) {
          logger.debug(`[WebSocket] Server unavailable. Retrying in ${Math.ceil((CIRCUIT_BREAKER_DELAY - timeSinceLastError) / 1000)}s...`);
          hasLoggedInitialErrorRef.current = true;
        }
        return;
      }
      
      // Reset circuit breaker after delay
      consecutiveFailuresRef.current = 0;
      hasLoggedInitialErrorRef.current = false;
    }

    // Don't reconnect if we've exceeded max attempts
    if (reconnectCountRef.current >= reconnectAttempts) {
      if (!hasLoggedInitialErrorRef.current) {
        logger.debug(`[WebSocket] Max reconnection attempts (${reconnectAttempts}) reached. WebSocket disabled.`);
        hasLoggedInitialErrorRef.current = true;
      }
      shouldReconnectRef.current = false;
      return;
    }

    try {
      isConnectingRef.current = true;
      setConnectionState('connecting');
      
      // Close existing connection if any
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) {
          // Ignore errors when closing
        }
        wsRef.current = null;
      }
      
      // Add auth token to WebSocket URL if user is authenticated
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      const wsUrlWithAuth = token ? `${currentUrl}?token=${token}` : currentUrl;
      
      wsRef.current = new WebSocket(wsUrlWithAuth, protocols);

      wsRef.current.onopen = (event) => {
        isConnectingRef.current = false;
        setIsConnected(true);
        setConnectionState('connected');
        reconnectCountRef.current = 0;
        consecutiveFailuresRef.current = 0;
        lastErrorTimeRef.current = null;
        shouldReconnectRef.current = true;
        hasLoggedInitialErrorRef.current = false;
        logger.debug('[WebSocket] Connected successfully');
        callbacksRef.current.onOpen?.(event);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          callbacksRef.current.onMessage?.(message);
        } catch (error) {
          logger.debug('[WebSocket] Failed to parse message', error);
        }
      };

      wsRef.current.onclose = (event) => {
        isConnectingRef.current = false;
        setIsConnected(false);
        setConnectionState('disconnected');
        callbacksRef.current.onClose?.(event);

        // Only attempt reconnection if it wasn't a clean close and we haven't exceeded attempts
        if (!event.wasClean && shouldReconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          consecutiveFailuresRef.current++;
          lastErrorTimeRef.current = Date.now();
          
          // Only log first few attempts
          if (reconnectCountRef.current <= 2) {
            const delay = getReconnectDelay(reconnectCountRef.current - 1);
            logger.debug(`[WebSocket] Connection closed. Reconnecting in ${Math.ceil(delay / 1000)}s (attempt ${reconnectCountRef.current}/${reconnectAttempts})`);
          }
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (shouldReconnectRef.current && enabledRef.current) {
              connect();
            }
          }, getReconnectDelay(reconnectCountRef.current - 1));
        } else if (!event.wasClean && reconnectCountRef.current >= reconnectAttempts) {
          if (!hasLoggedInitialErrorRef.current) {
            logger.debug('[WebSocket] Max reconnection attempts reached. Stopping reconnection attempts.');
            hasLoggedInitialErrorRef.current = true;
          }
          shouldReconnectRef.current = false;
        }
      };

      wsRef.current.onerror = (event) => {
        isConnectingRef.current = false;
        setConnectionState('error');
        consecutiveFailuresRef.current++;
        lastErrorTimeRef.current = Date.now();
        
        // Only log first error to avoid spam
        if (consecutiveFailuresRef.current === 1) {
          logger.debug('[WebSocket] Connection error (this is normal if WebSocket server is not configured)');
        }
        
        callbacksRef.current.onError?.(event);
      };

    } catch (error) {
      isConnectingRef.current = false;
      logger.debug('[WebSocket] Failed to create connection', error);
      setConnectionState('error');
      consecutiveFailuresRef.current++;
      lastErrorTimeRef.current = Date.now();
    }
  }, [protocols, reconnectAttempts, getReconnectDelay]);

  const disconnect = useCallback(() => {
    isConnectingRef.current = false;
    shouldReconnectRef.current = false;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      try {
        wsRef.current.close(1000, 'Manual disconnect');
      } catch (e) {
        // Ignore errors when closing
      }
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
    
    logger.debug('WebSocket is not connected');
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
  // Use a single useEffect to handle all connection logic
  useEffect(() => {
    const currentUrl = urlRef.current;
    const currentEnabled = enabledRef.current;
    
    // Only connect if URL is provided and not empty
    if (currentEnabled && user && currentUrl && currentUrl.trim() !== '') {
      // Only connect if not already connected or connecting
      if (wsRef.current?.readyState !== WebSocket.OPEN && 
          wsRef.current?.readyState !== WebSocket.CONNECTING &&
          !isConnectingRef.current) {
        connect();
      }
    } else {
      // Only disconnect if currently connected
      if (wsRef.current?.readyState === WebSocket.OPEN || 
          wsRef.current?.readyState === WebSocket.CONNECTING ||
          isConnectingRef.current) {
        disconnect();
      }
      // If URL is not set, this is expected - don't log errors
      if (!currentUrl || currentUrl.trim() === '') {
        shouldReconnectRef.current = false;
      }
    }

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, url, enabled]); // Depend on user, url, and enabled - single effect to avoid duplicates

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on unmount

  return {
    isConnected,
    connectionState,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
    sendVoiceData,
    sendVoiceStart,
    sendVoiceEnd,
    reconnectCount: reconnectCountRef.current
  };
}