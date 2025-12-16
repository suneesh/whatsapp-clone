"""Tests for messaging functionality (US6)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import time
import uuid

from whatsapp_client import WhatsAppClient
from whatsapp_client.transport import WebSocketClient, ConnectionState
from whatsapp_client.storage import MessageStorage
from whatsapp_client.models import Message
from whatsapp_client.exceptions import WhatsAppClientError


@pytest.fixture
def temp_storage(tmp_path):
    """Temporary storage directory."""
    return str(tmp_path / "test_storage")


@pytest.fixture
def message_storage(temp_storage):
    """Create message storage instance."""
    return MessageStorage(temp_storage, "test_user_id")


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection initialization."""
    ws = WebSocketClient(
        server_url="http://localhost:8787",
        user_id="test_user",
        auto_reconnect=False,
    )
    
    assert ws.state == ConnectionState.DISCONNECTED
    assert not ws.is_connected
    assert ws.user_id == "test_user"
    
    await ws.close()


@pytest.mark.asyncio
async def test_websocket_message_sending():
    """Test sending messages via WebSocket."""
    ws = WebSocketClient(
        server_url="http://localhost:8787",
        user_id="test_user",
        auto_reconnect=False,
    )
    
    # Mock the WebSocket connection
    mock_ws = AsyncMock()
    ws._ws = mock_ws
    ws._state = ConnectionState.CONNECTED
    
    # Send a message
    await ws.send_message("recipient_id", "Hello, World!", "text")
    
    # Verify message was sent
    assert mock_ws.send.called
    call_args = mock_ws.send.call_args[0][0]
    assert "Hello, World!" in call_args
    assert "recipient_id" in call_args
    
    await ws.close()


@pytest.mark.asyncio
async def test_websocket_event_handlers():
    """Test WebSocket event handler registration."""
    ws = WebSocketClient(
        server_url="http://localhost:8787",
        user_id="test_user",
    )
    
    messages_received = []
    
    @ws.on_message
    async def handle_message(msg):
        messages_received.append(msg)
    
    # Simulate incoming message
    await ws._route_message({
        "type": "message",
        "from": "alice",
        "content": "Hello",
    })
    
    assert len(messages_received) == 1
    assert messages_received[0]["from"] == "alice"
    
    await ws.close()


def test_message_storage_initialization(message_storage):
    """Test message storage initialization."""
    assert message_storage.user_id == "test_user_id"
    assert message_storage.db_path.exists()


def test_save_and_retrieve_messages(message_storage):
    """Test saving and retrieving messages."""
    # Create test messages
    msg1 = Message(
        id="msg1",
        from_user="test_user_id",
        to="alice",
        content="Hello Alice!",
        type="text",
        timestamp=1000,
        status="sent",
    )
    
    msg2 = Message(
        id="msg2",
        from_user="alice",
        to="test_user_id",
        content="Hi there!",
        type="text",
        timestamp=2000,
        status="delivered",
    )
    
    # Save messages
    message_storage.save_message(msg1)
    message_storage.save_message(msg2)
    
    # Retrieve messages
    messages = message_storage.get_messages("alice", limit=10)
    
    assert len(messages) == 2
    assert messages[0].id == "msg1"  # Chronological order
    assert messages[1].id == "msg2"


def test_message_deduplication(message_storage):
    """Test that duplicate messages are not saved."""
    msg = Message(
        id="msg1",
        from_user="test_user_id",
        to="alice",
        content="Hello",
        type="text",
        timestamp=1000,
        status="sent",
    )
    
    # Save same message twice
    message_storage.save_message(msg)
    message_storage.save_message(msg)
    
    # Should only have one message
    messages = message_storage.get_messages("alice")
    assert len(messages) == 1


