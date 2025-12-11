import { useState, useEffect } from 'react';

interface Group {
  id: string;
  name: string;
  description?: string;
  avatar?: string;
  updated_at: number;
  role: string;
}

interface GroupListProps {
  currentUserId: string;
  onSelectGroup: (group: Group) => void;
  selectedGroupId?: string;
  onCreateGroup: () => void;
}

export default function GroupList({ currentUserId, onSelectGroup, selectedGroupId, onCreateGroup }: GroupListProps) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGroups();
  }, [currentUserId]);

  const fetchGroups = async () => {
    try {
      const response = await fetch('/api/groups', {
        headers: {
          'Authorization': `Bearer ${currentUserId}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setGroups(data as Group[]);
      }
    } catch (error) {
      console.error('Failed to fetch groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  if (loading) {
    return <div className="group-list">Loading groups...</div>;
  }

  return (
    <div className="group-list">
      <div className="group-list-header">
        <h3>Groups</h3>
        <button onClick={onCreateGroup} className="create-group-btn" title="Create new group">
          +
        </button>
      </div>

      <div className="group-items">
        {groups.length === 0 ? (
          <div className="no-groups">
            <p>No groups yet</p>
            <button onClick={onCreateGroup} className="btn-primary">Create a Group</button>
          </div>
        ) : (
          groups.map((group) => (
            <div
              key={group.id}
              className={`group-item ${selectedGroupId === group.id ? 'active' : ''}`}
              onClick={() => onSelectGroup(group)}
            >
              <div className="group-avatar">
                {group.avatar ? (
                  <img src={group.avatar} alt={group.name} />
                ) : (
                  <div className="group-avatar-placeholder">
                    {group.name.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              <div className="group-info">
                <div className="group-name">{group.name}</div>
                {group.description && (
                  <div className="group-description">{group.description}</div>
                )}
                <div className="group-role">{group.role}</div>
              </div>
              <div className="group-time">{formatTime(group.updated_at)}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
