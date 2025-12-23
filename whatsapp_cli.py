#!/usr/bin/env python3
"""
WhatsApp Clone CLI Client

A command-line interface for the WhatsApp Clone E2E encrypted messaging platform.
Supports user registration, login, sending messages, and receiving real-time messages.
"""

import asyncio
import sys
import os
import logging
from typing import Optional
import getpass

# Add the python-client src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python-client', 'src'))

from whatsapp_client import WhatsAppClient
from whatsapp_client.exceptions import WhatsAppClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WhatsAppCLI:
    """Command-line interface for WhatsApp Clone."""

    def __init__(self):
        self.client: Optional[WhatsAppClient] = None
        self.username: Optional[str] = None
        self.user_id: Optional[str] = None
        self.running = False
        self.chat_with: Optional[str] = None
        self.chat_username: Optional[str] = None

    async def setup_client(self, server_url: str = 'https://whatsapp-clone-worker.hi-suneesh.workers.dev'):
        """Initialize the WhatsApp client."""
        self.client = WhatsAppClient(server_url=server_url)

        # Set up message handler
        @self.client.on_message
        async def handle_message(msg):
            if self.chat_with and msg.from_user == self.chat_with:
                content = msg.content
                if content.startswith('E2EE:'):
                    content = "[E2E Encrypted] " + content[:100] + "..."
                print(f"\n📨 {content}")
                print(f"💬 [{self.chat_username}] ", end='', flush=True)
            else:
                print(f"\n📨 [{msg.from_user}] {msg.content}")
                if not self.chat_with:
                    print("💬 ", end='', flush=True)

    async def register_user(self, username: str, password: str):
        """Register a new user."""
        try:
            print(f"🔐 Registering user: {username}")
            user = await self.client.register(username, password)
            self.username = username
            self.user_id = user.id
            print(f"✅ Registration successful! User ID: {user.id}")
            return True
        except WhatsAppClientError as e:
            print(f"❌ Registration failed: {e}")
            return False

    async def login_user(self, username: str, password: str):
        """Login existing user."""
        try:
            print(f"🔑 Logging in as: {username}")
            user = await self.client.login(username, password)
            self.username = username
            self.user_id = user.id
            print(f"✅ Login successful! User ID: {user.id}")
            return True
        except WhatsAppClientError as e:
            print(f"❌ Login failed: {e}")
            return False

    async def send_message(self, to_user: str, content: str):
        """Send a message to another user."""
        try:
            message = await self.client.send_message(to_user, content)
            if self.chat_with == to_user:
                print(f"\n📤 You: {content}")
                print(f"💬 [{self.chat_username}] ", end='', flush=True)
            else:
                print(f"📤 Message sent to {to_user}: {message.id}")
        except WhatsAppClientError as e:
            error_msg = str(e)
            if "Key material not found" in error_msg or "prekey bundle" in error_msg:
                print(f"❌ Cannot reach user: {to_user}")
                print("   Make sure the user ID is correct and the user has registered.")
                print(f"   Your ID: {self.user_id}")
            else:
                print(f"❌ Failed to send message: {e}")

    async def list_sessions(self):
        """List active sessions."""
        try:
            sessions = self.client.list_sessions()
            if sessions:
                print("🔗 Active sessions:")
                for session in sessions:
                    print(f"  - {session}")
            else:
                print("📭 No active sessions")
        except WhatsAppClientError as e:
            print(f"❌ Failed to list sessions: {e}")

    async def get_fingerprint(self):
        """Get own encryption fingerprint."""
        try:
            fingerprint = self.client.get_fingerprint()
            print(f"🔐 Your fingerprint: {fingerprint}")
        except WhatsAppClientError as e:
            print(f"❌ Failed to get fingerprint: {e}")

    async def run_interactive(self):
        """Run the interactive CLI loop."""
        print("🚀 WhatsApp Clone CLI Client")
        print("\nQuick start:")
        print("  Type 'register <username> <password>' to create account")
        print("  Type 'login <username> <password>' to login")
        print("  Type 'chat <user_id>' to start a chat")
        print("  Type 'help' for more commands\n")

        self.running = True
        while self.running:
            try:
                if self.chat_with:
                    print(f"💬 [{self.chat_username}] ", end='', flush=True)
                elif self.client and self.client.is_authenticated:
                    print(f"📱 [{self.username}] ", end='', flush=True)
                else:
                    print("❓ ", end='', flush=True)

                line = await asyncio.get_event_loop().run_in_executor(None, input)
                await self.process_command(line.strip())

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.exception("CLI error")

    async def process_command(self, command: str):
        """Process a user command."""
        if not command:
            return

        # If in chat mode and not a special command, send message
        if self.chat_with and not command.startswith('/') and command.lower() not in ['quit', 'exit', 'help', 'back']:
            await self.send_message(self.chat_with, command)
            return

        parts = command.split()
        cmd = parts[0].lower()

        if cmd == 'quit' or cmd == 'exit':
            if self.chat_with:
                print(f"👋 Left chat with {self.chat_username}")
                self.chat_with = None
                self.chat_username = None
            else:
                print("👋 Goodbye!")
                self.running = False

        elif cmd == 'back':
            if self.chat_with:
                print(f"👋 Left chat with {self.chat_username}")
                self.chat_with = None
                self.chat_username = None
            else:
                print("❌ Not in a chat")

        elif cmd == 'help':
            self.show_help()

        elif cmd == 'register':
            if len(parts) < 3:
                print("❌ Usage: register <username> <password>")
            else:
                username, password = parts[1], ' '.join(parts[2:])
                await self.register_user(username, password)

        elif cmd == 'login':
            if len(parts) < 3:
                print("❌ Usage: login <username> <password>")
            else:
                username, password = parts[1], ' '.join(parts[2:])
                await self.login_user(username, password)

        elif cmd == 'chat':
            if not self.client or not self.client.is_authenticated:
                print("❌ Please login first")
            elif len(parts) < 2:
                print("❌ Usage: chat <username_or_user_id>")
                print(f"   Your user ID: {self.user_id}")
            else:
                target = parts[1]
                display_name = ' '.join(parts[2:]) if len(parts) > 2 else None
                
                # Check if it looks like a UUID or username
                if '-' in target and len(target) == 36:
                    # Looks like a UUID
                    user_id = target
                    username = display_name or target
                else:
                    # Try to find user by username
                    print(f"🔍 Looking up user: {target}")
                    user = await self.client.find_user(target)
                    if user:
                        user_id = user['id']
                        username = display_name or user['username']
                        print(f"✅ Found: {username} ({user_id})")
                    else:
                        print(f"❌ User not found: {target}")
                        print("   Try 'users' to see available users")
                        return
                
                self.chat_with = user_id
                self.chat_username = username
                print(f"\n💬 Chat with {username}")
                print("Type messages to send. Type 'back' or 'quit' to exit.\n")

        elif cmd == 'users':
            if not self.client or not self.client.is_authenticated:
                print("❌ Please login first")
            else:
                print("🔍 Fetching user list...")
                users = await self.client.list_users()
                if users:
                    print(f"\n👥 Registered Users ({len(users)}):")
                    for u in users:
                        if u['id'] != self.user_id:
                            print(f"   {u['username']} - {u['id']}")
                    print(f"\n   Use: chat <username> to start chatting")
                else:
                    print("❌ No users found or failed to fetch")

        elif cmd == 'myid':
            if not self.client or not self.client.is_authenticated:
                print("❌ Please login first")
            else:
                print(f"📱 Your username: {self.username}")
                print(f"🆔 Your user ID: {self.user_id}")
                print("   Share this ID with others to chat with them")

        elif cmd == 'send':
            if not self.client or not self.client.is_authenticated:
                print("❌ Please login first")
            elif len(parts) < 3:
                print("❌ Usage: send <user_id> <message>")
            else:
                to_user = parts[1]
                content = ' '.join(parts[2:])
                await self.send_message(to_user, content)

        elif cmd == 'sessions':
            if not self.client or not self.client.is_authenticated:
                print("❌ Please login first")
            else:
                await self.list_sessions()

        elif cmd == 'fingerprint':
            if not self.client or not self.client.is_authenticated:
                print("❌ Please login first")
            else:
                await self.get_fingerprint()

        else:
            if not self.chat_with:
                print(f"❓ Unknown command: {cmd}. Type 'help' for available commands.")

    def show_help(self):
        """Show help information."""
        print("""
📚 WhatsApp Clone CLI Commands:

Authentication:
  register <username> <password>  - Register a new account
  login <username> <password>     - Login to existing account
  myid                            - Show your user ID and username

Users:
  users                           - List all registered users
  chat <username>                 - Start chat with user by username
  chat <user_id>                  - Start chat with user by ID

Chat Mode:
  Just type your message and press Enter to send
  Type 'back' or 'quit' to exit chat and return to menu

Messaging:
  send <user_id> <message>        - Send a single message to user

Information:
  sessions                        - List active encrypted sessions
  fingerprint                     - Show your encryption fingerprint

Other:
  help                            - Show this help
  quit                            - Exit the application

Getting Started:
  1. Register: register alice mypassword123
  2. List users: users
  3. Chat: chat bob
  4. Just type messages naturally!

Examples:
  register alice mypassword123
  users
  chat bob
  chat a1b2c3d4-e5f6-7890-abcd-ef1234567890
  sessions
  fingerprint
        """)

    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.close()


async def main():
    """Main entry point."""
    cli = WhatsAppCLI()

    try:
        # Setup client with default server
        await cli.setup_client()

        # Run interactive CLI
        await cli.run_interactive()

    except Exception as e:
        print(f"💥 Fatal error: {e}")
        logger.exception("Fatal error")
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("WhatsApp Clone CLI Client")
            print("Usage: python whatsapp_cli.py")
            print("Run interactively to register, login, and chat.")
            sys.exit(0)

    # Run the CLI
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)