export interface IdentityKeyMaterial {
  seed: Uint8Array;
  signingPublicKey: Uint8Array;
  signingSecretKey: Uint8Array;
  x25519PublicKey: Uint8Array;
  x25519SecretKey: Uint8Array;
  fingerprint: string;
}

export interface SignedPrekeyMaterial {
  keyId: number;
  publicKey: Uint8Array;
  secretKey: Uint8Array;
  signature: Uint8Array;
  createdAt: number;
}

export interface OneTimePrekeyMaterial {
  keyId: number;
  publicKey: Uint8Array;
  secretKey: Uint8Array;
  createdAt: number;
  uploaded: boolean;
}

export interface PrekeyBundlePayload {
  identityKey: string;
  signingKey: string;
  fingerprint: string;
  signedPrekey: {
    keyId: number;
    publicKey: string;
    signature: string;
  } | null;
  oneTimePrekeys: Array<{
    keyId: number;
    publicKey: string;
  }>;
}

export interface RemotePrekeyBundle {
  identityKey: string;
  signingKey: string;
  fingerprint: string;
  signedPrekey: {
    keyId: number;
    publicKey: string;
    signature: string;
    createdAt?: number;
  } | null;
  oneTimePrekey: {
    keyId: number;
    publicKey: string;
  } | null;
}

export interface X3DHResult {
  sharedSecret: Uint8Array;
  localEphemeralKeyPair: {
    publicKey: Uint8Array;
    secretKey: Uint8Array;
  };
  remoteIdentityKey: Uint8Array;
  remoteSignedPrekey: Uint8Array;
  remoteSignedPrekeyId: number;
  usedOneTimePrekeyId?: number;
}

export interface EncryptedSecret {
  ciphertext: string;
  iv: string;
}
