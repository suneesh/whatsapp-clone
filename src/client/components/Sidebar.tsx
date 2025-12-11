interface User {
  id: string;
  username: string;
  avatar?: string;
  online?: boolean;
}

interface SidebarProps {
  currentUser: User;
  users: User[];
  selectedUser: User | null;
  onSelectUser: (user: User) => void;
  onLogout: () => void;
}

function Sidebar({ currentUser, users, selectedUser, onSelectUser, onLogout }: SidebarProps) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div>
          <h2>Chats</h2>
          <div className="user-info">{currentUser.username}</div>
        </div>
        <button className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>
      <div className="user-list">
        {users.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#8696a0' }}>
            No users online
          </div>
        ) : (
          users.map((user) => (
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
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Sidebar;
