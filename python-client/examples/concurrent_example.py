"""
Concurrent Operations Example - Shows running multiple clients concurrently.

This example demonstrates:
- Multiple AsyncClient instances
- Concurrent operations with asyncio.gather
- Background task management
- Real-time message exchange
- Resource cleanup with context managers

Usage:
    python concurrent_example.py --server http://localhost:8000

This script:
1. Creates multiple bot instances
2. Runs them concurrently
3. Exchanges messages between them
4. Cleans up resources properly
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


class SimpleBot:
    """Simple bot for concurrent example."""
    
    def __init__(self, name: str, client: AsyncClient):
        """Initialize bot."""
        self.name = name
        self.client = client
        self.messages_received = []
    
    async def start(self):
        """Start the bot."""
        try:
            # Register
            await self.client.register(self.name, f"password_{self.name}")
            logger.info(f"[{self.name}] Registered")
        except:
            # Login
            await self.client.login(self.name, f"password_{self.name}")
            logger.info(f"[{self.name}] Logged in")
        
        # Register message handler
        @self.client.on_message
        async def handle(msg):
            self.messages_received.append(msg)
            logger.info(f"[{self.name}] Received: {msg.content}")
            
            # Auto-reply
            if msg.content.startswith("Hello"):
                response = f"Hi {msg.from_user}, I'm {self.name}!"
                await self.client.send_message(msg.from_user, response)
    
    async def run_for(self, duration: float):
        """Run bot for specified duration."""
        logger.info(f"[{self.name}] Running for {duration} seconds")
        await asyncio.sleep(duration)
        logger.info(f"[{self.name}] Received {len(self.messages_received)} messages")
    
    async def cleanup(self):
        """Cleanup bot."""
        logger.info(f"[{self.name}] Cleaning up")


async def create_bot(name: str, server_url: str) -> SimpleBot:
    """Create and start a bot."""
    client = AsyncClient(
        server_url=server_url,
        storage_path=f"/tmp/whatsapp_{name}",
    )
    
    bot = SimpleBot(name, client)
    await bot.start()
    
    return bot


async def run_concurrent_bots(
    bot_names: list,
    server_url: str,
    duration: float = 10.0,
):
    """Run multiple bots concurrently."""
    
    # Create all bots
    logger.info(f"Creating {len(bot_names)} bots")
    bots = []
    clients = []
    
    try:
        # Create and initialize bots
        for name in bot_names:
            client = AsyncClient(
                server_url=server_url,
                storage_path=f"/tmp/whatsapp_{name}",
            )
            clients.append(client)
            
            bot = SimpleBot(name, client)
            await bot.start()
            bots.append(bot)
        
        logger.info(f"All {len(bots)} bots started")
        
        # Let them run for a bit to stabilize
        await asyncio.sleep(1)
        
        # Send initial messages between bots
        if len(bots) >= 2:
            logger.info("Sending initial messages")
            for i, bot in enumerate(bots):
                if i < len(bots) - 1:
                    other_bot = bots[i + 1]
                    message = f"Hello {other_bot.name}! I'm {bot.name}"
                    try:
                        await bot.client.send_message(
                            other_bot.name,
                            message,
                        )
                        logger.info(f"[{bot.name}] Sent to {other_bot.name}")
                    except Exception as e:
                        logger.error(f"Failed to send: {e}")
        
        # Run all bots concurrently
        logger.info(f"Running {len(bots)} bots concurrently for {duration}s")
        
        tasks = [
            bot.run_for(duration)
            for bot in bots
        ]
        
        await asyncio.gather(*tasks)
        
        logger.info("All bots finished")
        
        # Summary
        logger.info("\n=== Final Summary ===")
        for bot in bots:
            logger.info(f"{bot.name}:")
            logger.info(f"  - Messages received: {len(bot.messages_received)}")
            if bot.messages_received:
                for msg in bot.messages_received[-3:]:  # Last 3 messages
                    logger.info(f"    • {msg.from_user}: {msg.content}")
        
    finally:
        # Cleanup all clients
        logger.info("Cleaning up resources")
        for client in clients:
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        logger.info("Done")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Concurrent operations example"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Server URL",
    )
    parser.add_argument(
        "--bots",
        type=int,
        default=3,
        help="Number of bots to create (default: 3)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Duration to run in seconds (default: 10)",
    )
    
    args = parser.parse_args()
    
    # Create bot names
    bot_names = [f"bot_{i}" for i in range(args.bots)]
    
    await run_concurrent_bots(
        bot_names,
        args.server,
        args.duration,
    )


if __name__ == "__main__":
    asyncio.run(main())
