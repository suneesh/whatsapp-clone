# Changelog

All notable changes to the WhatsApp Clone Python Client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-17

### Added
- Initial release of WhatsApp Clone Python Client
- Complete E2E encryption with X3DH and Double Ratchet
- Real-time messaging with WebSocket support
- User authentication and key management
- Message status tracking and read receipts
- Typing indicators and presence tracking
- Image and file sending/receiving
- Group chat support with member management
- Key fingerprint verification for MITM protection
- Local encrypted key persistence with Argon2id
- Comprehensive error handling and logging
- Configuration management with environment variable support
- Full async event loop integration
- AsyncClient with background task management
- TaskManager for lifecycle management
- Multiple concurrent client support
- Example bots (echo, command, group, concurrent)
- Comprehensive test suite (288 tests, 79% coverage)
- Documentation and API reference

### Features
#### Cryptography
- X3DH key exchange for session establishment
- Double Ratchet algorithm for forward secrecy
- NaCl SecretBox (XSalsa20-Poly1305) for message encryption
- HKDF-SHA256 for key derivation
- Argon2id for password-based key derivation
- AES-256-GCM for key file encryption

#### Messaging
- Real-time message delivery
- Message encryption and decryption
- Message status tracking (sent, delivered, read)
- Read receipts and auto-mark-read
- Message history and persistence
- Full-text message search
- Image and file transfers

#### User Management
- User registration and authentication
- Online presence tracking
- Typing indicators
- User discovery
- Fingerprint verification

#### Group Features
- Group creation and management
- Member management (add, remove, promote)
- Role-based access control
- Group messaging and broadcast
- Leave group functionality

#### Client Features
- Async/await throughout
- Context manager support
- Background task management
- Exception tracking and handling
- Structured logging
- Configuration management
- Multiple concurrent clients

### Documentation
- Complete API reference
- Usage examples (4 bots)
- Quick start guide
- Configuration guide
- Contributing guidelines

### Testing
- 288 comprehensive tests
- 79% code coverage
- Unit, integration, and edge case tests
- All core features tested
- AsyncIO integration tests

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking API changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

## Support

For issues, questions, or contributions, please visit:
https://github.com/suneesh/whatsapp-clone

## License

This project is licensed under the MIT License - see the LICENSE file for details.
