import { KeyManager } from './KeyManager';
import { performX3DHInitiator } from './X3DH';
import { RemotePrekeyBundle, X3DHResult } from './types';
import { apiFetch } from '../utils/api';
import {
  KeyStorage,
  SessionRecordInput,
  StoredSessionRecord,
} from '../storage/KeyStorage';

export class SessionManager {
  private readonly storage: KeyStorage;
  private inFlight = new Map<string, Promise<StoredSessionRecord>>();

  constructor(private readonly userId: string, private readonly keyManager: KeyManager) {
    this.storage = keyManager.getStorage();
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
    };

    await this.storage.saveSession(record);
    const stored = await this.storage.loadSession(peerId);
    if (!stored) {
      throw new Error('Failed to persist session state');
    }
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
}
