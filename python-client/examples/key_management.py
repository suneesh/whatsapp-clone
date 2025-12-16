"""
Example demonstrating key management and fingerprint usage.

This example shows how to:
- Access encryption key fingerprint
- Check prekey status
- Understand key rotation

Run with: python examples/key_management.py
"""

import asyncio
import os
from whatsapp_client import WhatsAppClient


async def main():
    # Get server URL from environment or use default
    server_url = os.getenv("WHATSAPP_SERVER_URL", "http://localhost:8787")

    # Initialize client
    client = WhatsAppClient(server_url=server_url)

    try:
        # Login (keys are automatically generated and uploaded)
        print("Logging in...")
        await client.login(username="key_demo_bot", password="secure_password_123")
        print(f"✓ Logged in as: {client.user.username}")

        # Get fingerprint
        fingerprint = client.get_fingerprint()
        print(f"\n📱 Your encryption key fingerprint:")
        print(f"   {fingerprint}")
        print(f"   (Share this with contacts for verification)")

        # Check prekey status
        status = await client.get_prekey_status()
        print(f"\n🔑 Prekey Status:")
        print(f"   Available prekeys: {status['available']}")
        print(f"   Needs rotation: {status['needs_rotation']}")

        # Explain what keys were generated
        print(f"\n🔐 Generated Keys:")
        print(f"   ✓ Identity key pair (Curve25519) - Long-term identity")
        print(f"   ✓ Signing key pair (Ed25519) - For signing prekeys")
        print(f"   ✓ 1 Signed prekey - For session establishment")
        print(f"   ✓ 100 One-time prekeys - For perfect forward secrecy")

        print(f"\n💡 All keys are automatically:")
        print(f"   • Generated using secure random numbers")
        print(f"   • Uploaded to server (public keys only)")
        print(f"   • Stored locally encrypted (future feature)")
        print(f"   • Rotated when running low (automatic)")

    except Exception as e:
        print(f"✗ Error: {e}")

    finally:
        # Cleanup
        await client.logout()
        await client.close()
        print("\n✓ Client closed")


if __name__ == "__main__":
    asyncio.run(main())
