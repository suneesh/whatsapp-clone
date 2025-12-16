"""Message storage and persistence."""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models import Message
from ..exceptions import WhatsAppClientError

logger = logging.getLogger(__name__)


class MessageStorage:
    """
    Local message storage using SQLite.
    
    Stores messages, handles message history, and provides search capabilities.
    """
    
    def __init__(self, storage_path: str, user_id: str):
        """
        Initialize message storage.
        
        Args:
            storage_path: Base storage directory
            user_id: Current user ID
        """
        self.storage_path = Path(storage_path).expanduser()
        self.user_id = user_id
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Database path
        self.db_path = self.storage_path / f"{user_id}_messages.db"
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                from_user TEXT NOT NULL,
                to_user TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                status TEXT,
                encrypted INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Indexes for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_from_user ON messages(from_user)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_to_user ON messages(to_user)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp DESC)
        """)
        
        # Create conversation view for easy querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation ON messages(
                from_user, to_user, timestamp DESC
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Initialized message database: {self.db_path}")
    
    def save_message(self, message: Message) -> None:
        """
        Save a message to storage.
        
        Args:
            message: Message to save
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if message already exists (deduplication)
            cursor.execute("SELECT id FROM messages WHERE id = ?", (message.id,))
            if cursor.fetchone():
                logger.debug(f"Message {message.id} already exists, skipping")
                return
            
            # Insert message
            cursor.execute("""
                INSERT INTO messages (
                    id, from_user, to_user, content, type, timestamp, status, encrypted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.from_user,
                message.to,
                message.content,
                message.type,
                message.timestamp,
                message.status,
                1 if message.content.startswith("E2EE:") else 0,
            ))
            
            conn.commit()
            logger.debug(f"Saved message {message.id} to storage")
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            raise WhatsAppClientError(f"Failed to save message: {e}")
        finally:
            conn.close()
    
    def update_message_status(self, message_id: str, status: str) -> None:
        """
        Update message status.
        
        Args:
            message_id: Message ID
            status: New status (sent, delivered, read)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE messages SET status = ? WHERE id = ?
            """, (status, message_id))
            
            conn.commit()
            logger.debug(f"Updated message {message_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
        finally:
            conn.close()
    
    def get_messages(
        self,
        peer_id: str,
        limit: int = 50,
        before_timestamp: Optional[int] = None,
    ) -> List[Message]:
        """
        Get message history with a peer.
        
        Args:
            peer_id: Peer user ID
            limit: Maximum number of messages to return
            before_timestamp: Get messages before this timestamp (for pagination)
            
        Returns:
            List of messages in chronological order (oldest first)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Build query
            query = """
                SELECT * FROM messages
                WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)
            """
            params = [self.user_id, peer_id, peer_id, self.user_id]
            
            if before_timestamp:
                query += " AND timestamp < ?"
                params.append(before_timestamp)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to Message objects (reverse for chronological order)
            messages = []
            for row in reversed(rows):
                msg = Message(
                    id=row["id"],
                    from_user=row["from_user"],
                    to=row["to_user"],
                    content=row["content"],
                    type=row["type"],
                    timestamp=row["timestamp"],
                    status=row["status"],
                )
                messages.append(msg)
            
            logger.debug(f"Retrieved {len(messages)} messages with {peer_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
        finally:
            conn.close()
    
    def get_recent_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent conversations.
        
        Args:
            limit: Maximum number of conversations
            
        Returns:
            List of conversation summaries with last message
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get last message for each peer
            query = """
                WITH peer_messages AS (
                    SELECT 
                        CASE 
                            WHEN from_user = ? THEN to_user
                            ELSE from_user
                        END as peer_id,
                        MAX(timestamp) as last_timestamp
                    FROM messages
                    GROUP BY peer_id
                )
                SELECT 
                    m.id,
                    m.from_user,
                    m.to_user,
                    m.content,
                    m.type,
                    m.timestamp,
                    m.status,
                    pm.peer_id
                FROM messages m
                JOIN peer_messages pm ON (
                    m.timestamp = pm.last_timestamp AND
                    (
                        (m.from_user = ? AND m.to_user = pm.peer_id) OR
                        (m.to_user = ? AND m.from_user = pm.peer_id)
                    )
                )
                ORDER BY m.timestamp DESC
                LIMIT ?
            """
            
            cursor.execute(query, [self.user_id, self.user_id, self.user_id, limit])
            rows = cursor.fetchall()
            
            conversations = []
            for row in rows:
                conv = {
                    "peer_id": row["peer_id"],
                    "last_message": {
                        "id": row["id"],
                        "from_user": row["from_user"],
                        "to": row["to_user"],
                        "content": row["content"],
                        "type": row["type"],
                        "timestamp": row["timestamp"],
                        "status": row["status"],
                    }
                }
                conversations.append(conv)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return []
        finally:
            conn.close()
    
    def search_messages(
        self,
        query: str,
        peer_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Message]:
        """
        Search messages by content.
        
        Args:
            query: Search query
            peer_id: Optional peer ID to limit search
            limit: Maximum results
            
        Returns:
            List of matching messages
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Build query
            sql = """
                SELECT * FROM messages
                WHERE content LIKE ?
            """
            params = [f"%{query}%"]
            
            if peer_id:
                sql += " AND ((from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?))"
                params.extend([self.user_id, peer_id, peer_id, self.user_id])
            
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                msg = Message(
                    id=row["id"],
                    from_user=row["from_user"],
                    to=row["to_user"],
                    content=row["content"],
                    type=row["type"],
                    timestamp=row["timestamp"],
                    status=row["status"],
                )
                messages.append(msg)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            return []
        finally:
            conn.close()
    
    def delete_conversation(self, peer_id: str) -> int:
        """
        Delete all messages with a peer.
        
        Args:
            peer_id: Peer user ID
            
        Returns:
            Number of messages deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM messages
                WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)
            """, (self.user_id, peer_id, peer_id, self.user_id))
            
            deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Deleted {deleted} messages with {peer_id}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return 0
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total = cursor.fetchone()[0]
            
            # Messages sent
            cursor.execute("SELECT COUNT(*) FROM messages WHERE from_user = ?", (self.user_id,))
            sent = cursor.fetchone()[0]
            
            # Messages received
            cursor.execute("SELECT COUNT(*) FROM messages WHERE to_user = ?", (self.user_id,))
            received = cursor.fetchone()[0]
            
            # Encrypted messages
            cursor.execute("SELECT COUNT(*) FROM messages WHERE encrypted = 1")
            encrypted = cursor.fetchone()[0]
            
            # Unique peers
            cursor.execute("""
                SELECT COUNT(DISTINCT peer_id) FROM (
                    SELECT CASE 
                        WHEN from_user = ? THEN to_user
                        ELSE from_user
                    END as peer_id
                    FROM messages
                )
            """, (self.user_id,))
            peers = cursor.fetchone()[0]
            
            return {
                "total_messages": total,
                "messages_sent": sent,
                "messages_received": received,
                "encrypted_messages": encrypted,
                "unique_peers": peers,
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
        finally:
            conn.close()
