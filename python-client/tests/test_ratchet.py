"""Tests for Double Ratchet encryption/decryption (US4 & US5)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nacl.public import PrivateKey, PublicKey
from nacl.encoding import RawEncoder

from whatsapp_client import WhatsAppClient
from whatsapp_client.crypto import RatchetEngine, RatchetHeader, RatchetState
from whatsapp_client.models import Session
from whatsapp_client.exceptions import WhatsAppClientError


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory."""
    return str(tmp_path / "test_storage")


def test_ratchet_header_serialization():
    """Test RatchetHeader to_dict and from_dict."""
    header = RatchetHeader(
        dh_public_key="a" * 64,
        prev_chain_length=5,
        message_number=10,
    )
    
    # Serialize (Signal protocol format)
    data = header.to_dict()
    assert data["ratchetKey"] == "a" * 64
    assert data["previousChainLength"] == 5
    assert data["messageNumber"] == 10
    
    # Deserialize
    header2 = RatchetHeader.from_dict(data)
    assert header2.dh_public_key == header.dh_public_key
    assert header2.prev_chain_length == header.prev_chain_length
    assert header2.message_number == header.message_number


def test_ratchet_initialization():
    """Test ratchet initialization."""
    ratchet = RatchetEngine()
    
    assert ratchet.state is not None
    assert ratchet.state.sending_message_number == 0
    assert ratchet.state.receiving_message_number == 0


def test_ratchet_sender_initialization():
    """Test ratchet initialization as sender."""
    ratchet = RatchetEngine()
    
    # Generate test keys
    shared_secret = b"0" * 32
    remote_key = PrivateKey.generate().public_key
    
    ratchet.initialize_sender(shared_secret, remote_key)
    
    assert ratchet.state.dh_self is not None
    assert ratchet.state.dh_remote == remote_key
    # Root key is modified during DH ratchet, so just check it exists
    assert ratchet.state.root_key is not None
    assert len(ratchet.state.root_key) == 32
    assert ratchet.state.sending_chain_key is not None


def test_ratchet_receiver_initialization():
    """Test ratchet initialization as receiver."""
    ratchet = RatchetEngine()
    
    # Generate test keys
    shared_secret = b"1" * 32
    dh_self = PrivateKey.generate()
    
    ratchet.initialize_receiver(shared_secret, dh_self)
    
    assert ratchet.state.dh_self == dh_self
    assert ratchet.state.root_key == shared_secret


def test_encrypt_decrypt_simple():
    """Test simple encrypt/decrypt cycle."""
    # Setup Alice as sender
    alice = RatchetEngine()
    shared_secret = b"shared_secret_32bytes_long!!"[:32]
    bob_identity = PrivateKey.generate()
    alice.initialize_sender(shared_secret, bob_identity.public_key)
    
    # Setup Bob as receiver
    bob = RatchetEngine()
    bob.initialize_receiver(shared_secret, bob_identity)
    
    # Alice encrypts message
    plaintext = "Hello Bob!"
    ciphertext, header = alice.encrypt(plaintext)
    
    assert ciphertext != plaintext
    assert header.message_number == 0
    
    # Bob decrypts (this will trigger DH ratchet automatically)
    decrypted = bob.decrypt(ciphertext, header)
    assert decrypted == plaintext


def test_multiple_messages():
    """Test multiple message encryption/decryption."""
    # Setup
    alice = RatchetEngine()
    shared_secret = b"x" * 32
    bob_key = PrivateKey.generate()
    alice.initialize_sender(shared_secret, bob_key.public_key)
    
    bob = RatchetEngine()
    bob.initialize_receiver(shared_secret, bob_key)
    
    # Send multiple messages
    messages = ["Message 1", "Message 2", "Message 3"]
    
    for i, msg in enumerate(messages):
        ciphertext, header = alice.encrypt(msg)
        assert header.message_number == i
        
        decrypted = bob.decrypt(ciphertext, header)
        assert decrypted == msg


