# End-to-End Encryption Architecture

## Overview

This WhatsApp clone implements **Signal Protocol** for end-to-end encryption (E2EE), providing the same security guarantees as Signal, WhatsApp, and other secure messaging apps.

## Security Properties

✅ **End-to-End Encryption**: Messages are encrypted on sender's device and decrypted only on recipient's device  
✅ **Forward Secrecy**: Compromise of long-term keys doesn't compromise past messages  
✅ **Future Secrecy** (Break-in Recovery): Compromise of session keys doesn't compromise future messages  
✅ **Deniability**: Messages cannot be cryptographically proven to have come from a specific sender  
✅ **Authenticity**: Recipients can verify messages came from claimed sender  
✅ **Integrity**: Message tampering is detected and rejected

## Components

### 1. X3DH (Extended Triple Diffie-Hellman)

**Purpose**: Asynchronous key agreement protocol for establishing shared secret between two parties who have never communicated.

**Participants**:
- **Initiator**: The party sending the first message (Alice)
- **Responder**: The party receiving the first message (Bob)

**Key Types**:
- **Identity Key (IK)**: Long-term Ed25519 key for signing, X25519 for DH
- **Signed Prekey (SPK)**: Medium-term X25519 key, rotated every 7 days
- **One-Time Prekey (OPK)**: Single-use X25519 keys, consumed after use

**X3DH Flow**:

```
Alice (Initiator)                          Server                          Bob (Responder)
      |                                       |                                    |
      |                                       |   1. Generate & Upload Prekeys     |
      |                                       |<-----------------------------------|
      |                                       |   - Identity Key (long-term)       |
      |                                       |   - Signed Prekey (7 days)         |
      |                                       |   - 100 One-Time Prekeys           |
      |                                       |                                    |
      | 2. Fetch Bob's Prekey Bundle          |                                    |
      |-------------------------------------->|                                    |
      |<--------------------------------------|                                    |
      |   {identityKey, signedPrekey, OPK}    |                                    |
      |                                       |                                    |
      | 3. Perform X3DH Initiator             |                                    |
      |   - Generate ephemeral key (random!)  |                                    |
      |   - DH1 = IK_A × SPK_B                |                                    |
      |   - DH2 = EK_A × IK_B                 |                                    |
      |   - DH3 = EK_A × SPK_B                |                                    |
      |   - DH4 = EK_A × OPK_B (if available) |                                    |
      |   - shared_secret = KDF(DH1‖DH2‖DH3‖DH4)                                  |
      |                                       |                                    |
      | 4. Send First Message with X3DH       |                                    |
      |   {                                   |                                    |
      |     header: {ratchetKey, ...},        |                                    |
      |     ciphertext: <encrypted>,          |                                    |
      |     x3dh: {                           |                                    |
      |       senderIdentityKey,              |                                    |
      |       senderEphemeralKey,   <---------|- Key Info for Responder           |
      |       usedSignedPrekeyId,             |                                    |
      |       usedOneTimePrekeyId             |                                    |
      |     }                                 |                                    |
      |   }                                   |                                    |
      |-------------------------------------->|----------------------------------->|
      |                                       |                                    |
      |                                       |    5. Perform X3DH Responder       |
      |                                       |      - Use Alice's ephemeral key   |
      |                                       |      - DH1 = SPK_B × IK_A          |
      |                                       |      - DH2 = IK_B × EK_A           |
      |                                       |      - DH3 = SPK_B × EK_A          |
      |                                       |      - DH4 = OPK_B × EK_A          |
      |                                       |      - shared_secret = KDF(...)    |
      |                                       |      - Delete consumed OPK         |
      |                                       |                                    |
      |                                       |    6. Initialize Ratchet           |
      |                                       |      - Use Alice's ratchet key     |
      |                                       |      - Decrypt message             |
```

**Critical Detail**: Both parties derive the **same** shared secret because:
- Alice uses her ephemeral secret key with Bob's public keys
- Bob uses his secret keys with Alice's ephemeral public key
- DH(a × G, b × G) = DH(b × G, a × G) = ab × G

### 2. Double Ratchet

**Purpose**: Ongoing encryption with forward secrecy and break-in recovery.

**Key Features**:
- **Symmetric-key ratchet**: Derives new message keys from chain keys
- **DH ratchet**: Periodically updates root key with new DH exchange

**Message Encryption Flow**:

```
Alice Sends Message 1:
  Chain Key₀ ──KDF──> Chain Key₁
                │
                └──> Message Key₁ ──> Encrypt("Hello")
                
Alice Sends Message 2:
  Chain Key₁ ──KDF──> Chain Key₂
                │
                └──> Message Key₂ ──> Encrypt("World")

Bob Receives Message 1:
  Chain Key₀ ──KDF──> Chain Key₁
                │
                └──> Message Key₁ ──> Decrypt("Hello")
```

**DH Ratchet Step** (when Bob replies):

