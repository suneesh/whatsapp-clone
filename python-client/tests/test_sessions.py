"""Tests for session management and X3DH protocol."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from nacl.public import PrivateKey
from nacl.encoding import RawEncoder

from whatsapp_client import WhatsAppClient
from whatsapp_client.crypto import X3DHProtocol, SessionManager
from whatsapp_client.models import PrekeyBundle, Session


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def alice_keys():
    """Generate Alice's key pair."""
    identity_key = PrivateKey.generate()
    return {
        "private": identity_key,
        "public": identity_key.public_key.encode(encoder=RawEncoder).hex()
    }


@pytest.fixture
def bob_keys():
    """Generate Bob's key bundle."""
    from nacl.signing import SigningKey
    
    identity_key = PrivateKey.generate()
    signing_key = SigningKey.generate()
    signed_prekey = PrivateKey.generate()
    one_time_prekeys = [PrivateKey.generate() for _ in range(3)]
    
    # Create signature for signed prekey
    signed_prekey_bytes = signed_prekey.public_key.encode(encoder=RawEncoder)
    signature = signing_key.sign(signed_prekey_bytes).signature
    
    return {
        "identity_private": identity_key,
        "identity_public": identity_key.public_key.encode(encoder=RawEncoder).hex(),
        "signing_private": signing_key,
        "signing_public": signing_key.verify_key.encode(encoder=RawEncoder).hex(),
        "signed_prekey_private": signed_prekey,
        "signed_prekey_public": signed_prekey.public_key.encode(encoder=RawEncoder).hex(),
        "signature": signature.hex(),
        "one_time_prekeys": [k.public_key.encode(encoder=RawEncoder).hex() for k in one_time_prekeys]
    }


@pytest.fixture
def prekey_bundle(bob_keys):
    """Create prekey bundle for Bob."""
    return PrekeyBundle(
        identity_key=bob_keys["identity_public"],
        signing_key=bob_keys["signing_public"],
        fingerprint="a" * 60,  # Mock fingerprint
        signed_prekey=bob_keys["signed_prekey_public"],
        signature=bob_keys["signature"],
        one_time_prekeys=bob_keys["one_time_prekeys"]
    )


@pytest.mark.asyncio
async def test_x3dh_session_initiation(alice_keys, prekey_bundle):
    """Test X3DH protocol session initiation."""
    shared_secret, ephemeral_key, initial_message_key = X3DHProtocol.initiate_session(
        alice_keys["private"],
        prekey_bundle
    )
    
    # Verify outputs
    assert isinstance(shared_secret, bytes)
    assert len(shared_secret) == 32
    assert isinstance(ephemeral_key, PrivateKey)
    assert isinstance(initial_message_key, bytes)
    assert len(initial_message_key) == 32


@pytest.mark.asyncio
async def test_x3dh_without_one_time_prekey(alice_keys, bob_keys):
    """Test X3DH when no one-time prekey is available."""
    bundle = PrekeyBundle(
        identity_key=bob_keys["identity_public"],
        signing_key=bob_keys["signing_public"],
        fingerprint="a" * 60,
        signed_prekey=bob_keys["signed_prekey_public"],
        signature=bob_keys["signature"],
        one_time_prekeys=[]  # No one-time prekeys
    )
    
    shared_secret, ephemeral_key, initial_message_key = X3DHProtocol.initiate_session(
        alice_keys["private"],
        bundle
    )
    
    assert isinstance(shared_secret, bytes)
    assert len(shared_secret) == 32


@pytest.mark.asyncio
async def test_prekey_signature_verification(bob_keys):
    """Test signed prekey signature verification."""
    is_valid = X3DHProtocol.verify_prekey_signature(
        bob_keys["signed_prekey_public"],
        bob_keys["signature"],
        bob_keys["signing_public"]
    )
    
    assert is_valid is True


