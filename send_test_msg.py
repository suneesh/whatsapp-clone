#!/usr/bin/env python
"""Send test message to echo bot and wait for response."""

import asyncio
import sys
import time
sys.path.insert(0, 'D:\\Codebase\\python-client\\src')

from whatsapp_client import WhatsAppClient

async def main():
    # Create test client
    client = WhatsAppClient(server_url='https://whatsapp-clone-worker.hi-suneesh.workers.dev')
    
    # Register/login
    username = f'testclient_v5'
    password = 'secret'
    
    try:
        user = await client.register(username, password)
        print(f"✓ Registered as {user.username} (ID: {user.id})")
    except Exception as e:
        print(f"✗ Registration failed: {e}")
        user = await client.login(username, password)
        print(f"✓ Logged in as {user.username}")
    
    # Get bot's ID
    bot_id = '4db80125-0033-4421-b9a2-c026cdcf4e0f'  # echobot_test
    
    # Set up message handler  
    @client.on_message
    async def handle_message(msg):
        print(f"✓ Received from {msg.from_user}: {msg.content}")
    
    # Send message
    print(f"Sending message to bot {bot_id}...")
    try:
        response = await client.send_message(bot_id, "Hello Echo Bot!")
        print(f"✓ Message sent (ID: {response.id})")
    except Exception as e:
        print(f"✗ Send failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Wait for response
    print("Waiting 10 seconds for bot response...")
    await asyncio.sleep(10)
    
    await client.close()
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
