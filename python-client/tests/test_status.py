"""Tests for US9: Message Status Tracking and Read Receipts."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from whatsapp_client import WhatsAppClient
from whatsapp_client.transport import WebSocketClient
from whatsapp_client.storage import MessageStorage
from whatsapp_client.models import Message


class TestMessageStatusTracking:
    """Test message status tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_status_update_handling(self):
        """Test handling status updates from WebSocket."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        # Simulate status update
        await client._handle_status({
            "messageId": "msg_456",
            "status": "delivered"
        })
        
        # Verify storage was updated
        mock_storage.update_message_status.assert_called_once_with("msg_456", "delivered")
    
    @pytest.mark.asyncio
    async def test_status_handler_registration(self):
        """Test registering status event handler."""
        client = WhatsAppClient(server_url="http://test.com")
        
        handler_called = False
        received_data = None
        
        @client.on_status
        async def handle_status(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data
        
        # Verify handler registered
        assert len(client._status_handlers) == 1
        
        # Simulate status event
        await client._handle_status({"messageId": "msg_456", "status": "read"})
        
        # Verify handler was called
        assert handler_called
        assert received_data["messageId"] == "msg_456"
        assert received_data["status"] == "read"
    
    @pytest.mark.asyncio
    async def test_on_message_status_alias(self):
        """Test on_message_status is an alias for on_status."""
        client = WhatsAppClient(server_url="http://test.com")
        
        handler_called = False
        
        @client.on_message_status
        async def handle_status(data):
            nonlocal handler_called
            handler_called = True
        
        # Verify handler registered (should be in _status_handlers)
        assert len(client._status_handlers) == 1
        
        # Simulate status event
        await client._handle_status({"messageId": "msg_456", "status": "delivered"})
        
        # Verify handler was called
        assert handler_called
    
    @pytest.mark.asyncio
    async def test_status_progression(self):
        """Test status progresses from sent → delivered → read."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        status_updates = []
        
        @client.on_message_status
        async def handle_status(data):
            status_updates.append(data["status"])
        
        # Simulate status progression
        await client._handle_status({"messageId": "msg_456", "status": "delivered"})
        await client._handle_status({"messageId": "msg_456", "status": "read"})
        
        # Verify progression
        assert status_updates == ["delivered", "read"]
    
    @pytest.mark.asyncio
    async def test_multiple_status_handlers(self):
        """Test multiple status handlers."""
        client = WhatsAppClient(server_url="http://test.com")
        
        handler1_calls = []
        handler2_calls = []
        
        @client.on_message_status
        async def handler1(data):
            handler1_calls.append(data)
        
        @client.on_message_status
        async def handler2(data):
            handler2_calls.append(data)
        
        # Simulate status event
        await client._handle_status({"messageId": "msg_456", "status": "read"})
        
        # Both handlers should be called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1


