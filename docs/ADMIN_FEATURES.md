# Admin Features Documentation

## Overview

This document describes the admin panel features that allow administrators to manage users and their permissions in the WhatsApp Clone application.

## Features

### 1. User Management
- View all registered users
- Enable/disable user accounts
- Promote users to admin role
- Revoke admin privileges

### 2. Permission Control
- Grant or revoke image sending rights
- Control user activity status
- Track disabled users and who disabled them

### 3. Admin Dashboard
- Real-time statistics (total users, active, disabled, admins, image rights)
- Search and filter users
- Sortable user list
- Quick action buttons

## Database Schema Changes

### Users Table - New Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | TEXT | 'user' | User role ('user' or 'admin') |
| `is_active` | INTEGER | 1 | Account status (1=active, 0=disabled) |
| `can_send_images` | INTEGER | 1 | Image sending permission (1=allowed, 0=denied) |
| `disabled_at` | INTEGER | NULL | Timestamp when account was disabled |
| `disabled_by` | TEXT | NULL | ID of admin who disabled the account |

## API Endpoints

### Admin Endpoints

All admin endpoints require authentication with the `Authorization` header:
```
Authorization: Bearer {userId}
```

#### GET /api/admin/users
Get all users with full details.

**Response:**
```json
[
  {
    "id": "user-id",
    "username": "john_doe",
    "role": "user",
    "is_active": 1,
    "can_send_images": 1,
    "lastSeen": 1699564800000,
    "created_at": 1699564800000,
    "disabled_at": null,
    "disabled_by": null
  }
]
```

#### PUT /api/admin/users/:userId/status
Enable or disable a user account.

**Request:**
```json
{
  "is_active": 0,
  "disabled_by": "admin-user-id"
}
```

**Response:**
```json
{
  "success": true
}
```

#### PUT /api/admin/users/:userId/permissions
Grant or revoke image sending permission.

**Request:**
```json
{
  "can_send_images": 0
}
```

**Response:**
```json
{
  "success": true
}
```

#### PUT /api/admin/users/:userId/role
Update user role (promote to admin or revoke admin).

**Request:**
```json
{
  "role": "admin"
}
```

**Response:**
```json
{
  "success": true
}
```

## WebSocket Permission Enforcement

The WebSocket server automatically enforces permissions when users send messages:

1. **Account Status Check**: Disabled users are disconnected and shown an error message
2. **Image Permission Check**: Users without image rights cannot send images
3. **Real-time Enforcement**: Permissions are checked on every message

### Error Messages

| Scenario | Error Message |
|----------|---------------|
| Account disabled | "Your account has been disabled by an administrator" |
| No image rights | "You do not have permission to send images" |
| User not found | "User not found. Please log in again" |

## Migration Guide

### Step 1: Run Database Migration

**For local development:**
```bash
npx wrangler d1 execute whatsapp_clone_db --local --file=./migrations/001_add_admin_features.sql
```

**For production:**
```bash
npx wrangler d1 execute whatsapp_clone_db --remote --file=./migrations/001_add_admin_features.sql
```

### Step 2: Create First Admin User

After running the migration, update one user to be an admin:

**Local:**
```bash
npx wrangler d1 execute whatsapp_clone_db --local --command "UPDATE users SET role = 'admin' WHERE username = 'your-username'"
```

**Production:**
```bash
npx wrangler d1 execute whatsapp_clone_db --remote --command "UPDATE users SET role = 'admin' WHERE username = 'your-username'"
```

### Step 3: Deploy Changes

```bash
# Deploy worker with admin endpoints
npx wrangler deploy

# Verify deployment
npx wrangler tail
```

## Frontend Integration

### Accessing Admin Dashboard

1. Log in with an admin account
2. The admin panel button will appear in the sidebar header (for admin users only)
3. Click the "Admin Panel" button to open the dashboard

### Admin Dashboard Component

**Location:** `src/client/components/AdminDashboard.tsx`

