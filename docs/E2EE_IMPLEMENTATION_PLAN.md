# E2EE Signal Protocol - Proper Implementation Plan

## Current Issues

The current implementation fails because:

1. **Both parties independently perform X3DH** - Sender and receiver each generate their own ephemeral keys, leading to different shared secrets
2. **No session synchronization** - Ratchet states diverge immediately after initialization
3. **One-time prekey mismatch** - Sender may use a one-time prekey that receiver doesn't have access to
4. **Missing initiator metadata** - First message doesn't contain X3DH parameters needed by responder

## Proper Signal Protocol Flow

### Phase 1: Initial Handshake (X3DH)

**Initiator (Alice) sends first message to Responder (Bob):**

1. Alice fetches Bob's prekey bundle from server
2. Alice performs X3DH:
   - Generates ephemeral key pair `EK_A`
   - Computes DH outputs: `DH1`, `DH2`, `DH3`, `DH4` (if one-time prekey available)
   - Derives shared secret `SK`
3. Alice initializes Double Ratchet with `SK`
4. Alice encrypts message with ratchet
5. **Alice sends message with X3DH initialization data:**
   - `IK_A` (Alice's identity key)
   - `EK_A` (Alice's ephemeral public key)
   - `used_prekey_id` (which of Bob's one-time prekeys was used)
   - Encrypted message payload

**Responder (Bob) receives first message:**

1. Bob extracts X3DH parameters from message
2. Bob performs X3DH as responder:
   - Uses Alice's `EK_A` (from message)
   - Uses his own `SPK` (signed prekey) secret key
   - Uses his own `OPK` (one-time prekey) if `used_prekey_id` is present
   - Computes same DH outputs: `DH1`, `DH2`, `DH3`, `DH4`
   - Derives same shared secret `SK`
3. Bob initializes Double Ratchet with `SK`
4. Bob decrypts message

### Phase 2: Ongoing Messages (Double Ratchet)

Both parties maintain synchronized ratchet state through message headers.

## Implementation Tasks

### Task 1: Extend Message Format ✅ (Already exists)

**Current message format already supports metadata:**
```typescript
interface SerializedEncryptedMessage {
  header: {
    ratchetKey: string;        // DH ratchet public key
    previousChainLength: number;
    messageNumber: number;
  };
  ciphertext: string;
  authTag: string;
}
```

**Add X3DH initialization data (optional, only on first message):**
```typescript
interface SerializedEncryptedMessage {
  header: {
    ratchetKey: string;
    previousChainLength: number;
    messageNumber: number;
  };
  ciphertext: string;
  authTag: string;
  // NEW: X3DH initialization (only present on first message)
  x3dh?: {
    senderIdentityKey: string;      // Base64 encoded
    senderEphemeralKey: string;     // Base64 encoded  
    usedSignedPrekeyId: number;
    usedOneTimePrekeyId?: number;
  };
}
```

**Files to modify:**
- `src/client/crypto/RatchetEngine.ts` - Update interfaces
- `src/client/crypto/types.ts` - Update type definitions

---

### Task 2: Implement X3DH Responder

**Create responder function that uses initiator's ephemeral key:**

```typescript
// src/client/crypto/X3DH.ts

export async function performX3DHResponder(options: {
  localIdentitySeed: Uint8Array;
  localSignedPrekeyPair: { publicKey: Uint8Array; secretKey: Uint8Array };
  localOneTimePrekeyPair?: { publicKey: Uint8Array; secretKey: Uint8Array };
  remoteIdentityKey: Uint8Array;
  remoteEphemeralKey: Uint8Array;  // From first message
}): Promise<Uint8Array> {
  // Compute DH outputs (same as initiator but with swapped roles)
  const dh1 = nacl.scalarMult(localSignedPrekeyPair.secretKey, remoteIdentityKey);
  const dh2 = nacl.scalarMult(localIdentityKeypair.secretKey, remoteEphemeralKey);
  const dh3 = nacl.scalarMult(localSignedPrekeyPair.secretKey, remoteEphemeralKey);
  
  const dhChunks = [dh1, dh2, dh3];
  
  if (localOneTimePrekeyPair) {
    const dh4 = nacl.scalarMult(localOneTimePrekeyPair.secretKey, remoteEphemeralKey);
    dhChunks.push(dh4);
  }
  
  const sharedSecret = await hkdf(concatUint8Arrays(dhChunks), {
    info: encodeUtf8('WHATSAPP-CLONE-X3DH'),
    length: 32,
  });
  
  return sharedSecret;
}
```

**Files to modify:**
- `src/client/crypto/X3DH.ts` - Add responder function

---

### Task 3: Update SessionManager to Detect Role

**Modify session establishment to detect initiator vs responder:**

```typescript
// src/client/crypto/SessionManager.ts

async decryptMessage(
  peerId: string,
  serializedMessage: SerializedEncryptedMessage
): Promise<string> {
  // Check if this is the first message (contains X3DH data)
  if (serializedMessage.x3dh) {
    console.log('[SessionManager] First message from', peerId, '- establishing session as responder');
    
    // Load our prekeys
    const signedPrekey = await this.keyManager.getSignedPrekey();
    let oneTimePrekeyPair;
    
    if (serializedMessage.x3dh.usedOneTimePrekeyId !== undefined) {
      oneTimePrekeyPair = await this.storage.loadOneTimePrekey(
        serializedMessage.x3dh.usedOneTimePrekeyId
      );
      
      // Delete used one-time prekey
      await this.storage.deleteOneTimePrekey(serializedMessage.x3dh.usedOneTimePrekeyId);
    }
    
    // Perform X3DH as responder
    const sharedSecret = await performX3DHResponder({
      localIdentitySeed: (await this.keyManager.getIdentityMaterial()).seed,
      localSignedPrekeyPair: {
        publicKey: fromBase64(signedPrekey.publicKey),
        secretKey: await this.storage.getSignedPrekeySecret(signedPrekey.keyId),
      },
      localOneTimePrekeyPair: oneTimePrekeyPair ? {
        publicKey: fromBase64(oneTimePrekeyPair.publicKey),
        secretKey: fromBase64(oneTimePrekeyPair.secretKey),
      } : undefined,
      remoteIdentityKey: fromBase64(serializedMessage.x3dh.senderIdentityKey),
      remoteEphemeralKey: fromBase64(serializedMessage.x3dh.senderEphemeralKey),
    });
    
    // Initialize ratchet with shared secret and sender's first ratchet key
    const ratchetState = await this.ratchetEngine.initializeRatchet(
      sharedSecret,
      fromBase64(serializedMessage.header.ratchetKey) // Remote ratchet key
    );
    
    // Save session
    await this.saveSession(peerId, {
      sharedSecret,
      ratchetState,
      remoteIdentityKey: fromBase64(serializedMessage.x3dh.senderIdentityKey),
    });
  }
  
  // Now decrypt normally
  const session = await this.ensureSession(peerId);
  // ... rest of decryption logic
}
```

**Files to modify:**
- `src/client/crypto/SessionManager.ts` - Add X3DH responder logic
- `src/client/storage/KeyStorage.ts` - Add methods to load/delete one-time prekeys by ID

---

### Task 4: Update Encryption to Include X3DH on First Message

**Modify encryptMessage to detect if this is the first message to a peer:**

```typescript
// src/client/crypto/SessionManager.ts

async encryptMessage(
  peerId: string,
  plaintext: string
): Promise<SerializedEncryptedMessage> {
  // Check if session exists
  const existingSession = await this.storage.loadSession(peerId);
  const isFirstMessage = !existingSession;
  
  // Ensure session (performs X3DH if needed)
  const session = await this.ensureSession(peerId);
  
  // Encrypt message
  const encrypted = await this.ratchetEngine.encryptMessage(...);
  const serialized = this.ratchetEngine.serializeMessage(encrypted);
  
  // Add X3DH data if this is the first message
  if (isFirstMessage && session.x3dhData) {
    serialized.x3dh = {
      senderIdentityKey: toBase64(session.x3dhData.localIdentityKey),
      senderEphemeralKey: toBase64(session.x3dhData.localEphemeralKey),
      usedSignedPrekeyId: session.x3dhData.usedSignedPrekeyId,
      usedOneTimePrekeyId: session.x3dhData.usedOneTimePrekeyId,
    };
  }
  
  return serialized;
}
```

**Need to store X3DH metadata in session:**

```typescript
interface StoredSessionRecord {
  // ... existing fields
  x3dhData?: {
    localIdentityKey: Uint8Array;
    localEphemeralKey: Uint8Array;
    usedSignedPrekeyId: number;
    usedOneTimePrekeyId?: number;
  };
}
```

**Files to modify:**
- `src/client/crypto/SessionManager.ts` - Store and send X3DH data
- `src/client/storage/KeyStorage.ts` - Update session storage schema

---

### Task 5: Fix RatchetEngine Initialization

**Ensure receiver initializes ratchet correctly:**

Current code initializes with:
- `receivingChainKey = null` (sender)
- `sendingChainKey = null` (receiver)

Should be:
- **Sender**: `sendingChainKey = derived`, `receivingChainKey = null`, generates DH ratchet key
- **Receiver**: `receivingChainKey = derived`, `sendingChainKey = null`, uses sender's DH ratchet key

```typescript
// src/client/crypto/RatchetEngine.ts

async initializeRatchet(
  sharedSecret: Uint8Array,
  remoteRatchetKey?: Uint8Array  // Present for receiver, absent for sender
): Promise<RatchetState> {
  const kdfOutput = await this.kdfRootKey(sharedSecret, new Uint8Array(32));

  const state: RatchetState = {
    rootKey: kdfOutput.rootKey,
    sendingChainKey: null,
    receivingChainKey: null,
    dhRatchetKeyPair: null,
    dhRatchetRemoteKey: remoteRatchetKey || null,
    sendingChainLength: 0,
    receivingChainLength: 0,
    previousSendingChainLength: 0,
    skippedMessageKeys: new Map(),
  };

  if (!remoteRatchetKey) {
    // SENDER: Initialize sending chain
    const ratchetKeyPair = nacl.box.keyPair();
    state.dhRatchetKeyPair = ratchetKeyPair;
    state.sendingChainKey = kdfOutput.chainKey;
  } else {
    // RECEIVER: Initialize receiving chain
    state.receivingChainKey = kdfOutput.chainKey;
  }

  return state;
}
```

**Files to modify:**
- `src/client/crypto/RatchetEngine.ts` - Fix initialization logic ✅ (Already correct)

---

### Task 6: Handle Session Cleanup

**Delete consumed one-time prekeys:**

```typescript
// After successful first message decryption
if (serializedMessage.x3dh?.usedOneTimePrekeyId) {
  await this.storage.deleteOneTimePrekey(
    serializedMessage.x3dh.usedOneTimePrekeyId
  );
  
  // Upload fresh one-time prekeys if running low
  const prekeyCount = await this.storage.countOneTimePrekeys();
  if (prekeyCount < ONE_TIME_PREKEY_MINIMUM) {
    await this.keyManager.generateAndUploadOneTimePrekeys();
  }
}
```

**Files to modify:**
- `src/client/storage/KeyStorage.ts` - Add deleteOneTimePrekey, countOneTimePrekeys
- `src/client/crypto/SessionManager.ts` - Cleanup and refresh logic

---

### Task 7: Remove Deterministic Ephemeral Keys

**Revert to random ephemeral keys** since proper X3DH will share them:

```typescript
// src/client/crypto/X3DH.ts

// REMOVE: deriveDeterministicEphemeralKeyPair function

// In performX3DHInitiator:
const ephemeralKeyPair = nacl.box.keyPair();  // Back to random
```

**Files to modify:**
- `src/client/crypto/X3DH.ts` - Remove deterministic key generation

---

### Task 8: Re-enable E2EE in App.tsx

**Remove temporary disable flag:**

```typescript
// src/client/App.tsx

const handleSendMessage = useCallback(async (to: string, content: string) => {
  if (!e2eeReady) {
    console.warn('[E2EE] Not ready, sending unencrypted');
    sendMessage(to, content, false);
    return;
  }

  try {
    await ensureSession(to);
    
    const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).slice(2);
    const sentMessage: Message = {
      id: messageId,
      from: currentUser!.id,
      to,
      content,
      timestamp: Date.now(),
      status: 'sent',
      type: 'text',
    };
    
    setMessages((prev) => [...prev, sentMessage]);
    
    const encrypted = await encryptMessage(to, content);
    const encryptedPayload = JSON.stringify(encrypted);
    sendMessage(to, encryptedPayload, true, messageId);
  } catch (err) {
    console.error('[E2EE] Encryption failed:', err);
    sendMessage(to, content, false);
  }
}, [e2eeReady, currentUser, ensureSession, encryptMessage, sendMessage]);
```

**Files to modify:**
- `src/client/App.tsx` - Re-enable E2EE code

---

## Implementation Order

### Phase A: Foundation (2-3 hours)
1. ✅ Update type definitions (Task 1)
2. ✅ Implement X3DH responder (Task 2)
3. ✅ Add session storage helpers (Task 6 partial)

### Phase B: Core Logic (3-4 hours)
4. Update SessionManager for role detection (Task 3)
5. Add X3DH metadata to first message (Task 4)
6. Fix session initialization flow (Task 5)

### Phase C: Cleanup & Testing (2-3 hours)
7. Remove deterministic keys (Task 7)
8. Re-enable E2EE (Task 8)
9. Clear old session data
10. End-to-end testing

### Phase D: Polish (1-2 hours)
11. Add error handling for missing prekeys
12. Add session refresh logic
13. Add prekey rotation monitoring
14. Update documentation

---

## Testing Strategy

### Unit Tests
- X3DH initiator and responder produce same shared secret
- Ratchet state synchronization across multiple messages
- One-time prekey consumption and cleanup

### Integration Tests
1. **Fresh session establishment**: Alice → Bob (first message)
2. **Session reuse**: Alice → Bob (subsequent messages)
3. **Bidirectional**: Alice ↔ Bob (both directions)
4. **Multiple sessions**: Alice → Bob, Alice → Charlie
5. **Out-of-order messages**: Test skipped message key handling
6. **Session recovery**: Clear one side's data, re-establish

### Manual Testing
1. Open two browser tabs (Alice, Bob)
2. Alice sends message to Bob → Bob sees plaintext
3. Bob replies to Alice → Alice sees plaintext
4. Clear IndexedDB on one side → session re-establishes
5. Check console logs for X3DH flow

---

## Rollback Plan

If implementation fails:
1. Keep E2EE disabled (current state)
2. All messages send as plaintext
3. Server validation still works
4. Can implement E2EE in future without breaking changes

---

## Success Criteria

✅ Both users derive same shared secret
✅ First message decrypts successfully
✅ Subsequent messages use Double Ratchet correctly
✅ No "authentication failed" errors
✅ Messages display as plaintext on both sides
✅ Session persists across page reloads
✅ One-time prekeys are consumed and refreshed

---

## Estimated Time

- **Total**: 8-12 hours
- **Core functionality**: 5-7 hours
- **Testing & debugging**: 2-3 hours
- **Polish & documentation**: 1-2 hours

---

## Dependencies

- No external dependencies required
- All crypto primitives already available (tweetnacl, crypto.subtle)
- IndexedDB already configured
- Server endpoints already support encrypted messages

---

## Risk Mitigation

1. **Backwards compatibility**: New X3DH data is optional field, old messages still work
2. **Graceful degradation**: Falls back to unencrypted if E2EE fails
3. **Clear logging**: Comprehensive logs for debugging
4. **Incremental rollout**: Can enable per-user or feature flag
