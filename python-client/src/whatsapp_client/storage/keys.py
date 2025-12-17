"""Encrypted key storage for persistent local key management."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any
import base64

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
    import secrets
except ImportError:
    raise ImportError("cryptography package required for encrypted key storage")

logger = logging.getLogger(__name__)


class KeyStorage:
    """Encrypted storage for cryptographic keys."""

    def __init__(self, storage_path: str, user_id: str):
        """
        Initialize encrypted key storage.

        Args:
            storage_path: Base storage directory path
            user_id: Current user ID
        """
        self.user_id = user_id
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.keys_file = self.storage_path / f"{user_id}_keys.json"
        self.password: Optional[bytes] = None
        self.salt: Optional[bytes] = None

        logger.debug(f"Initialized key storage at {self.keys_file}")

    def _derive_key(self, password: bytes) -> bytes:
        """
        Derive encryption key from password using Argon2id.

        Args:
            password: User password

        Returns:
            32-byte derived key
        """
        if self.salt is None:
            # Generate new salt for new keys
            self.salt = secrets.token_bytes(16)

        # Argon2id KDF with cryptography library
        kdf = Argon2id(
            salt=self.salt,
            length=32,  # 256-bit key for AES-256
            lanes=4,  # parallelism
            memory_cost=65536,  # 64MB
            iterations=3,
        )

        derived_key = kdf.derive(password)
        return derived_key

    def save_keys(
        self,
        keys_data: Dict[str, Any],
        password: str,
    ) -> bool:
        """
        Save keys encrypted with password.

        Args:
            keys_data: Keys dictionary to save
            password: Password for encryption

        Returns:
            True if successful
        """
        try:
            password_bytes = password.encode()

            # Derive key
            derived_key = self._derive_key(password_bytes)

            # Generate nonce
            nonce = secrets.token_bytes(12)

            # Serialize keys data
            json_data = json.dumps(keys_data).encode()

            # Encrypt
            cipher = AESGCM(derived_key)
            ciphertext = cipher.encrypt(nonce, json_data, None)

            # Prepare storage
            storage_data = {
                "version": "1.0",
                "salt": base64.b64encode(self.salt).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ciphertext).decode(),
            }

            # Write to file with restricted permissions
            with open(self.keys_file, "w") as f:
                json.dump(storage_data, f)

            # Set file permissions to 0600 (Unix) if available
            try:
                os.chmod(self.keys_file, 0o600)
            except (OSError, NotImplementedError):
                # Windows or permission issues - log but don't fail
                logger.warning("Could not set restrictive file permissions")

            logger.info(f"Saved encrypted keys to {self.keys_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save encrypted keys: {e}")
            return False

    def load_keys(self, password: str) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt keys from storage.

        Args:
            password: Password for decryption

        Returns:
            Keys dictionary or None
        """
        try:
            if not self.keys_file.exists():
                logger.debug(f"No stored keys found at {self.keys_file}")
                return None

            # Read file
            with open(self.keys_file, "r") as f:
                storage_data = json.load(f)

            # Extract components
            self.salt = base64.b64decode(storage_data["salt"])
            nonce = base64.b64decode(storage_data["nonce"])
            ciphertext = base64.b64decode(storage_data["ciphertext"])

            # Derive key
            password_bytes = password.encode()
            derived_key = self._derive_key(password_bytes)

            # Decrypt
            cipher = AESGCM(derived_key)
            plaintext = cipher.decrypt(nonce, ciphertext, None)

            # Deserialize
            keys_data = json.loads(plaintext.decode())

            logger.info(f"Loaded encrypted keys from {self.keys_file}")
            return keys_data

        except Exception as e:
            logger.error(f"Failed to load encrypted keys: {e}")
            return None

    def has_keys(self) -> bool:
        """Check if encrypted keys exist."""
        return self.keys_file.exists()

    def clear_keys(self) -> bool:
        """
        Clear stored keys securely.

        Returns:
            True if successful
        """
        try:
            if self.keys_file.exists():
                # Overwrite file with zeros before deletion
                file_size = self.keys_file.stat().st_size

                with open(self.keys_file, "wb") as f:
                    f.write(b"\x00" * file_size)

                self.keys_file.unlink()
                logger.info(f"Cleared keys from {self.keys_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear keys: {e}")
            return False

    def export_keys(self, password: str, export_format: str = "json") -> Optional[str]:
        """
        Export keys in specified format.

        Args:
            password: Password for decryption
            export_format: Format for export (json, base64)

        Returns:
            Exported keys string or None
        """
        try:
            keys_data = self.load_keys(password)
            if not keys_data:
                return None

            if export_format == "json":
                return json.dumps(keys_data, indent=2)
            elif export_format == "base64":
                json_str = json.dumps(keys_data)
                return base64.b64encode(json_str.encode()).decode()
            else:
                raise ValueError(f"Unknown export format: {export_format}")

        except Exception as e:
            logger.error(f"Failed to export keys: {e}")
            return None

    def import_keys(
        self,
        import_data: str,
        password: str,
        import_format: str = "json",
    ) -> bool:
        """
        Import keys from specified format.

        Args:
            import_data: Imported keys data
            password: Password for encryption
            import_format: Format of import (json, base64)

        Returns:
            True if successful
        """
        try:
            if import_format == "json":
                keys_data = json.loads(import_data)
            elif import_format == "base64":
                json_str = base64.b64decode(import_data).decode()
                keys_data = json.loads(json_str)
            else:
                raise ValueError(f"Unknown import format: {import_format}")

            return self.save_keys(keys_data, password)

        except Exception as e:
            logger.error(f"Failed to import keys: {e}")
            return False

    def backup_keys(self, backup_path: str, password: str) -> bool:
        """
        Create backup of encrypted keys.

        Args:
            backup_path: Path to save backup
            password: Password for encryption

        Returns:
            True if successful
        """
        try:
            backup_file = Path(backup_path).expanduser()
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            # Read current encrypted file
            with open(self.keys_file, "rb") as src:
                data = src.read()

            # Write backup
            with open(backup_file, "wb") as dst:
                dst.write(data)

            # Set permissions
            try:
                os.chmod(backup_file, 0o600)
            except (OSError, NotImplementedError):
                pass

            logger.info(f"Created key backup at {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore keys from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if successful
        """
        try:
            backup_file = Path(backup_path).expanduser()

            if not backup_file.exists():
                raise FileNotFoundError(f"Backup not found: {backup_path}")

            # Copy backup to keys file
            with open(backup_file, "rb") as src:
                data = src.read()

            with open(self.keys_file, "wb") as dst:
                dst.write(data)

            # Set permissions
            try:
                os.chmod(self.keys_file, 0o600)
            except (OSError, NotImplementedError):
                pass

            logger.info(f"Restored keys from backup: {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
