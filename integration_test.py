#!/usr/bin/env python
"""Integration test: verify bot can receive and send messages."""

import asyncio
import sys
sys.path.insert(0, 'D:\\Codebase\\python-client\\src')

from whatsapp_client import WhatsAppClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def main():
    # Shared state for message handlers
    messages_received = []
    client_messages_received = []
    
    # Create two clients
    bot_client = WhatsAppClient(server_url='https://whatsapp-clone-worker.hi-suneesh.workers.dev')
    test_client = WhatsAppClient(server_url='https://whatsapp-clone-worker.hi-suneesh.workers.dev')
    
    # Set up message handlers BEFORE registration to avoid race conditions
    @bot_client.on_message
    async def bot_handle_message(msg):
        print(f"[BOT MSG] Bot received message: {msg.content}")
        messages_received.append(msg)
        
        # Send echo response
        try:
            print(f"  [ECHO] Sending echo response...")
            response = await bot_client.send_message(msg.from_user, f"Echo: {msg.content}")
            print(f"  [ECHO OK] Echo sent: {response.id}")
        except Exception as e:
            print(f"  [ECHO ERR] Echo failed: {e}")
            import traceback
            traceback.print_exc()
    
    @test_client.on_message
    async def client_handle_message(msg):
        print(f"[CLIENT MSG] Client received: {msg.content}")
        client_messages_received.append(msg)
    
    # Register bot
    bot_user = f'bot_test_{timestamp}'
    bot = await bot_client.register(bot_user, 'secret')
    print(f"[BOT OK] Bot registered: {bot.id}")
    
    # Register test client
    client_user = f'client_test_{timestamp}'
    client = await test_client.register(client_user, 'secret')
    print(f"[CLIENT OK] Client registered: {client.id}")
    
    # Send message from client to bot
    print(f"\n[SEND] Sending message from client to bot...")
    msg = await test_client.send_message(bot.id, "Hello Bot!")
    print(f"[SEND OK] Message sent: {msg.id}")
    
    # Wait for echo response
    print("[WAIT] Waiting for echo response (10 seconds)...")
    await asyncio.sleep(10)
    
    # Check results
    if messages_received:
        print(f"\n[BOT] Bot received {len(messages_received)} message(s)")
        if client_messages_received:
            print(f"[CLIENT] Client received echo response!")
        else:
            print(f"[CLIENT] Client did NOT receive echo response")
    else:
        print(f"\n[BOT] Bot did NOT receive any messages")
    
    await bot_client.close()
    await test_client.close()

if __name__ == "__main__":
    asyncio.run(main())
