"""
WhatsApp Clone Python Client Library

A Python library for programmatic access to the WhatsApp Clone E2EE chat platform.
Enables developers to build bots, automation tools, and integrations.
"""

from .client import WhatsAppClient
from .async_client import AsyncClient
from .models import User, Message, PrekeyBundle, Session
from .exceptions import (
    WhatsAppClientError,
    AuthenticationError,
    ValidationError,
    ConnectionError,
)
from .async_utils import (
    TaskManager,
    EventLoopManager,
    AsyncContextManager,
    ExceptionHandler,
    managed_task,
    ensure_async,
)

__version__ = "0.1.0"
__all__ = [
    "WhatsAppClient",
    "AsyncClient",
    "User",
    "Message",
    "PrekeyBundle",
    "Session",
    "WhatsAppClientError",
    "AuthenticationError",
    "ValidationError",
    "ConnectionError",
    "TaskManager",
    "EventLoopManager",
    "AsyncContextManager",
    "ExceptionHandler",
    "managed_task",
    "ensure_async",
]
