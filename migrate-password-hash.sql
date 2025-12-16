-- Add password_hash column to users table if it doesn't exist
ALTER TABLE users ADD COLUMN password_hash TEXT;

-- Update any existing users (if needed)
-- This migration is safe to run multiple times