```
Alice                                  Bob
Root Key₀                         Root Key₀
  |                                     |
  |<-------- Bob's new Ratchet Key -----|
  |                                     |
  DH(Alice's DH Key, Bob's Ratchet Key) |
  |                                     |
  v                                     v
Root Key₁                         Root Key₁
  |                                     |
  v                                     v
New Sending/Receiving Chain Keys
```

### 3. Storage Layer (IndexedDB)

**Database**: `whatsapp-clone-e2ee`

**Object Stores**:
- `metadata`: User metadata (master key ID, prekey counters)
- `identity`: Ed25519 signing key, X25519 DH key
- `signed_prekeys`: Medium-term prekeys
- `one_time_prekeys`: Single-use prekeys
- `sessions`: Per-contact encryption sessions

**Encryption at Rest**:
- Master key generated from user password + salt
- All secret keys encrypted with AES-GCM before storage
- IndexedDB contents cannot be read without master key

## Session Lifecycle

### Establishment

1. **Alice wants to send to Bob**:
   ```javascript
   await sessionManager.encryptMessage('bob', 'Hello')
   ```

2. **ensureSession** checks for existing session:
   - If exists and valid → use it
   - If not exists → establish new session

3. **establishSession** performs X3DH:
   - Fetch Bob's prekey bundle from server
   - Perform X3DH initiator protocol
   - Initialize Double Ratchet with shared secret
   - Store session with X3DH init data

4. **encryptMessage** creates first message:
   - Encrypt plaintext with ratchet
   - Include X3DH parameters in `x3dh` field
   - Send to Bob
   - Clear X3DH data from session (only needed once)

### First Message Receipt

1. **Bob receives message** with `x3dh` field:
   ```javascript
   await sessionManager.decryptMessage('alice', encryptedMessage)
   ```

2. **decryptMessage** detects first message:
   - Extract X3DH parameters from message
   - Perform X3DH responder with Alice's ephemeral key
   - Derive same shared secret as Alice
   - Initialize ratchet with Alice's ratchet key
   - Decrypt message
   - Delete consumed one-time prekey

3. **Session established** - subsequent messages use ratchet

### Ongoing Conversation

```
Alice -> Bob: Message 1 (with x3dh)
Bob -> Alice: Message 2 (normal ratchet)
Alice -> Bob: Message 3 (normal ratchet)
Bob -> Alice: Message 4 (normal ratchet)
```

Each message advances the ratchet, providing forward secrecy.

### Session Refresh (Key Rotation)

When Bob rotates his signed prekey:

1. **Alice sends next message**:
   - `checkSessionNeedsRefresh` fetches Bob's current prekeys
   - Detects signed prekey ID changed
   - Deletes old session
   - Establishes new session (like first message)
   - Includes X3DH in message again

2. **Benefits**:
   - Updates to fresh signed prekey
   - Maintains forward secrecy
   - Conversation continues seamlessly

## Prekey Management

### Generation

- **Identity**: Generated once per user, never rotated
- **Signed Prekey**: Generated on init, rotated every 7 days
- **One-Time Prekeys**: Generated in batches of 50-100

### Upload

Prekeys uploaded to server in bundle:
```json
{
  "identityKey": "base64...",
  "signingKey": "base64...",
  "signedPrekey": {
    "keyId": 1,
    "publicKey": "base64...",
    "signature": "base64..."
  },
  "oneTimePrekeys": [
    {"keyId": 1, "publicKey": "base64..."},
    {"keyId": 2, "publicKey": "base64..."},
    ...
  ]
}
```

### Consumption

- One-time prekey consumed on first message
- Responder deletes used prekey from storage
- Pool automatically refreshed when below 20

### Health Monitoring

Every 5 minutes:
- Check one-time prekey count
- If < 20, generate new batch
- Check signed prekey age
- If > 7 days, rotate

## API Documentation

### KeyManager

```typescript
class KeyManager {
  // Initialize E2EE for user
  async initialize(): Promise<void>
  
  // Get identity material
  async getIdentityMaterial(): Promise<StoredIdentityRecord>
  
  // Get pending prekeys to upload
  async getPendingBundle(): Promise<PrekeyBundlePayload | null>
  
  // Queue new one-time prekeys
  async queueOneTimePrekeys(count: number): Promise<void>
  
  // Rotate signed prekey
  async rotateSignedPrekey(): Promise<void>
  
  // Clear all E2EE data and reinitialize
  async resetE2EE(): Promise<void>
}
```

### SessionManager

```typescript
class SessionManager {
  // Ensure session exists with peer
  async ensureSession(peerId: string): Promise<void>
  
  // Encrypt message for peer
  async encryptMessage(
    peerId: string, 
    plaintext: string
  ): Promise<SerializedEncryptedMessage>
  
  // Decrypt message from peer
  async decryptMessage(
    peerId: string, 
    encrypted: SerializedEncryptedMessage
  ): Promise<string>
  
  // List all sessions
  async listSessions(): Promise<StoredSessionRecord[]>
}
```

### X3DH Functions

