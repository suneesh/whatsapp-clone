import nacl from 'tweetnacl';
import { concatUint8Arrays, encodeUtf8, hkdf, toBase64, fromBase64 } from './utils';

export interface RatchetState {
  // Root key
  rootKey: Uint8Array;

  // Chain keys
  sendingChainKey: Uint8Array | null;
  receivingChainKey: Uint8Array | null;

  // DH ratchet keys
  dhRatchetKeyPair: {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
  } | null;
  dhRatchetRemoteKey: Uint8Array | null;

  // Message counters
  sendingChainLength: number;
  receivingChainLength: number;
  previousSendingChainLength: number;

  // Skipped message keys
  skippedMessageKeys: Map<string, Uint8Array>;
}

export interface MessageHeader {
  ratchetKey: Uint8Array;
  previousChainLength: number;
  messageNumber: number;
}

export interface EncryptedMessage {
  header: MessageHeader;
  ciphertext: Uint8Array;
  authTag: Uint8Array;
}

export interface SerializedEncryptedMessage {
  header: {
    ratchetKey: string;
    previousChainLength: number;
    messageNumber: number;
  };
  ciphertext: string;
  authTag: string;
  // X3DH initialization data (only present on first message)
  x3dh?: {
    senderIdentityKey: string;      // Base64 encoded public key
    senderEphemeralKey: string;     // Base64 encoded ephemeral public key
    usedSignedPrekeyId: number;     // Which signed prekey was used
    usedOneTimePrekeyId?: number;   // Which one-time prekey was used (if any)
  };
}

export class RatchetEngine {
  private readonly MAX_SKIP = 1000; // Maximum skipped message keys

  /**
   * Initialize Double Ratchet from shared secret (X3DH output)
   * @param sharedSecret - The shared secret from X3DH
   * @param remoteRatchetKey - The remote's initial ratchet public key (for receiver)
   */
  async initializeRatchet(
    sharedSecret: Uint8Array,
    remoteRatchetKey?: Uint8Array
  ): Promise<RatchetState> {
    // Derive root key and initial chain key from shared secret
    const kdfOutput = await this.kdfRootKey(sharedSecret, new Uint8Array(32));

    const state: RatchetState = {
      rootKey: kdfOutput.rootKey,
      sendingChainKey: null,
      receivingChainKey: kdfOutput.chainKey,
      dhRatchetKeyPair: null,
      dhRatchetRemoteKey: remoteRatchetKey || null,
      sendingChainLength: 0,
      receivingChainLength: 0,
      previousSendingChainLength: 0,
      skippedMessageKeys: new Map(),
    };

    // If we're the sender (no remote ratchet key yet), generate our ratchet key
    if (!remoteRatchetKey) {
      const ratchetKeyPair = nacl.box.keyPair();
      state.dhRatchetKeyPair = {
        publicKey: ratchetKeyPair.publicKey,
        secretKey: ratchetKeyPair.secretKey,
      };
      state.sendingChainKey = kdfOutput.chainKey;
      state.receivingChainKey = null;
    }

    return state;
  }

  /**
   * Encrypt a message
   */
  async encryptMessage(
    state: RatchetState,
    plaintext: Uint8Array
  ): Promise<{ message: EncryptedMessage; newState: RatchetState }> {
    // Ensure plaintext is a proper Uint8Array (handle cross-realm issues)
    const plaintextBytes = plaintext instanceof Uint8Array ? plaintext : new Uint8Array(plaintext);
    
    // If no sending chain, perform DH ratchet
    if (!state.sendingChainKey) {
      state = await this.performDHRatchet(state, null);
    }

    // Derive message key from chain key
    const messageKey = await this.kdfMessageKey(state.sendingChainKey!);

    // Advance chain key
    state.sendingChainKey = await this.kdfChainKey(state.sendingChainKey!);

    // Construct header
    const header: MessageHeader = {
      ratchetKey: state.dhRatchetKeyPair!.publicKey,
      previousChainLength: state.previousSendingChainLength,
      messageNumber: state.sendingChainLength,
    };

    // Encrypt message
    const nonce = nacl.randomBytes(24); // NaCl requires 24-byte nonce
    const ciphertext = nacl.secretbox(plaintextBytes, nonce, messageKey);

    // Combine nonce with ciphertext
    const combined = concatUint8Arrays([nonce, ciphertext]);

    state.sendingChainLength++;

    return {
      message: {
        header,
        ciphertext: combined,
        authTag: new Uint8Array(0), // NaCl secretbox includes auth tag in ciphertext
      },
      newState: state,
    };
  }