def test_update_message_status(message_storage):
    """Test updating message status."""
    msg = Message(
        id="msg1",
        from_user="test_user_id",
        to="alice",
        content="Hello",
        type="text",
        timestamp=1000,
        status="sent",
    )
    
    message_storage.save_message(msg)
    message_storage.update_message_status("msg1", "delivered")
    
    messages = message_storage.get_messages("alice")
    assert messages[0].status == "delivered"


def test_search_messages(message_storage):
    """Test message search functionality."""
    messages = [
        Message(
            id=f"msg{i}",
            from_user="test_user_id",
            to="alice",
            content=f"Message {i}" if i % 2 == 0 else "Something else",
            type="text",
            timestamp=1000 + i,
            status="sent",
        )
        for i in range(5)
    ]
    
    for msg in messages:
        message_storage.save_message(msg)
    
    # Search for "Message"
    results = message_storage.search_messages("Message", peer_id="alice")
    assert len(results) == 3  # Messages 0, 2, 4


def test_get_recent_conversations(message_storage):
    """Test getting recent conversations."""
    # Add messages with different peers
    peers = ["alice", "bob", "charlie"]
    
    for i, peer in enumerate(peers):
        msg = Message(
            id=f"msg_{peer}",
            from_user="test_user_id",
            to=peer,
            content=f"Hello {peer}",
            type="text",
            timestamp=1000 + i * 100,
            status="sent",
        )
        message_storage.save_message(msg)
    
    conversations = message_storage.get_recent_conversations(limit=5)
    
    assert len(conversations) == 3
    # Most recent should be charlie
    assert conversations[0]["peer_id"] == "charlie"


def test_delete_conversation(message_storage):
    """Test deleting a conversation."""
    # Add messages
    for i in range(3):
        msg = Message(
            id=f"msg{i}",
            from_user="test_user_id" if i % 2 == 0 else "alice",
            to="alice" if i % 2 == 0 else "test_user_id",
            content=f"Message {i}",
            type="text",
            timestamp=1000 + i,
            status="sent",
        )
        message_storage.save_message(msg)
    
    # Delete conversation
    deleted = message_storage.delete_conversation("alice")
    assert deleted == 3
    
    # Verify deletion
    messages = message_storage.get_messages("alice")
    assert len(messages) == 0


def test_message_storage_stats(message_storage):
    """Test storage statistics."""
    # Add test messages
    messages = [
        Message(
            id=f"msg{i}",
            from_user="test_user_id" if i < 3 else f"user{i}",
            to=f"user{i}" if i < 3 else "test_user_id",
            content="E2EE:encrypted" if i % 2 == 0 else "Plain text",
            type="text",
            timestamp=1000 + i,
            status="sent",
        )
        for i in range(6)
    ]
    
    for msg in messages:
        message_storage.save_message(msg)
    
    stats = message_storage.get_stats()
    
    assert stats["total_messages"] == 6
    assert stats["messages_sent"] == 3
    assert stats["messages_received"] == 3
    assert stats["encrypted_messages"] == 3  # Even-numbered messages
    assert stats["unique_peers"] == 6


