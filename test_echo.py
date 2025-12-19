#!/usr/bin/env python3
"""Test script to send a message to the echo bot."""

import asyncio
import sys
import uuid
sys.path.insert(0, 'python-client/src')

from whatsapp_client import AsyncClient

async def main():
    # Use a unique username each time to force fresh X3DH
    username = f"testuser{uuid.uuid4().hex[:8]}"
    
    client = AsyncClient(
        server_url="https://whatsapp-clone-worker.hi-suneesh.workers.dev"
    )
    
    # Register new user
    try:
        await client.register(username, "testpass")
        print(f"Registered as {username}")
    except Exception as e:
        print(f"Register failed: {e}")
        return
    
    # Send a message to echobot
    try:
        response = await client.send_message("562d86a6-dbdc-4606-8f1c-5b7b57631fdc", "Hello Echo!")
        print(f"Sent: {response.id}")
    except Exception as e:
        print(f"Send failed: {e}")
    
    await asyncio.sleep(1)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
