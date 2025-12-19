"""
Test script to verify session establishment with X3DH data works correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from whatsapp_client import AsyncClient


async def main():
    """Test session establishment and first message with X3DH data."""
    print("=== Testing Session Establishment with X3DH Data ===\n")

    # Use a unique storage path for testing
    test_storage = Path.home() / ".whatsapp_clone" / "test_sender"
    print(f"Storage path: {test_storage}\n")

    async with AsyncClient(
        server_url="http://localhost:8000",
        storage_path=str(test_storage),
    ) as client:
        # Login or register as test sender
        try:
            print("Attempting to register as 'test_sender'...")
            user = await client.register("test_sender", "test_password")
            print(f"✓ Registered: {user.username}\n")
        except Exception as e:
            print(f"Registration failed (may already exist), trying login: {e}")
            user = await client.login("test_sender", "test_password")
            print(f"✓ Logged in: {user.username}\n")

        # Check if echobot exists
        try:
            # Try to establish a session by sending a message to echobot
            target_user = "echobot"  # Assuming echobot user ID

            print(f"Sending encrypted message to '{target_user}'...")
            message = await client.send_message(
                target_user,
                "Hello from test_sender! This should include X3DH data."
            )
            print(f"✓ Message sent: {message.id}")
            print(f"  Content: {message.content}\n")

            # Check if session was established
            session_manager = client._session_manager
            session = session_manager.get_session(target_user)

            if session:
                print("✓ Session established successfully!")
                print(f"  Session ID: {session.session_id}")
                print(f"  Has X3DH data: {session.x3dh_data is not None}")
                print(f"  Has ratchet state: {session.ratchet_state is not None}")

                if session.x3dh_data:
                    print("  ⚠ Warning: X3DH data should be None after first message!")
                else:
                    print("  ✓ X3DH data correctly cleared after first message")

                # Check if session was saved to disk
                session_file = session_manager._get_session_file(target_user)
                if session_file.exists():
                    print(f"  ✓ Session saved to: {session_file}\n")
                else:
                    print(f"  ✗ Session NOT saved to disk!\n")
            else:
                print("✗ No session found!\n")

            # Send a second message to verify X3DH data is not included
            print(f"Sending second message to '{target_user}'...")
            message2 = await client.send_message(
                target_user,
                "Second message - should NOT include X3DH data."
            )
            print(f"✓ Second message sent: {message2.id}\n")

            # Verify session X3DH data is still None
            session = session_manager.get_session(target_user)
            if session and session.x3dh_data is None:
                print("✓ Second message correctly sent without X3DH data")
            else:
                print("✗ Unexpected X3DH data in session after second message")

            print("\n=== Test Complete ===")

        except Exception as e:
            print(f"\n✗ Error during test: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
