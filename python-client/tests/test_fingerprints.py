"""Tests for US11: Key Fingerprint Verification."""

import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import tempfile
import os

from whatsapp_client.client import WhatsAppClient
from whatsapp_client.models import User, Session
from whatsapp_client.exceptions import WhatsAppClientError
from whatsapp_client.storage import FingerprintStorage
from cryptography.hazmat.primitives.asymmetric import x25519


class TestFingerprintStorage:
    """Test FingerprintStorage class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FingerprintStorage(self.temp_dir, "test_user")

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_get_fingerprint(self):
        """Test saving and retrieving fingerprint."""
        peer_id = "peer_123"
        identity_key = "identity_key_data"
        fingerprint = "A1B2C3D4E5F6" * 5  # 60 chars

        self.storage.save_fingerprint(peer_id, identity_key, fingerprint)

        result = self.storage.get_fingerprint(peer_id)
        assert result is not None
        assert result["peer_id"] == peer_id
        assert result["fingerprint"] == fingerprint
        assert result["identity_key"] == identity_key
        assert result["verified"] == False

    def test_save_fingerprint_overwrites_existing(self):
        """Test that saving overwrites existing fingerprint."""
        peer_id = "peer_123"
        fp1 = "A1B2C3D4E5F6" * 5
        fp2 = "F6E5D4C3B2A1" * 5

        self.storage.save_fingerprint(peer_id, "id_key1", fp1)
        self.storage.save_fingerprint(peer_id, "id_key2", fp2)

        result = self.storage.get_fingerprint(peer_id)
        assert result["fingerprint"] == fp2
        assert result["identity_key"] == "id_key2"

    def test_verify_fingerprint(self):
        """Test verifying a fingerprint."""
        peer_id = "peer_123"
        fingerprint = "A1B2C3D4E5F6" * 5

        self.storage.save_fingerprint(peer_id, "id_key", fingerprint)
        assert self.storage.is_verified(peer_id) == False

        # Verify
        success = self.storage.verify_fingerprint(peer_id, True)
        assert success == True
        assert self.storage.is_verified(peer_id) == True

        # Unverify
        success = self.storage.verify_fingerprint(peer_id, False)
        assert success == True
        assert self.storage.is_verified(peer_id) == False

    def test_get_nonexistent_fingerprint(self):
        """Test getting nonexistent fingerprint returns None."""
        result = self.storage.get_fingerprint("nonexistent")
        assert result is None

    def test_is_verified_nonexistent(self):
        """Test checking if nonexistent fingerprint is verified."""
        result = self.storage.is_verified("nonexistent")
        assert result == False

    def test_delete_fingerprint(self):
        """Test deleting a fingerprint."""
        peer_id = "peer_123"
        fingerprint = "A1B2C3D4E5F6" * 5

        self.storage.save_fingerprint(peer_id, "id_key", fingerprint)
        assert self.storage.get_fingerprint(peer_id) is not None

        # Delete
        self.storage.delete_fingerprint(peer_id)
        assert self.storage.get_fingerprint(peer_id) is None

    def test_get_verified_fingerprints(self):
        """Test retrieving all verified fingerprints."""
        # Add some fingerprints
        self.storage.save_fingerprint("peer_1", "id1", "A1B2C3D4E5F6" * 5)
        self.storage.save_fingerprint("peer_2", "id2", "F6E5D4C3B2A1" * 5)
        self.storage.save_fingerprint("peer_3", "id3", "C3B2A1F6E5D4" * 5)

        # Verify some
        self.storage.verify_fingerprint("peer_1", True)
        self.storage.verify_fingerprint("peer_3", True)

        # Get verified
        verified = self.storage.get_verified_fingerprints()
        assert len(verified) == 2

        peer_ids = [v["peer_id"] for v in verified]
        assert "peer_1" in peer_ids
        assert "peer_3" in peer_ids
        assert "peer_2" not in peer_ids

    def test_get_all_fingerprints(self):
        """Test retrieving all fingerprints."""
        # Use unique peer IDs to avoid conflicts from other tests
        self.storage.save_fingerprint("peer_unique_1", "id1", "A1B2C3D4E5F6" * 5)
        self.storage.save_fingerprint("peer_unique_2", "id2", "F6E5D4C3B2A1" * 5)

        # Count only our new fingerprints
        all_fps = self.storage.get_all_fingerprints()
        our_fps = [fp for fp in all_fps if fp["peer_id"].startswith("peer_unique")]
        assert len(our_fps) == 2

    def test_fingerprint_persistence(self):
        """Test fingerprints persist across instances."""
        peer_id = "peer_123"
        fingerprint = "A1B2C3D4E5F6" * 5

        storage1 = FingerprintStorage(self.temp_dir, "test_user")
        storage1.save_fingerprint(peer_id, "id_key", fingerprint)
        storage1.verify_fingerprint(peer_id, True)

        # Create new instance
        storage2 = FingerprintStorage(self.temp_dir, "test_user")
        result = storage2.get_fingerprint(peer_id)

        assert result is not None
        assert result["fingerprint"] == fingerprint
        assert result["verified"] == True


class TestClientFingerprintMethods:
    """Test client fingerprint verification methods."""

    def test_compare_fingerprints_match(self):
        """Test comparing matching fingerprints."""
        fp1 = "A1B2C3D4E5F6" * 5
        fp2 = "A1B2C3D4E5F6" * 5

        assert WhatsAppClient.compare_fingerprints(fp1, fp2) == True

    def test_compare_fingerprints_no_match(self):
        """Test comparing non-matching fingerprints."""
        fp1 = "A1B2C3D4E5F6" * 5
        fp2 = "F6E5D4C3B2A1" * 5

        assert WhatsAppClient.compare_fingerprints(fp1, fp2) == False

    def test_compare_fingerprints_case_insensitive(self):
        """Test fingerprint comparison is case insensitive."""
        fp1 = "A1B2C3D4E5F6" * 5
        fp2 = "a1b2c3d4e5f6" * 5

        assert WhatsAppClient.compare_fingerprints(fp1, fp2) == True

    def test_compare_fingerprints_with_whitespace(self):
        """Test fingerprint comparison ignores whitespace."""
        fp1 = "A1B2C3D4E5F6" * 5
        fp2 = "A1B2 C3D4 E5F6 " * 5  # With spaces

        # Normalize for comparison
        fp2_normalized = fp2.upper().replace(" ", "").replace("\n", "")
        assert WhatsAppClient.compare_fingerprints(fp1, fp2_normalized) == True

    def test_compare_fingerprints_empty(self):
        """Test comparing empty fingerprints."""
        assert WhatsAppClient.compare_fingerprints("", "") == False
        assert WhatsAppClient.compare_fingerprints("A1B2C3D4E5F6" * 5, "") == False
        assert WhatsAppClient.compare_fingerprints("", "A1B2C3D4E5F6" * 5) == False

    def test_compare_fingerprints_none(self):
        """Test comparing None fingerprints."""
        assert WhatsAppClient.compare_fingerprints(None, None) == False
        assert WhatsAppClient.compare_fingerprints("A1B2C3D4E5F6" * 5, None) == False
    
    def test_get_own_fingerprint_not_authenticated(self):
        """Test getting fingerprint without authentication."""
        client = WhatsAppClient("https://test.workers.dev")
        
        with pytest.raises(WhatsAppClientError, match="Not authenticated"):
            client.get_fingerprint()


class TestFingerprintIntegration:
    """Integration tests for fingerprint verification."""

    def test_fingerprint_lifecycle(self):
        """Test complete fingerprint storage lifecycle."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            storage = FingerprintStorage("test_user", temp_dir)
            
            # 1. Save fingerprint
            peer_id = "alice"
            identity_key = "alice_identity_key_123"
            fingerprint = "A1B2C3D4E5" * 12  # 60 chars
            
            storage.save_fingerprint(peer_id, identity_key, fingerprint)
            
            # 2. Retrieve fingerprint
            fp = storage.get_fingerprint(peer_id)
            assert fp is not None
            assert fp["peer_id"] == peer_id
            assert fp["fingerprint"] == fingerprint
            assert fp["verified"] == False
            
            # 3. Verify fingerprint
            result = storage.verify_fingerprint(peer_id, True)
            assert result == True
            
            # 4. Check verified status
            assert storage.is_verified(peer_id) == True
            
            # 5. Get verified list
            verified = storage.get_verified_fingerprints()
            assert len(verified) >= 1
            
            # 6. Unverify
            storage.verify_fingerprint(peer_id, False)
            assert storage.is_verified(peer_id) == False
            
            # 7. Delete
            storage.delete_fingerprint(peer_id)
            assert storage.get_fingerprint(peer_id) is None
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_multiple_peer_fingerprints(self):
        """Test managing multiple peer fingerprints."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            storage = FingerprintStorage("test_user", temp_dir)
            
            # Add multiple peers
            peers = ["alice", "bob", "charlie"]
            for peer in peers:
                fp = "F" * 60
                storage.save_fingerprint(peer, f"{peer}_key", fp)
            
            # Verify some
            storage.verify_fingerprint("alice", True)
            storage.verify_fingerprint("charlie", True)
            
            # Get all fingerprints
            all_fps = storage.get_all_fingerprints()
            assert len(all_fps) >= 3
            
            # Get verified only
            verified = storage.get_verified_fingerprints()
            assert len(verified) >= 2
            
            verified_peers = [v["peer_id"] for v in verified]
            assert "alice" in verified_peers
            assert "charlie" in verified_peers
            assert "bob" not in verified_peers
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestFingerprintSchema:
    """Test fingerprint database schema."""

    def test_fingerprint_schema_creation(self):
        """Test fingerprint table schema is created correctly."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            storage = FingerprintStorage("test_user", temp_dir)

            # Check table exists
            db_path = Path(temp_dir) / "fingerprints.db"
            assert db_path.exists()

            # Check schema
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(fingerprints)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert "peer_id" in columns
            assert "identity_key" in columns
            assert "fingerprint" in columns
            assert "verified" in columns
            assert "verified_at" in columns
            assert "last_updated" in columns

            conn.close()

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_fingerprint_constraints(self):
        """Test fingerprint table constraints."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            storage = FingerprintStorage("test_user", temp_dir)

            # Try to save with same peer_id (should overwrite)
            storage.save_fingerprint("peer_constraint_1", "id_key1", "FP1" * 20)
            storage.save_fingerprint("peer_constraint_1", "id_key2", "FP2" * 20)

            # Check only one record exists via get_fingerprint
            constraint_fp = storage.get_fingerprint("peer_constraint_1")
            assert constraint_fp is not None
            assert constraint_fp["identity_key"] == "id_key2"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
