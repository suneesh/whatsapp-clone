import { KeyManager } from './KeyManager';
import { performX3DHInitiator, performX3DHResponder } from './X3DH';
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
import { encodeUtf8, decodeUtf8, toBase64, fromBase64 } from './utils';

export class SessionManager {
  private readonly storage: KeyStorage;
  private readonly ratchetEngine: RatchetEngine;
  private inFlight = new Map<string, Promise<StoredSessionRecord>>();
  private ratchetStates = new Map<string, RatchetState>();

  constructor(
    private readonly userId: string,
    private readonly keyManager: KeyManager,
    private readonly token: string
  ) {
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

    const promise = this.establishSession(peerId).catch(err => {
      // Add more context to errors
      if (err instanceof Error) {
        if (err.message === 'PREKEYS_NOT_AVAILABLE') {
          console.warn(`[SessionManager] ${peerId} hasn't set up encryption yet`);
          err.message = `Recipient hasn't set up encryption yet. They need to log in to enable encrypted messaging.`;
        } else if (err.message === 'NETWORK_ERROR') {
          err.message = 'Network error while establishing encrypted session. Please check your connection and try again.';
        }
      }
      throw err;
    });
    
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
      // Store X3DH data for first message
      x3dhData: {
        localIdentityKey: identity.x25519PublicKey,
        localEphemeralKey: handshake.localEphemeralKeyPair.publicKey,
        usedSignedPrekeyId: handshake.remoteSignedPrekeyId,
        usedOneTimePrekeyId: handshake.usedOneTimePrekeyId,
      },
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
    try {
      const response = await apiFetch(`/api/users/${peerId}/prekeys`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${this.token}`,
        },
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        
        // Handle specific error cases
        if (response.status === 404) {
          console.error('[SessionManager] Recipient prekeys not found:', peerId);
          throw new Error('PREKEYS_NOT_AVAILABLE');
        }
        
        console.error('[SessionManager] Failed to fetch prekeys:', response.status, payload);
        throw new Error(payload.error || 'Failed to fetch recipient prekeys');
      }

      const bundle = (await response.json()) as RemotePrekeyBundle;
      console.log('[SessionManager] Fetched prekey bundle for', peerId, {
        hasSignedPrekey: !!bundle.signedPrekey,
        hasOneTimePrekey: !!bundle.oneTimePrekey,
      });
      
      return bundle;
    } catch (err) {
      // Re-throw our custom errors
      if (err instanceof Error && err.message === 'PREKEYS_NOT_AVAILABLE') {
        throw err;
      }
      
      console.error('[SessionManager] Network error fetching prekeys:', err);
      throw new Error('NETWORK_ERROR');
    }
  }

  /**
   * Encrypt a message for a peer
   */
  async encryptMessage(
    peerId: string,
    plaintext: string
  ): Promise<SerializedEncryptedMessage> {
    // Ensure session exists
    let session = await this.ensureSession(peerId);
    
    // Check if we need to refresh the session (e.g., peer rotated their signed prekey)
    const needsRefresh = await this.checkSessionNeedsRefresh(session, peerId);
    if (needsRefresh) {
      console.log('[SessionManager] Session stale (key rotation detected), refreshing...');
      // Delete old session and ratchet state
      await this.storage.deleteSession(peerId);
      this.ratchetStates.delete(peerId);
      // Re-establish
      session = await this.ensureSession(peerId);
    }

    // Check if this is the first message (session has X3DH data)
    const isFirstMessage = !!session.x3dhData;

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
    const serialized = this.ratchetEngine.serializeMessage(message);

    // Add X3DH data if this is the first message
    if (isFirstMessage && session.x3dhData) {
      console.log('[SessionManager] Adding X3DH data to first message for', peerId);
      serialized.x3dh = {
        senderIdentityKey: toBase64(session.x3dhData.localIdentityKey),
        senderEphemeralKey: toBase64(session.x3dhData.localEphemeralKey),
        usedSignedPrekeyId: session.x3dhData.usedSignedPrekeyId,
        usedOneTimePrekeyId: session.x3dhData.usedOneTimePrekeyId,
      };

      // Clear X3DH data after including it in first message
      await this.storage.clearSessionX3DHData(peerId);
    }

    return serialized;
  }

  /**
   * Decrypt a message from a peer
   */
  async decryptMessage(
    peerId: string,
    serializedMessage: SerializedEncryptedMessage
  ): Promise<string> {
    console.log('[SessionManager] Decrypting message from', peerId);
    
    // Check if this is a first message (contains X3DH data)
    const isFirstMessage = !!serializedMessage.x3dh;
    console.log('[SessionManager] Is first message:', isFirstMessage);
    
    if (isFirstMessage && serializedMessage.x3dh) {
      // This is the first message from sender - perform X3DH as responder
      console.log('[SessionManager] Processing first message with X3DH data');
      
      const identity = await this.keyManager.getIdentityMaterial();
      
      // Get the signed prekey that was used
      const signedPrekeySecret = await this.storage.getSignedPrekeySecret(
        serializedMessage.x3dh.usedSignedPrekeyId
      );
      
      // Load current signed prekey for public key
      const signedPrekey = await this.storage.loadSignedPrekey();
      if (!signedPrekey) {
        throw new Error('No signed prekey available');
      }
      
      // Optionally load one-time prekey if it was used
      let oneTimePrekeyPair: { publicKey: Uint8Array; secretKey: Uint8Array } | undefined;
      if (serializedMessage.x3dh.usedOneTimePrekeyId !== undefined) {
        const otpk = await this.storage.loadOneTimePrekey(
          serializedMessage.x3dh.usedOneTimePrekeyId
        );
        if (otpk) {
          oneTimePrekeyPair = {
            publicKey: otpk.publicKey,
            secretKey: otpk.secretKey,
          };
        }
      }
      
      // Perform X3DH as responder using sender's ephemeral key
      const sharedSecret = await performX3DHResponder({
        localIdentitySeed: identity.seed,
        localSignedPrekeyPair: {
          publicKey: signedPrekey.publicKey,
          secretKey: signedPrekeySecret,
        },
        localOneTimePrekeyPair: oneTimePrekeyPair,
        remoteIdentityKey: fromBase64(serializedMessage.x3dh.senderIdentityKey),
        remoteEphemeralKey: fromBase64(serializedMessage.x3dh.senderEphemeralKey),
      });
      
      console.log('[SessionManager] X3DH responder shared secret derived');
      
      // Initialize ratchet with the sender's ratchet key (from message header)
      const remoteRatchetKey = fromBase64(serializedMessage.header.ratchetKey);
      const ratchetState = await this.ratchetEngine.initializeRatchet(
        sharedSecret,
        remoteRatchetKey
      );
      
      console.log('[SessionManager] Receiver ratchet state initialized with sender\'s ratchet key');
      
      // Store ratchet state
      this.ratchetStates.set(peerId, ratchetState);
      
      // Create/update session record
      const timestamp = Date.now();
      const sessionRecord: SessionRecordInput = {
        peerId,
        sessionId: `session-${timestamp}`,
        remoteIdentityKey: fromBase64(serializedMessage.x3dh.senderIdentityKey),
        remoteSignedPrekey: remoteRatchetKey,
        remoteSignedPrekeyId: serializedMessage.x3dh.usedSignedPrekeyId,
        remoteFingerprint: '', // Will be computed by storage layer
        rootKey: sharedSecret,
        localEphemeralKeyPair: {
          publicKey: signedPrekey.publicKey,
          secretKey: signedPrekeySecret,
        },
        usedOneTimePrekeyId: serializedMessage.x3dh.usedOneTimePrekeyId,
        status: 'ready',
        createdAt: timestamp,
        updatedAt: timestamp,
        ratchetState: this.ratchetEngine.serializeState(ratchetState),
        // No x3dhData for receiver - only sender needs this
      };
      
      await this.storage.saveSession(sessionRecord);
      console.log('[SessionManager] Session saved for receiver');
      
      // Delete consumed one-time prekey if used
      if (serializedMessage.x3dh.usedOneTimePrekeyId !== undefined) {
        await this.storage.deleteOneTimePrekey(
          serializedMessage.x3dh.usedOneTimePrekeyId
        );
        console.log('[SessionManager] Deleted consumed one-time prekey:', 
          serializedMessage.x3dh.usedOneTimePrekeyId);
        
        // Check if we need to generate more prekeys
        await this.checkPrekeyPool();
      }
      
      // Continue to decryption below with the newly initialized ratchet state
    } else {
      // Not first message - load existing session
      console.log('[SessionManager] Ensuring session with', peerId);
      const session = await this.ensureSession(peerId);
      console.log('[SessionManager] Session established, status:', session.status);

      // Load ratchet state
      let ratchetState = this.ratchetStates.get(peerId);
      if (!ratchetState && session.ratchetState) {
        console.log('[SessionManager] Deserializing ratchet state from storage');
        ratchetState = this.ratchetEngine.deserializeState(session.ratchetState);
        this.ratchetStates.set(peerId, ratchetState);
      }

      if (!ratchetState) {
        throw new Error('No ratchet state available for decryption');
      }
    }

    // Get ratchet state (either newly created or loaded)
    const ratchetState = this.ratchetStates.get(peerId);
    if (!ratchetState) {
      throw new Error('No ratchet state available for decryption');
    }

    // Deserialize message
    console.log('[SessionManager] Deserializing message');
    const message = this.ratchetEngine.deserializeMessage(serializedMessage);
    console.log('[SessionManager] Message header:', {
      ratchetKey: serializedMessage.header.ratchetKey?.substring(0, 20),
      messageNumber: serializedMessage.header.messageNumber,
      previousChainLength: serializedMessage.header.previousChainLength,
    });

    // Decrypt
    console.log('[SessionManager] Decrypting with ratchet engine');
    const { plaintext, newState } = await this.ratchetEngine.decryptMessage(
      ratchetState,
      message
    );
    console.log('[SessionManager] Decryption successful');

    // Update and persist ratchet state
    this.ratchetStates.set(peerId, newState);
    await this.storage.updateSessionRatchetState(
      peerId,
      this.ratchetEngine.serializeState(newState)
    );

    // Decode to string
    return decodeUtf8(plaintext);
  }

  /**
   * Check and refresh one-time prekey pool after consumption
   */
  private async checkPrekeyPool(): Promise<void> {
    try {
      const count = await this.storage.countOneTimePrekeys();
      const MINIMUM_THRESHOLD = 20;
      
      if (count < MINIMUM_THRESHOLD) {
        console.log(`[SessionManager] Low prekey count (${count}), generating more...`);
        const deficit = 100 - count; // ONE_TIME_PREKEY_TARGET
        const batchSize = Math.min(deficit, 50); // MAX_UPLOAD_PREKEYS
        
        await this.keyManager.queueOneTimePrekeys(batchSize);
        console.log(`[SessionManager] Queued ${batchSize} new one-time prekeys`);
      }
    } catch (err) {
      console.warn('[SessionManager] Failed to check/refresh prekey pool:', err);
    }
  }

  /**
   * Check if session needs refresh due to peer's key rotation
   */
  private async checkSessionNeedsRefresh(
    session: StoredSessionRecord,
    peerId: string
  ): Promise<boolean> {
    try {
      // Fetch current prekey bundle to see if signed prekey changed
      const bundle = await this.fetchRemoteBundle(peerId);
      
      if (!bundle.signedPrekey) {
        return false;
      }
      
      // If signed prekey ID changed, session is stale
      if (bundle.signedPrekey.keyId !== session.remoteSignedPrekeyId) {
        console.log('[SessionManager] Detected signed prekey rotation:', {
          old: session.remoteSignedPrekeyId,
          new: bundle.signedPrekey.keyId,
        });
        return true;
      }
      
      return false;
    } catch (err) {
      // If we can't fetch bundle, don't refresh (might be network issue)
      console.warn('[SessionManager] Could not check for key rotation:', err);
      return false;
    }
  }
}
