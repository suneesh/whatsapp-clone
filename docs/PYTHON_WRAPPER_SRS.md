# Software Requirements Specification (SRS)
## Python Wrapper for WhatsApp Clone E2EE Chat Application

**Version:** 1.0  
**Date:** December 16, 2025  
**Project Name:** WhatsApp Clone Python Wrapper  
**Document Status:** Draft

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Technical Architecture](#4-technical-architecture)
5. [API Specifications](#5-api-specifications)
6. [Security Requirements](#6-security-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [External Interface Requirements](#8-external-interface-requirements)
9. [Data Requirements](#9-data-requirements)
10. [Development Guidelines](#10-development-guidelines)

---

## 1. Introduction

### 1.1 Purpose

This document specifies requirements for a Python wrapper library that provides programmatic access to the WhatsApp Clone chat application. The wrapper acts as a drop-in replacement for the React frontend, enabling Python applications to send and receive end-to-end encrypted messages through the same backend infrastructure.

### 1.2 Scope

The Python wrapper shall provide:

**In Scope:**
- User authentication (login/register)
- End-to-end encrypted messaging (1-to-1 and group chats)
- E2EE cryptographic operations (X3DH key agreement, Double Ratchet algorithm)
- Key management (identity keys, prekeys, session management)
- Key fingerprint verification
- Real-time message delivery via WebSocket
- Message status tracking (sent/delivered/read)
- Online presence indicators
- Typing indicators
- Image/file sending and receiving
- Group chat management (create, join, leave, manage members)
- Message persistence and retrieval
- Read receipt management
- Complete feature parity with React frontend

**Out of Scope:**
- GUI/UI components
- Browser-based storage (uses file-based storage instead)
- Voice/video calls
- Screen sharing
- Desktop notifications (can be implemented by wrapper consumers)
- Rate limiting (handled by server)

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| E2EE | End-to-End Encryption |
| X3DH | Extended Triple Diffie-Hellman (key agreement protocol) |
| DH | Diffie-Hellman |
| KDF | Key Derivation Function |
| HKDF | HMAC-based Key Derivation Function |
| NaCl | Networking and Cryptography library (libsodium) |
| Prekey | Pre-generated public key for asynchronous key agreement |
| Ratchet | Cryptographic ratcheting for forward secrecy |
| Session | Encrypted communication channel between two users |
| Fingerprint | Hash of public key for verification |
| QR Code | Quick Response code for fingerprint verification |

### 1.4 References

- Original Application SRS: `docs/SRS.md`
- E2EE User Stories: `docs/USER_STORIES_E2E_ENCRYPTION.md`
- E2EE Design Document: `docs/DESIGN_E2EE.md`
- Signal Protocol Documentation: https://signal.org/docs/
- PyNaCl Documentation: https://pynacl.readthedocs.io/
- WebSocket Protocol (RFC 6455): https://tools.ietf.org/html/rfc6455

### 1.5 Overview

The Python wrapper provides a high-level API for interacting with the WhatsApp Clone backend. It handles all cryptographic operations, WebSocket communication, session management, and message persistence locally, mirroring the functionality of the React frontend.

---

## 2. Overall Description

### 2.1 Product Perspective

The Python wrapper is a client-side library that communicates with the existing Cloudflare Workers backend:

```
┌─────────────────────────────────────────────────────────┐
│                   Python Application                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Python Wrapper (whatsapp_client)           │ │
│  │                                                     │ │
│  │  ├─ Authentication Module                          │ │
│  │  ├─ E2EE Crypto Module                            │ │
│  │  │   ├─ KeyManager                                │ │
│  │  │   ├─ SessionManager                            │ │
│  │  │   ├─ X3DH Protocol                             │ │
│  │  │   └─ Double Ratchet Engine                     │ │
│  │  ├─ WebSocket Client                              │ │
│  │  ├─ Message Handler                               │ │
│  │  ├─ Storage Layer (file-based)                    │ │
│  │  └─ API Client (REST)                             │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        │ HTTPS/WSS
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Cloudflare Workers Backend                    │
│                                                          │
│  ├─ REST API Endpoints                                  │
│  ├─ WebSocket Handler (Durable Objects)                 │
│  ├─ D1 Database                                         │
│  └─ User/Message/Group Management                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Product Features

The wrapper provides the following feature groups:

1. **Authentication & User Management**
   - Register new users
   - Login/logout
   - Session persistence
   - User profile management

2. **End-to-End Encryption**
   - Automatic key pair generation (Curve25519)
   - Identity key management
   - Prekey generation and rotation
   - X3DH key agreement protocol
   - Double Ratchet algorithm for message encryption
   - Session establishment and management
   - Key fingerprint generation and verification

3. **Messaging**
   - Send/receive encrypted text messages
   - Send/receive encrypted images
   - Message status tracking
   - Read receipts
   - Message persistence
   - Message retrieval/history

4. **Real-time Communication**
   - WebSocket connection management
   - Typing indicators
   - Online/offline presence
   - Automatic reconnection
   - Event-driven message handling

5. **Group Chats**
   - Create/delete groups
   - Add/remove members
   - Send/receive group messages
   - Group metadata management
   - Role-based permissions

6. **Storage**
   - Local key storage (encrypted)
   - Session state persistence
   - Message caching
   - Ratchet state storage

### 2.3 User Classes and Characteristics

**Primary User:** Python developers building automated systems, bots, or integrations that need to:
- Send/receive encrypted messages programmatically
- Integrate chat functionality into Python applications
- Build chat bots with E2EE support
- Create automated notification systems
- Develop testing tools for the chat platform

**Technical Expertise:** Intermediate to advanced Python developers familiar with:
- Asynchronous programming (asyncio)
- WebSocket communication
- Basic cryptography concepts
- Event-driven architectures

### 2.4 Operating Environment

- **Python Version:** 3.9+
- **Operating Systems:** Windows, macOS, Linux
- **Dependencies:**
  - PyNaCl (libsodium bindings for crypto)
  - websockets (WebSocket client)
  - aiohttp (async HTTP client)
  - pydantic (data validation)
  - cryptography (additional crypto utilities)

### 2.5 Design and Implementation Constraints

1. **Cryptographic Compatibility:** Must implement identical E2EE protocols as React frontend
2. **Message Format:** Must maintain compatibility with existing message structure
3. **Session Compatibility:** Sessions established by Python wrapper must be readable by React client and vice versa
4. **Storage Format:** Local storage must be compatible with future migration capabilities
5. **Python Async:** Must use asyncio for all network operations
6. **Type Safety:** Full type hints for all public APIs

---

## 3. Functional Requirements

### 3.1 Authentication (FR-AUTH)

#### FR-AUTH-01: User Registration
**Priority:** High  
**Description:** The wrapper shall allow registration of new user accounts.

**Inputs:**
- Username (string, 3-100 characters)
- Password (string, 6+ characters)
- Avatar URL (optional)

**Processing:**
- Validate username format
- Validate password strength
- Send registration request to `/api/auth/register`
- Store authentication token

**Outputs:**
- User object with ID, username, avatar
- Authentication token

**Error Handling:**
- Username already exists → `UsernameExistsError`
- Invalid credentials → `ValidationError`
- Network error → `ConnectionError`

#### FR-AUTH-02: User Login
**Priority:** High  
**Description:** Authenticate existing users and establish session.

**Inputs:**
- Username
- Password

**Processing:**
- Send login request to `/api/auth/login`
- Store user ID and authentication token
- Initialize cryptographic keys
- Upload public keys to server
- Connect to WebSocket

**Outputs:**
- User object
- Active session

#### FR-AUTH-03: Logout
**Priority:** Medium  
**Description:** Terminate user session and cleanup resources.

**Processing:**
- Close WebSocket connection
- Clear in-memory session data
- Optionally clear local storage

### 3.2 Cryptographic Operations (FR-CRYPTO)

#### FR-CRYPTO-01: Key Generation
**Priority:** High  
**Description:** Generate and manage cryptographic key pairs on first use.

**Processing:**
- Generate Curve25519 identity key pair
- Generate Ed25519 signing key pair
- Generate 100 one-time prekeys
- Generate signed prekey with signature
- Compute key fingerprint (SHA-256 of identity key)
- Store private keys securely (encrypted file)
- Upload public keys to server

**Outputs:**
- Identity key pair (public/private)
- Signing key pair (public/private)
- Prekey bundle
- 60-character hexadecimal fingerprint

#### FR-CRYPTO-02: Session Establishment (X3DH)
**Priority:** High  
**Description:** Establish encrypted session with peer using X3DH protocol.

**Inputs:**
- Peer user ID

**Processing:**
1. Fetch peer's prekey bundle from `/api/users/{peerId}/prekeys`
2. Perform X3DH key agreement:
   - DH1 = DH(IKₐ, SPKᵦ)
   - DH2 = DH(EKₐ, IKᵦ)
   - DH3 = DH(EKₐ, SPKᵦ)
   - DH4 = DH(EKₐ, OPKᵦ) [if one-time prekey available]
3. Derive shared secret: SK = KDF(DH1 || DH2 || DH3 || DH4)
4. Initialize Double Ratchet with shared secret
5. Store session state locally
6. Mark one-time prekey as used (send to server)

**Outputs:**
- Session record with shared secret and ratchet state
- Session ID

#### FR-CRYPTO-03: Message Encryption (Double Ratchet)
**Priority:** High  
**Description:** Encrypt outgoing messages using Double Ratchet algorithm.

**Inputs:**
- Plaintext message
- Recipient user ID

**Processing:**
1. Load session state for recipient
2. Generate message key from current chain key
3. Encrypt message with AES-256-GCM using message key
4. Create ratchet header (DH public key, previous chain length, message number)
5. Update ratchet state
6. Save updated session state
7. Package encrypted message + header

**Outputs:**
- Encrypted message object:
  ```python
  {
    "ciphertext": bytes,
    "header": {
      "dh_public_key": bytes,
      "prev_chain_length": int,
      "message_number": int
    },
    "nonce": bytes
  }
  ```

#### FR-CRYPTO-04: Message Decryption (Double Ratchet)
**Priority:** High  
**Description:** Decrypt incoming encrypted messages.

**Inputs:**
- Encrypted message object
- Sender user ID

**Processing:**
1. Load session state for sender
2. Check if DH ratchet needed (compare header DH key)
3. If needed, perform DH ratchet step
4. Derive message key from receiving chain
5. Handle out-of-order messages (skip keys if needed, max 1000)
6. Decrypt ciphertext using message key
7. Update ratchet state
8. Save updated session state

**Outputs:**
- Decrypted plaintext message

**Error Handling:**
- Decryption failure → `DecryptionError`
- Too many skipped keys → `MessageSkipError`
- Invalid session → `SessionNotFoundError`

#### FR-CRYPTO-05: Fingerprint Verification
**Priority:** Medium  
**Description:** Verify peer's identity key fingerprint.

**Inputs:**
- Peer user ID
- Expected fingerprint (manual input or QR scan)

**Processing:**
- Fetch peer's public identity key from session
- Compute fingerprint
- Compare with expected fingerprint
- Store verification status locally
- Send verification status to server (`/api/verify-key`)

**Outputs:**
- Boolean verification result
- Verification timestamp

### 3.3 Messaging (FR-MSG)

#### FR-MSG-01: Send Text Message
**Priority:** High  
**Description:** Send encrypted text message to peer.

**Inputs:**
- Recipient user ID
- Message text

**Processing:**
1. Ensure session exists (establish if needed)
2. Encrypt message content
3. Serialize encrypted message
4. Prefix with "E2EE:" marker
5. Send via WebSocket with type="message"
6. Store message locally with status="sent"
7. Wait for delivery confirmation

**Outputs:**
- Message ID
- Message object with status

#### FR-MSG-02: Receive Text Message
**Priority:** High  
**Description:** Receive and decrypt incoming messages.

**Processing:**
1. Receive WebSocket message event
2. Extract encrypted payload
3. Decrypt message content
4. Store decrypted message locally
5. Trigger message received callback
6. Send delivery receipt to sender

**Outputs:**
- Decrypted message object

#### FR-MSG-03: Send Image
**Priority:** Medium  
**Description:** Send encrypted image data.

**Inputs:**
- Recipient user ID
- Image data (bytes or base64)

**Processing:**
1. Validate image size (max configurable)
2. Encode image as base64 if needed
3. Encrypt image data
4. Send via WebSocket with type="image"

#### FR-MSG-04: Receive Image
**Priority:** Medium  
**Description:** Receive and decrypt image messages.

**Processing:**
- Same as FR-MSG-02 but with image data
- Optionally save to file
- Return image bytes

#### FR-MSG-05: Message Status Updates
**Priority:** High  
**Description:** Track and update message delivery status.

**Processing:**
- Handle "status" WebSocket events
- Update local message status: sent → delivered → read
- Trigger status change callbacks

**Status Values:**
- `sent`: Message sent to server
- `delivered`: Message delivered to recipient's device
- `read`: Message read by recipient

#### FR-MSG-06: Send Read Receipts
**Priority:** Medium  
**Description:** Notify senders when messages are read.

**Inputs:**
- List of message IDs
- Sender user ID

**Processing:**
- Send "read" event via WebSocket
- Update local message status to "read"

#### FR-MSG-07: Message History
**Priority:** Medium  
**Description:** Retrieve message history for a conversation.

**Inputs:**
- Peer user ID
- Optional: limit, offset

**Processing:**
- Fetch from local storage first
- Optionally sync with server (`/api/messages/{peerId}`)
- Decrypt any encrypted messages
- Return chronologically sorted messages

**Outputs:**
- List of message objects

### 3.4 Real-Time Communication (FR-RT)

#### FR-RT-01: WebSocket Connection
**Priority:** High  
**Description:** Maintain persistent WebSocket connection.

**Processing:**
1. Connect to `/ws` endpoint
2. Send authentication message
3. Handle connection lifecycle
4. Implement exponential backoff reconnection (3s base)
5. Emit connection status events

**Events:**
- `connected`
- `disconnected`
- `reconnecting`

#### FR-RT-02: Typing Indicators
**Priority:** Low  
**Description:** Send and receive typing status.

**Inputs:**
- Recipient user ID
- Typing state (boolean)

**Processing:**
- Send "typing" event via WebSocket
- Trigger typing callback on receipt
- Implement typing timeout (5 seconds)

#### FR-RT-03: Online Presence
**Priority:** Medium  
**Description:** Track online/offline status of users.

**Processing:**
- Receive "online" events from WebSocket
- Maintain in-memory user presence map
- Trigger presence change callbacks

**Outputs:**
- Dict[user_id, online_status]

### 3.5 Group Chat (FR-GROUP)

#### FR-GROUP-01: Create Group
**Priority:** Medium  
**Description:** Create new group chat.

**Inputs:**
- Group name
- Description (optional)
- Initial member IDs (optional)

**Processing:**
- Send POST to `/api/groups`
- Store group metadata locally
- Return group object

#### FR-GROUP-02: Send Group Message
**Priority:** Medium  
**Description:** Send message to group.

**Inputs:**
- Group ID
- Message content

**Processing:**
- Send via WebSocket with type="group_message"
- Messages are not E2EE in groups (server-side encryption only)
- Store locally

#### FR-GROUP-03: Manage Group Members
**Priority:** Medium  
**Description:** Add/remove group members.

**Inputs:**
- Group ID
- User ID
- Action (add/remove)

**Processing:**
- Send to `/api/groups/{groupId}/members`
- Verify permissions (owner/admin only)

### 3.6 Storage (FR-STORE)

#### FR-STORE-01: Key Storage
**Priority:** High  
**Description:** Persist cryptographic keys securely.

**Storage Format:**
- File: `~/.whatsapp_client/{user_id}/keys.db`
- Encryption: AES-256-GCM with password-derived key
- Format: SQLite or JSON

**Data:**
- Identity key pair
- Signing key pair
- Prekeys (unused)
- Session records
- Ratchet states

#### FR-STORE-02: Message Storage
**Priority:** Medium  
**Description:** Cache messages locally.

**Storage:**
- File: `~/.whatsapp_client/{user_id}/messages.db`
- Format: SQLite

**Schema:**
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  peer_id TEXT NOT NULL,
  from_user TEXT NOT NULL,
  to_user TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  type TEXT DEFAULT 'text',
  is_encrypted BOOLEAN DEFAULT 1
);
```

#### FR-STORE-03: Configuration Storage
**Priority:** Low  
**Description:** Store user preferences.

**Data:**
- Server URL
- Auto-reconnect settings
- Logging level
- Storage paths

---

## 4. Technical Architecture

### 4.1 Module Structure

```
whatsapp_client/
├── __init__.py
├── client.py              # Main WhatsAppClient class
├── auth.py                # Authentication module
├── crypto/
│   ├── __init__.py
│   ├── key_manager.py     # Key generation and management
│   ├── session_manager.py # Session lifecycle
│   ├── x3dh.py           # X3DH protocol implementation
│   ├── ratchet.py        # Double Ratchet algorithm
│   └── utils.py          # Crypto utilities
├── transport/
│   ├── __init__.py
│   ├── websocket.py      # WebSocket client
│   └── rest_client.py    # REST API client
├── storage/
│   ├── __init__.py
│   ├── key_storage.py    # Encrypted key persistence
│   └── message_storage.py # Message database
├── models.py             # Data models (Pydantic)
├── exceptions.py         # Custom exceptions
└── utils.py              # General utilities
```

### 4.2 Class Diagram

```
WhatsAppClient
├── AuthManager
├── CryptoManager
│   ├── KeyManager
│   ├── SessionManager
│   ├── X3DHProtocol
│   └── RatchetEngine
├── WebSocketClient
├── RestClient
├── MessageHandler
└── StorageManager
    ├── KeyStorage
    └── MessageStorage
```

### 4.3 Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.9"
PyNaCl = "^1.5.0"           # Cryptography (libsodium)
websockets = "^12.0"         # WebSocket client
aiohttp = "^3.9.0"           # Async HTTP client
pydantic = "^2.5.0"          # Data validation
cryptography = "^41.0.0"     # Additional crypto
aiosqlite = "^0.19.0"        # Async SQLite
python-dotenv = "^1.0.0"     # Environment variables
qrcode = "^7.4.2"            # QR code generation (optional)
pillow = "^10.0.0"           # Image processing (optional)
```

---

## 5. API Specifications

### 5.1 Client Initialization

```python
from whatsapp_client import WhatsAppClient

# Initialize client
client = WhatsAppClient(
    server_url="https://your-worker.workers.dev",
    storage_path="~/.whatsapp_client",
    auto_connect=True
)

# Register new user
await client.register(
    username="alice",
    password="secure_password",
    avatar="https://example.com/avatar.jpg"
)

# Login existing user
await client.login(
    username="alice",
    password="secure_password"
)

# Logout
await client.logout()
```

### 5.2 Messaging API

```python
# Send text message
message = await client.send_message(
    to="user_id_123",
    content="Hello, World!"
)

# Send image
message = await client.send_image(
    to="user_id_123",
    image_data=b"...",  # or file path
    caption="Check this out!"
)

# Get message history
messages = await client.get_messages(
    peer_id="user_id_123",
    limit=50,
    before=timestamp  # optional
)

# Mark messages as read
await client.mark_as_read(
    peer_id="user_id_123",
    message_ids=["msg1", "msg2"]
)
```

### 5.3 Event Handlers

```python
# Register event handlers
@client.on_message
async def handle_message(message):
    print(f"From {message.from_user}: {message.content}")
    # Auto-reply
    await client.send_message(
        to=message.from_user,
        content="Got your message!"
    )

@client.on_message_status
async def handle_status(message_id, status):
    print(f"Message {message_id} is now {status}")

@client.on_typing
async def handle_typing(user_id, is_typing):
    if is_typing:
        print(f"{user_id} is typing...")

@client.on_presence
async def handle_presence(user_id, online):
    print(f"{user_id} is {'online' if online else 'offline'}")

@client.on_connection_change
async def handle_connection(connected):
    print(f"Connection: {'connected' if connected else 'disconnected'}")
```

### 5.4 Encryption API

```python
# Get own fingerprint
fingerprint = client.get_fingerprint()
print(f"My fingerprint: {fingerprint}")

# Get peer fingerprint
peer_fingerprint = await client.get_peer_fingerprint("user_id_123")

# Verify fingerprint
await client.verify_fingerprint(
    peer_id="user_id_123",
    fingerprint=peer_fingerprint,
    verified=True
)

# Check verification status
is_verified = await client.is_fingerprint_verified("user_id_123")

# Generate QR code for fingerprint
qr_code_image = client.generate_fingerprint_qr()
qr_code_image.save("my_fingerprint.png")
```

### 5.5 Group Chat API

```python
# Create group
group = await client.create_group(
    name="Dev Team",
    description="Developer discussions",
    member_ids=["user1", "user2"]
)

# Send group message
await client.send_group_message(
    group_id=group.id,
    content="Hello team!"
)

# Add member
await client.add_group_member(
    group_id=group.id,
    user_id="user3"
)

# Handle group messages
@client.on_group_message
async def handle_group_message(message):
    print(f"[{message.group_id}] {message.from_user}: {message.content}")
```

### 5.6 Advanced Usage

```python
# Custom message handler with filtering
@client.on_message
async def command_handler(message):
    if message.content.startswith("/"):
        command = message.content[1:].split()[0]
        if command == "help":
            await client.send_message(
                to=message.from_user,
                content="Available commands: /help, /status"
            )

# Bulk operations
async def broadcast_message(user_ids, content):
    tasks = [
        client.send_message(to=uid, content=content)
        for uid in user_ids
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Context manager
async with WhatsAppClient(server_url="...") as client:
    await client.login("alice", "password")
    await client.send_message("bob", "Hello!")
    # Auto-cleanup on exit
```

---

## 6. Security Requirements

### 6.1 Cryptographic Requirements

| Requirement | Specification |
|------------|---------------|
| Key Exchange | X3DH (Extended Triple Diffie-Hellman) |
| Encryption Algorithm | AES-256-GCM (via NaCl secretbox) |
| Key Derivation | HKDF-SHA256 |
| Signing | Ed25519 |
| Key Agreement | Curve25519 (X25519) |
| Random Number Generation | OS-provided CSPRNG |
| Session Ratcheting | Double Ratchet (Signal Protocol) |

### 6.2 Key Storage Security

- Private keys SHALL be encrypted at rest using AES-256-GCM
- Encryption key SHALL be derived from user password using Argon2id
- Key derivation parameters: memory=64MB, iterations=3, parallelism=4
- Storage files SHALL have restricted permissions (0600 on Unix)

### 6.3 Network Security

- All HTTP requests SHALL use HTTPS
- WebSocket connections SHALL use WSS (WebSocket Secure)
- TLS 1.2+ required
- Certificate validation enabled
- No downgrade attacks permitted

### 6.4 Session Security

- Sessions SHALL timeout after 30 days of inactivity
- Re-authentication required after timeout
- Session tokens SHALL be securely random (128 bits minimum)

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Metric | Requirement |
|--------|-------------|
| Message Encryption | < 10ms per message |
| Message Decryption | < 15ms per message |
| Session Establishment | < 500ms (excluding network) |
| WebSocket Reconnection | < 3 seconds |
| Memory Usage | < 50MB for typical workload |
| Message Throughput | > 100 messages/second |

### 7.2 Reliability

- **Availability:** 99.9% uptime (client-side, excludes server downtime)
- **Data Durability:** No message loss for stored messages
- **Connection Resilience:** Auto-reconnect with exponential backoff
- **Error Recovery:** Graceful degradation on crypto errors

### 7.3 Compatibility

- **Python Versions:** 3.9, 3.10, 3.11, 3.12
- **Operating Systems:** Windows 10+, macOS 11+, Linux (Ubuntu 20.04+, Debian 11+)
- **Architecture:** x86_64, ARM64
- **Protocol Compatibility:** 100% compatible with React frontend

### 7.4 Maintainability

- **Code Coverage:** Minimum 80% test coverage
- **Documentation:** Full API documentation (Sphinx)
- **Type Hints:** 100% type coverage
- **Linting:** Pass flake8, mypy, black
- **Versioning:** Semantic versioning (SemVer)

### 7.5 Usability

- **API Design:** Pythonic, intuitive, async-first
- **Error Messages:** Clear, actionable error descriptions
- **Logging:** Configurable logging levels
- **Examples:** Comprehensive example code
- **Documentation:** Beginner-friendly tutorials

---

## 8. External Interface Requirements

### 8.1 Backend API Endpoints

The wrapper SHALL communicate with these backend endpoints:

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Authenticate user

#### User Management
- `GET /api/users` - List all users
- `GET /api/users/{userId}` - Get user info

#### E2EE Key Management
- `POST /api/users/prekeys` - Upload prekey bundle
- `GET /api/users/{userId}/prekeys` - Fetch peer's prekeys
- `GET /api/users/prekeys/status` - Check prekey availability
- `DELETE /api/users/prekeys/{keyId}` - Mark prekey as used

#### Fingerprint Verification
- `POST /api/verify-key` - Mark fingerprint as verified
- `GET /api/verify-key/{userId}` - Check verification status
- `DELETE /api/verify-key/{userId}` - Remove verification

#### Messaging
- `GET /api/messages/{peerId}` - Get message history
- `PUT /api/messages/status` - Batch update message status

#### Groups
- `POST /api/groups` - Create group
- `GET /api/groups` - List user's groups
- `GET /api/groups/{groupId}` - Get group details
- `POST /api/groups/{groupId}/members` - Add member
- `DELETE /api/groups/{groupId}/members/{userId}` - Remove member
- `GET /api/groups/{groupId}/messages` - Get group messages

#### WebSocket
- `WS /ws` - WebSocket connection endpoint

### 8.2 WebSocket Message Format

#### Client → Server

```json
// Authentication
{
  "type": "auth",
  "payload": {
    "userId": "uuid",
    "username": "alice"
  }
}

// Send message
{
  "type": "message",
  "payload": {
    "to": "user_id",
    "content": "E2EE:{encrypted_data}",
    "messageType": "text"
  }
}

// Typing indicator
{
  "type": "typing",
  "payload": {
    "to": "user_id",
    "typing": true
  }
}

// Read receipt
{
  "type": "read",
  "payload": {
    "to": "sender_id",
    "messageIds": ["msg1", "msg2"]
  }
}
```

#### Server → Client

```json
// Incoming message
{
  "type": "message",
  "payload": {
    "id": "msg_uuid",
    "from": "user_id",
    "to": "current_user_id",
    "content": "E2EE:{encrypted_data}",
    "timestamp": 1702742400000,
    "status": "delivered",
    "type": "text"
  }
}

// Online status
{
  "type": "online",
  "payload": {
    "userId": "user_id",
    "username": "bob",
    "online": true
  }
}

// Message status update
{
  "type": "status",
  "payload": {
    "messageId": "msg_uuid",
    "status": "read"
  }
}

// Error
{
  "type": "error",
  "payload": {
    "message": "Error description"
  }
}
```

---

## 9. Data Requirements

### 9.1 Local Storage Schema

#### Keys Database (`keys.db`)

```sql
CREATE TABLE identity_keys (
  user_id TEXT PRIMARY KEY,
  identity_private_key BLOB NOT NULL,
  identity_public_key BLOB NOT NULL,
  signing_private_key BLOB NOT NULL,
  signing_public_key BLOB NOT NULL,
  fingerprint TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE prekeys (
  key_id INTEGER PRIMARY KEY,
  prekey_type TEXT NOT NULL, -- 'signed' or 'one_time'
  private_key BLOB NOT NULL,
  public_key BLOB NOT NULL,
  signature BLOB,
  created_at INTEGER NOT NULL,
  is_used INTEGER DEFAULT 0
);

CREATE TABLE sessions (
  peer_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  remote_identity_key BLOB NOT NULL,
  remote_signed_prekey BLOB NOT NULL,
  remote_fingerprint TEXT NOT NULL,
  root_key BLOB NOT NULL,
  ratchet_state BLOB NOT NULL, -- Serialized ratchet state
  status TEXT DEFAULT 'ready',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE verification_status (
  peer_id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL,
  verified INTEGER DEFAULT 0,
  verified_at INTEGER
);
```

#### Messages Database (`messages.db`)

```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  peer_id TEXT NOT NULL,
  from_user TEXT NOT NULL,
  to_user TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  type TEXT DEFAULT 'text',
  image_data TEXT,
  is_encrypted INTEGER DEFAULT 1,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (peer_id) REFERENCES users(id)
);

CREATE INDEX idx_messages_peer ON messages(peer_id, timestamp);
CREATE INDEX idx_messages_status ON messages(status);

CREATE TABLE group_messages (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  from_user TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  type TEXT DEFAULT 'text',
  created_at INTEGER NOT NULL
);
```

### 9.2 Configuration File

```yaml
# ~/.whatsapp_client/config.yaml
server:
  url: "https://your-worker.workers.dev"
  ws_url: "wss://your-worker.workers.dev/ws"
  
storage:
  path: "~/.whatsapp_client"
  encryption: true
  
connection:
  auto_reconnect: true
  reconnect_delay: 3
  max_reconnect_attempts: 10
  
logging:
  level: "INFO"
  file: "~/.whatsapp_client/logs/client.log"
  
crypto:
  prekey_minimum: 10  # Generate new prekeys when below this
  prekey_generation_count: 100
  session_timeout_days: 30
```

---

## 10. Development Guidelines

### 10.1 Code Structure

```python
# Example: client.py structure

from typing import Optional, Callable, List
import asyncio
from .auth import AuthManager
from .crypto import CryptoManager
from .transport import WebSocketClient, RestClient
from .storage import StorageManager
from .models import Message, User, Group

class WhatsAppClient:
    """Main client class for WhatsApp Clone."""
    
    def __init__(
        self,
        server_url: str,
        storage_path: str = "~/.whatsapp_client",
        auto_connect: bool = True
    ):
        self.server_url = server_url
        self.storage_path = storage_path
        self.auto_connect = auto_connect
        
        # Initialize components
        self._auth = AuthManager(self)
        self._crypto = CryptoManager(self)
        self._ws = WebSocketClient(self)
        self._rest = RestClient(self)
        self._storage = StorageManager(self)
        
        # Event handlers
        self._message_handlers: List[Callable] = []
        self._status_handlers: List[Callable] = []
        
    async def login(self, username: str, password: str) -> User:
        """Authenticate and initialize client."""
        user = await self._auth.login(username, password)
        await self._crypto.initialize(user.id)
        if self.auto_connect:
            await self._ws.connect()
        return user
    
    async def send_message(self, to: str, content: str) -> Message:
        """Send encrypted message to user."""
        # Ensure session exists
        await self._crypto.ensure_session(to)
        
        # Encrypt message
        encrypted = await self._crypto.encrypt_message(to, content)
        
        # Send via WebSocket
        message = await self._ws.send_message(to, encrypted)
        
        # Store locally
        await self._storage.save_message(message)
        
        return message
    
    def on_message(self, handler: Callable):
        """Decorator to register message handler."""
        self._message_handlers.append(handler)
        return handler
```

### 10.2 Testing Requirements

```python
# tests/test_encryption.py

import pytest
from whatsapp_client import WhatsAppClient

@pytest.mark.asyncio
async def test_message_encryption_decryption():
    """Test that messages can be encrypted and decrypted."""
    alice = WhatsAppClient(server_url="http://localhost:8787")
    bob = WhatsAppClient(server_url="http://localhost:8787")
    
    await alice.register("alice", "password123")
    await bob.register("bob", "password456")
    
    # Alice sends message to Bob
    plaintext = "Hello, Bob!"
    message = await alice.send_message(bob.user_id, plaintext)
    
    # Bob receives and decrypts
    received = await bob.receive_message(message)
    
    assert received.content == plaintext
    assert received.from_user == alice.user_id

@pytest.mark.asyncio
async def test_session_establishment():
    """Test X3DH session establishment."""
    alice = WhatsAppClient(server_url="http://localhost:8787")
    bob = WhatsAppClient(server_url="http://localhost:8787")
    
    await alice.register("alice", "password123")
    await bob.register("bob", "password456")
    
    # Establish session
    session = await alice._crypto.ensure_session(bob.user_id)
    
    assert session.peer_id == bob.user_id
    assert session.status == "ready"
    assert session.root_key is not None
```

### 10.3 Error Handling

```python
# exceptions.py

class WhatsAppClientError(Exception):
    """Base exception for all client errors."""
    pass

class AuthenticationError(WhatsAppClientError):
    """Authentication failed."""
    pass

class SessionNotFoundError(WhatsAppClientError):
    """No session exists for peer."""
    pass

class DecryptionError(WhatsAppClientError):
    """Message decryption failed."""
    pass

class ConnectionError(WhatsAppClientError):
    """WebSocket connection error."""
    pass

class ValidationError(WhatsAppClientError):
    """Input validation error."""
    pass

# Usage
try:
    await client.send_message("invalid_user", "Hello")
except SessionNotFoundError:
    # Establish session first
    await client._crypto.establish_session("invalid_user")
    await client.send_message("invalid_user", "Hello")
```

### 10.4 Logging

```python
import logging

logger = logging.getLogger("whatsapp_client")

# Configure in client
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("~/.whatsapp_client/client.log"),
        logging.StreamHandler()
    ]
)

# Usage
logger.info(f"Session established with {peer_id}")
logger.warning(f"Reconnecting to WebSocket (attempt {attempt})")
logger.error(f"Decryption failed: {error}", exc_info=True)
```

### 10.5 Documentation

Use docstrings with type hints:

```python
async def send_message(
    self,
    to: str,
    content: str,
    message_type: str = "text"
) -> Message:
    """
    Send an encrypted message to a user.
    
    Args:
        to: Recipient user ID
        content: Message text content
        message_type: Type of message (default: "text")
        
    Returns:
        Message object with ID and status
        
    Raises:
        SessionNotFoundError: If no session exists with recipient
        ConnectionError: If WebSocket is disconnected
        ValidationError: If content is empty or too long
        
    Example:
        >>> message = await client.send_message(
        ...     to="user_123",
        ...     content="Hello, World!"
        ... )
        >>> print(message.status)
        'sent'
    """
```

---

## Appendix A: Example Usage

### Complete Bot Example

```python
import asyncio
from whatsapp_client import WhatsAppClient

async def main():
    # Initialize client
    client = WhatsAppClient(
        server_url="https://your-worker.workers.dev"
    )
    
    # Login
    await client.login(
        username="bot_user",
        password="secure_password"
    )
    
    print(f"Logged in as {client.user.username}")
    print(f"Fingerprint: {client.get_fingerprint()}")
    
    # Message handler
    @client.on_message
    async def handle_message(message):
        print(f"From {message.from_user}: {message.content}")
        
        # Echo bot
        if message.content.startswith("/echo"):
            text = message.content[6:].strip()
            await client.send_message(
                to=message.from_user,
                content=f"Echo: {text}"
            )
        
        # Info command
        elif message.content == "/info":
            peer_fp = await client.get_peer_fingerprint(message.from_user)
            verified = await client.is_fingerprint_verified(message.from_user)
            await client.send_message(
                to=message.from_user,
                content=f"Your fingerprint: {peer_fp}\n"
                       f"Verified: {verified}"
            )
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await client.logout()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Appendix B: Migration from React Frontend

For users migrating from the React frontend, sessions should be compatible. Export/import functionality:

```python
# Export session from browser
# (Add this to React app)
exportSession(peerId) {
  const session = this.sessionManager.getSession(peerId);
  return JSON.stringify(session);
}

# Import to Python wrapper
await client.import_session(peer_id, session_json)
```

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | System | Initial draft |

