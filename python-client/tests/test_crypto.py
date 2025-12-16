"""Tests for cryptographic key management."""

import pytest
from unittest.mock import AsyncMock, patch

from whatsapp_client.crypto import KeyManager, format_fingerprint
from whatsapp_client.exceptions import ValidationError


@pytest.fixture
async def key_manager():
    """Create a test key manager."""
    manager = KeyManager(user_id="test_user_123", storage_path="/tmp/test_keys")
    await manager.initialize()
    return manager


@pytest.mark.asyncio
async def test_key_generation(key_manager):
    """Test identity and signing key generation."""
    # Check identity key exists
    identity_keypair = key_manager.get_identity_keypair()
    assert identity_keypair.public_key is not None
    assert identity_keypair.private_key is not None
    assert len(identity_keypair.public_key) == 32  # Curve25519 public key
    assert len(identity_keypair.private_key) == 32  # Curve25519 private key

    # Check signing key exists
    signing_keypair = key_manager.get_signing_keypair()
    assert signing_keypair.public_key is not None
    assert signing_keypair.private_key is not None
    assert len(signing_keypair.public_key) == 32  # Ed25519 public key
    assert len(signing_keypair.private_key) == 32  # Ed25519 private key (seed)


@pytest.mark.asyncio
async def test_prekey_generation(key_manager):
    """Test prekey bundle generation."""
    # Check signed prekey exists
    bundle = key_manager.get_public_bundle()
    assert bundle.signed_prekey is not None
    assert "keyId" in bundle.signed_prekey
    assert "publicKey" in bundle.signed_prekey
    assert "signature" in bundle.signed_prekey

    # Check one-time prekeys exist (default 100)
    assert len(bundle.one_time_prekeys) == 100

    for prekey in bundle.one_time_prekeys:
        assert "keyId" in prekey
        assert "publicKey" in prekey


@pytest.mark.asyncio
async def test_fingerprint_generation(key_manager):
    """Test fingerprint generation."""
    fingerprint = key_manager.get_fingerprint()

    # Should be 60 characters (30 bytes hex encoded)
    assert len(fingerprint) == 60
    # Should be valid hex
    assert all(c in "0123456789abcdef" for c in fingerprint)

    # Should be consistent
    fingerprint2 = key_manager.get_fingerprint()
    assert fingerprint == fingerprint2


@pytest.mark.asyncio
async def test_public_bundle(key_manager):
    """Test public key bundle creation."""
    bundle = key_manager.get_public_bundle()

    # Check all required fields
    assert bundle.identity_key is not None
    assert bundle.signing_key is not None
    assert bundle.fingerprint is not None
    assert bundle.signed_prekey is not None
    assert len(bundle.one_time_prekeys) > 0

    # Bundle should not contain private keys
    assert "privateKey" not in bundle.signed_prekey
    for prekey in bundle.one_time_prekeys:
        assert "privateKey" not in prekey


@pytest.mark.asyncio
async def test_prekey_count(key_manager):
    """Test prekey availability tracking."""
    initial_count = key_manager.get_available_prekey_count()
    assert initial_count == 100

    # Consume a prekey
    key_manager.consume_prekey(1)
    assert key_manager.get_available_prekey_count() == 99

    # Consume another
    key_manager.consume_prekey(2)
    assert key_manager.get_available_prekey_count() == 98


@pytest.mark.asyncio
async def test_prekey_rotation(key_manager):
    """Test prekey rotation."""
    # Consume most prekeys
    for i in range(1, 91):  # Leave 10
        key_manager.consume_prekey(i)

    assert key_manager.get_available_prekey_count() == 10

    # Rotate prekeys
    await key_manager.rotate_prekeys(count=100)

    # Should have 100 new prekeys
    assert key_manager.get_available_prekey_count() == 100


@pytest.mark.asyncio
async def test_keys_not_initialized():
    """Test error when accessing keys before initialization."""
    manager = KeyManager(user_id="test_user", storage_path="/tmp/test")

    # Should raise error before initialization
    with pytest.raises(ValidationError):
        manager.get_fingerprint()

    with pytest.raises(ValidationError):
        manager.get_public_bundle()


def test_fingerprint_format():
    """Test fingerprint formatting."""
    # Test with known data
    test_key = b"0" * 32  # 32 zero bytes

    fingerprint = format_fingerprint(test_key)

    # Should be 60 characters
    assert len(fingerprint) == 60
    # Should be valid hex
    assert all(c in "0123456789abcdef" for c in fingerprint)
