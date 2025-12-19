"""WebSocket client for real-time communication."""

import asyncio
import json
import logging
from typing import Optional, Callable, Any, Dict
from enum import Enum

import websockets
from websockets.client import WebSocketClientProtocol

from ..exceptions import WhatsAppClientError

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"


class WebSocketClient:
    """
    WebSocket client for real-time messaging.
    
    Handles connection management, message routing, and automatic reconnection.
    """
    
    def __init__(
        self,
        server_url: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        auto_reconnect: bool = True,
    ):
        """
        Initialize WebSocket client.
        
        Args:
            server_url: Base server URL (http/https)
            user_id: User ID for authentication
            username: Username for authentication
            auto_reconnect: Enable automatic reconnection on disconnect
        """
        # Convert http/https to ws/wss
        ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_url = f"{ws_url}/ws"
        self.user_id = user_id
        self.username = username
        self.auto_reconnect = auto_reconnect
        
        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self._ws: Optional[WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self._message_handlers: list[Callable] = []
        self._typing_handlers: list[Callable] = []
        self._status_handlers: list[Callable] = []
        self._presence_handlers: list[Callable] = []
        self._connection_handlers: list[Callable] = []
        
        # Reconnection config
        self._reconnect_delays = [3, 6, 12, 24, 60]  # Exponential backoff
        self._current_reconnect_attempt = 0
        self._max_reconnect_attempts = 10
        
        # State
        self._closed = False
        
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._state == ConnectionState.CONNECTED and self._ws is not None
    
    async def connect(self) -> None:
        """
        Connect to WebSocket server.
        
        Raises:
            WhatsAppClientError: If connection fails
        """
        if self._closed:
            raise WhatsAppClientError("WebSocket client is closed")
        
        if self.is_connected:
            logger.debug("Already connected to WebSocket")
            return
        
        self._state = ConnectionState.CONNECTING
        logger.info(f"Connecting to WebSocket: {self.ws_url}")
        
        try:
            # Connect to WebSocket
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
            )
            
            # Send authentication message if user_id is set
            if self.user_id:
                await self._send_auth()
            
            self._state = ConnectionState.CONNECTED
            self._current_reconnect_attempt = 0
            logger.info("WebSocket connected successfully")
            
            # Notify connection handlers
            await self._notify_connection_handlers(True)
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            logger.error(f"Failed to connect to WebSocket: {e}")
            
            # Attempt reconnection if enabled
            if self.auto_reconnect and not self._closed:
                await self._schedule_reconnect()
            else:
                raise WhatsAppClientError(f"WebSocket connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        logger.info("Disconnecting from WebSocket")
        
        # Cancel tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        
        # Close WebSocket
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self._state = ConnectionState.DISCONNECTED
        
        # Notify connection handlers
        await self._notify_connection_handlers(False)
        
        logger.info("WebSocket disconnected")
    
    async def close(self) -> None:
        """Close WebSocket client permanently."""
        self._closed = True
        self._state = ConnectionState.CLOSED
        await self.disconnect()
    
    async def send_message(self, to: str, content: str, type: str = "text") -> None:
        """
        Send a message via WebSocket.
        
        Args:
            to: Recipient user ID
            content: Message content (encrypted or plain)
            type: Message type (default: "text")
            
        Raises:
            WhatsAppClientError: If not connected
        """
        if not self.is_connected:
            raise WhatsAppClientError("Not connected to WebSocket")
        
        message = {
            "type": "message",
            "to": to,
            "content": content,
            "messageType": type,
        }
        
        await self._send(message)
    
    async def send_typing(self, to: str, typing: bool) -> None:
        """
        Send typing indicator.
        
        Args:
            to: User to send typing indicator to
            typing: True if typing, False if stopped
        """
        if not self.is_connected:
            return
        
        message = {
            "type": "typing",
            "to": to,
            "typing": typing,
        }
        
        await self._send(message)
    
    async def send_status_update(self, message_id: str, status: str) -> None:
        """
        Send message status update.
        
        Args:
            message_id: Message ID
            status: Status (delivered, read)
        """
        if not self.is_connected:
            return
        
        message = {
            "type": "status",
            "messageId": message_id,
            "status": status,
        }
        
        await self._send(message)
    
    def on_message(self, handler: Callable) -> Callable:
        """
        Register a message handler.
        
        Args:
            handler: Async function to handle messages
            
        Returns:
            The handler (for decorator usage)
            
        Example:
            @client.on_message
            async def handle_message(msg):
                print(f"Got message: {msg}")
        """
        self._message_handlers.append(handler)
        return handler
    
    def on_typing(self, handler: Callable) -> Callable:
        """Register a typing indicator handler."""
        self._typing_handlers.append(handler)
        return handler
    
    def on_status(self, handler: Callable) -> Callable:
        """Register a status update handler."""
        self._status_handlers.append(handler)
        return handler
    
    def on_presence(self, handler: Callable) -> Callable:
        """Register a presence update handler."""
        self._presence_handlers.append(handler)
        return handler
    
    def on_connection(self, handler: Callable) -> Callable:
        """Register a connection state change handler."""
        self._connection_handlers.append(handler)
        return handler
    
    async def _send_auth(self) -> None:
        """Send authentication message."""
        auth_msg = {
            "type": "auth",
            "payload": {
                "userId": self.user_id,
                "username": self.username,
            },
        }
        await self._send(auth_msg)
        logger.debug(f"Sent auth message for user {self.user_id} ({self.username})")
    
    async def _send(self, message: Dict[str, Any]) -> None:
        """
        Send a message to WebSocket.
        
        Args:
            message: Message dictionary
        """
        if not self._ws:
            raise WhatsAppClientError("WebSocket not connected")
        
        try:
            data = json.dumps(message)
            await self._ws.send(data)
            logger.debug(f"Sent WebSocket message: {message.get('type')}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise WhatsAppClientError(f"Failed to send message: {e}")
    
    async def _receive_loop(self) -> None:
        """Receive and route incoming messages."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._route_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            # Connection lost - attempt reconnect
            if not self._closed and self.auto_reconnect:
                self._state = ConnectionState.DISCONNECTED
                await self._notify_connection_handlers(False)
                await self._schedule_reconnect()
    
    async def _route_message(self, data: Dict[str, Any]) -> None:
        """
        Route incoming message to appropriate handlers.
        
        Args:
            data: Parsed message data
        """
        msg_type = data.get("type")
        
        if msg_type == "message":
            for handler in self._message_handlers:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
        
        elif msg_type == "typing":
            for handler in self._typing_handlers:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Typing handler error: {e}")
        
        elif msg_type == "status":
            for handler in self._status_handlers:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Status handler error: {e}")
        
        elif msg_type == "presence":
            for handler in self._presence_handlers:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Presence handler error: {e}")
        
        else:
            logger.debug(f"Unknown message type: {msg_type}")
    
    async def _schedule_reconnect(self) -> None:
        """Schedule reconnection with exponential backoff."""
        if self._reconnect_task and not self._reconnect_task.done():
            return
        
        self._reconnect_task = asyncio.create_task(self._reconnect())
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        self._state = ConnectionState.RECONNECTING
        
        while self._current_reconnect_attempt < self._max_reconnect_attempts:
            # Calculate delay
            delay_index = min(self._current_reconnect_attempt, len(self._reconnect_delays) - 1)
            delay = self._reconnect_delays[delay_index]
            
            logger.info(f"Reconnecting in {delay}s (attempt {self._current_reconnect_attempt + 1}/{self._max_reconnect_attempts})")
            
            try:
                await asyncio.sleep(delay)
                
                if self._closed:
                    break
                
                # Attempt connection
                await self.connect()
                
                # Success - exit reconnect loop
                logger.info("Reconnection successful")
                return
                
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                self._current_reconnect_attempt += 1
        
        # Max attempts reached
        logger.error("Max reconnection attempts reached, giving up")
        self._state = ConnectionState.DISCONNECTED
    
    async def _notify_connection_handlers(self, connected: bool) -> None:
        """
        Notify connection state handlers.
        
        Args:
            connected: True if connected, False if disconnected
        """
        for handler in self._connection_handlers:
            try:
                await handler(connected)
            except Exception as e:
                logger.error(f"Connection handler error: {e}")
