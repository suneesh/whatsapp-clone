import nacl from 'tweetnacl';
import { bytesToHex } from './utils';
import {
  IdentityKeyMaterial,
  OneTimePrekeyMaterial,
  SignedPrekeyMaterial,
} from './types';

export class CryptoEngine {
  async generateIdentityMaterial(): Promise<IdentityKeyMaterial> {
    const seed = nacl.randomBytes(32);
    const signingKeyPair = nacl.sign.keyPair.fromSeed(seed);
    const x25519KeyPair = nacl.box.keyPair.fromSecretKey(seed);

    const fingerprintBytes = new Uint8Array(
      await crypto.subtle.digest('SHA-256', x25519KeyPair.publicKey)
    );

    const fingerprintHex = bytesToHex(fingerprintBytes).toUpperCase();
    const fingerprint = fingerprintHex.slice(0, 60);

    return {
      seed,
      signingPublicKey: signingKeyPair.publicKey,
      signingSecretKey: signingKeyPair.secretKey,
      x25519PublicKey: x25519KeyPair.publicKey,
      x25519SecretKey: x25519KeyPair.secretKey,
      fingerprint,
    };
  }

  generateSignedPrekey(
    keyId: number,
    identitySigningSecretKey: Uint8Array
  ): SignedPrekeyMaterial {
    const secretSeed = nacl.randomBytes(32);
    const keyPair = nacl.box.keyPair.fromSecretKey(secretSeed);
    const signature = nacl.sign.detached(keyPair.publicKey, identitySigningSecretKey);

    return {
      keyId,
      publicKey: keyPair.publicKey,
      secretKey: keyPair.secretKey,
      signature,
      createdAt: Date.now(),
    };
  }

  generateOneTimePrekeys(
    startKeyId: number,
    count: number
  ): OneTimePrekeyMaterial[] {
    const results: OneTimePrekeyMaterial[] = [];
    for (let i = 0; i < count; i += 1) {
      const keyId = startKeyId + i;
      const secretSeed = nacl.randomBytes(32);
      const keyPair = nacl.box.keyPair.fromSecretKey(secretSeed);
      results.push({
        keyId,
        publicKey: keyPair.publicKey,
        secretKey: keyPair.secretKey,
        createdAt: Date.now(),
        uploaded: false,
      });
    }
    return results;
  }
}
