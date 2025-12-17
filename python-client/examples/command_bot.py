"""
Command Bot Example - Responds to commands (!help, !ping, !users, !status).

This example demonstrates:
- Advanced message parsing and command handling
- Error handling and validation
- Querying client state (online users, connections)
- Async concurrent operations

Usage:
    python command_bot.py --server http://localhost:8000 --user cmdbot --password secret

Available commands:
    !help         - Show available commands
    !ping         - Check bot responsiveness
    !users        - List online users
    !status       - Show bot connection status
    !echo <text>  - Echo back text
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


class CommandBot:
    """Command-based bot for WhatsApp Clone."""
    
    def __init__(self, client: AsyncClient):
        """Initialize bot with client."""
        self.client = client
        self.commands = {
            "help": self.cmd_help,
            "ping": self.cmd_ping,
            "users": self.cmd_users,
            "status": self.cmd_status,
            "echo": self.cmd_echo,
        }
    
    async def handle_message(self, message):
        """Process incoming message."""
        content = message.content.strip()
        
        # Check if message is a command
        if not content.startswith("!"):
            logger.debug(f"Not a command: {content}")
            return
        
        # Parse command
        parts = content[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        logger.info(f"Command from {message.from_user}: {cmd} {args}")
        
        # Execute command
        if cmd in self.commands:
            try:
                response = await self.commands[cmd](args)
                await self.client.send_message(message.from_user, response)
            except Exception as e:
                logger.error(f"Command error: {e}")
                await self.client.send_message(
                    message.from_user,
                    f"Error: {str(e)}",
                )
        else:
            await self.client.send_message(
                message.from_user,
                f"Unknown command: {cmd}\nType !help for available commands",
            )
    
    async def cmd_help(self, args: str) -> str:
        """Show available commands."""
        return """Available commands:
!help         - Show this help message
!ping         - Check bot responsiveness
!users        - List online users
!status       - Show bot status
!echo <text>  - Echo back text"""
    
    async def cmd_ping(self, args: str) -> str:
        """Ping command."""
        return "Pong! Bot is responsive ✓"
    
    async def cmd_users(self, args: str) -> str:
        """List online users."""
        try:
            users = self.client.get_online_users()
            if not users:
                return "No users online"
            
            user_list = "\n".join(f"  • {user}" for user in users)
            return f"Online users:\n{user_list}"
        except Exception as e:
            return f"Error getting users: {e}"
    
    async def cmd_status(self, args: str) -> str:
        """Show bot status."""
        state = self.client.get_running_state()
        
        return f"""Bot Status:
Authenticated: {state['is_authenticated']}
Connected: {state['is_connected']}
Running: {state['is_running']}
Background Tasks: {state['task_count']}
Exceptions: {state['exception_count']}"""
    
    async def cmd_echo(self, args: str) -> str:
        """Echo command."""
        if not args:
            return "Usage: !echo <text>"
        return f"Echo: {args}"


async def main():
    """Run the command bot."""
    parser = argparse.ArgumentParser(description="Command bot for WhatsApp Clone")
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Server URL",
    )
    parser.add_argument(
        "--user",
        default="cmdbot",
        help="Bot username",
    )
    parser.add_argument(
        "--password",
        default="bot_password",
        help="Bot password",
    )
    
    args = parser.parse_args()
    
    async with AsyncClient(
        server_url=args.server,
        storage_path="/tmp/whatsapp_cmdbot",
    ) as client:
        # Login
        try:
            await client.register(args.user, args.password)
            logger.info(f"Registered {args.user}")
        except:
            await client.login(args.user, args.password)
            logger.info(f"Logged in {args.user}")
        
        # Create bot
        bot = CommandBot(client)
        
        # Register handler
        @client.on_message
        async def handle(msg):
            await bot.handle_message(msg)
        
        logger.info("Command bot started. Use !help for available commands")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
