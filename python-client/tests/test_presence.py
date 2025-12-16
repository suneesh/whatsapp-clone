"""Tests for US8: Typing Indicators and Presence."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from whatsapp_client import WhatsAppClient
from whatsapp_client.transport import WebSocketClient


class TestTypingIndicators:
    """Test typing indicator functionality."""
    
    @pytest.mark.asyncio
    async def test_send_typing_indicator(self):
        """Test sending typing indicator."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_typing = AsyncMock()
        client._ws = mock_ws
        
        # Send typing indicator
        await client.send_typing(to="user_456", typing=True)
        
        # Verify WebSocket method was called
        mock_ws.send_typing.assert_called_once_with("user_456", True)
    
    @pytest.mark.asyncio
    async def test_send_typing_stopped(self):
        """Test sending typing stopped indicator."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocketClient)
        mock_ws.send_typing = AsyncMock()
        client._ws = mock_ws
        
        # Send typing stopped
        await client.send_typing(to="user_456", typing=False)
        
        mock_ws.send_typing.assert_called_once_with("user_456", False)
    
    @pytest.mark.asyncio
    async def test_typing_handler_registration(self):
        """Test registering typing event handler."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Create handler
        handler_called = False
        
        @client.on_typing
        async def handle_typing(data):
            nonlocal handler_called
            handler_called = True
        
        # Verify handler registered
        assert len(client._typing_handlers) == 1
        
        # Simulate typing event
        await client._handle_typing({"userId": "user_456", "typing": True})
        
        # Verify handler was called
        assert handler_called
    
    @pytest.mark.asyncio
    async def test_typing_event_handling(self):
        """Test handling typing events from other users."""
        client = WhatsAppClient(server_url="http://test.com")
        
        typing_events = []
        
        @client.on_typing
        async def handle_typing(data):
            typing_events.append(data)
        
        # Simulate typing events
        await client._handle_typing({"userId": "user_456", "typing": True})
        await client._handle_typing({"userId": "user_789", "typing": True})
        await client._handle_typing({"userId": "user_456", "typing": False})
        
        # Verify all events captured
        assert len(typing_events) == 3
        assert typing_events[0]["userId"] == "user_456"
        assert typing_events[0]["typing"] is True
        assert typing_events[2]["typing"] is False
    
    @pytest.mark.asyncio
    async def test_multiple_typing_handlers(self):
        """Test multiple typing handlers."""
        client = WhatsAppClient(server_url="http://test.com")
        
        handler1_calls = []
        handler2_calls = []
        
        @client.on_typing
        async def handler1(data):
            handler1_calls.append(data)
        
        @client.on_typing
        async def handler2(data):
            handler2_calls.append(data)
        
        # Simulate typing event
        await client._handle_typing({"userId": "user_456", "typing": True})
        
        # Both handlers should be called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1


