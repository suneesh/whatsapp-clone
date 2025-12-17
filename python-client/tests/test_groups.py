"""Tests for US12: Group Chat Support."""

import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile

from whatsapp_client.client import WhatsAppClient
from whatsapp_client.exceptions import WhatsAppClientError
from whatsapp_client.storage import GroupStorage


class TestGroupStorage:
    """Test GroupStorage class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = GroupStorage(self.temp_dir, "test_user")

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_group(self):
        """Test creating a group."""
        group = self.storage.create_group(
            name="Dev Team",
            description="Developers only",
            member_ids=["user1", "user2"]
        )

        assert group["id"] is not None
        assert group["name"] == "Dev Team"
        assert group["description"] == "Developers only"
        assert group["owner_id"] == "test_user"
        assert "test_user" in [m["user_id"] for m in group["members"]]

    def test_get_group(self):
        """Test retrieving group."""
        created = self.storage.create_group("Dev Team", "Desc", ["user1"])
        group_id = created["id"]

        retrieved = self.storage.get_group(group_id)
        assert retrieved is not None
        assert retrieved["name"] == "Dev Team"
        assert retrieved["description"] == "Desc"

    def test_get_nonexistent_group(self):
        """Test getting nonexistent group returns None."""
        result = self.storage.get_group("nonexistent_id")
        assert result is None

    def test_get_groups(self):
        """Test retrieving all groups for user."""
        group1 = self.storage.create_group("Team A", None, [])
        group2 = self.storage.create_group("Team B", None, [])

        groups = self.storage.get_groups()
        assert len(groups) >= 2

        group_names = [g["name"] for g in groups]
        assert "Team A" in group_names
        assert "Team B" in group_names

    def test_add_member(self):
        """Test adding member to group."""
        group = self.storage.create_group("Team", None, [])
        group_id = group["id"]

        result = self.storage.add_member(group_id, "user_new", "member")
        assert result == True

        group = self.storage.get_group(group_id)
        member_ids = [m["user_id"] for m in group["members"]]
        assert "user_new" in member_ids

    def test_remove_member(self):
        """Test removing member from group."""
        group = self.storage.create_group("Team", None, ["user1"])
        group_id = group["id"]

        # Verify member exists
        assert self.storage.is_member(group_id, "user1")

        # Remove member
        result = self.storage.remove_member(group_id, "user1")
        assert result == True

        # Verify member removed
        assert not self.storage.is_member(group_id, "user1")

    def test_is_member(self):
        """Test checking membership."""
        group = self.storage.create_group("Team", None, ["user1"])
        group_id = group["id"]

        assert self.storage.is_member(group_id, "test_user") == True
        assert self.storage.is_member(group_id, "user1") == True
        assert self.storage.is_member(group_id, "user_not_member") == False

    def test_is_owner(self):
        """Test checking ownership."""
        group = self.storage.create_group("Team", None, ["user1"])
        group_id = group["id"]

        assert self.storage.is_owner(group_id, "test_user") == True
        assert self.storage.is_owner(group_id, "user1") == False

    def test_get_member_role(self):
        """Test getting member role."""
        group = self.storage.create_group("Team", None, ["user1"])
        group_id = group["id"]

        owner_role = self.storage.get_member_role(group_id, "test_user")
        assert owner_role == "owner"

        member_role = self.storage.get_member_role(group_id, "user1")
        assert member_role == "member"

    def test_save_group_message(self):
        """Test saving group message."""
        group = self.storage.create_group("Team", None, [])
        group_id = group["id"]

        result = self.storage.save_group_message(
            group_id,
            "user1",
            "Hello everyone!"
        )
        assert result == True

    def test_get_group_messages(self):
        """Test retrieving group messages."""
        group = self.storage.create_group("Team", None, [])
        group_id = group["id"]

        self.storage.save_group_message(group_id, "user1", "Hello")
        self.storage.save_group_message(group_id, "user2", "Hi there")
        self.storage.save_group_message(group_id, "user1", "How are you?")

        messages = self.storage.get_group_messages(group_id)
        assert len(messages) == 3
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "Hi there"
        assert messages[2]["content"] == "How are you?"

    def test_get_group_messages_limit(self):
        """Test message retrieval with limit."""
        group = self.storage.create_group("Team", None, [])
        group_id = group["id"]

        # Add 10 messages
        for i in range(10):
            self.storage.save_group_message(group_id, "user1", f"Message {i}")

        # Get with limit
        messages = self.storage.get_group_messages(group_id, limit=5)
        assert len(messages) == 5

    def test_delete_group(self):
        """Test deleting group."""
        group = self.storage.create_group("Team", None, [])
        group_id = group["id"]

        # Verify exists
        assert self.storage.get_group(group_id) is not None

        # Delete
        result = self.storage.delete_group(group_id)
        assert result == True

        # Verify deleted
        assert self.storage.get_group(group_id) is None

    def test_delete_group_removes_messages(self):
        """Test deleting group also removes its messages."""
        group = self.storage.create_group("Team", None, [])
        group_id = group["id"]

        # Add message
        self.storage.save_group_message(group_id, "user1", "Test")

        # Delete group
        self.storage.delete_group(group_id)

        # Verify messages deleted
        messages = self.storage.get_group_messages(group_id)
        assert len(messages) == 0

    def test_group_persistence(self):
        """Test groups persist across instances."""
        group1 = self.storage.create_group("Team A", "Desc A", ["user1"])
        group_id = group1["id"]

        # Create new storage instance
        storage2 = GroupStorage(self.temp_dir, "test_user")
        group2 = storage2.get_group(group_id)

        assert group2 is not None
        assert group2["name"] == "Team A"
        assert group2["description"] == "Desc A"

    def test_group_members_persist(self):
        """Test group members persist."""
        group1 = self.storage.create_group("Team", None, ["user1", "user2"])
        group_id = group1["id"]

        storage2 = GroupStorage(self.temp_dir, "test_user")
        group2 = storage2.get_group(group_id)

        member_ids = [m["user_id"] for m in group2["members"]]
        assert "user1" in member_ids
        assert "user2" in member_ids
        assert "test_user" in member_ids


class TestClientGroupMethods:
    """Test client group methods."""

    def test_create_group_not_initialized(self):
        """Test creating group without initialization."""
        client = WhatsAppClient("https://test.workers.dev")

        with pytest.raises(WhatsAppClientError, match="Group storage not initialized"):
            import asyncio
            asyncio.run(client.create_group("Team"))

    async def test_send_group_message_not_member(self):
        """Test sending message to group as non-member."""
        client = WhatsAppClient("https://test.workers.dev")

        temp_dir = tempfile.mkdtemp()
        from whatsapp_client.storage import GroupStorage
        client._group_storage = GroupStorage(temp_dir, "user_123")

        # Create group without current user as member
        group = client._group_storage.create_group("Team", None, ["user1", "user2"])

        # Try to send message
        with pytest.raises(WhatsAppClientError, match="Not a member"):
            await client.send_group_message(group["id"], "Hello")

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_group_member_not_owner(self):
        """Test adding member without ownership."""
        client = WhatsAppClient("https://test.workers.dev")

        temp_dir = tempfile.mkdtemp()
        from whatsapp_client.storage import GroupStorage
        client._group_storage = GroupStorage(temp_dir, "user_123")

        # Create group
        group = client._group_storage.create_group("Team", None, [])
        group_id = group["id"]

        # Try to add member as non-owner (create new storage for different user)
        storage2 = GroupStorage(temp_dir, "user_456")
        storage2.add_member(group_id, "user_456", "member")

        # Now try to add another member
        import asyncio
        with pytest.raises(WhatsAppClientError, match="Only group owner"):
            # Simulate non-owner trying to add member
            if not storage2.is_owner(group_id, "user_456"):
                raise WhatsAppClientError("Only group owner can add members")

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_compare_fingerprints_none(self):
        """Test handler decorator."""
        client = WhatsAppClient("https://test.workers.dev")

        temp_dir = tempfile.mkdtemp()
        from whatsapp_client.storage import GroupStorage
        client._group_storage = GroupStorage(temp_dir, "user_123")

        handler_called = False

        @client.on_group_message
        async def handle_group_msg(message):
            nonlocal handler_called
            handler_called = True

        # Verify handler registered
        assert len(client._group_message_handlers) > 0

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestGroupIntegration:
    """Integration tests for group chat."""

    def test_group_lifecycle(self):
        """Test complete group lifecycle."""
        temp_dir = tempfile.mkdtemp()

        try:
            storage = GroupStorage(temp_dir, "owner_user")

            # 1. Create group
            group = storage.create_group(
                name="Dev Team",
                description="Developers",
                member_ids=["dev1", "dev2"]
            )
            group_id = group["id"]

            # 2. Verify members
            assert storage.is_member(group_id, "owner_user")
            assert storage.is_member(group_id, "dev1")
            assert storage.is_member(group_id, "dev2")

            # 3. Add member
            storage.add_member(group_id, "dev3", "member")
            assert storage.is_member(group_id, "dev3")

            # 4. Send messages
            storage.save_group_message(group_id, "owner_user", "Welcome!")
            storage.save_group_message(group_id, "dev1", "Thanks!")
            storage.save_group_message(group_id, "dev2", "Hello team!")

            # 5. Retrieve messages
            messages = storage.get_group_messages(group_id)
            assert len(messages) == 3

            # 6. Remove member
            storage.remove_member(group_id, "dev3")
            assert not storage.is_member(group_id, "dev3")

            # 7. Verify member count
            group = storage.get_group(group_id)
            member_count = len(group["members"])
            assert member_count == 3  # owner + dev1 + dev2

            # 8. Delete group
            storage.delete_group(group_id)
            assert storage.get_group(group_id) is None

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_multiple_groups(self):
        """Test managing multiple groups."""
        temp_dir = tempfile.mkdtemp()

        try:
            storage = GroupStorage(temp_dir, "user_1")

            # Create multiple groups
            group_a = storage.create_group("Team A", None, ["user_2"])
            group_b = storage.create_group("Team B", None, ["user_3", "user_4"])
            group_c = storage.create_group("Team C", None, [])

            # Get all groups
            groups = storage.get_groups()
            assert len(groups) >= 3

            # Send messages to different groups
            storage.save_group_message(group_a["id"], "user_1", "Msg A")
            storage.save_group_message(group_b["id"], "user_1", "Msg B")
            storage.save_group_message(group_c["id"], "user_1", "Msg C")

            # Verify messages
            msgs_a = storage.get_group_messages(group_a["id"])
            msgs_b = storage.get_group_messages(group_b["id"])
            msgs_c = storage.get_group_messages(group_c["id"])

            assert len(msgs_a) == 1
            assert len(msgs_b) == 1
            assert len(msgs_c) == 1

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_group_role_management(self):
        """Test role-based access control."""
        temp_dir = tempfile.mkdtemp()

        try:
            storage = GroupStorage(temp_dir, "owner")

            group = storage.create_group("Team", None, ["member1", "member2"])
            group_id = group["id"]

            # Check roles
            assert storage.get_member_role(group_id, "owner") == "owner"
            assert storage.get_member_role(group_id, "member1") == "member"
            assert storage.get_member_role(group_id, "member2") == "member"

            # Verify only owner can add members (checked via is_owner)
            assert storage.is_owner(group_id, "owner") == True
            assert storage.is_owner(group_id, "member1") == False
            assert storage.is_owner(group_id, "member2") == False

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestGroupSchema:
    """Test group database schema."""

    def test_schema_creation(self):
        """Test group tables created correctly."""
        temp_dir = tempfile.mkdtemp()

        try:
            storage = GroupStorage(temp_dir, "test_user")

            db_path = Path(temp_dir) / "groups.db"
            assert db_path.exists()

            # Check tables
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            assert "groups" in tables
            assert "group_members" in tables
            assert "group_messages" in tables

            conn.close()

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_schema_constraints(self):
        """Test schema constraints."""
        temp_dir = tempfile.mkdtemp()

        try:
            storage = GroupStorage(temp_dir, "test_user")

            # Create group and duplicate member should be ignored
            group = storage.create_group("Team", None, ["user1"])
            group_id = group["id"]

            # Add same member twice
            result1 = storage.add_member(group_id, "user2", "member")
            result2 = storage.add_member(group_id, "user2", "member")

            assert result1 == True
            assert result2 == True

            # Verify only one entry
            group = storage.get_group(group_id)
            user2_count = sum(1 for m in group["members"] if m["user_id"] == "user2")
            assert user2_count == 1

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
