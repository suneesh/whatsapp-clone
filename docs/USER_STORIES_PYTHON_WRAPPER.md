# User Stories: Python Wrapper for WhatsApp Clone

This document breaks down the Python Wrapper implementation into individual user stories for development.

---

## Epic: Python Client Library for E2EE Chat

**Epic Description:** As a Python developer, I want a programmatic client library to send and receive end-to-end encrypted messages through the WhatsApp Clone backend, so that I can build bots, automation tools, and integrations without needing a web browser.

**Business Value:** Enables developers to create automated chat systems, bots, monitoring tools, and integrations; expands platform usage beyond human users; provides testing infrastructure for the chat application.

---

## User Story 1: Client Initialization and Authentication

**As a** Python developer  
**I want** to initialize a client and authenticate with username/password  
**So that** I can establish a connection to the chat backend

### Acceptance Criteria
- [ ] I can install the library via pip: `pip install whatsapp-client`
- [ ] I can initialize a client with server URL
- [ ] I can register a new user account programmatically
- [ ] I can login with existing credentials
- [ ] I can logout and cleanup resources
- [ ] Authentication tokens are stored securely
- [ ] Invalid credentials raise appropriate exceptions
- [ ] The client supports both sync and async contexts

### Technical Requirements
- Python 3.9+ compatibility
- Async/await based API using asyncio
- REST API calls to `/api/auth/register` and `/api/auth/login`
- Password hashing validation matches backend (bcrypt)
- Session token persistence across restarts (optional)
- Context manager support (`async with`)
- Type hints for all public APIs

### Implementation Tasks
1. Create `WhatsAppClient` main class
2. Implement `AuthManager` module
3. Add `register()` method with validation
4. Add `login()` method with token storage
5. Add `logout()` method with cleanup
6. Implement REST client wrapper
7. Add exception classes
8. Write unit tests for auth flow

### Definition of Done
- [ ] Client can register new users
- [ ] Client can login existing users
- [ ] Authentication errors are properly handled
- [ ] Tests pass with 90%+ coverage
- [ ] Documentation includes auth examples
- [ ] Type checking passes (mypy)

### Example Usage
```python
from whatsapp_client import WhatsAppClient

client = WhatsAppClient(server_url="https://worker.dev")

# Register
await client.register(
    username="bot_user",
    password="secure_password"
)

# Login
await client.login(
    username="bot_user",
    password="secure_password"
)

print(f"Logged in as {client.user.username}")
```

---

## User Story 2: Cryptographic Key Generation and Management

**As a** Python developer  
**I want** the library to automatically generate and manage E2EE keys  
**So that** messages can be encrypted without manual cryptography work

### Acceptance Criteria
- [ ] On first login, identity key pair (Curve25519) is automatically generated
- [ ] Signing key pair (Ed25519) is generated for prekey signatures
- [ ] 100 one-time prekeys are generated on initialization
- [ ] Signed prekey is generated with Ed25519 signature
- [ ] All private keys are stored encrypted on disk
- [ ] Public keys are automatically uploaded to server
- [ ] I can retrieve my key fingerprint
- [ ] Prekeys are automatically rotated when depleted
- [ ] Keys persist across client sessions

### Technical Requirements
- Use PyNaCl (libsodium) for all cryptographic operations
- Implement Curve25519 key generation (X25519)
- Implement Ed25519 signing for prekeys
- Store keys in encrypted SQLite database
- AES-256-GCM encryption for key storage
- Password-derived encryption key (Argon2id)
- SHA-256 fingerprint (60-character hex)
- File permissions set to 0600 on Unix systems

### Implementation Tasks
1. Create `KeyManager` class
2. Implement identity key generation
3. Implement signing key generation
4. Implement prekey bundle generation
5. Create `KeyStorage` class with encryption
6. Implement key upload to server
7. Add fingerprint computation
8. Add prekey rotation logic
9. Write crypto tests with test vectors

### Definition of Done
- [ ] Keys generated on first use
- [ ] Keys encrypted and stored locally
- [ ] Public keys uploaded successfully
- [ ] Fingerprint matches React frontend format
- [ ] Key rotation works automatically
- [ ] Tests validate against Signal Protocol test vectors
- [ ] Storage files have secure permissions

### Example Usage
```python
await client.login("alice", "password")

# Automatic key generation happens during login
fingerprint = client.get_fingerprint()
print(f"My fingerprint: {fingerprint}")
# Output: "a3f8b9c2d1e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"

# Check prekey status
status = await client.get_prekey_status()
print(f"Unused prekeys: {status.available}")
```

---

## User Story 3: Session Establishment (X3DH Protocol)

**As a** Python developer  
**I want** encrypted sessions to be established automatically  
**So that** I can send encrypted messages without manual setup

