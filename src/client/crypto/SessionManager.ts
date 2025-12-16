import { KeyManager } from './KeyManager';
import { performX3DHInitiator } from './X3DH';
import { RemotePrekeyBundle, X3DHResult } from './types';
import { apiFetch } from '../utils/api';
import {
  KeyStorage,
  SessionRecordInput,
  StoredSessionRecord,
} from '../storage/KeyStorage';
import {
  RatchetEngine,
  RatchetState,
  EncryptedMessage,
  SerializedEncryptedMessage,
} from './RatchetEngine';
import { encodeUtf8, decodeUtf8 } from './utils';

export class SessionManager {
  private readonly storage: KeyStorage;
  private readonly ratchetEngine: RatchetEngine;
  private inFlight = new Map<string, Promise<StoredSessionRecord>>();
  private ratchetStates = new Map<string, RatchetState>();

  constructor(private readonly userId: string, private readonly keyManager: KeyManager) {
    this.storage = keyManager.getStorage();
    this.ratchetEngine = new RatchetEngine();
  }

  async listSessions(): Promise<StoredSessionRecord[]> {
    return this.storage.listSessions();
  }

  async ensureSession(peerId: string): Promise<StoredSessionRecord> {
    const existing = await this.storage.loadSession(peerId);
    if (existing && existing.status === 'ready') {
      return existing;
    }

    if (this.inFlight.has(peerId)) {
      return this.inFlight.get(peerId)!;
    }

    const promise = this.establishSession(peerId);
    this.inFlight.set(peerId, promise);
    try {
      const record = await promise;
      return record;
    } finally {
      this.inFlight.delete(peerId);
    }
  }

  private async establishSession(peerId: string): Promise<StoredSessionRecord> {
    const identity = await this.keyManager.getIdentityMaterial();
    const bundle = await this.fetchRemoteBundle(peerId);
    const handshake: X3DHResult = await performX3DHInitiator({
      localIdentitySeed: identity.seed,
      remoteBundle: bundle,
    });

    // Initialize ratchet state from X3DH shared secret
    const ratchetState = await this.ratchetEngine.initializeRatchet(
      handshake.sharedSecret
    );

    const timestamp = Date.now();
    const record: SessionRecordInput = {
      peerId,
      sessionId: `${peerId}:${timestamp}`,
      remoteIdentityKey: handshake.remoteIdentityKey,
      remoteSignedPrekey: handshake.remoteSignedPrekey,
      remoteSignedPrekeyId: handshake.remoteSignedPrekeyId,
      remoteFingerprint: bundle.fingerprint,
      rootKey: handshake.sharedSecret,
      localEphemeralKeyPair: handshake.localEphemeralKeyPair,
      usedOneTimePrekeyId: handshake.usedOneTimePrekeyId,
      status: 'ready',
      createdAt: timestamp,
      updatedAt: timestamp,
      ratchetState: this.ratchetEngine.serializeState(ratchetState),
    };

    await this.storage.saveSession(record);
    const stored = await this.storage.loadSession(peerId);
    if (!stored) {
      throw new Error('Failed to persist session state');
    }
    
    // Cache ratchet state in memory
    this.ratchetStates.set(peerId, ratchetState);
    
    return stored;
  }

  private async fetchRemoteBundle(peerId: string): Promise<RemotePrekeyBundle> {
    const response = await apiFetch(`/api/users/${peerId}/prekeys`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${this.userId}`,
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || 'Failed to fetch recipient prekeys');
    }

    return (await response.json()) as RemotePrekeyBundle;
  }

  /**
   * Encrypt a message for a peer
   */
  async encryptMessage(
    peerId: string,
    plaintext: string
  ): Promise<SerializedEncryptedMessage> {
    // Ensure session exists
    const session = await this.ensureSession(peerId);

    // Load ratchet state
    let ratchetState = this.ratchetStates.get(peerId);
    if (!ratchetState && session.ratchetState) {
      ratchetState = this.ratchetEngine.deserializeState(session.ratchetState);
      this.ratchetStates.set(peerId, ratchetState);
    }

    if (!ratchetState) {
      throw new Error('No ratchet state available for encryption');
    }

    // Encrypt
    const plaintextBytes = encodeUtf8(plaintext);
    const { message, newState } = await this.ratchetEngine.encryptMessage(
      ratchetState,
      plaintextBytes
    );

    // Update and persist ratchet state
    this.ratchetStates.set(peerId, newState);
    await this.storage.updateSessionRatchetState(
      peerId,
      this.ratchetEngine.serializeState(newState)
    );

    // Serialize for transmission
    return this.ratchetEngine.serializeMessage(message);
  }

  /**
   * Decrypt a message from a peer
   */
  async decryptMessage(
    peerId: string,
    serializedMessage: SerializedEncryptedMessage
  ): Promise<string> {
    // Ensure session exists
    const session = await this.ensureSession(peerId);

    // Load ratchet state
    let ratchetState = this.ratchetStates.get(peerId);
    if (!ratchetState && session.ratchetState) {
      ratchetState = this.ratchetEngine.deserializeState(session.ratchetState);
      this.ratchetStates.set(peerId, ratchetState);
    }

    if (!ratchetState) {
      throw new Error('No ratchet state available for decryption');
    }

    // Deserialize message
    const message = this.ratchetEngine.deserializeMessage(serializedMessage);

    // Decrypt
    const { plaintext, newState } = await this.ratchetEngine.decryptMessage(
      ratchetState,
      message
    );

    // Update and persist ratchet state
    this.ratchetStates.set(peerId, newState);
    await this.storage.updateSessionRatchetState(
      peerId,
      this.ratchetEngine.serializeState(newState)
    );

    // Decode to string
    return decodeUtf8(plaintext);
  }
}
