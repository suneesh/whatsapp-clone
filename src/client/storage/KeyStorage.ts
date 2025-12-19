import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { fromBase64, toBase64 } from '../crypto/utils';
import { EncryptedSecret } from '../crypto/types';

interface KeyDBSchema extends DBSchema {
  identity: {
    key: string;
    value: IdentityRecordRow;
  };
  signed_prekeys: {
    key: string;
    value: SignedPrekeyRecordRow;
  };
  one_time_prekeys: {
    key: string;
    value: OneTimePrekeyRecordRow;
  };
  metadata: {
    key: string;
    value: MetadataRecord;
  };
  sessions: {
    key: string;
    value: SessionRecordRow;
  };
}

export interface IdentityRecordRow {
  userId: string;
  fingerprint: string;
  signingPublicKey: string;
  x25519PublicKey: string;
  encryptedSeed: EncryptedSecret;
  createdAt: number;
}

export interface SignedPrekeyRecordRow {
  storageKey: string;
  userId: string;
  keyId: number;
  publicKey: string;
  signature: string;
  encryptedSecretKey: EncryptedSecret;
  createdAt: number;
  uploaded: boolean;
}

export interface OneTimePrekeyRecordRow {
  storageKey: string;
  userId: string;
  keyId: number;
  publicKey: string;
  encryptedSecretKey: EncryptedSecret;
  createdAt: number;
  uploaded: boolean;
  consumed: boolean;
}

export interface MetadataRecord {
  userId: string;
  masterKey: string;
  nextPrekeyId: number;
  lastSignedPrekeyId?: number;
  lastUploadAt?: number;
}

export interface StoredIdentityRecord {
  seed: Uint8Array;
  fingerprint: string;
  signingPublicKey: Uint8Array;
  x25519PublicKey: Uint8Array;
  createdAt: number;
}

export interface StoredSignedPrekeyRecord {
  keyId: number;
  publicKey: Uint8Array;
  secretKey: Uint8Array;
  signature: Uint8Array;
  createdAt: number;
  uploaded: boolean;
}

export interface StoredOneTimePrekeyRecord {
  keyId: number;
  publicKey: Uint8Array;
  secretKey: Uint8Array;
  createdAt: number;
  uploaded: boolean;
  consumed: boolean;
}

export type SessionStorageStatus = 'pending' | 'ready' | 'error';

export interface SessionRecordRow {
  storageKey: string;
  userId: string;
  peerId: string;
  sessionId: string;
  remoteIdentityKey: string;
  remoteSignedPrekey: string;
  remoteSignedPrekeyId: number;
  remoteFingerprint: string;
  rootKey: EncryptedSecret;
  localEphemeralPublicKey: string;
  localEphemeralSecret: EncryptedSecret;
  usedOneTimePrekeyId?: number;
  status: SessionStorageStatus;
  createdAt: number;
  updatedAt: number;
  lastError?: string;
  ratchetState?: string;
  // X3DH initialization data (for first message only)
  x3dhData?: string; // JSON-encoded X3DHInitData
}

export interface StoredSessionRecord {
  peerId: string;
  sessionId: string;
  remoteIdentityKey: Uint8Array;
  remoteSignedPrekey: Uint8Array;
  remoteSignedPrekeyId: number;
  remoteFingerprint: string;
  rootKey: Uint8Array;
  localEphemeralKeyPair: {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
  };
  usedOneTimePrekeyId?: number;
  status: SessionStorageStatus;
  createdAt: number;
  updatedAt: number;
  // X3DH initialization data (for first message only)
  x3dhData?: {
    localIdentityKey: Uint8Array;
    localEphemeralKey: Uint8Array;
    usedSignedPrekeyId: number;
    usedOneTimePrekeyId?: number;
  };
  lastError?: string;
  ratchetState?: string;
}

