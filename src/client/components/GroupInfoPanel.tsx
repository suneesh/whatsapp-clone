import { useState } from 'react';

interface Group {
  id: string;
  name: string;
  description?: string;
  avatar?: string;
  owner_id: string;
  settings: any;
}

interface GroupMember {
  user_id: string;
  username: string;
  role: string;
  avatar?: string;
  joined_at: number;
}

interface GroupInfoPanelProps {
  group: Group;
  members: GroupMember[];
  currentUserId: string;
  isAdmin: boolean;
  isOwner: boolean;
  onClose: () => void;
  onUpdateGroup: (updates: any) => void;
  onAddMembers: (userIds: string[]) => void;
  onRemoveMember: (userId: string) => void;
  onLeaveGroup: () => void;
  onUpdateMemberRole: (userId: string, role: string) => void;
}

export default function GroupInfoPanel({
  group,
  members,
  currentUserId,
  isAdmin,
  isOwner,
  onClose,
  onUpdateGroup,
  onAddMembers,
  onRemoveMember,
  onLeaveGroup,
  onUpdateMemberRole,
}: GroupInfoPanelProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(group.name);
  const [description, setDescription] = useState(group.description || '');
  const [showInviteLink, setShowInviteLink] = useState(false);
  const [inviteLink, setInviteLink] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  const canEditMetadata = 
    group.settings?.metadataPermission === 'everyone' || isAdmin;

  const handleSaveChanges = () => {
    onUpdateGroup({ name, description });
    setEditing(false);
  };

  const handleGenerateInviteLink = async () => {
    try {
      const response = await fetch(`/api/groups/${group.id}/invite`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentUserId}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          expiresIn: 7 * 24 * 60 * 60 * 1000, // 7 days
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const link = `${window.location.origin}/join/${data.link_code}`;
        setInviteLink(link);
        setShowInviteLink(true);
      }
    } catch (error) {
      console.error('Failed to generate invite link:', error);
    }
  };

  const copyInviteLink = () => {
    navigator.clipboard.writeText(inviteLink);
    alert('Invite link copied!');
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="group-info-panel">
      <div className="group-info-header">
        <h3>Group Info</h3>
        <button onClick={onClose} className="close-btn">×</button>
      </div>

      <div className="group-info-content">
        {/* Group Details */}
        <div className="group-details-section">
          {group.avatar && (
            <img src={group.avatar} alt={group.name} className="group-info-avatar" />
          )}
          
          {editing && canEditMetadata ? (
            <div className="edit-group-form">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Group name"
                className="form-input"
              />
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Group description"
                className="form-textarea"
                rows={3}
              />
              <div className="form-actions">
                <button onClick={() => setEditing(false)} className="btn-secondary">
                  Cancel
                </button>
                <button onClick={handleSaveChanges} className="btn-primary">
                  Save
                </button>
              </div>
            </div>
          ) : (
            <>
              <h2>{group.name}</h2>
              {group.description && <p className="group-description">{group.description}</p>}
              {canEditMetadata && (
                <button onClick={() => setEditing(true)} className="btn-edit">
                  Edit
                </button>
              )}
            </>
          )}
        </div>

        {/* Members List */}
        <div className="group-members-section">
          <h4>{members.length} Member{members.length !== 1 ? 's' : ''}</h4>
          <div className="members-list">
            {members.map((member) => (
              <div key={member.user_id} className="member-item">
                <div className="member-info">
                  <span className="member-username">{member.username}</span>
                  <span className={`member-role role-${member.role}`}>
                    {member.role}
                  </span>
                </div>
                {isOwner && member.user_id !== currentUserId && member.role !== 'owner' && (
                  <div className="member-actions">
                    <select
                      value={member.role}
                      onChange={(e) => onUpdateMemberRole(member.user_id, e.target.value)}
                      className="role-select"
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                    </select>
                    <button
                      onClick={() => {
                        if (confirm(`Remove ${member.username} from group?`)) {
                          onRemoveMember(member.user_id);
                        }
                      }}
                      className="btn-remove"
                      title="Remove member"
                    >
                      Remove
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
          {isAdmin && (
            <button onClick={handleGenerateInviteLink} className="btn-invite">
              Generate Invite Link
            </button>
          )}
        </div>

        {/* Invite Link */}
        {showInviteLink && (
          <div className="invite-link-section">
            <h4>Invite Link</h4>
            <div className="invite-link-container">
              <input
                type="text"
                value={inviteLink}
                readOnly
                className="invite-link-input"
              />
              <button onClick={copyInviteLink} className="btn-copy">
                Copy
              </button>
            </div>
            <p className="invite-link-note">
              This link expires in 7 days
            </p>
          </div>
        )}

        {/* Settings */}
        {isAdmin && (
          <div className="group-settings-section">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="btn-settings"
            >
              {showSettings ? '▼' : '▶'} Group Settings
            </button>
            {showSettings && (
              <div className="settings-content">
                <div className="setting-item">
                  <label>Who can send messages</label>
                  <select
                    value={group.settings?.messagePermission || 'everyone'}
                    onChange={(e) =>
                      onUpdateGroup({
                        settings: {
                          ...group.settings,
                          messagePermission: e.target.value,
                        },
                      })
                    }
                    className="setting-select"
                  >
                    <option value="everyone">Everyone</option>
                    <option value="admins_only">Admins only</option>
                  </select>
                </div>
                <div className="setting-item">
                  <label>Who can edit group info</label>
                  <select
                    value={group.settings?.metadataPermission || 'admins_only'}
                    onChange={(e) =>
                      onUpdateGroup({
                        settings: {
                          ...group.settings,
                          metadataPermission: e.target.value,
                        },
                      })
                    }
                    className="setting-select"
                  >
                    <option value="everyone">Everyone</option>
                    <option value="admins_only">Admins only</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Leave Group */}
        <div className="group-actions-section">
          {!isOwner && (
            <button
              onClick={() => {
                if (confirm('Are you sure you want to leave this group?')) {
                  onLeaveGroup();
                }
              }}
              className="btn-leave"
            >
              Leave Group
            </button>
          )}
          {isOwner && (
            <p className="owner-note">
              As the group owner, you cannot leave. Transfer ownership or delete the group.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
