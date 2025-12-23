#!/usr/bin/env python3
"""
Demo script showing programmatic usage of the WhatsApp CLI client.
This demonstrates how to use the WhatsAppClient for automated messaging.
"""

import asyncio
import sys
import os

# Add the python-client src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python-client', 'src'))

from whatsapp_client import WhatsAppClient
from whatsapp_client.exceptions import WhatsAppClientError


async def demo_registration():
    """Demo user registration."""
    print("Demo: User Registration")

    client = WhatsAppClient(server_url='https://whatsapp-clone-worker.hi-suneesh.workers.dev')

    try:
        # Register a new user
        user = await client.register("demo_user", "demo_password")
        print(f"Registered user: {user.username} (ID: {user.id})")

        # Clean up
        await client.close()

    except WhatsAppClientError as e:
        print(f"Registration failed: {e}")


async def demo_messaging():
    """Demo sending and receiving messages."""
    print("Demo: E2E Encrypted Messaging")

    # Create two clients
    alice_client = WhatsAppClient(server_url='https://whatsapp-clone-worker.hi-suneesh.workers.dev')
    bob_client = WhatsAppClient(server_url='https://whatsapp-clone-worker.hi-suneesh.workers.dev')

    # Track received messages
    alice_messages = []
    bob_messages = []

    # Set up message handlers
    @alice_client.on_message
    async def alice_handler(msg):
        print(f"Alice received: {msg.content}")
        alice_messages.append(msg)

    @bob_client.on_message
    async def bob_handler(msg):
        print(f"Bob received: {msg.content}")
        bob_messages.append(msg)

    try:
        # Register users
        print("Registering Alice...")
        alice = await alice_client.register("alice_demo", "password123")

        print("Registering Bob...")
        bob = await bob_client.register("bob_demo", "password456")

        print(f"Alice ID: {alice.id}")
        print(f"Bob ID: {bob.id}")

        # Alice sends message to Bob
        print("Alice sending message to Bob...")
        msg1 = await alice_client.send_message(bob.id, "Hello Bob! This is an E2E encrypted message.")
        print(f"Message sent: {msg1.id}")

        # Wait for message delivery
        await asyncio.sleep(3)

        # Bob sends reply to Alice
        print("Bob sending reply to Alice...")
        msg2 = await bob_client.send_message(alice.id, "Hi Alice! Message received and decrypted successfully!")
        print(f"Reply sent: {msg2.id}")

        # Wait for reply delivery
        await asyncio.sleep(3)

        # Show results
        print("Results:")
        print(f"Alice received {len(alice_messages)} messages")
        print(f"Bob received {len(bob_messages)} messages")

        # Show encryption info
        print("Encryption Info:")
        alice_fingerprint = alice_client.get_fingerprint()
        bob_fingerprint = bob_client.get_fingerprint()
        print(f"Alice's fingerprint: {alice_fingerprint}")
        print(f"Bob's fingerprint: {bob_fingerprint}")

        # Show sessions
        alice_sessions = alice_client.list_sessions()
        bob_sessions = bob_client.list_sessions()
        print(f"Alice has {len(alice_sessions)} active sessions")
        print(f"Bob has {len(bob_sessions)} active sessions")

    except WhatsAppClientError as e:
        print(f"Demo failed: {e}")
    finally:
        # Clean up
        await alice_client.close()
        await bob_client.close()


async def main():
    """Run the demo."""
    print("WhatsApp Clone Python Client Demo")
    print("=" * 50)

    await demo_registration()
    await demo_messaging()

    print("Demo completed!")
    print("Try the interactive CLI: python whatsapp_cli.py")


if __name__ == "__main__":
    asyncio.run(main())