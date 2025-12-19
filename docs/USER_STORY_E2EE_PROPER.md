# User Stories: Proper E2EE Signal Protocol Implementation

## Epic: End-to-End Encrypted Messaging with Signal Protocol

**As a** WhatsApp Clone user  
**I want** messages to be end-to-end encrypted using industry-standard Signal protocol  
**So that** my conversations remain private and secure from server operators and third parties

---

## Phase A: Foundation

### US-E2EE-01: X3DH Message Metadata

**Story**  
**As a** sender initiating an encrypted conversation  
**I want** my first message to include X3DH initialization parameters  
**So that** the receiver can derive the same encryption keys without a separate handshake

**Acceptance Criteria**
- [ ] `SerializedEncryptedMessage` interface includes optional `x3dh` field
- [ ] `x3dh` field contains: `senderIdentityKey`, `senderEphemeralKey`, `usedSignedPrekeyId`, `usedOneTimePrekeyId`
- [ ] X3DH metadata is only included on first message to each peer
- [ ] Subsequent messages do not include X3DH metadata (to save bandwidth)
- [ ] Message serialization/deserialization handles optional X3DH field

**Technical Details**
- Files: `src/client/crypto/RatchetEngine.ts`, `src/client/crypto/types.ts`
- Estimated: 1 hour

**Testing**
```typescript
// First message should have x3dh
const firstMsg = await sessionManager.encryptMessage('peer1', 'Hello');
expect(firstMsg.x3dh).toBeDefined();
expect(firstMsg.x3dh.senderEphemeralKey).toBeTruthy();

// Second message should NOT have x3dh
const secondMsg = await sessionManager.encryptMessage('peer1', 'World');
expect(secondMsg.x3dh).toBeUndefined();
```

**Points**: 3

---

### US-E2EE-02: X3DH Responder Function

**Story**  
**As a** receiver of an encrypted message  
**I want** to perform X3DH as a responder using the sender's ephemeral key  
**So that** I derive the same shared secret as the sender

**Acceptance Criteria**
- [ ] `performX3DHResponder()` function accepts sender's ephemeral public key
- [ ] Function computes DH1, DH2, DH3 using sender's ephemeral key
- [ ] Function computes DH4 if one-time prekey was used
- [ ] Derived shared secret matches initiator's shared secret (unit test)
- [ ] Function uses receiver's private keys (identity, signed prekey, one-time prekey)

**Technical Details**
- Files: `src/client/crypto/X3DH.ts`
- Estimated: 1.5 hours

**Testing**
```typescript
// Alice performs X3DH as initiator
const aliceResult = await performX3DHInitiator({
  localIdentitySeed: aliceSeed,
  remoteBundle: bobBundle,
});

// Bob performs X3DH as responder using Alice's ephemeral key
const bobSharedSecret = await performX3DHResponder({
  localIdentitySeed: bobSeed,
  localSignedPrekeyPair: bobSignedPrekey,
  remoteIdentityKey: aliceIdentityKey,
  remoteEphemeralKey: aliceResult.localEphemeralKeyPair.publicKey,
});

// Shared secrets should match
expect(toBase64(aliceResult.sharedSecret)).toBe(toBase64(bobSharedSecret));
```

**Points**: 5

---

### US-E2EE-03: KeyStorage Helper Methods

**Story**  
**As a** session manager  
**I want** to load and delete one-time prekeys by ID  
**So that** I can use consumed prekeys and clean them up after use

**Acceptance Criteria**
- [ ] `loadOneTimePrekey(keyId)` returns specific one-time prekey pair
- [ ] `deleteOneTimePrekey(keyId)` removes consumed key from storage
- [ ] `countOneTimePrekeys()` returns current count of available keys
- [ ] `getSignedPrekeySecret(keyId)` returns private key for signed prekey
- [ ] Methods handle IndexedDB errors gracefully

**Technical Details**
- Files: `src/client/storage/KeyStorage.ts`
- Estimated: 1 hour

**Testing**
```typescript
// Store one-time prekey
await storage.saveOneTimePrekey({ keyId: 123, publicKey: '...', secretKey: '...' });

// Load by ID
const prekey = await storage.loadOneTimePrekey(123);
expect(prekey.keyId).toBe(123);

// Delete
await storage.deleteOneTimePrekey(123);

// Should be gone
const deleted = await storage.loadOneTimePrekey(123);
expect(deleted).toBeUndefined();
```

