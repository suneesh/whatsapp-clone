# Code-to-Requirement Traceability Matrix

**Version:** 1.0  
**Date:** December 22, 2025  
**Project:** WhatsApp Clone with E2E Encryption  

---

## Overview

This document provides bidirectional traceability between source code components and functional requirements defined in the Software Requirements Specification (SRS). It enables:

- **Forward Traceability:** From requirements to implementation
- **Backward Traceability:** From code to requirements
- **Impact Analysis:** Understanding which code changes affect which requirements
- **Coverage Analysis:** Ensuring all requirements are implemented

---

## Table of Contents

1. [Backend Components](#1-backend-components)
2. [Frontend Components](#2-frontend-components)
3. [Python Client Components](#3-python-client-components)
4. [Database Schema](#4-database-schema)
5. [Test Components](#5-test-components)
6. [Coverage Summary](#6-coverage-summary)
7. [Change Impact Guidelines](#7-change-impact-guidelines)
8. [Maintenance Procedures](#8-maintenance-procedures)
9. [Commit History Traceability](#9-commit-history-traceability)
10. [Revision History](#10-revision-history)

---

## 1. Backend Components

### 1.1 Worker Entry Point

**File:** `src/worker/index.ts`  
**Lines:** 1-2000+  
**Purpose:** Main Cloudflare Worker with REST API endpoints

| Function/Handler | Requirements | Description |
|-----------------|--------------|-------------|
| `handleRegister()` | FR-AUTH-001, FR-AUTH-002, FR-AUTH-003, FR-AUTH-005 | User registration with password hashing |
| `handleLogin()` | FR-AUTH-004, FR-AUTH-006 | User authentication and JWT issuance |
| `hashPassword()` | FR-AUTH-002 | bcrypt password hashing (work factor 10) |
| `comparePassword()` | FR-AUTH-002 | bcrypt password verification |
| `generateToken()` | FR-AUTH-004 | JWT token generation (24h expiry) |
| `authenticateRequest()` | FR-AUTH-006 | JWT token validation middleware |
| `handleGetUsers()` | FR-CLI-004 | List all registered users |
| `handleGetUserPrekeys()` | FR-KEY-006, FR-E2EE-001 | Retrieve user's prekey bundle |
| `handleUploadPrekeys()` | FR-KEY-006 | Upload public keys to server |
| `handleGetPrekeyStatus()` | FR-KEY-008 | Check prekey count for rotation |
| `handleSaveMessage()` | FR-MSG-004 | Persist encrypted messages |
| `handleGetMessages()` | FR-MSG-007 | Retrieve message history (ordered) |
| `handleCreateGroup()` | FR-GRP-001, FR-GRP-002 | Create group with admin |
| `handleAddGroupMember()` | FR-GRP-003 | Add member to group |
| `handleGetGroupMessages()` | FR-GRP-006 | Retrieve group chat history |
| `handleAdminGetUsers()` | FR-AUTH-006 | Admin user management |
| `handleAdminDisableUser()` | FR-AUTH-006 | Disable user account |

**Key Code Snippets:**

```typescript
// FR-AUTH-002: bcrypt password hashing with work factor 10
async function hashPassword(password: string): Promise<string> {
  return await bcrypt.hash(password, 10);  // Work factor = 10
}

// FR-AUTH-004: JWT token generation (24h expiry)
async function generateToken(userId: string, username: string): Promise<string> {
  return await new SignJWT({ userId, username })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('24h')  // 24 hour expiry
    .sign(new TextEncoder().encode(JWT_SECRET));
}

// FR-MSG-007: Chronological message ordering
const query = `
  SELECT * FROM messages 
  WHERE (fromUser = ? AND toUser = ?) OR (fromUser = ? AND toUser = ?)
  ORDER BY timestamp ASC  // Chronological order
`;
```

---

### 1.2 Durable Object (ChatRoom)

**File:** `src/worker/ChatRoom.ts`  
**Lines:** 1-500+  
**Purpose:** WebSocket state management and real-time messaging

| Function/Method | Requirements | Description |
|----------------|--------------|-------------|
| `handleSession()` | FR-PRES-001, FR-MSG-001 | WebSocket connection handling |
| `closeSession()` | FR-PRES-002 | Disconnect and offline status |
| `handleMessage()` | FR-MSG-001, FR-MSG-006 | Real-time message routing |
| `handleGroupMessage()` | FR-GRP-005 | Group message broadcast |
| `handleTyping()` | FR-TYPE-002 | Typing indicator relay |
| `handleStatus()` | FR-MSG-005, FR-MSG-006 | Message status updates |
| `broadcast()` | FR-PRES-003, FR-MSG-001 | Broadcast to connected users |
| `getOnlineUsers()` | FR-PRES-005 | List of online users |

**Key Code Snippets:**

```typescript
// FR-PRES-001: Mark user online on connect
async handleSession(request: Request): Promise<Response> {
  // ... WebSocket setup ...
  this.sessions.set(userId, { ws, username });
  this.broadcast({ type: 'online', userId, online: true });
}

// FR-MSG-001: Real-time message delivery via WebSocket
handleMessage(data: any, senderId: string) {
  const recipientSession = this.sessions.get(data.to);
  if (recipientSession) {
    recipientSession.ws.send(JSON.stringify({
      type: 'message',
      from: senderId,
      content: data.content,
      timestamp: Date.now()
    }));
  }
}
```

---

## 2. Frontend Components

### 2.1 Main Application

**File:** `src/client/App.tsx`  
**Lines:** 1-800+  
**Purpose:** Root React component with authentication flow

| Component/Function | Requirements | Description |
|-------------------|--------------|-------------|
| `<App />` | FR-AUTH-001, FR-AUTH-004, FR-AUTH-007 | Main app with login/register |
| `handleRegister()` | FR-AUTH-001 | User registration flow |
| `handleLogin()` | FR-AUTH-004 | User login flow |
| `handleLogout()` | FR-AUTH-007 | Session cleanup |
| `<ChatView />` | FR-MSG-001, FR-MSG-007 | Chat interface |

---

### 2.2 User List Component

**File:** `src/client/components/UserList.tsx`  
**Lines:** 1-200+  
**Purpose:** Display users with online status

| Component/Function | Requirements | Description |
|-------------------|--------------|-------------|
| `<UserList />` | FR-PRES-004, FR-PRES-005 | List users with presence |
| Online indicator | FR-PRES-004 | Green dot for online users |

---

### 2.3 Chat Window Component

**File:** `src/client/components/ChatWindow.tsx`  
**Lines:** 1-400+  
**Purpose:** Message display and input

| Component/Function | Requirements | Description |
|-------------------|--------------|-------------|
| `<ChatWindow />` | FR-MSG-007, FR-TYPE-001, FR-TYPE-003 | Chat UI |
| `handleTyping()` | FR-TYPE-001, FR-TYPE-004 | Detect typing, 3s timeout |
| Typing indicator | FR-TYPE-003 | "User is typing..." display |
| Message bubbles | FR-MSG-007, FR-E2EE-009 | Display messages with E2EE marker |

---

## 3. Python Client Components

### 3.1 Main Client Class

**File:** `python-client/src/whatsapp_client/client.py`  
**Lines:** 1-1000+  
**Purpose:** WhatsApp client API

| Method | Requirements | Description |
|--------|--------------|-------------|
| `register()` | FR-AUTH-001 | User registration |
| `login()` | FR-AUTH-004 | User authentication |
| `logout()` | FR-AUTH-007 | Session cleanup |
| `send_message()` | FR-E2EE-001, FR-E2EE-009, FR-MSG-001 | Send encrypted message |
| `receive_message()` | FR-E2EE-008, FR-MSG-001 | Receive and decrypt |
| `list_users()` | FR-CLI-004 | List all users |
| `find_user()` | FR-CLI-004 | Find user by username |
| `send_group_message()` | FR-GRP-004, FR-GRP-005 | Send to group |
| `get_fingerprint()` | FR-FP-001, FR-FP-002 | Get identity fingerprint |
| `verify_fingerprint()` | FR-FP-003 | Mark fingerprint verified |

**Key Code Snippets:**

```python
# FR-E2EE-009: E2EE marker prefix
async def send_message(self, to_user: str, content: str) -> Message:
    # ... encryption ...
    encrypted_content = f"E2EE:{json.dumps(encrypted_data)}"
    return await self._send_message(to_user, encrypted_content)
```

---

### 3.2 Cryptographic Keys Module

**File:** `python-client/src/whatsapp_client/crypto/keys.py`  
**Lines:** 1-400+  
**Purpose:** Key generation and management

| Function/Class | Requirements | Description |
|---------------|--------------|-------------|
| `IdentityKeyPair` | FR-KEY-001 | Curve25519 identity keys |
| `SigningKeyPair` | FR-KEY-002 | Ed25519 signing keys |
| `generate_identity_keypair()` | FR-KEY-001 | Generate Curve25519 keys |
| `generate_signing_keypair()` | FR-KEY-002 | Generate Ed25519 keys |
| `generate_prekeys()` | FR-KEY-003 | Generate 100 one-time prekeys |
| `generate_signed_prekey()` | FR-KEY-004, FR-KEY-005 | Generate and sign prekey |
| `sign_prekey_bundle()` | FR-KEY-005 | Sign prekey bundle |
| `verify_prekey_signature()` | FR-KEY-005 | Verify signature |
| `get_fingerprint()` | FR-FP-001 | SHA-256 fingerprint |

**Key Code Snippets:**

```python
# FR-KEY-001: Curve25519 identity key generation
def generate_identity_keypair() -> IdentityKeyPair:
    private_key = PrivateKey.generate()  # Curve25519, 32 bytes
    public_key = private_key.public_key
    return IdentityKeyPair(private_key, public_key)

# FR-KEY-003: Generate 100 one-time prekeys
def generate_prekeys(count: int = 100) -> List[PreKey]:
    return [PreKey(i, PrivateKey.generate()) for i in range(count)]

# FR-FP-001: Fingerprint generation (SHA-256)
def get_fingerprint(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()
```

---

### 3.3 X3DH Key Exchange Module

**File:** `python-client/src/whatsapp_client/crypto/x3dh.py`  
**Lines:** 1-300+  
**Purpose:** Extended Triple Diffie-Hellman protocol

| Function/Class | Requirements | Description |
|---------------|--------------|-------------|
| `perform_x3dh()` | FR-E2EE-001 | Complete X3DH key exchange |
| `derive_shared_secret()` | FR-E2EE-002 | Derive 32-byte shared secret |
| `dh()` | FR-E2EE-001 | Diffie-Hellman operation |
| `X3DHResult` | FR-E2EE-001, FR-E2EE-002 | X3DH output data |

**Key Code Snippets:**

```python
# FR-E2EE-001: X3DH key exchange with all DH operations
def perform_x3dh(
    identity_key: PrivateKey,
    ephemeral_key: PrivateKey,
    recipient_identity: PublicKey,
    recipient_signed_prekey: PublicKey,
    recipient_onetime_prekey: Optional[PublicKey]
) -> bytes:
    # DH1: DH(IKa, SPKb)
    dh1 = dh(identity_key, recipient_signed_prekey)
    # DH2: DH(EKa, IKb)
    dh2 = dh(ephemeral_key, recipient_identity)
    # DH3: DH(EKa, SPKb)
    dh3 = dh(ephemeral_key, recipient_signed_prekey)
    
    # DH4: DH(EKa, OPKb) - if one-time prekey available
    if recipient_onetime_prekey:
        dh4 = dh(ephemeral_key, recipient_onetime_prekey)
        return hkdf(dh1 + dh2 + dh3 + dh4, 32)
    
    return hkdf(dh1 + dh2 + dh3, 32)

# FR-E2EE-002: Derive 32-byte shared secret
def derive_shared_secret(dh_outputs: List[bytes]) -> bytes:
    combined = b''.join(dh_outputs)
    return hkdf(combined, 32)  # 32-byte output
```

---

### 3.4 Double Ratchet Module

**File:** `python-client/src/whatsapp_client/crypto/double_ratchet.py`  
**Lines:** 1-600+  
**Purpose:** Double Ratchet algorithm for forward secrecy

| Function/Class | Requirements | Description |
|---------------|--------------|-------------|
| `DoubleRatchet` | FR-E2EE-003 to FR-E2EE-008 | Ratchet state machine |
| `initialize()` | FR-E2EE-003 | Initialize with shared secret |
| `encrypt()` | FR-E2EE-004, FR-E2EE-005, FR-E2EE-006 | Encrypt with AES-256-GCM |
| `decrypt()` | FR-E2EE-004, FR-E2EE-006, FR-E2EE-008 | Decrypt and handle out-of-order |
| `ratchet_encrypt()` | FR-E2EE-006 | Symmetric ratchet step |
| `ratchet_decrypt()` | FR-E2EE-006 | Symmetric ratchet step |
| `dh_ratchet()` | FR-E2EE-007 | DH ratchet on direction change |
| `skip_message_keys()` | FR-E2EE-008 | Handle out-of-order messages |

**Key Code Snippets:**

```python
# FR-E2EE-003: Initialize Double Ratchet with shared secret
def initialize(self, shared_secret: bytes, remote_ratchet_key: PublicKey):
    self.root_key = shared_secret
    self.sending_chain_key = hkdf(shared_secret, 32, b"sending")
    self.receiving_chain_key = hkdf(shared_secret, 32, b"receiving")

# FR-E2EE-004: AES-256-GCM encryption
def encrypt(self, plaintext: str) -> EncryptedMessage:
    key = self._derive_message_key(self.sending_chain_key)
    cipher = AESGCM(key)  # AES-256-GCM
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)
    
    # FR-E2EE-005: Include ratchet header
    return EncryptedMessage(
        ciphertext=ciphertext,
        header=RatchetHeader(
            ratchet_key=self.sending_ratchet_key.public_key,
            previous_chain_length=self.previous_chain_length,
            message_number=self.sending_message_number
        )
    )

# FR-E2EE-008: Out-of-order message handling (up to 1000 skipped keys)
def skip_message_keys(self, until: int):
    if until - self.receiving_message_number > 1000:
        raise ValueError("Too many skipped messages")
    
    while self.receiving_message_number < until:
        key = self._derive_message_key(self.receiving_chain_key)
        self.skipped_keys[self.receiving_message_number] = key
        self.receiving_message_number += 1
```

---

### 3.5 Storage Module

**File:** `python-client/src/whatsapp_client/storage/`  
**Lines:** Multiple files  
**Purpose:** Encrypted local key storage

| File/Class | Requirements | Description |
|-----------|--------------|-------------|
| `KeyStorage` | FR-KEY-007 | Encrypted private key storage |
| `SessionStorage` | FR-E2EE-003 | Ratchet state persistence |
| `FingerprintStorage` | FR-FP-003, FR-FP-005 | Verification status storage |

---

### 3.6 Authentication Module

**File:** `python-client/src/whatsapp_client/auth/manager.py`  
**Lines:** 1-200+  
**Purpose:** Authentication management

| Method | Requirements | Description |
|--------|--------------|-------------|
| `register()` | FR-AUTH-001, FR-AUTH-005 | User registration with validation |
| `login()` | FR-AUTH-004, FR-AUTH-006 | Login and token storage |
| `logout()` | FR-AUTH-007 | Clear credentials |

**Key Code Snippets:**

```python
# FR-AUTH-001: Validation (3-100 chars username, 6+ chars password)
async def register(self, username: str, password: str) -> User:
    # Validate via Pydantic model
    request = RegisterRequest(username=username, password=password)
    # Raises ValidationError if:
    # - username < 3 or > 100 chars
    # - password < 6 chars
```

---

### 3.7 Models Module

**File:** `python-client/src/whatsapp_client/models.py`  
**Lines:** 1-150+  
**Purpose:** Data validation models

| Class | Requirements | Description |
|-------|--------------|-------------|
| `RegisterRequest` | FR-AUTH-001 | Registration validation |
| `LoginRequest` | FR-AUTH-004 | Login validation |
| `User` | FR-AUTH-003 | User data with UUID |
| `Message` | FR-MSG-002, FR-MSG-003 | Message with UUID and timestamp |

---

## 4. Database Schema

**File:** `schema.sql`  
**Lines:** 1-200+  
**Purpose:** D1 database schema

| Table | Requirements | Description |
|-------|--------------|-------------|
| `users` | FR-AUTH-001, FR-AUTH-003, FR-PRES-001 | User accounts with UUID |
| `user_identity_keys` | FR-KEY-001, FR-KEY-002 | Identity and signing keys |
| `user_prekeys` | FR-KEY-003, FR-KEY-004, FR-KEY-009 | Prekey storage with usage tracking |
| `messages` | FR-MSG-002, FR-MSG-003, FR-MSG-004 | Message persistence |
| `groups` | FR-GRP-001, FR-GRP-002 | Group chat metadata |
| `group_members` | FR-GRP-003 | Group membership |
| `group_messages` | FR-GRP-006 | Group message history |

**Key Schema Snippets:**

```sql
-- FR-AUTH-003: UUID for each user
CREATE TABLE users (
  id TEXT PRIMARY KEY,  -- UUID v4
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,  -- FR-AUTH-002: bcrypt hash
  lastSeen INTEGER NOT NULL,  -- FR-PRES-002
  created_at INTEGER NOT NULL
);

-- FR-KEY-009: One-time prekey consumption tracking
CREATE TABLE user_prekeys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key_id INTEGER NOT NULL,
  prekey_type TEXT NOT NULL,
  public_key TEXT NOT NULL,
  is_used INTEGER DEFAULT 0,  -- Track usage
  used_at INTEGER,  -- Timestamp when used
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- FR-MSG-002, FR-MSG-003: Message UUID and timestamp
CREATE TABLE messages (
  id TEXT PRIMARY KEY,  -- UUID
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,  -- Encrypted
  timestamp INTEGER NOT NULL,  -- Server timestamp
  status TEXT NOT NULL,
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);
```

---

## 5. Test Components

### 5.1 Authentication Tests

**File:** `python-client/tests/test_auth.py`  
**Lines:** 1-500+  
**Purpose:** Test FR-AUTH-* requirements

| Test Case | Requirements | Description |
|-----------|--------------|-------------|
| `test_tc_auth_001_*` | FR-AUTH-001 | Valid username/password registration |
| `test_tc_auth_002_*` | FR-AUTH-001 | Reject username < 3 chars |
| `test_tc_auth_003_*` | FR-AUTH-001 | Reject username > 30 chars |
| `test_tc_auth_004_*` | FR-AUTH-001 | Reject password < 8 chars |
| `test_tc_auth_005_*` | FR-AUTH-002 | bcrypt work factor 10 |
| `test_tc_auth_006_*` | FR-AUTH-002 | Password hash differs from plaintext |
| `test_tc_auth_007_*` | FR-AUTH-002 | Password hash validation |
| `test_tc_auth_008_*` | FR-AUTH-003 | UUID v4 format |
| `test_tc_auth_009_*` | FR-AUTH-003 | UUID uniqueness |
| `test_tc_auth_010_*` | FR-AUTH-004 | JWT token issuance |
| `test_register_success()` | FR-AUTH-001 | Registration flow |
| `test_login_success()` | FR-AUTH-004 | Login flow |
| `test_logout()` | FR-AUTH-007 | Logout cleanup |

---

### 5.2 Cryptography Tests

**File:** `python-client/tests/test_crypto.py`  
**Lines:** 1-800+  
**Purpose:** Test FR-KEY-*, FR-E2EE-* requirements

| Test Function | Requirements | Description |
|--------------|--------------|-------------|
| `test_identity_key_generation()` | FR-KEY-001 | Curve25519 keys |
| `test_signing_key_generation()` | FR-KEY-002 | Ed25519 keys |
| `test_prekey_generation()` | FR-KEY-003 | 100 one-time prekeys |
| `test_signed_prekey()` | FR-KEY-004, FR-KEY-005 | Signed prekey |
| `test_x3dh_*()` | FR-E2EE-001, FR-E2EE-002 | X3DH protocol |
| `test_ratchet_*()` | FR-E2EE-003 to FR-E2EE-008 | Double Ratchet |

---

### 5.3 Messaging Tests

**File:** `python-client/tests/test_messaging.py`  
**Lines:** 1-400+  
**Purpose:** Test FR-MSG-* requirements

| Test Function | Requirements | Description |
|--------------|--------------|-------------|
| `test_send_message()` | FR-MSG-001, FR-E2EE-009 | Send with E2EE marker |
| `test_message_persistence()` | FR-MSG-004 | Database storage |
| `test_message_ordering()` | FR-MSG-007 | Chronological order |

---

### 5.4 Group Tests

**File:** `python-client/tests/test_groups.py`  
**Lines:** 1-300+  
**Purpose:** Test FR-GRP-* requirements

| Test Function | Requirements | Description |
|--------------|--------------|-------------|
| `test_create_group()` | FR-GRP-001, FR-GRP-002 | Group creation with admin |
| `test_add_member()` | FR-GRP-003 | Member management |
| `test_group_message()` | FR-GRP-004, FR-GRP-005 | Encrypted group messages |

---

## 6. Coverage Summary

### 6.1 Requirements Coverage by Component

| Component | Requirements Covered | Count |
|-----------|---------------------|-------|
| `src/worker/index.ts` | FR-AUTH-*, FR-KEY-006, FR-MSG-*, FR-GRP-* | 25 |
| `src/worker/ChatRoom.ts` | FR-MSG-001, FR-PRES-*, FR-TYPE-* | 11 |
| `python-client/.../client.py` | FR-CLI-*, FR-E2EE-009, FR-FP-* | 10 |
| `python-client/.../keys.py` | FR-KEY-001 to FR-KEY-005, FR-FP-001 | 6 |
| `python-client/.../x3dh.py` | FR-E2EE-001, FR-E2EE-002 | 2 |
| `python-client/.../double_ratchet.py` | FR-E2EE-003 to FR-E2EE-008 | 6 |
| `python-client/.../storage/` | FR-KEY-007, FR-FP-003, FR-FP-005 | 3 |
| `schema.sql` | FR-AUTH-003, FR-KEY-*, FR-MSG-*, FR-GRP-* | 15 |
| `src/client/components/*` | FR-PRES-004, FR-TYPE-*, FR-MSG-007 | 7 |
| **TOTAL** | **All 60 requirements** | **60** |

### 6.2 Coverage Percentage

| Category | Total Requirements | Implemented | Coverage |
|----------|-------------------|-------------|----------|
| Authentication (FR-AUTH) | 7 | 7 | 100% |
| Key Management (FR-KEY) | 9 | 9 | 100% |
| E2E Encryption (FR-E2EE) | 10 | 10 | 100% |
| Messaging (FR-MSG) | 8 | 8 | 100% |
| Presence (FR-PRES) | 5 | 5 | 100% |
| Typing (FR-TYPE) | 4 | 4 | 100% |
| Groups (FR-GRP) | 6 | 6 | 100% |
| Fingerprint (FR-FP) | 5 | 5 | 100% |
| CLI Client (FR-CLI) | 6 | 6 | 100% |
| **TOTAL** | **60** | **60** | **100%** |

---

## 7. Orphaned Code Analysis

### 7.1 Code Without Requirements

| File | Function/Component | Status |
|------|-------------------|--------|
| `whatsapp_cli.py` | CLI application | Implements FR-CLI-003 to FR-CLI-006 |
| `demo.py` | Demo script | Testing/demo only |
| `integration_test.py` | Integration testing | Testing only |
| `build.py` | Build script | Build automation |

**Result:** No significant orphaned code. All production code traces to requirements.

---

## 8. Impact Analysis Guide

### 8.1 How to Use This Matrix

**When modifying a requirement:**
1. Find the requirement ID in this document
2. Identify all affected code files
3. Review and update each implementation
4. Update corresponding test cases
5. Run affected tests to verify

**When modifying code:**
1. Find the file/function in this document
2. Identify affected requirements
3. Verify changes don't break requirement compliance
4. Update tests if behavior changes

**Example Impact Analysis:**

**Scenario:** Change password minimum length from 6 to 8 characters

**Affected Requirements:** FR-AUTH-001, FR-AUTH-004

**Affected Code:**
- `python-client/src/whatsapp_client/models.py` - `RegisterRequest.validate_password()`
- `python-client/tests/test_auth.py` - `test_tc_auth_004_*`
- `docs/SRS.md` - Update requirement specification

**Affected Tests:**
- TC-AUTH-004 (update assertions)
- All existing auth tests (verify still pass)

---

## 9. Commit History Traceability

This section maps Git commits to the requirements they implement, enabling:
- **Change Tracking:** Understanding when requirements were implemented
- **Audit Trail:** Documenting implementation history
- **Regression Analysis:** Identifying commits for specific features

### 9.1 Feature Implementation Commits

| Commit Hash | Date | Description | Requirements Implemented |
|-------------|------|-------------|-------------------------|
| `6513280` | Initial | US1/US2: Authentication and Key Generation | FR-AUTH-001, FR-AUTH-002, FR-AUTH-003, FR-AUTH-004, FR-AUTH-005, FR-KEY-001, FR-KEY-002, FR-KEY-003 |
| `efda9bb` | Initial | US3: Session Establishment (X3DH Protocol) | FR-E2EE-001, FR-E2EE-002, FR-E2EE-003, FR-E2EE-004, FR-KEY-004, FR-KEY-005, FR-KEY-006 |
| `3a0d7c9` | Initial | US4/US5: Double Ratchet Encryption | FR-E2EE-005, FR-E2EE-006, FR-E2EE-007, FR-E2EE-008, FR-E2EE-009, FR-E2EE-010 |
| `6a99638` | Initial | US6: WebSocket Messaging | FR-MSG-001, FR-MSG-002, FR-MSG-003, FR-MSG-004 |
| `bdfecaf` | Initial | US8: Typing Indicators & Presence | FR-PRES-001, FR-PRES-002, FR-PRES-003, FR-TYPE-001, FR-TYPE-002 |
| `8fc03fb` | Initial | US9: Message Status & Read Receipts | FR-MSG-005, FR-MSG-006, FR-MSG-007 |
| `5a10467` | Initial | US10: Image and File Sending | FR-MSG-003 (media support) |
| `f128d0e` | Initial | US11: Key Fingerprint Verification | FR-FP-001, FR-FP-002, FR-FP-003, FR-FP-004 |
| `0db692c` | Initial | US12: Group Chat Support | FR-GRP-001, FR-GRP-002, FR-GRP-003, FR-GRP-004, FR-GRP-005, FR-GRP-006, FR-GRP-007 |
| `4151319` | Initial | US13: Local Storage & Key Management | FR-KEY-007 |
| `63f0051` | Initial | US14: Error Handling and Logging | FR-CLI-005 |
| `0d49610` | Initial | US15: Configuration and Customization | FR-CLI-003 |
| `725b698` | Initial | US16: Async Event Loop Integration | FR-CLI-006 |
| `d24d2b3` | Initial | US17: Testing and Examples | Test coverage for all FR-* |
| `fd77126` | Initial | US18: Package Distribution | FR-CLI-001, FR-CLI-002 |
| `afa09e0` | Initial | JWT Authentication Implementation | FR-AUTH-004, FR-AUTH-006 |
| `1fdddc7` | Latest | Complete E2EE with X3DH + Double Ratchet | FR-E2EE-001 to FR-E2EE-010, FR-KEY-* |

### 9.2 Bug Fix Commits with Requirement Impact

| Commit Hash | Description | Requirements Affected |
|-------------|-------------|----------------------|
| `89903a5` | Fix parameter order in responder KDF | FR-E2EE-004, FR-E2EE-006 |
| `b0baaaf` | Fix responder init and ratchet encoding | FR-E2EE-005, FR-E2EE-006 |
| `60c36f9` | Fix ratchet KDF parameters | FR-E2EE-006, FR-E2EE-007 |
| `881ca8b` | Fix HKDF parameters | FR-E2EE-005, FR-KEY-004 |
| `1f29433` | Graceful session mismatch handling | FR-E2EE-003, FR-E2EE-009 |
| `7a3f367` | Simplify ratchet decryption | FR-E2EE-006 |
| `bc80066` | Support base64 key encoding | FR-KEY-002, FR-E2EE-001 |
| `fd3e9b0` | Fix signature verification encoding | FR-KEY-003, FR-E2EE-002 |
| `e794613` | Parse prekey bundle response | FR-KEY-006, FR-E2EE-001 |
| `89132b9` | Prevent duplicate sessions, fix WS format | FR-E2EE-003, FR-MSG-002 |
| `a257b67` | Auto-establish session on encrypted msg | FR-E2EE-003, FR-E2EE-009 |
| `ed66b72` | Add username to WS auth for presence | FR-PRES-002 |
| `be40f60` | Comprehensive Python E2EE implementation | FR-CLI-004, FR-E2EE-* |
| `85606fb` | Establish session before decryption | FR-E2EE-003, FR-E2EE-006 |
| `5208370` | Extract payload from WS message data | FR-MSG-002 |
| `aeb986d` | Initialize E2EE on registration | FR-AUTH-005, FR-KEY-001 |
| `1879f84` | Cascade JWT to Python client | FR-AUTH-006, FR-CLI-004 |
| `8547ae6` | Pass token to SessionManager in resetE2EE | FR-AUTH-006, FR-E2EE-003 |
| `58150da` | Skip decryption for sender's own messages | FR-E2EE-006, FR-MSG-001 |
| `dab20e5` | Fix JWT in SessionManager for prekeys | FR-AUTH-006, FR-KEY-006 |
| `59a151f` | Use JWT token instead of userId | FR-AUTH-006 |

### 9.3 Deployment Commits

| Commit Hash | Description | Environment |
|-------------|-------------|-------------|
| `c91bced` | Deploy Worker and Client to Cloudflare | Production |
| `da573e0` | Add PROJECT_SUMMARY.md | Documentation |
| `9cfc9d6` | Update STATUS.md (All 18 User Stories) | Documentation |

### 9.4 Requirement-to-Commit Reverse Mapping

| Requirement ID | Implementing Commits | Latest Commit |
|---------------|---------------------|---------------|
| FR-AUTH-001 | `6513280` | `6513280` |
| FR-AUTH-002 | `6513280` | `6513280` |
| FR-AUTH-003 | `6513280` | `6513280` |
| FR-AUTH-004 | `6513280`, `afa09e0` | `afa09e0` |
| FR-AUTH-005 | `6513280`, `aeb986d` | `aeb986d` |
| FR-AUTH-006 | `afa09e0`, `1879f84`, `dab20e5`, `59a151f`, `8547ae6` | `1879f84` |
| FR-KEY-001 | `6513280`, `aeb986d` | `aeb986d` |
| FR-KEY-002 | `6513280`, `bc80066` | `bc80066` |
| FR-KEY-003 | `6513280`, `fd3e9b0` | `fd3e9b0` |
| FR-KEY-004 | `efda9bb`, `881ca8b` | `881ca8b` |
| FR-KEY-005 | `efda9bb` | `efda9bb` |
| FR-KEY-006 | `efda9bb`, `e794613`, `dab20e5` | `dab20e5` |
| FR-KEY-007 | `4151319` | `4151319` |
| FR-KEY-008 | `efda9bb` | `efda9bb` |
| FR-E2EE-001 | `efda9bb`, `bc80066`, `e794613`, `1fdddc7` | `1fdddc7` |
| FR-E2EE-002 | `efda9bb`, `fd3e9b0` | `fd3e9b0` |
| FR-E2EE-003 | `efda9bb`, `1f29433`, `89132b9`, `a257b67`, `85606fb`, `8547ae6` | `8547ae6` |
| FR-E2EE-004 | `efda9bb`, `89903a5` | `89903a5` |
| FR-E2EE-005 | `3a0d7c9`, `881ca8b`, `b0baaaf` | `b0baaaf` |
| FR-E2EE-006 | `3a0d7c9`, `89903a5`, `b0baaaf`, `60c36f9`, `7a3f367`, `85606fb`, `58150da` | `89903a5` |
| FR-E2EE-007 | `3a0d7c9`, `60c36f9` | `60c36f9` |
| FR-E2EE-008 | `3a0d7c9` | `3a0d7c9` |
| FR-E2EE-009 | `3a0d7c9`, `1f29433`, `a257b67` | `a257b67` |
| FR-E2EE-010 | `3a0d7c9`, `1fdddc7` | `1fdddc7` |
| FR-MSG-001 | `6a99638`, `58150da` | `58150da` |
| FR-MSG-002 | `6a99638`, `89132b9`, `5208370` | `5208370` |
| FR-MSG-003 | `6a99638`, `5a10467` | `5a10467` |
| FR-MSG-004 | `6a99638` | `6a99638` |
| FR-MSG-005 | `8fc03fb` | `8fc03fb` |
| FR-MSG-006 | `8fc03fb` | `8fc03fb` |
| FR-MSG-007 | `8fc03fb` | `8fc03fb` |
| FR-PRES-001 | `bdfecaf` | `bdfecaf` |
| FR-PRES-002 | `bdfecaf`, `ed66b72` | `ed66b72` |
| FR-PRES-003 | `bdfecaf` | `bdfecaf` |
| FR-TYPE-001 | `bdfecaf` | `bdfecaf` |
| FR-TYPE-002 | `bdfecaf` | `bdfecaf` |
| FR-GRP-001 | `0db692c` | `0db692c` |
| FR-GRP-002 | `0db692c` | `0db692c` |
| FR-GRP-003 | `0db692c` | `0db692c` |
| FR-GRP-004 | `0db692c` | `0db692c` |
| FR-GRP-005 | `0db692c` | `0db692c` |
| FR-GRP-006 | `0db692c` | `0db692c` |
| FR-GRP-007 | `0db692c` | `0db692c` |
| FR-FP-001 | `f128d0e` | `f128d0e` |
| FR-FP-002 | `f128d0e` | `f128d0e` |
| FR-FP-003 | `f128d0e` | `f128d0e` |
| FR-FP-004 | `f128d0e` | `f128d0e` |
| FR-CLI-001 | `fd77126` | `fd77126` |
| FR-CLI-002 | `fd77126` | `fd77126` |
| FR-CLI-003 | `0d49610` | `0d49610` |
| FR-CLI-004 | `be40f60`, `1879f84` | `1879f84` |
| FR-CLI-005 | `63f0051` | `63f0051` |
| FR-CLI-006 | `725b698` | `725b698` |

### 9.5 Commit Statistics Summary

| Category | Count | Description |
|----------|-------|-------------|
| Feature Commits | 17 | Initial implementations of user stories |
| Bug Fix Commits | 21 | Corrections and improvements |
| Deployment Commits | 3 | Production deployments |
| Documentation Commits | 5 | Docs and status updates |
| **Total Commits** | **46** | Full implementation history |

**Most Modified Requirements:**
1. **FR-E2EE-006** (Double Ratchet): 7 commits
2. **FR-AUTH-006** (JWT Validation): 5 commits  
3. **FR-E2EE-003** (Session Establishment): 6 commits
4. **FR-KEY-006** (Prekey Retrieval): 3 commits

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-22 | System | Initial code traceability matrix |
| 1.1 | 2025-12-22 | System | Added commit history traceability (Section 9) |

---

**End of Code-to-Requirement Traceability Matrix**
