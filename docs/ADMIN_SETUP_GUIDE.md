# Admin Dashboard - Quick Setup Guide

## ✅ Integration Complete!

The admin dashboard has been successfully integrated into your WhatsApp Clone application. Follow these steps to start using it.

---

## Step 1: Run Database Migration

Add the new admin columns to your database:

### Local Development:
```bash
npx wrangler d1 execute whatsapp_clone_db --local --file=./migrations/001_add_admin_features.sql
```

### Production:
```bash
npx wrangler d1 execute whatsapp_clone_db --remote --file=./migrations/001_add_admin_features.sql
```

---

## Step 2: Create Your First Admin User

Update an existing user to have admin privileges:

### Local Development:
```bash
npx wrangler d1 execute whatsapp_clone_db --local --command "UPDATE users SET role = 'admin' WHERE username = 'YOUR_USERNAME'"
```

**Replace `YOUR_USERNAME` with your actual username.**

### Production:
```bash
npx wrangler d1 execute whatsapp_clone_db --remote --command "UPDATE users SET role = 'admin' WHERE username = 'YOUR_USERNAME'"
```

---

## Step 3: Restart Development Servers

Stop and restart your development servers to pick up the changes:

```bash
# Stop current servers (Ctrl+C)

# Start backend
npm run dev

# In another terminal, start frontend
npm run dev:client
```

---

## Step 4: Access the Admin Dashboard

1. **Log in** to the application with your admin account (the username you made admin in Step 2)
2. You should see a **"👑 Admin"** button in the sidebar header (next to the Logout button)
3. Click the **"👑 Admin"** button to open the admin dashboard
4. Manage users, permissions, and roles!

---

## Admin Dashboard Features

### 📊 Statistics Dashboard
- Total users
- Active users
- Disabled users
- Admin count
- Users with image rights

### 👥 User Management
- **Enable/Disable Accounts**: Prevent users from logging in
- **Image Permissions**: Control who can send images
- **Promote to Admin**: Give admin privileges to users
- **Revoke Admin**: Remove admin privileges

### 🔍 Search & Filter
- Search users by username
- Filter by status (all/active/disabled)
- Real-time table updates

### 🛡️ Permission Enforcement
- Disabled users are automatically logged out
- Users without image rights cannot send images
- Real-time permission checks

---

## Troubleshooting

### "Admin button doesn't appear"

**Check 1:** Verify your user has admin role
```bash
npx wrangler d1 execute whatsapp_clone_db --local --command "SELECT username, role FROM users WHERE username = 'YOUR_USERNAME'"
```

**Check 2:** Clear localStorage and log in again
```javascript
// In browser console:
localStorage.clear();
// Then refresh and log in again
```

### "403 Forbidden" when accessing admin endpoints

- Make sure you're logged in with an admin account
- Check browser console for errors
- Verify the Authorization header is being sent

### "Database changes not applied"

Re-run the migration:
```bash
npx wrangler d1 execute whatsapp_clone_db --local --file=./migrations/001_add_admin_features.sql
```

---

## Security Notes

⚠️ **Important:**
- Admin users have full control over all other users
- You cannot disable your own account (UI prevents this)
- All admin actions require authentication
- Disabled users are immediately disconnected

---

## Next Steps

After completing the setup:

1. ✅ Test disabling a user
2. ✅ Test revoking image permissions
3. ✅ Test promoting a user to admin
4. ✅ Verify disabled users cannot log in
5. ✅ Check that users without image rights see error messages

---

## Quick Reference

### Database Columns Added
- `role` - User role ('user' or 'admin')
- `is_active` - Account status (1=active, 0=disabled)
- `can_send_images` - Image permission (1=allowed, 0=denied)
- `disabled_at` - Timestamp of when account was disabled
- `disabled_by` - Admin user ID who disabled the account

### API Endpoints
- `GET /api/admin/users` - Get all users
- `PUT /api/admin/users/:id/status` - Enable/disable user
- `PUT /api/admin/users/:id/permissions` - Update image rights
- `PUT /api/admin/users/:id/role` - Change user role

---

## Support

For detailed documentation, see:
- **Full Documentation**: `docs/ADMIN_FEATURES.md`
- **API Reference**: Admin endpoints section in `src/worker/index.ts`
- **Database Schema**: `schema.sql`

---

**Setup Complete!** 🎉

You now have a fully functional admin dashboard. Log in with your admin account and start managing your users!