**Points**: 3

---

## Phase B: Core Logic

### US-E2EE-04: Detect First Message in Decryption

**Story**  
**As a** receiver  
**I want** the system to detect when I'm receiving the first message from a sender  
**So that** it can initialize the session using X3DH responder logic

**Acceptance Criteria**
- [ ] `decryptMessage()` checks if message contains `x3dh` field
- [ ] If `x3dh` present, performs X3DH as responder
- [ ] Extracts sender's identity key and ephemeral key from `x3dh`
- [ ] Loads correct signed prekey and one-time prekey (if used)
- [ ] Derives shared secret using responder logic
- [ ] Initializes ratchet state with sender's first ratchet key
- [ ] Logs "First message from {peer} - establishing session as responder"

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`
- Estimated: 2 hours

**Testing**
```typescript
// Alice sends first message to Bob
const encrypted = await alice.encryptMessage('bob', 'Hello');

// Bob has no session with Alice yet
expect(await bob.storage.loadSession('alice')).toBeUndefined();

// Bob receives and decrypts first message
const plaintext = await bob.decryptMessage('alice', encrypted);

// Session should now exist
expect(await bob.storage.loadSession('alice')).toBeDefined();
expect(plaintext).toBe('Hello');
```

**Points**: 8

---

### US-E2EE-05: Store X3DH Metadata in Session

**Story**  
**As a** sender initiating a session  
**I want** X3DH parameters to be stored in the session record  
**So that** they can be included in the first message

**Acceptance Criteria**
- [ ] Session record includes `x3dhData` field
- [ ] `x3dhData` contains: `localIdentityKey`, `localEphemeralKey`, `usedSignedPrekeyId`, `usedOneTimePrekeyId`
- [ ] Data is stored when session is first established
- [ ] Data persists across page reloads
- [ ] Data is cleared after first message is sent

**Technical Details**
- Files: `src/client/storage/KeyStorage.ts`, `src/client/crypto/SessionManager.ts`
- Estimated: 1.5 hours

**Testing**
```typescript
// Create session
await sessionManager.ensureSession('peer1');

// Session should have X3DH data
const session = await storage.loadSession('peer1');
expect(session.x3dhData).toBeDefined();
expect(session.x3dhData.localEphemeralKey).toBeTruthy();

// After first message, X3DH data should be cleared
await sessionManager.encryptMessage('peer1', 'Hello');
const updated = await storage.loadSession('peer1');
expect(updated.x3dhData).toBeUndefined();
```

**Points**: 5

---

### US-E2EE-06: Include X3DH in First Message

**Story**  
**As a** sender  
**I want** my first message to automatically include X3DH parameters  
**So that** the receiver can establish the session

**Acceptance Criteria**
- [ ] `encryptMessage()` checks if session already exists
- [ ] If new session, includes `x3dh` field in encrypted message
- [ ] X3DH field contains sender's identity key (base64)
- [ ] X3DH field contains sender's ephemeral key (base64)
- [ ] X3DH field contains which prekeys were used
- [ ] Subsequent messages to same peer do NOT include X3DH
- [ ] X3DH data is removed from session after first message

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`
- Estimated: 2 hours

**Testing**
```typescript
// No existing session
expect(await storage.loadSession('bob')).toBeUndefined();

// First message includes X3DH
const msg1 = await alice.encryptMessage('bob', 'First');
expect(msg1.x3dh).toBeDefined();
expect(msg1.x3dh.senderIdentityKey).toBeTruthy();

// Second message does not include X3DH
const msg2 = await alice.encryptMessage('bob', 'Second');
expect(msg2.x3dh).toBeUndefined();
```

**Points**: 8

---

### US-E2EE-07: Initialize Receiver Ratchet State

**Story**  
**As a** receiver of the first message  
**I want** my ratchet state to be initialized with the sender's ratchet key  
**So that** I can properly decrypt messages and maintain synchronized state

**Acceptance Criteria**
- [ ] Receiver calls `initializeRatchet()` with sender's ratchet key
- [ ] Receiver's initial state has `receivingChainKey` set
- [ ] Receiver's initial state has `sendingChainKey` as null
- [ ] Receiver's `dhRatchetRemoteKey` is sender's ratchet key
- [ ] Receiver does NOT generate their own ratchet key initially
- [ ] First message decrypts successfully without "authentication failed"

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`, `src/client/crypto/RatchetEngine.ts`
- Estimated: 1.5 hours

**Testing**
```typescript
// Alice sends first message
const encrypted = await alice.encryptMessage('bob', 'Test');

