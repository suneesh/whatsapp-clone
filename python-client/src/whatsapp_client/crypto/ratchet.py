"""Double Ratchet algorithm implementation for E2EE messaging."""

import hashlib
import json
from typing import Optional, Tuple, Dict
from dataclasses import dataclass, field

from nacl.public import PrivateKey, PublicKey
from nacl.secret import SecretBox
from nacl.encoding import RawEncoder, Base64Encoder
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ..exceptions import WhatsAppClientError


@dataclass
class RatchetHeader:
    """Header attached to encrypted messages."""
    
    dh_public_key: str  # Base64-encoded public DH key (for Signal protocol compatibility)
    prev_chain_length: int  # Number of messages in previous sending chain
    message_number: int  # Message number in current chain
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization (Signal protocol format)."""
        return {
            "ratchetKey": self.dh_public_key,
            "previousChainLength": self.prev_chain_length,
            "messageNumber": self.message_number,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RatchetHeader":
        """Create from dictionary (supports both formats)."""
        # Signal protocol format
        if "ratchetKey" in data:
            return cls(
                dh_public_key=data["ratchetKey"],
                prev_chain_length=data.get("previousChainLength", 0),
                message_number=data.get("messageNumber", 0),
            )
        # Legacy format
        return cls(
            dh_public_key=data.get("dh", ""),
            prev_chain_length=data.get("pn", 0),
            message_number=data.get("n", 0),
        )


@dataclass
class RatchetState:
    """State of the Double Ratchet."""
    
    # DH ratchet state
    dh_self: Optional[PrivateKey] = None  # Our current DH key pair
    dh_remote: Optional[PublicKey] = None  # Remote's current DH public key
    
    # Symmetric ratchet state
    root_key: bytes = b""  # Root key (KDF input)
    sending_chain_key: Optional[bytes] = None  # Chain key for sending
    receiving_chain_key: Optional[bytes] = None  # Chain key for receiving
    
    # Message counters
    sending_message_number: int = 0  # Messages sent in current chain
    receiving_message_number: int = 0  # Messages received in current chain
    prev_sending_chain_length: int = 0  # Length of previous sending chain
    
    # Skipped message keys (for out-of-order messages)
    skipped_keys: Dict[Tuple[str, int], bytes] = field(default_factory=dict)
    
    # Maximum skipped message keys to prevent DoS
    max_skip: int = 1000


class RatchetEngine:
    """
    Double Ratchet algorithm implementation.
    
    Provides forward secrecy and break-in recovery for E2EE messaging.
    Uses a combination of DH ratchet and symmetric-key ratchet.
    """
    
    def __init__(self, state: Optional[RatchetState] = None):
        """
        Initialize ratchet engine.
        
        Args:
            state: Existing ratchet state, or None for new ratchet
        """
        self.state = state or RatchetState()
    
    def initialize_sender(
        self,
        shared_secret: bytes,
        remote_dh_public: PublicKey,
    ) -> None:
        """
        Initialize as message sender (after X3DH).
        
        Args:
            shared_secret: Shared secret from X3DH
            remote_dh_public: Remote party's DH public key
        """
        # Generate our DH key pair
        self.state.dh_self = PrivateKey.generate()
        self.state.dh_remote = remote_dh_public
        
        # Initialize root key from shared secret
        self.state.root_key = shared_secret
        
        # Perform initial DH ratchet step
        self._dh_ratchet()
    
    def initialize_receiver(
        self,
        shared_secret: bytes,
        dh_self: PrivateKey,
    ) -> None:
        """
        Initialize as message receiver (after X3DH).
        
        Args:
            shared_secret: Shared secret from X3DH
            dh_self: Our DH private key
        """
        self.state.dh_self = dh_self
        self.state.root_key = shared_secret
        # Remote DH key will be set when first message arrives

    def initialize_responder(
        self,
        shared_secret: bytes,
        remote_ratchet_key: bytes,
    ) -> None:
        """
        Initialize as responder to a first message (after X3DH respond).
        
        This is called when processing a first message from someone else.
        We receive their initial ratchet key from the message header.
        
        Must match JavaScript's initializeRatchet(sharedSecret, remoteRatchetKey).
        
        Args:
            shared_secret: Shared secret from X3DH respond
            remote_ratchet_key: Sender's ratchet public key from message header
        """
        import base64
        
        # Match JavaScript: first derive root key and initial chain key from shared secret
        # JS: kdfRootKey(sharedSecret, new Uint8Array(32))
        # In kdfRootKey: hkdf(dhOutput, { salt: rootKey, ... })
        # Parameters: kdfRootKey(rootKey, dhOutput) → hkdf(dhOutput, { salt: rootKey, ... })
        # So: hkdf(zeros, { salt: sharedSecret, ... })
        initial_root_key, initial_chain_key = self._kdf_rk(shared_secret, bytes(32))
        
        # Set up state like JavaScript does
        self.state.root_key = initial_root_key
        self.state.receiving_chain_key = initial_chain_key
        self.state.receiving_message_number = 0
        
        # Parse remote's ratchet key
        self.state.dh_remote = PublicKey(remote_ratchet_key, encoder=RawEncoder)
        
        # Generate our own DH key pair (needed for future sends)
        self.state.dh_self = PrivateKey.generate()
        
        # Note: JavaScript does NOT perform DH ratchet immediately!
        # The DH ratchet happens during decryption when needsRatchet is true
    
    def encrypt(self, plaintext: str) -> Tuple[str, RatchetHeader]:
        """
        Encrypt a message using Double Ratchet.
        
        Args:
            plaintext: Message to encrypt
            
        Returns:
            Tuple of (ciphertext_base64, header)

        Raises:
            WhatsAppClientError: If encryption fails
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # If no sending chain, perform DH ratchet (responder case)
        if not self.state.sending_chain_key:
            logger.info(f"No sending chain key, performing DH ratchet...")
            self._dh_ratchet()

        # Derive message key from sending chain key
        message_key = self._derive_message_key(self.state.sending_chain_key)
        
        logger.debug(f"Encrypting message (plaintext: '{plaintext[:30]}...')")
        logger.debug(f"  sending_message_number: {self.state.sending_message_number}")

        # Create header with base64-encoded ratchet key (to match JS implementation)
        import base64
        # Encode ratchet key and ensure it's a clean base64 string (strip any whitespace)
        ratchet_key_b64 = base64.b64encode(bytes(self.state.dh_self.public_key)).decode('ascii').strip()
        header = RatchetHeader(
            dh_public_key=ratchet_key_b64,
            prev_chain_length=self.state.prev_sending_chain_length,
            message_number=self.state.sending_message_number,
        )
        
        # Encrypt message with NaCl SecretBox (XSalsa20-Poly1305)
        box = SecretBox(message_key)
        ciphertext_bytes = box.encrypt(plaintext.encode('utf-8'))
        
        # Encode to base64 for transmission
        import base64
        ciphertext_b64 = base64.b64encode(ciphertext_bytes).decode('ascii')
        
        logger.debug(f"  encrypted ciphertext (base64): {ciphertext_b64[:30]}...")
        logger.debug(f"  header: {header.to_dict()}")
        
        # Advance sending chain
        self.state.sending_chain_key = self._advance_chain_key(self.state.sending_chain_key)
        self.state.sending_message_number += 1
        
        return ciphertext_b64, header
    
    def decrypt(
        self,
        ciphertext_b64: str,
        header: RatchetHeader,
        auth_tag: bytes = None,
    ) -> str:
        """
        Decrypt a message using Double Ratchet.
        
        Args:
            ciphertext_b64: Base64-encoded ciphertext (or bytes)
            header: Message header with ratchet info
            auth_tag: Optional auth tag for Signal protocol format
            
        Returns:
            Decrypted plaintext
            
        Raises:
            WhatsAppClientError: If decryption fails
        """
        import base64
        
        # Decode ratchet key - could be base64 or hex
        remote_dh_key = header.dh_public_key
        remote_dh_bytes = None
        
        # Try base64 first (Signal protocol format from server)
        try:
            decoded = base64.b64decode(remote_dh_key)
            if len(decoded) == 32:  # Valid 32-byte key
                remote_dh_bytes = decoded
        except Exception:
            pass
        
        # Try hex if base64 didn't work (legacy/test format)
        if remote_dh_bytes is None:
            try:
                remote_dh_bytes = bytes.fromhex(remote_dh_key)
            except Exception as e:
                raise WhatsAppClientError(f"Invalid ratchet key format: {e}")
        
        # Check if we need to perform DH ratchet
        current_remote_dh_bytes = bytes(self.state.dh_remote) if self.state.dh_remote else None
        
        if remote_dh_bytes != current_remote_dh_bytes:
            # New DH key from sender - perform DH ratchet
            self._skip_message_keys(header.prev_chain_length)
            self._dh_ratchet_receive(PublicKey(remote_dh_bytes, encoder=RawEncoder))
        
        # Skip any message keys if we missed messages
        self._skip_message_keys(header.message_number)
        
        # Derive message key
        if not self.state.receiving_chain_key:
            raise WhatsAppClientError("Receiving chain not initialized")
        
        message_key = self._derive_message_key(self.state.receiving_chain_key)
        
        # Advance receiving chain
        self.state.receiving_chain_key = self._advance_chain_key(self.state.receiving_chain_key)
        self.state.receiving_message_number += 1
        
        # Decrypt message
        try:
            # Decode ciphertext from base64
            if isinstance(ciphertext_b64, bytes):
                ciphertext_bytes = ciphertext_b64
            else:
                ciphertext_bytes = base64.b64decode(ciphertext_b64)
            
            # JavaScript format: nonce (24 bytes) + ciphertext + MAC (16 bytes)
            # PyNaCl SecretBox.decrypt expects the same format
            box = SecretBox(message_key)
            plaintext_bytes = box.decrypt(ciphertext_bytes)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise WhatsAppClientError(f"Decryption failed: {e}")
    
    def try_skipped_message_keys(
        self,
        ciphertext_b64: str,
        header: RatchetHeader,
    ) -> Optional[str]:
        """
        Try to decrypt using skipped message keys.
        
        Args:
            ciphertext_b64: Base64-encoded ciphertext
            header: Message header
            
        Returns:
            Decrypted plaintext if key found, None otherwise
        """
        key_id = (header.dh_public_key, header.message_number)
        
        if key_id in self.state.skipped_keys:
            message_key = self.state.skipped_keys[key_id]
            del self.state.skipped_keys[key_id]
            
            try:
                box = SecretBox(message_key)
                # Decode base64 first
                import base64
                ciphertext_bytes = base64.b64decode(ciphertext_b64.encode('ascii'))
                plaintext_bytes = box.decrypt(ciphertext_bytes)
                return plaintext_bytes.decode('utf-8')
            except Exception:
                return None
        
        return None
    
    def _dh_ratchet(self) -> None:
        """Perform DH ratchet step (sender initiates)."""
        if not self.state.dh_self or not self.state.dh_remote:
            raise WhatsAppClientError("DH keys not initialized")
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Performing DH ratchet...")
        logger.debug(f"  dh_self: {bytes(self.state.dh_self).hex()[:16]}...")
        logger.debug(f"  dh_remote: {bytes(self.state.dh_remote).hex()[:16]}...")
        logger.debug(f"  current root_key: {self.state.root_key.hex()[:16]}...")
        
        # Perform DH
        from nacl.bindings import crypto_scalarmult
        dh_output = crypto_scalarmult(
            bytes(self.state.dh_self),
            bytes(self.state.dh_remote)
        )
        
        logger.debug(f"  dh_output: {dh_output.hex()[:16]}...")
        
        # Derive new root key and sending chain key
        self.state.root_key, self.state.sending_chain_key = self._kdf_rk(
            self.state.root_key,
            dh_output
        )
        
        logger.debug(f"  new root_key: {self.state.root_key.hex()[:16]}...")
        logger.debug(f"  new sending_chain_key: {self.state.sending_chain_key.hex()[:16]}...")
        
        # Reset sending message number
        self.state.prev_sending_chain_length = self.state.sending_message_number
        self.state.sending_message_number = 0
    
    def _dh_ratchet_receive(self, remote_dh_public: PublicKey) -> None:
        """
        Perform DH ratchet step when receiving new key.
        
        Args:
            remote_dh_public: New DH public key from remote party
        """
        # Update remote DH key
        self.state.dh_remote = remote_dh_public
        
        # Derive receiving chain key
        from nacl.bindings import crypto_scalarmult
        dh_output = crypto_scalarmult(
            bytes(self.state.dh_self),
            bytes(self.state.dh_remote)
        )
        
        self.state.root_key, self.state.receiving_chain_key = self._kdf_rk(
            self.state.root_key,
            dh_output
        )
        
        # Reset receiving message number
        self.state.receiving_message_number = 0
        
        # Generate new DH key pair for next sending
        self.state.dh_self = PrivateKey.generate()
        
        # Perform DH ratchet to get new sending chain
        self._dh_ratchet()
    
    def _skip_message_keys(self, until: int) -> None:
        """
        Skip message keys for missed messages.
        
        Args:
            until: Message number to skip until
        """
        if not self.state.receiving_chain_key:
            return
        
        while self.state.receiving_message_number < until:
            # Check DoS limit
            if len(self.state.skipped_keys) >= self.state.max_skip:
                raise WhatsAppClientError("Too many skipped message keys")
            
            # Derive and store message key
            message_key = self._derive_message_key(self.state.receiving_chain_key)
            
            key_id = (
                bytes(self.state.dh_remote).hex() if self.state.dh_remote else "",
                self.state.receiving_message_number
            )
            self.state.skipped_keys[key_id] = message_key
            
            # Advance chain
            self.state.receiving_chain_key = self._advance_chain_key(self.state.receiving_chain_key)
            self.state.receiving_message_number += 1
    
    @staticmethod
    def _kdf_rk(root_key: bytes, dh_output: bytes) -> Tuple[bytes, bytes]:
        """
        KDF for root key and chain key derivation.
        
        Args:
            root_key: Current root key
            dh_output: DH output
            
        Returns:
            Tuple of (new_root_key, chain_key)
        """
        # Use HKDF to derive 64 bytes, split into root key and chain key
        # Must match JavaScript: hkdf(dhOutput, { salt: rootKey, info: 'WhatsAppCloneRootKey', length: 64 })
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,
            salt=root_key,
            info=b"WhatsAppCloneRootKey",
        )
        output = hkdf.derive(dh_output)
        
        return output[:32], output[32:]
    
    @staticmethod
    def _derive_message_key(chain_key: bytes) -> bytes:
        """
        Derive message key from chain key.
        
        Args:
            chain_key: Current chain key
            
        Returns:
            32-byte message key
        """
        # Use HMAC-SHA256 - must match JavaScript which uses 0x02 for message key
        import hmac
        return hmac.digest(chain_key, b"\x02", hashlib.sha256)
    
    @staticmethod
    def _advance_chain_key(chain_key: bytes) -> bytes:
        """
        Advance chain key to next value.
        
        Args:
            chain_key: Current chain key
            
        Returns:
            Next chain key
        """
        # Use HMAC-SHA256 - must match JavaScript which uses 0x01 for chain key
        import hmac
        return hmac.digest(chain_key, b"\x01", hashlib.sha256)
    
    def serialize_state(self) -> dict:
        """
        Serialize ratchet state to dictionary.
        
        Returns:
            Dictionary representation of state
        """
        return {
            "dh_self": bytes(self.state.dh_self).hex() if self.state.dh_self else None,
            "dh_remote": bytes(self.state.dh_remote).hex() if self.state.dh_remote else None,
            "root_key": self.state.root_key.hex(),
            "sending_chain_key": self.state.sending_chain_key.hex() if self.state.sending_chain_key else None,
            "receiving_chain_key": self.state.receiving_chain_key.hex() if self.state.receiving_chain_key else None,
            "sending_message_number": self.state.sending_message_number,
            "receiving_message_number": self.state.receiving_message_number,
            "prev_sending_chain_length": self.state.prev_sending_chain_length,
            "skipped_keys": {
                f"{dh}:{n}": key.hex()
                for (dh, n), key in self.state.skipped_keys.items()
            },
        }
    
    @classmethod
    def deserialize_state(cls, data: dict) -> "RatchetEngine":
        """
        Deserialize ratchet state from dictionary.
        
        Args:
            data: Dictionary representation of state
            
        Returns:
            RatchetEngine with restored state
        """
        state = RatchetState()
        
        if data.get("dh_self"):
            state.dh_self = PrivateKey(bytes.fromhex(data["dh_self"]))
        if data.get("dh_remote"):
            state.dh_remote = PublicKey(bytes.fromhex(data["dh_remote"]))
        
        state.root_key = bytes.fromhex(data["root_key"])
        
        if data.get("sending_chain_key"):
            state.sending_chain_key = bytes.fromhex(data["sending_chain_key"])
        if data.get("receiving_chain_key"):
            state.receiving_chain_key = bytes.fromhex(data["receiving_chain_key"])
        
        state.sending_message_number = data["sending_message_number"]
        state.receiving_message_number = data["receiving_message_number"]
        state.prev_sending_chain_length = data["prev_sending_chain_length"]
        
        # Deserialize skipped keys
        for key_str, key_hex in data.get("skipped_keys", {}).items():
            dh, n = key_str.split(":")
            state.skipped_keys[(dh, int(n))] = bytes.fromhex(key_hex)
        
        return cls(state)
