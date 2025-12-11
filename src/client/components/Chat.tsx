import { useState } from 'react';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';

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

interface ChatProps {
  currentUser: User;
  users: User[];
  messages: Message[];
  typingUsers: Set<string>;
  connected: boolean;
  onSendMessage: (to: string, content: string) => void;
  onTyping: (to: string, typing: boolean) => void;
  onMarkAsRead: (toUserId: string, messageIds: string[]) => void;
  onLogout: () => void;
}

function Chat({
  currentUser,
  users,
  messages,
  typingUsers,
  connected,
  onSendMessage,
  onTyping,
  onMarkAsRead,
  onLogout,
}: ChatProps) {
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  return (
    <div className="app">
      <Sidebar
        currentUser={currentUser}
        users={users}
        selectedUser={selectedUser}
        onSelectUser={setSelectedUser}
        onLogout={onLogout}
      />
      <ChatWindow
        currentUser={currentUser}
        selectedUser={selectedUser}
        messages={messages}
        typingUsers={typingUsers}
        connected={connected}
        onSendMessage={onSendMessage}
        onTyping={onTyping}
        onMarkAsRead={onMarkAsRead}
      />
    </div>
  );
}

export default Chat;
