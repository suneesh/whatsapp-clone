import { useEffect, useRef, useCallback, useState } from 'react';

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
}

interface WSMessage {
  type: 'auth' | 'message' | 'typing' | 'status' | 'online' | 'read' | 'error';
  payload: any;
}

interface UseWebSocketProps {
  userId: string;
  username: string;
  onMessage: (message: Message) => void;
  onTyping: (userId: string, typing: boolean) => void;
  onOnlineStatus: (users: Array<{ userId: string; username: string; online: boolean }>) => void;
  onReadReceipt: (messageIds: string[]) => void;
  enabled?: boolean;
}

export const useWebSocket = ({
  userId,
  username,
  onMessage,
  onTyping,
  onOnlineStatus,
  onReadReceipt,
  enabled = true,
}: UseWebSocketProps) => {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeout = useRef<number>();

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // In development, use the worker port (8787), in production use current port
    const port = import.meta.env.DEV ? '8787' : window.location.port;
    const wsUrl = `${protocol}//${window.location.hostname}:${port}/ws`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);

      ws.current?.send(
        JSON.stringify({
          type: 'auth',
          payload: { userId, username },
        })
      );
    };

    ws.current.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);

        switch (data.type) {
          case 'message':
            onMessage(data.payload);
            break;
          case 'typing':
            onTyping(data.payload.from, data.payload.typing);
            break;
          case 'online':
            if (data.payload.users) {
              onOnlineStatus(data.payload.users.map((u: any) => ({ ...u, online: true })));
            } else {
              onOnlineStatus([data.payload]);
            }
            break;
          case 'read':
            if (data.payload.messageIds) {
              onReadReceipt(data.payload.messageIds);
            }
            break;
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);

      reconnectTimeout.current = window.setTimeout(() => {
        console.log('Attempting to reconnect...');
        connect();
      }, 3000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [userId, username, onMessage, onTyping, onOnlineStatus, onReadReceipt]);

  useEffect(() => {
    if (!enabled || !userId) {
      return;
    }

    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect, enabled, userId]);

  const sendMessage = useCallback((to: string, content: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'message',
          payload: { to, content },
        })
      );
    }
  }, []);

  const sendTyping = useCallback((to: string, typing: boolean) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'typing',
          payload: { to, typing },
        })
      );
    }
  }, []);

  const sendStatus = useCallback((to: string, messageId: string, status: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'status',
          payload: { to, messageId, status },
        })
      );
    }
  }, []);

  const sendReadReceipt = useCallback((messageIds: string[], to: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log(`[Read Receipt] Sending for ${messageIds.length} messages to ${to}`);
      ws.current.send(
        JSON.stringify({
          type: 'read',
          payload: { messageIds, to },
        })
      );
    }
  }, []);

  return {
    connected,
    sendMessage,
    sendTyping,
    sendStatus,
    sendReadReceipt,
  };
};