// Bob decrypts as responder
await bob.decryptMessage('alice', encrypted);

// Bob's ratchet state should have receiving chain
const bobSession = await bob.storage.loadSession('alice');
const bobState = ratchetEngine.deserializeState(bobSession.ratchetState);

expect(bobState.receivingChainKey).toBeTruthy();
expect(bobState.sendingChainKey).toBeNull();
expect(bobState.dhRatchetRemoteKey).toEqual(aliceRatchetKey);
```

**Points**: 5

---

## Phase C: Cleanup & Testing

### US-E2EE-08: Delete Consumed One-Time Prekeys

**Story**  
**As a** receiver who used a one-time prekey  
**I want** that prekey to be deleted after use  
**So that** it cannot be reused (which would break forward secrecy)

**Acceptance Criteria**
- [ ] After decrypting first message, check if one-time prekey was used
- [ ] Delete the specific one-time prekey from storage
- [ ] Log which prekey was consumed
- [ ] Do not delete if no one-time prekey was used
- [ ] Handle case where prekey already deleted

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`
- Estimated: 0.5 hours

**Testing**
```typescript
// Bob has one-time prekeys
const prekeysBefore = await bob.storage.listOneTimePrekeys();
expect(prekeysBefore.length).toBeGreaterThan(0);

// Alice uses Bob's one-time prekey
const encrypted = await alice.encryptMessage('bob', 'Test');
expect(encrypted.x3dh.usedOneTimePrekeyId).toBeDefined();

// Bob decrypts
await bob.decryptMessage('alice', encrypted);

// One-time prekey should be deleted
const prekey = await bob.storage.loadOneTimePrekey(encrypted.x3dh.usedOneTimePrekeyId);
expect(prekey).toBeUndefined();
```

**Points**: 2

---

### US-E2EE-09: Refresh One-Time Prekey Pool

**Story**  
**As a** user whose one-time prekeys are being consumed  
**I want** new prekeys to be automatically generated and uploaded  
**So that** I always have prekeys available for new sessions

**Acceptance Criteria**
- [ ] After consuming prekey, count remaining prekeys
- [ ] If count < 20, generate new batch of prekeys
- [ ] Upload new prekeys to server
- [ ] Log prekey refresh activity
- [ ] Don't upload if already above threshold

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`, `src/client/crypto/KeyManager.ts`
- Estimated: 1 hour

**Testing**
```typescript
// Bob starts with 5 one-time prekeys (below threshold)
await bob.storage.setOneTimePrekeyCount(5);

// Alice uses one of Bob's prekeys
await alice.encryptMessage('bob', 'Test');
await bob.decryptMessage('alice', encrypted);

// Bob should have generated and uploaded more
const count = await bob.storage.countOneTimePrekeys();
expect(count).toBeGreaterThan(20);
```

**Points**: 3

---

### US-E2EE-10: Remove Deterministic Ephemeral Keys

**Story**  
**As a** developer  
**I want** to remove the temporary deterministic ephemeral key workaround  
**So that** the system uses proper random ephemeral keys as per Signal protocol

**Acceptance Criteria**
- [ ] Remove `deriveDeterministicEphemeralKeyPair()` function
- [ ] Revert X3DH initiator to use `nacl.box.keyPair()`
- [ ] Remove identity key sorting logic
- [ ] Update logs to remove deterministic references
- [ ] Verify random ephemeral keys work with X3DH responder

**Technical Details**
- Files: `src/client/crypto/X3DH.ts`
- Estimated: 0.5 hours

**Testing**
```typescript
// Generate two ephemeral keys
const ek1 = await performX3DHInitiator({ ... });
const ek2 = await performX3DHInitiator({ ... });