### Acceptance Criteria
- [ ] When sending first message to a peer, session is established automatically
- [ ] X3DH protocol is implemented correctly
- [ ] Peer's prekey bundle is fetched from server
- [ ] Four Diffie-Hellman operations are performed (DH1-DH4)
- [ ] Shared secret is derived using HKDF
- [ ] Session state is stored locally with encryption
- [ ] One-time prekey is marked as used on server
- [ ] Session establishment errors are handled gracefully
- [ ] Sessions are compatible with React frontend

### Technical Requirements
- Implement X3DH initiator role
- Fetch prekey bundle from `/api/users/{userId}/prekeys`
- Perform DH operations: DH(IKa, SPKb), DH(EKa, IKb), DH(EKa, SPKb), DH(EKa, OPKb)
- Use HKDF-SHA256 for key derivation
- Initialize Double Ratchet with shared secret
- Store session record in local database
- Send DELETE to `/api/users/prekeys/{keyId}` after use

### Implementation Tasks
1. Create `SessionManager` class
2. Implement `X3DHProtocol` class
3. Add `ensure_session()` method
4. Implement prekey bundle fetching
5. Implement DH operations
6. Implement HKDF key derivation
7. Add session storage and retrieval
8. Add prekey usage tracking
9. Write session establishment tests

### Definition of Done
- [ ] Sessions established successfully
- [ ] X3DH passes Signal Protocol test vectors
- [ ] Sessions persist across restarts
- [ ] Prekeys marked as used on server
- [ ] Compatible with React frontend sessions
- [ ] Error handling for missing prekeys
- [ ] Tests cover all DH combinations

### Example Usage
```python
# Session established automatically on first message
await client.send_message("bob_user_id", "Hello!")

# Or establish explicitly
session = await client._crypto.ensure_session("bob_user_id")
print(f"Session established: {session.session_id}")
```

---

## User Story 4: Message Encryption (Double Ratchet)

**As a** Python developer  
**I want** outgoing messages to be encrypted automatically  
**So that** only the intended recipient can read them

### Acceptance Criteria
- [ ] Text messages are encrypted before transmission
- [ ] Double Ratchet algorithm is implemented correctly
- [ ] Each message uses a unique message key
- [ ] Ratchet state advances with each message
- [ ] Encrypted messages include ratchet header
- [ ] DH ratchet is performed when needed
- [ ] Encryption uses AES-256-GCM
- [ ] Ratchet state is persisted after each message
- [ ] Messages are prefixed with "E2EE:" marker

### Technical Requirements
- Implement Double Ratchet algorithm (Signal Protocol)
- Use NaCl secretbox for encryption (XSalsa20-Poly1305)
- Generate message keys from chain keys (KDF)
- Perform symmetric ratchet for each message
- Perform DH ratchet when receiving new DH key
- Include header: { dh_public_key, prev_chain_length, message_number }
- Serialize encrypted message to JSON/base64
- Update session state atomically

### Implementation Tasks
1. Create `RatchetEngine` class
2. Implement symmetric-key ratchet
3. Implement DH ratchet
4. Implement message key derivation (KDF)
5. Implement encryption with NaCl
6. Add ratchet header creation
7. Implement state serialization
8. Add session state updates
9. Write ratchet tests with test vectors

### Definition of Done
- [ ] Messages encrypted successfully
- [ ] Ratchet advances correctly
- [ ] State persists after encryption
- [ ] Compatible with React frontend decryption
- [ ] Tests pass with Signal Protocol vectors
- [ ] Forward secrecy verified
- [ ] Break-in recovery tested

### Example Usage
```python
# Encryption happens automatically
message = await client.send_message(
    to="bob_user_id",
    content="This is encrypted!"
)

print(f"Message sent: {message.id}")
print(f"Status: {message.status}")  # 'sent'

# Message content on wire looks like:
# "E2EE:{\"ciphertext\":\"...\",\"header\":{...}}"
```

---

## User Story 5: Message Decryption (Double Ratchet)

**As a** Python developer  
**I want** incoming encrypted messages to be decrypted automatically  
**So that** I can read message content easily

### Acceptance Criteria
- [ ] Received messages are automatically detected as encrypted
- [ ] "E2EE:" prefix is recognized and stripped
- [ ] Messages are decrypted using Double Ratchet
- [ ] Out-of-order messages are handled correctly
- [ ] Skipped message keys are stored (up to 1000)
- [ ] DH ratchet is performed when new key received
- [ ] Decryption failures raise clear exceptions
- [ ] Ratchet state is updated after decryption
- [ ] Plaintext is returned to message handler

### Technical Requirements
- Parse encrypted message structure
- Detect DH ratchet by comparing header DH key
- Derive skipped message keys and store
- Decrypt using message key and NaCl
- Handle message number gaps gracefully
- Limit skipped keys to prevent DoS (max 1000)
- Update receiving chain state
- Persist updated session state

