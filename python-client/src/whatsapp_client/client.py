"""Main WhatsApp Client class."""

import logging
from typing import Optional, Callable, List, Dict, Any
import uuid
import time

from .auth import AuthManager
from .transport import RestClient, WebSocketClient, ConnectionState
from .crypto import KeyManager, SessionManager
from .storage import MessageStorage
from .models import User, PrekeyBundle, Session, Message
from .exceptions import WhatsAppClientError

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Main client for WhatsApp Clone platform.

    This is the primary interface for interacting with the chat backend.
    Supports user authentication, messaging, and E2EE operations.

    Example:
        >>> client = WhatsAppClient(server_url="https://worker.workers.dev")
        >>> await client.register("alice", "password123")
        >>> await client.login("alice", "password123")
        >>> print(f"Logged in as {client.user.username}")
    """

    def __init__(
        self,
        server_url: str,
        storage_path: str = "~/.whatsapp_client",
        auto_connect: bool = True,
        log_level: str = "INFO",
    ) -> None:
        """
        Initialize WhatsApp Client.

        Args:
            server_url: Base URL of the Cloudflare Worker backend
            storage_path: Path for local data storage (default: ~/.whatsapp_client)
            auto_connect: Auto-connect WebSocket on login (default: True)
            log_level: Logging level (default: INFO)
        """
        self.server_url = server_url
        self.storage_path = storage_path
        self.auto_connect = auto_connect

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info(f"Initializing WhatsAppClient (server: {server_url})")

        # Initialize subsystems
        self._rest = RestClient(server_url)
        self._auth = AuthManager(self)
        self._key_manager: Optional[KeyManager] = None
        self._session_manager: Optional[SessionManager] = None
        self._ws: Optional[WebSocketClient] = None
        self._message_storage: Optional[MessageStorage] = None
        self._fingerprint_storage: Optional[Any] = None
        self._group_storage: Optional[Any] = None

        # State
        self._closed = False
        self._message_handlers: List[Callable] = []
        self._typing_handlers: List[Callable] = []
        self._status_handlers: List[Callable] = []
        self._presence_handlers: List[Callable] = []
        self._group_message_handlers: List[Callable] = []
        self._online_users: Dict[str, bool] = {}  # Track online presence

    @property
    def user(self) -> Optional[User]:
        """Get current authenticated user."""
        return self._auth.user

    @property
    def user_id(self) -> Optional[str]:
        """Get current user ID."""
        return self._auth.user_id

    @property
    def token(self) -> Optional[str]:
        """Get current JWT authentication token."""
        return self._auth.token

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._auth.is_authenticated

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws is not None and self._ws.is_connected

    @property
    def connection_state(self) -> Optional[ConnectionState]:
        """Get WebSocket connection state."""
        return self._ws.state if self._ws else None

    def get_fingerprint(self) -> str:
        """
        Get own encryption key fingerprint.

        Returns:
            60-character hexadecimal fingerprint

        Raises:
            WhatsAppClientError: If not authenticated or keys not initialized

        Example:
            >>> fingerprint = client.get_fingerprint()
            >>> print(f"My fingerprint: {fingerprint}")
        """
        if not self.is_authenticated:
            raise WhatsAppClientError("Not authenticated")
        if not self._key_manager:
            raise WhatsAppClientError("Keys not initialized")
        return self._key_manager.get_fingerprint()
    
    async def get_peer_fingerprint(self, peer_id: str) -> str:
        """
        Get peer's encryption key fingerprint.
        
        Retrieves the fingerprint from the established session with the peer.
        
        Args:
            peer_id: Peer user ID
            
        Returns:
            Peer's 60-character hexadecimal fingerprint
            
        Raises:
            WhatsAppClientError: If session not established or peer not found
            
        Example:
            >>> peer_fp = await client.get_peer_fingerprint("user_123")
            >>> print(f"Peer fingerprint: {peer_fp}")
        """
        if not self._session_manager:
            raise WhatsAppClientError("Session manager not initialized")
        
        try:
            # Ensure session exists
            await self.ensure_session(peer_id)
            
            # Get session and compute fingerprint from peer's identity key
            session = self._session_manager.get_session(peer_id)
            if not session:
                raise WhatsAppClientError(f"No session with {peer_id}")
            
            # Compute fingerprint from peer's DH public key
            import hashlib
            peer_key_bytes = session.dh_public_key.public_bytes_raw()
            fingerprint_hash = hashlib.sha256(peer_key_bytes).hexdigest().upper()
            
            logger.debug(f"Got peer fingerprint for {peer_id}")
            return fingerprint_hash
            
        except Exception as e:
            logger.error(f"Failed to get peer fingerprint: {e}")
            raise WhatsAppClientError(f"Failed to get peer fingerprint: {e}")
    
    async def verify_fingerprint(
        self,
        peer_id: str,
        fingerprint: Optional[str] = None,
        verified: bool = True,
    ) -> bool:
        """
        Verify a peer's encryption key fingerprint.
        
        Call this after verifying the fingerprint out-of-band (e.g., QR code scan).
        
        Args:
            peer_id: Peer user ID
            fingerprint: Expected fingerprint (optional, for validation)
            verified: Mark as verified (default: True)
            
        Returns:
            True if verification successful, False otherwise
            
        Raises:
            WhatsAppClientError: If verification fails
            
        Example:
            >>> # After scanning QR code and verifying fingerprint matches:
            >>> await client.verify_fingerprint("user_123", verified=True)
            >>> is_verified = await client.is_fingerprint_verified("user_123")
        """
        from .storage import FingerprintStorage
        
        if not self._fingerprint_storage:
            raise WhatsAppClientError("Fingerprint storage not initialized")
        
        try:
            # Get peer's current fingerprint if not provided
            if fingerprint is None:
                fingerprint = await self.get_peer_fingerprint(peer_id)
            
            # Get stored fingerprint to validate
            stored_fp = self._fingerprint_storage.get_fingerprint(peer_id)
            
            if stored_fp and fingerprint != stored_fp["fingerprint"]:
                logger.warning(f"Fingerprint mismatch for {peer_id}!")
                raise WhatsAppClientError(f"Fingerprint mismatch for {peer_id}")
            
            # Mark as verified
            success = self._fingerprint_storage.verify_fingerprint(peer_id, verified)
            
            if success:
                logger.info(f"Fingerprint for {peer_id} verified: {verified}")
            
            return success
            
        except Exception as e:
            logger.error(f"Fingerprint verification failed: {e}")
            raise WhatsAppClientError(f"Fingerprint verification failed: {e}")
    
    async def is_fingerprint_verified(self, peer_id: str) -> bool:
        """
        Check if a peer's fingerprint is verified.
        
        Args:
            peer_id: Peer user ID
            
        Returns:
            True if fingerprint is verified, False otherwise
            
        Example:
            >>> verified = await client.is_fingerprint_verified("user_123")
            >>> print(f"Verified: {verified}")
        """
        if not self._fingerprint_storage:
            return False
        
        return self._fingerprint_storage.is_verified(peer_id)
    
    async def get_verified_fingerprints(self) -> List[Dict[str, Any]]:
        """
        Get list of all verified peer fingerprints.
        
        Returns:
            List of verified fingerprint records
            
        Example:
            >>> verified = await client.get_verified_fingerprints()
            >>> for record in verified:
            ...     print(f"{record['peer_id']}: {record['fingerprint']}")
        """
        if not self._fingerprint_storage:
            return []
        
        return self._fingerprint_storage.get_verified_fingerprints()

    async def list_users(self) -> List[Dict[str, Any]]:
        """
        List all registered users on the server.
        
        Returns:
            List of user dictionaries with id, username, avatar, lastSeen
            
        Example:
            >>> users = await client.list_users()
            >>> for user in users:
            ...     print(f"{user['username']}: {user['id']}")
        """
        try:
            response = await self._rest.get("/api/users")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    async def find_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their username.
        
        Args:
            username: Username to search for
            
        Returns:
            User dictionary with id, username, avatar, lastSeen or None if not found
            
        Example:
            >>> user = await client.find_user("alice")
            >>> if user:
            ...     print(f"Found: {user['id']}")
        """
        try:
            users = await self.list_users()
            for user in users:
                if user.get("username", "").lower() == username.lower():
                    return user
            return None
        except Exception as e:
            logger.error(f"Failed to find user: {e}")
            return None
    
    @staticmethod
    def compare_fingerprints(fingerprint1: str, fingerprint2: str) -> bool:
        """
        Compare two fingerprints for equality.
        
        Args:
            fingerprint1: First fingerprint
            fingerprint2: Second fingerprint
            
        Returns:
            True if fingerprints match, False otherwise
            
        Example:
            >>> match = client.compare_fingerprints(my_fp, peer_fp)
        """
        if not fingerprint1 or not fingerprint2:
            return False
        
        # Normalize to uppercase and remove whitespace
        fp1 = fingerprint1.upper().replace(" ", "").replace("\n", "")
        fp2 = fingerprint2.upper().replace(" ", "").replace("\n", "")
        
        return fp1 == fp2

    async def get_prekey_status(self) -> dict:
        """
        Get status of available prekeys.

        Returns:
            Dictionary with prekey availability info

        Example:
            >>> status = await client.get_prekey_status()
            >>> print(f"Available prekeys: {status['available']}")
        """
        if not self._key_manager:
            raise WhatsAppClientError("Keys not initialized")

        available = self._key_manager.get_available_prekey_count()
        return {
            "available": available,
            "needs_rotation": available < 10,
        }

    async def register(
        self, username: str, password: str, avatar: Optional[str] = None
    ) -> User:
        """
        Register a new user account.

        Args:
            username: Desired username
            password: Password
            avatar: Optional avatar URL

        Returns:
            User object with account details

        Raises:
            ValidationError: If username/password are invalid
            AuthenticationError: If registration fails
            ConnectionError: If network request fails

        Example:
            >>> user = await client.register("alice", "secure_password")
            >>> print(f"Registered: {user.username}")
        """
        user = await self._auth.register(username, password, avatar)
        self._rest.set_token(self.token)

        # Initialize cryptographic keys
        logger.info("Initializing cryptographic keys...")
        self._key_manager = KeyManager(self.user_id, self.storage_path)
        await self._key_manager.initialize(password=password)

        # Initialize session manager
        self._session_manager = SessionManager(self.user_id, self.storage_path)
        
        # Initialize message storage
        self._message_storage = MessageStorage(self.storage_path, self.user_id)
        
        # Initialize fingerprint storage
        from .storage import FingerprintStorage
        self._fingerprint_storage = FingerprintStorage(self.storage_path, self.user_id)
        
        # Initialize group storage
        from .storage import GroupStorage
        self._group_storage = GroupStorage(self.storage_path, self.user_id)

        # Upload public keys to server
        await self._upload_public_keys()
        
        # Connect to WebSocket if auto_connect enabled
        if self.auto_connect:
            await self._connect_websocket()

        logger.info(f"Registration successful for user: {username}")
        return user

    async def login(self, username: str, password: str) -> User:
        """
        Login with existing credentials.

        Args:
            username: Username
            password: Password

        Returns:
            User object with account details

        Raises:
            ValidationError: If credentials are empty
            AuthenticationError: If login fails
            ConnectionError: If network request fails

        Example:
            >>> user = await client.login("alice", "password123")
            >>> print(f"Logged in as {user.username}")
        """
        user = await self._auth.login(username, password)
        self._rest.set_token(self.token)

        # Initialize cryptographic keys
        logger.info("Initializing cryptographic keys...")
        self._key_manager = KeyManager(self.user_id, self.storage_path)
        await self._key_manager.initialize(password=password)

        # Initialize session manager
        self._session_manager = SessionManager(self.user_id, self.storage_path)
        
        # Initialize message storage
        self._message_storage = MessageStorage(self.storage_path, self.user_id)
        
        # Initialize fingerprint storage
        from .storage import FingerprintStorage
        self._fingerprint_storage = FingerprintStorage(self.storage_path, self.user_id)
        
        # Initialize group storage
        from .storage import GroupStorage
        self._group_storage = GroupStorage(self.storage_path, self.user_id)

        # Upload public keys to server
        await self._upload_public_keys()
        
        # Connect to WebSocket if auto_connect enabled
        if self.auto_connect:
            await self._connect_websocket()

        logger.info(f"Login successful for user: {username}")
        return user

    async def _upload_public_keys(self) -> None:
        """Upload public key bundle to server."""
        if not self._key_manager:
            raise WhatsAppClientError("Key manager not initialized")

        logger.info("Uploading public key bundle to server...")

        bundle = self._key_manager.get_public_bundle()

        # Prepare upload data - server expects specific structure
        upload_data = {
            "identityKey": bundle.identity_key,
            "signingKey": bundle.signing_key,
            "fingerprint": bundle.fingerprint,
        }

        # Add signed prekey if available
        if bundle.signed_prekey and bundle.signature and bundle.signed_prekey_id is not None:
            if isinstance(bundle.signed_prekey, dict):
                # New format: signed_prekey is a dict
                upload_data["signedPrekey"] = bundle.signed_prekey
            else:
                # Legacy format: signed_prekey is a string
                upload_data["signedPrekey"] = {
                    "keyId": bundle.signed_prekey_id,
                    "publicKey": bundle.signed_prekey,
                    "signature": bundle.signature,
                }
        else:
            upload_data["signedPrekey"] = None

        # Add one-time prekeys if available
        # get_public_bundle now returns list of {keyId, publicKey} dicts
        upload_data["oneTimePrekeys"] = bundle.one_time_prekeys if bundle.one_time_prekeys else []

        try:
            response = await self._rest.post("/api/users/prekeys", data=upload_data)

            if "error" in response:
                logger.error(f"Failed to upload keys: {response['error']}")
                raise WhatsAppClientError(f"Key upload failed: {response['error']}")

            logger.info(
                f"Uploaded keys: signed={response.get('signedPrekeyUploaded')}, "
                f"one-time={response.get('oneTimePrekeysUploaded')}"
            )

        except Exception as e:
            logger.error(f"Key upload failed: {e}")
            raise

    async def ensure_session(self, peer_id: str) -> Session:
        """
        Ensure encrypted session exists with peer.
        
        If no session exists, establishes one using X3DH protocol.
        
        Args:
            peer_id: Peer's user ID
            
        Returns:
            Session object
            
        Raises:
            WhatsAppClientError: If not authenticated or session establishment fails
            
        Example:
            >>> session = await client.ensure_session("bob_user_id")
            >>> print(f"Session established: {session.session_id}")
        """
        if not self.is_authenticated:
            raise WhatsAppClientError("Not authenticated")
        if not self._key_manager:
            raise WhatsAppClientError("Keys not initialized")
        if not self._session_manager:
            raise WhatsAppClientError("Session manager not initialized")
        
        # Get identity private key
        from nacl.public import PrivateKey as NaClPrivateKey
        identity_private_key = NaClPrivateKey(self._key_manager._identity_keypair.private_key)
        
        # Ensure session with callbacks
        session = await self._session_manager.ensure_session(
            peer_id=peer_id,
            identity_private_key=identity_private_key,
            fetch_prekey_bundle_callback=self._fetch_prekey_bundle,
            mark_prekey_used_callback=self._mark_prekey_used
        )
        
        return session
    
    async def _fetch_prekey_bundle(self, peer_id: str) -> PrekeyBundle:
        """Fetch prekey bundle from server for peer."""
        try:
            response = await self._rest.get(f"/api/users/{peer_id}/prekeys")
            
            if "error" in response:
                raise WhatsAppClientError(f"Failed to fetch prekey bundle: {response['error']}")
            
            # Extract signed prekey data
            signed_prekey_data = response.get("signedPrekey")
            if not signed_prekey_data:
                raise WhatsAppClientError(f"No signed prekey available for {peer_id}")

            # Extract one-time prekey if available
            one_time_prekey_data = response.get("oneTimePrekey")
            one_time_prekeys = []
            one_time_prekey_id = None
            if one_time_prekey_data:
                one_time_prekeys = [one_time_prekey_data["publicKey"]]
                one_time_prekey_id = one_time_prekey_data.get("keyId")

            # Parse response into PrekeyBundle
            bundle = PrekeyBundle(
                identity_key=response["identityKey"],
                signing_key=response["signingKey"],
                fingerprint=response["fingerprint"],
                signed_prekey=signed_prekey_data["publicKey"],
                signature=signed_prekey_data["signature"],
                signed_prekey_id=signed_prekey_data.get("keyId"),
                one_time_prekeys=one_time_prekeys,
                one_time_prekey_id=one_time_prekey_id
            )
            
            return bundle
            
        except Exception as e:
            logger.error(f"Failed to fetch prekey bundle for {peer_id}: {e}")
            raise WhatsAppClientError(f"Failed to fetch prekey bundle: {e}")
    
    async def _mark_prekey_used(self, prekey_id: str) -> None:
        """Mark one-time prekey as used on server."""
        try:
            await self._rest.delete(f"/api/users/prekeys/{prekey_id}")
            logger.debug(f"Marked prekey {prekey_id[:8]}... as used")
        except Exception as e:
            logger.warning(f"Failed to mark prekey as used: {e}")

    async def _get_signed_prekey(self, prekey_id: int):
        """Get our signed prekey private key by ID."""
        if not self._key_manager:
            return None
        # The key manager stores signed prekeys
        return self._key_manager.get_signed_prekey_private(prekey_id)
    
    async def _get_one_time_prekey(self, prekey_id: int):
        """Get our one-time prekey private key by ID."""
        if not self._key_manager:
            return None
        return self._key_manager.get_one_time_prekey_private(prekey_id)
    
    def get_session(self, peer_id: str) -> Optional[Session]:
        """
        Get existing session with peer (does not create new session).
        
        Args:
            peer_id: Peer's user ID
            
        Returns:
            Session object or None if no session exists
            
        Example:
            >>> session = client.get_session("bob_user_id")
            >>> if session:
            >>>     print(f"Session exists: {session.session_id}")
        """
        if not self._session_manager:
            return None
        return self._session_manager.get_session(peer_id)
    
    def delete_session(self, peer_id: str) -> None:
        """
        Delete session with peer.
        
        Args:
            peer_id: Peer's user ID
            
        Example:
            >>> client.delete_session("bob_user_id")
        """
        if self._session_manager:
            self._session_manager.delete_session(peer_id)
    
    def list_sessions(self) -> list[str]:
        """
        List all peer IDs with active sessions.
        
        Returns:
            List of peer user IDs
            
        Example:
            >>> peers = client.list_sessions()
            >>> print(f"Active sessions: {peers}")
        """
        if not self._session_manager:
            return []
        return self._session_manager.list_sessions()
    
    async def send_message(
        self,
        to: str,
        content: str,
        message_type: str = "text",
    ) -> Message:
        """
        Send an encrypted message to a user.
        
        Args:
            to: Recipient user ID
            content: Message content (will be encrypted)
            message_type: Message type (default: "text")
            
        Returns:
            Message object with sent message details
            
        Raises:
            WhatsAppClientError: If not authenticated or sending fails
            
        Example:
            >>> message = await client.send_message("bob_user_id", "Hello Bob!")
            >>> print(f"Message sent: {message.id}")
        """
        if not self.is_authenticated:
            raise WhatsAppClientError("Not authenticated")
        if not self._session_manager:
            raise WhatsAppClientError("Session manager not initialized")
        if not self._ws or not self._ws.is_connected:
            raise WhatsAppClientError("WebSocket not connected")
        
        # Ensure session exists with recipient
        await self.ensure_session(to)
        
        # Encrypt message
        encrypted_content = self._session_manager.encrypt_message(to, content)
        
        # Send encrypted message via WebSocket
        try:
            await self._ws.send_message(to, encrypted_content, message_type, encrypted=True)
            
            # Create Message object for return (we don't get confirmation immediately)
            message = Message(
                id=str(uuid.uuid4()),
                from_user=self.user_id,
                to=to,
                content=content,  # Return decrypted content
                timestamp=int(time.time() * 1000),
                status="sent",
                type=message_type,
            )
            
            logger.info(f"Message sent to {to}: {message.id}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise WhatsAppClientError(f"Failed to send message: {e}")
    
    def decrypt_message(self, from_user: str, encrypted_content: str) -> str:
        """
        Decrypt a received message.
        
        Args:
            from_user: Sender user ID
            encrypted_content: Encrypted message content
            
        Returns:
            Decrypted plaintext
            
        Raises:
            WhatsAppClientError: If no session or decryption fails
            
        Example:
            >>> plaintext = client.decrypt_message("alice_user_id", "E2EE:...")
            >>> print(f"Decrypted: {plaintext}")
        """
        if not self._session_manager:
            raise WhatsAppClientError("Session manager not initialized")
        
        return self._session_manager.decrypt_message(from_user, encrypted_content)
    
    async def _connect_websocket(self) -> None:
        """Initialize and connect WebSocket client."""
        if not self.user_id:
            raise WhatsAppClientError("Not authenticated")
        
        logger.info("Connecting to WebSocket...")
        self._ws = WebSocketClient(
            server_url=self.server_url,
            user_id=self.user_id,
            username=self.user.username if self.user else None,
            auto_reconnect=True,
        )
        
        # Register internal handlers
        self._ws.on_message(self._handle_incoming_message)
        self._ws.on_typing(self._handle_typing)
        self._ws.on_status(self._handle_status)
        self._ws.on_presence(self._handle_presence)
        
        await self._ws.connect()
    
    async def _handle_incoming_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming message from WebSocket."""
        try:
            import json
            
            # Extract payload from WebSocket message
            # Worker sends { type: 'message', payload: {...} }
            payload = data.get("payload", data)
            
            from_user = payload["from"]
            content = payload["content"]

            # Ignore messages from ourselves (echo bot shouldn't process its own replies)
            if from_user == self.user_id:
                logger.debug(f"Ignoring message from self: {from_user}")
                return

            # Create Message object
            message = Message(
                id=payload.get("id", str(uuid.uuid4())),
                from_user=from_user,
                to=self.user_id,
                content=content,
                type=payload.get("type", "text"),
                timestamp=payload.get("timestamp", int(time.time() * 1000)),
                status="delivered",
            )
            
            # Decrypt if encrypted (check for Signal protocol format)
            # Note: Server might not always set encrypted=true correctly, so also check content format
            content_is_encrypted_json = False
            try:
                encrypted_data = json.loads(content)
                content_is_encrypted_json = "ciphertext" in encrypted_data and "header" in encrypted_data
                if content_is_encrypted_json:
                    logger.debug(f"Detected encrypted JSON content from {from_user}")
            except json.JSONDecodeError:
                pass
            
            if payload.get("encrypted") or content_is_encrypted_json:
                logger.debug(f"Processing encrypted message from {from_user} (encrypted flag={payload.get('encrypted')}, is_encrypted_json={content_is_encrypted_json})")
                try:
                    if not self._session_manager:
                        raise WhatsAppClientError("Session manager not initialized")
                    if not self._key_manager:
                        raise WhatsAppClientError("Key manager not initialized")
                    
                    # Parse the encrypted content to check for X3DH first message
                    encrypted_data = json.loads(content)
                    
                    # Check if we already have a session with this peer
                    existing_session = self._session_manager.get_session(from_user)
                    logger.debug(f"Session check: from_user={from_user}, existing_session={existing_session is not None}, has_x3dh={'x3dh' in encrypted_data}")
                    
                    if "x3dh" in encrypted_data and not existing_session:
                        # This is a first message from a new peer - process X3DH as responder
                        logger.info(f"Received first encrypted message from {from_user} with X3DH data")
                        
                        from nacl.public import PrivateKey as NaClPrivateKey
                        identity_private_key = NaClPrivateKey(self._key_manager._identity_keypair.private_key)
                        
                        message.content = await self._session_manager.process_first_message(
                            peer_id=from_user,
                            encrypted_content=content,
                            identity_private_key=identity_private_key,
                            get_signed_prekey_callback=self._get_signed_prekey,
                            get_one_time_prekey_callback=self._get_one_time_prekey,
                        )
                    elif existing_session:
                        # Session exists - decrypt with existing session
                        # But first check if sender's message number is suspiciously low
                        # (indicates they reset their encryption but we still have old session)
                        sender_msg_num = encrypted_data.get("header", {}).get("messageNumber", 0)
                        if sender_msg_num < 5 and existing_session.ratchet_state:
                            our_receiving_num = existing_session.ratchet_state.get("receiving_message_number", 0)
                            our_sending_num = existing_session.ratchet_state.get("sending_message_number", 0)
                            # If sender is at msg 0-4 but we've sent/received many messages before,
                            # they likely reset - delete our old session
                            if our_receiving_num > 5 or our_sending_num > 5:
                                logger.warning(
                                    f"Session mismatch detected with {from_user}: "
                                    f"sender at msg #{sender_msg_num}, we're at send:{our_sending_num}/recv:{our_receiving_num}. "
                                    f"Deleting old session. Sender should include X3DH data in next message."
                                )
                                self._session_manager.delete_session(from_user)
                                existing_session = None

                        if existing_session:
                            logger.debug(f"Decrypting with existing session for {from_user}")
                            message.content = self._session_manager.decrypt_message(from_user, content)

                    if not existing_session and "x3dh" not in encrypted_data:
                        # No session and no X3DH data - cannot decrypt
                        # This happens when:
                        # 1. We restarted and lost our session
                        # 2. The sender has an old session with us
                        # 3. The sender needs to reset their encryption
                        logger.warning(
                            f"Cannot decrypt message from {from_user}: no session and no X3DH data. "
                            "The sender may need to reset their encryption."
                        )
                        # Keep the encrypted content - don't try to establish a new session
                        # as it won't match what the sender used
                        
                except json.JSONDecodeError:
                    # Not JSON, might be legacy E2EE: format
                    if content.startswith("E2EE:"):
                        message.content = self._session_manager.decrypt_message(from_user, content)
                    else:
                        logger.error(f"Unknown encrypted message format from {from_user}")
                except Exception as e:
                    logger.error(f"Failed to decrypt message from {from_user}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Keep encrypted content for debugging
            
            # Save to storage
            if self._message_storage:
                self._message_storage.save_message(message)
            
            # Send delivery status
            if self._ws:
                await self._ws.send_status_update(message.id, "delivered")
            
            # Notify user handlers
            for handler in self._message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
        
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_typing(self, data: Dict[str, Any]) -> None:
        """Handle typing indicator."""
        for handler in self._typing_handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Typing handler error: {e}")
    
    async def _handle_status(self, data: Dict[str, Any]) -> None:
        """Handle status update."""
        # Update message status in storage
        if self._message_storage:
            message_id = data.get("messageId")
            status = data.get("status")
            if message_id and status:
                self._message_storage.update_message_status(message_id, status)
        
        # Notify user handlers
        for handler in self._status_handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Status handler error: {e}")
    
    async def _handle_presence(self, data: Dict[str, Any]) -> None:
        """Handle presence update."""
        # Update presence tracking
        user_id = data.get("userId")
        online = data.get("online", False)
        
        if user_id:
            self._online_users[user_id] = online
        
        # Notify handlers
        for handler in self._presence_handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Presence handler error: {e}")
    
    async def send_message_realtime(
        self,
        to: str,
        content: str,
        type: str = "text",
        encrypt: bool = True,
    ) -> Message:
        """
        Send a message in real-time via WebSocket.
        
        Args:
            to: Recipient user ID
            content: Message content
            type: Message type (default: "text")
            encrypt: Whether to encrypt the message (default: True)
            
        Returns:
            Message object
            
        Raises:
            WhatsAppClientError: If not connected or send fails
        """
        if not self.is_connected:
            raise WhatsAppClientError("Not connected to WebSocket")
        
        # Encrypt message if requested
        if encrypt and self._session_manager:
            try:
                # Ensure session exists
                await self.ensure_session(to)
                # Encrypt content
                content = self._session_manager.encrypt_message(to, content)
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                raise WhatsAppClientError(f"Message encryption failed: {e}")
        
        # Create message object
        message = Message(
            id=str(uuid.uuid4()),
            from_user=self.user_id,
            to=to,
            content=content,
            type=type,
            timestamp=int(time.time() * 1000),
            status="sent",
        )
        
        # Save to storage
        if self._message_storage:
            self._message_storage.save_message(message)
        
        # Send via WebSocket
        await self._ws.send_message(to, content, type)
        
        logger.debug(f"Sent message to {to}")
        return message
    
    async def get_messages(
        self,
        peer_id: str,
        limit: int = 50,
        before_timestamp: Optional[int] = None,
    ) -> List[Message]:
        """
        Get message history with a peer.
        
        Args:
            peer_id: Peer user ID
            limit: Maximum number of messages (default: 50)
            before_timestamp: Get messages before this timestamp (for pagination)
            
        Returns:
            List of messages in chronological order
        """
        if not self._message_storage:
            raise WhatsAppClientError("Message storage not initialized")
        
        return self._message_storage.get_messages(peer_id, limit, before_timestamp)
    
    async def get_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent conversations.
        
        Args:
            limit: Maximum number of conversations
            
        Returns:
            List of conversation summaries
        """
        if not self._message_storage:
            raise WhatsAppClientError("Message storage not initialized")
        
        return self._message_storage.get_recent_conversations(limit)
    
    async def search_messages(
        self,
        query: str,
        peer_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Message]:
        """
        Search messages by content.
        
        Args:
            query: Search query
            peer_id: Optional peer to limit search
            limit: Maximum results
            
        Returns:
            List of matching messages
        """
        if not self._message_storage:
            raise WhatsAppClientError("Message storage not initialized")
        
        return self._message_storage.search_messages(query, peer_id, limit)
    
    async def send_image(
        self,
        to: str,
        image_path: Optional[str] = None,
        image_data: Optional[bytes] = None,
        caption: Optional[str] = None,
        max_size: int = 5 * 1024 * 1024,  # 5MB default
    ) -> Message:
        """
        Send an encrypted image.
        
        Args:
            to: Recipient user ID
            image_path: Path to image file (mutually exclusive with image_data)
            image_data: Image bytes (mutually exclusive with image_path)
            caption: Optional caption for the image
            max_size: Maximum file size in bytes (default: 5MB)
            
        Returns:
            Message object
            
        Raises:
            ValueError: If neither or both image_path and image_data provided
            WhatsAppClientError: If file too large or send fails
            
        Example:
            >>> # Send from file
            >>> msg = await client.send_image(
            ...     to="user_123",
            ...     image_path="photo.jpg",
            ...     caption="Check this out!"
            ... )
            >>> 
            >>> # Send from bytes
            >>> with open("photo.jpg", "rb") as f:
            ...     data = f.read()
            >>> await client.send_image(to="user_123", image_data=data)
        """
        import base64
        from pathlib import Path
        
        # Validate inputs
        if image_path is None and image_data is None:
            raise ValueError("Either image_path or image_data must be provided")
        if image_path is not None and image_data is not None:
            raise ValueError("Cannot specify both image_path and image_data")
        
        # Load image data from file if path provided
        if image_path:
            path = Path(image_path)
            if not path.exists():
                raise WhatsAppClientError(f"Image file not found: {image_path}")
            
            with open(path, "rb") as f:
                image_data = f.read()
        
        # Check size limit
        if len(image_data) > max_size:
            size_mb = len(image_data) / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            raise WhatsAppClientError(
                f"Image too large: {size_mb:.2f}MB (max: {max_mb:.2f}MB)"
            )
        
        # Base64 encode image data
        encoded_data = base64.b64encode(image_data).decode('utf-8')
        
        # Encrypt the base64 data if encryption enabled
        content_to_send = encoded_data
        if self._session_manager:
            try:
                await self.ensure_session(to)
                content_to_send = self._session_manager.encrypt_message(to, encoded_data)
            except Exception as e:
                logger.error(f"Image encryption failed: {e}")
                raise WhatsAppClientError(f"Image encryption failed: {e}")
        
        # Create message
        message = Message(
            id=str(uuid.uuid4()),
            from_user=self.user_id,
            to=to,
            content=caption or "",
            type="image",
            timestamp=int(time.time() * 1000),
            status="sent",
            image_data=content_to_send,
        )
        
        # Save to storage
        if self._message_storage:
            self._message_storage.save_message(message)
        
        # Send via WebSocket
        if self.is_connected:
            await self._ws.send_message(
                to=to,
                content=content_to_send,
                type="image",
            )
        
        logger.info(f"Sent image to {to} ({len(image_data)} bytes)")
        return message
    
    async def save_image(
        self,
        message: Message,
        path: str,
        decrypt: bool = True,
    ) -> None:
        """
        Save image from message to file.
        
        Args:
            message: Message object with image data
            path: Destination file path
            decrypt: Whether to decrypt the image (default: True)
            
        Raises:
            ValueError: If message is not an image type
            WhatsAppClientError: If save fails
            
        Example:
            >>> @client.on_message
            >>> async def handle_message(msg):
            ...     if msg.type == "image":
            ...         await client.save_image(
            ...             message=msg,
            ...             path=f"downloads/{msg.id}.jpg"
            ...         )
        """
        import base64
        from pathlib import Path
        
        if message.type != "image":
            raise ValueError("Message is not an image type")
        
        if not message.image_data:
            raise ValueError("Message has no image data")
        
        # Decrypt if needed
        image_data_b64 = message.image_data
        if decrypt and self._session_manager:
            try:
                image_data_b64 = self._session_manager.decrypt_message(
                    message.from_user,
                    message.image_data
                )
            except Exception as e:
                logger.error(f"Image decryption failed: {e}")
                raise WhatsAppClientError(f"Image decryption failed: {e}")
        
        # Decode base64
        try:
            image_bytes = base64.b64decode(image_data_b64)
        except Exception as e:
            raise WhatsAppClientError(f"Failed to decode image data: {e}")
        
        # Create parent directory if needed
        dest_path = Path(path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        try:
            with open(dest_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Saved image to {path} ({len(image_bytes)} bytes)")
        except Exception as e:
            raise WhatsAppClientError(f"Failed to save image: {e}")
    
    def decode_image(self, image_data: str, decrypt: bool = True, from_user: Optional[str] = None) -> bytes:
        """
        Decode and optionally decrypt image data.
        
        Args:
            image_data: Base64 encoded (and possibly encrypted) image data
            decrypt: Whether to decrypt the data (default: True)
            from_user: User ID who sent the image (required if decrypt=True)
            
        Returns:
            Image bytes
            
        Raises:
            ValueError: If decrypt=True but from_user not provided
            WhatsAppClientError: If decoding/decryption fails
            
        Example:
            >>> @client.on_message
            >>> async def handle_message(msg):
            ...     if msg.type == "image":
            ...         image_bytes = client.decode_image(
            ...             image_data=msg.image_data,
            ...             from_user=msg.from_user
            ...         )
        """
        import base64
        
        # Decrypt if needed
        data_b64 = image_data
        if decrypt:
            if not from_user:
                raise ValueError("from_user required when decrypt=True")
            
            if self._session_manager:
                try:
                    data_b64 = self._session_manager.decrypt_message(from_user, image_data)
                except Exception as e:
                    logger.error(f"Image decryption failed: {e}")
                    raise WhatsAppClientError(f"Image decryption failed: {e}")
        
        # Decode base64
        try:
            return base64.b64decode(data_b64)
        except Exception as e:
            raise WhatsAppClientError(f"Failed to decode image data: {e}")
    
    def on_message(self, handler: Callable) -> Callable:
        """
        Register handler for incoming messages.
        
        Args:
            handler: Async function to handle messages
            
        Returns:
            The handler (for decorator usage)
            
        Example:
            @client.on_message
            async def handle_message(msg):
                print(f"{msg.from_user}: {msg.content}")
        """
        self._message_handlers.append(handler)
        return handler
    
    def on_typing(self, handler: Callable) -> Callable:
        """Register handler for typing indicators."""
        self._typing_handlers.append(handler)
        return handler
    
    def on_status(self, handler: Callable) -> Callable:
        """Register handler for message status updates."""
        self._status_handlers.append(handler)
        return handler
    
    def on_presence(self, handler: Callable) -> Callable:
        """Register handler for presence updates."""
        self._presence_handlers.append(handler)
        return handler
    
    async def send_typing(self, to: str, typing: bool = True) -> None:
        """
        Send typing indicator.
        
        Args:
            to: User to send typing indicator to
            typing: True if typing, False if stopped
        """
        if self._ws:
            await self._ws.send_typing(to, typing)
    
    async def mark_as_read(
        self, 
        peer_id: str, 
        message_ids: List[str]
    ) -> None:
        """
        Mark messages as read and send read receipts.
        
        Args:
            peer_id: User ID of the conversation peer
            message_ids: List of message IDs to mark as read (max 100)
            
        Raises:
            ValueError: If message_ids list is empty or too large
            
        Example:
            >>> @client.on_message
            >>> async def handle_message(message):
            ...     await client.mark_as_read(
            ...         peer_id=message.from_user,
            ...         message_ids=[message.id]
            ...     )
        """
        if not message_ids:
            raise ValueError("message_ids cannot be empty")
        
        if len(message_ids) > 100:
            raise ValueError("Cannot mark more than 100 messages at once")
        
        # Update local storage
        if self._message_storage:
            for message_id in message_ids:
                self._message_storage.update_message_status(message_id, "read")
        
        # Send read receipts via WebSocket
        if self._ws:
            for message_id in message_ids:
                await self._ws.send_status_update(message_id, "read")
    
    def on_message_status(self, handler: Callable) -> Callable:
        """
        Register handler for message status updates.
        
        This is an alias for on_status() for better API clarity.
        
        Args:
            handler: Async function to handle status updates
            
        Example:
            >>> @client.on_message_status
            >>> async def handle_status(data):
            ...     print(f"Message {data['messageId']}: {data['status']}")
        """
        return self.on_status(handler)
    
    def get_online_users(self) -> List[str]:
        """
        Get list of currently online users.
        
        Returns:
            List of user IDs that are currently online
            
        Example:
            >>> online = client.get_online_users()
            >>> print(f"Online users: {len(online)}")
        """
        return [user_id for user_id, online in self._online_users.items() if online]
    
    def is_user_online(self, user_id: str) -> bool:
        """
        Check if a specific user is online.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is online, False otherwise
            
        Example:
            >>> if client.is_user_online("user_123"):
            ...     print("User is online!")
        """
        return self._online_users.get(user_id, False)
    
    def get_all_presence(self) -> Dict[str, bool]:
        """
        Get presence status for all tracked users.
        
        Returns:
            Dictionary mapping user IDs to online status
            
        Example:
            >>> presence = client.get_all_presence()
            >>> for user_id, online in presence.items():
            ...     print(f"{user_id}: {'online' if online else 'offline'}")
        """
        return self._online_users.copy()

    # Group Chat Methods

    async def create_group(
        self,
        name: str,
        description: Optional[str] = None,
        member_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new group chat.

        Args:
            name: Group name
            description: Optional group description
            member_ids: List of member IDs to add (excluding creator)

        Returns:
            Dict with group data (id, name, description, owner_id, members)

        Raises:
            WhatsAppClientError: If group creation fails

        Example:
            >>> group = await client.create_group(
            ...     name="Dev Team",
            ...     description="Developers only",
            ...     member_ids=["user1", "user2"]
            ... )
            >>> print(f"Group {group['id']}: {group['name']}")
        """
        if not self._group_storage:
            raise WhatsAppClientError("Group storage not initialized")

        try:
            group = self._group_storage.create_group(name, description, member_ids)
            logger.info(f"Created group {group['id']}: {name}")
            return group
        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            raise WhatsAppClientError(f"Failed to create group: {e}")

    async def get_groups(self) -> List[Dict[str, Any]]:
        """
        Get all groups current user is member of.

        Returns:
            List of group dicts

        Example:
            >>> groups = await client.get_groups()
            >>> for group in groups:
            ...     print(f"{group['name']}: {len(group['members'])} members")
        """
        if not self._group_storage:
            return []

        return self._group_storage.get_groups()

    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get group details.

        Args:
            group_id: Group ID

        Returns:
            Dict with group metadata or None

        Example:
            >>> group = await client.get_group("group_123")
            >>> if group:
            ...     print(f"{group['name']}: {len(group['members'])} members")
        """
        if not self._group_storage:
            return None

        return self._group_storage.get_group(group_id)

    async def send_group_message(
        self,
        group_id: str,
        content: str,
    ) -> bool:
        """
        Send message to group.

        Args:
            group_id: Group ID
            content: Message content

        Returns:
            True if successful

        Raises:
            WhatsAppClientError: If not a group member or send fails

        Example:
            >>> success = await client.send_group_message(
            ...     group_id="group_123",
            ...     content="Hello everyone!"
            ... )
        """
        if not self._group_storage:
            raise WhatsAppClientError("Group storage not initialized")

        if not self._group_storage.is_member(group_id, self.user_id):
            raise WhatsAppClientError("Not a member of this group")

        try:
            # Save to local storage
            self._group_storage.save_group_message(group_id, self.user_id, content)

            # Send to server via WebSocket
            if self._ws and self._ws.is_connected:
                await self._ws.send({
                    "type": "group_message",
                    "groupId": group_id,
                    "content": content,
                })

            logger.info(f"Sent group message to {group_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send group message: {e}")
            raise WhatsAppClientError(f"Failed to send group message: {e}")

    async def get_group_messages(
        self,
        group_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get group message history.

        Args:
            group_id: Group ID
            limit: Max messages to retrieve (default: 50)

        Returns:
            List of message dicts

        Example:
            >>> messages = await client.get_group_messages("group_123")
            >>> for msg in messages:
            ...     print(f"{msg['from_user']}: {msg['content']}")
        """
        if not self._group_storage:
            return []

        return self._group_storage.get_group_messages(group_id, limit)

    async def add_group_member(self, group_id: str, member_id: str) -> bool:
        """
        Add member to group (owner only).

        Args:
            group_id: Group ID
            member_id: User ID to add

        Returns:
            True if successful

        Raises:
            WhatsAppClientError: If not owner or operation fails

        Example:
            >>> success = await client.add_group_member("group_123", "user_new")
        """
        if not self._group_storage:
            raise WhatsAppClientError("Group storage not initialized")

        if not self._group_storage.is_owner(group_id, self.user_id):
            raise WhatsAppClientError("Only group owner can add members")

        try:
            result = self._group_storage.add_member(group_id, member_id)
            logger.info(f"Added {member_id} to group {group_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            raise WhatsAppClientError(f"Failed to add member: {e}")

    async def remove_group_member(self, group_id: str, member_id: str) -> bool:
        """
        Remove member from group (owner only).

        Args:
            group_id: Group ID
            member_id: User ID to remove

        Returns:
            True if successful

        Raises:
            WhatsAppClientError: If not owner or operation fails

        Example:
            >>> success = await client.remove_group_member("group_123", "user_old")
        """
        if not self._group_storage:
            raise WhatsAppClientError("Group storage not initialized")

        if not self._group_storage.is_owner(group_id, self.user_id):
            raise WhatsAppClientError("Only group owner can remove members")

        try:
            result = self._group_storage.remove_member(group_id, member_id)
            logger.info(f"Removed {member_id} from group {group_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            raise WhatsAppClientError(f"Failed to remove member: {e}")

    async def leave_group(self, group_id: str) -> bool:
        """
        Leave a group.

        Args:
            group_id: Group ID

        Returns:
            True if successful

        Example:
            >>> success = await client.leave_group("group_123")
        """
        if not self._group_storage:
            raise WhatsAppClientError("Group storage not initialized")

        return self._group_storage.remove_member(group_id, self.user_id)

    def on_group_message(self, handler: Callable) -> Callable:
        """
        Register handler for group messages.

        Args:
            handler: Async function to handle group messages

        Returns:
            The handler function (for decorator support)

        Example:
            >>> @client.on_group_message
            ... async def handle_group_msg(message):
            ...     print(f"[{message['group_id']}] {message['from_user']}: {message['content']}")
        """
        self._group_message_handlers.append(handler)
        logger.debug(f"Registered group message handler: {handler.__name__}")
        return handler

    async def logout(self) -> None:
        """
        Logout current user and cleanup resources.

        Example:
            >>> await client.logout()
        """
        # Disconnect WebSocket
        if self._ws:
            await self._ws.disconnect()
            self._ws = None
        
        await self._auth.logout()
        self._rest.set_token(None)
        self._key_manager = None
        self._session_manager = None
        self._message_storage = None
        self._online_users.clear()  # Clear presence tracking
        logger.info("Logged out successfully")

    async def close(self) -> None:
        """
        Close client and cleanup all resources.

        This should be called when done using the client to ensure
        proper cleanup of network connections and resources.
        """
        if self._closed:
            return

        logger.info("Closing WhatsAppClient")

        # Close WebSocket
        if self._ws:
            await self._ws.close()
            self._ws = None

        # Logout if authenticated
        if self.is_authenticated:
            await self.logout()

        # Close HTTP session
        await self._rest.close()

        self._closed = True
        logger.info("WhatsAppClient closed")

    async def __aenter__(self) -> "WhatsAppClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Exit async context manager and cleanup."""
        await self.close()