export interface SessionRecordInput {
  peerId: string;
  sessionId: string;
  remoteIdentityKey: Uint8Array;
  remoteSignedPrekey: Uint8Array;
  remoteSignedPrekeyId: number;
  remoteFingerprint: string;
  rootKey: Uint8Array;
  localEphemeralKeyPair: {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
  };
  usedOneTimePrekeyId?: number;
  status: SessionStorageStatus;
  createdAt: number;
  updatedAt: number;
  lastError?: string;
  ratchetState?: string;
  // X3DH initialization data (for first message only)
  x3dhData?: {
    localIdentityKey: Uint8Array;
    localEphemeralKey: Uint8Array;
    usedSignedPrekeyId: number;
    usedOneTimePrekeyId?: number;
  };
}

export class KeyStorage {
  private static DB_NAME = 'quick-chat-e2ee';

  private static DB_VERSION = 2;

  private dbPromise: Promise<IDBPDatabase<KeyDBSchema>>;

  private masterKeyPromise?: Promise<CryptoKey>;

  private metadataCache?: MetadataRecord;

  constructor(private readonly userId: string) {
    console.log('[KeyStorage] Initializing IndexedDB for user:', userId);
    this.dbPromise = openDB<KeyDBSchema>(KeyStorage.DB_NAME, KeyStorage.DB_VERSION, {
      upgrade(db) {
        console.log('[KeyStorage] Upgrading database schema');
        if (!db.objectStoreNames.contains('identity')) {
          db.createObjectStore('identity');
        }
        if (!db.objectStoreNames.contains('signed_prekeys')) {
          db.createObjectStore('signed_prekeys');
        }
        if (!db.objectStoreNames.contains('one_time_prekeys')) {
          db.createObjectStore('one_time_prekeys');
        }
        if (!db.objectStoreNames.contains('metadata')) {
          db.createObjectStore('metadata');
        }
        if (!db.objectStoreNames.contains('sessions')) {
          db.createObjectStore('sessions');
        }
        console.log('[KeyStorage] Database schema upgraded');
      },
    }).catch((error) => {
      console.error('[KeyStorage] Failed to open IndexedDB:', error);
      throw error;
    });
  }

  async loadIdentity(): Promise<StoredIdentityRecord | null> {
    try {
      console.log('[KeyStorage] Loading identity for user:', this.userId);
      const db = await this.dbPromise;
      const row = await db.get('identity', this.userId);
      if (!row) {
        console.log('[KeyStorage] No identity found for user:', this.userId);
        return null;
      }

      console.log('[KeyStorage] Identity found, decrypting seed');
      const seed = await this.decrypt(row.encryptedSeed);
      console.log('[KeyStorage] Identity decrypted successfully');
      return {
        seed,
        fingerprint: row.fingerprint,
        signingPublicKey: fromBase64(row.signingPublicKey),
        x25519PublicKey: fromBase64(row.x25519PublicKey),
        createdAt: row.createdAt,
      };
    } catch (error) {
      console.error('[KeyStorage] Failed to load identity:', error);
      throw error;
    }
  }

  async saveIdentity(record: {
    seed: Uint8Array;
    fingerprint: string;
    signingPublicKey: Uint8Array;
    x25519PublicKey: Uint8Array;
    createdAt: number;
  }): Promise<void> {
    const db = await this.dbPromise;
    const encryptedSeed = await this.encrypt(record.seed);
    const row: IdentityRecordRow = {
      userId: this.userId,
      fingerprint: record.fingerprint,
      signingPublicKey: toBase64(record.signingPublicKey),
      x25519PublicKey: toBase64(record.x25519PublicKey),
      encryptedSeed,
      createdAt: record.createdAt,
    };
    await db.put('identity', row, this.userId);
  }

  async loadSignedPrekey(): Promise<StoredSignedPrekeyRecord | null> {
    const metadata = await this.getMetadata();
    if (!metadata.lastSignedPrekeyId) {
      return null;
    }
    const storageKey = this.getStorageKey(metadata.lastSignedPrekeyId);
    const db = await this.dbPromise;
    const row = await db.get('signed_prekeys', storageKey);
    if (!row) {
      return null;
    }
    const secretKey = await this.decrypt(row.encryptedSecretKey);
    return {
      keyId: row.keyId,
      publicKey: fromBase64(row.publicKey),
      secretKey,
      signature: fromBase64(row.signature),
      createdAt: row.createdAt,
      uploaded: row.uploaded,
    };
  }

