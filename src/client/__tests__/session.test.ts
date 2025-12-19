import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SessionManager } from '../crypto/SessionManager';
import { KeyManager } from '../crypto/KeyManager';
import { toBase64, encodeUtf8, decodeUtf8 } from '../crypto/utils';
import type { RemotePrekeyBundle } from '../crypto/types';

// Mock fetch globally
global.fetch = vi.fn();

describe('Session Manager Integration', () => {
  let aliceSessionManager: SessionManager;
  let bobSessionManager: SessionManager;
  let aliceKeyManager: KeyManager;
  let bobKeyManager: KeyManager;
  let aliceUserId: string;
  let bobUserId: string;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Unique user IDs for isolation
    aliceUserId = `alice-${Date.now()}-${Math.random()}`;
    bobUserId = `bob-${Date.now()}-${Math.random()}`;

    // Setup Alice
    aliceKeyManager = new KeyManager(aliceUserId);
    await aliceKeyManager.initialize();
    aliceSessionManager = new SessionManager(aliceUserId, aliceKeyManager);

    // Setup Bob
    bobKeyManager = new KeyManager(bobUserId);
    await bobKeyManager.initialize();
    bobSessionManager = new SessionManager(bobUserId, bobKeyManager);
  });

  describe('First Message Flow', () => {
    it('should send and receive encrypted message', async () => {
      // Mock Bob's prekey bundle
      const bobStorage = bobKeyManager.getStorage();
      const bobIdentity = await bobStorage.loadIdentity();
      const bobSignedPrekey = await bobStorage.loadSignedPrekey();
      const bobOneTimePrekey = await bobStorage.loadOneTimePrekey(1);

      const bobBundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity!.x25519PublicKey),
        signingKey: toBase64(bobIdentity!.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey!.keyId,
          publicKey: toBase64(bobSignedPrekey!.publicKey),
          signature: toBase64(bobSignedPrekey!.signature),
          createdAt: bobSignedPrekey!.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity!.fingerprint,
      };

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => bobBundle,
      });

      // Alice sends message to Bob
      const plaintext = 'Hello Bob!';
      const encrypted = await aliceSessionManager.encryptMessage(bobUserId, plaintext);

      expect(encrypted.ciphertext).toBeDefined();
      expect(encrypted.x3dh).toBeDefined();
      // Note: One-time prekeys are currently disabled in implementation
      expect(encrypted.x3dh?.usedOneTimePrekeyId).toBeUndefined();

      // Bob decrypts message
      const decrypted = await bobSessionManager.decryptMessage(aliceUserId, encrypted);
      expect(decrypted).toBe(plaintext);
    });

    it('should create session on both sides', async () => {
      const bobStorage = bobKeyManager.getStorage();
      const bobIdentity = await bobStorage.loadIdentity();
      const bobSignedPrekey = await bobStorage.loadSignedPrekey();
      const bobOneTimePrekey = await bobStorage.loadOneTimePrekey(1);

      const bobBundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity!.x25519PublicKey),
        signingKey: toBase64(bobIdentity!.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey!.keyId,
          publicKey: toBase64(bobSignedPrekey!.publicKey),
          signature: toBase64(bobSignedPrekey!.signature),
          createdAt: bobSignedPrekey!.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity!.fingerprint,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => bobBundle,
      });

      const encrypted = await aliceSessionManager.encryptMessage(bobUserId, 'Hi');
      await bobSessionManager.decryptMessage(aliceUserId, encrypted);

      // Verify sessions exist
      const aliceStorage = aliceKeyManager.getStorage();
      const aliceSession = await aliceStorage.loadSession(bobUserId);
      const bobSession = await bobStorage.loadSession(aliceUserId);

      expect(aliceSession).toBeDefined();
      expect(bobSession).toBeDefined();
    });
  });

  describe('Bidirectional Communication', () => {
    it('should handle back-and-forth messages', async () => {
      // Setup Bob's bundle for Alice
      const bobStorage = bobKeyManager.getStorage();
      const bobIdentity = await bobStorage.loadIdentity();
      const bobSignedPrekey = await bobStorage.loadSignedPrekey();
      const bobOneTimePrekey = await bobStorage.loadOneTimePrekey(1);

      const bobBundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity!.x25519PublicKey),
        signingKey: toBase64(bobIdentity!.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey!.keyId,
          publicKey: toBase64(bobSignedPrekey!.publicKey),
          signature: toBase64(bobSignedPrekey!.signature),
          createdAt: bobSignedPrekey!.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity!.fingerprint,
      };

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => bobBundle,
      });

      // Alice -> Bob
      const msg1 = 'Hi Bob!';
      const enc1 = await aliceSessionManager.encryptMessage(bobUserId, msg1);
      const dec1 = await bobSessionManager.decryptMessage(aliceUserId, enc1);
      expect(dec1).toBe(msg1);

      // Bob -> Alice (no fetch needed, session exists)
      const msg2 = 'Hi Alice!';
      const enc2 = await bobSessionManager.encryptMessage(aliceUserId, msg2);
      const dec2 = await aliceSessionManager.decryptMessage(bobUserId, enc2);
      expect(dec2).toBe(msg2);

      // Alice -> Bob again
      const msg3 = 'How are you?';
      const enc3 = await aliceSessionManager.encryptMessage(bobUserId, msg3);
      expect(enc3.x3dh).toBeUndefined(); // No X3DH for subsequent messages
      const dec3 = await bobSessionManager.decryptMessage(aliceUserId, enc3);
      expect(dec3).toBe(msg3);

      // Verify fetch was called for key rotation checks
      // (SessionManager checks on every encryptMessage)
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle multiple messages in sequence', async () => {
      const bobStorage = bobKeyManager.getStorage();
      const bobIdentity = await bobStorage.loadIdentity();
      const bobSignedPrekey = await bobStorage.loadSignedPrekey();

      const bobBundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity!.x25519PublicKey),
        signingKey: toBase64(bobIdentity!.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey!.keyId,
          publicKey: toBase64(bobSignedPrekey!.publicKey),
          signature: toBase64(bobSignedPrekey!.signature),
          createdAt: bobSignedPrekey!.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity!.fingerprint,
      };

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => bobBundle,
      });

      const messages = ['Msg 1', 'Msg 2', 'Msg 3', 'Msg 4', 'Msg 5'];

      for (const msg of messages) {
        const encrypted = await aliceSessionManager.encryptMessage(bobUserId, msg);
        const decrypted = await bobSessionManager.decryptMessage(aliceUserId, encrypted);
        expect(decrypted).toBe(msg);
      }
    });
  });

  describe('Error Handling', () => {
    it('should handle missing prekey bundle', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({}),
      });

      await expect(
        aliceSessionManager.encryptMessage(bobUserId, 'Hello')
      ).rejects.toThrow("Recipient hasn't set up encryption yet");
    });

    it('should handle network errors', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      await expect(
        aliceSessionManager.encryptMessage(bobUserId, 'Hello')
      ).rejects.toThrow('Network error while establishing encrypted session');
    });

    it('should require X3DH data for first message', async () => {
      const invalidMessage = {
        ciphertext: 'test',
        x3dhData: undefined,
      };

      await expect(
        bobSessionManager.decryptMessage(aliceUserId, invalidMessage as any)
      ).rejects.toThrow();
    });
  });

  describe('Session Persistence', () => {
    it('should persist session across manager instances', async () => {
      const bobStorage = bobKeyManager.getStorage();
      const bobIdentity = await bobStorage.loadIdentity();
      const bobSignedPrekey = await bobStorage.loadSignedPrekey();

      const bobBundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity!.x25519PublicKey),
        signingKey: toBase64(bobIdentity!.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey!.keyId,
          publicKey: toBase64(bobSignedPrekey!.publicKey),
          signature: toBase64(bobSignedPrekey!.signature),
          createdAt: bobSignedPrekey!.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity!.fingerprint,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => bobBundle,
      });

      // Send first message
      const enc1 = await aliceSessionManager.encryptMessage(bobUserId, 'First');
      await bobSessionManager.decryptMessage(aliceUserId, enc1);

      // Create new manager instances (simulate app restart)
      const newAliceManager = new SessionManager(aliceUserId, aliceKeyManager);
      const newBobManager = new SessionManager(bobUserId, bobKeyManager);

      // Continue conversation without new X3DH
      const enc2 = await newAliceManager.encryptMessage(bobUserId, 'Second');
      expect(enc2.x3dhData).toBeUndefined();

      const dec2 = await newBobManager.decryptMessage(aliceUserId, enc2);
      expect(dec2).toBe('Second');
    });
  });

  describe('Reset E2EE', () => {
    it('should clear all data and regenerate keys', async () => {
      const bobStorage = bobKeyManager.getStorage();
      const aliceStorage = aliceKeyManager.getStorage();
      const bobIdentity = await bobStorage.loadIdentity();
      const bobSignedPrekey = await bobStorage.loadSignedPrekey();

      const bobBundle: RemotePrekeyBundle = {
        identityKey: toBase64(bobIdentity!.x25519PublicKey),
        signingKey: toBase64(bobIdentity!.signingPublicKey),
        signedPrekey: {
          keyId: bobSignedPrekey!.keyId,
          publicKey: toBase64(bobSignedPrekey!.publicKey),
          signature: toBase64(bobSignedPrekey!.signature),
          createdAt: bobSignedPrekey!.createdAt,
        },
        oneTimePrekey: null,
        fingerprint: bobIdentity!.fingerprint,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => bobBundle,
      });

      // Create session
      await aliceSessionManager.encryptMessage(bobUserId, 'Test');

      // Reset E2EE (via KeyManager)
      await aliceKeyManager.resetE2EE();

      // Verify session cleared
      expect(await aliceStorage.loadSession(bobUserId)).toBeNull();

      // Verify new identity generated
      const newIdentity = await aliceStorage.loadIdentity();
      expect(newIdentity).toBeDefined();
      expect(newIdentity?.fingerprint).not.toBe(bobIdentity?.fingerprint);
    });
  });
});