### Implementation Tasks
1. Add message decryption to `RatchetEngine`
2. Implement skipped key storage
3. Add DH ratchet detection logic
4. Implement out-of-order handling
5. Add decryption error handling
6. Update session state on decrypt
7. Add message parsing utilities
8. Write decryption tests

### Definition of Done
- [ ] Messages decrypt successfully
- [ ] Out-of-order messages handled
- [ ] Skipped keys stored correctly
- [ ] Compatible with React frontend encryption
- [ ] Decryption errors handled gracefully
- [ ] Tests cover edge cases
- [ ] Performance acceptable (<15ms/message)

### Example Usage
```python
@client.on_message
async def handle_message(message):
    # Message automatically decrypted
    print(f"From {message.from_user}: {message.content}")
    # content is plaintext, decryption happened automatically

# Or decrypt manually
encrypted_msg = "E2EE:{...}"
plaintext = await client._crypto.decrypt_message(
    from_user="alice_user_id",
    encrypted=encrypted_msg
)
```

---

## User Story 6: Send and Receive Text Messages

**As a** Python developer  
**I want** to send and receive text messages programmatically  
**So that** I can build chat bots and automated systems

### Acceptance Criteria
- [ ] I can send text messages to any user ID
- [ ] Messages are encrypted end-to-end automatically
- [ ] I can register event handlers for incoming messages
- [ ] Messages are sent via WebSocket in real-time
- [ ] Message status updates are received (sent/delivered/read)
- [ ] Messages are persisted locally
- [ ] I can retrieve message history
- [ ] Long messages (up to 10KB) are supported
- [ ] Unicode and emoji are handled correctly

### Technical Requirements
- WebSocket message sending with type="message"
- Event-driven architecture for receiving
- Decorator-based handler registration
- Local SQLite message storage
- REST API fallback for message history
- UTF-8 encoding throughout
- Message deduplication by ID
- Async message handlers

### Implementation Tasks
1. Create `WebSocketClient` class
2. Implement `send_message()` method
3. Add event handler registration system
4. Implement message receive handling
5. Create `MessageStorage` class
6. Add message history retrieval
7. Add status update tracking
8. Write messaging tests

### Definition of Done
- [ ] Messages send successfully
- [ ] Incoming messages trigger handlers
- [ ] Message history retrievable
- [ ] Status updates work correctly
- [ ] Unicode/emoji supported
- [ ] Tests cover happy and error paths
- [ ] Example bot provided

### Example Usage
```python
# Send message
message = await client.send_message(
    to="user_123",
    content="Hello, World! 👋"
)

# Receive messages
@client.on_message
async def handle_message(message):
    print(f"[{message.timestamp}] {message.from_user}: {message.content}")
    
    # Auto-reply bot
    if "hello" in message.content.lower():
        await client.send_message(
            to=message.from_user,
            content="Hi there!"
        )

# Get history
messages = await client.get_messages(
    peer_id="user_123",
    limit=50
)
```

---

## User Story 7: WebSocket Connection Management

**As a** Python developer  
**I want** real-time WebSocket communication to be managed automatically  
**So that** I receive messages instantly without polling

### Acceptance Criteria
- [ ] WebSocket connects automatically on login
- [ ] Connection is authenticated with user ID
- [ ] Incoming messages trigger event handlers
- [ ] Typing indicators work bidirectionally
- [ ] Online presence updates are received
- [ ] Connection drops trigger automatic reconnection
- [ ] Reconnection uses exponential backoff
- [ ] I can monitor connection status
- [ ] Graceful disconnect on logout

### Technical Requirements
- WebSocket client using `websockets` library
- Connect to `/ws` endpoint with upgrade
- Send auth message on connection
- Message routing to appropriate handlers
- Exponential backoff: 3s, 6s, 12s, 24s, 60s (max)
- Connection state machine (disconnected, connecting, connected, reconnecting)
- Heartbeat/ping support
- Async event loop integration

### Implementation Tasks
1. Implement WebSocket connection logic
2. Add authentication handshake
3. Implement message routing
4. Add reconnection logic with backoff
5. Create connection state tracking
6. Add connection event callbacks
7. Implement graceful shutdown
8. Write connection tests

### Definition of Done
- [ ] WebSocket connects successfully
- [ ] Messages received in real-time
- [ ] Reconnection works after drops
- [ ] No message loss during reconnect
- [ ] Connection state observable
- [ ] Tests cover connection scenarios
- [ ] Memory leaks prevented

### Example Usage
```python
# Auto-connect on login
await client.login("alice", "password")
# WebSocket connected automatically

# Monitor connection
@client.on_connection_change
async def handle_connection(connected):
    if connected:
        print("Connected to server")
    else:
        print("Disconnected, reconnecting...")

# Connection state
print(f"Connected: {client.is_connected()}")

# Manual control
await client.disconnect()
await client.connect()
```

---

## User Story 8: Typing Indicators and Presence

**As a** Python developer  
**I want** to send typing indicators and track user presence  
**So that** my bot can provide better UX

