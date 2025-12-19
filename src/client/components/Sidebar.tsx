interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
  role?: string;
}

interface SidebarProps {
  currentUser: User;
  users: User[];
  selectedUser: User | null;
  onSelectUser: (user: User) => void;
  onLogout: () => void;
  onResetE2EE?: () => void;
  onOpenAdmin?: () => void;
  unreadCounts?: Map<string, number>;
  fingerprint?: string;
}

function formatFingerprint(value: string): string {
  return value
    .replace(/\s+/g, '')
    .match(/.{1,4}/g)
    ?.join(' ')
    .trim() ?? value;
}

function Sidebar({ currentUser, users, selectedUser, onSelectUser, onLogout, onResetE2EE, onOpenAdmin, unreadCounts, fingerprint }: SidebarProps) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div>
          <h2>Chats</h2>
          <div className="user-info">{currentUser.username}</div>
          {fingerprint && (
            <div className="fingerprint-block">
              <div className="fingerprint-label">Fingerprint</div>
              <code className="fingerprint-value">{formatFingerprint(fingerprint)}</code>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {currentUser.role === 'admin' && onOpenAdmin && (
            <button className="admin-panel-btn" onClick={onOpenAdmin}>
              👑 Admin
            </button>
          )}
          {onResetE2EE && (
            <button 
              className="reset-e2ee-btn" 
              onClick={onResetE2EE}
              title="Reset encryption data"
              style={{
                padding: '6px 10px',
                fontSize: '11px',
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              🔄 Reset E2EE
            </button>
          )}
          <button className="logout-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>
      <div className="user-list">
        {users.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#8696a0' }}>
            No users online
          </div>
        ) : (
          users.map((user) => {
            const unreadCount = unreadCounts?.get(user.id) || 0;
            return (
              <div
                key={user.id}
                className={`user-item ${selectedUser?.id === user.id ? 'active' : ''}`}
                onClick={() => onSelectUser(user)}
              >
                <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
                <div className="user-details">
                  <div className="user-name">{user.username}</div>
                  <div className={`user-status ${user.online ? 'online' : ''}`}>
                    {user.online ? 'online' : 'offline'}
                  </div>
                </div>
                {unreadCount > 0 && (
                  <div className="unread-badge">{unreadCount}</div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default Sidebar;
