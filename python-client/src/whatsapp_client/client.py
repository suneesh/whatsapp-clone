"""Main WhatsApp Client class."""

import logging
from typing import Optional

from .auth import AuthManager
from .transport import RestClient
from .crypto import KeyManager, SessionManager
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

        # State
        self._closed = False

    @property
    def user(self) -> Optional[User]:
        """Get current authenticated user."""
        return self._auth.user

    @property
    def user_id(self) -> Optional[str]:
        """Get current user ID."""
        return self._auth.user_id

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._auth.is_authenticated

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
        self._rest.set_user_id(self.user_id)

        # Initialize cryptographic keys
        logger.info("Initializing cryptographic keys...")
        self._key_manager = KeyManager(self.user_id, self.storage_path)
        await self._key_manager.initialize()

        # Upload public keys to server
        await self._upload_public_keys()

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
        self._rest.set_user_id(self.user_id)

        # Initialize cryptographic keys
        logger.info("Initializing cryptographic keys...")
        self._key_manager = KeyManager(self.user_id, self.storage_path)
        await self._key_manager.initialize()

        # Initialize session manager
        self._session_manager = SessionManager(self.user_id, self.storage_path)

        # Upload public keys to server
        await self._upload_public_keys()

        logger.info(f"Login successful for user: {username}")
        return user

    async def _upload_public_keys(self) -> None:
        """Upload public key bundle to server."""
        if not self._key_manager:
            raise WhatsAppClientError("Key manager not initialized")

        logger.info("Uploading public key bundle to server...")

        bundle = self._key_manager.get_public_bundle()

        # Prepare upload data
        upload_data = {
            "identityKey": bundle.identity_key,
            "signingKey": bundle.signing_key,
            "fingerprint": bundle.fingerprint,
            "signedPrekey": bundle.signed_prekey,
            "oneTimePrekeys": bundle.one_time_prekeys,
        }

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
        identity_private_key = self._key_manager._identity_keypair.private_key
        
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
            
            # Parse response into PrekeyBundle
            bundle = PrekeyBundle(
                identity_key=response["identityKey"],
                signing_key=response["signingKey"],
                fingerprint=response["fingerprint"],
                signed_prekey=response["signedPrekey"],
                signature=response["signature"],
                one_time_prekeys=response.get("oneTimePrekeys", [])
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
        
        # Ensure session exists with recipient
        await self.ensure_session(to)
        
        # Encrypt message
        encrypted_content = self._session_manager.encrypt_message(to, content)
        
        # Send encrypted message to server
        message_data = {
            "to": to,
            "content": encrypted_content,
            "type": message_type,
        }
        
        try:
            response = await self._rest.post("/api/messages", data=message_data)
            
            if "error" in response:
                raise WhatsAppClientError(f"Failed to send message: {response['error']}")
            
            # Parse response into Message model
            message = Message(
                id=response["id"],
                from_user=response["from"],
                to=response["to"],
                content=content,  # Return decrypted content
                timestamp=response["timestamp"],
                status=response.get("status", "sent"),
                type=response.get("type", "text"),
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

    async def logout(self) -> None:
        """
        Logout current user and cleanup resources.

        Example:
            >>> await client.logout()
        """
        await self._auth.logout()
        self._rest.set_user_id(None)
        self._key_manager = None
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