@pytest.mark.asyncio
async def test_invalid_signature_rejected(bob_keys):
    """Test that invalid signatures are rejected."""
    # Create invalid signature
    invalid_signature = "0" * 128
    
    is_valid = X3DHProtocol.verify_prekey_signature(
        bob_keys["signed_prekey_public"],
        invalid_signature,
        bob_keys["signing_public"]
    )
    
    assert is_valid is False


@pytest.mark.asyncio
async def test_session_manager_initialization(temp_storage):
    """Test session manager initialization."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    assert manager.user_id == "alice_user_id"
    assert manager.sessions_dir.exists()
    assert manager.sessions_dir.is_dir()


@pytest.mark.asyncio
async def test_session_persistence(temp_storage, alice_keys, prekey_bundle):
    """Test session is saved and loaded correctly."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    # Create mock session
    shared_secret, ephemeral_key, initial_message_key = X3DHProtocol.initiate_session(
        alice_keys["private"],
        prekey_bundle
    )
    
    session = Session(
        session_id="test_session_123",
        peer_id="bob_user_id",
        shared_secret=shared_secret.hex(),
        ephemeral_key=ephemeral_key.encode(encoder=RawEncoder).hex(),
        initial_message_key=initial_message_key.hex(),
        created_at="2025-12-16T10:00:00",
        one_time_prekey_used=prekey_bundle.one_time_prekeys[0]
    )
    
    # Save session
    manager._save_session(session)
    
    # Load session
    loaded_session = manager._load_session("bob_user_id")
    
    assert loaded_session is not None
    assert loaded_session.session_id == session.session_id
    assert loaded_session.peer_id == session.peer_id
    assert loaded_session.shared_secret == session.shared_secret


@pytest.mark.asyncio
async def test_get_session_from_cache(temp_storage):
    """Test getting session from memory cache."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    # Create mock session
    session = Session(
        session_id="test_session_123",
        peer_id="bob_user_id",
        shared_secret="a" * 64,
        ephemeral_key="b" * 64,
        initial_message_key="c" * 64,
        created_at="2025-12-16T10:00:00",
        one_time_prekey_used=None
    )
    
    # Add to cache
    manager._sessions["bob_user_id"] = session
    
    # Get from cache
    cached_session = manager.get_session("bob_user_id")
    
    assert cached_session is not None
    assert cached_session.session_id == session.session_id


@pytest.mark.asyncio
async def test_delete_session(temp_storage):
    """Test session deletion."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    session = Session(
        session_id="test_session_123",
        peer_id="bob_user_id",
        shared_secret="a" * 64,
        ephemeral_key="b" * 64,
        initial_message_key="c" * 64,
        created_at="2025-12-16T10:00:00",
        one_time_prekey_used=None
    )
    
    # Save and cache
    manager._save_session(session)
    manager._sessions["bob_user_id"] = session
    
    # Delete session
    manager.delete_session("bob_user_id")
    
    # Verify deletion
    assert "bob_user_id" not in manager._sessions
    assert not manager._get_session_file("bob_user_id").exists()


@pytest.mark.asyncio
async def test_list_sessions(temp_storage):
    """Test listing all sessions."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    # Create multiple sessions
    for peer_id in ["bob", "charlie", "david"]:
        session = Session(
            session_id=f"session_{peer_id}",
            peer_id=peer_id,
            shared_secret="a" * 64,
            ephemeral_key="b" * 64,
            initial_message_key="c" * 64,
            created_at="2025-12-16T10:00:00",
            one_time_prekey_used=None
        )
        manager._save_session(session)
    
    # List sessions
    sessions = manager.list_sessions()
    
    assert len(sessions) == 3
    assert "bob" in sessions
    assert "charlie" in sessions
    assert "david" in sessions


@pytest.mark.asyncio
async def test_ensure_session_creates_new(temp_storage, alice_keys, prekey_bundle):
    """Test ensure_session creates new session when none exists."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    # Mock callbacks
    async def fetch_bundle(peer_id):
        return prekey_bundle
    
    async def mark_used(prekey_id):
        pass
    
    # Ensure session
    session = await manager.ensure_session(
        "bob_user_id",
        alice_keys["private"],
        fetch_bundle,
        mark_used
    )
    
    assert session is not None
    assert session.peer_id == "bob_user_id"
    assert len(session.shared_secret) == 64  # 32 bytes hex encoded
    assert session.one_time_prekey_used == prekey_bundle.one_time_prekeys[0]


