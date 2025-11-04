import { useEffect, useRef, useState, useCallback } from 'react';
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
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
    protocols,
    onMessage,
    onError,
    onOpen,
    onClose,
    reconnectAttempts = 5,
    reconnectInterval = 3000
  } = options;

  const { user } = useAppStore();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setConnectionState('connecting');
      
      // Add auth token to WebSocket URL if user is authenticated
      const wsUrl = user ? `${url}?token=${localStorage.getItem('auth_token')}` : url;
      
      wsRef.current = new WebSocket(wsUrl, protocols);

      wsRef.current.onopen = (event) => {
        setIsConnected(true);
        setConnectionState('connected');
        reconnectCountRef.current = 0;
        onOpen?.(event);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        setConnectionState('disconnected');
        onClose?.(event);

        // Attempt reconnection if not a clean close
        if (!event.wasClean && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      wsRef.current.onerror = (event) => {
        setConnectionState('error');
        onError?.(event);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState('error');
    }
  }, [url, protocols, user, onOpen, onMessage, onClose, onError, reconnectAttempts, reconnectInterval]);

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

  // Auto-connect when user is authenticated
  useEffect(() => {
    if (user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, connect, disconnect]);

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
    connect,
    disconnect,
    sendMessage,
    sendVoiceData,
    sendVoiceStart,
    sendVoiceEnd,
    reconnectCount: reconnectCountRef.current
  };
}