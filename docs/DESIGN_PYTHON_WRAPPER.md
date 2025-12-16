# Technical Design: Python Wrapper for WhatsApp Clone

**Version:** 1.0  
**Date:** December 16, 2025  
**Status:** Draft

---

## 1. Overview

A Python library that provides programmatic access to the WhatsApp Clone E2EE chat platform. The wrapper replicates all React frontend functionality, enabling developers to build bots, automation, and integrations.

**Key Goals:**
- 100% feature parity with React frontend
- Full E2EE support (X3DH + Double Ratchet)
- Async-first API design
- Drop-in replacement for browser client

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────┐
│        Python Application                │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   WhatsAppClient (Main API)        │ │
│  └────────────────────────────────────┘ │
│           │         │         │          │
│     ┌─────┴────┐ ┌──┴───┐ ┌──┴────┐    │
│     │   Auth   │ │Crypto│ │ Msg   │    │
│     └─────┬────┘ └──┬───┘ └──┬────┘    │
│           │         │         │          │
│  ┌────────┴─────────┴─────────┴───────┐ │
│  │      Transport Layer               │ │
│  │   ┌──────────┐   ┌──────────┐     │ │
│  │   │WebSocket │   │   REST   │     │ │
│  │   └──────────┘   └──────────┘     │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │      Storage Layer (SQLite)        │ │
│  │   Keys (encrypted) | Messages      │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
                    │
                    │ HTTPS/WSS
                    ▼
┌──────────────────────────────────────────┐
│    Cloudflare Workers Backend            │
│    (Existing - No Changes Required)      │
└──────────────────────────────────────────┘
```

### 2.2 Module Structure

```
whatsapp_client/
├── __init__.py                 # Public API exports
├── client.py                   # WhatsAppClient main class
├── models.py                   # Pydantic data models
├── exceptions.py               # Custom exceptions
│
├── auth/
│   ├── __init__.py
│   └── manager.py              # Authentication logic
│
├── crypto/
│   ├── __init__.py
│   ├── key_manager.py          # Key generation & storage
│   ├── session_manager.py      # Session lifecycle
│   ├── x3dh.py                 # X3DH protocol
│   ├── ratchet.py              # Double Ratchet algorithm
│   └── utils.py                # Crypto helpers
│
├── transport/
│   ├── __init__.py
│   ├── websocket.py            # WebSocket client
│   └── rest.py                 # REST API client
│
├── storage/
│   ├── __init__.py
│   ├── key_storage.py          # Encrypted key DB
│   └── message_storage.py      # Message cache DB
│
└── utils/
    ├── __init__.py
    └── helpers.py              # General utilities
```

---

## 3. Core Components

### 3.1 WhatsAppClient (Main Interface)

**Responsibilities:**
- Initialize all subsystems
- Provide high-level API
- Coordinate between modules
- Manage event handlers

**Key Methods:**
```python
class WhatsAppClient:
    async def register(username, password) -> User
    async def login(username, password) -> User
    async def logout() -> None
    
    async def send_message(to, content) -> Message
    async def send_image(to, image_data) -> Message
    async def get_messages(peer_id, limit) -> List[Message]
    
    def on_message(handler: Callable)
    def on_message_status(handler: Callable)
    def on_typing(handler: Callable)
    def on_presence(handler: Callable)
    
    async def create_group(name, members) -> Group
    async def send_group_message(group_id, content) -> Message
```

### 3.2 Crypto Module

#### KeyManager
- Generate identity key pair (Curve25519)
- Generate signing key pair (Ed25519)
- Generate prekey bundles (100 one-time + 1 signed)
- Compute fingerprints (SHA-256)
- Upload public keys to server

#### SessionManager
- Fetch peer prekey bundles
- Establish sessions via X3DH
- Manage session lifecycle
- Track session state

#### X3DH Protocol
```python
def perform_x3dh(local_keys, remote_bundle) -> SharedSecret:
    DH1 = DH(IK_local, SPK_remote)
    DH2 = DH(EK_local, IK_remote)
    DH3 = DH(EK_local, SPK_remote)
    DH4 = DH(EK_local, OPK_remote)  # if available
    
    SK = HKDF(DH1 || DH2 || DH3 || DH4)
    return SK
```

#### RatchetEngine
- Initialize from X3DH shared secret
- Symmetric ratchet (KDF chain for each message)
- DH ratchet (periodic key rotation)
- Out-of-order message handling
- Skipped key storage (max 1000)

**Encryption Flow:**
```python
def encrypt_message(session, plaintext) -> EncryptedMessage:
    message_key = derive_key(session.send_chain_key)
    session.send_chain_key = KDF(session.send_chain_key)
    
    ciphertext = AES_GCM.encrypt(message_key, plaintext)
    header = {
        "dh_key": session.dh_public,
        "prev_chain_len": session.prev_chain_length,
        "msg_num": session.send_counter
    }
    
    return {"ciphertext": ciphertext, "header": header}
