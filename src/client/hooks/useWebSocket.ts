import { useEffect, useRef, useCallback, useState } from 'react';
import { WS_URL } from '../config';

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
  type?: 'text' | 'image';
  imageData?: string;
}

interface WSMessage {
  type: 'auth' | 'message' | 'typing' | 'status' | 'online' | 'read' | 'error' | 'group_message' | 'group_read' | 'group_typing' | 'group_event';
  payload: any;
}

interface UseWebSocketProps {
  userId: string;
  username: string;
  onMessage: (message: Message) => void;
  onTyping: (userId: string, typing: boolean) => void;
  onOnlineStatus: (users: Array<{ userId: string; username: string; online: boolean }>) => void;
  onReadReceipt: (messageIds: string[]) => void;
  onGroupMessage?: (message: any) => void;
  onGroupTyping?: (groupId: string, userId: string, username: string, typing: boolean) => void;
  onGroupEvent?: (event: any) => void;
  enabled?: boolean;
}

export const useWebSocket = ({
  userId,
  username,
  onMessage,
  onTyping,
  onOnlineStatus,
  onReadReceipt,
  onGroupMessage,
  onGroupTyping,
  onGroupEvent,
  enabled = true,
}: UseWebSocketProps) => {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeout = useRef<number>();

  const connect = useCallback(() => {
    const wsUrl = WS_URL;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);

      // Ensure connection is ready before sending
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(
          JSON.stringify({
            type: 'auth',
            payload: { userId, username },
          })
        );
      }
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
              // Received list of online users
              onOnlineStatus(data.payload.users);
            } else {
              // Received single user status update
              onOnlineStatus([data.payload]);
            }
            break;
          case 'read':
            if (data.payload.messageIds) {
              onReadReceipt(data.payload.messageIds);
            }
            break;
          case 'group_message':
            if (onGroupMessage) {
              onGroupMessage(data.payload);
            }
            break;
          case 'group_typing':
            if (onGroupTyping) {
              onGroupTyping(
                data.payload.groupId,
                data.payload.userId,
                data.payload.username,
                data.payload.typing
              );
            }
            break;
          case 'group_event':
            if (onGroupEvent) {
              onGroupEvent(data.payload);
            }
            break;
          case 'error':
            console.error('[WebSocket] Server error:', data.payload.message);
            // Handle authentication errors with user confirmation
            if (data.payload.message.includes('not found') || data.payload.message.includes('log in again')) {
              const shouldLogout = confirm(
                'Session error: ' + data.payload.message + '\n\n' +
                'Would you like to logout and login again? If you click "Cancel", ' +
                'you can try reconnecting by refreshing the page.'
              );
              if (shouldLogout) {
                localStorage.removeItem('user');
                window.location.reload();
              }
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

      // Clear online users when connection closes (e.g., on logout)
      // This prevents showing stale online status
      onOnlineStatus([]);

      reconnectTimeout.current = window.setTimeout(() => {
        console.log('Attempting to reconnect...');
        connect();
      }, 3000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [userId, username, onMessage, onTyping, onOnlineStatus, onReadReceipt, onGroupMessage, onGroupTyping, onGroupEvent]);

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

  const sendMessage = useCallback((to: string, content: string, encrypted: boolean = false, messageId?: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(
          JSON.stringify({
            type: 'message',
            payload: { to, content, messageType: 'text', encrypted, messageId },
          })
        );
      } catch (error) {
        console.error('Failed to send message:', error);
      }
    } else {
      console.warn('WebSocket not ready, message not sent');
    }
  }, []);

  const sendImage = useCallback((to: string, imageData: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'message',
          payload: { to, content: '📷 Image', imageData, messageType: 'image' },
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

  const sendGroupMessage = useCallback((groupId: string, content: string, messageType: string = 'text', imageData?: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'group_message',
          payload: { groupId, content, messageType, imageData },
        })
      );
    }
  }, []);

  const sendGroupTyping = useCallback((groupId: string, typing: boolean) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'group_typing',
          payload: { groupId, typing },
        })
      );
    }
  }, []);

  const sendGroupRead = useCallback((groupId: string, messageId: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'group_read',
          payload: { groupId, messageId },
        })
      );
    }
  }, []);

  return {
    connected,
    sendMessage,
    sendImage,
    sendTyping,
    sendStatus,
    sendReadReceipt,
    sendGroupMessage,
    sendGroupTyping,
    sendGroupRead,
  };
};
