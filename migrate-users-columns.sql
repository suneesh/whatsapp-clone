-- Add missing columns to users table
-- These might fail if columns already exist, but that's okay

-- Add role column
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';

-- Add is_active column  
ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;

-- Add can_send_images column
ALTER TABLE users ADD COLUMN can_send_images INTEGER DEFAULT 1;

-- Add disabled_at column
ALTER TABLE users ADD COLUMN disabled_at INTEGER;

-- Add disabled_by column
ALTER TABLE users ADD COLUMN disabled_by TEXT;

-- Update existing users to have default values
UPDATE users SET role = 'user' WHERE role IS NULL;
UPDATE users SET is_active = 1 WHERE is_active IS NULL;
UPDATE users SET can_send_images = 1 WHERE can_send_images IS NULL;
