# Impact Analysis: Core E2E Encryption User Stories

**Document Version:** 1.1
**Created:** 2025-12-16
**Analysis Scope:** User Stories 1-6 (Phase 1-2 - Core Encryption)

---

## Executive Summary

This document analyzes the impact of implementing the core End-to-End Encryption (E2EE) user stories on the existing Quick Chat codebase. The analysis covers architectural changes, database modifications, API updates, and identifies potential risks and mitigation strategies.

**Overall Impact Rating:** **HIGH** - Major architectural changes required across all layers

**Key Findings:**
- 29 files touched (17 new, 12 modified) across frontend, backend, and database layers
- 6 new client-side crypto/storage modules required plus 2 new UI components
- 4 new database tables plus a major `messages` table refactor with legacy coexistence
- 2 new API endpoints for prekey management (authenticated + rate limited)
- WebSocket protocol requires encrypted payload extension and ratchet metadata handling
- Message storage format changes to encrypted content with transitional plain-text dual writes

---

## Table of Contents

1. [Affected User Stories](#affected-user-stories)
2. [Architectural Impact](#architectural-impact)
3. [Database Impact](#database-impact)
4. [Backend Impact](#backend-impact)
5. [Frontend Impact](#frontend-impact)
6. [API Impact](#api-impact)
7. [Performance Impact](#performance-impact)
8. [Security Impact](#security-impact)
9. [User Experience Impact](#user-experience-impact)
10. [Testing Impact](#testing-impact)
11. [Deployment Impact](#deployment-impact)
12. [Risk Analysis](#risk-analysis)
13. [Migration Strategy](#migration-strategy)
14. [Effort Estimation](#effort-estimation)

---

## Affected User Stories

### Phase 1: Core Encryption (Weeks 1-4)
1. **US1: Key Pair Generation and Management** - Infrastructure foundation
2. **US2: Secure Session Establishment** - X3DH protocol implementation
3. **US3: Message Encryption and Decryption** - Double Ratchet algorithm

### Phase 2: Security Features (Weeks 5-6)
4. **US4: Key Fingerprint Verification** - Trust establishment
5. **US5: Forward Secrecy** - Validation and testing
6. **US6: Backward Secrecy** - Validation and testing

---

## Architectural Impact

### Current Architecture

```
┌─────────────┐         WebSocket          ┌──────────────┐
│   Client    │◄─────────────────────────►│ ChatRoom DO  │
│  (React)    │                            │              │
└─────────────┘                            └──────────────┘
      │                                            │
      │ REST API                                   │
      ▼                                            ▼
┌─────────────┐                            ┌──────────────┐
│  Worker     │                            │      D1      │
│  (index.ts) │◄──────────────────────────►│   Database   │
└─────────────┘                            └──────────────┘
```

### New Architecture with E2EE

```
┌─────────────────────────────────────────────────────┐
│              Client (Browser)                        │
│  ┌───────────┐  ┌────────────┐  ┌──────────────┐   │
│  │ React UI  │  │ E2EE Layer │  │  IndexedDB   │   │
│  │           │  │            │  │  (Keys)      │   │
│  └─────┬─────┘  └─────┬──────┘  └──────┬───────┘   │
│        │              │                 │            │
│        │        ┌─────▼─────┐          │            │
│        │        │CryptoEngine│         │            │
│        │        │KeyManager │          │            │
│        │        │RatchetEngine│        │            │
│        │        └─────┬─────┘          │            │
│        │              │                 │            │
└────────┼──────────────┼─────────────────┼────────────┘
         │              │                 │
         │ Encrypted    │                 │
         │ WebSocket    │                 │
         ▼              ▼                 ▼
┌─────────────┐         WebSocket          ┌──────────────┐
│   Client    │◄─────────────────────────►│ ChatRoom DO  │
│ (Encrypted) │    (Encrypted Payload)     │ (Passthrough)│
└─────────────┘                            └──────────────┘
      │                                            │
      │ REST API                                   │
      │ (Prekey fetch)                            │
      ▼                                            ▼
┌─────────────┐                            ┌──────────────┐
│  Worker     │                            │      D1      │
│  (index.ts) │◄──────────────────────────►│   Database   │
│             │                            │ + Prekeys    │
└─────────────┘                            └──────────────┘
```

### Key Architectural Changes

#### 1. Client-Side Encryption Layer (NEW)
**Impact:** HIGH
- **New Module:** `src/client/crypto/` directory structure
- **Files to Create:**
  - `src/client/crypto/CryptoEngine.ts` - Low-level crypto primitives
  - `src/client/crypto/KeyManager.ts` - Key generation and storage
  - `src/client/crypto/RatchetEngine.ts` - Double Ratchet implementation
  - `src/client/crypto/X3DH.ts` - Session establishment
  - `src/client/crypto/SessionStore.ts` - IndexedDB session management
  - `src/client/crypto/types.ts` - Crypto-specific types

**Rationale:** All encryption/decryption must happen client-side to maintain E2EE guarantees.

#### 2. IndexedDB Storage Layer (NEW)
**Impact:** HIGH
- **New Module:** `src/client/storage/` directory
- **Files to Create:**
  - `src/client/storage/KeyStorage.ts` - Identity and prekey storage
  - `src/client/storage/SessionStorage.ts` - Ratchet state storage
  - `src/client/storage/MessageStorage.ts` - Encrypted message cache
  - `src/client/storage/db.ts` - IndexedDB initialization

**Purpose:** Persistent storage for keys, sessions, and messages in the browser.

#### 3. Server as Prekey Repository
**Impact:** MEDIUM
- **Change:** Server stores public keys only (no plaintext messages)
- **Implication:** Server becomes a key distribution and relay service
- **Modified Behavior:** ChatRoom and Worker become "dumb pipes"

> **Transitional Note:** During the phased rollout described later, the Worker will temporarily persist both plaintext and encrypted payloads (flagged via `is_legacy`) so that legacy clients remain functional. Plaintext retention is time-boxed to Phase 1–2, and the cleanup phase explicitly deletes the legacy columns to realign with the "dumb pipe" end-state.

---

## Database Impact

### Schema Changes

#### 1. New Table: `user_identity_keys`
**Impact:** HIGH - New table creation

```sql
CREATE TABLE IF NOT EXISTS user_identity_keys (
  user_id TEXT PRIMARY KEY,
  identity_key TEXT NOT NULL,  -- Base64-encoded public key
  created_at INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_identity_keys_user
  ON user_identity_keys(user_id);
```

**Purpose:** Store users' long-term identity public keys.

#### 2. New Table: `user_prekeys`
**Impact:** HIGH - New table creation

```sql
CREATE TABLE IF NOT EXISTS user_prekeys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key_id INTEGER NOT NULL,
  prekey_type TEXT NOT NULL,  -- 'signed' or 'onetime'
  public_key TEXT NOT NULL,   -- Base64-encoded
  signature TEXT,             -- For signed prekeys (Base64)
  created_at INTEGER NOT NULL,
  is_used INTEGER DEFAULT 0,
  used_at INTEGER,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, key_id, prekey_type)
);

CREATE INDEX IF NOT EXISTS idx_user_prekeys_user
  ON user_prekeys(user_id, prekey_type, is_used);
```

**Purpose:** Store one-time prekeys and signed prekeys for X3DH.

#### 3. Modified Table: `messages`
**Impact:** HIGH - Existing table modification

**Before:**
```sql
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,        -- ❌ Plaintext
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  readAt INTEGER,
  type TEXT DEFAULT 'text',
  imageData TEXT,              -- ❌ Plaintext
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);
```

**After (transition state):**
```sql
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,              -- Legacy plaintext (kept for rollback)
  encrypted_content TEXT,             -- ✅ Encrypted (Base64)
  ratchet_header TEXT,                -- ✅ NEW: Ratchet metadata (JSON)
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  readAt INTEGER,
  type TEXT DEFAULT 'text',
  imageData TEXT,                     -- Legacy plaintext attachments
  encrypted_image_data TEXT,          -- ✅ Encrypted attachments
  is_legacy INTEGER DEFAULT 0,        -- ✅ Flags rows awaiting migration
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);
```

During Phase 1 the application dual-writes plaintext and encrypted payloads while `is_legacy = 1`. Once every row has encrypted payloads (Phase 3 cleanup), `content`/`imageData` will be dropped and `encrypted_content`/`ratchet_header` flip to `NOT NULL`. This sequencing matches the migration script in [Migration Strategy](#migration-strategy) and prevents constraint violations during rollout.

**Migration Required:** YES - see [Migration Strategy](#migration-strategy)

#### 4. New Table: `session_metadata`
**Impact:** MEDIUM - Optional audit table

```sql
CREATE TABLE IF NOT EXISTS session_metadata (
  id TEXT PRIMARY KEY,
  user_a TEXT NOT NULL,
  user_b TEXT NOT NULL,
  established_at INTEGER NOT NULL,
  prekey_used TEXT,  -- Which prekey was consumed
  last_message_at INTEGER,
  FOREIGN KEY (user_a) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (user_b) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_a, user_b)
);
```

**Purpose:** Track session establishment for debugging and key rotation.

#### 5. New Table: `key_verification`
**Impact:** MEDIUM - User Story 4

```sql
CREATE TABLE IF NOT EXISTS key_verification (
  id TEXT PRIMARY KEY,
  verifier_user_id TEXT NOT NULL,
  verified_user_id TEXT NOT NULL,
  verified_fingerprint TEXT NOT NULL,
  verified_at INTEGER NOT NULL,
  verification_method TEXT, -- 'manual', 'qr_code'
  FOREIGN KEY (verifier_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (verified_user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(verifier_user_id, verified_user_id)
);
```

**Purpose:** Store key verification status (Safety Numbers).

### Database Size Impact

**Current Estimate:**
- Average message size: ~200 bytes (plaintext)

**Post-E2EE Estimate:**
- Average message size: ~500 bytes (encrypted + overhead)
- Breakdown:
  - Encrypted content: ~256 bytes (Base64-encoded ciphertext)
  - Ratchet header: ~150 bytes (JSON with ratchet keys)
  - Metadata: ~94 bytes (same as before)

**Storage Increase:** ~150% for messages table

---

## Backend Impact

### Files to Modify

#### 1. `src/worker/index.ts`
**Impact:** MEDIUM
**Lines Affected:** ~150 lines (new endpoints + modifications)

**Changes Required:**

```typescript
// NEW ENDPOINTS

// Get user's prekey bundle
if (path.match(/^\/users\/[^\/]+\/prekeys$/) && request.method === 'GET') {
  const userId = path.split('/')[2];

  // Fetch identity key
  const identityKey = await env.DB.prepare(
    'SELECT identity_key FROM user_identity_keys WHERE user_id = ?'
  ).bind(userId).first();

  // Fetch signed prekey
  const signedPrekey = await env.DB.prepare(
    'SELECT key_id, public_key, signature FROM user_prekeys WHERE user_id = ? AND prekey_type = ? ORDER BY created_at DESC LIMIT 1'
  ).bind(userId, 'signed').first();

  // Fetch one unused one-time prekey
  const onetimePrekey = await env.DB.prepare(
    'SELECT id, key_id, public_key FROM user_prekeys WHERE user_id = ? AND prekey_type = ? AND is_used = 0 LIMIT 1'
  ).bind(userId, 'onetime').first();

  // Mark one-time prekey as used
  if (onetimePrekey) {
    await env.DB.prepare(
      'UPDATE user_prekeys SET is_used = 1, used_at = ? WHERE id = ?'
    ).bind(Date.now(), onetimePrekey.id).run();
  }

  return new Response(JSON.stringify({
    identityKey: identityKey?.identity_key,
    signedPrekey: signedPrekey ? {
      keyId: signedPrekey.key_id,
      publicKey: signedPrekey.public_key,
      signature: signedPrekey.signature,
    } : null,
    onetimePrekey: onetimePrekey ? {
      keyId: onetimePrekey.key_id,
      publicKey: onetimePrekey.public_key,
    } : null,
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

// Upload prekey bundle
if (path === '/users/prekeys' && request.method === 'POST') {
  const authHeader = request.headers.get('Authorization');
  const userId = authHeader?.replace('Bearer ', '');

  const body = await request.json() as {
    identityKey: string;
    signedPrekey: { keyId: number; publicKey: string; signature: string };
    onetimePrekeys: Array<{ keyId: number; publicKey: string }>;
  };

  // Store identity key
  await env.DB.prepare(
    'INSERT OR REPLACE INTO user_identity_keys (user_id, identity_key, created_at) VALUES (?, ?, ?)'
  ).bind(userId, body.identityKey, Date.now()).run();

  // Store signed prekey
  await env.DB.prepare(
    'INSERT INTO user_prekeys (id, user_id, key_id, prekey_type, public_key, signature, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).bind(
    crypto.randomUUID(),
    userId,
    body.signedPrekey.keyId,
    'signed',
    body.signedPrekey.publicKey,
    body.signedPrekey.signature,
    Date.now()
  ).run();

  // Store one-time prekeys
  for (const prekey of body.onetimePrekeys) {
    await env.DB.prepare(
      'INSERT INTO user_prekeys (id, user_id, key_id, prekey_type, public_key, created_at) VALUES (?, ?, ?, ?, ?, ?)'
    ).bind(
      crypto.randomUUID(),
      userId,
      prekey.keyId,
      'onetime',
      prekey.publicKey,
      Date.now()
    ).run();
  }

  return new Response(JSON.stringify({ success: true }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

// MODIFIED: Save message endpoint (now accepts encrypted content)
if (path === '/messages' && request.method === 'POST') {
  const body = await request.json() as {
    id: string;
    fromUser: string;
    toUser: string;
    encrypted_content: string;      // CHANGED
    ratchet_header: string;         // NEW
    timestamp: number;
    status: string;
    type?: string;
    encrypted_image_data?: string;  // CHANGED
  };

  await env.DB.prepare(
    'INSERT INTO messages (id, fromUser, toUser, encrypted_content, ratchet_header, timestamp, status, type, encrypted_image_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(
    body.id,
    body.fromUser,
    body.toUser,
    body.encrypted_content,
    body.ratchet_header,
    body.timestamp,
    body.status,
    body.type || 'text',
    body.encrypted_image_data || null
  ).run();

  return new Response(JSON.stringify({ success: true }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    status: 201,
  });
}
```

**Testing Impact:** New integration tests needed for prekey distribution.

#### 2. `src/worker/ChatRoom.ts`
**Impact:** MEDIUM
**Lines Affected:** ~50 lines

**Changes Required:**

```typescript
// MODIFIED: Message handling now relays encrypted content
case 'message':
  if (session) {
    const messageType = data.payload.messageType || 'text';

    // Permission checks remain the same
    // ... [existing permission checks] ...

    const message: Message = {
      id: crypto.randomUUID(),
      from: session.userId,
      to: data.payload.to,
      encrypted_content: data.payload.encrypted_content,  // CHANGED
      ratchet_header: data.payload.ratchet_header,        // NEW
      timestamp: Date.now(),
      status: 'sent',
      type: messageType,
      encrypted_image_data: data.payload.encrypted_image_data,  // CHANGED
    };

    // Save encrypted message to database
    await this.env.DB.prepare(
      'INSERT INTO messages (id, fromUser, toUser, encrypted_content, ratchet_header, timestamp, status, type, encrypted_image_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(
      message.id,
      message.from,
      message.to,
      message.encrypted_content,
      message.ratchet_header,
      message.timestamp,
      message.status,
      message.type,
      message.encrypted_image_data || null
    ).run();

    // Relay encrypted message to recipient
    const recipient = this.sessions.get(data.payload.to);
    if (recipient) {
      recipient.ws.send(JSON.stringify({
        type: 'message',
        payload: message,
      }));
      message.status = 'delivered';

      await this.env.DB.prepare(
        'UPDATE messages SET status = ? WHERE id = ?'
      ).bind(message.status, message.id).run();
    }

    // Send confirmation to sender
    ws.send(JSON.stringify({
      type: 'message',
      payload: message,
    }));
  }
  break;
```

**Key Point:** Server never decrypts messages; it only relays encrypted payloads.

#### 3. `src/worker/types.ts`
**Impact:** LOW
**Lines Affected:** ~20 lines

**Changes Required:**

```typescript
// MODIFIED: Message interface
export interface Message {
  id: string;
  from: string;
  to: string;
  encrypted_content: string;      // CHANGED from 'content'
  ratchet_header: string;         // NEW
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
  type?: 'text' | 'image';
  encrypted_image_data?: string;  // CHANGED from 'imageData'
}

// NEW: Prekey bundle types
export interface PrekeyBundle {
  identityKey: string;
  signedPrekey: {
    keyId: number;
    publicKey: string;
    signature: string;
  };
  onetimePrekey?: {
    keyId: number;
    publicKey: string;
  };
}

export interface IdentityKey {
  userId: string;
  publicKey: string;
  fingerprint: string;
}
```

---

## Frontend Impact

### Files to Modify

#### 1. `src/client/App.tsx`
**Impact:** MEDIUM
**Lines Affected:** ~80 lines

**Changes Required:**

```typescript
import { useE2EE } from './hooks/useE2EE';  // NEW HOOK

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  // ... existing state ...

  // NEW: E2EE Hook
  const {
    initializeKeys,
    encryptMessage,
    decryptMessage,
    getFingerprint,
    verifyFingerprint,
    sessionEstablished,
  } = useE2EE(currentUser?.id || '');

  // Initialize keys on login
  useEffect(() => {
    if (currentUser) {
      initializeKeys().then(() => {
        console.log('[E2EE] Keys initialized');
      });
    }
  }, [currentUser, initializeKeys]);

  // MODIFIED: Handle incoming messages with decryption
  const handleMessage = useCallback(async (message: Message) => {
    // Decrypt message before storing
    try {
      const decryptedContent = await decryptMessage(
        message.from,
        message.encrypted_content,
        message.ratchet_header
      );

      const decryptedMessage = {
        ...message,
        content: decryptedContent,  // Decrypted content for UI
      };

      setMessages((prev) => {
        const exists = prev.find((m) => m.id === message.id);
        if (exists) {
          return prev.map((m) => (m.id === message.id ? decryptedMessage : m));
        }
        return [...prev, decryptedMessage];
      });
    } catch (error) {
      console.error('[E2EE] Failed to decrypt message:', error);
      // Store with decryption error indicator
      setMessages((prev) => [...prev, {
        ...message,
        content: '⚠️ Unable to decrypt this message',
        decryptionError: true,
      }]);
    }
  }, [decryptMessage]);

  // MODIFIED: WebSocket send with encryption
  const handleSendMessage = useCallback(async (to: string, content: string) => {
    try {
      const { encrypted_content, ratchet_header } = await encryptMessage(to, content);

      // Send encrypted message via WebSocket
      sendMessage(to, encrypted_content, ratchet_header);
    } catch (error) {
      console.error('[E2EE] Failed to encrypt message:', error);
      alert('Failed to encrypt message. Please try again.');
    }
  }, [encryptMessage, sendMessage]);

  return (
    <>
      <Chat
        currentUser={currentUser}
        users={users}
        messages={messages}
        typingUsers={typingUsers}
        connected={connected}
        onSendMessage={handleSendMessage}  // MODIFIED
        // ... other props ...

        // NEW: E2EE props
        sessionEstablished={sessionEstablished}
        onGetFingerprint={getFingerprint}
        onVerifyFingerprint={verifyFingerprint}
      />
      {/* ... rest of app ... */}
    </>
  );
}
```

**New Dependencies:**
- `src/client/hooks/useE2EE.ts` - Main E2EE hook
- `src/client/crypto/*` - Crypto modules

#### 2. `src/client/components/ChatWindow.tsx`
**Impact:** MEDIUM
**Lines Affected:** ~40 lines

**Changes Required:**

```typescript
// NEW: Encryption status indicator in header
<div className="chat-header">
  <div className="user-info">
    <h2>{selectedUser.username}</h2>
    {/* NEW: Encryption indicator */}
    {sessionEstablished ? (
      <span className="encryption-badge encrypted" title="End-to-end encrypted">
        🔒 Encrypted
      </span>
    ) : (
      <span className="encryption-badge establishing" title="Establishing encrypted session...">
        🔐 Establishing...
      </span>
    )}
  </div>
  {/* NEW: Fingerprint verification button */}
  <button
    className="fingerprint-btn"
    onClick={() => setShowFingerprintModal(true)}
    title="Verify encryption keys"
  >
    🔑 Verify
  </button>
</div>

// NEW: Fingerprint verification modal
{showFingerprintModal && (
  <FingerprintModal
    currentUser={currentUser}
    otherUser={selectedUser}
    onGetFingerprint={onGetFingerprint}
    onVerify={onVerifyFingerprint}
    onClose={() => setShowFingerprintModal(false)}
  />
)}
```

**New Components:**
- `src/client/components/FingerprintModal.tsx` - Fingerprint verification UI
- `src/client/components/EncryptionBadge.tsx` - Reusable encryption status indicator

#### 3. `src/client/components/MessageList.tsx`
**Impact:** LOW
**Lines Affected:** ~10 lines

**Changes Required:**

```typescript
// Display decryption errors
<div className={`message ${message.decryptionError ? 'error' : ''}`}>
  <p>{message.content}</p>
  {message.decryptionError && (
    <span className="decryption-error-badge" title="Message could not be decrypted">
      ⚠️ Decryption failed
    </span>
  )}
</div>
```

#### 4. NEW: `src/client/hooks/useE2EE.ts`
**Impact:** HIGH - New file
**Lines:** ~300 lines

**Overview:**

```typescript
import { useState, useCallback, useEffect } from 'react';
import { KeyManager } from '../crypto/KeyManager';
import { X3DH } from '../crypto/X3DH';
import { RatchetEngine } from '../crypto/RatchetEngine';
import { SessionStore } from '../crypto/SessionStore';

export function useE2EE(userId: string) {
  const [keyManager, setKeyManager] = useState<KeyManager | null>(null);
  const [sessionStore, setSessionStore] = useState<SessionStore | null>(null);
  const [sessions, setSessions] = useState<Map<string, any>>(new Map());

  // Initialize crypto system
  const initializeKeys = useCallback(async () => {
    const km = new KeyManager(userId);
    await km.initialize();

    const ss = new SessionStore(userId);
    await ss.initialize();

    setKeyManager(km);
    setSessionStore(ss);

    // Upload prekey bundle to server
    const bundle = await km.getPrekeyBundle();
    await uploadPrekeyBundle(bundle);
  }, [userId]);

  // Encrypt message
  const encryptMessage = useCallback(async (recipientId: string, plaintext: string) => {
    if (!keyManager || !sessionStore) {
      throw new Error('E2EE not initialized');
    }

    // Get or establish session
    let session = sessions.get(recipientId);
    if (!session) {
      // Fetch recipient's prekey bundle
      const bundle = await fetchPrekeyBundle(recipientId);

      // Perform X3DH
      const x3dh = new X3DH(keyManager.cryptoEngine);
      const sharedSecret = await x3dh.initiatorX3DH(
        keyManager.identityKeyPair,
        bundle
      );

      // Initialize ratchet
      const ratchet = new RatchetEngine(keyManager.cryptoEngine);
      session = await ratchet.initializeSession(sharedSecret, bundle.signedPrekey.publicKey);

      // Save session
      await sessionStore.saveSession(recipientId, session);
      setSessions(prev => new Map(prev).set(recipientId, session));
    }

    // Encrypt with ratchet
    const ratchet = new RatchetEngine(keyManager.cryptoEngine);
    const { message, newState } = await ratchet.encryptMessage(session, new TextEncoder().encode(plaintext));

    // Update session
    await sessionStore.saveSession(recipientId, newState);
    setSessions(prev => new Map(prev).set(recipientId, newState));

    return {
      encrypted_content: btoa(String.fromCharCode(...message.ciphertext)),
      ratchet_header: JSON.stringify(message.header),
    };
  }, [keyManager, sessionStore, sessions]);

  // Decrypt message
  const decryptMessage = useCallback(async (senderId: string, encryptedContent: string, ratchetHeaderJson: string) => {
    // Implementation similar to encryptMessage
    // ...
  }, [keyManager, sessionStore, sessions]);

  // Get fingerprint
  const getFingerprint = useCallback(async (userId: string) => {
    if (!keyManager) return '';
    return await keyManager.getFingerprint(userId);
  }, [keyManager]);

  // Verify fingerprint
  const verifyFingerprint = useCallback(async (userId: string, fingerprint: string) => {
    // Store verification in database
    // ...
  }, []);

  return {
    initializeKeys,
    encryptMessage,
    decryptMessage,
    getFingerprint,
    verifyFingerprint,
    sessionEstablished: (userId: string) => sessions.has(userId),
  };
}
```

#### 5. NEW: Crypto Module Files

**Files to Create:**
- `src/client/crypto/CryptoEngine.ts` (~200 lines)
- `src/client/crypto/KeyManager.ts` (~250 lines)
- `src/client/crypto/RatchetEngine.ts` (~350 lines)
- `src/client/crypto/X3DH.ts` (~200 lines)
- `src/client/crypto/SessionStore.ts` (~150 lines)
- `src/client/crypto/types.ts` (~100 lines)

**Total New Frontend Code:** ~1,550 lines

---

## API Impact

### New Endpoints

#### 1. `GET /api/users/:userId/prekeys`
**Purpose:** Fetch prekey bundle for session establishment
**Request:** None
**Response:**
```json
{
  "identityKey": "base64-encoded-public-key",
  "signedPrekey": {
    "keyId": 1,
    "publicKey": "base64-encoded",
    "signature": "base64-encoded"
  },
  "onetimePrekey": {
    "keyId": 42,
    "publicKey": "base64-encoded"
  }
}
```
**Authorization:** Required (Bearer token). The Worker validates that the caller is authenticated and only allows access to the requested user's bundle if the caller is either the owner or an approved contact. Requests without a valid token return `401 Unauthorized`; mismatched IDs return `403 Forbidden`. Endpoint is rate limited (50 requests / 5 minutes per caller) to mitigate scraping.

#### 2. `POST /api/users/prekeys`
**Purpose:** Upload prekey bundle
**Request:**
```json
{
  "identityKey": "base64-encoded-public-key",
  "signedPrekey": {
    "keyId": 1,
    "publicKey": "base64-encoded",
    "signature": "base64-encoded"
  },
  "onetimePrekeys": [
    { "keyId": 1, "publicKey": "base64-encoded" },
    { "keyId": 2, "publicKey": "base64-encoded" }
  ]
}
```
**Response:**
```json
{
  "success": true
}
```
**Authorization:** Required (Bearer token). The Worker extracts the user ID from `Authorization` and rejects payloads where the embedded IDs don't match (`403`). Uploads require `Content-Type: application/json` and are rate limited (5 uploads / hour) to control resource usage. Error responses follow:

```json
{
  "error": "invalid_token",
  "message": "Bearer token missing or expired"
}
```

### Modified Endpoints

#### 1. `POST /api/messages`
**Before:**
```json
{
  "id": "uuid",
  "fromUser": "user-id",
  "toUser": "user-id",
  "content": "Hello!",
  "timestamp": 1234567890,
  "status": "sent"
}
```

**After:**
```json
{
  "id": "uuid",
  "fromUser": "user-id",
  "toUser": "user-id",
  "encrypted_content": "base64-encrypted-data",
  "ratchet_header": "{\"ratchetKey\":\"...\",\"messageNumber\":5}",
  "timestamp": 1234567890,
  "status": "sent",
  "type": "text"
}
```

#### 2. `GET /api/messages/:userId`
**Before:** Returned plaintext messages
**After:** Returns encrypted messages (client must decrypt)

**Breaking Change:** YES - clients without E2EE support cannot read messages

---

## Performance Impact

### Encryption/Decryption Overhead

| Operation | Current | With E2EE | Overhead |
|-----------|---------|-----------|----------|
| Send Message | ~5ms | ~15ms | +10ms |
| Receive Message | ~2ms | ~12ms | +10ms |
| Session Establishment | N/A | ~300ms | First time only |
| Key Generation | N/A | ~500ms | On login |

### Memory Impact

| Component | Current | With E2EE | Increase |
|-----------|---------|-----------|----------|
| Browser Memory | ~30 MB | ~50 MB | +67% |
| IndexedDB Storage | 0 MB | ~5 MB (10k messages) | +5 MB |

### Network Impact

| Metric | Current | With E2EE | Change |
|--------|---------|-----------|--------|
| Message Size (avg) | 200 bytes | 500 bytes | +150% |
| Initial Load | 1 request | 3 requests | +2 (fetch prekeys) |

**Mitigation Strategies:**
1. **Web Workers:** Offload encryption to background thread
2. **Message Batching:** Encrypt multiple messages at once
3. **Session Caching:** Persist sessions in IndexedDB to avoid re-establishment
4. **Lazy Loading:** Only initialize E2EE when user opens a chat

---

## Security Impact

### Threat Model Changes

#### Before E2EE
| Threat | Severity | Mitigation |
|--------|----------|------------|
| Server compromise | **CRITICAL** | None - all messages readable |
| MITM attack | **HIGH** | TLS only |
| Database leak | **CRITICAL** | None - plaintext storage |

#### After E2EE
| Threat | Severity | Mitigation |
|--------|----------|------------|
| Server compromise | **LOW** | Encrypted messages unreadable |
| MITM attack | **MEDIUM** | X3DH + key verification |
| Database leak | **LOW** | Only encrypted data exposed |
| Client-side XSS | **CRITICAL** | ⚠️ NEW THREAT - can steal keys |
| Key storage compromise | **HIGH** | ⚠️ NEW THREAT - IndexedDB accessible |

### New Security Considerations

1. **Content Security Policy (CSP)**
   - **Current:** None
   - **Required:** Strict CSP to prevent XSS
   - **Impact:** May break existing inline scripts

2. **Subresource Integrity (SRI)**
   - **Current:** Not enforced
   - **Required:** SRI for all crypto libraries
   - **Impact:** Build process changes

3. **Key Storage Security**
   - **Risk:** IndexedDB is accessible to any script on the same origin
   - **Mitigation:** Consider wrapping keys with a user-derived key (password)

---

## User Experience Impact

### Positive Impacts
1. **Privacy Assurance:** Visual encryption indicators build trust
2. **Safety Numbers:** Users can verify contacts are authentic
3. **Message Security:** Peace of mind that messages are private

### Negative Impacts
1. **Initial Setup Delay:** 500ms key generation on first login
2. **Session Establishment:** 300ms delay on first message to new contact
3. **Decryption Errors:** Users may see "Unable to decrypt" for old messages
4. **Lost Keys = Lost History:** If user clears browser data, messages are unrecoverable (unless backup implemented)

### UX Mitigations
1. **Loading Indicators:** Show "Establishing secure connection..." during X3DH
2. **Onboarding:** Explain E2EE benefits during signup
3. **Backup Prompts:** Encourage users to backup keys
4. **Error Messaging:** Clear explanations for decryption failures

---

## Testing Impact

### New Test Requirements

#### 1. Unit Tests
**New Files:**
- `src/client/crypto/CryptoEngine.test.ts` - Test all crypto primitives
- `src/client/crypto/KeyManager.test.ts` - Test key generation and storage
- `src/client/crypto/RatchetEngine.test.ts` - Test Double Ratchet
- `src/client/crypto/X3DH.test.ts` - Test session establishment

**Test Coverage Required:** >90% for crypto code

#### 2. Integration Tests
- **Session Establishment:** Two users establish E2EE session
- **Message Exchange:** Alice sends encrypted message to Bob
- **Out-of-Order Messages:** Test message key skipping
- **Prekey Rotation:** Test prekey replenishment

#### 3. End-to-End Tests
- **Full Chat Flow:** Login → Send message → Receive message → Verify fingerprint
- **Multi-Device:** Same user on two devices

#### 4. Security Tests
- **Crypto Correctness:** Validate against Signal Protocol test vectors
- **Forward Secrecy:** Verify old messages cannot be decrypted after key deletion
- **Backward Secrecy:** Verify future messages cannot be decrypted after compromise

#### 5. Performance Tests
- **Encryption Speed:** Ensure < 20ms per message
- **Memory Leaks:** Verify no memory leaks during long sessions
- **Concurrent Sessions:** Test with 10+ active encrypted chats

**Estimated Test Code:** ~1,000 lines

---

## Deployment Impact

### Migration Checklist

#### Database Migration
1. **Create new tables:**
   - `user_identity_keys`
   - `user_prekeys`
   - `session_metadata`
   - `key_verification`

2. **Alter `messages` table:**
   - Add `encrypted_content` column
   - Add `ratchet_header` column
   - Rename `imageData` to `encrypted_image_data`
   - **Note:** Existing messages will be unreadable after migration

3. **Run migration script:**
   ```bash
   wrangler d1 execute whatsapp_clone_db --file=./migrations/002_add_e2ee.sql
   ```

#### Deployment Strategy

**Option 1: Big Bang (NOT RECOMMENDED)**
- Deploy all changes at once
- **Risk:** All users lose access to old messages immediately
- **Downtime:** Potential 30 minutes

**Option 2: Phased Rollout (RECOMMENDED)**

**Phase 1: Shadow Mode (Week 1)**
- Deploy E2EE code with feature flag OFF
- New tables created
- Dual-write: Save both plaintext and encrypted messages with `is_legacy = 1`
- Schedule nightly job to purge plaintext columns for rows older than 7 days while still keeping encrypted copies
- Monitor for errors

**Phase 2: Opt-In Beta (Week 2)**
- Enable E2EE for beta users
- Collect feedback on UX
- Monitor performance metrics

**Phase 3: Gradual Rollout (Week 3-4)**
- Enable for 25% of users → 50% → 75% → 100%
- Monitor error rates at each stage

**Phase 4: Cleanup (Week 5)**
- Stop writing plaintext messages
- Archive old plaintext messages (optional) and delete `content`/`imageData` data after successful archive
- Remove feature flag

#### Rollback Plan

**If critical issues arise:**
1. Disable E2EE feature flag
2. Revert to plaintext message storage
3. Investigate and fix issues
4. Re-enable when stable

**Data Loss Risk:** If rollback happens, encrypted messages sent during E2EE period may be lost.

---

## Risk Analysis

### Critical Risks

| Risk | Probability | Impact | Severity | Mitigation |
|------|-------------|--------|----------|------------|
| **Crypto Implementation Bug** | Medium | Critical | **HIGH** | Extensive testing, security audit, use test vectors |
| **Key Loss** | High | High | **HIGH** | Implement key backup (US12) |
| **Performance Degradation** | Medium | Medium | **MEDIUM** | Web Workers, performance testing |
| **Browser Compatibility** | Low | High | **MEDIUM** | Feature detection, polyfills |
| **IndexedDB Corruption** | Low | Critical | **MEDIUM** | Regular backups, error recovery |

### Medium Risks

| Risk | Probability | Impact | Severity | Mitigation |
|------|-------------|--------|----------|------------|
| **UX Confusion** | High | Low | **MEDIUM** | Clear onboarding, help documentation |
| **Session Sync Issues** | Medium | Medium | **MEDIUM** | Robust error handling, session reset |
| **Prekey Exhaustion** | Low | Medium | **LOW** | Automated prekey rotation |
| **Database Migration Failure** | Low | Medium | **LOW** | Test on staging, backup before migration |

### Technical Debt

| Item | Impact | Priority |
|------|--------|----------|
| No E2EE for group chats | High | P0 (Future - US13) |
| No key backup/restore | High | P1 (US12 - Phase 4) |
| No multi-device sync | Medium | P1 (US7 - Phase 4) |
| No message search (encrypted) | Low | P2 (US10 - Phase 4) |

---

## Migration Strategy

### Pre-Migration

1. **Announce to Users (1 week before):**
   ```
   "We're upgrading to end-to-end encryption for enhanced privacy.
   After [date], messages will be fully encrypted. Note: You may not
   be able to read messages sent before this date."
   ```

2. **Export Tool (optional):**
   - Provide users ability to export plaintext message history
   - One-time download before migration

3. **Backup Database:**
   ```bash
   wrangler d1 backup whatsapp_clone_db
   ```

### Migration Script

**File:** `migrations/002_add_e2ee.sql`

```sql
-- Backup existing messages to archive table
CREATE TABLE IF NOT EXISTS messages_archive AS SELECT * FROM messages;

-- Add new columns to messages table
ALTER TABLE messages ADD COLUMN encrypted_content TEXT;
ALTER TABLE messages ADD COLUMN ratchet_header TEXT;
ALTER TABLE messages ADD COLUMN encrypted_image_data TEXT;

-- Rename old content column (keep for rollback)
-- SQLite doesn't support column rename directly, so we keep both

-- Mark all existing messages as legacy (unencrypted)
ALTER TABLE messages ADD COLUMN is_legacy INTEGER DEFAULT 0;
UPDATE messages SET is_legacy = 1 WHERE encrypted_content IS NULL;

-- Create new E2EE tables
CREATE TABLE IF NOT EXISTS user_identity_keys (
  user_id TEXT PRIMARY KEY,
  identity_key TEXT NOT NULL,
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
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, key_id, prekey_type)
);

CREATE TABLE IF NOT EXISTS session_metadata (
  id TEXT PRIMARY KEY,
  user_a TEXT NOT NULL,
  user_b TEXT NOT NULL,
  established_at INTEGER NOT NULL,
  prekey_used TEXT,
  last_message_at INTEGER,
  FOREIGN KEY (user_a) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (user_b) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_a, user_b)
);

CREATE TABLE IF NOT EXISTS key_verification (
  id TEXT PRIMARY KEY,
  verifier_user_id TEXT NOT NULL,
  verified_user_id TEXT NOT NULL,
  verified_fingerprint TEXT NOT NULL,
  verified_at INTEGER NOT NULL,
  verification_method TEXT,
  FOREIGN KEY (verifier_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (verified_user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(verifier_user_id, verified_user_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_identity_keys_user ON user_identity_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_prekeys_user ON user_prekeys(user_id, prekey_type, is_used);
CREATE INDEX IF NOT EXISTS idx_messages_legacy ON messages(is_legacy);
```

### Post-Migration

1. **Verify Migration:**
   ```sql
   SELECT COUNT(*) FROM user_identity_keys;  -- Should be 0 initially
   SELECT COUNT(*) FROM user_prekeys;        -- Should be 0 initially
   SELECT COUNT(*) FROM messages WHERE is_legacy = 1;  -- Should match old message count
   ```

2. **Deploy Client Code:**
   - Push updated frontend with E2EE enabled
   - Monitor error rates

3. **Monitor Metrics:**
   - Key generation success rate
   - Session establishment success rate
   - Encryption/decryption error rate
   - Performance metrics (message send time)

---

## Effort Estimation

### Development Effort

| Component | Complexity | Estimated Hours | Developer Days |
|-----------|------------|-----------------|----------------|
| **Crypto Modules** | Very High | 40h | 5 days |
| CryptoEngine | High | 8h | 1 day |
| KeyManager | Very High | 12h | 1.5 days |
| RatchetEngine | Very High | 16h | 2 days |
| X3DH | High | 8h | 1 day |
| SessionStore | Medium | 6h | 0.75 days |
| **Backend Changes** | Medium | 16h | 2 days |
| API endpoints | Medium | 8h | 1 day |
| Database schema | Low | 4h | 0.5 days |
| ChatRoom updates | Medium | 4h | 0.5 days |
| **Frontend Integration** | High | 32h | 4 days |
| useE2EE hook | High | 12h | 1.5 days |
| UI components | Medium | 12h | 1.5 days |
| Message flow updates | Medium | 8h | 1 day |
| **Testing** | High | 40h | 5 days |
| Unit tests | High | 20h | 2.5 days |
| Integration tests | Medium | 12h | 1.5 days |
| E2E tests | Medium | 8h | 1 day |
| **Documentation** | Medium | 8h | 1 day |
| **Security Audit** | High | 16h | 2 days |
| **TOTAL** | - | **152h** | **19 days** |

**Assumptions:**
- 1 developer day = 8 hours
- Senior developer with cryptography experience
- Does not include QA time or code review time

**With Buffer (30%):** ~25 developer days = **5 weeks** for 1 developer

**Recommended:** 2 developers working in parallel = **3 weeks**

### Testing Effort

| Testing Type | Hours | Notes |
|--------------|-------|-------|
| Unit Testing | 20h | Automated, part of development |
| Integration Testing | 12h | Automated |
| Security Testing | 16h | Manual + automated |
| Performance Testing | 8h | Automated benchmarks |
| UAT (User Acceptance) | 16h | Beta users |
| **TOTAL** | **72h** | ~9 days |

---

## Dependency Analysis

### External Dependencies

| Dependency | Purpose | Risk | Mitigation |
|------------|---------|------|------------|
| **Web Crypto API** | Cryptographic operations | Low - browser native | Feature detection, polyfill for old browsers |
| **IndexedDB** | Key/session storage | Low - browser native | Fallback to localStorage (less secure) |
| **TextEncoder/Decoder** | String ↔ Uint8Array | Low - browser native | Polyfill for IE11 (if needed) |

**No external crypto libraries required** - all using Web Crypto API.

### Browser Support

| Browser | Version | Support | Notes |
|---------|---------|---------|-------|
| Chrome | 60+ | ✅ Full | Web Crypto fully supported |
| Firefox | 55+ | ✅ Full | Web Crypto fully supported |
| Safari | 11+ | ✅ Full | Web Crypto fully supported |
| Edge | 79+ | ✅ Full | Chromium-based |
| IE 11 | - | ❌ None | No Web Crypto support |

**Recommendation:** Drop IE11 support or provide non-E2EE fallback.

---

## Monitoring and Observability

### New Metrics to Track

#### Client-Side Metrics
```typescript
// Track in Analytics
{
  event: 'e2ee_key_generation',
  duration_ms: 450,
  success: true,
}

{
  event: 'e2ee_session_establishment',
  recipient_id: 'user-123',
  duration_ms: 320,
  success: true,
}

{
  event: 'e2ee_message_encryption',
  duration_ms: 12,
  success: true,
}

{
  event: 'e2ee_message_decryption',
  duration_ms: 10,
  success: false,
  error: 'Invalid ratchet header',
}
```

#### Server-Side Metrics
```
- Prekey bundle requests/sec
- Prekey exhaustion rate (users with < 20 prekeys)
- Encrypted message throughput
- Message size distribution (monitor overhead)
```

### Error Monitoring

**Critical Errors to Alert On:**
1. Decryption failure rate > 5%
2. Session establishment failure rate > 10%
3. Prekey exhaustion (any user with 0 prekeys)
4. IndexedDB write failures

---

## Compliance and Legal

### Data Protection Impact

| Aspect | Before E2EE | After E2EE |
|--------|-------------|------------|
| **GDPR Article 32** (Security) | ❌ Plaintext storage | ✅ Encrypted at rest and in transit |
| **Data Breach Impact** | HIGH - all messages exposed | LOW - encrypted data useless |
| **Right to Erasure** | Easy - delete from DB | Same - delete encrypted data |
| **Law Enforcement Requests** | Can provide plaintext | Cannot decrypt (no keys) |

### Legal Considerations

**Positive:**
- Improved compliance with privacy regulations
- Reduced liability in case of data breach
- Competitive advantage in privacy-focused markets

**Risks:**
- Some jurisdictions may require lawful access to communications
- May complicate compliance with court orders
- Consider legal review before deployment

---

## Recommendations

### Must Do (P0)
1. ✅ Implement all Phase 1-2 user stories (US1-US6)
2. ✅ Comprehensive security testing and code review
3. ✅ Phased rollout with feature flags
4. ✅ Clear user communication about changes
5. ✅ Rollback plan ready

### Should Do (P1)
1. ⚠️ Web Workers for crypto operations (performance)
2. ⚠️ Key backup/restore (US12) - implement soon after launch
3. ⚠️ Multi-device support (US7) - high user demand
4. ⚠️ Security audit by external firm
5. ⚠️ Performance monitoring and optimization

### Nice to Have (P2)
1. 💡 Animated loading states during session establishment
2. 💡 QR code fingerprint verification
3. 💡 In-app tutorial explaining E2EE
4. 💡 Message search (US10)
5. 💡 Export/import session backups

---

## Appendix A: Files Impacted Summary

### Backend Files (3 modified)
1. ✏️ `src/worker/index.ts` - Add prekey endpoints (~150 lines)
2. ✏️ `src/worker/ChatRoom.ts` - Update message handling (~50 lines)
3. ✏️ `src/worker/types.ts` - Update interfaces (~20 lines)

### Frontend Files (4 modified + 12 new)
**Modified:**
1. ✏️ `src/client/App.tsx` - E2EE initialization (~80 lines)
2. ✏️ `src/client/components/Chat.tsx` - Pass E2EE props (~20 lines)
3. ✏️ `src/client/components/ChatWindow.tsx` - Encryption status UI (~40 lines)
4. ✏️ `src/client/components/MessageList.tsx` - Decryption error handling (~10 lines)

**New:**
5. ➕ `src/client/crypto/CryptoEngine.ts` (~200 lines)
6. ➕ `src/client/crypto/KeyManager.ts` (~250 lines)
7. ➕ `src/client/crypto/RatchetEngine.ts` (~350 lines)
8. ➕ `src/client/crypto/X3DH.ts` (~200 lines)
9. ➕ `src/client/crypto/SessionStore.ts` (~150 lines)
10. ➕ `src/client/crypto/types.ts` (~100 lines)
11. ➕ `src/client/hooks/useE2EE.ts` (~300 lines)
12. ➕ `src/client/storage/KeyStorage.ts` (~150 lines)
13. ➕ `src/client/storage/SessionStorage.ts` (~150 lines)
14. ➕ `src/client/storage/db.ts` (~100 lines)
15. ➕ `src/client/components/FingerprintModal.tsx` (~150 lines)
16. ➕ `src/client/components/EncryptionBadge.tsx` (~50 lines)

### Database Files (1 modified, 1 new)
1. ✏️ `schema.sql` - Add E2EE tables (~80 lines)
2. ➕ `migrations/002_add_e2ee.sql` - Migration script (~120 lines)

### CSS Files (1 modified)
1. ✏️ `src/client/styles.css` - Add E2EE UI styles (~100 lines)

### Test Files (12 new)
1. ➕ `src/client/crypto/CryptoEngine.test.ts`
2. ➕ `src/client/crypto/KeyManager.test.ts`
3. ➕ `src/client/crypto/RatchetEngine.test.ts`
4. ➕ `src/client/crypto/X3DH.test.ts`
5. ➕ (8 more test files)

**Total Files Impacted:** 29 files
**Total New Code:** ~2,500 lines
**Total Modified Code:** ~370 lines

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **X3DH** | Extended Triple Diffie-Hellman - Asynchronous key agreement protocol |
| **Double Ratchet** | Encryption protocol providing forward and backward secrecy |
| **Prekey** | Public key uploaded to server for asynchronous key exchange |
| **Signed Prekey** | Long-lived prekey signed by identity key, rotated weekly |
| **One-time Prekey** | Single-use prekey consumed during session establishment |
| **Ratchet State** | Current state of the Double Ratchet algorithm (chain keys, message numbers) |
| **Message Key** | Ephemeral key used to encrypt a single message |
| **Chain Key** | Key used to derive message keys via KDF |
| **DH Ratchet** | Diffie-Hellman key exchange step in Double Ratchet |
| **Symmetric Ratchet** | KDF-based key derivation step in Double Ratchet |
| **Forward Secrecy** | Past messages remain secure if current keys are compromised |
| **Backward Secrecy** | Future messages remain secure after key compromise (break-in recovery) |
| **Fingerprint** | SHA-256 hash of identity public key, displayed for verification |

---

**End of Impact Analysis**

**Next Steps:**
1. Review this analysis with the development team
2. Get stakeholder approval for implementation
3. Create detailed task breakdown in issue tracker
4. Begin Phase 1 development (Core Encryption)

**Document Maintained By:** Engineering Team
**Last Updated:** 2025-12-16