```

### 3.3 Transport Module

#### WebSocketClient
- Connect to `/ws` endpoint
- Authenticate on connection
- Route incoming messages to handlers
- Send messages, typing, read receipts
- Auto-reconnect with exponential backoff (3s → 60s)
- Handle connection state transitions

**Message Types:**
- `auth` - Authenticate connection
- `message` - Send/receive messages
- `typing` - Typing indicators
- `online` - Presence updates
- `read` - Read receipts
- `group_message` - Group messages

#### RestClient
- Async HTTP client (aiohttp)
- Authentication header injection
- Endpoint wrappers:
  - POST `/api/auth/register`
  - POST `/api/auth/login`
  - POST `/api/users/prekeys`
  - GET `/api/users/{id}/prekeys`
  - POST `/api/verify-key`
  - GET `/api/messages/{peerId}`

### 3.4 Storage Module

#### KeyStorage (SQLite + AES-256-GCM)
```sql
-- Encrypted with password-derived key (Argon2id)
CREATE TABLE identity_keys (
  user_id TEXT PRIMARY KEY,
  identity_private_key BLOB,
  identity_public_key BLOB,
  signing_private_key BLOB,
  signing_public_key BLOB,
  fingerprint TEXT,
  created_at INTEGER
);

CREATE TABLE prekeys (
  key_id INTEGER PRIMARY KEY,
  prekey_type TEXT,  -- 'signed' or 'one_time'
  private_key BLOB,
  public_key BLOB,
  signature BLOB,
  is_used INTEGER
);

CREATE TABLE sessions (
  peer_id TEXT PRIMARY KEY,
  session_id TEXT,
  remote_identity_key BLOB,
  remote_fingerprint TEXT,
  root_key BLOB,
  ratchet_state BLOB,  -- Serialized ratchet state
  created_at INTEGER,
  updated_at INTEGER
);
```

**Encryption:**
- Argon2id(password, salt) → encryption_key
- AES-256-GCM(encryption_key, data) → encrypted_data
- File permissions: 0600 (Unix)

#### MessageStorage (SQLite)
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  peer_id TEXT,
  from_user TEXT,
  to_user TEXT,
  content TEXT,
  timestamp INTEGER,
  status TEXT,  -- 'sent' | 'delivered' | 'read'
  type TEXT,    -- 'text' | 'image'
  is_encrypted INTEGER
);

CREATE INDEX idx_messages_peer_time ON messages(peer_id, timestamp);
```

---

## 4. Data Flow

### 4.1 Message Send Flow

```
User Code
  │
  ├─► client.send_message("user_123", "Hello")
  │
  ├─► SessionManager.ensure_session("user_123")
  │     │
  │     ├─► KeyStorage.load_session()
  │     │     └─► Found? Return session
  │     │
  │     └─► Not found? Establish new session
  │           ├─► RestClient.get_prekey_bundle("user_123")
  │           ├─► X3DH.perform_handshake()
  │           ├─► RatchetEngine.initialize()
  │           └─► KeyStorage.save_session()
  │
  ├─► RatchetEngine.encrypt_message("Hello")
  │     ├─► Derive message key from chain
  │     ├─► Encrypt plaintext
  │     ├─► Update ratchet state
  │     └─► Return encrypted message
  │
  ├─► WebSocketClient.send({
  │     type: "message",
  │     to: "user_123",
  │     content: "E2EE:{encrypted_data}"
  │   })
  │
  └─► MessageStorage.save_message()
```

### 4.2 Message Receive Flow

```
WebSocket
  │
  ├─► Receive {"type": "message", "payload": {...}}
  │
  ├─► Detect "E2EE:" prefix
  │
  ├─► RatchetEngine.decrypt_message()
  │     ├─► Load session state
  │     ├─► Check DH ratchet needed?
  │     ├─► Handle out-of-order (skip keys)
  │     ├─► Derive message key
  │     ├─► Decrypt ciphertext
  │     └─► Update ratchet state
  │
  ├─► MessageStorage.save_message(decrypted)
  │
  ├─► Trigger event handlers
  │     └─► @client.on_message → user callback
  │
  └─► Send delivery receipt
        └─► WebSocketClient.send({type: "status", ...})
```

---

## 5. Security Design

### 5.1 Cryptographic Primitives

| Operation | Algorithm | Library |
|-----------|-----------|---------|
| Key Agreement | X25519 (Curve25519) | PyNaCl |
| Signing | Ed25519 | PyNaCl |
| Encryption | XSalsa20-Poly1305 | PyNaCl (secretbox) |
| KDF | HKDF-SHA256 | PyNaCl |
| Fingerprint | SHA-256 | hashlib |
| Storage Encryption | AES-256-GCM | cryptography |
| Password KDF | Argon2id | argon2-cffi |

### 5.2 Key Hierarchy

```
User Password
    │
    ├─► Argon2id(password, salt) → Storage Encryption Key
    │       │
    │       └─► Encrypts all private keys in SQLite
    │
    └─► (Not used for E2EE keys - separate hierarchy)

E2EE Key Hierarchy:
    Identity Key (long-term)
        │
        ├─► X3DH Handshake → Session Root Key
        │       │
        │       └─► Double Ratchet
        │               ├─► Root Key (DH ratchet)
        │               │     └─► Chain Keys (symmetric ratchet)
        │               │           └─► Message Keys (one-time use)
        │               │
        │               └─► Same on receiving side
```

