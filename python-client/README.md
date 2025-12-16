# WhatsApp Clone Python Client

A Python client library for the WhatsApp Clone E2EE chat application. This library provides programmatic access to send and receive end-to-end encrypted messages, enabling developers to build bots, automation tools, and integrations.

## Features

- 🔐 End-to-End Encryption (E2EE) support
- 🚀 Async/await API design
- 📱 Real-time messaging via WebSocket
- 🤖 Perfect for building chat bots
- 🔑 Automatic key management
- 📦 Type hints throughout

## Installation

```bash
pip install whatsapp-client
```

## Quick Start

```python
import asyncio
from whatsapp_client import WhatsAppClient

async def main():
    # Initialize client
    client = WhatsAppClient(
        server_url="https://your-worker.workers.dev"
    )
    
    # Register new user
    await client.register(
        username="bot_user",
        password="secure_password"
    )
    
    # Or login with existing credentials
    await client.login(
        username="bot_user",
        password="secure_password"
    )
    
    print(f"Logged in as {client.user.username}")
    
    # Send a message
    message = await client.send_message(
        to="user_id_123",
        content="Hello, World!"
    )
    
    # Receive messages
    @client.on_message
    async def handle_message(message):
        print(f"From {message.from_user}: {message.content}")
        
        # Auto-reply
        await client.send_message(
            to=message.from_user,
            content="Got your message!"
        )
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

See the [User Stories](../docs/USER_STORIES_PYTHON_WRAPPER.md) and [Technical Design](../docs/DESIGN_PYTHON_WRAPPER.md) for detailed documentation.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/suneesh/whatsapp-clone.git
cd whatsapp-clone/python-client

# Install in development mode
pip install -e ".[dev]"
```

### Testing

```bash
pytest
pytest --cov=whatsapp_client
```

### Type Checking

```bash
mypy src/whatsapp_client
```

### Code Formatting

```bash
black src tests
ruff check src tests
```

## License

MIT
