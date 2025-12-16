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

        # State
        self._closed = False
        self._message_handlers: List[Callable] = []
        self._typing_handlers: List[Callable] = []
        self._status_handlers: List[Callable] = []
        self._presence_handlers: List[Callable] = []
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
        
        # Initialize message storage
        self._message_storage = MessageStorage(self.storage_path, self.user_id)

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
    
    async def _connect_websocket(self) -> None:
        """Initialize and connect WebSocket client."""
        if not self.user_id:
            raise WhatsAppClientError("Not authenticated")
        
        logger.info("Connecting to WebSocket...")
        self._ws = WebSocketClient(
            server_url=self.server_url,
            user_id=self.user_id,
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
            # Create Message object
            message = Message(
                id=data.get("id", str(uuid.uuid4())),
                from_user=data["from"],
                to=self.user_id,
                content=data["content"],
                type=data.get("type", "text"),
                timestamp=data.get("timestamp", int(time.time() * 1000)),
                status="delivered",
            )
            
            # Decrypt if encrypted
            if message.content.startswith("E2EE:"):
                try:
                    message.content = self.decrypt_message(message.from_user, message.content)
                except Exception as e:
                    logger.error(f"Failed to decrypt message: {e}")
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
        self._rest.set_user_id(None)
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