### Acceptance Criteria
- [ ] I can send typing status to a user
- [ ] I receive typing notifications from others
- [ ] Typing automatically stops after timeout (5s)
- [ ] I can track which users are online
- [ ] Online status updates are received in real-time
- [ ] Presence data is accessible via property/method
- [ ] Presence updates trigger event callbacks

### Technical Requirements
- Send "typing" WebSocket events
- Receive and parse "typing" events
- Implement typing timeout (5 seconds)
- Track online users in memory (dict)
- Receive "online" events on WebSocket
- Provide presence query methods
- Event callbacks for presence changes

### Implementation Tasks
1. Implement `send_typing()` method
2. Add typing event handler
3. Implement typing timeout
4. Add presence tracking dict
5. Handle online/offline events
6. Add presence query methods
7. Write typing/presence tests

### Definition of Done
- [ ] Typing indicators work bidirectionally
- [ ] Presence tracking accurate
- [ ] Event callbacks functional
- [ ] Tests verify behavior
- [ ] Compatible with frontend

### Example Usage
```python
# Send typing indicator
await client.send_typing(to="user_123", typing=True)
await asyncio.sleep(2)
await client.send_typing(to="user_123", typing=False)

# Receive typing
@client.on_typing
async def handle_typing(user_id, is_typing):
    if is_typing:
        print(f"{user_id} is typing...")

# Check presence
online_users = client.get_online_users()
is_online = client.is_user_online("user_123")
print(f"User online: {is_online}")

# Presence events
@client.on_presence
async def handle_presence(user_id, online):
    status = "online" if online else "offline"
    print(f"{user_id} is now {status}")
```

---

## User Story 9: Message Status Tracking and Read Receipts

**As a** Python developer  
**I want** to track message delivery and read status  
**So that** I know when recipients have seen messages

### Acceptance Criteria
- [ ] Message status progresses: sent → delivered → read
- [ ] I receive status update events for my sent messages
- [ ] I can mark received messages as read
- [ ] Read receipts are sent to senders
- [ ] Batch read receipts are supported
- [ ] Message objects reflect current status
- [ ] Status updates persist locally

### Technical Requirements
- Handle "status" WebSocket events
- Send "read" events with message IDs
- Update local message database
- Trigger status change callbacks
- Support batch status updates (up to 100)
- Atomic database updates
- Status: 'sent' | 'delivered' | 'read'

### Implementation Tasks
1. Implement status update handling
2. Add `mark_as_read()` method
3. Update message storage schema
4. Add status change callbacks
5. Implement batch read receipts
6. Write status tracking tests

### Definition of Done
- [ ] Status tracking works end-to-end
- [ ] Read receipts sent correctly
- [ ] Status persists locally
- [ ] Callbacks trigger appropriately
- [ ] Tests verify all states

### Example Usage
```python
# Send message and track status
message = await client.send_message("user_123", "Hello")
print(f"Initial status: {message.status}")  # 'sent'

# Status updates
@client.on_message_status
async def handle_status(message_id, status):
    print(f"Message {message_id}: {status}")
    # Will print: 'delivered', then 'read'

# Mark messages as read
@client.on_message
async def handle_message(message):
    print(f"Received: {message.content}")
    
    # Mark as read
    await client.mark_as_read(
        peer_id=message.from_user,
        message_ids=[message.id]
    )
```

---

## User Story 10: Image and File Sending

**As a** Python developer  
**I want** to send images and files encrypted  
**So that** my bot can share media content

### Acceptance Criteria
- [ ] I can send images as bytes or file paths
- [ ] Images are encrypted end-to-end
- [ ] Image data is base64 encoded for transmission
- [ ] Received images are automatically decoded
- [ ] I can save received images to disk
- [ ] File size limits are enforced (configurable)
- [ ] Image captions are supported
- [ ] Multiple image formats supported (JPEG, PNG, GIF)

### Technical Requirements
- Accept file path or bytes for images
- Encrypt image data like text messages
- Base64 encode for JSON transport
- Decode and decrypt on receive
- Size limit check (default 5MB)
- Save to configurable directory
- Support common image MIME types
- Optional compression

### Implementation Tasks
1. Add `send_image()` method
2. Implement image encryption
3. Add base64 encoding/decoding
4. Implement image receive handling
5. Add save to file functionality
6. Add size validation
7. Write image tests

### Definition of Done
- [ ] Images send successfully
- [ ] Images encrypted properly
- [ ] Received images decrypted
- [ ] File I/O works correctly
- [ ] Size limits enforced
- [ ] Tests include various formats

