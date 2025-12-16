"""
Basic usage example for WhatsApp Client.

This example demonstrates how to:
- Initialize the client
- Register a new user
- Login with credentials
- Logout

Run with: python examples/basic_usage.py
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
        # Register new user
        print("Registering new user...")
        user = await client.register(
            username="example_bot", password="secure_password_123"
        )
        print(f"✓ Registered: {user.username} (ID: {user.id})")

        # Logout
        await client.logout()
        print("✓ Logged out")

        # Login again
        print("\nLogging in...")
        user = await client.login(username="example_bot", password="secure_password_123")
        print(f"✓ Logged in as: {user.username}")
        print(f"  User ID: {user.id}")
        print(f"  Role: {user.role}")
        print(f"  Is Active: {user.is_active}")

    except Exception as e:
        print(f"✗ Error: {e}")

    finally:
        # Cleanup
        await client.logout()
        await client.close()
        print("\n✓ Client closed")


if __name__ == "__main__":
    asyncio.run(main())