class TestPresenceTracking:
    """Test presence tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_presence_handler_registration(self):
        """Test registering presence event handler."""
        client = WhatsAppClient(server_url="http://test.com")
        
        handler_called = False
        
        @client.on_presence
        async def handle_presence(data):
            nonlocal handler_called
            handler_called = True
        
        # Verify handler registered
        assert len(client._presence_handlers) == 1
        
        # Simulate presence event
        await client._handle_presence({"userId": "user_456", "online": True})
        
        # Verify handler was called
        assert handler_called
    
    @pytest.mark.asyncio
    async def test_presence_tracking_online(self):
        """Test tracking user coming online."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # User comes online
        await client._handle_presence({"userId": "user_456", "online": True})
        
        # Verify tracking
        assert client.is_user_online("user_456") is True
        assert "user_456" in client.get_online_users()
    
    @pytest.mark.asyncio
    async def test_presence_tracking_offline(self):
        """Test tracking user going offline."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # User comes online
        await client._handle_presence({"userId": "user_456", "online": True})
        assert client.is_user_online("user_456") is True
        
        # User goes offline
        await client._handle_presence({"userId": "user_456", "online": False})
        
        # Verify tracking
        assert client.is_user_online("user_456") is False
        assert "user_456" not in client.get_online_users()
    
    @pytest.mark.asyncio
    async def test_multiple_users_online(self):
        """Test tracking multiple users online."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Multiple users come online
        await client._handle_presence({"userId": "user_456", "online": True})
        await client._handle_presence({"userId": "user_789", "online": True})
        await client._handle_presence({"userId": "user_abc", "online": True})
        
        # Verify all tracked
        online_users = client.get_online_users()
        assert len(online_users) == 3
        assert "user_456" in online_users
        assert "user_789" in online_users
        assert "user_abc" in online_users
    
    @pytest.mark.asyncio
    async def test_get_online_users(self):
        """Test getting list of online users."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Initially empty
        assert client.get_online_users() == []
        
        # Add online users
        await client._handle_presence({"userId": "user_456", "online": True})
        await client._handle_presence({"userId": "user_789", "online": True})
        
        online = client.get_online_users()
        assert len(online) == 2
        assert "user_456" in online
        assert "user_789" in online
    
    @pytest.mark.asyncio
    async def test_is_user_online(self):
        """Test checking if specific user is online."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # User not tracked yet
        assert client.is_user_online("user_456") is False
        
        # User comes online
        await client._handle_presence({"userId": "user_456", "online": True})
        assert client.is_user_online("user_456") is True
        
        # User goes offline
        await client._handle_presence({"userId": "user_456", "online": False})
        assert client.is_user_online("user_456") is False
    
    @pytest.mark.asyncio
    async def test_get_all_presence(self):
        """Test getting all presence data."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Add mixed online/offline users
        await client._handle_presence({"userId": "user_456", "online": True})
        await client._handle_presence({"userId": "user_789", "online": False})
        await client._handle_presence({"userId": "user_abc", "online": True})
        
        presence = client.get_all_presence()
        
        assert len(presence) == 3
        assert presence["user_456"] is True
        assert presence["user_789"] is False
        assert presence["user_abc"] is True
    
    @pytest.mark.asyncio
    async def test_presence_events_notification(self):
        """Test presence event handlers are notified."""
        client = WhatsAppClient(server_url="http://test.com")
        
        presence_events = []
        
        @client.on_presence
        async def handle_presence(data):
            presence_events.append(data)
        
        # Simulate presence events
        await client._handle_presence({"userId": "user_456", "online": True})
        await client._handle_presence({"userId": "user_456", "online": False})
        
        # Verify events captured
        assert len(presence_events) == 2
        assert presence_events[0]["online"] is True
        assert presence_events[1]["online"] is False
    
    @pytest.mark.asyncio
    async def test_presence_cleared_on_logout(self):
        """Test presence tracking cleared on logout."""
        client = WhatsAppClient(server_url="http://test.com")
        
        # Mock authenticated state
        client._auth._user_id = "user_123"
        client._auth._user = MagicMock(id="user_123", username="alice")
        client._auth.logout = AsyncMock()
        
        # Add some presence data
        await client._handle_presence({"userId": "user_456", "online": True})
        await client._handle_presence({"userId": "user_789", "online": True})
        
        assert len(client.get_online_users()) == 2
        
        # Logout
        await client.logout()
        
        # Presence should be cleared
        assert len(client.get_online_users()) == 0
        assert client.get_all_presence() == {}


class TestIntegration:
    """Integration tests for typing and presence."""
    
    @pytest.mark.asyncio
    async def test_typing_and_presence_together(self):
        """Test typing and presence work together."""
        client = WhatsAppClient(server_url="http://test.com")
        
        typing_events = []
        presence_events = []
        
        @client.on_typing
        async def handle_typing(data):
            typing_events.append(data)
        
        @client.on_presence
        async def handle_presence(data):
            presence_events.append(data)
        
        # User comes online
        await client._handle_presence({"userId": "user_456", "online": True})
        
        # User starts typing
        await client._handle_typing({"userId": "user_456", "typing": True})
        
        # User stops typing
        await client._handle_typing({"userId": "user_456", "typing": False})
        
        # User goes offline
        await client._handle_presence({"userId": "user_456", "online": False})
        
        # Verify all events captured
        assert len(presence_events) == 2
        assert len(typing_events) == 2
        
        # Final state: user offline
        assert client.is_user_online("user_456") is False
    
    @pytest.mark.asyncio
    async def test_handler_error_doesnt_crash(self):
        """Test that handler errors don't crash the system."""
        client = WhatsAppClient(server_url="http://test.com")
        
        other_handler_called = False
        
        @client.on_presence
        async def bad_handler(data):
            raise ValueError("Handler error")
        
        @client.on_presence
        async def good_handler(data):
            nonlocal other_handler_called
            other_handler_called = True
        
        # Should not raise despite bad_handler error
        await client._handle_presence({"userId": "user_456", "online": True})
        
        # Good handler should still be called
        assert other_handler_called
        
        # Presence should still be tracked
        assert client.is_user_online("user_456") is True
