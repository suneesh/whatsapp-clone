"""Custom exceptions for WhatsApp Client library."""


class WhatsAppClientError(Exception):
    """Base exception for all client errors."""

    pass


class AuthenticationError(WhatsAppClientError):
    """Authentication failed."""

    pass


class ValidationError(WhatsAppClientError):
    """Input validation error."""

    pass


class ConnectionError(WhatsAppClientError):
    """Network connection error."""

    pass


class SessionNotFoundError(WhatsAppClientError):
    """No session exists for peer."""

    pass


class DecryptionError(WhatsAppClientError):
    """Message decryption failed."""

    pass


class MessageSkipError(WhatsAppClientError):
    """Too many skipped message keys."""

    pass


class UsernameExistsError(ValidationError):
    """Username already taken."""

    pass


class CryptographyError(WhatsAppClientError):
    """Cryptographic operation failed."""

    pass


class StorageError(WhatsAppClientError):
    """Storage operation failed."""

    pass
