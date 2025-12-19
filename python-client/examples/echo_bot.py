"""
Echo Bot Example - Echoes back every message received.

This is a simple example bot that demonstrates:
- Basic client initialization and login
- Message event handling with decorators
- Sending messages
- Using async/await with AsyncClient

Usage:
    python echo_bot.py --server http://localhost:8000 --user echobot --password secret
"""

import asyncio
import argparse
import logging
import os
from pathlib import Path
from whatsapp_client import AsyncClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_storage_path(bot_name: str) -> str:
    """Get cross-platform storage path for bot data."""
    # Use user's home directory for persistent storage
    home = Path.home()
    storage_dir = home / ".whatsapp_clone" / bot_name
    storage_dir.mkdir(parents=True, exist_ok=True)
    return str(storage_dir)


async def main():
    """Run the echo bot."""
    parser = argparse.ArgumentParser(description="Echo bot for WhatsApp Clone")
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--user",
        default="echobot",
        help="Bot username (default: echobot)",
    )
    parser.add_argument(
        "--password",
        default="bot_password",
        help="Bot password (default: bot_password)",
    )
    parser.add_argument(
        "--storage",
        default=None,
        help="Storage path (default: ~/.whatsapp_clone/<username>)",
    )
    
    args = parser.parse_args()
    
    # Use provided storage path or default to user's home directory
    storage_path = args.storage or get_storage_path(args.user)
    logger.info(f"Using storage path: {storage_path}")
    
    async with AsyncClient(
        server_url=args.server,
        storage_path=storage_path,
    ) as client:
        # Register or login
        try:
            logger.info(f"Registering as {args.user}...")
            user = await client.register(args.user, args.password)
            logger.info(f"Registered new user: {user.username}")
        except Exception as e:
            logger.info(f"Registration failed, trying login: {e}")
            user = await client.login(args.user, args.password)
            logger.info(f"Logged in as {user.username}")
        
        # Set up message handler
        message_count = 0
        
        @client.on_message
        async def handle_message(message):
            """Handle incoming messages."""
            nonlocal message_count
            message_count += 1
            
            logger.info(
                f"[{message_count}] Message from {message.from_user}: {message.content}"
            )
            
            # Check if message was decrypted successfully
            # (failed decryption leaves the raw encrypted content)
            if message.content.startswith('{') and '"ciphertext"' in message.content:
                logger.warning(
                    f"Could not decrypt message from {message.from_user}. "
                    "They may need to reset their encryption (the sender should go to Settings > Reset Encryption)."
                )
                return
            
            # Send echo response
            try:
                echo_response = f"Echo: {message.content}"
                response = await client.send_message(
                    message.from_user,
                    echo_response,
                )
                logger.info(f"Sent response: {response.id}")
            except Exception as e:
                logger.error(f"Failed to send response: {e}")
        
        # Keep running
        logger.info("Echo bot started. Waiting for messages...")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