// Should be different (random)
expect(ek1.localEphemeralKeyPair.publicKey).not.toEqual(
  ek2.localEphemeralKeyPair.publicKey
);
```

**Points**: 2

---

### US-E2EE-11: Re-enable E2EE in Application

**Story**  
**As a** user  
**I want** encrypted messaging to be enabled by default  
**So that** my messages are automatically protected

**Acceptance Criteria**
- [ ] Remove temporary E2EE disable code from `App.tsx`
- [ ] `handleSendMessage` uses E2EE when ready
- [ ] Falls back to unencrypted if E2EE not initialized
- [ ] Sender sees plaintext in UI
- [ ] Receiver sees plaintext after decryption
- [ ] No "🔒 [Decryption failed]" messages
- [ ] Console logs show successful encryption/decryption

**Technical Details**
- Files: `src/client/App.tsx`
- Estimated: 0.5 hours

**Testing**
```typescript
// Manual test:
// 1. Open two browser tabs
// 2. Login as different users
// 3. Send message from A to B
// 4. B should see plaintext
// 5. Reply from B to A
// 6. A should see plaintext
// 7. Check console for "Decryption successful"
```

**Points**: 2

---

### US-E2EE-12: End-to-End Integration Test

**Story**  
**As a** QA tester  
**I want** comprehensive integration tests for the full E2EE flow  
**So that** I can verify messages encrypt and decrypt correctly

**Acceptance Criteria**
- [ ] Test: Alice sends first message to Bob → Bob decrypts
- [ ] Test: Bob replies to Alice → Alice decrypts
- [ ] Test: Multiple messages in conversation maintain sync
- [ ] Test: Alice sends to Bob and Charlie (multiple sessions)
- [ ] Test: Session persists across page reload
- [ ] Test: Out-of-order message handling
- [ ] All tests pass with no authentication errors

**Technical Details**
- Files: `src/client/__tests__/e2ee-integration.test.ts` (new)
- Estimated: 2 hours

**Testing**
```typescript
describe('E2EE Integration', () => {
  it('should establish session and exchange messages', async () => {
    // Alice sends first message
    const msg1 = await alice.encryptMessage('bob', 'Hello Bob');
    const plaintext1 = await bob.decryptMessage('alice', msg1);
    expect(plaintext1).toBe('Hello Bob');

    // Bob replies
    const msg2 = await bob.encryptMessage('alice', 'Hi Alice');
    const plaintext2 = await alice.decryptMessage('bob', msg2);
    expect(plaintext2).toBe('Hi Alice');

    // Continue conversation
    const msg3 = await alice.encryptMessage('bob', 'How are you?');
    const plaintext3 = await bob.decryptMessage('alice', msg3);
    expect(plaintext3).toBe('How are you?');
  });
});
```

**Points**: 8

---

## Phase D: Polish

### US-E2EE-13: Handle Missing Prekey Errors

**Story**  
**As a** sender  
**I want** clear error messages when recipient's prekeys are unavailable  
**So that** I understand why encryption failed

**Acceptance Criteria**
- [ ] Detect when prekey bundle fetch returns 404
- [ ] Show user-friendly error: "Recipient hasn't set up encryption yet"
- [ ] Log technical details to console
- [ ] Offer option to send unencrypted
- [ ] Retry prekey fetch after delay

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`, `src/client/App.tsx`
- Estimated: 1 hour

**Testing**
```typescript
// Mock server returns 404 for prekey bundle
mockServer.get('/api/users/bob/prekeys').reply(404);

// Alice tries to send encrypted message
await expect(
  alice.encryptMessage('bob', 'Test')
).rejects.toThrow('Recipient prekeys not available');
```

**Points**: 3

---

### US-E2EE-14: Session Refresh on Key Rotation

**Story**  
**As a** user who rotates their signed prekey  
**I want** existing sessions to be refreshed  
**So that** forward secrecy is maintained

**Acceptance Criteria**
- [ ] Detect when signed prekey has been rotated
- [ ] Mark old sessions as "stale"
- [ ] Re-establish session on next message
- [ ] Log session refresh activity
- [ ] Don't break ongoing conversations

**Technical Details**
- Files: `src/client/crypto/SessionManager.ts`, `src/client/hooks/useE2EE.ts`
- Estimated: 2 hours

**Testing**
```typescript
// Alice and Bob have active session
await alice.encryptMessage('bob', 'Test 1');

// Bob rotates signed prekey
await bob.keyManager.rotateSignedPrekey();

// Next message should trigger session refresh
const msg = await alice.encryptMessage('bob', 'Test 2');
expect(msg.x3dh).toBeDefined(); // Should include X3DH again
```

**Points**: 5

---

### US-E2EE-15: Prekey Health Monitoring

**Story**  
**As a** user  
**I want** the system to monitor my prekey health  
**So that** I'm always ready to receive encrypted messages