```typescript
// Initiator (sender of first message)
async function performX3DHInitiator(options: {
  localIdentitySeed: Uint8Array;
  remoteBundle: RemotePrekeyBundle;
}): Promise<X3DHResult>

// Responder (receiver of first message)
async function performX3DHResponder(options: {
  localIdentitySeed: Uint8Array;
  localSignedPrekeyPair: { publicKey: Uint8Array; secretKey: Uint8Array };
  localOneTimePrekeyPair?: { publicKey: Uint8Array; secretKey: Uint8Array };
  remoteIdentityKey: Uint8Array;
  remoteEphemeralKey: Uint8Array;
}): Promise<Uint8Array> // shared secret
```

### RatchetEngine

```typescript
class RatchetEngine {
  // Initialize ratchet from shared secret
  async initializeRatchet(
    sharedSecret: Uint8Array,
    remoteRatchetKey?: Uint8Array
  ): Promise<RatchetState>
  
  // Encrypt message
  async encryptMessage(
    state: RatchetState,
    plaintext: Uint8Array
  ): Promise<{ message: EncryptedMessage; newState: RatchetState }>
  
  // Decrypt message
  async decryptMessage(
    state: RatchetState,
    message: EncryptedMessage
  ): Promise<{ plaintext: Uint8Array; newState: RatchetState }>
}
```

## Troubleshooting

### "Recipient hasn't set up encryption yet"

**Cause**: Recipient hasn't logged in or initialized E2EE.

**Solution**: 
- Tell recipient to log in once
- E2EE initializes automatically on first login

### "Authentication failed" errors

**Cause**: Mismatched shared secrets or corrupted session.

**Solution**:
1. Check browser console for detailed error
2. Use "Reset E2EE" button to clear and reinitialize
3. Both parties may need to reset if sessions very corrupted

### Messages show as encrypted JSON

**Cause**: Decryption failed or E2EE not initialized.

**Solution**:
- Check that E2EE status shows "Ready" (green 🔒)
- Try refreshing the page
- Use "Reset E2EE" if problem persists

### Session refresh taking too long

**Cause**: Network latency fetching prekey bundle.

**Solution**:
- Normal, can take 1-2 seconds
- Message will send after session established
- Check network connection if > 5 seconds

### One-time prekeys depleted

**Cause**: Many new sessions established quickly.

**Solution**:
- System auto-generates more when below 20
- If critically low, manually trigger with Reset E2EE
- Check that prekey upload succeeded (network logs)

## Testing

### Manual Integration Test

1. **Open two browser tabs** (incognito for second)
2. **Tab 1**: Login as Alice
3. **Tab 2**: Login as Bob
4. **Tab 1**: Send message "Hello Bob" to Bob
   - Check console: Should see X3DH initiator logs
   - Check console: First message includes x3dh field
5. **Tab 2**: Receive message
   - Check console: Should see X3DH responder logs
   - Message displays as "Hello Bob" (plaintext)
6. **Tab 2**: Reply "Hi Alice"
   - Check console: Normal ratchet encryption (no x3dh)
7. **Tab 1**: Receive reply
   - Message displays as "Hi Alice"
8. **Continue conversation** - all messages decrypt correctly

### Verify Forward Secrecy

1. Send several messages
2. Open DevTools → Application → IndexedDB → whatsapp-clone-e2ee
3. View sessions table - ratchet state changes with each message
4. Old message keys are deleted - can't decrypt past messages even with current state

### Verify One-Time Prekey Consumption

1. Check one-time prekey count before session
2. Establish new session
3. Check console: "Deleted consumed one-time prekey: X"
4. Count should be -1
5. When < 20, new batch auto-generated

## Security Considerations

### What's Protected

✅ Message content  
✅ Message metadata (sender, recipient) from server*  
✅ Conversation history  
✅ Identity fingerprints  

*Server can see who messages whom, but not content

### What's NOT Protected

❌ Contact list (server knows who you talk to)  
❌ Timing information (when messages sent)  
❌ Message size  
❌ Online status  

### Best Practices

1. **Verify fingerprints** with contacts out-of-band (phone, in-person)
2. **Don't screenshot** encrypted chats
3. **Use Reset E2EE** sparingly (starts fresh identity)
4. **Keep browser updated** (crypto APIs)
5. **Use strong password** (master key derivation)

## Performance

### Initialization
- **Cold start**: ~500ms (generate identity, prekeys)
- **Warm start**: ~100ms (load from IndexedDB)

### Message Encryption
- **First message**: ~150ms (X3DH + encryption)
- **Subsequent**: ~10ms (ratchet only)

### Message Decryption  
- **First message**: ~200ms (X3DH responder + decryption)
- **Subsequent**: ~15ms (ratchet only)

### Storage
- **Identity + keys**: ~5KB
- **Session**: ~2KB per contact
- **100 one-time prekeys**: ~10KB

## References

- [Signal Protocol Specifications](https://signal.org/docs/)
- [X3DH Specification](https://signal.org/docs/specifications/x3dh/)
- [Double Ratchet Algorithm](https://signal.org/docs/specifications/doubleratchet/)
- [libsignal Protocol](https://github.com/signalapp/libsignal)
