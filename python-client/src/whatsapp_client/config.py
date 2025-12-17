"""Configuration and customization for WhatsApp Client."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

from .logging import LogLevel


class MessageEncryption(str, Enum):
    """Message encryption types."""

    DOUBLE_RATCHET = "double_ratchet"  # Default E2EE with Double Ratchet


class StorageType(str, Enum):
    """Storage backend types."""

    SQLITE = "sqlite"  # Local SQLite storage


@dataclass
class ClientConfig:
    """WhatsApp Client configuration."""

    # Server configuration
    server_url: str = "http://localhost:8787"
    ws_url: str = "ws://localhost:8787"
    
    # Storage configuration
    storage_path: str = field(default_factory=lambda: str(Path.home() / ".whatsapp_client"))
    storage_type: StorageType = StorageType.SQLITE
    
    # Key management
    key_encryption_enabled: bool = True
    key_storage_dir: str = field(default_factory=lambda: str(Path.home() / ".whatsapp_client" / "keys"))
    
    # Message encryption
    message_encryption: MessageEncryption = MessageEncryption.DOUBLE_RATCHET
    
    # File transfer
    max_file_size_mb: int = 5  # Maximum file size in MB
    file_download_dir: str = field(default_factory=lambda: str(Path.home() / "Downloads" / "WhatsApp"))
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[str] = None
    
    # Performance
    connection_timeout_seconds: int = 30
    reconnect_max_backoff_seconds: int = 60
    message_poll_interval_seconds: int = 1
    
    # Security
    fingerprint_verification_required: bool = False
    verify_peer_before_send: bool = False
    
    # Feature toggles
    auto_download_images: bool = False
    auto_mark_read: bool = True
    typing_indicator_enabled: bool = True
    presence_enabled: bool = True
    
    # Advanced
    max_prekeys: int = 100
    min_prekeys_threshold: int = 20
    max_skipped_keys: int = 50

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        data = asdict(self)
        # Convert enum values to their string values
        data["storage_type"] = self.storage_type.value
        data["message_encryption"] = self.message_encryption.value
        data["log_level"] = self.log_level.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientConfig":
        """Create config from dictionary."""
        # Convert string enum values back to enums
        if "storage_type" in data:
            data["storage_type"] = StorageType(data["storage_type"])
        if "message_encryption" in data:
            data["message_encryption"] = MessageEncryption(data["message_encryption"])
        if "log_level" in data:
            data["log_level"] = LogLevel(data["log_level"])
        
        return cls(**data)


class ConfigManager:
    """Manage client configuration."""

    _instance: Optional["ConfigManager"] = None
    _config: ClientConfig

    def __new__(cls) -> "ConfigManager":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize config manager."""
        if self._initialized:
            return

        self._initialized = True
        self._config = ClientConfig()
        self._config_file: Optional[Path] = None

    def load_config(self, config_file: str) -> None:
        """
        Load configuration from JSON file.

        Args:
            config_file: Path to config JSON file
        """
        config_path = Path(config_file).expanduser()

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(config_path, "r") as f:
            data = json.load(f)

        self._config = ClientConfig.from_dict(data)
        self._config_file = config_path

    def save_config(self, config_file: Optional[str] = None) -> None:
        """
        Save configuration to JSON file.

        Args:
            config_file: Path to save config (uses loaded path if not provided)
        """
        if config_file:
            self._config_file = Path(config_file).expanduser()
        elif not self._config_file:
            raise ValueError("No config file path specified")

        self._config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self._config_file, "w") as f:
            json.dump(self._config.to_dict(), f, indent=2)

    def load_config_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Server configuration
        if "WHATSAPP_SERVER_URL" in os.environ:
            self._config.server_url = os.environ["WHATSAPP_SERVER_URL"]
        
        if "WHATSAPP_WS_URL" in os.environ:
            self._config.ws_url = os.environ["WHATSAPP_WS_URL"]
        
        # Storage configuration
        if "WHATSAPP_STORAGE_PATH" in os.environ:
            self._config.storage_path = os.environ["WHATSAPP_STORAGE_PATH"]
        
        # Key management
        if "WHATSAPP_KEY_ENCRYPTION_ENABLED" in os.environ:
            self._config.key_encryption_enabled = (
                os.environ["WHATSAPP_KEY_ENCRYPTION_ENABLED"].lower() == "true"
            )
        
        # Logging
        if "WHATSAPP_LOG_LEVEL" in os.environ:
            self._config.log_level = LogLevel(os.environ["WHATSAPP_LOG_LEVEL"])
        
        if "WHATSAPP_LOG_FILE" in os.environ:
            self._config.log_file = os.environ["WHATSAPP_LOG_FILE"]
        
        # File transfer
        if "WHATSAPP_MAX_FILE_SIZE_MB" in os.environ:
            self._config.max_file_size_mb = int(os.environ["WHATSAPP_MAX_FILE_SIZE_MB"])

    def get_config(self) -> ClientConfig:
        """Get current configuration."""
        return self._config

    def update_config(self, **kwargs: Any) -> None:
        """
        Update specific configuration values.

        Args:
            **kwargs: Configuration keys and values to update
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")

    def get_value(self, key: str) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key

        Returns:
            Configuration value

        Raises:
            KeyError: If key not found
        """
        if not hasattr(self._config, key):
            raise KeyError(f"Unknown configuration key: {key}")
        return getattr(self._config, key)

    def set_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Value to set

        Raises:
            KeyError: If key not found
        """
        if not hasattr(self._config, key):
            raise KeyError(f"Unknown configuration key: {key}")
        setattr(self._config, key, value)

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = ClientConfig()


# Global config manager instance
_config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get global config manager instance."""
    return _config_manager


def get_config() -> ClientConfig:
    """Get current client configuration."""
    return _config_manager.get_config()


def load_config(config_file: str) -> None:
    """Load configuration from file."""
    _config_manager.load_config(config_file)


def save_config(config_file: Optional[str] = None) -> None:
    """Save configuration to file."""
    _config_manager.save_config(config_file)


def load_config_from_env() -> None:
    """Load configuration from environment variables."""
    _config_manager.load_config_from_env()


def update_config(**kwargs: Any) -> None:
    """Update configuration values."""
    _config_manager.update_config(**kwargs)


def get_config_value(key: str) -> Any:
    """Get a configuration value."""
    return _config_manager.get_value(key)


def set_config_value(key: str, value: Any) -> None:
    """Set a configuration value."""
    _config_manager.set_value(key, value)
