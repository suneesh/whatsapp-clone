import { useState, useEffect } from 'react';

interface User {
  id: string;
  username: string;
  role?: string;
  is_active?: number;
  can_send_images?: number;
  lastSeen?: number;
  created_at?: number;
  disabled_at?: number;
  disabled_by?: string;
  avatar?: string;
  online?: boolean;
}

interface AdminDashboardProps {
  currentUser: User;
  onClose: () => void;
}

function AdminDashboard({ currentUser, onClose }: AdminDashboardProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'disabled'>('all');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/admin/users', {
        headers: {
          'Authorization': `Bearer ${currentUser.id}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }

      const data = await response.json();
      setUsers(data as User[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const toggleUserStatus = async (userId: string, currentStatus: number) => {
    try {
      const newStatus = currentStatus === 1 ? 0 : 1;
      const response = await fetch(`/api/admin/users/${userId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentUser.id}`,
        },
        body: JSON.stringify({
          is_active: newStatus,
          disabled_by: currentUser.id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update user status');
      }

      setSuccessMessage(`User ${newStatus === 1 ? 'enabled' : 'disabled'} successfully`);
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user status');
      setTimeout(() => setError(null), 3000);
    }
  };

  const toggleImagePermission = async (userId: string, currentPermission: number) => {
    try {
      const newPermission = currentPermission === 1 ? 0 : 1;
      const response = await fetch(`/api/admin/users/${userId}/permissions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentUser.id}`,
        },
        body: JSON.stringify({
          can_send_images: newPermission,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update image permission');
      }

      setSuccessMessage(`Image permission ${newPermission === 1 ? 'granted' : 'revoked'} successfully`);
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update image permission');
      setTimeout(() => setError(null), 3000);
    }
  };

  const makeAdmin = async (userId: string) => {
    if (!confirm('Are you sure you want to make this user an admin?')) {
      return;
    }

    try {
      const response = await fetch(`/api/admin/users/${userId}/role`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentUser.id}`,
        },
        body: JSON.stringify({
          role: 'admin',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update user role');
      }

      setSuccessMessage('User promoted to admin successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user role');
      setTimeout(() => setError(null), 3000);
    }
  };

  const revokeAdmin = async (userId: string) => {
    if (!confirm('Are you sure you want to revoke admin privileges?')) {
      return;
    }

    try {
      const response = await fetch(`/api/admin/users/${userId}/role`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentUser.id}`,
        },
        body: JSON.stringify({
          role: 'user',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update user role');
      }

      setSuccessMessage('Admin privileges revoked successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user role');
      setTimeout(() => setError(null), 3000);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatLastSeen = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.username.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter =
      filterStatus === 'all' ||
      (filterStatus === 'active' && user.is_active === 1) ||
      (filterStatus === 'disabled' && user.is_active === 0);
    return matchesSearch && matchesFilter;
  });

  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active === 1).length,
    disabled: users.filter(u => u.is_active === 0).length,
    admins: users.filter(u => u.role === 'admin').length,
    withImageRights: users.filter(u => u.can_send_images === 1).length,
  };

  return (
    <div className="admin-overlay">
      <div className="admin-dashboard">
        <div className="admin-header">
          <div>
            <h1>Admin Dashboard</h1>
            <p>Manage users and permissions</p>
          </div>
          <button className="admin-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {error && (
          <div className="admin-alert admin-alert-error">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="admin-alert admin-alert-success">
            {successMessage}
          </div>
        )}

        <div className="admin-stats">
          <div className="stat-card">
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Total Users</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.active}</div>
            <div className="stat-label">Active</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.disabled}</div>
            <div className="stat-label">Disabled</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.admins}</div>
            <div className="stat-label">Admins</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.withImageRights}</div>
            <div className="stat-label">Image Rights</div>
          </div>
        </div>

        <div className="admin-controls">
          <input
            type="text"
            placeholder="Search users..."
            className="admin-search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select
            className="admin-filter"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as 'all' | 'active' | 'disabled')}
          >
            <option value="all">All Users</option>
            <option value="active">Active Only</option>
            <option value="disabled">Disabled Only</option>
          </select>
          <button className="admin-refresh-btn" onClick={fetchUsers}>
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="admin-loading">Loading users...</div>
        ) : (
          <div className="admin-table-container">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Image Rights</th>
                  <th>Last Seen</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(user => (
                  <tr key={user.id} className={user.is_active === 0 ? 'user-disabled' : ''}>
                    <td>
                      <div className="user-cell">
                        <div className="user-avatar-sm">
                          {user.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="user-name-cell">{user.username}</div>
                          {user.id === currentUser.id && (
                            <span className="badge badge-you">You</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${user.role}`}>
                        {user.role === 'admin' ? '👑 Admin' : 'User'}
                      </span>
                    </td>
                    <td>
                      {user.is_active === 1 ? (
                        <span className="badge badge-success">Active</span>
                      ) : (
                        <span className="badge badge-danger">Disabled</span>
                      )}
                    </td>
                    <td>
                      {user.can_send_images === 1 ? (
                        <span className="badge badge-success">✓ Enabled</span>
                      ) : (
                        <span className="badge badge-danger">✗ Disabled</span>
                      )}
                    </td>
                    <td>{user.lastSeen ? formatLastSeen(user.lastSeen) : 'Never'}</td>
                    <td>{user.created_at ? formatDate(user.created_at) : 'Unknown'}</td>
                    <td>
                      <div className="action-buttons">
                        {user.id !== currentUser.id && (
                          <>
                            <button
                              className={`action-btn ${user.is_active === 1 ? 'btn-danger' : 'btn-success'}`}
                              onClick={() => toggleUserStatus(user.id, user.is_active ?? 1)}
                              title={user.is_active === 1 ? 'Disable User' : 'Enable User'}
                            >
                              {user.is_active === 1 ? '🚫' : '✓'}
                            </button>
                            <button
                              className={`action-btn ${user.can_send_images === 1 ? 'btn-warning' : 'btn-success'}`}
                              onClick={() => toggleImagePermission(user.id, user.can_send_images ?? 1)}
                              title={user.can_send_images === 1 ? 'Revoke Image Rights' : 'Grant Image Rights'}
                            >
                              📷
                            </button>
                            {user.role === 'admin' ? (
                              <button
                                className="action-btn btn-warning"
                                onClick={() => revokeAdmin(user.id)}
                                title="Revoke Admin"
                              >
                                👑↓
                              </button>
                            ) : (
                              <button
                                className="action-btn btn-primary"
                                onClick={() => makeAdmin(user.id)}
                                title="Make Admin"
                              >
                                👑↑
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredUsers.length === 0 && (
              <div className="admin-empty">
                No users found matching your criteria.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminDashboard;
