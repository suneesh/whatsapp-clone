-- Migration: Add Admin Features
-- Date: 2025-12-11
-- Description: Add role, permissions, and status fields to users table

-- Add new columns to users table
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';
ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN can_send_images INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN disabled_at INTEGER;
ALTER TABLE users ADD COLUMN disabled_by TEXT;

-- Create first admin user (replace with your desired admin username)
-- UPDATE users SET role = 'admin' WHERE username = 'admin';
