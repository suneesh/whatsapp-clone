"""Main WhatsApp Client class."""

import logging
from typing import Optional

from .auth import AuthManager
from .transport import RestClient
from .crypto import KeyManager
from .models import User
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