**Acceptance Criteria**
- [ ] Periodically check one-time prekey count (every 5 minutes)
- [ ] If count < 20, auto-generate and upload batch
- [ ] Check signed prekey age (should be < 7 days)
- [ ] If signed prekey too old, generate and upload new one
- [ ] Log prekey health status
- [ ] Display warning in UI if prekeys critically low

**Technical Details**
- Files: `src/client/hooks/useE2EE.ts`
- Estimated: 1.5 hours

**Testing**
```typescript
// Mock timer
jest.useFakeTimers();

// Start monitoring
const { monitorPrekeyHealth } = useE2EE(userId);

// Advance 5 minutes
jest.advanceTimersByTime(5 * 60 * 1000);

// Should have checked and refreshed if needed
expect(mockKeyManager.checkPrekeyHealth).toHaveBeenCalled();
```

**Points**: 5

---

### US-E2EE-16: Clear Session Data Utility

**Story**  
**As a** user experiencing E2EE issues  
**I want** a way to clear my encryption data and start fresh  
**So that** I can recover from corrupted state

**Acceptance Criteria**
- [ ] Add "Clear Encryption Data" button in settings
- [ ] Button deletes all IndexedDB E2EE data
- [ ] Button re-initializes KeyManager
- [ ] Button regenerates identity, signed prekey, one-time prekeys
- [ ] Button uploads fresh prekey bundle
- [ ] Shows confirmation dialog before clearing
- [ ] Works without logging out

**Technical Details**
- Files: `src/client/App.tsx`, `src/client/hooks/useE2EE.ts`
- Estimated: 1 hour

**Testing**
```typescript
// User has sessions and keys
expect(await storage.listSessions()).toHaveLength(3);
expect(await storage.loadIdentity()).toBeDefined();

// Clear E2EE data
await clearE2EEData();

// Everything should be fresh
expect(await storage.listSessions()).toHaveLength(0);
const newIdentity = await storage.loadIdentity();
expect(newIdentity).toBeDefined();
expect(newIdentity.publicKey).not.toBe(oldIdentity.publicKey);
```

**Points**: 3

---

### US-E2EE-17: Documentation Update

**Story**  
**As a** developer  
**I want** updated documentation explaining the E2EE implementation  
**So that** I can understand and maintain the system

**Acceptance Criteria**
- [ ] Update README with E2EE section
- [ ] Document X3DH flow with diagram
- [ ] Document Double Ratchet message flow
- [ ] Explain session establishment
- [ ] List security properties (forward secrecy, etc.)
- [ ] Include troubleshooting guide
- [ ] Add API documentation for crypto functions

**Technical Details**
- Files: `README.md`, `docs/E2EE_ARCHITECTURE.md` (new)
- Estimated: 2 hours

**Testing**
- Documentation reviewed by team
- No broken links
- Code examples compile and run

**Points**: 3

---

## Summary

### Total Story Points by Phase

- **Phase A (Foundation)**: 11 points (~3.5 hours)
- **Phase B (Core Logic)**: 26 points (~7 hours)
- **Phase C (Cleanup & Testing)**: 17 points (~4.5 hours)
- **Phase D (Polish)**: 19 points (~7.5 hours)

**Grand Total**: 73 points (~22.5 hours)

### Priority Order

**Must Have (P0)**:
- US-E2EE-01, 02, 03, 04, 05, 06, 07, 11, 12 (Core functionality)

**Should Have (P1)**:
- US-E2EE-08, 09, 10, 13 (Cleanup and error handling)

**Nice to Have (P2)**:
- US-E2EE-14, 15, 16, 17 (Polish and maintenance)

### Dependencies

```
US-E2EE-01 ─┬─> US-E2EE-06 ──> US-E2EE-11 ──> US-E2EE-12
            │
US-E2EE-02 ─┴─> US-E2EE-04 ──> US-E2EE-08 ──> US-E2EE-09
            │
US-E2EE-03 ─┘
            │
US-E2EE-05 ─┴─> US-E2EE-07

US-E2EE-10 (Independent, can be done anytime)
US-E2EE-13, 14, 15, 16, 17 (Post-core implementation)
```

### Velocity Planning

Assuming **8 story points per day** (1 point ≈ 45 minutes):

- **Sprint 1 (Phase A + B)**: 37 points = ~5 days
- **Sprint 2 (Phase C)**: 17 points = ~2 days  
- **Sprint 3 (Phase D)**: 19 points = ~3 days

**Total**: ~10 working days (2 weeks)
