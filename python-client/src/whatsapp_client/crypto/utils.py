"""Cryptography utilities."""

import hashlib
from typing import Tuple


def format_fingerprint(public_key: bytes) -> str:
    """
    Generate human-readable fingerprint from public key.
    
    Args:
        public_key: 32-byte public key
        
    Returns:
        60-character hexadecimal fingerprint (SHA-256)
    """
    digest = hashlib.sha256(public_key).digest()
    # Take first 30 bytes for 60-char hex string
    return digest[:30].hex()


def encode_base64(data: bytes) -> str:
    """
    Encode bytes to base64 string.
    
    Args:
        data: Raw bytes
        
    Returns:
        Base64 encoded string
    """
    import base64
    return base64.b64encode(data).decode('ascii')


def decode_base64(data: str) -> bytes:
    """
    Decode base64 string to bytes.
    
    Args:
        data: Base64 encoded string
        
    Returns:
        Raw bytes
    """
    import base64
    return base64.b64decode(data)


def generate_salt() -> bytes:
    """
    Generate random salt for key derivation.
    
    Returns:
        32 bytes of random data
    """
    import os
    return os.urandom(32)
