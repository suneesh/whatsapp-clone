"""Tests for data models."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from whatsapp_client.models import User, Message, RegisterRequest, LoginRequest


def test_user_model():
    """Test User model."""
    user_data = {
        "id": "user_123",
        "username": "alice",
        "avatar": "https://example.com/avatar.jpg",
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }

    user = User(**user_data)

    assert user.id == "user_123"
    assert user.username == "alice"
    assert user.last_seen == 1234567890
    assert user.role == "user"


def test_message_model():
    """Test Message model."""
    message_data = {
        "id": "msg_123",
        "from": "user_123",
        "to": "user_456",
        "content": "Hello, World!",
        "timestamp": 1234567890,
        "status": "sent",
        "type": "text",
    }

    message = Message(**message_data)

    assert message.id == "msg_123"
    assert message.from_user == "user_123"
    assert message.to == "user_456"
    assert message.content == "Hello, World!"
    assert message.status == "sent"


def test_register_request_validation():
    """Test RegisterRequest validation."""
    # Valid request
    request = RegisterRequest(username="alice", password="password123")
    assert request.username == "alice"
    assert request.password == "password123"

    # Username too short
    with pytest.raises(PydanticValidationError) as exc_info:
        RegisterRequest(username="ab", password="password123")
    assert "at least 3 characters" in str(exc_info.value).lower()

    # Password too short
    with pytest.raises(PydanticValidationError) as exc_info:
        RegisterRequest(username="alice", password="12345")
    assert "at least 6 characters" in str(exc_info.value).lower()


def test_login_request_validation():
    """Test LoginRequest validation."""
    # Valid request
    request = LoginRequest(username="alice", password="password123")
    assert request.username == "alice"
    assert request.password == "password123"

    # Empty username
    with pytest.raises(PydanticValidationError):
        LoginRequest(username="", password="password123")

    # Empty password
    with pytest.raises(PydanticValidationError):
        LoginRequest(username="alice", password="")
