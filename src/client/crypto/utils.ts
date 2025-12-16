const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

export function toBase64(data: Uint8Array): string {
  if (typeof window === 'undefined') {
    return Buffer.from(data).toString('base64');
  }
  let binary = '';
  data.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

export function fromBase64(value: string): Uint8Array {
  if (typeof window === 'undefined') {
    return new Uint8Array(Buffer.from(value, 'base64'));
  }
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.replace(/^0x/, '');
  const result = new Uint8Array(clean.length / 2);
  for (let i = 0; i < clean.length; i += 2) {
    result[i / 2] = parseInt(clean.substr(i, 2), 16);
  }
  return result;
}

export function encodeUtf8(value: string): Uint8Array {
  return textEncoder.encode(value);
}

export function decodeUtf8(data: Uint8Array): string {
  return textDecoder.decode(data);
}

export function concatUint8Arrays(chunks: Uint8Array[]): Uint8Array {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}

interface HKDFOptions {
  salt?: Uint8Array;
  info?: Uint8Array;
  length: number;
  hash?: 'SHA-256' | 'SHA-512';
}

export async function hkdf(ikm: Uint8Array, options: HKDFOptions): Promise<Uint8Array> {
  const salt = options.salt ?? new Uint8Array(32);
  const info = options.info ?? new Uint8Array(0);
  const hash = options.hash ?? 'SHA-256';
  const hkdfKey = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveBits']);
  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: 'HKDF',
      salt,
      info,
      hash,
    },
    hkdfKey,
    options.length * 8
  );
  return new Uint8Array(derivedBits);
}
