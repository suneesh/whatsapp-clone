import { useState, useEffect, useCallback } from 'react';
import Login from './components/Login';
import Chat from './components/Chat';
import AdminDashboard from './components/AdminDashboard';
import { useWebSocket } from './hooks/useWebSocket';
import { useE2EE } from './hooks/useE2EE';
import { apiFetch } from './utils/api';

interface User {
  id: string;
  username: string;
  token?: string;
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
  encrypted?: boolean;
}

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [groupMessages, setGroupMessages] = useState<any[]>([]);
  const [groupTypingUsers, setGroupTypingUsers] = useState<Map<string, Set<string>>>(new Map());
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);
  const {
    ready: e2eeReady,
    initializing: e2eeInitializing,
    fingerprint: currentUserFingerprint,
    error: e2eeError,
    ensureSession,
    sessions: sessionStates,
    encryptMessage,
    decryptMessage,
    resetE2EE,
  } = useE2EE(currentUser?.id, currentUser?.token);

  // Restore user from localStorage on app mount
  useEffect(() => {
    // Clear users list on mount - only show users who connect via WebSocket
    setUsers([]);

    try {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const user = JSON.parse(storedUser);

        // Validate user object structure
        if (
          user &&
          typeof user === 'object' &&
          typeof user.id === 'string' &&
          typeof user.username === 'string' &&
          user.id.length > 0 &&
          user.username.length > 0 &&
          // Prevent XSS in username
          !/[<>]/.test(user.username)
        ) {
          // Sanitize the user object - only keep safe fields
          const sanitizedUser: User = {
            id: user.id,
            username: user.username,
            token: typeof user.token === 'string' ? user.token : undefined,
            avatar: typeof user.avatar === 'string' ? user.avatar : undefined,
            role: typeof user.role === 'string' ? user.role : undefined,
            is_active: typeof user.is_active === 'number' ? user.is_active : undefined,
            can_send_images: typeof user.can_send_images === 'number' ? user.can_send_images : undefined,
            created_at: typeof user.created_at === 'number' ? user.created_at : undefined,
            disabled_at: typeof user.disabled_at === 'number' ? user.disabled_at : undefined,
            disabled_by: typeof user.disabled_by === 'string' ? user.disabled_by : undefined,
            lastSeen: typeof user.lastSeen === 'number' ? user.lastSeen : undefined,
          };

          setCurrentUser(sanitizedUser);
          console.log('[App] Restored user from localStorage:', sanitizedUser.username);
        } else {
          console.warn('[App] Invalid user data in localStorage, clearing');
          localStorage.removeItem('user');
        }
      }
    } catch (error) {
      console.error('Failed to restore user from localStorage:', error);
      localStorage.removeItem('user');
    }
  }, []);

  const handleMessage = useCallback(async (message: Message) => {
    console.log('[App] Received message:', { id: message.id, from: message.from, encrypted: message.encrypted, contentPreview: message.content.substring(0, 50) });
    
    // Skip decryption for own messages - we already have the plaintext
    if (message.from === currentUser?.id) {
      // For own messages, check if we already have it (with plaintext)
      setMessages((prev) => {
        const exists = prev.find((m) => m.id === message.id);
        if (exists) {
          // Keep the existing message (which has plaintext), just update status
          return prev.map((m) => (m.id === message.id ? { ...m, status: message.status } : m));
        }
        // If somehow we don't have it, add it (but this shouldn't happen)
        return [...prev, message];
      });
      return;
    }
    
    // Decrypt if encrypted (check server-validated encrypted flag)
    let decryptedMessage = message;
    if (message.encrypted && message.type === 'text') {
      try {
        console.log('[App] Message is encrypted, attempting decryption');
        console.log('[App] Encrypted content:', message.content.substring(0, 100));
        // Content should be JSON with encrypted data
        const encryptedData = JSON.parse(message.content);
        console.log('[App] Parsed encrypted data, calling decryptMessage');
        const plaintext = await decryptMessage(message.from, encryptedData);
        console.log('[App] Plaintext result:', plaintext);
        decryptedMessage = {
          ...message,
          content: plaintext,
        };
        console.log('[App] Message decrypted successfully');
      } catch (err) {
        console.error('[E2EE] Failed to decrypt message:', err);
        console.error('[E2EE] Error stack:', err instanceof Error ? err.stack : 'No stack');
        decryptedMessage = {
          ...message,
          content: '🔒 [Decryption failed] - Check console for details',
        };
      }
    } else if (!message.encrypted) {
      console.log('[App] Message is not encrypted');
    }

    setMessages((prev) => {
      const exists = prev.find((m) => m.id === decryptedMessage.id);
      if (exists) {
        console.log('[App] Updating existing message:', decryptedMessage.id);
        return prev.map((m) => (m.id === decryptedMessage.id ? decryptedMessage : m));
      }
      console.log('[App] Adding new message:', decryptedMessage.id);
      return [...prev, decryptedMessage];
    });
  }, [currentUser?.id, decryptMessage]);

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

  const handleResetE2EE = useCallback(async () => {
    if (!resetE2EE) return;
    
    const confirmed = window.confirm(
      'Are you sure you want to reset encryption data? This will:\n\n' +
      '• Delete all encryption keys and sessions\n' +
      '• Generate new encryption identity\n' +
      '• Require re-establishing sessions with all contacts\n\n' +
      'This action cannot be undone.'
    );
    
    if (!confirmed) return;
    
    try {
      await resetE2EE();
      alert('Encryption data has been reset successfully. You can now send encrypted messages with a fresh identity.');
    } catch (err) {
      console.error('[App] Failed to reset E2EE:', err);
      alert('Failed to reset encryption data: ' + (err as Error).message);
    }
  }, [resetE2EE]);

  const handleSendGroupMessage = useCallback((groupId: string, content: string, type?: string) => {
    sendGroupMessage(groupId, content, type || 'text');
  }, [sendGroupMessage]);

  const handleSendGroupImage = useCallback((groupId: string, imageData: string) => {
    sendGroupMessage(groupId, '📷 Image', 'image', imageData);
  }, [sendGroupMessage]);

  const handleGroupTyping = useCallback((groupId: string, typing: boolean) => {
    sendGroupTyping(groupId, typing);
  }, [sendGroupTyping]);

  const handleSendMessage = useCallback(async (to: string, content: string) => {
    if (!e2eeReady) {
      console.warn('[E2EE] Not ready, sending unencrypted');
      sendMessage(to, content, false);
      return;
    }

    try {
      // Ensure session exists
      await ensureSession(to);

      // Create message object to display immediately to sender with plaintext
      const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).slice(2);
      const sentMessage: Message = {
        id: messageId,
        from: currentUser!.id,
        to,
        content, // Show plaintext to sender
        timestamp: Date.now(),
        status: 'sent',
        type: 'text',
      };

      // Add to messages immediately (before encryption/sending)
      setMessages((prev) => [...prev, sentMessage]);

      // Encrypt the message
      console.log('[E2EE] Encrypting message to', to);
      const encrypted = await encryptMessage(to, content);

      // Send encrypted message as JSON with encrypted flag
      const encryptedPayload = JSON.stringify(encrypted);
      sendMessage(to, encryptedPayload, true, messageId);
    } catch (err) {
      console.error('[E2EE] Encryption failed, sending unencrypted:', err);
      sendMessage(to, content, false);
    }
  }, [currentUser, e2eeReady, ensureSession, encryptMessage, sendMessage]);

  const handleSendImage = useCallback(async (to: string, imageData: string) => {
    // For now, images are not encrypted (placeholder for future implementation)
    sendImage(to, imageData);
  }, [sendImage]);

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
        currentUserFingerprint={currentUserFingerprint || undefined}
        e2eeReady={e2eeReady}
        e2eeInitializing={e2eeInitializing}
        e2eeError={e2eeError}
        sessionStates={sessionStates}
        onEnsureSession={ensureSession}
        onSendMessage={handleSendMessage}
        onSendImage={handleSendImage}
        onTyping={sendTyping}
        onMarkAsRead={handleMarkAsRead}
        onLogout={handleLogout}
        onResetE2EE={handleResetE2EE}
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
