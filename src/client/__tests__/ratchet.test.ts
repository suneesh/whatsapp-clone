import { describe, it, expect, beforeEach } from 'vitest';
import { RatchetEngine, type RatchetState } from '../crypto/RatchetEngine';

describe('Double Ratchet Engine', () => {
  let engine: RatchetEngine;
  let sharedSecret: Uint8Array;

  beforeEach(() => {
    engine = new RatchetEngine();
    sharedSecret = new Uint8Array(32);
    crypto.getRandomValues(sharedSecret);
  });

  describe('Initialization', () => {
    it('should initialize sender with remote ratchet key', async () => {
      const remoteRatchetKey = new Uint8Array(32);
      crypto.getRandomValues(remoteRatchetKey);

      const state = await engine.initializeRatchet(sharedSecret, remoteRatchetKey);

      expect(state.rootKey).toBeInstanceOf(Uint8Array);
      expect(state.sendingChainKey).toBeDefined();
      expect(state.dhRatchetRemoteKey).toEqual(remoteRatchetKey);
    });

    it('should initialize receiver without remote ratchet key', async () => {
      const state = await engine.initializeRatchet(sharedSecret);

      expect(state.rootKey).toBeInstanceOf(Uint8Array);
      expect(state.receivingChainKey).toBeDefined();
      expect(state.dhRatchetRemoteKey).toBeNull();
    });
  });

  describe('Message Encryption', () => {
    it('should encrypt message', async () => {
      const remoteRatchetKey = new Uint8Array(32);
      crypto.getRandomValues(remoteRatchetKey);

      let state = await engine.initializeRatchet(sharedSecret, remoteRatchetKey);

      const plaintext = new TextEncoder().encode('Hello, World!');
      const result = await engine.encryptMessage(state, plaintext);

      expect(result.message.ciphertext).toBeInstanceOf(Uint8Array);
      expect(result.message.header).toBeDefined();
      expect(result.message.header.ratchetKey).toBeInstanceOf(Uint8Array);
      expect(result.message.header.messageNumber).toBe(0);
      expect(result.newState).toBeDefined();
    });

    it('should increment message number', async () => {
      const remoteRatchetKey = new Uint8Array(32);
      crypto.getRandomValues(remoteRatchetKey);

      let state = await engine.initializeRatchet(sharedSecret, remoteRatchetKey);

      const plaintext = new TextEncoder().encode('Message');

      const result1 = await engine.encryptMessage(state, plaintext);
      expect(result1.message.header.messageNumber).toBe(0);

      const result2 = await engine.encryptMessage(result1.newState, plaintext);
      expect(result2.message.header.messageNumber).toBe(1);

      const result3 = await engine.encryptMessage(result2.newState, plaintext);
      expect(result3.message.header.messageNumber).toBe(2);
    });

    it('should produce different ciphertexts for same plaintext', async () => {
      const remoteRatchetKey = new Uint8Array(32);
      crypto.getRandomValues(remoteRatchetKey);

      let state = await engine.initializeRatchet(sharedSecret, remoteRatchetKey);

      const plaintext = new TextEncoder().encode('Same message');

      const result1 = await engine.encryptMessage(state, plaintext);
      const result2 = await engine.encryptMessage(result1.newState, plaintext);

      expect(result1.message.ciphertext).not.toEqual(result2.message.ciphertext);
    });
  });

  describe('Message Decryption', () => {
    it('should decrypt message', async () => {
      // Initialize sender
      const senderEngine = new RatchetEngine();
      const receiverEngine = new RatchetEngine();

      const receiverInitState = await receiverEngine.initializeRatchet(sharedSecret);
      const senderInitState = await senderEngine.initializeRatchet(
        sharedSecret,
        receiverInitState.dhRatchetKeyPair!.publicKey
      );

      // Encrypt message
      const plaintext = new TextEncoder().encode('Test message');
      const encrypted = await senderEngine.encryptMessage(senderInitState, plaintext);

      // Decrypt message
      const decrypted = await receiverEngine.decryptMessage(
        receiverInitState,
        encrypted.message
      );

      const decryptedText = new TextDecoder().decode(decrypted.plaintext);
      expect(decryptedText).toBe('Test message');
    });

    it('should decrypt multiple messages in order', async () => {
      const senderEngine = new RatchetEngine();
      const receiverEngine = new RatchetEngine();

      let receiverState = await receiverEngine.initializeRatchet(sharedSecret);
      let senderState = await senderEngine.initializeRatchet(
        sharedSecret,
        receiverState.dhRatchetKeyPair!.publicKey
      );

      const messages = ['First', 'Second', 'Third'];
      const encrypted = [];

      // Encrypt all messages
      for (const msg of messages) {
        const plaintext = new TextEncoder().encode(msg);
        const result = await senderEngine.encryptMessage(senderState, plaintext);
        encrypted.push(result.message);
        senderState = result.newState;
      }

      // Decrypt all messages
      for (let i = 0; i < encrypted.length; i++) {
        const result = await receiverEngine.decryptMessage(receiverState, encrypted[i]);
        const decryptedText = new TextDecoder().decode(result.plaintext);
        expect(decryptedText).toBe(messages[i]);
        receiverState = result.newState;
      }
    });
  });

  describe('Bidirectional Communication', () => {
    it('should handle back-and-forth messages', async () => {
      const aliceEngine = new RatchetEngine();
      const bobEngine = new RatchetEngine();

      // Alice as initial sender
      let bobState = await bobEngine.initializeRatchet(sharedSecret);
      let aliceState = await aliceEngine.initializeRatchet(
        sharedSecret,
        bobState.dhRatchetKeyPair!.publicKey
      );

      // Alice -> Bob
      const msg1 = new TextEncoder().encode('Hello Bob');
      const enc1 = await aliceEngine.encryptMessage(aliceState, msg1);
      const dec1 = await bobEngine.decryptMessage(bobState, enc1.message);
      expect(new TextDecoder().decode(dec1.plaintext)).toBe('Hello Bob');

      aliceState = enc1.newState;
      bobState = dec1.newState;

      // Bob -> Alice (triggers DH ratchet)
      const msg2 = new TextEncoder().encode('Hello Alice');
      const enc2 = await bobEngine.encryptMessage(bobState, msg2);
      const dec2 = await aliceEngine.decryptMessage(aliceState, enc2.message);
      expect(new TextDecoder().decode(dec2.plaintext)).toBe('Hello Alice');

      aliceState = dec2.newState;
      bobState = enc2.newState;

      // Alice -> Bob again
      const msg3 = new TextEncoder().encode('How are you?');
      const enc3 = await aliceEngine.encryptMessage(aliceState, msg3);
      const dec3 = await bobEngine.decryptMessage(bobState, enc3.message);
      expect(new TextDecoder().decode(dec3.plaintext)).toBe('How are you?');
    });
  });

  describe('Forward Secrecy', () => {
    it('should update chain keys after each message', async () => {
      const remoteRatchetKey = new Uint8Array(32);
      crypto.getRandomValues(remoteRatchetKey);

      let state = await engine.initializeRatchet(sharedSecret, remoteRatchetKey);
      const initialChainKey = state.sendingChainKey;

      const plaintext = new TextEncoder().encode('Test');
      const result = await engine.encryptMessage(state, plaintext);

      // Chain key should have changed
      expect(result.newState.sendingChainKey).not.toEqual(initialChainKey);
    });
  });

  describe('Out-of-Order Messages', () => {
    it('should handle skipped messages', async () => {
      const senderEngine = new RatchetEngine();
      const receiverEngine = new RatchetEngine();

      let receiverState = await receiverEngine.initializeRatchet(sharedSecret);
      let senderState = await senderEngine.initializeRatchet(
        sharedSecret,
        receiverState.dhRatchetKeyPair!.publicKey
      );

      // Encrypt 3 messages
      const msg1 = new TextEncoder().encode('Message 1');
      const enc1 = await senderEngine.encryptMessage(senderState, msg1);
      senderState = enc1.newState;

      const msg2 = new TextEncoder().encode('Message 2');
      const enc2 = await senderEngine.encryptMessage(senderState, msg2);
      senderState = enc2.newState;

      const msg3 = new TextEncoder().encode('Message 3');
      const enc3 = await senderEngine.encryptMessage(senderState, msg3);

      // Receive message 1
      const dec1 = await receiverEngine.decryptMessage(receiverState, enc1.message);
      expect(new TextDecoder().decode(dec1.plaintext)).toBe('Message 1');
      receiverState = dec1.newState;

      // Skip message 2, receive message 3
      const dec3 = await receiverEngine.decryptMessage(receiverState, enc3.message);
      expect(new TextDecoder().decode(dec3.plaintext)).toBe('Message 3');
      receiverState = dec3.newState;

      // Now receive skipped message 2
      const dec2 = await receiverEngine.decryptMessage(receiverState, enc2.message);
      expect(new TextDecoder().decode(dec2.plaintext)).toBe('Message 2');
    });
  });
});