### 5.3 Security Properties

- **Forward Secrecy:** Message keys deleted after use
- **Break-in Recovery:** DH ratchet provides future secrecy
- **Out-of-Order:** Skipped keys stored temporarily
- **Deniability:** No long-term signing of messages
- **Confidentiality:** AES-256-equivalent encryption
- **Authenticity:** Poly1305 MAC on all messages

---

## 6. API Design

### 6.1 Initialization

```python
from whatsapp_client import WhatsAppClient

client = WhatsAppClient(
    server_url="https://worker.workers.dev",
    storage_path="~/.whatsapp_client",
    auto_connect=True
)

# Register new user
await client.register("bot_user", "secure_password")

# Login existing user
await client.login("bot_user", "secure_password")
```

### 6.2 Event-Driven Messaging

```python
# Register handlers with decorators
@client.on_message
async def handle_message(message: Message):
    print(f"{message.from_user}: {message.content}")
    
    # Auto-reply
    await client.send_message(
        to=message.from_user,
        content=f"Echo: {message.content}"
    )

@client.on_message_status
async def handle_status(message_id: str, status: str):
    print(f"Message {message_id} → {status}")

# Start event loop
await client.run()
```

### 6.3 Synchronous Operations

```python
# Send message
msg = await client.send_message("user_id", "Hello!")
print(f"Sent: {msg.id}, status: {msg.status}")

# Get history
messages = await client.get_messages("user_id", limit=50)
for msg in messages:
    print(f"[{msg.timestamp}] {msg.content}")

# Fingerprint verification
my_fp = client.get_fingerprint()
peer_fp = await client.get_peer_fingerprint("user_id")
await client.verify_fingerprint("user_id", peer_fp, verified=True)
```

---

## 7. Implementation Plan

### Phase 1: Core Infrastructure (2 weeks)
- [ ] Project structure & dependencies
- [ ] WhatsAppClient skeleton
- [ ] REST client + authentication
- [ ] Basic storage layer
- [ ] Unit test framework

### Phase 2: Cryptography (3 weeks)
- [ ] KeyManager (key generation)
- [ ] X3DH protocol implementation
- [ ] Double Ratchet engine
- [ ] Encrypted key storage
- [ ] Crypto test vectors

### Phase 3: Messaging (2 weeks)
- [ ] WebSocket client
- [ ] Message encryption/decryption integration
- [ ] Event handler system
- [ ] Message storage
- [ ] Send/receive text messages

### Phase 4: Features (2 weeks)
- [ ] Typing indicators & presence
- [ ] Read receipts & status tracking
- [ ] Image/file sending
- [ ] Fingerprint verification
- [ ] Group chat support

### Phase 5: Polish (2 weeks)
- [ ] Error handling & logging
- [ ] Configuration system
- [ ] Documentation
- [ ] Example bots
- [ ] PyPI packaging

**Total:** ~11 weeks

---

## 8. Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.9"
PyNaCl = "^1.5.0"              # Cryptography (libsodium)
websockets = "^12.0"           # WebSocket client
aiohttp = "^3.9.0"             # Async HTTP
pydantic = "^2.5.0"            # Data validation
cryptography = "^41.0.0"       # AES-GCM for storage
aiosqlite = "^0.19.0"          # Async SQLite
argon2-cffi = "^23.1.0"        # Password KDF
python-dotenv = "^1.0.0"       # Config from .env

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
mypy = "^1.7.0"
black = "^23.12.0"
ruff = "^0.1.0"
```

---

## 9. Testing Strategy

### Unit Tests
- Crypto primitives (X3DH, Ratchet) with test vectors
- Storage encryption/decryption
- Message parsing/serialization
- Event handler registration

### Integration Tests
- Mock server for API testing
- End-to-end message flow
- Session establishment
- Reconnection logic

### Compatibility Tests
- Cross-compatibility with React frontend
- Session import/export
- Message format validation

**Coverage Target:** 80%+

---

## 10. Open Questions

1. **Session Migration:** Should we support importing sessions from React frontend?
   - *Decision:* Yes, provide export/import utilities

2. **Group E2EE:** Should groups support E2EE like Signal?
   - *Decision:* No, keep parity with current backend (no group E2EE)

3. **Multiple Devices:** Support for same account on multiple clients?
   - *Decision:* Not in v1.0, each login generates new keys

4. **Sync Strategy:** Should messages sync from server or rely on local storage?
   - *Decision:* Hybrid - local cache + server fetch for history

---

## 11. Success Criteria

- [ ] 100% feature parity with React frontend
- [ ] Messages encrypted/decrypted successfully
- [ ] Compatible with existing backend (no changes required)
- [ ] Cross-client compatibility (Python ↔ React)
- [ ] 80%+ test coverage
- [ ] Published to PyPI
- [ ] Documentation complete
- [ ] Example bots working
- [ ] Performance: <10ms encryption, <15ms decryption

---

**Document Status:** Ready for Development
