import { useEffect, useRef } from 'react';

interface GroupMessage {
  id: string;
  group_id: string;
  from_user: string;
  from_username: string;
  content: string;
  timestamp: number;
  type: 'text' | 'image' | 'system';
  imageData?: string;
  system_event?: string;
}

interface GroupMember {
  user_id: string;
  username: string;
  role: string;
}

interface GroupMessageListProps {
  messages: GroupMessage[];
  currentUserId: string;
  members: GroupMember[];
  typingUsers: Set<string>;
}

export default function GroupMessageList({
  messages,
  currentUserId,
  members,
  typingUsers,
}: GroupMessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getMemberRole = (userId: string) => {
    return members.find(m => m.user_id === userId)?.role || 'member';
  };

  const renderMessage = (message: GroupMessage) => {
    const isOwnMessage = message.from_user === currentUserId;
    const role = getMemberRole(message.from_user);

    if (message.type === 'system') {
      return (
        <div key={message.id} className="system-message">
          <span>{message.content}</span>
          <span className="message-time">{formatTime(message.timestamp)}</span>
        </div>
      );
    }

    return (
      <div
        key={message.id}
        className={`group-message ${isOwnMessage ? 'own-message' : 'other-message'}`}
      >
        {!isOwnMessage && (
          <div className="message-sender">
            <span className="sender-name">{message.from_username}</span>
            {role !== 'member' && (
              <span className={`sender-role role-${role}`}>{role}</span>
            )}
          </div>
        )}
        <div className="message-content">
          {message.type === 'image' && message.imageData ? (
            <img
              src={message.imageData}
              alt="Shared image"
              className="message-image"
            />
          ) : (
            <p>{message.content}</p>
          )}
        </div>
        <span className="message-time">{formatTime(message.timestamp)}</span>
      </div>
    );
  };

  const typingUsersList = Array.from(typingUsers)
    .filter(userId => userId !== currentUserId)
    .map(userId => members.find(m => m.user_id === userId)?.username)
    .filter(Boolean);

  return (
    <div className="group-message-list">
      {messages.length === 0 ? (
        <div className="no-messages">
          <p>No messages yet. Start the conversation!</p>
        </div>
      ) : (
        messages.map(renderMessage)
      )}

      {typingUsersList.length > 0 && (
        <div className="typing-indicator">
          {typingUsersList.length === 1
            ? `${typingUsersList[0]} is typing...`
            : `${typingUsersList.length} people are typing...`}
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
