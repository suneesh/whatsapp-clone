import { describe, it, expect } from 'vitest';
import { CryptoEngine } from '../crypto/CryptoEngine';
import { KeyStorage } from '../storage/KeyStorage';
import nacl from 'tweetnacl';

describe('E2EE Core Functionality', () => {
  describe('CryptoEngine', () => {
    let engine: CryptoEngine;

    beforeEach(() => {
      engine = new CryptoEngine();
    });

    it('should generate identity material', async () => {
      const identity = await engine.generateIdentityMaterial();

      expect(identity.seed).toBeInstanceOf(Uint8Array);
      expect(identity.seed.length).toBe(32);
      expect(identity.x25519PublicKey).toBeInstanceOf(Uint8Array);
      expect(identity.x25519PublicKey.length).toBe(32);
      expect(identity.signingPublicKey).toBeInstanceOf(Uint8Array);
      expect(identity.signingPublicKey.length).toBe(32);
      expect(identity.signingSecretKey).toBeInstanceOf(Uint8Array);
      expect(identity.signingSecretKey.length).toBe(64);
      expect(typeof identity.fingerprint).toBe('string');
      expect(identity.fingerprint).toMatch(/^[0-9A-F]+$/);
    });

    it('should generate unique identities', async () => {
      const id1 = await engine.generateIdentityMaterial();
      const id2 = await engine.generateIdentityMaterial();

      expect(id1.fingerprint).not.toBe(id2.fingerprint);
    });

    it('should generate signed prekey with valid signature', async () => {
      const identity = await engine.generateIdentityMaterial();
      const prekey = engine.generateSignedPrekey(1, identity.signingSecretKey);

      expect(prekey.keyId).toBe(1);
      expect(prekey.publicKey.length).toBe(32);
      expect(prekey.signature.length).toBe(64);

      // Verify signature
      const isValid = nacl.sign.detached.verify(
        prekey.publicKey,
        prekey.signature,
        identity.signingPublicKey
      );
      expect(isValid).toBe(true);
    });

    it('should generate one-time prekeys', () => {
      const prekeys = engine.generateOneTimePrekeys(1, 5);

      expect(prekeys.length).toBe(5);
      expect(prekeys[0].keyId).toBe(1);
      expect(prekeys[4].keyId).toBe(5);

      prekeys.forEach(pk => {
        expect(pk.publicKey.length).toBe(32);
        expect(pk.secretKey.length).toBe(32);
      });
    });
  });

  describe('KeyStorage', () => {
    let storage: KeyStorage;
    let engine: CryptoEngine;
    let testUserId: string;

    beforeEach(() => {
      // Use unique user ID for each test to avoid interference
      testUserId = `test-user-${Date.now()}-${Math.random()}`;
      storage = new KeyStorage(testUserId);
      engine = new CryptoEngine();
    });

    it('should save and load identity', async () => {
      const identity = await engine.generateIdentityMaterial();
      await storage.saveIdentity(identity);

      const loaded = await storage.loadIdentity();
      expect(loaded).not.toBeNull();
      expect(loaded?.fingerprint).toBe(identity.fingerprint);
    });

    it('should save and load signed prekey', async () => {
      const identity = await engine.generateIdentityMaterial();
      const prekey = engine.generateSignedPrekey(1, identity.signingSecretKey);

      await storage.saveSignedPrekey(prekey);

      const loaded = await storage.loadSignedPrekey();
      expect(loaded).not.toBeNull();
      expect(loaded?.keyId).toBe(1);
    });

    it('should save and load one-time prekeys', async () => {
      const prekeys = engine.generateOneTimePrekeys(1, 5);
      await storage.saveOneTimePrekeys(prekeys);

      const count = await storage.countOneTimePrekeys();
      expect(count).toBe(5);

      const prekey = await storage.loadOneTimePrekey(1);
      expect(prekey).not.toBeNull();
      expect(prekey?.keyId).toBe(1);
    });

    it('should delete one-time prekey', async () => {
      const prekeys = engine.generateOneTimePrekeys(1, 3);
      await storage.saveOneTimePrekeys(prekeys);

      await storage.deleteOneTimePrekey(2);

      // Verify deleted prekey is gone
      const deleted = await storage.loadOneTimePrekey(2);
      expect(deleted).toBeUndefined();

      // Verify others still exist
      const prekey1 = await storage.loadOneTimePrekey(1);
      const prekey3 = await storage.loadOneTimePrekey(3);
      expect(prekey1).not.toBeNull();
      expect(prekey3).not.toBeNull();
    });

    it('should clear all E2EE data', async () => {
      const identity = await engine.generateIdentityMaterial();
      const prekey = engine.generateSignedPrekey(1, identity.signingSecretKey);
      const oneTimePrekeys = engine.generateOneTimePrekeys(1, 5);

      await storage.saveIdentity(identity);
      await storage.saveSignedPrekey(prekey);
      await storage.saveOneTimePrekeys(oneTimePrekeys);

      await storage.clearAllE2EEData();

      expect(await storage.loadIdentity()).toBeNull();
      expect(await storage.loadSignedPrekey()).toBeNull();
      expect(await storage.countOneTimePrekeys()).toBe(0);
    });
  });
});
