"""Session management for E2EE messaging."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

from nacl.public import PrivateKey
from nacl.encoding import RawEncoder

from .x3dh import X3DHProtocol
from ..models import PrekeyBundle, Session
from ..exceptions import WhatsAppClientError

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages encrypted sessions with other users.
    
    Handles session establishment using X3DH protocol and session persistence.
    """

    def __init__(self, user_id: str, storage_path: str):
        """
        Initialize session manager.
        
        Args:
            user_id: Current user's ID
            storage_path: Path to store session data
        """
        self.user_id = user_id
        self.storage_path = Path(storage_path).expanduser()
        self.sessions_dir = self.storage_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory session cache
        self._sessions: Dict[str, Session] = {}
        
        logger.info(f"SessionManager initialized for user {user_id}")
    
    def get_session(self, peer_id: str) -> Optional[Session]:
        """
        Get existing session with peer.
        
        Args:
            peer_id: Peer's user ID
            
        Returns:
            Session object or None if no session exists
        """
        # Check cache first
        if peer_id in self._sessions:
            return self._sessions[peer_id]
        
        # Load from disk
        session = self._load_session(peer_id)
        if session:
            self._sessions[peer_id] = session
        
        return session
    
    async def ensure_session(
        self,
        peer_id: str,
        identity_private_key: PrivateKey,
        fetch_prekey_bundle_callback,
        mark_prekey_used_callback
    ) -> Session:
        """
        Ensure session exists with peer, creating if necessary.
        
        Args:
            peer_id: Peer's user ID
            identity_private_key: Own identity private key
            fetch_prekey_bundle_callback: Async function to fetch peer's prekey bundle
            mark_prekey_used_callback: Async function to mark one-time prekey as used
            
        Returns:
            Session object
            
        Raises:
            WhatsAppClientError: If session establishment fails
        """
        # Check if session already exists
        session = self.get_session(peer_id)
        if session:
            logger.info(f"Using existing session with {peer_id}")
            return session
        
        # Establish new session using X3DH
        logger.info(f"Establishing new session with {peer_id}")
        
        # Fetch peer's prekey bundle
        prekey_bundle = await fetch_prekey_bundle_callback(peer_id)
        if not prekey_bundle:
            raise WhatsAppClientError(f"Failed to fetch prekey bundle for {peer_id}")
        
        # Verify signed prekey signature
        if not X3DHProtocol.verify_prekey_signature(
            prekey_bundle.signed_prekey,
            prekey_bundle.signature,
            prekey_bundle.signing_key
        ):
            raise WhatsAppClientError(f"Invalid prekey signature for {peer_id}")
        
        # Perform X3DH key agreement
        shared_secret, ephemeral_key, initial_message_key = X3DHProtocol.initiate_session(
            identity_private_key,
            prekey_bundle
        )
        
        # Create session record
        session = Session(
            session_id=f"{self.user_id}_{peer_id}_{datetime.now().timestamp()}",
            peer_id=peer_id,
            shared_secret=shared_secret.hex(),
            ephemeral_key=ephemeral_key.encode(encoder=RawEncoder).hex(),
            initial_message_key=initial_message_key.hex(),
            created_at=datetime.now().isoformat(),
            one_time_prekey_used=None
        )
        
        # Mark one-time prekey as used if it was consumed
        if prekey_bundle.one_time_prekeys and len(prekey_bundle.one_time_prekeys) > 0:
            one_time_prekey_id = prekey_bundle.one_time_prekeys[0]
            session.one_time_prekey_used = one_time_prekey_id
            
            try:
                await mark_prekey_used_callback(one_time_prekey_id)
                logger.info(f"Marked one-time prekey {one_time_prekey_id[:8]}... as used")
            except Exception as e:
                logger.warning(f"Failed to mark prekey as used: {e}")
        
        # Store session
        self._save_session(session)
        self._sessions[peer_id] = session
        
        logger.info(f"Session established with {peer_id}: {session.session_id}")
        return session
    
    def delete_session(self, peer_id: str) -> None:
        """
        Delete session with peer.
        
        Args:
            peer_id: Peer's user ID
        """
        # Remove from cache
        if peer_id in self._sessions:
            del self._sessions[peer_id]
        
        # Remove from disk
        session_file = self._get_session_file(peer_id)
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session with {peer_id}")
    
    def _get_session_file(self, peer_id: str) -> Path:
        """Get path to session file for peer."""
        return self.sessions_dir / f"{peer_id}.json"
    
    def _save_session(self, session: Session) -> None:
        """Save session to disk."""
        session_file = self._get_session_file(session.peer_id)
        
        session_data = {
            "session_id": session.session_id,
            "peer_id": session.peer_id,
            "shared_secret": session.shared_secret,
            "ephemeral_key": session.ephemeral_key,
            "initial_message_key": session.initial_message_key,
            "created_at": session.created_at,
            "one_time_prekey_used": session.one_time_prekey_used,
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(session_file, 0o600)
        
        logger.debug(f"Saved session to {session_file}")
    
    def _load_session(self, peer_id: str) -> Optional[Session]:
        """Load session from disk."""
        session_file = self._get_session_file(peer_id)
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            session = Session(
                session_id=session_data["session_id"],
                peer_id=session_data["peer_id"],
                shared_secret=session_data["shared_secret"],
                ephemeral_key=session_data["ephemeral_key"],
                initial_message_key=session_data["initial_message_key"],
                created_at=session_data["created_at"],
                one_time_prekey_used=session_data.get("one_time_prekey_used"),
            )
            
            logger.debug(f"Loaded session from {session_file}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session from {session_file}: {e}")
            return None
    
    def list_sessions(self) -> list[str]:
        """
        List all peer IDs with active sessions.
        
        Returns:
            List of peer user IDs
        """
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            peer_id = session_file.stem
            sessions.append(peer_id)
        return sessions