### Example Usage
```python
# Send image from file
message = await client.send_image(
    to="user_123",
    image_path="photo.jpg",
    caption="Check this out!"
)

# Send image from bytes
with open("photo.jpg", "rb") as f:
    image_bytes = f.read()

await client.send_image(
    to="user_123",
    image_data=image_bytes
)

# Receive images
@client.on_message
async def handle_message(message):
    if message.type == "image":
        # Save to disk
        await client.save_image(
            message=message,
            path=f"downloads/{message.id}.jpg"
        )
        
        # Or get bytes
        image_bytes = client.decode_image(message.image_data)
```

---

## User Story 11: Key Fingerprint Verification

**As a** Python developer  
**I want** to verify peer encryption key fingerprints  
**So that** I can ensure communication security and prevent MITM attacks

### Acceptance Criteria
- [ ] I can retrieve my own key fingerprint
- [ ] I can get peer's key fingerprint from session
- [ ] I can verify a fingerprint manually
- [ ] Verification status is stored locally
- [ ] Verification status syncs with server
- [ ] I can generate QR code for my fingerprint
- [ ] I can check if a peer's key is verified
- [ ] Verification status is displayed in message metadata

### Technical Requirements
- Compute SHA-256 fingerprint of identity key
- Format as 60-character hex string
- Store verification in local database
- POST to `/api/verify-key` on verification
- GET from `/api/verify-key/{userId}` for status
- QR code generation using `qrcode` library
- Fingerprint comparison utility

### Implementation Tasks
1. Add `get_fingerprint()` method
2. Add `get_peer_fingerprint()` method
3. Implement `verify_fingerprint()` method
4. Add verification storage
5. Implement server sync
6. Add QR code generation
7. Add verification status queries
8. Write verification tests

### Definition of Done
- [ ] Fingerprints retrievable
- [ ] Verification works end-to-end
- [ ] Status persists locally
- [ ] Server sync functional
- [ ] QR codes generated correctly
- [ ] Tests verify security properties

### Example Usage
```python
# Get own fingerprint
my_fingerprint = client.get_fingerprint()
print(f"My fingerprint:\n{my_fingerprint}")

# Get peer fingerprint
peer_fp = await client.get_peer_fingerprint("user_123")
print(f"Peer fingerprint:\n{peer_fp}")

# Verify fingerprint (after out-of-band verification)
await client.verify_fingerprint(
    peer_id="user_123",
    fingerprint=peer_fp,
    verified=True
)

# Check verification status
is_verified = await client.is_fingerprint_verified("user_123")
print(f"Verified: {is_verified}")

# Generate QR code
qr_image = client.generate_fingerprint_qr()
qr_image.save("my_fingerprint_qr.png")

# Compare fingerprints
match = client.compare_fingerprints(
    fingerprint1=my_fingerprint,
    fingerprint2=peer_fp
)
```

---

## User Story 12: Group Chat Support

**As a** Python developer  
**I want** to participate in group chats  
**So that** my bot can interact with multiple users simultaneously

### Acceptance Criteria
- [ ] I can create new groups
- [ ] I can send messages to groups
- [ ] I receive group messages
- [ ] I can add/remove group members (if owner/admin)
- [ ] I can list my groups
- [ ] I can get group member lists
- [ ] I can leave groups
- [ ] Group metadata is accessible (name, description)

### Technical Requirements
- POST to `/api/groups` for creation
- WebSocket "group_message" event type
- Role-based permission checks
- Group membership tracking
- Group message storage
- Member management endpoints
- Group messages NOT E2EE (server-side only)

### Implementation Tasks
1. Add `create_group()` method
2. Implement `send_group_message()` method
3. Add group message handler
4. Implement member management
5. Add group listing/queries
6. Add group storage
7. Write group tests

### Definition of Done
- [ ] Groups created successfully
- [ ] Group messages work bidirectionally
- [ ] Member management functional
- [ ] Permissions enforced
- [ ] Tests cover group scenarios

### Example Usage
```python
# Create group
group = await client.create_group(
    name="Dev Team",
    description="Developers only",
    member_ids=["user1", "user2", "user3"]
)

# Send group message
await client.send_group_message(
    group_id=group.id,
    content="Hello everyone!"
)

# Receive group messages
@client.on_group_message
async def handle_group_msg(message):
    print(f"[{message.group_name}] {message.from_user}: {message.content}")

# Manage members
await client.add_group_member(group.id, "user4")
await client.remove_group_member(group.id, "user2")

# List groups
groups = await client.get_groups()
for group in groups:
    print(f"{group.name}: {len(group.members)} members")
```

---

## User Story 13: Local Storage and Persistence

**As a** Python developer  
**I want** messages and keys to persist locally  
**So that** data is available across client restarts

### Acceptance Criteria
- [ ] All private keys are encrypted before storage
- [ ] Keys persist across client restarts
- [ ] Messages are cached locally
- [ ] Session state persists
- [ ] Storage location is configurable
- [ ] Storage files have secure permissions
- [ ] I can export/import sessions
- [ ] I can clear local data

