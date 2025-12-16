import { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import FingerprintModal from './FingerprintModal';
import { SessionViewState } from '../hooks/useE2EE';

interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
  can_send_images?: number;
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

interface ChatWindowProps {
  currentUser: User;
  selectedUser: User | null;
  messages: Message[];
  typingUsers: Set<string>;
  connected: boolean;
  e2eeReady: boolean;
  e2eeInitializing: boolean;
  e2eeError: string | null;
  sessionState?: SessionViewState;
  currentUserFingerprint?: string;
  onEnsureSession: (peerId: string) => Promise<void>;
  onSendMessage: (to: string, content: string) => void;
  onSendImage: (to: string, imageData: string) => void;
  onTyping: (to: string, typing: boolean) => void;
  onMarkAsRead: (toUserId: string, messageIds: string[]) => void;
}

function ChatWindow({
  currentUser,
  selectedUser,
  messages,
  typingUsers,
  connected,
  e2eeReady,
  e2eeInitializing,
  e2eeError,
  sessionState,
  currentUserFingerprint,
  onEnsureSession,
  onSendMessage,
  onSendImage,
  onTyping,
  onMarkAsRead,
}: ChatWindowProps) {
  const [inputValue, setInputValue] = useState('');
  const [showFingerprintModal, setShowFingerprintModal] = useState(false);
  const typingTimeoutRef = useRef<number>();

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  const handleInputChange = (value: string) => {
    setInputValue(value);

    if (selectedUser) {
      onTyping(selectedUser.id, value.length > 0);

      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      typingTimeoutRef.current = window.setTimeout(() => {
        onTyping(selectedUser.id, false);
      }, 1000);
    }
  };

  const handleSend = () => {
    if (!selectedUser) {
      return;
    }
    const sessionReady = sessionState?.status === 'ready';
    if (!sessionReady || !e2eeReady) {
      return;
    }
    if (inputValue.trim()) {
      onSendMessage(selectedUser.id, inputValue.trim());
      setInputValue('');
      onTyping(selectedUser.id, false);
    }
  };

  const handleSendImage = (imageData: string) => {
    if (selectedUser && sessionState?.status === 'ready' && e2eeReady) {
      onSendImage(selectedUser.id, imageData);
    }
  };

  const handleRetrySession = () => {
    if (!selectedUser) {
      return;
    }
    onEnsureSession(selectedUser.id).catch((err) => {
      console.warn('[ChatWindow] Session retry failed', err);
    });
  };

  if (!selectedUser) {
    return (
      <div className="chat-container">
        <div className="empty-chat">Select a user to start chatting</div>
      </div>
    );
  }

  const chatMessages = messages.filter(
    (m) =>
      (m.from === currentUser.id && m.to === selectedUser.id) ||
      (m.from === selectedUser.id && m.to === currentUser.id)
  );

  const isTyping = typingUsers.has(selectedUser.id);
  const sessionStatus = sessionState?.status || 'idle';
  const sessionError = sessionState?.error || e2eeError;
  const sessionReady = sessionStatus === 'ready';
  const sessionEstablishing = sessionStatus === 'establishing';
  const inputDisabled = !connected || !sessionReady || !e2eeReady;

  const renderSessionBanner = () => {
    if (e2eeError) {
      return (
        <div className="session-status-banner danger">
          <span>{e2eeError}</span>
          <button type="button" onClick={() => window.location.reload()} className="session-retry-btn">
            Reload
          </button>
        </div>
      );
    }

    if (e2eeInitializing || !e2eeReady) {
      return (
        <div className="session-status-banner warning">
          <span>Generating secure identity…</span>
        </div>
      );
    }

    if (sessionEstablishing) {
      return (
        <div className="session-status-banner info">
          <span>Establishing secure session…</span>
        </div>
      );
    }
    if (sessionStatus === 'error') {
      return (
        <div className="session-status-banner danger">
          <span>{sessionError || 'Secure session failed'}</span>
          <button type="button" onClick={handleRetrySession} className="session-retry-btn">
            Retry
          </button>
        </div>
      );
    }
    if (!sessionReady) {
      return (
        <div className="session-status-banner warning">
          <span>Secure session required before sending messages.</span>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="user-avatar">{selectedUser.username.charAt(0).toUpperCase()}</div>
        <div className="user-details">
          <div className="user-name">
            {selectedUser.username}
            {sessionReady && sessionState?.fingerprint && (
              <span className="verified-badge-inline" title="Encrypted">🔒</span>
            )}
          </div>
          <div className={`user-status ${selectedUser.online ? 'online' : ''}`}>
            {selectedUser.online ? 'online' : 'offline'}
          </div>
        </div>
        {sessionReady && sessionState?.fingerprint && (
          <button
            className="fingerprint-btn"
            onClick={() => setShowFingerprintModal(true)}
            title="Verify encryption"
          >
            🔑 Verify
          </button>
        )}
      </div>

      <MessageList
        messages={chatMessages}
        currentUserId={currentUser.id}
        selectedUserId={selectedUser.id}
        isTyping={isTyping}
        typingUsername={selectedUser.username}
        onMarkAsRead={(messageIds) => onMarkAsRead(selectedUser.id, messageIds)}
      />

      {renderSessionBanner()}

      <MessageInput
        value={inputValue}
        onChange={handleInputChange}
        onSend={handleSend}
        onSendImage={handleSendImage}
        disabled={inputDisabled}
        canSendImages={currentUser.can_send_images !== 0}
      />

      {showFingerprintModal && currentUserFingerprint && sessionState?.fingerprint && (
        <FingerprintModal
          currentUserId={currentUser.id}
          currentUserFingerprint={currentUserFingerprint}
          otherUserId={selectedUser.id}
          otherUserFingerprint={sessionState.fingerprint}
          otherUsername={selectedUser.username}
          onClose={() => setShowFingerprintModal(false)}
        />
      )}
    </div>
  );
}

export default ChatWindow;