  async saveSignedPrekey(record: {
    keyId: number;
    publicKey: Uint8Array;
    secretKey: Uint8Array;
    signature: Uint8Array;
    createdAt: number;
  }): Promise<void> {
    const db = await this.dbPromise;
    const encryptedSecretKey = await this.encrypt(record.secretKey);
    const storageKey = this.getStorageKey(record.keyId);
    const row: SignedPrekeyRecordRow = {
      storageKey,
      userId: this.userId,
      keyId: record.keyId,
      publicKey: toBase64(record.publicKey),
      signature: toBase64(record.signature),
      encryptedSecretKey,
      createdAt: record.createdAt,
      uploaded: false,
    };
    await db.put('signed_prekeys', row, storageKey);

    await this.updateMetadata({ lastSignedPrekeyId: record.keyId });
  }

  async markSignedPrekeyUploaded(keyId: number): Promise<void> {
    const storageKey = this.getStorageKey(keyId);
    const db = await this.dbPromise;
    const existing = await db.get('signed_prekeys', storageKey);
    if (!existing) {
      return;
    }
    existing.uploaded = true;
    await db.put('signed_prekeys', existing, storageKey);
  }

  async saveOneTimePrekeys(records: Array<{
    keyId: number;
    publicKey: Uint8Array;
    secretKey: Uint8Array;
    createdAt: number;
  }>): Promise<void> {
    if (records.length === 0) {
      return;
    }
    const db = await this.dbPromise;
    for (const record of records) {
      const encryptedSecretKey = await this.encrypt(record.secretKey);
      const storageKey = this.getStorageKey(record.keyId);
      const row: OneTimePrekeyRecordRow = {
        storageKey,
        userId: this.userId,
        keyId: record.keyId,
        publicKey: toBase64(record.publicKey),
        encryptedSecretKey,
        createdAt: record.createdAt,
        uploaded: false,
        consumed: false,
      };
      await db.put('one_time_prekeys', row, storageKey);
    }
  }