@pytest.mark.asyncio
async def test_client_message_sending_integration(temp_storage):
    """Test sending messages through WhatsAppClient."""
    client = WhatsAppClient(
        server_url="http://localhost:8787",
        storage_path=temp_storage,
        auto_connect=False,  # Don't auto-connect for testing
    )
    
    # Mock login
    mock_user = {
        "id": "test_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
    
    # Mock WebSocket connection
    mock_ws = AsyncMock()
    client._ws = mock_ws
    mock_ws.is_connected = True
    mock_ws.send_message = AsyncMock()
    
    # Send message
    message = await client.send_message_realtime(
        to="bob_user_id",
        content="Hello Bob!",
        encrypt=False,  # Skip encryption for this test
    )
    
    assert message.to == "bob_user_id"
    assert message.content == "Hello Bob!"
    assert message.status == "sent"
    assert mock_ws.send_message.called
    
    await client.close()


@pytest.mark.asyncio
async def test_client_message_receiving(temp_storage):
    """Test receiving messages through WhatsAppClient."""
    client = WhatsAppClient(
        server_url="http://localhost:8787",
        storage_path=temp_storage,
        auto_connect=False,
    )
    
    # Mock login
    mock_user = {
        "id": "test_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
    
    # Register message handler
    received_messages = []
    
    @client.on_message
    async def handle_message(msg):
        received_messages.append(msg)
    
    # Simulate incoming message
    await client._handle_incoming_message({
        "id": "msg123",
        "from": "bob_user_id",
        "content": "Hello Alice!",
        "type": "text",
        "timestamp": int(time.time() * 1000),
    })
    
    # Verify message was received
    assert len(received_messages) == 1
    assert received_messages[0].from_user == "bob_user_id"
    assert received_messages[0].content == "Hello Alice!"
    
    # Verify message was saved
    messages = await client.get_messages("bob_user_id")
    assert len(messages) == 1
    
    await client.close()


@pytest.mark.asyncio
async def test_client_get_message_history(temp_storage):
    """Test retrieving message history."""
    client = WhatsAppClient(
        server_url="http://localhost:8787",
        storage_path=temp_storage,
        auto_connect=False,
    )
    
    # Mock login
    mock_user = {
        "id": "test_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
    
    # Add some test messages directly to storage
    for i in range(5):
        msg = Message(
            id=f"msg{i}",
            from_user="test_user_id" if i % 2 == 0 else "bob_user_id",
            to="bob_user_id" if i % 2 == 0 else "test_user_id",
            content=f"Message {i}",
            type="text",
            timestamp=1000 + i,
            status="sent",
        )
        client._message_storage.save_message(msg)
    
    # Get message history
    messages = await client.get_messages("bob_user_id", limit=10)
    
    assert len(messages) == 5
    assert messages[0].id == "msg0"  # Chronological order
    
    await client.close()


@pytest.mark.asyncio
async def test_client_search_messages(temp_storage):
    """Test searching messages."""
    client = WhatsAppClient(
        server_url="http://localhost:8787",
        storage_path=temp_storage,
        auto_connect=False,
    )
    
    # Mock login
    mock_user = {
        "id": "test_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
    
    # Add test messages
    messages_data = [
        ("important", "This is important"),
        ("random", "Random message"),
        ("important", "Another important one"),
    ]
    
    for i, (tag, content) in enumerate(messages_data):
        msg = Message(
            id=f"msg{i}",
            from_user="bob_user_id",
            to="test_user_id",
            content=content,
            type="text",
            timestamp=1000 + i,
            status="delivered",
        )
        client._message_storage.save_message(msg)
    
    # Search for "important"
    results = await client.search_messages("important")
    
    assert len(results) == 2
    
    await client.close()


@pytest.mark.asyncio
async def test_typing_indicator(temp_storage):
    """Test sending typing indicators."""
    client = WhatsAppClient(
        server_url="http://localhost:8787",
        storage_path=temp_storage,
        auto_connect=False,
    )
    
    # Mock login
    mock_user = {
        "id": "test_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
    
    # Mock WebSocket
    mock_ws = AsyncMock()
    client._ws = mock_ws
    
    # Send typing indicator
    await client.send_typing("bob_user_id", typing=True)
    
    assert mock_ws.send_typing.called
    assert mock_ws.send_typing.call_args[0][0] == "bob_user_id"
    assert mock_ws.send_typing.call_args[0][1] == True
    
    await client.close()


@pytest.mark.asyncio
async def test_connection_properties(temp_storage):
    """Test connection state properties."""
    client = WhatsAppClient(
        server_url="http://localhost:8787",
        storage_path=temp_storage,
        auto_connect=False,
    )
    
    # Initially not connected
    assert not client.is_connected
    assert client.connection_state is None
    
    # Mock login
    mock_user = {
        "id": "test_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
    
    # Still not connected (auto_connect=False)
    assert not client.is_connected
    
    await client.close()
