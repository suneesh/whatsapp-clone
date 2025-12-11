-- Database schema for Cloudflare D1
-- Run this with: wrangler d1 execute whatsapp_clone_db --file=./schema.sql

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  avatar TEXT,
  lastSeen INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  readAt INTEGER,
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(fromUser, toUser);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
