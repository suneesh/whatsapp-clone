-- Database schema for Cloudflare D1
-- Run this with: wrangler d1 execute whatsapp_clone_db --file=./schema.sql

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  avatar TEXT,
  lastSeen INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  role TEXT DEFAULT 'user',
  is_active INTEGER DEFAULT 1,
  can_send_images INTEGER DEFAULT 1,
  disabled_at INTEGER,
  disabled_by TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  readAt INTEGER,
  type TEXT DEFAULT 'text',
  imageData TEXT,
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(fromUser, toUser);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- E2EE identity + prekey tables
CREATE TABLE IF NOT EXISTS user_identity_keys (
  user_id TEXT PRIMARY KEY,
  identity_key TEXT NOT NULL,
  signing_key TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_prekeys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key_id INTEGER NOT NULL,
  prekey_type TEXT NOT NULL,
  public_key TEXT NOT NULL,
  signature TEXT,
  created_at INTEGER NOT NULL,
  is_used INTEGER DEFAULT 0,
  used_at INTEGER,
  UNIQUE(user_id, key_id, prekey_type),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_prekeys_user_type ON user_prekeys(user_id, prekey_type, is_used);

-- Groups table
CREATE TABLE IF NOT EXISTS groups (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  avatar TEXT,
  owner_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  settings TEXT, -- JSON: messagePermission, metadataPermission, joinApproval, maxMembers
  FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- Group members table
CREATE TABLE IF NOT EXISTS group_members (
  group_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member', -- 'owner', 'admin', 'member'
  joined_at INTEGER NOT NULL,
  added_by TEXT,
  PRIMARY KEY (group_id, user_id),
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (added_by) REFERENCES users(id)
);

-- Group messages table
CREATE TABLE IF NOT EXISTS group_messages (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  from_user TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  type TEXT DEFAULT 'text', -- 'text', 'image', 'system'
  imageData TEXT,
  system_event TEXT, -- For system messages: 'member_added', 'member_removed', etc.
  metadata TEXT, -- JSON for additional data
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
  FOREIGN KEY (from_user) REFERENCES users(id)
);

-- Group message read receipts
CREATE TABLE IF NOT EXISTS group_message_reads (
  message_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  read_at INTEGER NOT NULL,
  PRIMARY KEY (message_id, user_id),
  FOREIGN KEY (message_id) REFERENCES group_messages(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Group invite links
CREATE TABLE IF NOT EXISTS group_invite_links (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  link_code TEXT NOT NULL UNIQUE,
  created_by TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER,
  max_uses INTEGER,
  current_uses INTEGER DEFAULT 0,
  is_active INTEGER DEFAULT 1,
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Indexes for groups
CREATE INDEX IF NOT EXISTS idx_groups_owner ON groups(owner_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_messages_group ON group_messages(group_id);
CREATE INDEX IF NOT EXISTS idx_group_messages_timestamp ON group_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_group_invite_links_code ON group_invite_links(link_code);
CREATE INDEX IF NOT EXISTS idx_group_invite_links_group ON group_invite_links(group_id);
