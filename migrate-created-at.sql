-- Add created_at column to users table if it doesn't exist
ALTER TABLE users ADD COLUMN created_at INTEGER DEFAULT 0;

-- Update existing users to have a created_at timestamp
UPDATE users SET created_at = strftime('%s', 'now') * 1000 WHERE created_at = 0 OR created_at IS NULL;
