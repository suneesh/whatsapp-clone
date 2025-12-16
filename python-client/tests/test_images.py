"""Tests for US10: Image and File Sending."""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from whatsapp_client import WhatsAppClient
from whatsapp_client.transport import WebSocketClient
from whatsapp_client.storage import MessageStorage
from whatsapp_client.models import Message
from whatsapp_client.exceptions import WhatsAppClientError


class TestImageSending:
    """Test image sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_image_from_bytes(self):
        """Test sending image from bytes."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        
        # Mock session manager
        mock_session = MagicMock()
        mock_session.encrypt_message = MagicMock(return_value="encrypted_data")
        client._session_manager = mock_session
        client.ensure_session = AsyncMock()
        
        # Mock message storage
        mock_storage = MagicMock(spec=MessageStorage)
        mock_storage.save_message = MagicMock()
        client._message_storage = mock_storage
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_message = AsyncMock()
        mock_ws.is_connected = True
        client._ws = mock_ws
        
        # Create fake image data
        image_data = b"fake_image_data"
        
        # Send image
        message = await client.send_image(
            to="user_456",
            image_data=image_data,
            caption="Test image"
        )
        
        # Verify message created
        assert message.type == "image"
        assert message.to == "user_456"
        assert message.content == "Test image"
        assert message.image_data is not None
        
        # Verify storage called
        mock_storage.save_message.assert_called_once()
        
        # Verify WebSocket called
        mock_ws.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_image_from_file(self, tmp_path):
        """Test sending image from file path."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        
        # Mock session manager
        mock_session = MagicMock()
        mock_session.encrypt_message = MagicMock(return_value="encrypted_data")
        client._session_manager = mock_session
        client.ensure_session = AsyncMock()
        
        # Mock storage and WebSocket
        client._message_storage = MagicMock(spec=MessageStorage)
        client._message_storage.save_message = MagicMock()
        
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_message = AsyncMock()
        mock_ws.is_connected = True
        client._ws = mock_ws
        
        # Create temporary image file
        image_path = tmp_path / "test_image.jpg"
        image_data = b"fake_jpeg_data"
        image_path.write_bytes(image_data)
        
        # Send image
        message = await client.send_image(
            to="user_456",
            image_path=str(image_path)
        )
        
        # Verify message created
        assert message.type == "image"
        assert message.image_data is not None
    
    @pytest.mark.asyncio
    async def test_send_image_file_not_found(self):
        """Test error when image file doesn't exist."""
        client = WhatsAppClient(server_url="http://test.com")
        client._auth._user_id = "user_123"
        
        with pytest.raises(WhatsAppClientError, match="Image file not found"):
            await client.send_image(
                to="user_456",
                image_path="/nonexistent/image.jpg"
            )
    
    @pytest.mark.asyncio
    async def test_send_image_no_source_error(self):
        """Test error when neither image_path nor image_data provided."""
        client = WhatsAppClient(server_url="http://test.com")
        client._auth._user_id = "user_123"
        
        with pytest.raises(ValueError, match="Either image_path or image_data must be provided"):
            await client.send_image(to="user_456")
    
    @pytest.mark.asyncio
    async def test_send_image_both_sources_error(self):
        """Test error when both image_path and image_data provided."""
        client = WhatsAppClient(server_url="http://test.com")
        client._auth._user_id = "user_123"
        
        with pytest.raises(ValueError, match="Cannot specify both"):
            await client.send_image(
                to="user_456",
                image_path="test.jpg",
                image_data=b"data"
            )
    
    @pytest.mark.asyncio
    async def test_send_image_size_limit(self):
        """Test size limit enforcement."""
        client = WhatsAppClient(server_url="http://test.com")
        client._auth._user_id = "user_123"
        
        # Create image larger than limit
        large_image = b"x" * (6 * 1024 * 1024)  # 6MB
        
        with pytest.raises(WhatsAppClientError, match="Image too large"):
            await client.send_image(
                to="user_456",
                image_data=large_image,
                max_size=5 * 1024 * 1024  # 5MB limit
            )
    
    @pytest.mark.asyncio
    async def test_send_image_without_encryption(self):
        """Test sending image without encryption."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state but no session manager
        client._auth._user_id = "user_123"
        client._session_manager = None
        
        # Mock storage and WebSocket
        client._message_storage = MagicMock(spec=MessageStorage)
        client._message_storage.save_message = MagicMock()
        
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_message = AsyncMock()
        mock_ws.is_connected = True
        client._ws = mock_ws
        
        # Send image
        image_data = b"test_data"
        message = await client.send_image(
            to="user_456",
            image_data=image_data
        )
        
        # Verify message created (should use base64 encoded data)
        assert message.type == "image"
        assert message.image_data is not None


class TestImageReceiving:
    """Test image receiving and saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_image_to_file(self, tmp_path):
        """Test saving received image to file."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock session manager for decryption
        mock_session = MagicMock()
        mock_session.decrypt_message = MagicMock(return_value="ZmFrZV9pbWFnZV9kYXRh")  # base64 of "fake_image_data"
        client._session_manager = mock_session
        
        # Create message with image data
        import base64
        original_data = b"fake_image_data"
        encoded_data = base64.b64encode(original_data).decode('utf-8')
        
        message = Message(
            id="msg_123",
            from_user="user_456",
            to="user_123",
            content="Image message",
            type="image",
            timestamp=1234567890,
            status="delivered",
            image_data=encoded_data,
        )
        
        # Save image
        output_path = tmp_path / "saved_image.jpg"
        await client.save_image(message, str(output_path))
        
        # Verify file created
        assert output_path.exists()
        
        # Verify content
        saved_data = output_path.read_bytes()
        assert saved_data == original_data
    
    @pytest.mark.asyncio
    async def test_save_image_non_image_type_error(self):
        """Test error when trying to save non-image message."""
        client = WhatsAppClient(server_url="http://test.com")
        
        message = Message(
            id="msg_123",
            from_user="user_456",
            to="user_123",
            content="Text message",
            type="text",
            timestamp=1234567890,
            status="delivered",
        )
        
        with pytest.raises(ValueError, match="Message is not an image type"):
            await client.save_image(message, "/tmp/image.jpg")
    
    @pytest.mark.asyncio
    async def test_save_image_no_data_error(self):
        """Test error when message has no image data."""
        client = WhatsAppClient(server_url="http://test.com")
        
        message = Message(
            id="msg_123",
            from_user="user_456",
            to="user_123",
            content="Image message",
            type="image",
            timestamp=1234567890,
            status="delivered",
            image_data=None,
        )
        
        with pytest.raises(ValueError, match="Message has no image data"):
            await client.save_image(message, "/tmp/image.jpg")
    
    @pytest.mark.asyncio
    async def test_save_image_creates_directory(self, tmp_path):
        """Test that save_image creates parent directories."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock session manager
        mock_session = MagicMock()
        mock_session.decrypt_message = MagicMock(return_value="ZmFrZV9kYXRh")  # base64
        client._session_manager = mock_session
        
        import base64
        message = Message(
            id="msg_123",
            from_user="user_456",
            to="user_123",
            content="",
            type="image",
            timestamp=1234567890,
            status="delivered",
            image_data=base64.b64encode(b"fake_data").decode('utf-8'),
        )
        
        # Save to nested path that doesn't exist
        output_path = tmp_path / "subdir" / "nested" / "image.jpg"
        await client.save_image(message, str(output_path))
        
        # Verify directory and file created
        assert output_path.exists()
        assert output_path.parent.exists()
    
    @pytest.mark.asyncio
    async def test_decode_image(self):
        """Test decoding image data."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock session manager
        mock_session = MagicMock()
        mock_session.decrypt_message = MagicMock(return_value="ZmFrZV9pbWFnZV9kYXRh")
        client._session_manager = mock_session
        
        # Decode image
        import base64
        original_data = b"fake_image_data"
        encoded = base64.b64encode(original_data).decode('utf-8')
        
        decoded = client.decode_image(encoded, decrypt=True, from_user="user_456")
        
        assert decoded == original_data
    
    @pytest.mark.asyncio
    async def test_decode_image_no_decryption(self):
        """Test decoding without decryption."""
        client = WhatsAppClient(server_url="http://test.com")
        
        import base64
        original_data = b"fake_image_data"
        encoded = base64.b64encode(original_data).decode('utf-8')
        
        # Decode without decryption
        decoded = client.decode_image(encoded, decrypt=False)
        
        assert decoded == original_data
    
    def test_decode_image_decrypt_without_from_user_error(self):
        """Test error when decrypt=True but no from_user."""
        client = WhatsAppClient(server_url="http://test.com")
        
        with pytest.raises(ValueError, match="from_user required when decrypt=True"):
            client.decode_image("data", decrypt=True)


class TestImageStorage:
    """Test image data storage."""
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_image_message(self, tmp_path):
        """Test saving and retrieving image message."""
        storage = MessageStorage(user_id="user_123", storage_path=str(tmp_path))
        
        import base64
        image_data = base64.b64encode(b"fake_image").decode('utf-8')
        
        # Save image message
        message = Message(
            id="msg_456",
            from_user="user_123",
            to="user_789",
            content="Check this out!",
            type="image",
            timestamp=1234567890,
            status="sent",
            image_data=image_data,
        )
        storage.save_message(message)
        
        # Retrieve by ID
        retrieved = storage.get_message_by_id("msg_456")
        
        assert retrieved is not None
        assert retrieved.type == "image"
        assert retrieved.content == "Check this out!"
        assert retrieved.image_data == image_data
    
    @pytest.mark.asyncio
    async def test_get_messages_includes_image_data(self, tmp_path):
        """Test that get_messages includes image_data."""
        storage = MessageStorage(user_id="user_123", storage_path=str(tmp_path))
        
        import base64
        image_data = base64.b64encode(b"fake_image").decode('utf-8')
        
        # Save image message
        message = Message(
            id="msg_456",
            from_user="user_123",
            to="user_789",
            content="",
            type="image",
            timestamp=1234567890,
            status="sent",
            image_data=image_data,
        )
        storage.save_message(message)
        
        # Get messages
        messages = storage.get_messages(peer_id="user_789")
        
        assert len(messages) == 1
        assert messages[0].type == "image"
        assert messages[0].image_data == image_data


class TestIntegration:
    """Integration tests for image functionality."""
    
    @pytest.mark.asyncio
    async def test_send_and_receive_image_flow(self, tmp_path):
        """Test complete flow of sending and receiving image."""
        # Sender
        sender = WhatsAppClient(server_url="http://test.com")
        sender._auth._user_id = "user_alice"
        sender._session_manager = None  # No encryption for simplicity
        sender._message_storage = MagicMock(spec=MessageStorage)
        sender._message_storage.save_message = MagicMock()
        
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_message = AsyncMock()
        mock_ws.is_connected = True
        sender._ws = mock_ws
        
        # Create and send image
        image_data = b"test_image_content"
        sent_message = await sender.send_image(
            to="user_bob",
            image_data=image_data,
            caption="Test photo"
        )
        
        # Verify sent message
        assert sent_message.type == "image"
        assert sent_message.content == "Test photo"
        
        # Receiver
        receiver = WhatsAppClient(server_url="http://test.com")
        receiver._session_manager = None
        
        # Simulate receiving the message
        import base64
        received_message = Message(
            id=sent_message.id,
            from_user="user_alice",
            to="user_bob",
            content="Test photo",
            type="image",
            timestamp=sent_message.timestamp,
            status="delivered",
            image_data=sent_message.image_data,
        )
        
        # Save received image
        output_path = tmp_path / "received_image.jpg"
        await receiver.save_image(received_message, str(output_path), decrypt=False)
        
        # Verify saved image
        assert output_path.exists()
        saved_data = output_path.read_bytes()
        
        # Should match original (since no encryption)
        import base64
        expected = base64.b64decode(sent_message.image_data)
        assert saved_data == expected
