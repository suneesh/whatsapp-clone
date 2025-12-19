"""Tests for authentication functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from whatsapp_client import WhatsAppClient
from whatsapp_client.exceptions import (
    AuthenticationError,
    ValidationError,
    UsernameExistsError,
)


@pytest.fixture
def client():
    """Create a test client."""
    return WhatsAppClient(server_url="http://localhost:8787")


@pytest.mark.asyncio
async def test_register_success(client):
    """Test successful user registration."""
    mock_response = {
        "id": "user_123",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJ1c2VyXzEyMyIsImV4cCI6OTk5OTk5OTk5OX0.test_token",
    }

    with patch.object(client._rest, "post", new=AsyncMock(return_value=mock_response)):
        user = await client.register("alice", "password123")

        assert user.username == "alice"
        assert user.id == "user_123"
        assert client.user_id == "user_123"
        assert client.is_authenticated


@pytest.mark.asyncio
async def test_register_username_exists(client):
    """Test registration with existing username."""
    mock_response = {"error": "Username already taken"}

    with patch.object(client._rest, "post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(UsernameExistsError) as exc_info:
            await client.register("alice", "password123")

        assert "already taken" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_register_validation_error():
    """Test registration with invalid input."""
    client = WhatsAppClient(server_url="http://localhost:8787")

    # Username too short
    with pytest.raises(ValidationError) as exc_info:
        await client.register("ab", "password123")
    assert "at least 3 characters" in str(exc_info.value).lower()

    # Password too short
    with pytest.raises(ValidationError) as exc_info:
        await client.register("alice", "12345")
    assert "at least 6 characters" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_login_success(client):
    """Test successful login."""
    mock_response = {
        "id": "user_123",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJ1c2VyXzEyMyIsImV4cCI6OTk5OTk5OTk5OX0.test_token",
    }

    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }

    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_response, mock_upload_response])):
        user = await client.login("alice", "password123")

        assert user.username == "alice"
        assert user.id == "user_123"
        assert client.user_id == "user_123"
        assert client.is_authenticated
        
        # Check that keys were initialized
        assert client._key_manager is not None
        fingerprint = client.get_fingerprint()
        assert len(fingerprint) == 60


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    mock_response = {"error": "Invalid username or password"}

    with patch.object(client._rest, "post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(AuthenticationError) as exc_info:
            await client.login("alice", "wrong_password")

        assert "invalid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_login_validation_error(client):
    """Test login with empty credentials."""
    with pytest.raises(ValidationError):
        await client.login("", "password123")

    with pytest.raises(ValidationError):
        await client.login("alice", "")


@pytest.mark.asyncio
async def test_logout(client):
    """Test logout functionality."""
    # Mock successful login
    mock_response = {
        "id": "user_123",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJ1c2VyXzEyMyIsImV4cCI6OTk5OTk5OTk5OX0.test_token",
    }

    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }

    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_response, mock_upload_response])):
        await client.login("alice", "password123")

    assert client.is_authenticated

    # Logout
    await client.logout()

    assert not client.is_authenticated
    assert client.user is None
    assert client.user_id is None
    assert client._key_manager is None


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    async with WhatsAppClient(server_url="http://localhost:8787") as client:
        assert client is not None
        assert not client._closed


@pytest.mark.asyncio
async def test_close():
    """Test client cleanup."""
    client = WhatsAppClient(server_url="http://localhost:8787")

    # Mock login
    mock_response = {
        "id": "user_123",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJ1c2VyXzEyMyIsImV4cCI6OTk5OTk5OTk5OX0.test_token",
    }

    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }

    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_response, mock_upload_response])):
        await client.login("alice", "password123")

    assert client.is_authenticated

    # Close client
    await client.close()

    assert not client.is_authenticated
    assert client._closed
