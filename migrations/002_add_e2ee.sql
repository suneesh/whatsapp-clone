-- Migration: add E2EE identity and prekey tables
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