  /**
   * Decrypt a message
   */
  async decryptMessage(
    state: RatchetState,
    message: EncryptedMessage
  ): Promise<{ plaintext: Uint8Array; newState: RatchetState }> {
    console.log('[RatchetEngine] Starting decryption');
    console.log('[RatchetEngine] Remote ratchet key matches:', 
      state.dhRatchetRemoteKey ? this.compareKeys(state.dhRatchetRemoteKey, message.header.ratchetKey) : 'no current key'
    );
    
    // Check if we need to perform DH ratchet
    const needsRatchet =
      !state.dhRatchetRemoteKey ||
      !this.compareKeys(state.dhRatchetRemoteKey, message.header.ratchetKey);

    console.log('[RatchetEngine] Needs ratchet:', needsRatchet);
    
    if (needsRatchet) {
      console.log('[RatchetEngine] Performing DH ratchet');
      state = await this.performDHRatchet(state, message.header.ratchetKey);
      console.log('[RatchetEngine] DH ratchet complete');
    }

    // Skip message keys if needed
    console.log('[RatchetEngine] Current receiving chain length:', state.receivingChainLength, 'Message number:', message.header.messageNumber);
    state = await this.skipMessageKeys(state, message.header.messageNumber);
    console.log('[RatchetEngine] Skip complete, now at message number:', state.receivingChainLength);

    // Try to get message key from skipped keys first
    const skippedKey = this.getSkippedMessageKey(
      state,
      message.header.ratchetKey,
      message.header.messageNumber
    );

    let messageKey: Uint8Array;
    if (skippedKey) {
      console.log('[RatchetEngine] Using skipped message key');
      messageKey = skippedKey;
      this.deleteSkippedMessageKey(
        state,
        message.header.ratchetKey,
        message.header.messageNumber
      );
    } else {
      console.log('[RatchetEngine] Deriving message key from chain');
      // Derive message key from receiving chain
      messageKey = await this.kdfMessageKey(state.receivingChainKey!);

      // Advance chain key
      state.receivingChainKey = await this.kdfChainKey(state.receivingChainKey!);
      state.receivingChainLength++;
    }

    // Extract nonce and ciphertext
    console.log('[RatchetEngine] Ciphertext length:', message.ciphertext.length);
    const nonce = message.ciphertext.slice(0, 24);
    const ciphertext = message.ciphertext.slice(24);
    console.log('[RatchetEngine] Nonce:', nonce.length, 'bytes, Encrypted data:', ciphertext.length, 'bytes');

    // Decrypt
    console.log('[RatchetEngine] Calling nacl.secretbox.open');
    const plaintext = nacl.secretbox.open(ciphertext, nonce, messageKey);

    if (!plaintext) {
      console.log('[RatchetEngine] Decryption failed - authentication check failed');
      console.log('[RatchetEngine] Message key (first 8 bytes):', toBase64(messageKey.slice(0, 8)));
      console.log('[RatchetEngine] Nonce (first 8 bytes):', toBase64(nonce.slice(0, 8)));
      throw new Error('Failed to decrypt message - authentication failed');
    }

    console.log('[RatchetEngine] Decryption successful, plaintext length:', plaintext.length);
    return { plaintext, newState: state };
  }

