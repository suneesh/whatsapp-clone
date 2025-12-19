import nacl from 'tweetnacl';
import { RemotePrekeyBundle, X3DHResult } from './types';
import { concatUint8Arrays, encodeUtf8, fromBase64, hkdf, toBase64 } from './utils';

function deriveIdentityKeyPair(seed: Uint8Array) {
  return nacl.box.keyPair.fromSecretKey(seed);
}

export async function performX3DHInitiator(options: {
  localIdentitySeed: Uint8Array;
  remoteBundle: RemotePrekeyBundle;
}): Promise<X3DHResult> {
  const { localIdentitySeed, remoteBundle } = options;
  console.log('[X3DH] Initiator starting with bundle:', {
    identityKey: remoteBundle.identityKey?.substring(0, 20),
    signedPrekeyId: remoteBundle.signedPrekey?.keyId,
    oneTimePrekeyId: remoteBundle.oneTimePrekey?.keyId,
  });
  
  if (!remoteBundle.signedPrekey) {
    throw new Error('Recipient is missing signed prekey');
  }

  const identityKeyPair = deriveIdentityKeyPair(localIdentitySeed);
  const remoteIdentityKey = fromBase64(remoteBundle.identityKey);
  const remoteSigningKey = fromBase64(remoteBundle.signingKey);
  const remoteSignedPrekey = fromBase64(remoteBundle.signedPrekey.publicKey);
  const remoteSignature = fromBase64(remoteBundle.signedPrekey.signature);

  const signatureValid = nacl.sign.detached.verify(
    remoteSignedPrekey,
    remoteSignature,
    remoteSigningKey
  );
  if (!signatureValid) {
    throw new Error('Invalid signed prekey signature');
  }

  // Generate random ephemeral key pair (Signal protocol standard)
  const ephemeralKeyPair = nacl.box.keyPair();
  console.log('[X3DH] Generated random ephemeral key, public:', toBase64(ephemeralKeyPair.publicKey).substring(0, 20));

  const dh1 = nacl.scalarMult(identityKeyPair.secretKey, remoteSignedPrekey);
  const dh2 = nacl.scalarMult(ephemeralKeyPair.secretKey, remoteIdentityKey);
  const dh3 = nacl.scalarMult(ephemeralKeyPair.secretKey, remoteSignedPrekey);
  let usedOneTimePrekeyId: number | undefined;
  const dhChunks = [dh1, dh2, dh3];
  // DISABLED: One-time prekeys cause sync issues when sender and receiver
  // independently perform X3DH. Both must use the same DH output for shared secret.
  // TODO: Implement proper Signal protocol with shared X3DH initialization
  /*
  if (remoteBundle.oneTimePrekey) {
    const remoteOneTimePrekey = fromBase64(remoteBundle.oneTimePrekey.publicKey);
    const dh4 = nacl.scalarMult(ephemeralKeyPair.secretKey, remoteOneTimePrekey);
    dhChunks.push(dh4);
    usedOneTimePrekeyId = remoteBundle.oneTimePrekey.keyId;
    console.log('[X3DH] Using one-time prekey:', usedOneTimePrekeyId);
  }
  */

  const sharedSecret = await hkdf(concatUint8Arrays(dhChunks), {
    info: encodeUtf8('WHATSAPP-CLONE-X3DH'),
    length: 32,
  });
  
  console.log('[X3DH] Shared secret (dh1+dh2+dh3 only, no OTP):', toBase64(sharedSecret).substring(0, 20));

  return {
    sharedSecret,
    localEphemeralKeyPair: {
      publicKey: ephemeralKeyPair.publicKey,
      secretKey: ephemeralKeyPair.secretKey,
    },
    remoteIdentityKey,
    remoteSignedPrekey,
    remoteSignedPrekeyId: remoteBundle.signedPrekey.keyId,
    usedOneTimePrekeyId,
  };
}

/**
 * X3DH responder - uses the initiator's ephemeral key to derive the same shared secret
 * This is called by the receiver when processing the first message from a sender
 */
export async function performX3DHResponder(options: {
  localIdentitySeed: Uint8Array;
  localSignedPrekeyPair: { publicKey: Uint8Array; secretKey: Uint8Array };
  localOneTimePrekeyPair?: { publicKey: Uint8Array; secretKey: Uint8Array };
  remoteIdentityKey: Uint8Array;
  remoteEphemeralKey: Uint8Array;  // From first message
}): Promise<Uint8Array> {
  const { 
    localIdentitySeed, 
    localSignedPrekeyPair, 
    localOneTimePrekeyPair,
    remoteIdentityKey,
    remoteEphemeralKey,
  } = options;

  console.log('[X3DH] Responder starting with ephemeral key from sender:', toBase64(remoteEphemeralKey).substring(0, 20));

  const identityKeyPair = deriveIdentityKeyPair(localIdentitySeed);

  // DH calculations - note the reversed order compared to initiator
  // DH1: my signed prekey secret × remote identity public
  const dh1 = nacl.scalarMult(localSignedPrekeyPair.secretKey, remoteIdentityKey);
  
  // DH2: my identity secret × remote ephemeral public
  const dh2 = nacl.scalarMult(identityKeyPair.secretKey, remoteEphemeralKey);
  
  // DH3: my signed prekey secret × remote ephemeral public
  const dh3 = nacl.scalarMult(localSignedPrekeyPair.secretKey, remoteEphemeralKey);

  const dhChunks = [dh1, dh2, dh3];
  
  // DH4: one-time prekey if available
  if (localOneTimePrekeyPair) {
    const dh4 = nacl.scalarMult(localOneTimePrekeyPair.secretKey, remoteEphemeralKey);
    dhChunks.push(dh4);
    console.log('[X3DH] Responder used one-time prekey');
  }

  const sharedSecret = await hkdf(concatUint8Arrays(dhChunks), {
    info: encodeUtf8('WHATSAPP-CLONE-X3DH'),
    length: 32,
  });

  console.log('[X3DH] Responder shared secret:', toBase64(sharedSecret).substring(0, 20));

  return sharedSecret;
}

