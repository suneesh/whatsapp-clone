import { useEffect, useRef } from 'react';

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
}

interface MessageListProps {
  messages: Message[];
  currentUserId: string;
  selectedUserId: string;
  isTyping: boolean;
  typingUsername: string;
  onMarkAsRead: (messageIds: string[]) => void;
}

function MessageList({
  messages,
  currentUserId,
  selectedUserId,
  isTyping,
  typingUsername,
  onMarkAsRead,
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Detect unread messages and mark as read after 500ms
  useEffect(() => {
    const unreadMessages = messages.filter(
      (m) =>
        m.from === selectedUserId &&
        m.to === currentUserId &&
        m.status !== 'read'
    );

    if (unreadMessages.length > 0) {
      console.log(`[MessageList] Found ${unreadMessages.length} unread messages`);
      const timer = setTimeout(() => {
        console.log(`[MessageList] Marking ${unreadMessages.length} messages as read`);
        onMarkAsRead(unreadMessages.map((m) => m.id));
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [messages, selectedUserId, currentUserId, onMarkAsRead]);

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
        return '✓';
      case 'delivered':
        return '✓✓';
      case 'read':
        return '✓✓';
      default:
        return '';
    }
  };

  return (
    <div className="messages-container">
      {messages.map((message) => {
        const isSent = message.from === currentUserId;
        return (
          <div key={message.id} className={`message ${isSent ? 'sent' : 'received'}`}>
            <div className="message-content">{message.content}</div>
            <div className="message-meta">
              <span>{formatTime(message.timestamp)}</span>
              {isSent && (
                <span className={`status-icon ${message.status}`}>
                  {getStatusIcon(message.status)}
                </span>
              )}
            </div>
          </div>
        );
      })}
      {isTyping && (
        <div className="typing-indicator">{typingUsername} is typing...</div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}

export default MessageList;
