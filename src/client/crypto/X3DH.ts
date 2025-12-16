import nacl from 'tweetnacl';
import { RemotePrekeyBundle, X3DHResult } from './types';
import { concatUint8Arrays, encodeUtf8, fromBase64, hkdf } from './utils';

function deriveIdentityKeyPair(seed: Uint8Array) {
  return nacl.box.keyPair.fromSecretKey(seed);
}

export async function performX3DHInitiator(options: {
  localIdentitySeed: Uint8Array;
  remoteBundle: RemotePrekeyBundle;
}): Promise<X3DHResult> {
  const { localIdentitySeed, remoteBundle } = options;
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

  const ephemeralKeyPair = nacl.box.keyPair();

  const dh1 = nacl.scalarMult(identityKeyPair.secretKey, remoteSignedPrekey);
  const dh2 = nacl.scalarMult(ephemeralKeyPair.secretKey, remoteIdentityKey);
  const dh3 = nacl.scalarMult(ephemeralKeyPair.secretKey, remoteSignedPrekey);

  let usedOneTimePrekeyId: number | undefined;
  const dhChunks = [dh1, dh2, dh3];
  if (remoteBundle.oneTimePrekey) {
    const remoteOneTimePrekey = fromBase64(remoteBundle.oneTimePrekey.publicKey);
    const dh4 = nacl.scalarMult(ephemeralKeyPair.secretKey, remoteOneTimePrekey);
    dhChunks.push(dh4);
    usedOneTimePrekeyId = remoteBundle.oneTimePrekey.keyId;
  }

  const sharedSecret = await hkdf(concatUint8Arrays(dhChunks), {
    info: encodeUtf8('WHATSAPP-CLONE-X3DH'),
    length: 32,
  });

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
