"""Group chat storage and management."""

import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GroupStorage:
    """Store and manage group chats."""

    def __init__(self, storage_path: str, user_id: str):
        """
        Initialize group storage.

        Args:
            storage_path: Base storage directory path
            user_id: Current user ID
        """
        self.user_id = user_id
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.db_path = self.storage_path / "groups.db"
        self._init_db()

        logger.debug(f"Initialized group storage at {self.db_path}")

    def _init_db(self) -> None:
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Groups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # Group members table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at INTEGER NOT NULL,
                    PRIMARY KEY (group_id, user_id),
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            """)

            # Group messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_messages (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    from_user TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            """)

            conn.commit()
            logger.debug("Group storage tables initialized")

        except Exception as e:
            logger.error(f"Failed to initialize group storage: {e}")
            conn.rollback()
        finally:
            conn.close()

    def create_group(
        self,
        name: str,
        description: Optional[str] = None,
        member_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Create a new group.

        Args:
            name: Group name
            description: Optional group description
            member_ids: List of initial member IDs (excluding creator)

        Returns:
            Dict with group data
        """
        import time

        group_id = str(uuid.uuid4())
        now = int(time.time())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Create group
            cursor.execute("""
                INSERT INTO groups (id, name, description, owner_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (group_id, name, description, self.user_id, now, now))

            # Add creator as owner
            cursor.execute("""
                INSERT INTO group_members (group_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            """, (group_id, self.user_id, "owner", now))

            # Add other members
            if member_ids:
                for member_id in member_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at)
                        VALUES (?, ?, ?, ?)
                    """, (group_id, member_id, "member", now))

            conn.commit()
            logger.info(f"Created group {group_id}: {name}")

            return {
                "id": group_id,
                "name": name,
                "description": description,
                "owner_id": self.user_id,
                "created_at": now,
                "updated_at": now,
                "members": [
                    {"user_id": self.user_id, "role": "owner"},
                    *[{"user_id": m, "role": "member"} for m in (member_ids or [])]
                ],
            }

        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_group(self, group_id: str) -> Optional[Dict]:
        """
        Get group metadata.

        Args:
            group_id: Group ID

        Returns:
            Dict with group data or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM groups WHERE id = ?",
                (group_id,)
            )
            row = cursor.fetchone()

            if row:
                # Get members
                cursor.execute(
                    "SELECT user_id, role FROM group_members WHERE group_id = ?",
                    (group_id,)
                )
                members = [dict(m) for m in cursor.fetchall()]

                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "owner_id": row["owner_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "members": members,
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get group: {e}")
            return None
        finally:
            conn.close()

    def get_groups(self) -> List[Dict]:
        """
        Get all groups current user is member of.

        Returns:
            List of group dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get groups where user is member
            cursor.execute("""
                SELECT g.* FROM groups g
                INNER JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ?
                ORDER BY g.updated_at DESC
            """, (self.user_id,))

            groups = []
            for row in cursor.fetchall():
                # Get members for each group
                cursor.execute(
                    "SELECT user_id, role FROM group_members WHERE group_id = ?",
                    (row["id"],)
                )
                members = [dict(m) for m in cursor.fetchall()]

                groups.append({
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "owner_id": row["owner_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "members": members,
                })

            return groups

        except Exception as e:
            logger.error(f"Failed to get groups: {e}")
            return []
        finally:
            conn.close()

    def add_member(self, group_id: str, member_id: str, role: str = "member") -> bool:
        """
        Add member to group.

        Args:
            group_id: Group ID
            member_id: User ID to add
            role: Member role (default: member)

        Returns:
            True if successful
        """
        import time

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = int(time.time())

            cursor.execute("""
                INSERT OR IGNORE INTO group_members (group_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            """, (group_id, member_id, role, now))

            cursor.execute(
                "UPDATE groups SET updated_at = ? WHERE id = ?",
                (now, group_id)
            )

            conn.commit()
            logger.info(f"Added {member_id} to group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def remove_member(self, group_id: str, member_id: str) -> bool:
        """
        Remove member from group.

        Args:
            group_id: Group ID
            member_id: User ID to remove

        Returns:
            True if successful
        """
        import time

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM group_members WHERE group_id = ? AND user_id = ?",
                (group_id, member_id)
            )

            now = int(time.time())
            cursor.execute(
                "UPDATE groups SET updated_at = ? WHERE id = ?",
                (now, group_id)
            )

            conn.commit()
            logger.info(f"Removed {member_id} from group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def save_group_message(
        self,
        group_id: str,
        from_user: str,
        content: str,
    ) -> bool:
        """
        Save group message.

        Args:
            group_id: Group ID
            from_user: Sender user ID
            content: Message content

        Returns:
            True if successful
        """
        import time

        message_id = str(uuid.uuid4())
        now = int(time.time())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO group_messages (id, group_id, from_user, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, group_id, from_user, content, now))

            cursor.execute(
                "UPDATE groups SET updated_at = ? WHERE id = ?",
                (now, group_id)
            )

            conn.commit()
            logger.debug(f"Saved message {message_id} to group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save group message: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_group_messages(self, group_id: str, limit: int = 50) -> List[Dict]:
        """
        Get group messages.

        Args:
            group_id: Group ID
            limit: Max messages to retrieve

        Returns:
            List of message dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM group_messages
                WHERE group_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (group_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "id": row["id"],
                    "group_id": row["group_id"],
                    "from_user": row["from_user"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                })

            return messages

        except Exception as e:
            logger.error(f"Failed to get group messages: {e}")
            return []
        finally:
            conn.close()

    def is_member(self, group_id: str, user_id: str) -> bool:
        """
        Check if user is member of group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            True if user is member
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?",
                (group_id, user_id)
            )
            return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check membership: {e}")
            return False
        finally:
            conn.close()

    def is_owner(self, group_id: str, user_id: str) -> bool:
        """
        Check if user is owner of group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            True if user is owner
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ? AND role = 'owner'",
                (group_id, user_id)
            )
            return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check ownership: {e}")
            return False
        finally:
            conn.close()

    def get_member_role(self, group_id: str, user_id: str) -> Optional[str]:
        """
        Get member role in group.

        Args:
            group_id: Group ID
            user_id: User ID

        Returns:
            Role string or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT role FROM group_members WHERE group_id = ? AND user_id = ?",
                (group_id, user_id)
            )
            row = cursor.fetchone()
            return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to get member role: {e}")
            return None
        finally:
            conn.close()

    def delete_group(self, group_id: str) -> bool:
        """
        Delete group (owner only).

        Args:
            group_id: Group ID

        Returns:
            True if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete group messages
            cursor.execute(
                "DELETE FROM group_messages WHERE group_id = ?",
                (group_id,)
            )

            # Delete group members
            cursor.execute(
                "DELETE FROM group_members WHERE group_id = ?",
                (group_id,)
            )

            # Delete group
            cursor.execute(
                "DELETE FROM groups WHERE id = ?",
                (group_id,)
            )

            conn.commit()
            logger.info(f"Deleted group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete group: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
