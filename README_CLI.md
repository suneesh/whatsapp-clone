# WhatsApp Clone CLI Client

A command-line interface for the WhatsApp Clone E2E encrypted messaging platform.

## Features

- 🔐 User registration and login
- 📨 Send and receive E2E encrypted messages in real-time
- 🔗 Session management for encrypted conversations
- 🔐 Display encryption fingerprints for verification
- 🚀 Interactive command-line interface

## Installation

Make sure you have Python 3.8+ installed and the python-client package available.

## Usage

### Running the CLI

```bash
python whatsapp_cli.py
```

### Commands

#### Authentication
- `register <username> <password>` - Register a new account
- `login <username> <password>` - Login to existing account

#### Messaging
- `send <user_id> <message>` - Send an encrypted message to another user

#### Information
- `sessions` - List your active encrypted sessions
- `fingerprint` - Display your encryption fingerprint

#### Other
- `help` - Show available commands
- `quit` - Exit the application

### Example Session

```
🚀 WhatsApp Clone CLI Client
Commands: register <username> <password>, login <username> <password>
         send <user_id> <message>, sessions, fingerprint, help, quit
❓ register alice mypassword123
🔐 Registering user: alice
✅ Registration successful! User ID: abc-123-def

💬 login bob secretpass
🔑 Logging in as: bob
✅ Login successful! User ID: xyz-789-ghi

💬 send abc-123-def Hello Alice!
📤 Message sent to abc-123-def: msg-456

📨 [abc-123-def] Hi Bob!

💬 fingerprint
🔐 Your fingerprint: ABCDEF123456...

💬 quit
👋 Goodbye!
```

## Security

All messages are end-to-end encrypted using the Signal protocol implementation:
- X3DH key exchange for initial session establishment
- Double Ratchet algorithm for forward secrecy
- Automatic key rotation and session management

## Architecture

The CLI uses the WhatsApp Python client wrapper which provides:
- Asynchronous WebSocket connections for real-time messaging
- Automatic encryption/decryption of messages
- Secure key storage and management
- Session persistence across restarts

## Troubleshooting

### Connection Issues
- Ensure you have internet connectivity
- Check that the server URL is accessible
- Verify your credentials are correct

### Message Issues
- Make sure the recipient user ID is correct
- Check that both users are online for real-time messaging
- Messages may be delivered when the recipient comes online

### Encryption Issues
- Use `fingerprint` command to verify encryption keys
- Check `sessions` to see active encrypted conversations
- Reset encryption if keys become out of sync</content>
<parameter name="filePath">d:\Codebase\README_CLI.md