### Technical Requirements
- SQLite for structured data
- AES-256-GCM for key encryption
- Argon2id for key derivation (memory=64MB, iterations=3)
- File permissions: 0600 (Unix)
- Storage path: `~/.whatsapp_client/{user_id}/`
- Database files: `keys.db`, `messages.db`
- Atomic writes for data integrity

### Implementation Tasks
1. Create `KeyStorage` class
2. Create `MessageStorage` class
3. Implement encryption layer
4. Add session persistence
5. Implement export/import
6. Add data clearing methods
7. Set file permissions
8. Write storage tests

### Definition of Done
- [ ] Keys persist encrypted
- [ ] Messages persist correctly
- [ ] Sessions resume after restart
- [ ] Permissions set securely
- [ ] Export/import functional
- [ ] Tests verify data integrity

### Example Usage
```python
# Configure storage
client = WhatsAppClient(
    server_url="https://worker.dev",
    storage_path="~/my_bot_data"
)

# Keys and messages persist automatically
await client.login("bot", "password")
await client.send_message("user", "Hello")
await client.logout()

# Restart - data restored
await client.login("bot", "password")
messages = await client.get_messages("user")
# Previous messages available

# Export session
session_data = await client.export_session("user_123")
with open("backup.json", "w") as f:
    json.dump(session_data, f)

# Import session
with open("backup.json") as f:
    session_data = json.load(f)
await client.import_session("user_123", session_data)

# Clear data
await client.clear_storage()  # Removes all local data
```

---

## User Story 14: Error Handling and Logging

**As a** Python developer  
**I want** comprehensive error handling and logging  
**So that** I can debug issues and build reliable applications

### Acceptance Criteria
- [ ] All errors have custom exception types
- [ ] Exceptions include helpful error messages
- [ ] Logging is configurable (level, output)
- [ ] Network errors are retried automatically
- [ ] Crypto errors are clearly identified
- [ ] WebSocket disconnects handled gracefully
- [ ] Validation errors raised before operations
- [ ] Stack traces available in debug mode

### Technical Requirements
- Custom exception hierarchy
- Python logging module integration
- Log levels: DEBUG, INFO, WARNING, ERROR
- Configurable log output (file, stdout)
- Retry logic with exponential backoff
- Exception chaining for context
- Type validation with Pydantic
- Structured logging support

### Implementation Tasks
1. Create exception classes
2. Configure logging infrastructure
3. Add retry decorators
4. Implement validation
5. Add error recovery logic
6. Write error handling tests

### Definition of Done
- [ ] All errors properly typed
- [ ] Logging works as configured
- [ ] Retries function correctly
- [ ] Error messages are helpful
- [ ] Tests cover error cases

### Example Usage
```python
import logging
from whatsapp_client import (
    WhatsAppClient,
    AuthenticationError,
    SessionNotFoundError,
    DecryptionError,
    ConnectionError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

client = WhatsAppClient(
    server_url="https://worker.dev",
    log_level="DEBUG"
)

# Error handling
try:
    await client.login("user", "wrong_password")
except AuthenticationError as e:
    print(f"Login failed: {e}")

try:
    await client.send_message("invalid_user", "Hello")
except SessionNotFoundError:
    # Establish session first
    await client._crypto.establish_session("invalid_user")
    await client.send_message("invalid_user", "Hello")
except ConnectionError as e:
    print(f"Network error: {e}")
    # Will auto-retry

# Decryption errors
@client.on_message
async def handle_message(message):
    try:
        # Process message
        pass
    except DecryptionError as e:
        logging.error(f"Cannot decrypt message {message.id}: {e}")
        # Request key re-exchange
        await client.request_key_refresh(message.from_user)
```

---

## User Story 15: Configuration and Customization

**As a** Python developer  
**I want** configurable client settings  
**So that** I can customize behavior for my use case

### Acceptance Criteria
- [ ] Server URL is configurable
- [ ] Storage path is configurable
- [ ] Auto-reconnect can be disabled
- [ ] Reconnect delay is configurable
- [ ] Message cache size is configurable
- [ ] Prekey generation count is configurable
- [ ] Session timeout is configurable
- [ ] Configuration can be loaded from file

### Technical Requirements
- Configuration via constructor arguments
- Config file support (YAML/JSON)
- Environment variable support
- Sensible defaults provided
- Validation of config values
- Config schema documentation
- Override priority: args > env > file > defaults

### Implementation Tasks
1. Create configuration class
2. Add file loading (YAML/JSON)
3. Add environment variable support
4. Implement validation
5. Add config property access
6. Write configuration tests

### Definition of Done
- [ ] All settings configurable
- [ ] Config files work
- [ ] Environment vars work
- [ ] Validation functional
- [ ] Documentation complete

