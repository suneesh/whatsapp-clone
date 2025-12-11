import { useState, useEffect, useCallback } from 'react';
import Login from './components/Login';
import Chat from './components/Chat';
import { useWebSocket } from './hooks/useWebSocket';

interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
}

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
}

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());

  // Restore user from localStorage on app mount
  useEffect(() => {
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
        const updated = [...prev];
        statusUpdates.forEach((update) => {
          const index = updated.findIndex((u) => u.id === update.userId);
          if (index !== -1) {
            updated[index] = { ...updated[index], online: update.online };
          } else if (update.online && update.userId !== currentUser?.id) {
            updated.push({
              id: update.userId,
              username: update.username,
              online: true,
            });
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

  // WebSocket connection - always call the hook
  const websocketEnabled = currentUser !== null;
  const { connected, sendMessage, sendTyping, sendStatus, sendReadReceipt } = useWebSocket({
    userId: currentUser?.id || '',
    username: currentUser?.username || '',
    onMessage: handleMessage,
    onTyping: handleTyping,
    onOnlineStatus: handleOnlineStatus,
    onReadReceipt: handleReadReceipt,
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
      fetchUsers();
    }
  }, [currentUser]);

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users');
      const data = await response.json();
      setUsers(data.filter((u: User) => u.id !== currentUser?.id));
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const handleLogin = async (username: string, password: string) => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentUser(data);
        // Save user to localStorage
        localStorage.setItem('user', JSON.stringify(data));
        console.log('[App] User logged in and saved to localStorage');
      } else {
        console.error('Login failed:', data.error);
        throw new Error(data.error || 'Login failed');
      }
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const handleRegister = async (username: string, password: string) => {
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentUser(data);
        // Save user to localStorage
        localStorage.setItem('user', JSON.stringify(data));
        console.log('[App] User registered and saved to localStorage');
      } else {
        console.error('Registration failed:', data.error);
        throw new Error(data.error || 'Registration failed');
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
    // Clear localStorage
    localStorage.removeItem('user');
    console.log('[App] User logged out');
  };

  if (!currentUser) {
    return <Login onLogin={handleLogin} onRegister={handleRegister} />;
  }

  return (
    <Chat
      currentUser={currentUser}
      users={users}
      messages={messages}
      typingUsers={typingUsers}
      connected={connected}
      onSendMessage={sendMessage}
      onTyping={sendTyping}
      onMarkAsRead={handleMarkAsRead}
      onLogout={handleLogout}
    />
  );
}

export default App;
