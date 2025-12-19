import { describe, it, expect, beforeEach } from 'vitest';
import { performX3DHInitiator, performX3DHResponder } from '../crypto/X3DH';
import { CryptoEngine } from '../crypto/CryptoEngine';
import { toBase64 } from '../crypto/utils';
import type { RemotePrekeyBundle } from '../crypto/types';
import nacl from 'tweetnacl';

describe('X3DH Key Agreement', () => {
  let engine: CryptoEngine;
  let aliceIdentity: Awaited<ReturnType<CryptoEngine['generateIdentityMaterial']>>;
  let bobIdentity: Awaited<ReturnType<CryptoEngine['generateIdentityMaterial']>>;
  let bobSignedPrekey: ReturnType<CryptoEngine['generateSignedPrekey']>;
  let bobOneTimePrekey: ReturnType<CryptoEngine['generateOneTimePrekeys']>[0];

  beforeEach(async () => {
    engine = new CryptoEngine();
    aliceIdentity = await engine.generateIdentityMaterial();
    bobIdentity = await engine.generateIdentityMaterial();
    bobSignedPrekey = engine.generateSignedPrekey(1, bobIdentity.signingSecretKey);
    bobOneTimePrekey = engine.generateOneTimePrekeys(1, 1)[0];
  });

  describe('Initiator', () => {
    it('should perform X3DH and generate shared secret', async () => {
      const bundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity.x25519PublicKey),
        signingKey: toBase64(bobIdentity.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey.keyId,
          publicKey: toBase64(bobSignedPrekey.publicKey),
          signature: toBase64(bobSignedPrekey.signature),
          createdAt: bobSignedPrekey.createdAt,
        },
        oneTimePrekey: {
          keyId: bobOneTimePrekey.keyId,
          publicKey: toBase64(bobOneTimePrekey.publicKey),
        },
        fingerprint: bobIdentity.fingerprint,
      };

      const result = await performX3DHInitiator({
        localIdentitySeed: aliceIdentity.seed,
        remoteBundle: bundle
      });

      expect(result.sharedSecret).toBeInstanceOf(Uint8Array);
      expect(result.sharedSecret.length).toBe(32);
      expect(result.localEphemeralKeyPair.publicKey).toBeInstanceOf(Uint8Array);
      // Note: One-time prekeys are currently disabled in implementation
      expect(result.usedOneTimePrekeyId).toBeUndefined();
    });

    it('should work without one-time prekey', async () => {
      const bundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity.x25519PublicKey),
        signingKey: toBase64(bobIdentity.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey.keyId,
          publicKey: toBase64(bobSignedPrekey.publicKey),
          signature: toBase64(bobSignedPrekey.signature),
          createdAt: bobSignedPrekey.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity.fingerprint,
      };

      const result = await performX3DHInitiator({
        localIdentitySeed: aliceIdentity.seed,
        remoteBundle: bundle
      });

      expect(result.sharedSecret).toBeInstanceOf(Uint8Array);
      expect(result.usedOneTimePrekeyId).toBeUndefined();
    });

    it('should reject invalid signature', async () => {
      const bundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity.x25519PublicKey),
        signingKey: toBase64(bobIdentity.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey.keyId,
          publicKey: toBase64(bobSignedPrekey.publicKey),
          signature: toBase64(new Uint8Array(64).fill(0)), // Invalid signature
          createdAt: bobSignedPrekey.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity.fingerprint,
      };

      await expect(
        performX3DHInitiator({
          localIdentitySeed: aliceIdentity.seed,
          remoteBundle: bundle
        })
      ).rejects.toThrow('Invalid signed prekey signature');
    });
  });

  describe('Responder', () => {
    it('should derive same shared secret as initiator', async () => {
      const bundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity.x25519PublicKey),
        signingKey: toBase64(bobIdentity.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey.keyId,
          publicKey: toBase64(bobSignedPrekey.publicKey),
          signature: toBase64(bobSignedPrekey.signature),
          createdAt: bobSignedPrekey.createdAt,
        },
        oneTimePrekey: {
          keyId: bobOneTimePrekey.keyId,
          publicKey: toBase64(bobOneTimePrekey.publicKey),
        },
        fingerprint: bobIdentity.fingerprint,
      };

      const initiatorResult = await performX3DHInitiator({
        localIdentitySeed: aliceIdentity.seed,
        remoteBundle: bundle
      });

      // Regenerate full keypair from stored secret key
      const bobSignedPrekeyPair = nacl.box.keyPair.fromSecretKey(bobSignedPrekey.secretKey);
      // Note: Don't pass one-time prekey as they're disabled in initiator implementation

      const responderSecret = await performX3DHResponder({
        localIdentitySeed: bobIdentity.seed,
        localSignedPrekeyPair: bobSignedPrekeyPair,
        remoteIdentityKey: aliceIdentity.x25519PublicKey,
        remoteEphemeralKey: initiatorResult.localEphemeralKeyPair.publicKey
      });

      expect(toBase64(initiatorResult.sharedSecret)).toBe(toBase64(responderSecret));
    });

    it('should work without one-time prekey', async () => {
      const bundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity.x25519PublicKey),
        signingKey: toBase64(bobIdentity.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey.keyId,
          publicKey: toBase64(bobSignedPrekey.publicKey),
          signature: toBase64(bobSignedPrekey.signature),
          createdAt: bobSignedPrekey.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity.fingerprint,
      };

      const initiatorResult = await performX3DHInitiator({
        localIdentitySeed: aliceIdentity.seed,
        remoteBundle: bundle
      });

      // Regenerate full keypair from stored secret key
      const bobSignedPrekeyPair = nacl.box.keyPair.fromSecretKey(bobSignedPrekey.secretKey);

      const responderSecret = await performX3DHResponder({
        localIdentitySeed: bobIdentity.seed,
        localSignedPrekeyPair: bobSignedPrekeyPair,
        remoteIdentityKey: aliceIdentity.x25519PublicKey,
        remoteEphemeralKey: initiatorResult.localEphemeralKeyPair.publicKey
      });

      expect(toBase64(initiatorResult.sharedSecret)).toBe(toBase64(responderSecret));
    });
  });

  describe('Protocol Symmetry', () => {
    it('should always derive same shared secret', async () => {
      // Run X3DH multiple times to ensure consistency
      const results: string[] = [];

      for (let i = 0; i < 3; i++) {
        const bundle: RemotePrekeyBundle = {
          identityKey: toBase64(bobIdentity.x25519PublicKey),
          signingKey: toBase64(bobIdentity.signingPublicKey),
          signedPrekey: {
            keyId: bobSignedPrekey.keyId,
            publicKey: toBase64(bobSignedPrekey.publicKey),
            signature: toBase64(bobSignedPrekey.signature),
            createdAt: bobSignedPrekey.createdAt,
          },
          oneTimePrekey: {
            keyId: bobOneTimePrekey.keyId,
            publicKey: toBase64(bobOneTimePrekey.publicKey),
          },
          fingerprint: bobIdentity.fingerprint,
        };

        const initiatorResult = await performX3DHInitiator({
          localIdentitySeed: aliceIdentity.seed,
          remoteBundle: bundle
        });

        // Regenerate full keypair from stored secret key
        const bobSignedPrekeyPair = nacl.box.keyPair.fromSecretKey(bobSignedPrekey.secretKey);
        // Note: Don't pass one-time prekey as they're disabled in initiator implementation

        const responderSecret = await performX3DHResponder({
          localIdentitySeed: bobIdentity.seed,
          localSignedPrekeyPair: bobSignedPrekeyPair,
          remoteIdentityKey: aliceIdentity.x25519PublicKey,
          remoteEphemeralKey: initiatorResult.localEphemeralKeyPair.publicKey
        });

        expect(toBase64(initiatorResult.sharedSecret)).toBe(toBase64(responderSecret));
        results.push(toBase64(responderSecret));
      }

      // Each run has different ephemeral key, so secrets will differ
      const uniqueSecrets = new Set(results);
      expect(uniqueSecrets.size).toBe(3);
    });
  });
});