def test_out_of_order_messages():
    """Test handling out-of-order messages with skipped keys."""
    # Setup
    alice = RatchetEngine()
    shared_secret = b"y" * 32
    bob_key = PrivateKey.generate()
    alice.initialize_sender(shared_secret, bob_key.public_key)
    
    bob = RatchetEngine()
    bob.initialize_receiver(shared_secret, bob_key)
    
    # Alice sends 3 messages
    msg1_cipher, msg1_header = alice.encrypt("Message 1")
    msg2_cipher, msg2_header = alice.encrypt("Message 2")
    msg3_cipher, msg3_header = alice.encrypt("Message 3")
    
    # Bob receives them out of order: 1, 3, 2
    plaintext1 = bob.decrypt(msg1_cipher, msg1_header)
    assert plaintext1 == "Message 1"
    
    # Decrypt message 3 (skips message 2)
    plaintext3 = bob.decrypt(msg3_cipher, msg3_header)
    assert plaintext3 == "Message 3"
    
    # Skipped key for message 2 should be stored
    assert len(bob.state.skipped_keys) == 1
    
    # Now decrypt message 2 using skipped key
    plaintext2 = bob.try_skipped_message_keys(msg2_cipher, msg2_header)
    assert plaintext2 == "Message 2"
    
    # Skipped key should be consumed
    assert len(bob.state.skipped_keys) == 0


def test_ratchet_state_serialization():
    """Test ratchet state serialization/deserialization."""
    # Create ratchet with some state
    ratchet = RatchetEngine()
    shared_secret = b"z" * 32
    bob_key = PrivateKey.generate()
    ratchet.initialize_sender(shared_secret, bob_key.public_key)
    
    # Encrypt a message to advance state
    ratchet.encrypt("Test message")
    
    # Serialize
    state_dict = ratchet.serialize_state()
    
    assert "dh_self" in state_dict
    assert "root_key" in state_dict
    assert "sending_chain_key" in state_dict
    assert state_dict["sending_message_number"] == 1
    
    # Deserialize
    ratchet2 = RatchetEngine.deserialize_state(state_dict)
    
    assert ratchet2.state.sending_message_number == 1
    assert bytes(ratchet2.state.dh_self) == bytes(ratchet.state.dh_self)
    assert ratchet2.state.root_key == ratchet.state.root_key


def test_chain_key_derivation():
    """Test chain key advancement."""
    chain_key = b"initial_chain_key_32bytes!!"[:32]
    
    # Advance chain key
    next_key = RatchetEngine._advance_chain_key(chain_key)
    
    assert next_key != chain_key
    assert len(next_key) == 32
    
    # Derive message key
    msg_key = RatchetEngine._derive_message_key(chain_key)
    
    assert msg_key != chain_key
    assert len(msg_key) == 32


def test_max_skipped_keys():
    """Test DoS protection - max skipped keys limit."""
    alice = RatchetEngine()
    shared_secret = b"a" * 32
    bob_key = PrivateKey.generate()
    alice.initialize_sender(shared_secret, bob_key.public_key)
    
    bob = RatchetEngine()
    bob.initialize_receiver(shared_secret, bob_key)
    bob.state.max_skip = 10  # Low limit for testing
    
    # Alice sends many messages
    for i in range(15):
        alice.encrypt(f"Message {i}")
    
    # Bob tries to decrypt last message (would need to skip >10)
    _, last_header = alice.encrypt("Last message")
    
    # Should raise error due to too many skipped keys
    with pytest.raises(WhatsAppClientError, match="Too many skipped"):
        bob.decrypt("dummy", last_header)


