"""X3DH (Extended Triple Diffie-Hellman) Protocol Implementation."""

import hashlib
import secrets
from typing import Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import RawEncoder

from ..models import PrekeyBundle
from ..exceptions import WhatsAppClientError


class X3DHProtocol:
    """
    Implements the X3DH key agreement protocol for secure session establishment.
    
    X3DH performs four Diffie-Hellman operations to establish a shared secret:
    - DH1: DH(IKa, SPKb) - Identity key A with signed prekey B
    - DH2: DH(EKa, IKb) - Ephemeral key A with identity key B
    - DH3: DH(EKa, SPKb) - Ephemeral key A with signed prekey B
    - DH4: DH(EKa, OPKb) - Ephemeral key A with one-time prekey B (if available)
    
    The shared secret is derived using HKDF-SHA256.
    """

    @staticmethod
    def initiate_session(
        identity_private_key: PrivateKey,
        prekey_bundle: PrekeyBundle,
    ) -> Tuple[bytes, PrivateKey, bytes]:
        """
        Initiate X3DH session as the initiator (Alice).
        
        Args:
            identity_private_key: Alice's identity private key
            prekey_bundle: Bob's public key bundle
            
        Returns:
            Tuple of (shared_secret, ephemeral_private_key, initial_message_key)
            
        Raises:
            WhatsAppClientError: If key agreement fails
        """
        try:
            # Parse Bob's public keys
            identity_key_bob = PublicKey(
                bytes.fromhex(prekey_bundle.identity_key),
                encoder=RawEncoder
            )
            signed_prekey_bob = PublicKey(
                bytes.fromhex(prekey_bundle.signed_prekey),
                encoder=RawEncoder
            )
            
            # Generate ephemeral key for this session
            ephemeral_key_alice = PrivateKey.generate()
            
            # Perform DH operations
            # DH1: DH(IKa, SPKb)
            dh1 = X3DHProtocol._dh(identity_private_key, signed_prekey_bob)
            
            # DH2: DH(EKa, IKb)
            dh2 = X3DHProtocol._dh(ephemeral_key_alice, identity_key_bob)
            
            # DH3: DH(EKa, SPKb)
            dh3 = X3DHProtocol._dh(ephemeral_key_alice, signed_prekey_bob)
            
            # DH4: DH(EKa, OPKb) - if one-time prekey available
            dh_results = [dh1, dh2, dh3]
            one_time_prekey_id = None
            
            if prekey_bundle.one_time_prekeys and len(prekey_bundle.one_time_prekeys) > 0:
                # Use first available one-time prekey
                one_time_prekey_hex = prekey_bundle.one_time_prekeys[0]
                one_time_prekey_bob = PublicKey(
                    bytes.fromhex(one_time_prekey_hex),
                    encoder=RawEncoder
                )
                dh4 = X3DHProtocol._dh(ephemeral_key_alice, one_time_prekey_bob)
                dh_results.append(dh4)
                one_time_prekey_id = one_time_prekey_hex
            
            # Concatenate all DH outputs
            dh_concatenated = b"".join(dh_results)
            
            # Derive shared secret using HKDF
            shared_secret = X3DHProtocol._derive_key(
                input_key_material=dh_concatenated,
                salt=b"WhatsAppCloneX3DH",
                info=b"SharedSecret",
                length=32
            )
            
            # Derive initial root key and chain key for Double Ratchet
            initial_message_key = X3DHProtocol._derive_key(
                input_key_material=shared_secret,
                salt=b"WhatsAppCloneX3DH",
                info=b"InitialMessageKey",
                length=32
            )
            
            return shared_secret, ephemeral_key_alice, initial_message_key
            
        except Exception as e:
            raise WhatsAppClientError(f"X3DH session initiation failed: {e}")

    @staticmethod
    def respond_session(
        identity_private_key: PrivateKey,
        signed_prekey_private: PrivateKey,
        one_time_prekey_private: PrivateKey | None,
        remote_identity_key: bytes,
        remote_ephemeral_key: bytes,
    ) -> bytes:
        """
        Respond to X3DH session as the responder (Bob).
        
        This is called when receiving a first message with X3DH data.
        
        Args:
            identity_private_key: Bob's identity private key
            signed_prekey_private: Bob's signed prekey private key that was used
            one_time_prekey_private: Bob's one-time prekey private key if used (or None)
            remote_identity_key: Alice's identity public key (from X3DH data)
            remote_ephemeral_key: Alice's ephemeral public key (from X3DH data)
            
        Returns:
            32-byte shared secret
            
        Raises:
            WhatsAppClientError: If key agreement fails
        """
        try:
            # Parse remote public keys
            identity_key_alice = PublicKey(remote_identity_key, encoder=RawEncoder)
            ephemeral_key_alice = PublicKey(remote_ephemeral_key, encoder=RawEncoder)
            
            # Perform DH operations (note: reversed order from initiator)
            # DH1: DH(SPKb, IKa) - signed prekey B with identity key A
            dh1 = X3DHProtocol._dh(signed_prekey_private, identity_key_alice)
            
            # DH2: DH(IKb, EKa) - identity key B with ephemeral key A
            dh2 = X3DHProtocol._dh(identity_private_key, ephemeral_key_alice)
            
            # DH3: DH(SPKb, EKa) - signed prekey B with ephemeral key A
            dh3 = X3DHProtocol._dh(signed_prekey_private, ephemeral_key_alice)
            
            dh_results = [dh1, dh2, dh3]
            
            # DH4: DH(OPKb, EKa) - if one-time prekey was used
            if one_time_prekey_private:
                dh4 = X3DHProtocol._dh(one_time_prekey_private, ephemeral_key_alice)
                dh_results.append(dh4)
            
            # Concatenate all DH outputs
            dh_concatenated = b"".join(dh_results)
            
            # Derive shared secret using HKDF (same as initiator)
            shared_secret = X3DHProtocol._derive_key(
                input_key_material=dh_concatenated,
                salt=b"WhatsAppCloneX3DH",
                info=b"SharedSecret",
                length=32
            )
            
            return shared_secret
            
        except Exception as e:
            raise WhatsAppClientError(f"X3DH session response failed: {e}")
    
    @staticmethod
    def _dh(private_key: PrivateKey, public_key: PublicKey) -> bytes:
        """
        Perform Diffie-Hellman key exchange.
        
        Args:
            private_key: Private key for DH
            public_key: Public key for DH
            
        Returns:
            32-byte shared secret
        """
        # Use PyNaCl's crypto_scalarmult for X25519 DH
        from nacl.bindings import crypto_scalarmult
        
        # Extract raw bytes
        private_bytes = bytes(private_key)
        public_bytes = bytes(public_key)
        
        # Perform X25519 scalar multiplication
        return crypto_scalarmult(private_bytes, public_bytes)
    
    @staticmethod
    def _derive_key(
        input_key_material: bytes,
        salt: bytes,
        info: bytes,
        length: int = 32
    ) -> bytes:
        """
        Derive key using HKDF-SHA256.
        
        Args:
            input_key_material: Input key material
            salt: Salt value
            info: Context information
            length: Output key length (default: 32 bytes)
            
        Returns:
            Derived key
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            info=info,
        )
        return hkdf.derive(input_key_material)
    
    @staticmethod
    def verify_prekey_signature(
        signed_prekey: str,
        signature: str,
        signing_key: str
    ) -> bool:
        """
        Verify the signature of a signed prekey.
        
        Args:
            signed_prekey: Hex-encoded signed prekey
            signature: Hex-encoded signature
            signing_key: Hex-encoded signing public key
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            from nacl.signing import VerifyKey
            from nacl.encoding import RawEncoder
            
            verify_key = VerifyKey(bytes.fromhex(signing_key), encoder=RawEncoder)
            signed_prekey_bytes = bytes.fromhex(signed_prekey)
            signature_bytes = bytes.fromhex(signature)
            
            # Verify signature
            verify_key.verify(signed_prekey_bytes, signature_bytes)
            return True
            
        except Exception:
            return False