class TestReadReceipts:
    """Test read receipt functionality."""
    
    @pytest.mark.asyncio
    async def test_mark_as_read_single_message(self):
        """Test marking a single message as read."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_status_update = AsyncMock()
        client._ws = mock_ws
        
        # Mark message as read
        await client.mark_as_read(
            peer_id="user_456",
            message_ids=["msg_789"]
        )
        
        # Verify storage updated
        mock_storage.update_message_status.assert_called_once_with("msg_789", "read")
        
        # Verify read receipt sent
        mock_ws.send_status_update.assert_called_once_with("msg_789", "read")
    
    @pytest.mark.asyncio
    async def test_mark_as_read_multiple_messages(self):
        """Test marking multiple messages as read (batch)."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_status_update = AsyncMock()
        client._ws = mock_ws
        
        # Mark multiple messages as read
        message_ids = ["msg_1", "msg_2", "msg_3"]
        await client.mark_as_read(
            peer_id="user_456",
            message_ids=message_ids
        )
        
        # Verify all messages updated in storage
        assert mock_storage.update_message_status.call_count == 3
        
        # Verify all read receipts sent
        assert mock_ws.send_status_update.call_count == 3
    
    @pytest.mark.asyncio
    async def test_mark_as_read_empty_list_error(self):
        """Test error when marking empty list as read."""
        client = WhatsAppClient(server_url="http://test.com")
        
        with pytest.raises(ValueError, match="message_ids cannot be empty"):
            await client.mark_as_read(peer_id="user_456", message_ids=[])
    
    @pytest.mark.asyncio
    async def test_mark_as_read_too_many_error(self):
        """Test error when marking too many messages at once."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Create list of 101 message IDs
        message_ids = [f"msg_{i}" for i in range(101)]
        
        with pytest.raises(ValueError, match="Cannot mark more than 100"):
            await client.mark_as_read(peer_id="user_456", message_ids=message_ids)
    
    @pytest.mark.asyncio
    async def test_mark_as_read_without_websocket(self):
        """Test marking as read when WebSocket not connected."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock message storage only
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        # No WebSocket
        client._ws = None
        
        # Should still update storage
        await client.mark_as_read(
            peer_id="user_456",
            message_ids=["msg_789"]
        )
        
        # Storage should be updated
        mock_storage.update_message_status.assert_called_once_with("msg_789", "read")
    
    @pytest.mark.asyncio
    async def test_mark_as_read_without_storage(self):
        """Test marking as read when storage not initialized."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock WebSocket only
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_status_update = AsyncMock()
        client._ws = mock_ws
        
        # No storage
        client._message_storage = None
        
        # Should still send read receipt
        await client.mark_as_read(
            peer_id="user_456",
            message_ids=["msg_789"]
        )
        
        # Read receipt should be sent
        mock_ws.send_status_update.assert_called_once_with("msg_789", "read")


class TestMessageStorage:
    """Test message storage status functionality."""
    
    @pytest.mark.asyncio
    async def test_get_message_by_id(self, tmp_path):
        """Test retrieving a message by ID."""
        storage = MessageStorage(user_id="user_123", storage_path=str(tmp_path))
        
        # Save a message
        message = Message(
            id="msg_456",
            from_user="user_123",
            to="user_789",
            content="Test message",
            type="text",
            timestamp=1234567890,
            status="sent",
        )
        storage.save_message(message)
        
        # Retrieve by ID
        retrieved = storage.get_message_by_id("msg_456")
        
        assert retrieved is not None
        assert retrieved.id == "msg_456"
        assert retrieved.content == "Test message"
        assert retrieved.status == "sent"
    
    @pytest.mark.asyncio
    async def test_get_message_by_id_not_found(self, tmp_path):
        """Test retrieving non-existent message returns None."""
        storage = MessageStorage(user_id="user_123", storage_path=str(tmp_path))
        
        # Try to get non-existent message
        retrieved = storage.get_message_by_id("non_existent")
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_update_message_status_persistence(self, tmp_path):
        """Test that status updates persist in database."""
        storage = MessageStorage(user_id="user_123", storage_path=str(tmp_path))
        
        # Save a message
        message = Message(
            id="msg_456",
            from_user="user_123",
            to="user_789",
            content="Test message",
            type="text",
            timestamp=1234567890,
            status="sent",
        )
        storage.save_message(message)
        
        # Update status
        storage.update_message_status("msg_456", "delivered")
        
        # Retrieve and verify
        retrieved = storage.get_message_by_id("msg_456")
        assert retrieved.status == "delivered"
        
        # Update again
        storage.update_message_status("msg_456", "read")
        
        # Verify again
        retrieved = storage.get_message_by_id("msg_456")
        assert retrieved.status == "read"


class TestIntegration:
    """Integration tests for status tracking."""
    
    @pytest.mark.asyncio
    async def test_send_and_receive_status_updates(self):
        """Test full flow of sending message and receiving status updates."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        status_updates = []
        
        @client.on_message_status
        async def handle_status(data):
            status_updates.append({
                "messageId": data["messageId"],
                "status": data["status"]
            })
        
        # Simulate receiving status updates
        await client._handle_status({"messageId": "msg_456", "status": "delivered"})
        await client._handle_status({"messageId": "msg_456", "status": "read"})
        
        # Verify status updates received
        assert len(status_updates) == 2
        assert status_updates[0]["status"] == "delivered"
        assert status_updates[1]["status"] == "read"
        
        # Verify storage updated
        assert mock_storage.update_message_status.call_count == 2
    
    @pytest.mark.asyncio
    async def test_auto_mark_as_read_on_receive(self):
        """Test automatically marking messages as read when received."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_status_update = AsyncMock()
        client._ws = mock_ws
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        received_messages = []
        
        @client.on_message
        async def handle_message(message):
            received_messages.append(message)
            # Auto-mark as read
            await client.mark_as_read(
                peer_id=message.from_user,
                message_ids=[message.id]
            )
        
        # Simulate receiving a message
        incoming_message = {
            "type": "text",
            "id": "msg_789",
            "from": "user_456",
            "to": "user_123",
            "content": "Hello!",
            "timestamp": 1234567890,
            "encrypted": False
        }
        
        await client._handle_incoming_message(incoming_message)
        
        # Verify message received
        assert len(received_messages) == 1
        
        # Verify read receipt sent
        mock_ws.send_status_update.assert_called_with("msg_789", "read")
    
    @pytest.mark.asyncio
    async def test_status_handler_error_doesnt_crash(self):
        """Test that status handler errors don't crash the system."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.update_message_status = MagicMock()
        client._message_storage = mock_storage
        
        other_handler_called = False
        
        @client.on_message_status
        async def bad_handler(data):
            raise ValueError("Handler error")
        
        @client.on_message_status
        async def good_handler(data):
            nonlocal other_handler_called
            other_handler_called = True
        
        # Should not raise despite bad_handler error
        await client._handle_status({"messageId": "msg_456", "status": "read"})
        
        # Good handler should still be called
        assert other_handler_called
        
        # Storage should still be updated
        mock_storage.update_message_status.assert_called_once()
