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
  lastError?: string;
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
}

export class KeyStorage {
  private static DB_NAME = 'quick-chat-e2ee';

  private static DB_VERSION = 2;

  private dbPromise: Promise<IDBPDatabase<KeyDBSchema>>;

  private masterKeyPromise?: Promise<CryptoKey>;

  private metadataCache?: MetadataRecord;

  constructor(private readonly userId: string) {
    this.dbPromise = openDB<KeyDBSchema>(KeyStorage.DB_NAME, KeyStorage.DB_VERSION, {
      upgrade(db) {
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
      },
    });
  }

  async loadIdentity(): Promise<StoredIdentityRecord | null> {
    const db = await this.dbPromise;
    const row = await db.get('identity', this.userId);
    if (!row) {
      return null;
    }

    const seed = await this.decrypt(row.encryptedSeed);
    return {
      seed,
      fingerprint: row.fingerprint,
      signingPublicKey: fromBase64(row.signingPublicKey),
      x25519PublicKey: fromBase64(row.x25519PublicKey),
      createdAt: row.createdAt,
    };
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

    return Promise.all(
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
    };
  }

  private async encrypt(data: Uint8Array): Promise<EncryptedSecret> {
    const masterKey = await this.getMasterKey();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      masterKey,
      data
    );
    return {
      ciphertext: toBase64(new Uint8Array(encrypted)),
      iv: toBase64(iv),
    };
  }

  private async decrypt(secret: EncryptedSecret): Promise<Uint8Array> {
    const masterKey = await this.getMasterKey();
    const iv = fromBase64(secret.iv);
    const ciphertext = fromBase64(secret.ciphertext);
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      masterKey,
      ciphertext
    );
    return new Uint8Array(decrypted);
  }

  private async getMasterKey(): Promise<CryptoKey> {
    if (this.masterKeyPromise) {
      return this.masterKeyPromise;
    }
    this.masterKeyPromise = this.loadMasterKey();
    return this.masterKeyPromise;
  }

  private async loadMasterKey(): Promise<CryptoKey> {
    const metadata = await this.getMetadata();
    const keyBytes = fromBase64(metadata.masterKey);
    return crypto.subtle.importKey(
      'raw',
      keyBytes,
      { name: 'AES-GCM' },
      false,
      ['encrypt', 'decrypt']
    );
  }
}
