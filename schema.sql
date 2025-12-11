-- Database schema for Cloudflare D1
-- Run this with: wrangler d1 execute whatsapp_clone_db --file=./schema.sql

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  avatar TEXT,
  lastSeen INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(fromUser, toUser);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