  /**
   * Perform DH ratchet (generate new sending chain)
   */
  private async performDHRatchet(
    state: RatchetState,
    remoteRatchetKey: Uint8Array | null
  ): Promise<RatchetState> {
    // Save current sending chain length as previous
    state.previousSendingChainLength = state.sendingChainLength;

    // If receiving a new ratchet key, update receiving chain
    if (remoteRatchetKey) {
      // Perform DH with remote ratchet key
      const dhOutput = nacl.scalarMult(
        state.dhRatchetKeyPair!.secretKey,
        remoteRatchetKey
      );

      // Derive new root key and receiving chain key
      const kdfOutput = await this.kdfRootKey(state.rootKey, dhOutput);
      state.rootKey = kdfOutput.rootKey;
      state.receivingChainKey = kdfOutput.chainKey;
      state.receivingChainLength = 0;
      state.dhRatchetRemoteKey = remoteRatchetKey;
    }

    // Generate new DH ratchet key pair
    const newRatchetKeyPair = nacl.box.keyPair();

    // Perform DH with remote's ratchet key
    const dhOutput = nacl.scalarMult(
      newRatchetKeyPair.secretKey,
      state.dhRatchetRemoteKey!
    );

    // Derive new root key and sending chain key
    const kdfOutput = await this.kdfRootKey(state.rootKey, dhOutput);
    state.rootKey = kdfOutput.rootKey;
    state.sendingChainKey = kdfOutput.chainKey;
    state.sendingChainLength = 0;

    state.dhRatchetKeyPair = {
      publicKey: newRatchetKeyPair.publicKey,
      secretKey: newRatchetKeyPair.secretKey,
    };

    return state;
  }

  /**
   * Skip message keys for out-of-order messages
   */
  private async skipMessageKeys(
    state: RatchetState,
    until: number
  ): Promise<RatchetState> {
    if (state.receivingChainLength + this.MAX_SKIP < until) {
      throw new Error('Exceeded maximum skip limit');
    }

    if (state.receivingChainKey) {
      while (state.receivingChainLength < until) {
        const messageKey = await this.kdfMessageKey(state.receivingChainKey);
        const keyId = this.makeSkippedKeyId(
          state.dhRatchetRemoteKey!,
          state.receivingChainLength
        );
        state.skippedMessageKeys.set(keyId, messageKey);

        state.receivingChainKey = await this.kdfChainKey(state.receivingChainKey);
        state.receivingChainLength++;
      }
    }

    return state;
  }

  /**
   * KDF for root key (HKDF)
   */
  private async kdfRootKey(
    rootKey: Uint8Array,
    dhOutput: Uint8Array
  ): Promise<{ rootKey: Uint8Array; chainKey: Uint8Array }> {
    const output = await hkdf(dhOutput, {
      salt: rootKey,
      info: encodeUtf8('WhatsAppCloneRootKey'),
      length: 64, // 32 bytes for each key
    });

    return {
      rootKey: new Uint8Array(output.slice(0, 32)),
      chainKey: new Uint8Array(output.slice(32, 64)),
    };
  }

