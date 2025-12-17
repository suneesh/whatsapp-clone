"""Fingerprint verification storage and management."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class FingerprintStorage:
    """Store and manage fingerprint verifications."""
    
    def __init__(self, user_id: str, storage_path: str):
        """
        Initialize fingerprint storage.
        
        Args:
            user_id: Current user ID
            storage_path: Base storage directory path
        """
        self.user_id = user_id
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.storage_path / "fingerprints.db"
        self._init_db()
        
        logger.debug(f"Initialized fingerprint storage at {self.db_path}")
    
    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fingerprints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fingerprints (
                peer_id TEXT PRIMARY KEY,
                identity_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                verified_at INTEGER,
                last_updated INTEGER NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Index for verified fingerprints
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_verified ON fingerprints(verified)
        """)
        
        conn.commit()
        conn.close()
    
    def save_fingerprint(
        self,
        peer_id: str,
        identity_key: str,
        fingerprint: str,
        verified: bool = False,
    ) -> None:
        """
        Save or update a peer's fingerprint.
        
        Args:
            peer_id: Peer user ID
            identity_key: Raw identity key (base64)
            fingerprint: Computed fingerprint (60-char hex string)
            verified: Whether fingerprint is verified
        """
        import time
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = int(time.time())
            verified_at = now if verified else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO fingerprints (
                    peer_id, identity_key, fingerprint, verified, verified_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                peer_id,
                identity_key,
                fingerprint,
                1 if verified else 0,
                verified_at,
                now,
            ))
            
            conn.commit()
            logger.debug(f"Saved fingerprint for {peer_id}")
            
        except Exception as e:
            logger.error(f"Failed to save fingerprint: {e}")
        finally:
            conn.close()
    
    def get_fingerprint(self, peer_id: str) -> Optional[Dict]:
        """
        Get stored fingerprint for a peer.
        
        Args:
            peer_id: Peer user ID
            
        Returns:
            Dict with fingerprint data or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fingerprints WHERE peer_id = ?",
                (peer_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "peer_id": row["peer_id"],
                    "identity_key": row["identity_key"],
                    "fingerprint": row["fingerprint"],
                    "verified": bool(row["verified"]),
                    "verified_at": row["verified_at"],
                    "last_updated": row["last_updated"],
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get fingerprint: {e}")
            return None
        finally:
            conn.close()
    
    def verify_fingerprint(self, peer_id: str, verified: bool = True) -> bool:
        """
        Mark a fingerprint as verified or unverified.
        
        Args:
            peer_id: Peer user ID
            verified: Verification status
            
        Returns:
            True if successful, False otherwise
        """
        import time
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = int(time.time())
            verified_at = now if verified else None
            
            cursor.execute("""
                UPDATE fingerprints
                SET verified = ?, verified_at = ?, last_updated = ?
                WHERE peer_id = ?
            """, (
                1 if verified else 0,
                verified_at,
                now,
                peer_id,
            ))
            
            if cursor.rowcount == 0:
                logger.warning(f"Fingerprint for {peer_id} not found")
                return False
            
            conn.commit()
            logger.info(f"Verified fingerprint for {peer_id}: {verified}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify fingerprint: {e}")
            return False
        finally:
            conn.close()
    
    def is_verified(self, peer_id: str) -> bool:
        """
        Check if a peer's fingerprint is verified.
        
        Args:
            peer_id: Peer user ID
            
        Returns:
            True if verified, False otherwise
        """
        fp = self.get_fingerprint(peer_id)
        return fp["verified"] if fp else False
    
    def get_verified_fingerprints(self) -> List[Dict]:
        """
        Get all verified fingerprints.
        
        Returns:
            List of verified fingerprint records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fingerprints WHERE verified = 1 ORDER BY verified_at DESC"
            )
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    "peer_id": row["peer_id"],
                    "fingerprint": row["fingerprint"],
                    "verified_at": row["verified_at"],
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get verified fingerprints: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_fingerprints(self) -> List[Dict]:
        """
        Get all stored fingerprints.
        
        Returns:
            List of all fingerprint records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fingerprints ORDER BY last_updated DESC"
            )
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    "peer_id": row["peer_id"],
                    "fingerprint": row["fingerprint"],
                    "verified": bool(row["verified"]),
                    "last_updated": row["last_updated"],
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all fingerprints: {e}")
            return []
        finally:
            conn.close()
    
    def delete_fingerprint(self, peer_id: str) -> bool:
        """
        Delete stored fingerprint.
        
        Args:
            peer_id: Peer user ID
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM fingerprints WHERE peer_id = ?", (peer_id,))
            
            if cursor.rowcount == 0:
                return False
            
            conn.commit()
            logger.debug(f"Deleted fingerprint for {peer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete fingerprint: {e}")
            return False
        finally:
            conn.close()