### Example Usage
```python
# Via constructor
client = WhatsAppClient(
    server_url="https://worker.dev",
    storage_path="~/bot_data",
    auto_reconnect=True,
    reconnect_delay=5,
    prekey_count=200,
    session_timeout_days=60
)

# Via config file
# config.yaml:
# server:
#   url: "https://worker.dev"
# storage:
#   path: "~/bot_data"
# connection:
#   auto_reconnect: true
#   reconnect_delay: 5

client = WhatsAppClient.from_config("config.yaml")

# Via environment variables
# WHATSAPP_SERVER_URL=https://worker.dev
# WHATSAPP_STORAGE_PATH=~/bot_data

import os
client = WhatsAppClient(
    server_url=os.getenv("WHATSAPP_SERVER_URL"),
    storage_path=os.getenv("WHATSAPP_STORAGE_PATH")
)

# Access config
print(f"Server: {client.config.server_url}")
print(f"Storage: {client.config.storage_path}")
```

---

## User Story 16: Async Event Loop Integration

**As a** Python developer  
**I want** seamless asyncio integration  
**So that** the client works well with other async libraries

### Acceptance Criteria
- [ ] All I/O operations are async
- [ ] Client works with existing event loops
- [ ] Multiple clients can run concurrently
- [ ] Background tasks are properly managed
- [ ] Graceful shutdown closes all tasks
- [ ] Compatible with asyncio, trio, curio
- [ ] No blocking calls in async context
- [ ] Task cancellation handled properly

### Technical Requirements
- Async/await for all network operations
- Use `asyncio.create_task()` for background work
- Implement `__aenter__` and `__aexit__`
- Track all background tasks
- Cancel tasks on shutdown
- Use `anyio` for async backend abstraction
- No `time.sleep()`, use `asyncio.sleep()`

### Implementation Tasks
1. Ensure all methods are async
2. Implement context manager protocol
3. Add task tracking
4. Implement graceful shutdown
5. Add anyio support (optional)
6. Write async integration tests

### Definition of Done
- [ ] All I/O is non-blocking
- [ ] Multiple clients work together
- [ ] Shutdown is clean
- [ ] Tasks don't leak
- [ ] Tests verify async behavior

### Example Usage
```python
import asyncio
from whatsapp_client import WhatsAppClient

async def run_bot():
    async with WhatsAppClient(server_url="...") as client:
        await client.login("bot", "password")
        
        @client.on_message
        async def handle(msg):
            await client.send_message(msg.from_user, "Echo: " + msg.content)
        
        # Keep running
        await asyncio.Event().wait()
    # Auto-cleanup on exit

# Multiple clients
async def main():
    bot1 = WhatsAppClient(server_url="...")
    bot2 = WhatsAppClient(server_url="...")
    
    await bot1.login("bot1", "pass1")
    await bot2.login("bot2", "pass2")
    
    # Both run concurrently
    await asyncio.gather(
        bot1.run(),
        bot2.run()
    )

asyncio.run(main())
```

---

## User Story 17: Testing and Examples

**As a** Python developer  
**I want** comprehensive tests and examples  
**So that** I can understand usage and trust the library

### Acceptance Criteria
- [ ] Unit tests for all modules (80%+ coverage)
- [ ] Integration tests with mock server
- [ ] Example bots provided (echo, command, group)
- [ ] Documentation includes code examples
- [ ] README has quickstart guide
- [ ] API reference auto-generated
- [ ] Test suite runs in CI/CD
- [ ] Performance benchmarks provided

### Technical Requirements
- pytest for testing
- pytest-asyncio for async tests
- aioresponses for HTTP mocking
- Test fixtures for common setup
- Sphinx for documentation
- GitHub Actions for CI
- Coverage reporting (codecov)
- Type checking (mypy) in CI

### Implementation Tasks
1. Write unit tests for all modules
2. Create integration test suite
3. Add mock server for testing
4. Create example bots
5. Write documentation
6. Set up CI/CD pipeline
7. Add performance benchmarks

### Definition of Done
- [ ] 80%+ test coverage achieved
- [ ] All tests passing
- [ ] Examples working
- [ ] Documentation complete
- [ ] CI/CD configured
- [ ] Benchmarks documented

### Example Tests
```python
# tests/test_messaging.py
import pytest
from whatsapp_client import WhatsAppClient

@pytest.mark.asyncio
async def test_send_message(mock_server):
    client = WhatsAppClient(server_url=mock_server.url)
    await client.login("alice", "password")
    
    message = await client.send_message("bob", "Hello")
    
    assert message.content == "Hello"
    assert message.status == "sent"
    assert message.to == "bob"

@pytest.mark.asyncio
async def test_encryption_decryption():
    alice = WhatsAppClient(server_url="...")
    bob = WhatsAppClient(server_url="...")
    
    await alice.register("alice", "pass1")
    await bob.register("bob", "pass2")
    
    # Alice sends to Bob
    sent = await alice.send_message(bob.user_id, "Secret message")
    
    # Bob receives
    received = None
    @bob.on_message
    async def handle(msg):
        nonlocal received
        received = msg
    
    await asyncio.sleep(0.5)  # Wait for delivery
    
    assert received.content == "Secret message"
    assert received.from_user == alice.user_id
```