@pytest.mark.asyncio
async def test_session_manager_encrypt_decrypt(temp_storage):
    """Test SessionManager encrypt/decrypt integration with two parties."""
    from whatsapp_client.crypto import SessionManager, RatchetEngine
    
    # Simulate Alice and Bob both having the same shared secret from X3DH
    shared_secret = bytes.fromhex("f" * 64)
    
    # In X3DH, Bob publishes his DH key, Alice uses Bob's public key
    bob_ephemeral = PrivateKey.generate()
    bob_public = bob_ephemeral.public_key
    
    # Create Alice's session manager (she's the initiator)
    alice_manager = SessionManager("alice", f"{temp_storage}/alice")
    alice_session = Session(
        session_id="test_session",
        peer_id="bob",
        shared_secret=shared_secret.hex(),
        ephemeral_key=PrivateKey.generate().encode(encoder=RawEncoder).hex(),  # Alice's own ephemeral
        initial_message_key=("e" * 64),
        created_at="2025-01-01T00:00:00",
    )
    
    # Manually initialize Alice's ratchet as sender with Bob's public key
    alice_ratchet = RatchetEngine()
    alice_ratchet.initialize_sender(shared_secret, bob_public)
    alice_session.ratchet_state = alice_ratchet.serialize_state()
    
    alice_manager._save_session(alice_session)
    alice_manager._sessions["bob"] = alice_session
    
    # Create Bob's session manager (he's the receiver)
    bob_manager = SessionManager("bob", f"{temp_storage}/bob")
    bob_session = Session(
        session_id="test_session",
        peer_id="alice",
        shared_secret=shared_secret.hex(),
        ephemeral_key=bob_ephemeral.encode(encoder=RawEncoder).hex(),  # Bob's ephemeral (matches published key)
        initial_message_key=("e" * 64),
        created_at="2025-01-01T00:00:00",
    )
    
    # Manually initialize Bob's ratchet as receiver with his private key
    bob_ratchet = RatchetEngine()
    bob_ratchet.initialize_receiver(shared_secret, bob_ephemeral)
    bob_session.ratchet_state = bob_ratchet.serialize_state()
    
    bob_manager._save_session(bob_session)
    bob_manager._sessions["alice"] = bob_session
    
    # Alice encrypts a message to Bob
    plaintext = "Hello from Alice!"
    encrypted = alice_manager.encrypt_message("bob", plaintext)
    
    assert encrypted.startswith("E2EE:")
    assert plaintext not in encrypted
    
    # Bob decrypts the message from Alice
    decrypted = bob_manager.decrypt_message("alice", encrypted)
    assert decrypted == plaintext


@pytest.mark.asyncio
async def test_client_send_message_integration(temp_storage):
    """Test WhatsAppClient.send_message with encryption."""
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
        "signedPrekey": "d" * 64,
        "signature": "e" * 128,
        "oneTimePrekeys": ["f" * 64]
    }
    
    mock_message_response = {
        "id": "msg_123",
        "from": "alice_user_id",
        "to": "bob_user_id",
        "content": "E2EE:{encrypted_data}",
        "timestamp": 1234567890,
        "status": "sent",
        "type": "text",
    }
    
    with patch.object(client._rest, "post", new=AsyncMock(side_effect=[mock_user, mock_upload_response, mock_message_response])):
        with patch.object(client._rest, "get", new=AsyncMock(return_value=mock_prekey_bundle)):
            with patch.object(client._rest, "delete", new=AsyncMock(return_value={"status": "ok"})):
                with patch("whatsapp_client.crypto.x3dh.X3DHProtocol.verify_prekey_signature", return_value=True):
                    await client.login("alice", "password123")
                    
                    # Send encrypted message
                    message = await client.send_message("bob_user_id", "Hello Bob!")
                    
                    assert message.id == "msg_123"
                    assert message.content == "Hello Bob!"  # Client returns plaintext
                    assert message.status == "sent"