  async getPendingOneTimePrekeys(limit: number): Promise<StoredOneTimePrekeyRecord[]> {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('one_time_prekeys');
      const rows: OneTimePrekeyRecordRow[] = [];
      let cursor = await tx.store.openCursor();
      while (cursor && rows.length < limit) {
        const value = cursor.value as OneTimePrekeyRecordRow;
        if (!value.uploaded) {
          rows.push(value);
        }
        cursor = await cursor.continue();
      }
      await tx.done;

      const results = await Promise.allSettled(
        rows.map(async (value) => {
          const secretKey = await this.decrypt(value.encryptedSecretKey);
          return {
            keyId: value.keyId,
            publicKey: fromBase64(value.publicKey),
            secretKey,
            createdAt: value.createdAt,
            uploaded: value.uploaded,
            consumed: value.consumed,
          };
        })
      );

      // Filter out failed decryptions and return only successful ones
      return results
        .filter((result) => result.status === 'fulfilled')
        .map((result) => (result as PromiseFulfilledResult<StoredOneTimePrekeyRecord>).value);
    } catch (error) {
      console.error('[KeyStorage] Failed to get pending one-time prekeys:', error);
      // Return empty array on error instead of failing completely
      return [];
    }
  }

  async markOneTimePrekeysUploaded(keyIds: number[]): Promise<void> {
    if (keyIds.length === 0) {
      return;
    }
    const db = await this.dbPromise;
    const tx = db.transaction('one_time_prekeys', 'readwrite');
    for (const keyId of keyIds) {
      const storageKey = this.getStorageKey(keyId);
      const existing = await tx.store.get(storageKey);
      if (existing) {
        existing.uploaded = true;
        await tx.store.put(existing, storageKey);
      }
    }
    await tx.done;
  }

  async countOneTimePrekeys(): Promise<number> {
    const db = await this.dbPromise;
    let count = 0;
    let cursor = await db.transaction('one_time_prekeys').store.openCursor();
    while (cursor) {
      count += 1;
      cursor = await cursor.continue();
    }
    return count;
  }

  /**
   * Load a specific one-time prekey by ID
   */
  async loadOneTimePrekey(keyId: number): Promise<StoredOneTimePrekeyRecord | undefined> {
    console.log('[KeyStorage] Loading one-time prekey:', keyId);
    try {
      const db = await this.dbPromise;
      const storageKey = this.getStorageKey(keyId);
      const row = await db.get('one_time_prekeys', storageKey);
      
      if (!row) {
        console.log('[KeyStorage] One-time prekey not found:', keyId);
        return undefined;
      }

      const secretKey = await this.decrypt(row.encryptedSecretKey);
      return {
        keyId: row.keyId,
        publicKey: fromBase64(row.publicKey),
        secretKey,
        createdAt: row.createdAt,
        uploaded: row.uploaded,
        consumed: row.consumed,
      };
    } catch (error) {
      console.error('[KeyStorage] Failed to load one-time prekey:', keyId, error);
      return undefined;
    }
  }

  /**
   * Delete a specific one-time prekey by ID (after it has been consumed)
   */
  async deleteOneTimePrekey(keyId: number): Promise<void> {
    console.log('[KeyStorage] Deleting one-time prekey:', keyId);
    try {
      const db = await this.dbPromise;
      const storageKey = this.getStorageKey(keyId);
      await db.delete('one_time_prekeys', storageKey);
      console.log('[KeyStorage] One-time prekey deleted:', keyId);
    } catch (error) {
      console.error('[KeyStorage] Failed to delete one-time prekey:', keyId, error);
    }
  }

  /**
   * Get the secret key for a signed prekey
   */
  async getSignedPrekeySecret(keyId: number): Promise<Uint8Array> {
    console.log('[KeyStorage] Getting signed prekey secret:', keyId);
    const db = await this.dbPromise;
    const storageKey = this.getStorageKey(keyId);
    const row = await db.get('signed_prekeys', storageKey);
    
    if (!row) {
      throw new Error(`Signed prekey ${keyId} not found`);
    }

    return await this.decrypt(row.encryptedSecretKey);
  }

  async saveSession(record: SessionRecordInput): Promise<void> {
    const db = await this.dbPromise;
    const storageKey = this.getSessionStorageKey(record.peerId);
    const row: SessionRecordRow = {
      storageKey,
      userId: this.userId,
      peerId: record.peerId,
      sessionId: record.sessionId,
      remoteIdentityKey: toBase64(record.remoteIdentityKey),
      remoteSignedPrekey: toBase64(record.remoteSignedPrekey),
      remoteSignedPrekeyId: record.remoteSignedPrekeyId,
      remoteFingerprint: record.remoteFingerprint,
      rootKey: await this.encrypt(record.rootKey),
      localEphemeralPublicKey: toBase64(record.localEphemeralKeyPair.publicKey),
      localEphemeralSecret: await this.encrypt(record.localEphemeralKeyPair.secretKey),
      usedOneTimePrekeyId: record.usedOneTimePrekeyId,
      status: record.status,
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
      lastError: record.lastError,
      ratchetState: record.ratchetState,
      x3dhData: record.x3dhData ? JSON.stringify({
        localIdentityKey: toBase64(record.x3dhData.localIdentityKey),
        localEphemeralKey: toBase64(record.x3dhData.localEphemeralKey),
        usedSignedPrekeyId: record.x3dhData.usedSignedPrekeyId,
        usedOneTimePrekeyId: record.x3dhData.usedOneTimePrekeyId,
      }) : undefined,
    };
    await db.put('sessions', row, storageKey);
  }

  async loadSession(peerId: string): Promise<StoredSessionRecord | null> {
    const db = await this.dbPromise;
    const row = await db.get('sessions', this.getSessionStorageKey(peerId));
    if (!row) {
      return null;
    }
    return this.mapSessionRow(row);
  }

  async listSessions(): Promise<StoredSessionRecord[]> {
    const db = await this.dbPromise;
    const tx = db.transaction('sessions');
    const rows: SessionRecordRow[] = [];
    let cursor = await tx.store.openCursor();
    while (cursor) {
      rows.push(cursor.value as SessionRecordRow);
      cursor = await cursor.continue();
    }
    await tx.done;

    return Promise.all(rows.map((row) => this.mapSessionRow(row)));
  }

  async updateSessionRatchetState(peerId: string, ratchetState: string): Promise<void> {
    const db = await this.dbPromise;
    const storageKey = this.getSessionStorageKey(peerId);
    const row = await db.get('sessions', storageKey);
    if (!row) {
      throw new Error(`Session not found for peer: ${peerId}`);
    }
    row.ratchetState = ratchetState;
    row.updatedAt = Date.now();
    await db.put('sessions', row, storageKey);
  }

  /**
   * Clear X3DH initialization data after first message is sent
   */
  async clearSessionX3DHData(peerId: string): Promise<void> {
    console.log('[KeyStorage] Clearing X3DH data for peer:', peerId);
    const db = await this.dbPromise;
    const storageKey = this.getSessionStorageKey(peerId);
    const row = await db.get('sessions', storageKey);
    if (!row) {
      console.warn('[KeyStorage] Session not found when clearing X3DH data:', peerId);
      return;
    }
    row.x3dhData = undefined;
    row.updatedAt = Date.now();
    await db.put('sessions', row, storageKey);
  }

  /**
   * Delete a session (used when refreshing due to key rotation)
   */
  async deleteSession(peerId: string): Promise<void> {
    console.log('[KeyStorage] Deleting session for peer:', peerId);
    const db = await this.dbPromise;
    const storageKey = this.getSessionStorageKey(peerId);
    await db.delete('sessions', storageKey);
  }

  async ensureNextPrekeyIdIncrement(count: number): Promise<number> {
    const metadata = await this.getMetadata();
    const current = metadata.nextPrekeyId || 1;
    metadata.nextPrekeyId = current + count;
    await this.saveMetadata(metadata);
    return current;
  }

  async updateLastUpload(timestamp: number): Promise<void> {
    await this.updateMetadata({ lastUploadAt: timestamp });
  }

  async getMetadata(): Promise<MetadataRecord> {
    if (this.metadataCache) {
      return this.metadataCache;
    }
    const db = await this.dbPromise;
    let metadata = await db.get('metadata', this.userId);
    if (!metadata) {
      const masterKeyBytes = crypto.getRandomValues(new Uint8Array(32));
      metadata = {
        userId: this.userId,
        masterKey: toBase64(masterKeyBytes),
        nextPrekeyId: 1,
      };
      await db.put('metadata', metadata, this.userId);
    }
    this.metadataCache = metadata;
    return metadata;
  }

  private async updateMetadata(patch: Partial<MetadataRecord>): Promise<void> {
    const metadata = await this.getMetadata();
    const updated = { ...metadata, ...patch } as MetadataRecord;
    await this.saveMetadata(updated);
  }

  private async saveMetadata(record: MetadataRecord): Promise<void> {
    const db = await this.dbPromise;
    await db.put('metadata', record, this.userId);
    this.metadataCache = record;
  }

  private getStorageKey(keyId: number): string {
    return `${this.userId}:${keyId}`;
  }

  private getSessionStorageKey(peerId: string): string {
    return `${this.userId}:session:${peerId}`;
  }

  private async mapSessionRow(row: SessionRecordRow): Promise<StoredSessionRecord> {
    return {
      peerId: row.peerId,
      sessionId: row.sessionId,
      remoteIdentityKey: fromBase64(row.remoteIdentityKey),
      remoteSignedPrekey: fromBase64(row.remoteSignedPrekey),
      remoteSignedPrekeyId: row.remoteSignedPrekeyId,
      remoteFingerprint: row.remoteFingerprint,
      rootKey: await this.decrypt(row.rootKey),
      localEphemeralKeyPair: {
        publicKey: fromBase64(row.localEphemeralPublicKey),
        secretKey: await this.decrypt(row.localEphemeralSecret),
      },
      usedOneTimePrekeyId: row.usedOneTimePrekeyId,
      status: row.status,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
      lastError: row.lastError,
      ratchetState: row.ratchetState,
      x3dhData: row.x3dhData ? (() => {
        const parsed = JSON.parse(row.x3dhData);
        return {
          localIdentityKey: fromBase64(parsed.localIdentityKey),
          localEphemeralKey: fromBase64(parsed.localEphemeralKey),
          usedSignedPrekeyId: parsed.usedSignedPrekeyId,
          usedOneTimePrekeyId: parsed.usedOneTimePrekeyId,
        };
      })() : undefined,
    };
  }

  private async encrypt(data: Uint8Array): Promise<EncryptedSecret> {
    try {
      console.log('[KeyStorage] Encrypting data');
      const masterKey = await this.getMasterKey();
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        masterKey,
        data
      );
      console.log('[KeyStorage] Data encrypted successfully');
      return {
        ciphertext: toBase64(new Uint8Array(encrypted)),
        iv: toBase64(iv),
      };
    } catch (error) {
      console.error('[KeyStorage] Encryption failed:', error);
      throw error;
    }
  }

  private async decrypt(secret: EncryptedSecret): Promise<Uint8Array> {
    try {
      console.log('[KeyStorage] Decrypting data');
      const masterKey = await this.getMasterKey();
      const iv = fromBase64(secret.iv);
      const ciphertext = fromBase64(secret.ciphertext);
      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv },
        masterKey,
        ciphertext
      );
      console.log('[KeyStorage] Data decrypted successfully');
      return new Uint8Array(decrypted);
    } catch (error) {
      console.error('[KeyStorage] Decryption failed:', error);
      throw error;
    }
  }

  private async getMasterKey(): Promise<CryptoKey> {
    if (this.masterKeyPromise) {
      return this.masterKeyPromise;
    }
    console.log('[KeyStorage] Loading master key');
    this.masterKeyPromise = this.loadMasterKey();
    return this.masterKeyPromise;
  }

  private async loadMasterKey(): Promise<CryptoKey> {
    try {
      console.log('[KeyStorage] Importing master key from metadata');
      const metadata = await this.getMetadata();
      const keyBytes = fromBase64(metadata.masterKey);
      const masterKey = await crypto.subtle.importKey(
        'raw',
        keyBytes,
        { name: 'AES-GCM' },
        false,
        ['encrypt', 'decrypt']
      );
      console.log('[KeyStorage] Master key imported successfully');
      return masterKey;
    } catch (error) {
      console.error('[KeyStorage] Failed to load master key:', error);
      throw error;
    }
  }

  /**
   * Clear all E2EE data - use with caution!
   * This will delete identity, prekeys, and sessions
   */
  async clearAllE2EEData(): Promise<void> {
    console.log('[KeyStorage] Clearing all E2EE data...');
    const db = await this.dbPromise;
    const tx = db.transaction(
      ['metadata', 'identity', 'signed_prekeys', 'one_time_prekeys', 'sessions'],
      'readwrite'
    );
    
    await Promise.all([
      tx.objectStore('metadata').clear(),
      tx.objectStore('identity').clear(),
      tx.objectStore('signed_prekeys').clear(),
      tx.objectStore('one_time_prekeys').clear(),
      tx.objectStore('sessions').clear(),
    ]);
    
    await tx.done;
    console.log('[KeyStorage] All E2EE data cleared');
  }
}
