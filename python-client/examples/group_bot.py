"""
Group Chat Bot Example - Manages and broadcasts to groups.

This example demonstrates:
- Group creation and member management
- Broadcasting messages to groups
- Group event handling
- Multiple concurrent operations

Usage:
    python group_bot.py --server http://localhost:8000 --user groupbot --password secret
"""

import asyncio
import argparse
import logging
from whatsapp_client import AsyncClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GroupBot:
    """Group management bot."""
    
    def __init__(self, client: AsyncClient):
        """Initialize bot."""
        self.client = client
        self.managed_groups = {}
    
    async def create_group(self, name: str, description: str = "") -> str:
        """Create a new managed group."""
        try:
            group_id = await self.client.create_group(
                name=name,
                description=description,
            )
            self.managed_groups[group_id] = {
                "name": name,
                "description": description,
                "created_at": asyncio.get_event_loop().time(),
            }
            logger.info(f"Created group: {name} ({group_id})")
            return group_id
        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            raise
    
    async def add_member_to_group(self, group_id: str, user_id: str) -> bool:
        """Add member to group."""
        try:
            result = await self.client.add_group_member(group_id, user_id)
            logger.info(f"Added {user_id} to group {group_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            return False
    
    async def broadcast_to_group(self, group_id: str, message: str) -> bool:
        """Broadcast message to group."""
        try:
            await self.client.send_group_message(group_id, message)
            logger.info(f"Broadcast to {group_id}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to broadcast: {e}")
            return False
    
    async def handle_group_message(self, message):
        """Handle group messages."""
        logger.info(
            f"[Group {message['group_id']}] "
            f"{message['from_user']}: {message['content']}"
        )
        
        # Auto-respond to group messages
        if message["content"].startswith("!"):
            response = f"Got your command: {message['content']}"
            await self.client.send_group_message(
                message["group_id"],
                response,
            )


async def main():
    """Run group bot."""
    parser = argparse.ArgumentParser(description="Group bot for WhatsApp Clone")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--user", default="groupbot")
    parser.add_argument("--password", default="bot_password")
    
    args = parser.parse_args()
    
    async with AsyncClient(
        server_url=args.server,
        storage_path="/tmp/whatsapp_groupbot",
    ) as client:
        # Login
        try:
            await client.register(args.user, args.password)
            logger.info(f"Registered {args.user}")
        except:
            await client.login(args.user, args.password)
            logger.info(f"Logged in {args.user}")
        
        # Create bot
        bot = GroupBot(client)
        
        # Register handler
        @client.on_group_message
        async def handle_group_msg(msg):
            await bot.handle_group_message(msg)
        
        # Create example group
        try:
            group_id = await bot.create_group(
                name="Test Group",
                description="Example group managed by bot",
            )
            await bot.broadcast_to_group(
                group_id,
                "Welcome to the test group! 👋",
            )
        except Exception as e:
            logger.error(f"Failed to create example group: {e}")
        
        logger.info("Group bot started")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
