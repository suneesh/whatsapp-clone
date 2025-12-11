import { useState, useEffect } from 'react';
import GroupMessageList from './GroupMessageList';
import GroupMessageInput from './GroupMessageInput';
import GroupInfoPanel from './GroupInfoPanel';

interface Group {
  id: string;
  name: string;
  description?: string;
  avatar?: string;
  owner_id: string;
  settings: any;
  userRole: string;
}

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
  avatar?: string;
  joined_at: number;
}

interface GroupChatWindowProps {
  group: Group;
  currentUserId: string;
  messages: GroupMessage[];
  members: GroupMember[];
  typingUsers: Set<string>;
  onSendMessage: (content: string, type?: string) => void;
  onSendImage: (imageData: string) => void;
  onTyping: (typing: boolean) => void;
  onUpdateGroup: (updates: any) => void;
  onAddMembers: (userIds: string[]) => void;
  onRemoveMember: (userId: string) => void;
  onLeaveGroup: () => void;
  onUpdateMemberRole: (userId: string, role: string) => void;
}

export default function GroupChatWindow({
  group,
  currentUserId,
  messages,
  members,
  typingUsers,
  onSendMessage,
  onSendImage,
  onTyping,
  onUpdateGroup,
  onAddMembers,
  onRemoveMember,
  onLeaveGroup,
  onUpdateMemberRole,
}: GroupChatWindowProps) {
  const [showInfo, setShowInfo] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const currentMember = members.find(m => m.user_id === currentUserId);
  const isAdmin = currentMember?.role === 'admin' || currentMember?.role === 'owner';
  const isOwner = currentMember?.role === 'owner';

  // Check if user can send messages
  const canSendMessages = 
    group.settings?.messagePermission === 'everyone' || isAdmin;

  const handleSendMessage = (content: string) => {
    if (canSendMessages) {
      onSendMessage(content, 'text');
    }
  };

  const handleSendImage = (imageData: string) => {
    if (canSendMessages) {
      onSendImage(imageData);
    }
  };

  return (
    <div className="group-chat-window">
      <div className="group-chat-header">
        <div className="group-header-info">
          {group.avatar ? (
            <img src={group.avatar} alt={group.name} className="group-header-avatar" />
          ) : (
            <div className="group-header-avatar-placeholder">
              {group.name.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="group-header-details">
            <h2>{group.name}</h2>
            <p>{members.length} member{members.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="group-info-toggle"
          title="Group info"
        >
          ℹ️
        </button>
      </div>

      <div className="group-chat-body">
        <div className={`group-chat-messages ${showInfo ? 'with-info-panel' : ''}`}>
          <GroupMessageList
            messages={messages}
            currentUserId={currentUserId}
            members={members}
            typingUsers={typingUsers}
          />
          <GroupMessageInput
            onSendMessage={handleSendMessage}
            onSendImage={handleSendImage}
            onTyping={onTyping}
            disabled={!canSendMessages}
            disabledMessage={
              !canSendMessages
                ? 'Only admins can send messages in this group'
                : undefined
            }
          />
        </div>

        {showInfo && (
          <GroupInfoPanel
            group={group}
            members={members}
            currentUserId={currentUserId}
            isAdmin={isAdmin}
            isOwner={isOwner}
            onClose={() => setShowInfo(false)}
            onUpdateGroup={onUpdateGroup}
            onAddMembers={onAddMembers}
            onRemoveMember={onRemoveMember}
            onLeaveGroup={onLeaveGroup}
            onUpdateMemberRole={onUpdateMemberRole}
          />
        )}
      </div>
    </div>
  );
}