**Usage:**
```tsx
import AdminDashboard from './components/AdminDashboard';

{currentUser.role === 'admin' && showAdminPanel && (
  <AdminDashboard
    currentUser={currentUser}
    onClose={() => setShowAdminPanel(false)}
  />
)}
```

## Security Considerations

### Authorization

- All admin endpoints verify the requesting user's role
- Only users with `role='admin'` can access admin endpoints
- Authorization is checked on every API call

### Permissions Hierarchy

1. **Admins can:**
   - View all users
   - Enable/disable any user account
   - Grant/revoke image permissions
   - Promote users to admin
   - Revoke admin from other admins

2. **Admins cannot:**
   - Disable their own account
   - Change their own permissions (grayed out in UI)

3. **Disabled users:**
   - Cannot log in
   - Are automatically disconnected if online
   - Cannot send any messages

4. **Users without image rights:**
   - Can still send text messages
   - Cannot upload or send images
   - See error message when attempting to send images

## Best Practices

### Creating Admins

1. Start with one trusted admin account
2. Test admin functions thoroughly before production
3. Use strong passwords for admin accounts
4. Keep track of who has admin access

### Managing Users

1. **Disabling Users:**
   - Disabled users are automatically logged out
   - Their messages remain in the database
   - They can be re-enabled at any time

2. **Image Permissions:**
   - Useful for moderating content
   - Can be used to restrict new users initially
   - Can be revoked temporarily for violations

3. **Admin Privileges:**
   - Grant admin carefully
   - Admins have full control over all users
   - Consider having multiple admins for availability

## Troubleshooting

### User Can't Access Admin Panel

1. Verify user has `role='admin'` in database:
   ```sql
   SELECT id, username, role FROM users WHERE username = 'username';
   ```

2. Check if role is included in login response
3. Clear localStorage and log in again

### Permission Changes Not Taking Effect

1. User must reconnect WebSocket (refresh page or log out/in)
2. Check database has been updated:
   ```sql
   SELECT id, username, is_active, can_send_images FROM users WHERE id = 'user-id';
   ```

### Admin Endpoints Returning 403

1. Verify `Authorization` header is being sent
2. Check user ID in header matches an admin user
3. Verify CORS headers include 'Authorization'

## Future Enhancements

Potential improvements for future versions:

1. **Role-based Access Control (RBAC)**
   - Multiple admin levels (super admin, moderator, etc.)
   - Granular permissions per role

2. **Audit Log**
   - Track all admin actions
   - View history of user changes
   - Filter by admin, date, action type

3. **Bulk Actions**
   - Select multiple users
   - Apply actions to multiple users at once
   - Import/export user lists

4. **User Analytics**
   - Message count per user
   - Active hours analysis
   - User engagement metrics

5. **Content Moderation**
   - View reported messages
   - Ban users for violations
   - Automated content filtering

6. **Notifications**
   - Notify users when disabled/enabled
   - Alert admins of suspicious activity
   - Email notifications for admin actions

## Testing Checklist

- [ ] Create admin user via database update
- [ ] Log in with admin account
- [ ] Verify admin panel button appears
- [ ] Open admin dashboard
- [ ] View all users in table
- [ ] Search for specific user
- [ ] Filter by status (all/active/disabled)
- [ ] Disable a user account
- [ ] Verify disabled user cannot log in
- [ ] Re-enable user account
- [ ] Revoke image permission from user
- [ ] Verify user cannot send images
- [ ] Grant image permission back
- [ ] Promote user to admin
- [ ] Verify new admin can access admin panel
- [ ] Revoke admin privileges
- [ ] Check statistics are accurate
- [ ] Test with disabled account (should get error)
- [ ] Test with user without image rights
- [ ] Verify admin cannot disable themselves

## Support

For issues or questions regarding admin features:
1. Check the troubleshooting section above
2. Review the API endpoint documentation
3. Check browser console for error messages
4. Verify database schema is up to date

---

**Document Version:** 1.0
**Last Updated:** 2025-12-11
**Author:** Development Team
