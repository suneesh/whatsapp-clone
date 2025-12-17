-- Migration: Add encrypted column to messages table
-- Run this with: wrangler d1 execute whatsapp_clone_db --file=./migrations/001_add_encrypted_column.sql

-- Add encrypted flag to messages table
ALTER TABLE messages ADD COLUMN encrypted INTEGER DEFAULT 0;

-- Create index for encrypted messages
CREATE INDEX IF NOT EXISTS idx_messages_encrypted ON messages(encrypted);
