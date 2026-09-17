import { useEffect, useRef, useCallback } from 'react';
import { useStreamStore } from '../store/streamStore';
import type { WebSocketStreamMessage, AllocatorVariant } from '../types/schemas';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/stream';

export function useWebSocketStream() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { setConnected, addEvent, addNotification, setActiveVariant } = useStreamStore();

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const socket = new WebSocket(WS_URL);
      wsRef.current = socket;

      socket.onopen = () => {
        setConnected(true);
        console.log('[WebSocket]: Connected to CAQI telemetry stream.');
      };

      socket.onmessage = (event) => {
        try {
          const msg: WebSocketStreamMessage = JSON.parse(event.data);
          if (msg.type === 'QUERY_PROCESSED') {
            addEvent(msg);
          } else if (msg.type === 'SYSTEM_NOTIFICATION') {
            addNotification(msg.message);
          }
        } catch (err) {
          console.error('[WebSocket JSON Parse Error]:', err);
        }
      };

      socket.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        console.warn('[WebSocket]: Connection closed. Reconnecting in 3 seconds...');
        reconnectTimerRef.current = setTimeout(() => connect(), 3000);
      };

      socket.onerror = (error) => {
        console.error('[WebSocket Error]:', error);
        socket.close();
      };
    } catch (e) {
      console.error('[WebSocket Connection Error]:', e);
      setConnected(false);
      reconnectTimerRef.current = setTimeout(() => connect(), 3000);
    }
  }, [setConnected, addEvent, addNotification]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const switchVariant = useCallback((variant: AllocatorVariant) => {
    setActiveVariant(variant);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'set_variant', variant }));
    }
  }, [setActiveVariant]);

  const triggerSpikeControl = useCallback((multiplier: number = 5.0, duration: number = 15.0) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'trigger_spike', multiplier, duration }));
    }
  }, []);

  const clearSpikeControl = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'clear_spike' }));
    }
  }, []);

  return {
    switchVariant,
    triggerSpikeControl,
    clearSpikeControl,
  };
}