### Example Bots
```python
# examples/echo_bot.py
"""Simple echo bot that replies to all messages."""
import asyncio
from whatsapp_client import WhatsAppClient

async def main():
    client = WhatsAppClient(server_url="https://worker.dev")
    await client.login("echo_bot", "password")
    
    print(f"Echo bot started as {client.user.username}")
    
    @client.on_message
    async def echo(message):
        await client.send_message(
            to=message.from_user,
            content=f"Echo: {message.content}"
        )
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## User Story 18: Package Distribution

**As a** Python developer  
**I want** to install the library via pip  
**So that** I can easily add it to my projects

### Acceptance Criteria
- [ ] Package published to PyPI
- [ ] Installable via `pip install whatsapp-client`
- [ ] All dependencies installed automatically
- [ ] Works with pip, poetry, pipenv
- [ ] Supports Python 3.9-3.12
- [ ] Wheels provided for major platforms
- [ ] Version follows semantic versioning
- [ ] Changelog maintained

### Technical Requirements
- setuptools or poetry for packaging
- pyproject.toml configuration
- Proper dependency specifications
- Platform wheels (manylinux, macOS, Windows)
- Source distribution (sdist)
- PyPI upload automation
- Git tags for versions
- Automated releases

### Implementation Tasks
1. Create pyproject.toml
2. Configure build system
3. Build wheels for platforms
4. Set up PyPI account/tokens
5. Create release workflow
6. Write installation docs
7. Test installation process

### Definition of Done
- [ ] Package on PyPI
- [ ] Installation works on all platforms
- [ ] Dependencies resolve correctly
- [ ] Wheels available
- [ ] Automated release process
- [ ] Installation documented

### Example Installation
```bash
# Install latest version
pip install whatsapp-client

# Install specific version
pip install whatsapp-client==1.0.0

# Install with extras
pip install whatsapp-client[qr]  # QR code support

# Install from git (development)
pip install git+https://github.com/user/whatsapp-client.git

# With poetry
poetry add whatsapp-client

# With pipenv
pipenv install whatsapp-client
```

---

## Epic Summary

### Implementation Order (Recommended)

1. **US1**: Client Initialization and Authentication
2. **US2**: Cryptographic Key Generation and Management
3. **US3**: Session Establishment (X3DH Protocol)
4. **US4**: Message Encryption (Double Ratchet)
5. **US5**: Message Decryption (Double Ratchet)
6. **US7**: WebSocket Connection Management
7. **US6**: Send and Receive Text Messages
8. **US9**: Message Status Tracking and Read Receipts
9. **US8**: Typing Indicators and Presence
10. **US13**: Local Storage and Persistence
11. **US11**: Key Fingerprint Verification
12. **US10**: Image and File Sending
13. **US12**: Group Chat Support
14. **US14**: Error Handling and Logging
15. **US15**: Configuration and Customization
16. **US16**: Async Event Loop Integration
17. **US17**: Testing and Examples
18. **US18**: Package Distribution

### Total Story Points Estimate

Assuming complexity scoring:
- Simple: 1-2 points
- Medium: 3-5 points
- Complex: 8-13 points

| User Story | Complexity | Points |
|-----------|------------|--------|
| US1 | Simple | 2 |
| US2 | Complex | 13 |
| US3 | Complex | 13 |
| US4 | Complex | 13 |
| US5 | Complex | 13 |
| US6 | Medium | 5 |
| US7 | Medium | 5 |
| US8 | Simple | 2 |
| US9 | Medium | 3 |
| US10 | Medium | 5 |
| US11 | Medium | 5 |
| US12 | Medium | 5 |
| US13 | Medium | 5 |
| US14 | Medium | 3 |
| US15 | Simple | 2 |
| US16 | Medium | 3 |
| US17 | Medium | 5 |
| US18 | Medium | 3 |
| **Total** | | **105** |

**Estimated Timeline:** 8-12 weeks for a single developer, 4-6 weeks for a small team.

---

## Acceptance Criteria for Epic Completion

- [ ] All 18 user stories completed
- [ ] 80%+ test coverage achieved
- [ ] Package published to PyPI
- [ ] Documentation complete (API reference, tutorials, examples)
- [ ] Compatible with React frontend (session interoperability)
- [ ] All E2EE features functional
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Example bots working
- [ ] Installation guide validated on Windows, macOS, Linux

---

## Notes

- **Security Critical**: User Stories 2-5, 11 require careful implementation and security review
- **Performance Critical**: User Stories 4-5 (encryption/decryption) should be optimized
- **Dependencies**: US4-5 depend on US2-3; US6 depends on US4-5-7
- **Optional Features**: QR code generation (US11) can be optional dependency
- **Testing**: Each US should have unit and integration tests before completion
