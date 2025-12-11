import { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

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

interface ChatWindowProps {
  currentUser: User;
  selectedUser: User | null;
  messages: Message[];
  typingUsers: Set<string>;
  connected: boolean;
  onSendMessage: (to: string, content: string) => void;
  onTyping: (to: string, typing: boolean) => void;
  onMarkAsRead: (toUserId: string, messageIds: string[]) => void;
}

function ChatWindow({
  currentUser,
  selectedUser,
  messages,
  typingUsers,
  connected,
  onSendMessage,
  onTyping,
  onMarkAsRead,
}: ChatWindowProps) {
  const [inputValue, setInputValue] = useState('');
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
    if (inputValue.trim() && selectedUser) {
      onSendMessage(selectedUser.id, inputValue.trim());
      setInputValue('');
      onTyping(selectedUser.id, false);
    }
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

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="user-avatar">{selectedUser.username.charAt(0).toUpperCase()}</div>
        <div className="user-details">
          <div className="user-name">{selectedUser.username}</div>
          <div className={`user-status ${selectedUser.online ? 'online' : ''}`}>
            {selectedUser.online ? 'online' : 'offline'}
          </div>
        </div>
      </div>

      <MessageList
        messages={chatMessages}
        currentUserId={currentUser.id}
        selectedUserId={selectedUser.id}
        isTyping={isTyping}
        typingUsername={selectedUser.username}
        onMarkAsRead={(messageIds) => onMarkAsRead(selectedUser.id, messageIds)}
      />

      <MessageInput
        value={inputValue}
        onChange={handleInputChange}
        onSend={handleSend}
        disabled={!connected}
      />
    </div>
  );
}

export default ChatWindow;
