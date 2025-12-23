"""Session management for E2EE messaging."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Tuple
from pathlib import Path

from nacl.public import PrivateKey, PublicKey
from nacl.encoding import RawEncoder

from .x3dh import X3DHProtocol
from .ratchet import RatchetEngine, RatchetHeader
from ..models import PrekeyBundle, Session
from ..exceptions import WhatsAppClientError

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages encrypted sessions with other users.
    
    Handles session establishment using X3DH protocol and session persistence.
    """

    def __init__(self, user_id: str, storage_path: str):
        """
        Initialize session manager.
        
        Args:
            user_id: Current user's ID
            storage_path: Path to store session data
        """
        self.user_id = user_id
        self.storage_path = Path(storage_path).expanduser()
        self.sessions_dir = self.storage_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory session cache
        self._sessions: Dict[str, Session] = {}
        
        logger.info(f"SessionManager initialized for user {user_id}")
    
    def get_session(self, peer_id: str) -> Optional[Session]:
        """
        Get existing session with peer.
        
        Args:
            peer_id: Peer's user ID
            
        Returns:
            Session object or None if no session exists
        """
        # Check cache first
        if peer_id in self._sessions:
            return self._sessions[peer_id]
        
        # Load from disk
        session = self._load_session(peer_id)
        if session:
            self._sessions[peer_id] = session
        
        return session
    
    async def ensure_session(
        self,
        peer_id: str,
        identity_private_key: PrivateKey,
        fetch_prekey_bundle_callback,
        mark_prekey_used_callback
    ) -> Session:
        """
        Ensure session exists with peer, creating if necessary.
        
        Args:
            peer_id: Peer's user ID
            identity_private_key: Own identity private key
            fetch_prekey_bundle_callback: Async function to fetch peer's prekey bundle
            mark_prekey_used_callback: Async function to mark one-time prekey as used
            
        Returns:
            Session object
            
        Raises:
            WhatsAppClientError: If session establishment fails
        """
        # Check if session already exists
        session = self.get_session(peer_id)
        if session:
            logger.info(f"Using existing session with {peer_id}")
            return session
        
        # Establish new session using X3DH
        logger.info(f"Establishing new session with {peer_id}")
        
        # Fetch peer's prekey bundle
        prekey_bundle = await fetch_prekey_bundle_callback(peer_id)
        if not prekey_bundle:
            raise WhatsAppClientError(f"Failed to fetch prekey bundle for {peer_id}")
        
        # Verify signed prekey signature
        if not X3DHProtocol.verify_prekey_signature(
            prekey_bundle.signed_prekey,
            prekey_bundle.signature,
            prekey_bundle.signing_key
        ):
            raise WhatsAppClientError(f"Invalid prekey signature for {peer_id}")
        
        # Perform X3DH key agreement
        shared_secret, ephemeral_key, initial_message_key = X3DHProtocol.initiate_session(
            identity_private_key,
            prekey_bundle
        )
        
        logger.debug(f"X3DH initiator shared secret: {shared_secret.hex()}")

        # Get identity public key for X3DH data (from the PrivateKey object)
        import base64
        identity_public_key = bytes(identity_private_key.public_key)

        # Create session record
        session = Session(
            session_id=f"{self.user_id}_{peer_id}_{datetime.now().timestamp()}",
            peer_id=peer_id,
            shared_secret=shared_secret.hex(),
            ephemeral_key=ephemeral_key.encode(encoder=RawEncoder).hex(),
            initial_message_key=initial_message_key.hex(),
            created_at=datetime.now().isoformat(),
            one_time_prekey_used=None
        )

        # Store X3DH data for first message (will be cleared after sending)
        import base64
        session.x3dh_data = {
            "localIdentityKey": base64.b64encode(identity_public_key).decode('utf-8'),
            "localEphemeralKey": base64.b64encode(
                ephemeral_key.public_key.encode(encoder=RawEncoder)
            ).decode('utf-8'),
            "usedSignedPrekeyId": prekey_bundle.signed_prekey_id,
            "usedOneTimePrekeyId": prekey_bundle.one_time_prekey_id
        }

        # Mark one-time prekey as used if it was consumed
        if prekey_bundle.one_time_prekeys and len(prekey_bundle.one_time_prekeys) > 0:
            one_time_prekey_id = prekey_bundle.one_time_prekeys[0]
            session.one_time_prekey_used = one_time_prekey_id

            try:
                await mark_prekey_used_callback(one_time_prekey_id)
                logger.info(f"Marked one-time prekey {one_time_prekey_id[:8]}... as used")
            except Exception as e:
                logger.warning(f"Failed to mark prekey as used: {e}")

        # Initialize ratchet with shared secret as sender/initiator
        # This matches JavaScript: kdfRootKey(sharedSecret, new Uint8Array(32))
        ratchet = RatchetEngine()

        # Derive root key and initial chain key from shared secret and 32 zero bytes
        # Matches JavaScript implementation in initializeRatchet()
        new_root_key, initial_chain_key = ratchet._kdf_rk(shared_secret, bytes(32))

        # Generate our DH ratchet key pair for Double Ratchet
        dh_ratchet_key = PrivateKey.generate()

        # Set up initial state for sender (no remote ratchet key yet)
        ratchet.state.root_key = new_root_key
        ratchet.state.dh_self = dh_ratchet_key
        ratchet.state.dh_remote = None  # Will be set when we receive first response
        ratchet.state.sending_chain_key = initial_chain_key  # Sender uses chain key
        ratchet.state.receiving_chain_key = None
        ratchet.state.sending_message_number = 0
        ratchet.state.receiving_message_number = 0
        ratchet.state.prev_sending_chain_length = 0

        # Save ratchet state to session
        session.ratchet_state = ratchet.serialize_state()

        # Store session
        self._save_session(session)
        self._sessions[peer_id] = session

        logger.info(f"Session established with {peer_id}: {session.session_id}")
        return session

    async def process_first_message(
        self,
        peer_id: str,
        encrypted_content: str,
        identity_private_key,
        get_signed_prekey_callback,
        get_one_time_prekey_callback,
    ) -> str:
        """
        Process first message from peer containing X3DH data.
        
        This establishes a session as responder (receiver) when someone sends
        us their first encrypted message with X3DH initialization data.
        
        Args:
            peer_id: Sender's user ID
            encrypted_content: The encrypted message JSON string
            identity_private_key: Our identity private key
            get_signed_prekey_callback: Callback to get our signed prekey by ID
            get_one_time_prekey_callback: Callback to get our one-time prekey by ID
            
        Returns:
            Decrypted plaintext
            
        Raises:
            WhatsAppClientError: If X3DH or decryption fails
        """
        import base64
        
        try:
            payload = json.loads(encrypted_content)
        except json.JSONDecodeError as e:
            raise WhatsAppClientError(f"Invalid encrypted message format: {e}")
        
        # Check if this is a first message with X3DH data
        x3dh_data = payload.get("x3dh")
        if not x3dh_data:
            raise WhatsAppClientError("No X3DH data in first message")
        
        logger.info(f"Processing first message from {peer_id} with X3DH data")
        
        # Extract X3DH parameters
        remote_identity_key = base64.b64decode(x3dh_data["senderIdentityKey"])
        remote_ephemeral_key = base64.b64decode(x3dh_data["senderEphemeralKey"])
        used_signed_prekey_id = x3dh_data["usedSignedPrekeyId"]
        used_one_time_prekey_id = x3dh_data.get("usedOneTimePrekeyId")
        
        # Get our signed prekey that was used
        signed_prekey_private = await get_signed_prekey_callback(used_signed_prekey_id)
        if not signed_prekey_private:
            raise WhatsAppClientError(f"Signed prekey {used_signed_prekey_id} not found")
        
        # Get our one-time prekey if it was used
        one_time_prekey_private = None
        if used_one_time_prekey_id is not None:
            one_time_prekey_private = await get_one_time_prekey_callback(used_one_time_prekey_id)
        
        # Perform X3DH as responder
        shared_secret = X3DHProtocol.respond_session(
            identity_private_key=identity_private_key,
            signed_prekey_private=signed_prekey_private,
            one_time_prekey_private=one_time_prekey_private,
            remote_identity_key=remote_identity_key,
            remote_ephemeral_key=remote_ephemeral_key,
        )
        
        logger.info(f"X3DH responder shared secret derived for {peer_id}")
        logger.debug(f"X3DH shared secret: {shared_secret.hex()}")
        
        # Create session record
        from datetime import datetime
        session = Session(
            session_id=f"{peer_id}_{self.user_id}_{datetime.now().timestamp()}",
            peer_id=peer_id,
            shared_secret=shared_secret.hex(),
            ephemeral_key="",  # Not used for responder
            initial_message_key="",  # Not used for responder
            created_at=datetime.now().isoformat(),
            one_time_prekey_used=str(used_one_time_prekey_id) if used_one_time_prekey_id else None
        )
        
        # Initialize ratchet for receiving
        ratchet = RatchetEngine()
        
        # Parse the sender's ratchet key from message header
        header_data = payload.get("header", {})
        sender_ratchet_key_b64 = header_data.get("ratchetKey")
        if not sender_ratchet_key_b64:
            raise WhatsAppClientError("Missing ratchet key in message header")
        
        sender_ratchet_key = base64.b64decode(sender_ratchet_key_b64)
        logger.debug(f"Sender's ratchet key (base64): {sender_ratchet_key_b64}")
        logger.debug(f"Sender's ratchet key (hex): {sender_ratchet_key.hex()}")
        
        # Initialize ratchet as receiver with sender's ratchet key
        logger.debug(f"Calling initialize_responder with shared_secret={shared_secret.hex()[:16]}...")
        ratchet.initialize_responder(shared_secret, sender_ratchet_key)
        logger.debug(f"Ratchet initialized.")
        logger.debug(f"  root_key={ratchet.state.root_key.hex()[:16]}...")
        logger.debug(f"  receiving_chain_key={ratchet.state.receiving_chain_key.hex() if ratchet.state.receiving_chain_key else 'None'}")
        logger.debug(f"  sending_chain_key={ratchet.state.sending_chain_key.hex() if ratchet.state.sending_chain_key else 'None'}")
        logger.debug(f"  dh_remote={bytes(ratchet.state.dh_remote).hex()[:16] if ratchet.state.dh_remote else 'None'}...")
        logger.debug(f"  dh_self={bytes(ratchet.state.dh_self).hex()[:16] if ratchet.state.dh_self else 'None'}...")
        
        # Save ratchet state to session
        session.ratchet_state = ratchet.serialize_state()
        
        # Store session
        self._save_session(session)
        self._sessions[peer_id] = session
        
        logger.info(f"Session established as responder with {peer_id}")
        
        # Now decrypt the actual message
        ciphertext_b64 = payload.get("ciphertext")
        auth_tag_b64 = payload.get("authTag")
        
        if not ciphertext_b64:
            raise WhatsAppClientError("Missing ciphertext in encrypted message")
        
        ciphertext = base64.b64decode(ciphertext_b64)
        auth_tag = base64.b64decode(auth_tag_b64) if auth_tag_b64 else None
        
        header = RatchetHeader.from_dict(header_data)
        
        logger.debug(f"Attempting to decrypt first message. Header: {header.to_dict()}")
        
        # Decrypt with the ratchet
        plaintext = ratchet.decrypt(ciphertext, header, auth_tag)
        
        # Update session with new ratchet state
        session.ratchet_state = ratchet.serialize_state()
        self._save_session(session)
        
        logger.info(f"Successfully decrypted first message from {peer_id}: plaintext='{plaintext[:50]}...'")
        return plaintext
    
    def encrypt_message(self, peer_id: str, plaintext: str) -> str:
        """
        Encrypt a message for peer.
        
        Args:
            peer_id: Peer's user ID
            plaintext: Message to encrypt
            
        Returns:
            Encrypted message with E2EE: prefix
            
        Raises:
            WhatsAppClientError: If no session exists or encryption fails
        """
        session = self.get_session(peer_id)
        if not session:
            raise WhatsAppClientError(f"No session with {peer_id}")
        
        # Get or initialize ratchet
        ratchet = self._get_ratchet(session)
        
        # Check if this is the first message (session has X3DH data)
        is_first_message = session.x3dh_data is not None

        # Encrypt message
        ciphertext, header = ratchet.encrypt(plaintext)

        # Update session with new ratchet state
        session.ratchet_state = ratchet.serialize_state()

        # Create encrypted message payload (Signal protocol format)
        header_dict = header.to_dict()
        payload = {
            "ciphertext": ciphertext,
            "header": header_dict,
        }

        # Log the exact values being sent for debugging
        logger.debug(f"Payload header.ratchetKey: '{header_dict['ratchetKey']}'")
        logger.debug(f"Payload header.ratchetKey length: {len(header_dict['ratchetKey'])}")
        logger.debug(f"Payload ciphertext length: {len(ciphertext)}")

        # Add X3DH data if this is the first message
        if is_first_message and session.x3dh_data:
            logger.info(f"Adding X3DH data to first message for {peer_id}")
            payload["x3dh"] = {
                "senderIdentityKey": session.x3dh_data["localIdentityKey"],
                "senderEphemeralKey": session.x3dh_data["localEphemeralKey"],
                "usedSignedPrekeyId": session.x3dh_data["usedSignedPrekeyId"],
                "usedOneTimePrekeyId": session.x3dh_data["usedOneTimePrekeyId"]
            }

            # Clear X3DH data after including it in first message
            session.x3dh_data = None

        # Save session (updates ratchet state and clears x3dh_data if needed)
        self._save_session(session)

        # Return with E2EE: prefix for compatibility
        return "E2EE:" + json.dumps(payload)
    
    def decrypt_message(self, peer_id: str, encrypted_message: str) -> str:
        """
        Decrypt a message from peer.
        
        Args:
            peer_id: Peer's user ID
            encrypted_message: Encrypted message (with or without E2EE: prefix)
            
        Returns:
            Decrypted plaintext
            
        Raises:
            WhatsAppClientError: If no session exists or decryption fails
        """
        session = self.get_session(peer_id)
        if not session:
            raise WhatsAppClientError(f"No session with {peer_id}")
        
        # Strip E2EE: prefix if present
        message = encrypted_message
        if message.startswith("E2EE:"):
            message = message[5:]
        
        logger.debug(f"Decrypting message from {peer_id}: {message[:80]}...")
        
        # Parse encrypted payload
        try:
            payload = json.loads(message)
            ciphertext = payload["ciphertext"]
            header = RatchetHeader.from_dict(payload["header"])
            logger.debug(f"Parsed payload: ciphertext={ciphertext[:30]}..., header={header.to_dict()}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Invalid encrypted message format: {e}")
            raise WhatsAppClientError(f"Invalid encrypted message format: {e}")
        
        # Get or initialize ratchet
        ratchet = self._get_ratchet(session)
        
        # Try skipped keys first (for out-of-order messages)
        plaintext = ratchet.try_skipped_message_keys(ciphertext, header)
        
        if plaintext is None:
            # Decrypt with current ratchet state
            logger.debug(f"Attempting to decrypt with current ratchet state...")
            plaintext = ratchet.decrypt(ciphertext, header)
            logger.info(f"Successfully decrypted message from {peer_id}: '{plaintext[:50]}...'")
        
        # Update session with new ratchet state
        session.ratchet_state = ratchet.serialize_state()
        self._save_session(session)
        
        return plaintext
    
    def _get_ratchet(self, session: Session) -> RatchetEngine:
        """
        Get or initialize ratchet for session.
        
        Args:
            session: Session object
            
        Returns:
            RatchetEngine instance
        """
        # If ratchet state exists, deserialize it
        if session.ratchet_state:
            return RatchetEngine.deserialize_state(session.ratchet_state)
        
        # Initialize new ratchet as sender
        ratchet = RatchetEngine()
        
        # Get shared secret from X3DH
        shared_secret = bytes.fromhex(session.shared_secret)
        ephemeral_key = PrivateKey(bytes.fromhex(session.ephemeral_key), encoder=RawEncoder)
        
        # Initialize as receiver first (we have our DH key from X3DH)
        ratchet.initialize_receiver(shared_secret, ephemeral_key)
        
        # For initial encryption, we need to perform DH ratchet with a new key pair
        # Generate new DH key pair
        ratchet.state.dh_self = PrivateKey.generate()
        
        # Derive sending chain (without remote DH key yet - will be set from first message)
        # For now, derive from root key directly
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"WhatsAppCloneRatchet",
            info=b"InitialSendingChain",
        )
        ratchet.state.sending_chain_key = hkdf.derive(shared_secret)
        
        return ratchet
    
    def delete_session(self, peer_id: str) -> None:
        """
        Delete session with peer.
        
        Args:
            peer_id: Peer's user ID
        """
        # Remove from cache
        if peer_id in self._sessions:
            del self._sessions[peer_id]
        
        # Remove from disk
        session_file = self._get_session_file(peer_id)
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session with {peer_id}")
    
    def _get_session_file(self, peer_id: str) -> Path:
        """Get path to session file for peer."""
        return self.sessions_dir / f"{peer_id}.json"
    
    def _save_session(self, session: Session) -> None:
        """Save session to disk."""
        session_file = self._get_session_file(session.peer_id)
        
        session_data = {
            "session_id": session.session_id,
            "peer_id": session.peer_id,
            "shared_secret": session.shared_secret,
            "ephemeral_key": session.ephemeral_key,
            "initial_message_key": session.initial_message_key,
            "created_at": session.created_at,
            "one_time_prekey_used": session.one_time_prekey_used,
            "ratchet_state": session.ratchet_state,
            "x3dh_data": session.x3dh_data,
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(session_file, 0o600)
        
        logger.debug(f"Saved session to {session_file}")
    
    def _load_session(self, peer_id: str) -> Optional[Session]:
        """Load session from disk."""
        session_file = self._get_session_file(peer_id)
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            session = Session(
                session_id=session_data["session_id"],
                peer_id=session_data["peer_id"],
                shared_secret=session_data["shared_secret"],
                ephemeral_key=session_data["ephemeral_key"],
                initial_message_key=session_data["initial_message_key"],
                created_at=session_data["created_at"],
                one_time_prekey_used=session_data.get("one_time_prekey_used"),
                ratchet_state=session_data.get("ratchet_state"),
                x3dh_data=session_data.get("x3dh_data"),
            )
            
            logger.debug(f"Loaded session from {session_file}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session from {session_file}: {e}")
            return None
    
    def list_sessions(self) -> list[str]:
        """
        List all peer IDs with active sessions.
        
        Returns:
            List of peer user IDs
        """
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            peer_id = session_file.stem
            sessions.append(peer_id)
        return sessions
