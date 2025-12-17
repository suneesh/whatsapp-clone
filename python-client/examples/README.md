# WhatsApp Clone Python Client - Examples

This directory contains example bots and usage patterns for the WhatsApp Clone Python client library.

## Quick Start

### Installation

```bash
# Install from source
cd ..
pip install -e .
```

### Basic Usage

```python
import asyncio
from whatsapp_client import AsyncClient

async def main():
    async with AsyncClient(server_url="http://localhost:8000") as client:
        # Register or login
        user = await client.register("alice", "password123")
        # OR
        # user = await client.login("alice", "password123")
        
        # Send a message
        message = await client.send_message("bob", "Hello Bob!")
        print(f"Message sent: {message.id}")
        
        # Listen for messages
        @client.on_message
        async def handle_message(msg):
            print(f"Message from {msg.from_user}: {msg.content}")
        
        # Keep running
        await asyncio.Event().wait()

asyncio.run(main())
```

## Examples

### 1. Echo Bot

The echo bot demonstrates basic message handling and response.

**Features:**
- Simple message reception and echoing
- Basic event handling with decorators
- Command-line argument parsing

**Run:**
```bash
python echo_bot.py --server http://localhost:8000 --user echobot --password secret
```

**Usage:**
- Send any message to the bot and it will echo it back

**Source:** `echo_bot.py`

### 2. Command Bot

The command bot shows advanced parsing and state queries.

**Features:**
- Command parsing (!command args)
- Bot state queries (online users, connection status)
- Error handling and validation
- Extensible command structure

**Available Commands:**
- `!help` - Show available commands
- `!ping` - Check bot responsiveness
- `!users` - List online users
- `!status` - Show bot status
- `!echo <text>` - Echo back text

**Run:**
```bash
python command_bot.py --server http://localhost:8000 --user cmdbot --password secret
```

**Usage:**
- Send `!help` to see available commands
- Send `!ping` to check if bot is responsive
- Send `!echo hello` to echo a message

**Source:** `command_bot.py`

### 3. Group Bot

The group bot demonstrates group management and broadcasting.

**Features:**
- Group creation and member management
- Broadcasting messages to groups
- Group event handling
- Multiple concurrent operations

**Run:**
```bash
python group_bot.py --server http://localhost:8000 --user groupbot --password secret
```

**Usage:**
- Bot automatically creates an example group
- Send messages to the group
- Bot responds to commands in the group

**Source:** `group_bot.py`

## Common Patterns

### Event Handling with Decorators

```python
@client.on_message
async def handle_message(message):
    print(f"From {message.from_user}: {message.content}")

@client.on_typing
async def handle_typing(data):
    print(f"{data['user']} is typing")

@client.on_presence
async def handle_presence(data):
    print(f"{data['user']} is {'online' if data['online'] else 'offline'}")

@client.on_status
async def handle_status(data):
    print(f"Message {data['message_id']} status: {data['status']}")

@client.on_group_message
async def handle_group_message(message):
    print(f"[{message['group_id']}] {message['from_user']}: {message['content']}")
```

### Async Context Manager

```python
async with AsyncClient(server_url="...") as client:
    await client.login("user", "password")
    # Use client...
# Automatically cleaned up and closed
```

### Multiple Concurrent Clients

```python
async def client_task(user_id):
    async with AsyncClient(server_url="...") as client:
        await client.login(user_id, f"pass_{user_id}")
        # Use client...

# Run multiple clients concurrently
await asyncio.gather(
    client_task("alice"),
    client_task("bob"),
    client_task("charlie"),
)
```

### Message Sending

```python
# Send text message
msg = await client.send_message("bob", "Hello!")

# Send with encryption
msg = await client.send_message("bob", "Secret", encrypted=True)

# Send image
msg = await client.send_image("bob", path="/path/to/image.jpg", caption="My photo")

# Send to group
msg = await client.send_group_message("group_123", "Group message")
```

### Message History

```python
# Get recent messages with a user
messages = await client.get_messages("bob", limit=50)

# Search messages
results = await client.search_messages("hello", limit=20)

# Get conversations
conversations = await client.get_conversations(limit=10)
```

### User Discovery

```python
# Get online users
online_users = client.get_online_users()

# Check if user is online
is_online = client.is_user_online("bob")

# List verified fingerprints (for security)
verified = await client.get_verified_fingerprints()
```

### Group Management

```python
# Create group
group_id = await client.create_group(
    name="Team Chat",
    description="Team communication",
)

# Add member
await client.add_group_member(group_id, "alice")

# Remove member
await client.remove_group_member(group_id, "bob")

# Leave group
await client.leave_group(group_id)

# Get group info
group = await client.get_group(group_id)
```

### Error Handling

```python
from whatsapp_client import WhatsAppClientError, AuthenticationError

try:
    await client.login("user", "wrong_password")
except AuthenticationError as e:
    print(f"Login failed: {e}")
except WhatsAppClientError as e:
    print(f"Client error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Configuration

```python
from whatsapp_client import AsyncClient
from whatsapp_client.config import ClientConfig

# Create custom config
config = ClientConfig(
    server_url="http://localhost:8000",
    storage_path="/tmp/my_client",
    key_encryption_enabled=True,
    max_file_size_mb=50,
    log_level="DEBUG",
)

# Create client with config
client = AsyncClient(
    server_url=config.server_url,
    storage_path=config.storage_path,
)
```

### Background Task Management

```python
# Access background tasks
task_count = await client.get_background_task_count()
print(f"Running tasks: {task_count}")

# Get exceptions from background tasks
exceptions = await client.get_background_exceptions()
for exc in exceptions:
    print(f"Background error: {exc}")

# Get running state
state = client.get_running_state()
print(f"Connected: {state['is_connected']}")
print(f"Authenticated: {state['is_authenticated']}")
```

## Testing

All examples have been tested with the WhatsApp Clone backend. To run tests:

```bash
# Run full test suite
cd ..
pytest tests/ -v

# Run specific example test
pytest tests/test_integration.py -k echo -v
```

## Performance

The client is designed for:
- **Low latency**: Real-time message delivery (< 100ms)
- **High throughput**: Thousands of messages per second per client
- **Concurrent clients**: Multiple clients running concurrently in same event loop
- **Scalability**: Async/await for efficient resource usage

## Troubleshooting

### Connection Issues

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check server health
state = client.get_running_state()
print(f"Connected: {state['is_connected']}")
```

### Memory Leaks

```python
# Always use context manager
async with AsyncClient(...) as client:
    # Your code
    # Automatic cleanup

# Or manually close
client = AsyncClient(...)
await client.login(...)
# ... use client ...
await client.close()
```

### Timeout Issues

```python
from whatsapp_client.async_utils import EventLoopManager

# Run with timeout
result = await EventLoopManager.run_with_timeout(
    client.send_message("bob", "Hello"),
    timeout=5.0,
)
```

## API Reference

See the main README for full API documentation: `../README.md`

## Contributing Examples

To add your own example:

1. Create a new Python file in this directory
2. Add clear docstring with description and usage
3. Include argument parsing for server/credentials
4. Test with the backend
5. Update this README

## License

Same as main project - See LICENSE file