@pytest.mark.asyncio
async def test_ensure_session_reuses_existing(temp_storage, alice_keys):
    """Test ensure_session returns existing session."""
    manager = SessionManager("alice_user_id", temp_storage)
    
    # Create existing session
    existing_session = Session(
        session_id="existing_session",
        peer_id="bob_user_id",
        shared_secret="a" * 64,
        ephemeral_key="b" * 64,
        initial_message_key="c" * 64,
        created_at="2025-12-16T10:00:00",
        one_time_prekey_used=None
    )
    manager._sessions["bob_user_id"] = existing_session
    
    # Mock callbacks (should not be called)
    fetch_bundle = AsyncMock()
    mark_used = AsyncMock()
    
    # Ensure session
    session = await manager.ensure_session(
        "bob_user_id",
        alice_keys["private"],
        fetch_bundle,
        mark_used
    )
    
    assert session.session_id == "existing_session"
    fetch_bundle.assert_not_called()
    mark_used.assert_not_called()


@pytest.mark.asyncio
async def test_client_ensure_session_integration(temp_storage):
    """Test WhatsAppClient.ensure_session integration."""
    client = WhatsAppClient(server_url="http://localhost:8787", storage_path=temp_storage)
    
    # Mock login
    mock_user = {
        "id": "alice_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJhbGljZV91c2VyX2lkIiwiZXhwIjo5OTk5OTk5OTk5fQ.test_token",
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    mock_prekey_bundle = {
        "identityKey": "a" * 64,
        "signingKey": "b" * 64,
        "fingerprint": "c" * 60,
        "signedPrekey": {
            "keyId": 1,
            "publicKey": "d" * 64,
            "signature": "e" * 128,
            "createdAt": 1234567890,
        },
        "oneTimePrekey": {
            "keyId": 1,
            "publicKey": "f" * 64,
        }
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        with patch.object(client._rest, "get", new=AsyncMock(return_value=mock_prekey_bundle)):
            with patch.object(client._rest, "delete", new=AsyncMock(return_value={"status": "ok"})):
                with patch("whatsapp_client.crypto.x3dh.X3DHProtocol.verify_prekey_signature", return_value=True):
                    await client.login("alice", "password123")
                    
                    # Ensure session
                    session = await client.ensure_session("bob_user_id")
                    
                    assert session is not None
                    assert session.peer_id == "bob_user_id"


@pytest.mark.asyncio
async def test_client_get_session(temp_storage):
    """Test WhatsAppClient.get_session."""
    client = WhatsAppClient(server_url="http://localhost:8787", storage_path=temp_storage)
    
    # Before login
    session = client.get_session("bob_user_id")
    assert session is None
    
    # Mock login
    mock_user = {
        "id": "alice_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
        
        # After login, still no session
        session = client.get_session("bob_user_id")
        assert session is None


@pytest.mark.asyncio
async def test_client_list_sessions(temp_storage):
    """Test WhatsAppClient.list_sessions."""
    client = WhatsAppClient(server_url="http://localhost:8787", storage_path=temp_storage)
    
    # Before login
    sessions = client.list_sessions()
    assert sessions == []
    
    # Mock login
    mock_user = {
        "id": "alice_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    mock_upload_response = {
        "success": True,
        "signedPrekeyUploaded": True,
        "oneTimePrekeysUploaded": 100,
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response])):
        await client.login("alice", "password123")
        
        # After login
        sessions = client.list_sessions()
        assert sessions == []