  /**
   * KDF for chain key (HMAC-based)
   */
  private async kdfChainKey(chainKey: Uint8Array): Promise<Uint8Array> {
    const input = new Uint8Array([0x01]);
    const key = await crypto.subtle.importKey(
      'raw',
      chainKey,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    const output = await crypto.subtle.sign('HMAC', key, input);
    return new Uint8Array(output);
  }

  /**
   * KDF for message key (HMAC-based)
   */
  private async kdfMessageKey(chainKey: Uint8Array): Promise<Uint8Array> {
    const input = new Uint8Array([0x02]);
    const key = await crypto.subtle.importKey(
      'raw',
      chainKey,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    const output = await crypto.subtle.sign('HMAC', key, input);
    const messageKey = new Uint8Array(output);
    return new Uint8Array(messageKey.slice(0, 32)); // 256 bits, explicitly wrap slice
  }

  /**
   * Helper: Create skipped message key ID
   */
  private makeSkippedKeyId(ratchetKey: Uint8Array, msgNum: number): string {
    return `${toBase64(ratchetKey)}:${msgNum}`;
  }

  /**
   * Helper: Get skipped message key
   */
  private getSkippedMessageKey(
    state: RatchetState,
    ratchetKey: Uint8Array,
    msgNum: number
  ): Uint8Array | undefined {
    const keyId = this.makeSkippedKeyId(ratchetKey, msgNum);
    return state.skippedMessageKeys.get(keyId);
  }

  /**
   * Helper: Delete skipped message key
   */
  private deleteSkippedMessageKey(
    state: RatchetState,
    ratchetKey: Uint8Array,
    msgNum: number
  ): void {
    const keyId = this.makeSkippedKeyId(ratchetKey, msgNum);
    state.skippedMessageKeys.delete(keyId);
  }

  /**
   * Helper: Compare two keys
   */
  private compareKeys(key1: Uint8Array, key2: Uint8Array): boolean {
    if (key1.length !== key2.length) return false;
    for (let i = 0; i < key1.length; i++) {
      if (key1[i] !== key2[i]) return false;
    }
    return true;
  }

  /**
   * Serialize encrypted message for transmission
   */
  serializeMessage(message: EncryptedMessage): SerializedEncryptedMessage {
    return {
      header: {
        ratchetKey: toBase64(message.header.ratchetKey),
        previousChainLength: message.header.previousChainLength,
        messageNumber: message.header.messageNumber,
      },
      ciphertext: toBase64(message.ciphertext),
      authTag: toBase64(message.authTag),
    };
  }

  /**
   * Deserialize encrypted message from transmission
   */
  deserializeMessage(serialized: SerializedEncryptedMessage): EncryptedMessage {
    return {
      header: {
        ratchetKey: fromBase64(serialized.header.ratchetKey),
        previousChainLength: serialized.header.previousChainLength,
        messageNumber: serialized.header.messageNumber,
      },
      ciphertext: fromBase64(serialized.ciphertext),
      authTag: fromBase64(serialized.authTag),
    };
  }

  /**
   * Serialize ratchet state for storage
   */
  serializeState(state: RatchetState): string {
    const serializable = {
      rootKey: toBase64(state.rootKey),
      sendingChainKey: state.sendingChainKey ? toBase64(state.sendingChainKey) : null,
      receivingChainKey: state.receivingChainKey
        ? toBase64(state.receivingChainKey)
        : null,
      dhRatchetKeyPair: state.dhRatchetKeyPair
        ? {
            publicKey: toBase64(state.dhRatchetKeyPair.publicKey),
            secretKey: toBase64(state.dhRatchetKeyPair.secretKey),
          }
        : null,
      dhRatchetRemoteKey: state.dhRatchetRemoteKey
        ? toBase64(state.dhRatchetRemoteKey)
        : null,
      sendingChainLength: state.sendingChainLength,
      receivingChainLength: state.receivingChainLength,
      previousSendingChainLength: state.previousSendingChainLength,
      skippedMessageKeys: Array.from(state.skippedMessageKeys.entries()).map(
        ([k, v]) => [k, toBase64(v)]
      ),
    };
    return JSON.stringify(serializable);
  }

  /**
   * Deserialize ratchet state from storage
   */
  deserializeState(serialized: string): RatchetState {
    const data = JSON.parse(serialized);
    return {
      rootKey: fromBase64(data.rootKey),
      sendingChainKey: data.sendingChainKey ? fromBase64(data.sendingChainKey) : null,
      receivingChainKey: data.receivingChainKey
        ? fromBase64(data.receivingChainKey)
        : null,
      dhRatchetKeyPair: data.dhRatchetKeyPair
        ? {
            publicKey: fromBase64(data.dhRatchetKeyPair.publicKey),
            secretKey: fromBase64(data.dhRatchetKeyPair.secretKey),
          }
        : null,
      dhRatchetRemoteKey: data.dhRatchetRemoteKey
        ? fromBase64(data.dhRatchetRemoteKey)
        : null,
      sendingChainLength: data.sendingChainLength,
      receivingChainLength: data.receivingChainLength,
      previousSendingChainLength: data.previousSendingChainLength,
      skippedMessageKeys: new Map(
        data.skippedMessageKeys.map(([k, v]: [string, string]) => [k, fromBase64(v)])
      ),
    };
  }
}
