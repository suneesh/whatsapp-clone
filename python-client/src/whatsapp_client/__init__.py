"""
WhatsApp Clone Python Client Library

A Python library for programmatic access to the WhatsApp Clone E2EE chat platform.
Enables developers to build bots, automation tools, and integrations.
"""

from .client import WhatsAppClient
from .models import User, Message
from .exceptions import (
    WhatsAppClientError,
    AuthenticationError,
    ValidationError,
    ConnectionError,
)

__version__ = "0.1.0"
__all__ = [
    "WhatsAppClient",
    "User",
    "Message",
    "WhatsAppClientError",
    "AuthenticationError",
    "ValidationError",
    "ConnectionError",
]
