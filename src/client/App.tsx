import { useState, useEffect, useCallback } from 'react';
import Login from './components/Login';
import Chat from './components/Chat';
import AdminDashboard from './components/AdminDashboard';
import { useWebSocket } from './hooks/useWebSocket';
import { apiFetch } from './utils/api';

interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
  role?: string;
  is_active?: number;
  can_send_images?: number;
  created_at?: number;
  disabled_at?: number;
  disabled_by?: string;
  lastSeen?: number;
}

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

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [groupMessages, setGroupMessages] = useState<any[]>([]);
  const [groupTypingUsers, setGroupTypingUsers] = useState<Map<string, Set<string>>>(new Map());
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);

  // Restore user from localStorage on app mount
  useEffect(() => {
    // Clear users list on mount - only show users who connect via WebSocket
    setUsers([]);
    
    try {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const user = JSON.parse(storedUser);
        setCurrentUser(user);
        console.log('[App] Restored user from localStorage:', user.username);
      }
    } catch (error) {
      console.error('Failed to restore user from localStorage:', error);
      localStorage.removeItem('user');
    }
  }, []);

  const handleMessage = useCallback((message: Message) => {
    setMessages((prev) => {
      const exists = prev.find((m) => m.id === message.id);
      if (exists) {
        return prev.map((m) => (m.id === message.id ? message : m));
      }
      return [...prev, message];
    });
  }, []);

  const handleTyping = useCallback((userId: string, typing: boolean) => {
    setTypingUsers((prev) => {
      const newSet = new Set(prev);
      if (typing) {
        newSet.add(userId);
      } else {
        newSet.delete(userId);
      }
      return newSet;
    });
  }, []);

  const handleOnlineStatus = useCallback(
    (statusUpdates: Array<{ userId: string; username: string; online: boolean }>) => {
      setUsers((prev) => {
        let updated = [...prev];
        statusUpdates.forEach((update) => {
          const index = updated.findIndex((u) => u.id === update.userId);
          
          if (update.online) {
            // User came online
            if (index !== -1) {
              updated[index] = { ...updated[index], online: true };
            } else if (update.userId !== currentUser?.id) {
              updated.push({
                id: update.userId,
                username: update.username,
                online: true,
              });
            }
          } else {
            // User went offline - remove them from the list
            if (index !== -1) {
              updated = updated.filter((u) => u.id !== update.userId);
            }
          }
        });
        return updated;
      });
    },
    [currentUser]
  );

  const handleReadReceipt = useCallback((messageIds: string[]) => {
    console.log(`[App] Received read receipt for ${messageIds.length} messages`);
    setMessages((prev) =>
      prev.map((m) =>
        messageIds.includes(m.id) ? { ...m, status: 'read' } : m
      )
    );
  }, []);

  const handleGroupMessage = useCallback((message: any) => {
    setGroupMessages((prev) => {
      const exists = prev.find((m) => m.id === message.id);
      if (exists) {
        return prev;
      }
      return [...prev, message];
    });
  }, []);

  const handleWebSocketGroupTyping = useCallback((groupId: string, userId: string, username: string, typing: boolean) => {
    setGroupTypingUsers((prev) => {
      const newMap = new Map(prev);
      const groupTyping = newMap.get(groupId) || new Set<string>();
      
      if (typing) {
        groupTyping.add(userId);
      } else {
        groupTyping.delete(userId);
      }
      
      if (groupTyping.size > 0) {
        newMap.set(groupId, groupTyping);
      } else {
        newMap.delete(groupId);
      }
      
      return newMap;
    });
  }, []);

  const handleGroupEvent = useCallback((event: any) => {
    console.log('[App] Group event:', event);
    // Could handle group events like member added/removed here
  }, []);

  // WebSocket connection - always call the hook
  const websocketEnabled = currentUser !== null;
  const { 
    connected, 
    sendMessage, 
    sendImage, 
    sendTyping, 
    sendStatus, 
    sendReadReceipt,
    sendGroupMessage,
    sendGroupTyping,
    sendGroupRead,
  } = useWebSocket({
    userId: currentUser?.id || '',
    username: currentUser?.username || '',
    onMessage: handleMessage,
    onTyping: handleTyping,
    onOnlineStatus: handleOnlineStatus,
    onReadReceipt: handleReadReceipt,
    onGroupMessage: handleGroupMessage,
    onGroupTyping: handleWebSocketGroupTyping,
    onGroupEvent: handleGroupEvent,
    enabled: websocketEnabled,
  });

  const handleMarkAsRead = useCallback((toUserId: string, messageIds: string[]) => {
    console.log(`[App] Marking ${messageIds.length} messages as read to ${toUserId}`);
    // Optimistic UI update
    setMessages((prev) =>
      prev.map((m) =>
        messageIds.includes(m.id) ? { ...m, status: 'read' } : m
      )
    );

    // Send via WebSocket
    sendReadReceipt(messageIds, toUserId);
  }, [sendReadReceipt]);

  useEffect(() => {
    if (currentUser) {
      // Don't fetch all users from database - only show users who come online via WebSocket
      // This prevents showing stale/offline users
    }
  }, [currentUser]);

  const fetchUsers = async () => {
    // Deprecated: Don't fetch all users from database
    // Only show users who connect via WebSocket (online users only)
    // This prevents the stale user list issue
  };

  const handleLogin = async (username: string, password: string) => {
    try {
      const response = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentUser(data as User);
        // Save user to localStorage
        localStorage.setItem('user', JSON.stringify(data));
        console.log('[App] User logged in and saved to localStorage');
      } else {
        console.error('Login failed:', (data as any).error);
        throw new Error((data as any).error || 'Login failed');
      }
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const handleRegister = async (username: string, password: string) => {
    try {
      const response = await apiFetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentUser(data as User);
        // Save user to localStorage
        localStorage.setItem('user', JSON.stringify(data));
        console.log('[App] User registered and saved to localStorage');
      } else {
        console.error('Registration failed:', (data as any).error);
        throw new Error((data as any).error || 'Registration failed');
      }
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const handleLogout = () => {
    // Clear all state
    setCurrentUser(null);
    setUsers([]);
    setMessages([]);
    setTypingUsers(new Set());
    setGroupMessages([]);
    setGroupTypingUsers(new Map());
    // Clear localStorage
    localStorage.removeItem('user');
    console.log('[App] User logged out');
  };

  const handleSendGroupMessage = useCallback((groupId: string, content: string, type?: string) => {
    sendGroupMessage(groupId, content, type || 'text');
  }, [sendGroupMessage]);

  const handleSendGroupImage = useCallback((groupId: string, imageData: string) => {
    sendGroupMessage(groupId, '📷 Image', 'image', imageData);
  }, [sendGroupMessage]);

  const handleGroupTyping = useCallback((groupId: string, typing: boolean) => {
    sendGroupTyping(groupId, typing);
  }, [sendGroupTyping]);

  if (!currentUser) {
    return <Login onLogin={handleLogin} onRegister={handleRegister} />;
  }

  return (
    <>
      <Chat
        currentUser={currentUser}
        users={users}
        messages={messages}
        typingUsers={typingUsers}
        connected={connected}
        onSendMessage={sendMessage}
        onSendImage={sendImage}
        onTyping={sendTyping}
        onMarkAsRead={handleMarkAsRead}
        onLogout={handleLogout}
        onOpenAdmin={() => setShowAdminDashboard(true)}
        groupMessages={groupMessages}
        groupTypingUsers={groupTypingUsers}
        onSendGroupMessage={handleSendGroupMessage}
        onSendGroupImage={handleSendGroupImage}
        onGroupTyping={handleGroupTyping}
      />
      {showAdminDashboard && currentUser.role === 'admin' && (
        <AdminDashboard
          currentUser={currentUser}
          onClose={() => setShowAdminDashboard(false)}
        />
      )}
    </>
  );
}

export default App;