@pytest.mark.asyncio
async def test_client_decrypt_message(temp_storage):
    """Test WhatsAppClient.decrypt_message with two separate ratchets."""
    alice_client = WhatsAppClient(server_url="http://localhost:8787", storage_path=f"{temp_storage}/alice")
    bob_client = WhatsAppClient(server_url="http://localhost:8787", storage_path=f"{temp_storage}/bob")
    
    # Mock login for Alice
    mock_user_alice = {
        "id": "alice_user_id",
        "username": "alice",
        "avatar": None,
        "lastSeen": 1234567890,
        "role": "user",
        "is_active": 1,
        "can_send_images": 1,
        "created_at": 1234567890,
    }
    
    # Mock login for Bob
    mock_user_bob = {
        "id": "bob_user_id",
        "username": "bob",
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
    
    with patch.object(alice_client._rest, "post", new=AsyncMock(side_effect=[mock_user_alice, mock_upload_response])):
        await alice_client.login("alice", "password123")
    
    with patch.object(bob_client._rest, "post", new=AsyncMock(side_effect=[mock_user_bob, mock_upload_response])):
        await bob_client.login("bob", "password123")
    
    # Setup symmetric sessions - Bob publishes his DH key, Alice uses it
    shared_secret = ("a" * 64)
    bob_ephemeral = PrivateKey.generate()
    bob_public = bob_ephemeral.public_key
    
    # Alice's session with Bob (she's the initiator)
    alice_session = Session(
        session_id="test",
        peer_id="bob_user_id",
        shared_secret=shared_secret,
        ephemeral_key=PrivateKey.generate().encode(encoder=RawEncoder).hex(),  # Alice's own ephemeral
        initial_message_key=("b" * 64),
        created_at="2025-01-01",
    )
    
    # Initialize Alice's ratchet as sender
    from whatsapp_client.crypto import RatchetEngine
    alice_ratchet = RatchetEngine()
    alice_ratchet.initialize_sender(bytes.fromhex(shared_secret), bob_public)
    alice_session.ratchet_state = alice_ratchet.serialize_state()
    
    alice_client._session_manager._sessions["bob_user_id"] = alice_session
    
    # Bob's session with Alice (he's the receiver)
    bob_session = Session(
        session_id="test",
        peer_id="alice_user_id",
        shared_secret=shared_secret,
        ephemeral_key=bob_ephemeral.encode(encoder=RawEncoder).hex(),  # Bob's ephemeral (matches published key)
        initial_message_key=("b" * 64),
        created_at="2025-01-01",
    )
    
    # Initialize Bob's ratchet as receiver
    bob_ratchet = RatchetEngine()
    bob_ratchet.initialize_receiver(bytes.fromhex(shared_secret), bob_ephemeral)
    bob_session.ratchet_state = bob_ratchet.serialize_state()
    
    bob_client._session_manager._sessions["alice_user_id"] = bob_session
    
    # Alice encrypts a message
    plaintext = "Hello from Alice!"
    encrypted = alice_client._session_manager.encrypt_message("bob_user_id", plaintext)
    
    # Bob decrypts it
    decrypted = bob_client.decrypt_message("alice_user_id", encrypted)
    assert decrypted == plaintext


def test_encryption_not_initialized():
    """Test encryption fails if ratchet not initialized."""
    ratchet = RatchetEngine()
    
    with pytest.raises(WhatsAppClientError, match="not initialized"):
        ratchet.encrypt("Test")


def test_dh_ratchet_step():
    """Test DH ratchet step performs key derivation."""
    alice = RatchetEngine()
    shared_secret = b"s" * 32
    bob_key = PrivateKey.generate()
    alice.initialize_sender(shared_secret, bob_key.public_key)
    
    # Store initial state
    initial_sending_chain = alice.state.sending_chain_key
    initial_root_key = alice.state.root_key
    
    # Perform another DH ratchet (simulate receiving new DH key)
    new_bob_key = PrivateKey.generate()
    alice._dh_ratchet_receive(new_bob_key.public_key)
    
    # State should have changed
    assert alice.state.root_key != initial_root_key
    assert alice.state.dh_remote == new_bob_key.public_key
