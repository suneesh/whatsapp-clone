import { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';
import GroupChatWindow from './GroupChatWindow';
import GroupList from './GroupList';
import CreateGroupModal from './CreateGroupModal';
import { SessionViewState } from '../hooks/useE2EE';

interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
  role?: string;
  is_active?: number;
  can_send_images?: number;
  created_at?: number;
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

interface Group {
  id: string;
  name: string;
  description?: string;
  avatar?: string;
  updated_at: number;
  role: string;
}

interface ChatProps {
  currentUser: User;
  users: User[];
  messages: Message[];
  typingUsers: Set<string>;
  connected: boolean;
  currentUserFingerprint?: string;
  e2eeReady: boolean;
  e2eeInitializing: boolean;
  e2eeError: string | null;
  sessionStates: Record<string, SessionViewState>;
  onEnsureSession: (peerId: string) => Promise<void>;
  onSendMessage: (to: string, content: string) => void;
  onSendImage: (to: string, imageData: string) => void;
  onTyping: (to: string, typing: boolean) => void;
  onMarkAsRead: (toUserId: string, messageIds: string[]) => void;
  onLogout: () => void;
  onOpenAdmin?: () => void;
  // Group props
  groupMessages: any[];
  groupTypingUsers: Map<string, Set<string>>;
  onSendGroupMessage: (groupId: string, content: string, type?: string) => void;
  onSendGroupImage: (groupId: string, imageData: string) => void;
  onGroupTyping: (groupId: string, typing: boolean) => void;
}

function Chat({
  currentUser,
  users,
  messages,
  typingUsers,
  connected,
  e2eeReady,
  e2eeInitializing,
  e2eeError,
  sessionStates,
  onEnsureSession,
  onSendMessage,
  onSendImage,
  onTyping,
  onMarkAsRead,
  onLogout,
  onOpenAdmin,
  groupMessages,
  groupTypingUsers,
  currentUserFingerprint,
  onSendGroupMessage,
  onSendGroupImage,
  onGroupTyping,
}: ChatProps) {
  const [view, setView] = useState<'chats' | 'groups'>('chats');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<any | null>(null);
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [groupDetails, setGroupDetails] = useState<any>(null);
  const [groupMembers, setGroupMembers] = useState<any[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [sidebarVisible, setSidebarVisible] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!selectedUser || !e2eeReady) {
      return;
    }
    onEnsureSession(selectedUser.id).catch((err) => {
      if (!cancelled) {
        console.warn('[Chat] Failed to establish session', err);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedUser, e2eeReady, onEnsureSession]);

  // Fetch groups when component mounts or view changes to groups
  useEffect(() => {
    if (view === 'groups') {
      fetchGroups();
    }
  }, [view]);

  const fetchGroups = async () => {
    try {
      const response = await fetch('/api/groups', {
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setGroups(data as Group[]);
      }
    } catch (error) {
      console.error('Failed to fetch groups:', error);
    }
  };

  const handleSelectUser = (user: User) => {
    setSelectedUser(user);
    setSelectedGroup(null);
    setView('chats');
    // Hide sidebar on mobile when user is selected
    if (window.innerWidth <= 768) {
      setSidebarVisible(false);
    }
  };

  const handleSelectGroup = async (group: any) => {
    setSelectedGroup(group);
    setSelectedUser(null);
    setView('groups');
    // Hide sidebar on mobile when group is selected
    if (window.innerWidth <= 768) {
      setSidebarVisible(false);
    }

    // Fetch group details and members
    try {
      const [detailsRes, membersRes, messagesRes] = await Promise.all([
        fetch(`/api/groups/${group.id}`, {
          headers: { 'Authorization': `Bearer ${currentUser.id}` },
        }),
        fetch(`/api/groups/${group.id}/members`, {
          headers: { 'Authorization': `Bearer ${currentUser.id}` },
        }),
        fetch(`/api/groups/${group.id}/messages`, {
          headers: { 'Authorization': `Bearer ${currentUser.id}` },
        }),
      ]);

      if (detailsRes.ok && membersRes.ok) {
        const details = await detailsRes.json();
        const members = await membersRes.json();
        setGroupDetails(details);
        setGroupMembers(members);
      }
    } catch (error) {
      console.error('Failed to fetch group data:', error);
    }
  };

  const handleCreateGroup = async (name: string, description: string, memberIds: string[], avatar?: string) => {
    try {
      const response = await fetch('/api/groups', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, description, avatar, memberIds }),
      });

      if (response.ok) {
        const newGroup = await response.json();
        setShowCreateGroup(false);
        // Refresh groups list
        await fetchGroups();
        // Refresh groups list by selecting the new group
        handleSelectGroup({ ...newGroup, role: 'owner', updated_at: newGroup.created_at } as Group);
      } else {
        const error = await response.json();
        alert(error.error || 'Failed to create group');
      }
    } catch (error) {
      console.error('Failed to create group:', error);
      alert('Failed to create group');
    }
  };

  const handleUpdateGroup = async (updates: any) => {
    if (!selectedGroup) return;

    try {
      const response = await fetch(`/api/groups/${selectedGroup.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        // Refresh group details
        handleSelectGroup(selectedGroup);
      }
    } catch (error) {
      console.error('Failed to update group:', error);
    }
  };

  const handleAddMembers = async (userIds: string[]) => {
    if (!selectedGroup) return;

    try {
      const response = await fetch(`/api/groups/${selectedGroup.id}/members`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ userIds }),
      });

      if (response.ok) {
        // Refresh members
        handleSelectGroup(selectedGroup);
      }
    } catch (error) {
      console.error('Failed to add members:', error);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedGroup) return;

    try {
      const response = await fetch(`/api/groups/${selectedGroup.id}/members/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
        },
      });

      if (response.ok) {
        // Refresh members
        handleSelectGroup(selectedGroup);
      }
    } catch (error) {
      console.error('Failed to remove member:', error);
    }
  };

  const handleLeaveGroup = async () => {
    if (!selectedGroup) return;

    try {
      const response = await fetch(`/api/groups/${selectedGroup.id}/leave`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
        },
      });

      if (response.ok) {
        setSelectedGroup(null);
        setGroupDetails(null);
        setGroupMembers([]);
      }
    } catch (error) {
      console.error('Failed to leave group:', error);
    }
  };

  const handleUpdateMemberRole = async (userId: string, role: string) => {
    if (!selectedGroup) return;

    try {
      const response = await fetch(`/api/groups/${selectedGroup.id}/members/${userId}/role`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role }),
      });

      if (response.ok) {
        // Refresh members
        handleSelectGroup(selectedGroup);
      }
    } catch (error) {
      console.error('Failed to update member role:', error);
    }
  };

  const filteredGroupMessages = selectedGroup
    ? groupMessages.filter(m => m.group_id === selectedGroup.id)
    : [];

  const currentGroupTypingUsers = selectedGroup
    ? groupTypingUsers.get(selectedGroup.id) || new Set()
    : new Set();

  // Calculate unread message counts for each user
  const unreadCounts = new Map<string, number>();
  users.forEach(user => {
    const count = messages.filter(m => 
      m.from === user.id && 
      m.to === currentUser.id && 
      m.status !== 'read'
    ).length;
    if (count > 0) {
      unreadCounts.set(user.id, count);
    }
  });

  // Calculate unread message counts for each group
  const groupUnreadCounts = new Map<string, number>();
  groups.forEach(group => {
    const count = groupMessages.filter(m => 
      m.group_id === group.id && 
      m.from_user !== currentUser.id &&
      // Check if current user hasn't read this message
      !m.read_by?.includes(currentUser.id)
    ).length;
    if (count > 0) {
      groupUnreadCounts.set(group.id, count);
    }
  });

  return (
    <div className="app">
      {/* Mobile sidebar toggle button */}
      {!sidebarVisible && (
        <button 
          className="mobile-sidebar-toggle"
          onClick={() => setSidebarVisible(true)}
          aria-label="Show sidebar"
        >
          ☰
        </button>
      )}

      <div className={`app-sidebar-container ${sidebarVisible ? 'visible' : 'hidden'}`}>
        {/* Close button for mobile */}
        <button 
          className="mobile-sidebar-close"
          onClick={() => setSidebarVisible(false)}
          aria-label="Hide sidebar"
        >
          ✕
        </button>

        <div className="view-toggle">
          <button
            className={`view-toggle-btn ${view === 'chats' ? 'active' : ''}`}
            onClick={() => setView('chats')}
          >
            Chats
          </button>
          <button
            className={`view-toggle-btn ${view === 'groups' ? 'active' : ''}`}
            onClick={() => setView('groups')}
          >
            Groups
          </button>
        </div>

        {view === 'chats' ? (
          <Sidebar
            currentUser={currentUser}
            users={users}
            selectedUser={selectedUser}
            onSelectUser={handleSelectUser}
            onLogout={onLogout}
            onOpenAdmin={onOpenAdmin}
            unreadCounts={unreadCounts}
            fingerprint={currentUserFingerprint}
          />
        ) : (
          <GroupList
            currentUserId={currentUser.id}
            onSelectGroup={handleSelectGroup}
            selectedGroupId={selectedGroup?.id}
            onCreateGroup={() => setShowCreateGroup(true)}
            groups={groups}
            unreadCounts={groupUnreadCounts}
          />
        )}
      </div>

      {view === 'chats' ? (
        <ChatWindow
          currentUser={currentUser}
          selectedUser={selectedUser}
          messages={messages}
          typingUsers={typingUsers}
          connected={connected}
          e2eeReady={e2eeReady}
          e2eeInitializing={e2eeInitializing}
          e2eeError={e2eeError}
          sessionState={selectedUser ? sessionStates[selectedUser.id] : undefined}
          onEnsureSession={onEnsureSession}
          onSendMessage={onSendMessage}
          onSendImage={onSendImage}
          onTyping={onTyping}
          onMarkAsRead={onMarkAsRead}
        />
      ) : (
        selectedGroup && groupDetails ? (
          <GroupChatWindow
            group={groupDetails}
            currentUser={currentUser}
            messages={filteredGroupMessages}
            members={groupMembers}
            typingUsers={currentGroupTypingUsers}
            onSendMessage={(content, type) => onSendGroupMessage(selectedGroup.id, content, type)}
            onSendImage={(imageData) => onSendGroupImage(selectedGroup.id, imageData)}
            onTyping={(typing) => onGroupTyping(selectedGroup.id, typing)}
            onUpdateGroup={handleUpdateGroup}
            onAddMembers={handleAddMembers}
            onRemoveMember={handleRemoveMember}
            onLeaveGroup={handleLeaveGroup}
            onUpdateMemberRole={handleUpdateMemberRole}
          />
        ) : (
          <div className="no-selection">
            <p>Select a group to start messaging</p>
          </div>
        )
      )}

      {showCreateGroup && (
        <CreateGroupModal
          onClose={() => setShowCreateGroup(false)}
          onCreate={handleCreateGroup}
          availableUsers={users}
          currentUserId={currentUser.id}
        />
      )}
    </div>
  );
}

export default Chat;
