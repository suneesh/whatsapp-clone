"""Tests for US15: Configuration and Customization."""

import pytest
import tempfile
import json
import os
from pathlib import Path

from whatsapp_client.config import (
    ClientConfig,
    ConfigManager,
    MessageEncryption,
    StorageType,
    get_config_manager,
    get_config,
    load_config,
    save_config,
    load_config_from_env,
    update_config,
    get_config_value,
    set_config_value,
)
from whatsapp_client.logging import LogLevel


class TestClientConfig:
    """Test ClientConfig dataclass."""

    def test_default_config_creation(self):
        """Test creating config with defaults."""
        config = ClientConfig()
        assert config.server_url == "http://localhost:8787"
        assert config.ws_url == "ws://localhost:8787"
        assert config.storage_type == StorageType.SQLITE
        assert config.message_encryption == MessageEncryption.DOUBLE_RATCHET
        assert config.max_file_size_mb == 5
        assert config.log_level == LogLevel.INFO
        assert config.auto_mark_read == True
        assert config.typing_indicator_enabled == True

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = ClientConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["server_url"] == "http://localhost:8787"
        assert config_dict["storage_type"] == "sqlite"
        assert config_dict["message_encryption"] == "double_ratchet"
        assert config_dict["log_level"] == "INFO"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "server_url": "http://example.com:8787",
            "ws_url": "ws://example.com:8787",
            "max_file_size_mb": 10,
            "storage_type": "sqlite",
            "message_encryption": "double_ratchet",
            "log_level": "DEBUG",
            "key_encryption_enabled": False,
        }

        config = ClientConfig.from_dict(data)
        assert config.server_url == "http://example.com:8787"
        assert config.ws_url == "ws://example.com:8787"
        assert config.max_file_size_mb == 10
        assert config.storage_type == StorageType.SQLITE
        assert config.message_encryption == MessageEncryption.DOUBLE_RATCHET
        assert config.log_level == LogLevel.DEBUG
        assert config.key_encryption_enabled == False

    def test_config_from_dict_round_trip(self):
        """Test round-trip conversion: dict -> config -> dict."""
        original_dict = {
            "server_url": "http://test.com",
            "max_file_size_mb": 20,
            "auto_mark_read": False,
            "storage_type": "sqlite",
            "message_encryption": "double_ratchet",
            "log_level": "WARNING",
        }

        config = ClientConfig.from_dict(original_dict)
        result_dict = config.to_dict()

        # Check key values are preserved
        assert result_dict["server_url"] == original_dict["server_url"]
        assert result_dict["max_file_size_mb"] == original_dict["max_file_size_mb"]
        assert result_dict["auto_mark_read"] == original_dict["auto_mark_read"]


