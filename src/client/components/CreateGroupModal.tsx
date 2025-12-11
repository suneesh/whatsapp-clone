import { useState } from 'react';

interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
}

interface CreateGroupModalProps {
  onClose: () => void;
  onCreate: (name: string, description: string, memberIds: string[], avatar?: string) => void;
  availableUsers: User[];
  currentUserId: string;
}

export default function CreateGroupModal({ onClose, onCreate, availableUsers, currentUserId }: CreateGroupModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [avatar, setAvatar] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Group name is required');
      return;
    }

    if (selectedMembers.length === 0) {
      setError('Select at least one member');
      return;
    }

    onCreate(name.trim(), description.trim(), selectedMembers, avatar || undefined);
  };

  const toggleMember = (userId: string) => {
    setSelectedMembers(prev => 
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be less than 5MB');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result as string;
      setAvatar(result);
      setError('');
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Group</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <form onSubmit={handleSubmit} className="create-group-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="group-name">Group Name *</label>
            <input
              id="group-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter group name"
              maxLength={50}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="group-description">Description</label>
            <textarea
              id="group-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional group description"
              rows={3}
              maxLength={200}
            />
          </div>

          <div className="form-group">
            <label htmlFor="group-avatar">Group Avatar</label>
            <div className="avatar-upload">
              {avatar && (
                <div className="avatar-preview">
                  <img src={avatar} alt="Group avatar" />
                </div>
              )}
              <input
                id="group-avatar"
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
              />
            </div>
          </div>

          <div className="form-group">
            <label>Select Members *</label>
            <div className="member-selection">
              {availableUsers
                .filter(user => user.id !== currentUserId)
                .map(user => (
                  <div
                    key={user.id}
                    className={`member-item ${selectedMembers.includes(user.id) ? 'selected' : ''}`}
                    onClick={() => toggleMember(user.id)}
                  >
                    <input
                      type="checkbox"
                      checked={selectedMembers.includes(user.id)}
                      onChange={() => toggleMember(user.id)}
                    />
                    <span className="member-username">{user.username}</span>
                    {user.online && <span className="online-indicator">●</span>}
                  </div>
                ))}
              {availableUsers.filter(u => u.id !== currentUserId).length === 0 && (
                <div className="no-users">No users available</div>
              )}
            </div>
            <div className="selected-count">
              {selectedMembers.length} member(s) selected
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Create Group
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
