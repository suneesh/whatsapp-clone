"""Cryptographic key management."""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple
import nacl.public
import nacl.signing
import nacl.encoding
import nacl.utils

from .utils import format_fingerprint, encode_base64, decode_base64
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class KeyPair:
    """Represents a cryptographic key pair."""
    
    def __init__(self, public_key: bytes, private_key: bytes):
        """
        Initialize key pair.
        
        Args:
            public_key: Public key bytes
            private_key: Private key bytes (seed)
        """
        self.public_key = public_key
        self.private_key = private_key


class PrekeyBundle:
    """Prekey bundle for X3DH protocol."""
    
    def __init__(
        self,
        identity_key: str,
        signing_key: str,
        fingerprint: str,
        signed_prekey: Optional[Dict[str, Any]] = None,
        one_time_prekeys: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize prekey bundle.
        
        Args:
            identity_key: Base64 encoded identity public key
            signing_key: Base64 encoded signing public key
            fingerprint: Key fingerprint
            signed_prekey: Signed prekey data
            one_time_prekeys: List of one-time prekeys
        """
        self.identity_key = identity_key
        self.signing_key = signing_key
        self.fingerprint = fingerprint
        self.signed_prekey = signed_prekey
        self.one_time_prekeys = one_time_prekeys or []


class KeyManager:
    """
    Manages cryptographic keys for E2EE.
    
    Handles generation, storage, and rotation of:
    - Identity key pair (Curve25519)
    - Signing key pair (Ed25519)
    - Prekeys (signed + one-time)
    """
    
    def __init__(self, user_id: str, storage_path: str = "~/.whatsapp_client"):
        """
        Initialize KeyManager.
        
        Args:
            user_id: User ID for key storage
            storage_path: Base path for key storage
        """
        self.user_id = user_id
        self.storage_path = os.path.expanduser(storage_path)
        
        # Keys (loaded on demand)
        self._identity_keypair: Optional[KeyPair] = None
        self._signing_keypair: Optional[KeyPair] = None
        self._signed_prekey: Optional[Dict[str, Any]] = None
        self._one_time_prekeys: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized KeyManager for user {user_id}")
    
    async def initialize(self) -> None:
        """
        Initialize cryptographic keys.
        
        Generates keys if they don't exist, otherwise loads from storage.
        """
        logger.info("Initializing cryptographic keys...")
        
        # For now, always generate new keys (storage implementation in US13)
        await self._generate_identity_keys()
        await self._generate_prekeys()
        
        logger.info("Cryptographic keys initialized")
    
    async def _generate_identity_keys(self) -> None:
        """Generate identity and signing key pairs."""
        logger.info("Generating identity key pair (Curve25519)...")
        
        # Generate Curve25519 identity key pair
        private_key = nacl.public.PrivateKey.generate()
        self._identity_keypair = KeyPair(
            public_key=bytes(private_key.public_key),
            private_key=bytes(private_key)
        )
        
        logger.info("Generating signing key pair (Ed25519)...")
        
        # Generate Ed25519 signing key pair
        signing_key = nacl.signing.SigningKey.generate()
        self._signing_keypair = KeyPair(
            public_key=bytes(signing_key.verify_key),
            private_key=bytes(signing_key)
        )
        
        logger.info("Identity and signing keys generated successfully")
    
    async def _generate_prekeys(self, count: int = 100) -> None:
        """
        Generate prekey bundle (1 signed prekey + N one-time prekeys).
        
        Args:
            count: Number of one-time prekeys to generate (default: 100)
        """
        if not self._signing_keypair:
            raise ValidationError("Signing key not initialized")
        
        logger.info(f"Generating prekey bundle (1 signed + {count} one-time)...")
        
        # Generate signed prekey
        signed_prekey_private = nacl.public.PrivateKey.generate()
        signed_prekey_public = bytes(signed_prekey_private.public_key)
        
        # Sign the prekey with signing key
        signing_key = nacl.signing.SigningKey(self._signing_keypair.private_key)
        signature = signing_key.sign(signed_prekey_public).signature
        
        self._signed_prekey = {
            "keyId": 1,
            "publicKey": encode_base64(signed_prekey_public),
            "signature": encode_base64(signature),
            "privateKey": bytes(signed_prekey_private),  # Store for local use
        }
        
        # Generate one-time prekeys
        self._one_time_prekeys = []
        for i in range(count):
            prekey_private = nacl.public.PrivateKey.generate()
            prekey_public = bytes(prekey_private.public_key)
            
            self._one_time_prekeys.append({
                "keyId": i + 1,
                "publicKey": encode_base64(prekey_public),
                "privateKey": bytes(prekey_private),  # Store for local use
            })
        
        logger.info(f"Generated {count} one-time prekeys and 1 signed prekey")
    
    def get_fingerprint(self) -> str:
        """
        Get fingerprint of identity public key.
        
        Returns:
            60-character hexadecimal fingerprint
        """
        if not self._identity_keypair:
            raise ValidationError("Identity key not initialized")
        
        return format_fingerprint(self._identity_keypair.public_key)
    
    def get_public_bundle(self) -> PrekeyBundle:
        """
        Get public prekey bundle for upload to server.
        
        Returns:
            PrekeyBundle with public keys only
        """
        if not self._identity_keypair or not self._signing_keypair:
            raise ValidationError("Keys not initialized")
        
        # Prepare signed prekey (without private key)
        signed_prekey = None
        if self._signed_prekey:
            signed_prekey = {
                "keyId": self._signed_prekey["keyId"],
                "publicKey": self._signed_prekey["publicKey"],
                "signature": self._signed_prekey["signature"],
            }
        
        # Prepare one-time prekeys (without private keys)
        one_time_prekeys = [
            {
                "keyId": prekey["keyId"],
                "publicKey": prekey["publicKey"],
            }
            for prekey in self._one_time_prekeys
        ]
        
        return PrekeyBundle(
            identity_key=encode_base64(self._identity_keypair.public_key),
            signing_key=encode_base64(self._signing_keypair.public_key),
            fingerprint=self.get_fingerprint(),
            signed_prekey=signed_prekey,
            one_time_prekeys=one_time_prekeys,
        )
    
    def get_identity_keypair(self) -> KeyPair:
        """
        Get identity key pair.
        
        Returns:
            Identity KeyPair
        """
        if not self._identity_keypair:
            raise ValidationError("Identity key not initialized")
        return self._identity_keypair
    
    def get_signing_keypair(self) -> KeyPair:
        """
        Get signing key pair.
        
        Returns:
            Signing KeyPair
        """
        if not self._signing_keypair:
            raise ValidationError("Signing key not initialized")
        return self._signing_keypair
    
    async def rotate_prekeys(self, count: int = 100) -> None:
        """
        Rotate one-time prekeys when running low.
        
        Args:
            count: Number of new prekeys to generate
        """
        logger.info(f"Rotating prekeys, generating {count} new one-time prekeys")
        await self._generate_prekeys(count)
    
    def get_available_prekey_count(self) -> int:
        """
        Get count of available (unused) one-time prekeys.
        
        Returns:
            Number of available prekeys
        """
        return len(self._one_time_prekeys)
    
    def consume_prekey(self, key_id: int) -> None:
        """
        Mark a prekey as consumed/used.
        
        Args:
            key_id: ID of the prekey to consume
        """
        # Remove the consumed prekey
        self._one_time_prekeys = [
            pk for pk in self._one_time_prekeys if pk["keyId"] != key_id
        ]
        logger.debug(f"Consumed prekey {key_id}, {len(self._one_time_prekeys)} remaining")
