-- Migration: add encrypted column to messages table
-- This migration adds support for tracking whether messages are encrypted (E2EE)

ALTER TABLE messages ADD COLUMN encrypted INTEGER DEFAULT 0;

-- Create index for querying encrypted messages
CREATE INDEX IF NOT EXISTS idx_messages_encrypted ON messages(encrypted, timestamp);
