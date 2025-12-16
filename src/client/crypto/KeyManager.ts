import nacl from 'tweetnacl';
import { CryptoEngine } from './CryptoEngine';
import { toBase64 } from './utils';
import { PrekeyBundlePayload, SignedPrekeyMaterial } from './types';
import {
  KeyStorage,
  StoredIdentityRecord,
  StoredOneTimePrekeyRecord,
  StoredSignedPrekeyRecord,
} from '../storage/KeyStorage';

export const ONE_TIME_PREKEY_TARGET = 100;
export const MAX_UPLOAD_PREKEYS = 50;
export const SIGNED_PREKEY_TTL_MS = 7 * 24 * 60 * 60 * 1000;

export class KeyManager {
  private readonly storage: KeyStorage;

  private readonly engine = new CryptoEngine();

  private identityCache?: StoredIdentityRecord;

  constructor(private readonly userId: string) {
    this.storage = new KeyStorage(userId);
  }

  async initialize(): Promise<void> {
    await this.ensureIdentity();
    await this.ensureSignedPrekey();
    await this.ensureOneTimePrekeys();
  }

  async getFingerprint(): Promise<string> {
    const identity = await this.getIdentity();
    return identity.fingerprint;
  }

  async getPendingBundle(): Promise<PrekeyBundlePayload | null> {
    const identity = await this.getIdentity();
    const signedPrekey = await this.storage.loadSignedPrekey();
    const pendingSignedPrekey = signedPrekey && !signedPrekey.uploaded ? signedPrekey : null;
    const pendingOneTimePrekeys = await this.storage.getPendingOneTimePrekeys(MAX_UPLOAD_PREKEYS);

    if (!pendingSignedPrekey && pendingOneTimePrekeys.length === 0) {
      return null;
    }

    return {
      identityKey: toBase64(identity.x25519PublicKey),
      signingKey: toBase64(identity.signingPublicKey),
      fingerprint: identity.fingerprint,
      signedPrekey: pendingSignedPrekey
        ? {
            keyId: pendingSignedPrekey.keyId,
            publicKey: toBase64(pendingSignedPrekey.publicKey),
            signature: toBase64(pendingSignedPrekey.signature),
          }
        : null,
      oneTimePrekeys: pendingOneTimePrekeys.map((prekey) => ({
        keyId: prekey.keyId,
        publicKey: toBase64(prekey.publicKey),
      })),
    };
  }

  async markBundleUploaded(bundle: PrekeyBundlePayload | null): Promise<void> {
    if (!bundle) {
      return;
    }

    if (bundle.signedPrekey) {
      await this.storage.markSignedPrekeyUploaded(bundle.signedPrekey.keyId);
    }

    if (bundle.oneTimePrekeys.length > 0) {
      await this.storage.markOneTimePrekeysUploaded(bundle.oneTimePrekeys.map((prekey) => prekey.keyId));
    }

    await this.storage.updateLastUpload(Date.now());
  }

  private async ensureIdentity(): Promise<void> {
    const identity = await this.storage.loadIdentity();
    if (identity) {
      this.identityCache = identity;
      return;
    }

    const material = await this.engine.generateIdentityMaterial();
    await this.storage.saveIdentity({
      seed: material.seed,
      fingerprint: material.fingerprint,
      signingPublicKey: material.signingPublicKey,
      x25519PublicKey: material.x25519PublicKey,
      createdAt: Date.now(),
    });
    this.identityCache = await this.storage.loadIdentity();
  }

  private async ensureSignedPrekey(): Promise<void> {
    const existing = await this.storage.loadSignedPrekey();
    const needsNewSignedPrekey = !existing || Date.now() - existing.createdAt > SIGNED_PREKEY_TTL_MS;

    if (!needsNewSignedPrekey) {
      return;
    }

    await this.createSignedPrekey();
  }

  private async ensureOneTimePrekeys(): Promise<void> {
    const count = await this.storage.countOneTimePrekeys();
    if (count >= ONE_TIME_PREKEY_TARGET) {
      return;
    }
    const needed = ONE_TIME_PREKEY_TARGET - count;
    await this.createOneTimePrekeys(needed);
  }

  async queueOneTimePrekeys(batchSize: number): Promise<void> {
    if (batchSize <= 0) {
      return;
    }
    await this.createOneTimePrekeys(batchSize);
  }

  async rotateSignedPrekey(): Promise<void> {
    await this.createSignedPrekey();
  }

  private async getIdentity(): Promise<StoredIdentityRecord> {
    if (!this.identityCache) {
      const loaded = await this.storage.loadIdentity();
      if (!loaded) {
        throw new Error('Identity keys missing');
      }
      this.identityCache = loaded;
    }
    return this.identityCache;
  }

  async getIdentityMaterial(): Promise<StoredIdentityRecord> {
    return this.getIdentity();
  }

  getStorage(): KeyStorage {
    return this.storage;
  }

  private getSigningSecretKey(identity: StoredIdentityRecord): Uint8Array {
    const signingKeyPair = nacl.sign.keyPair.fromSeed(identity.seed);
    return signingKeyPair.secretKey;
  }

  private async createSignedPrekey(): Promise<void> {
    const identity = await this.getIdentity();
    const keyId = await this.storage.ensureNextPrekeyIdIncrement(1);
    const material: SignedPrekeyMaterial = this.engine.generateSignedPrekey(
      keyId,
      this.getSigningSecretKey(identity)
    );

    await this.storage.saveSignedPrekey({
      keyId: material.keyId,
      publicKey: material.publicKey,
      secretKey: material.secretKey,
      signature: material.signature,
      createdAt: material.createdAt,
    });
  }

  private async createOneTimePrekeys(count: number): Promise<void> {
    if (count <= 0) {
      return;
    }
    const startKeyId = await this.storage.ensureNextPrekeyIdIncrement(count);
    const materials = this.engine.generateOneTimePrekeys(startKeyId, count);
    await this.storage.saveOneTimePrekeys(
      materials.map((item) => ({
        keyId: item.keyId,
        publicKey: item.publicKey,
        secretKey: item.secretKey,
        createdAt: item.createdAt,
      }))
    );
  }
}