class TestConfigManager:
    """Test ConfigManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConfigManager()
        self.manager.reset_to_defaults()

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        assert manager1 is manager2

    def test_get_config(self):
        """Test getting current configuration."""
        config = self.manager.get_config()
        assert isinstance(config, ClientConfig)
        assert config.server_url == "http://localhost:8787"

    def test_load_config_from_file(self):
        """Test loading configuration from JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            config_data = {
                "server_url": "http://example.com",
                "max_file_size_mb": 15,
                "auto_mark_read": False,
                "storage_type": "sqlite",
                "message_encryption": "double_ratchet",
                "log_level": "DEBUG",
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            self.manager.load_config(str(config_file))
            config = self.manager.get_config()

            assert config.server_url == "http://example.com"
            assert config.max_file_size_mb == 15
            assert config.auto_mark_read == False
            assert config.log_level == LogLevel.DEBUG

    def test_save_config_to_file(self):
        """Test saving configuration to JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            config = self.manager.get_config()
            config.server_url = "http://custom.com"
            config.max_file_size_mb = 25

            self.manager.save_config(str(config_file))

            assert config_file.exists()

            with open(config_file, "r") as f:
                loaded_data = json.load(f)

            assert loaded_data["server_url"] == "http://custom.com"
            assert loaded_data["max_file_size_mb"] == 25

    def test_load_config_from_missing_file(self):
        """Test loading config from non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.manager.load_config("/nonexistent/config.json")

    def test_update_config(self):
        """Test updating configuration values."""
        self.manager.update_config(
            server_url="http://newserver.com",
            max_file_size_mb=30,
            auto_mark_read=False,
        )

        config = self.manager.get_config()
        assert config.server_url == "http://newserver.com"
        assert config.max_file_size_mb == 30
        assert config.auto_mark_read == False

    def test_update_config_with_invalid_key(self):
        """Test updating config with invalid key."""
        with pytest.raises(ValueError):
            self.manager.update_config(invalid_key="value")

    def test_get_value(self):
        """Test getting individual config values."""
        self.manager.update_config(max_file_size_mb=50)

        value = self.manager.get_value("max_file_size_mb")
        assert value == 50

    def test_get_value_invalid_key(self):
        """Test getting value for invalid key."""
        with pytest.raises(KeyError):
            self.manager.get_value("invalid_key")

    def test_set_value(self):
        """Test setting individual config values."""
        self.manager.set_value("max_file_size_mb", 100)
        assert self.manager.get_value("max_file_size_mb") == 100

    def test_set_value_invalid_key(self):
        """Test setting value for invalid key."""
        with pytest.raises(KeyError):
            self.manager.set_value("invalid_key", "value")

    def test_reset_to_defaults(self):
        """Test resetting config to defaults."""
        self.manager.update_config(
            server_url="http://custom.com",
            max_file_size_mb=50,
        )

        self.manager.reset_to_defaults()
        config = self.manager.get_config()

        assert config.server_url == "http://localhost:8787"
        assert config.max_file_size_mb == 5

    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        # Set environment variables
        os.environ["WHATSAPP_SERVER_URL"] = "http://env.example.com"
        os.environ["WHATSAPP_WS_URL"] = "ws://env.example.com"
        os.environ["WHATSAPP_MAX_FILE_SIZE_MB"] = "20"
        os.environ["WHATSAPP_LOG_LEVEL"] = "WARNING"

        try:
            self.manager.load_config_from_env()
            config = self.manager.get_config()

            assert config.server_url == "http://env.example.com"
            assert config.ws_url == "ws://env.example.com"
            assert config.max_file_size_mb == 20
            assert config.log_level == LogLevel.WARNING
        finally:
            # Clean up environment variables
            del os.environ["WHATSAPP_SERVER_URL"]
            del os.environ["WHATSAPP_WS_URL"]
            del os.environ["WHATSAPP_MAX_FILE_SIZE_MB"]
            del os.environ["WHATSAPP_LOG_LEVEL"]

    def test_load_config_from_env_partial(self):
        """Test loading config from environment with only some variables set."""
        original_server = self.manager.get_config().server_url

        os.environ["WHATSAPP_SERVER_URL"] = "http://partial.example.com"

        try:
            self.manager.load_config_from_env()
            config = self.manager.get_config()
            assert config.server_url == "http://partial.example.com"
        finally:
            del os.environ["WHATSAPP_SERVER_URL"]

    def test_key_encryption_disabled(self):
        """Test disabling key encryption."""
        self.manager.update_config(key_encryption_enabled=False)
        assert self.manager.get_config().key_encryption_enabled == False

    def test_fingerprint_verification_config(self):
        """Test fingerprint verification configuration."""
        self.manager.update_config(
            fingerprint_verification_required=True,
            verify_peer_before_send=True,
        )

        config = self.manager.get_config()
        assert config.fingerprint_verification_required == True
        assert config.verify_peer_before_send == True


class TestConfigModule:
    """Test module-level config functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = get_config_manager()
        self.manager.reset_to_defaults()

    def test_get_config_function(self):
        """Test get_config() function."""
        config = get_config()
        assert isinstance(config, ClientConfig)

    def test_update_config_function(self):
        """Test update_config() function."""
        update_config(max_file_size_mb=40)
        config = get_config()
        assert config.max_file_size_mb == 40

    def test_get_config_value_function(self):
        """Test get_config_value() function."""
        update_config(max_file_size_mb=35)
        value = get_config_value("max_file_size_mb")
        assert value == 35

    def test_set_config_value_function(self):
        """Test set_config_value() function."""
        set_config_value("max_file_size_mb", 45)
        assert get_config_value("max_file_size_mb") == 45

    def test_load_config_function(self):
        """Test load_config() function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            config_data = {
                "server_url": "http://func.example.com",
                "storage_type": "sqlite",
                "message_encryption": "double_ratchet",
                "log_level": "INFO",
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            load_config(str(config_file))
            config = get_config()
            assert config.server_url == "http://func.example.com"

    def test_save_config_function(self):
        """Test save_config() function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "save_test.json"

            update_config(server_url="http://save.example.com")
            save_config(str(config_file))

            assert config_file.exists()
            with open(config_file, "r") as f:
                data = json.load(f)
            assert data["server_url"] == "http://save.example.com"

    def test_load_config_from_env_function(self):
        """Test load_config_from_env() function."""
        os.environ["WHATSAPP_SERVER_URL"] = "http://env.func.example.com"

        try:
            load_config_from_env()
            config = get_config()
            assert config.server_url == "http://env.func.example.com"
        finally:
            del os.environ["WHATSAPP_SERVER_URL"]


class TestConfigurationEdgeCases:
    """Test edge cases in configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = get_config_manager()
        self.manager.reset_to_defaults()

    def test_config_with_special_characters(self):
        """Test config with special characters in values."""
        special_url = "http://example.com/path?query=value&other=123"
        self.manager.update_config(server_url=special_url)
        assert self.manager.get_config().server_url == special_url

    def test_config_with_large_file_size(self):
        """Test config with large file size values."""
        large_size = 10000  # 10GB
        self.manager.update_config(max_file_size_mb=large_size)
        assert self.manager.get_config().max_file_size_mb == large_size

    def test_config_persistence_across_instances(self):
        """Test that config persists across different manager instances."""
        manager1 = ConfigManager()
        manager1.update_config(max_file_size_mb=77)

        manager2 = ConfigManager()
        assert manager2.get_config().max_file_size_mb == 77

    def test_enum_values_in_config(self):
        """Test that enum values are properly handled."""
        config_data = {
            "storage_type": "sqlite",
            "message_encryption": "double_ratchet",
            "log_level": "ERROR",
            "server_url": "http://localhost",
            "ws_url": "ws://localhost",
            "key_encryption_enabled": True,
        }

        config = ClientConfig.from_dict(config_data)
        assert config.storage_type == StorageType.SQLITE
        assert config.message_encryption == MessageEncryption.DOUBLE_RATCHET
        assert config.log_level == LogLevel.ERROR
