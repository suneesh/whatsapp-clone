# Software Requirements Specification (SRS)
## End-to-End Encryption for Peer-to-Peer Chats

---

## Document Information

| Field | Value |
|-------|-------|
| **Document ID** | SRS-E2EE-001 |
| **Project** | WhatsApp Clone - End-to-End Encryption |
| **Version** | 1.0 |
| **Status** | Draft |
| **Date** | 2025-12-16 |
| **Author** | Development Team |
| **Priority** | High |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Features](#3-system-features)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Security Requirements](#6-security-requirements)
7. [Cryptographic Specifications](#7-cryptographic-specifications)
8. [Data Requirements](#8-data-requirements)
9. [System Constraints](#9-system-constraints)
10. [Technical Architecture](#10-technical-architecture)
11. [Implementation Plan](#11-implementation-plan)
12. [Testing Requirements](#12-testing-requirements)
13. [Appendices](#13-appendices)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document describes the requirements for implementing end-to-end encryption (E2EE) for peer-to-peer chat functionality in the WhatsApp Clone application. The system will ensure that only the intended recipients can read messages, providing privacy and security for all user communications.

### 1.2 Scope

The E2EE implementation will:

**In Scope:**
- End-to-end encryption for one-on-one text messages
- End-to-end encryption for one-on-one image messages
- Secure key generation and exchange using Signal Protocol (Double Ratchet Algorithm)
- Client-side encryption and decryption
- Key storage and management in browser
- Identity verification mechanisms
- Encrypted message persistence
- Key rotation and forward secrecy

**Out of Scope (Future Enhancements):**
- Group chat end-to-end encryption (requires separate implementation)
- Voice/video call encryption
- File sharing encryption (beyond images)
- Cross-device synchronization
- Cloud backup of encrypted messages
- Key recovery mechanisms

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| **E2EE** | End-to-End Encryption |
| **Signal Protocol** | Cryptographic protocol combining Double Ratchet, X3DH, and Prekeys |
| **Double Ratchet** | Key derivation algorithm providing forward and backward secrecy |
| **X3DH** | Extended Triple Diffie-Hellman key agreement protocol |
| **Identity Key** | Long-term public/private key pair identifying a user |
| **Prekey** | One-time public key used for asynchronous key exchange |
| **Signed Prekey** | Periodically rotated prekey signed by identity key |
| **Session Key** | Ephemeral key used for encrypting a message |
| **ECDH** | Elliptic Curve Diffie-Hellman key exchange |
| **HKDF** | HMAC-based Key Derivation Function |
| **AEAD** | Authenticated Encryption with Associated Data |
| **Forward Secrecy** | Past messages remain secure even if current keys are compromised |
| **Backward Secrecy** | Future messages remain secure even if current keys are compromised |

### 1.4 References

- Signal Protocol Specifications: https://signal.org/docs/
- Web Crypto API: https://www.w3.org/TR/WebCryptoAPI/
- NIST SP 800-56A: Recommendation for Pair-Wise Key Establishment Schemes
- RFC 7748: Elliptic Curves for Security (Curve25519)
- RFC 5869: HMAC-based Extract-and-Expand Key Derivation Function (HKDF)

### 1.5 Overview

This document describes the functional and non-functional requirements for implementing end-to-end encryption in the WhatsApp Clone application. It covers cryptographic algorithms, key management, message encryption/decryption, security considerations, and implementation details.

---

## 2. Overall Description

### 2.1 Product Perspective

The E2EE feature will be integrated into the existing WhatsApp Clone application as a core security layer for peer-to-peer messaging. It operates at the client level, ensuring that the server cannot decrypt message content.

**System Context:**
```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Browser A                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   React UI   │  │  Crypto      │  │  Key Storage         │ │
│  │              │←→│  Engine      │←→│  (IndexedDB)         │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│         ↓                  ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          WebSocket (Encrypted Messages Only)             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Worker (Server)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Routes encrypted messages (cannot decrypt)            │  │
│  │  • Stores encrypted messages in database                 │  │
│  │  • Manages prekey bundles                                │  │
│  │  • Facilitates key exchange                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Client Browser B                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   React UI   │  │  Crypto      │  │  Key Storage         │ │
│  │              │←→│  Engine      │←→│  (IndexedDB)         │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Functions

The E2EE system will provide the following high-level functions:

1. **Key Generation and Management**
   - Generate identity key pairs on user registration
   - Generate and rotate prekey bundles
   - Store keys securely in browser storage
   - Publish public keys to server

2. **Session Establishment**
   - Perform X3DH key agreement for new conversations
   - Derive initial chain keys and message keys
   - Initialize Double Ratchet state

3. **Message Encryption**
   - Encrypt plaintext messages with current message key
   - Advance ratchet state after encryption
   - Include authentication data in ciphertext
   - Handle out-of-order messages

4. **Message Decryption**
   - Decrypt received ciphertext with derived message key
   - Verify message authenticity
   - Detect and handle replay attacks
   - Manage message key skipping for out-of-order messages

5. **Security Indicators**
   - Display encryption status in UI
   - Show key fingerprints for verification
   - Indicate when encryption is active
   - Warn about key changes

### 2.3 User Classes and Characteristics

| User Class | Characteristics | Technical Skill | Security Awareness |
|-----------|-----------------|-----------------|-------------------|
| **End User** | Regular chat application user | Low to Medium | Low - expects automatic encryption |
| **Privacy-Conscious User** | Verifies contacts, checks encryption status | Medium | High - verifies fingerprints |
| **Administrator** | Manages server but cannot decrypt messages | High | High - understands E2EE limitations |
| **Developer** | Implements and maintains E2EE system | Very High | Very High - security expert |

### 2.4 Operating Environment

**Client Environment:**
- Modern web browsers supporting Web Crypto API:
  - Chrome/Edge 37+
  - Firefox 34+
  - Safari 11+
  - Mobile browsers (iOS Safari 11+, Chrome Mobile)
- IndexedDB support for key storage
- JavaScript enabled
- Minimum 2GB RAM recommended

**Server Environment:**
- Cloudflare Workers runtime
- Cloudflare D1 (SQLite) database
- Durable Objects for WebSocket connections

**Network Requirements:**
- HTTPS/WSS connections required
- Minimum bandwidth: 128 kbps
- WebSocket support

### 2.5 Design and Implementation Constraints

**Technical Constraints:**
- Must use Web Crypto API (no external crypto libraries initially)
- Browser-based key storage (IndexedDB)
- No hardware security module (HSM) access
- Limited to browser cryptographic capabilities
- Must maintain backward compatibility with unencrypted messages during transition

**Regulatory Constraints:**
- GDPR compliance for EU users
- Export control regulations for cryptography
- Local data protection laws

**Performance Constraints:**
- Message encryption must complete within 100ms
- Key generation should not block UI (async operations)
- Minimal impact on message throughput
- Support for up to 10,000 stored message keys

### 2.6 Assumptions and Dependencies

**Assumptions:**
1. Users have access to modern browsers with Web Crypto API
2. Users understand basic security concepts (optional for basic usage)
3. Server infrastructure is trusted for routing (but not for decryption)
4. Users maintain single browser session (no multi-device sync initially)
5. Clock synchronization within reasonable bounds (±5 minutes)

**Dependencies:**
1. Web Crypto API availability and stability
2. IndexedDB for persistent key storage
3. Secure WebSocket (WSS) connection
4. HTTPS for all API communications
5. Server support for prekey bundle management

---

## 3. System Features

### 3.1 User Registration and Key Generation

**Priority:** Critical
**Risk:** High

#### 3.1.1 Description

When a user registers or first enables E2EE, the system generates a complete set of cryptographic keys including identity keys, signed prekeys, and one-time prekeys.

#### 3.1.2 Functional Requirements

**FR-REG-001:** The system SHALL generate a Curve25519 identity key pair during user registration.

**FR-REG-002:** The system SHALL generate a signed prekey and sign it with the identity private key.

**FR-REG-003:** The system SHALL generate a batch of 100 one-time prekeys.

**FR-REG-004:** The system SHALL store private keys securely in IndexedDB with encryption.

**FR-REG-005:** The system SHALL upload public keys (identity public key, signed prekey, and one-time prekeys) to the server.

**FR-REG-006:** The system SHALL generate a unique key fingerprint from the identity public key for user verification.

**FR-REG-007:** The system SHALL complete key generation asynchronously without blocking the UI.

**FR-REG-008:** The system SHALL display a security code/fingerprint to the user for out-of-band verification.

#### 3.1.3 Use Case

**Use Case ID:** UC-001
**Title:** New User Enables E2EE

**Actor:** End User

**Preconditions:**
- User has registered an account
- User is logged into the application
- Browser supports Web Crypto API

**Main Flow:**
1. User navigates to security settings or is prompted on first message
2. System displays E2EE enablement dialog
3. User confirms enablement
4. System generates identity key pair in background
5. System generates signed prekey
6. System generates 100 one-time prekeys
7. System stores private keys in IndexedDB
8. System uploads public key bundle to server
9. System displays success message with security code
10. E2EE is now enabled for user

**Postconditions:**
- User has complete key set generated and stored
- Public keys are available on server for key exchange
- User can send and receive encrypted messages

**Alternative Flows:**
- **4a.** Key generation fails: Display error, allow retry
- **8a.** Network error during upload: Queue for retry, allow offline key generation

---

### 3.2 Key Exchange and Session Establishment

**Priority:** Critical
**Risk:** High

#### 3.2.1 Description

Before sending the first message to a recipient, the sender must establish a shared secret using the X3DH (Extended Triple Diffie-Hellman) protocol.

#### 3.2.2 Functional Requirements

**FR-EXCH-001:** The system SHALL fetch the recipient's public key bundle before sending the first message.

**FR-EXCH-002:** The system SHALL perform X3DH key agreement using:
- Sender's identity private key
- Sender's ephemeral private key
- Recipient's identity public key
- Recipient's signed prekey
- Recipient's one-time prekey (if available)

**FR-EXCH-003:** The system SHALL derive a shared secret using HKDF from the X3DH output.

**FR-EXCH-004:** The system SHALL initialize the Double Ratchet state with the shared secret.

**FR-EXCH-005:** The system SHALL send an initial message containing:
- Sender's identity public key
- Sender's ephemeral public key
- Used one-time prekey ID
- Encrypted message payload

**FR-EXCH-006:** The system SHALL mark one-time prekeys as used after consumption.

**FR-EXCH-007:** The system SHALL fall back to signed prekey if no one-time prekeys are available.

**FR-EXCH-008:** The system SHALL cache session state to avoid repeated key exchanges.

#### 3.2.3 X3DH Protocol Flow

```
Alice (Sender)                                          Bob (Recipient)
     │                                                        │
     │  1. Fetch Bob's prekey bundle                        │
     │ ─────────────────────────────────────────────────────▶│
     │                                                        │
     │  2. Receive bundle:                                   │
     │     - Identity Key (IKb)                              │
     │     - Signed Prekey (SPKb)                            │
     │     - One-time Prekey (OPKb)                          │
     │ ◀─────────────────────────────────────────────────────│
     │                                                        │
     │  3. Generate ephemeral key (EKa)                      │
     │                                                        │
     │  4. Perform DH operations:                            │
     │     DH1 = DH(IKa, SPKb)                               │
     │     DH2 = DH(EKa, IKb)                                │
     │     DH3 = DH(EKa, SPKb)                               │
     │     DH4 = DH(EKa, OPKb)  [if OPK available]           │
     │                                                        │
     │  5. Derive shared secret:                             │
     │     SK = HKDF(DH1 || DH2 || DH3 || DH4)               │
     │                                                        │
     │  6. Initialize Double Ratchet with SK                 │
     │                                                        │
     │  7. Encrypt first message                             │
     │                                                        │
     │  8. Send initial message with:                        │
     │     - IKa (Identity Key)                              │
     │     - EKa (Ephemeral Key)                             │
     │     - Used OPK ID                                     │
     │     - Encrypted payload                               │
     │ ─────────────────────────────────────────────────────▶│
     │                                                        │
     │                                  9. Receive message   │
     │                                  10. Perform same DHs │
     │                                  11. Derive same SK   │
     │                                  12. Decrypt message  │
     │                                                        │
```

---

### 3.3 Message Encryption

**Priority:** Critical
**Risk:** High

#### 3.3.1 Description

All peer-to-peer messages (text and images) are encrypted using the Double Ratchet algorithm before transmission.

#### 3.3.2 Functional Requirements

**FR-ENC-001:** The system SHALL encrypt all message content before sending.

**FR-ENC-002:** The system SHALL use AES-256-GCM for symmetric encryption.

**FR-ENC-003:** The system SHALL derive a unique message key for each message using the Double Ratchet.

**FR-ENC-004:** The system SHALL include message header containing:
- Ratchet public key
- Previous chain length
- Message number in current chain

**FR-ENC-005:** The system SHALL compute HMAC over the encrypted message for authenticity.

**FR-ENC-006:** The system SHALL never reuse message keys.

**FR-ENC-007:** The system SHALL delete message keys immediately after use.

**FR-ENC-008:** The system SHALL encrypt image data as base64 strings before transmission.

**FR-ENC-009:** The system SHALL advance the sending chain after successful encryption.

**FR-ENC-010:** The system SHALL handle encryption failures gracefully without exposing plaintext.

#### 3.3.3 Encryption Process

```
Plaintext Message
     ↓
┌────────────────────────────────────┐
│  1. Get current sending chain key  │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  2. Derive message key using KDF   │
│     MK = HKDF(ChainKey, "message") │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  3. Generate random IV (nonce)     │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  4. Encrypt with AES-256-GCM       │
│     CT = AES-GCM(MK, IV, PT)       │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  5. Create message header          │
│     - Ratchet public key           │
│     - Previous chain length        │
│     - Message number               │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  6. Advance ratchet state          │
│     - Increment message number     │
│     - Update chain key             │
│     - Perform DH ratchet if needed │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  7. Construct encrypted message    │
│     {header, ciphertext, auth_tag} │
└────────────────────────────────────┘
     ↓
Encrypted Message → Send via WebSocket
```

---

### 3.4 Message Decryption

**Priority:** Critical
**Risk:** High

#### 3.4.1 Description

Received encrypted messages are decrypted using the Double Ratchet algorithm, which handles out-of-order delivery and key derivation.

#### 3.4.2 Functional Requirements

**FR-DEC-001:** The system SHALL decrypt received encrypted messages using the Double Ratchet.

**FR-DEC-002:** The system SHALL verify message authenticity before decryption.

**FR-DEC-003:** The system SHALL handle out-of-order message delivery.

**FR-DEC-004:** The system SHALL skip message keys for missing messages (up to a limit).

**FR-DEC-005:** The system SHALL store skipped message keys for delayed messages.

**FR-DEC-006:** The system SHALL limit skipped message key storage to prevent DoS (max 1000 keys).

**FR-DEC-007:** The system SHALL detect and reject replayed messages.

**FR-DEC-008:** The system SHALL perform DH ratchet when receiving a new ratchet public key.

**FR-DEC-009:** The system SHALL gracefully handle decryption failures and log errors.

**FR-DEC-010:** The system SHALL display decrypted plaintext only after successful verification.

**FR-DEC-011:** The system SHALL delete message keys immediately after decryption.

#### 3.4.3 Decryption Process

```
Encrypted Message Received
     ↓
┌────────────────────────────────────┐
│  1. Extract message header         │
│     - Ratchet public key           │
│     - Previous chain length        │
│     - Message number               │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  2. Check if DH ratchet needed     │
│     (new ratchet public key?)      │
└────────────────────────────────────┘
     ↓ Yes                        ↓ No
┌─────────────────────┐    ┌──────────────────────┐
│ Perform DH ratchet  │    │ Use existing chain   │
│ - Generate new keys │    │                      │
│ - Update state      │    │                      │
└─────────────────────┘    └──────────────────────┘
     ↓                              ↓
┌────────────────────────────────────────────────┐
│  3. Skip message keys if needed                │
│     (for out-of-order messages)                │
│     - Derive and store skipped keys            │
└────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  4. Derive message key             │
│     MK = HKDF(ChainKey, "message") │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  5. Verify authentication tag      │
│     (HMAC or GCM auth tag)         │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  6. Decrypt with AES-256-GCM       │
│     PT = AES-GCM-Decrypt(MK, CT)   │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  7. Advance receiving chain        │
│     - Increment message number     │
│     - Update chain key             │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│  8. Delete message key             │
└────────────────────────────────────┘
     ↓
Plaintext Message → Display in UI
```

---

### 3.5 Key Rotation and Prekey Replenishment

**Priority:** High
**Risk:** Medium

#### 3.5.1 Description

The system maintains a sufficient supply of one-time prekeys and periodically rotates signed prekeys to maintain forward secrecy.

#### 3.5.2 Functional Requirements

**FR-ROT-001:** The system SHALL monitor one-time prekey count on the server.

**FR-ROT-002:** The system SHALL generate new one-time prekeys when count drops below 20.

**FR-ROT-003:** The system SHALL rotate signed prekey every 7 days.

**FR-ROT-004:** The system SHALL keep old signed prekey for 7 days after rotation to handle in-flight messages.

**FR-ROT-005:** The system SHALL notify users when prekey rotation occurs (optional).

**FR-ROT-006:** The system SHALL automatically upload new prekeys to server.

**FR-ROT-007:** The system SHALL handle prekey rotation failures with exponential backoff retry.

---

### 3.6 Identity Verification

**Priority:** High
**Risk:** Medium

#### 3.6.1 Description

Users can verify each other's identity using safety numbers (fingerprints) to prevent man-in-the-middle attacks.

#### 3.6.2 Functional Requirements

**FR-VER-001:** The system SHALL generate a 60-digit safety number from identity keys.

**FR-VER-002:** The system SHALL display safety numbers in user-friendly format (groups of 5 digits).

**FR-VER-003:** The system SHALL provide QR code for safety number verification.

**FR-VER-004:** The system SHALL allow users to mark contacts as "verified."

**FR-VER-005:** The system SHALL show verification status in chat UI.

**FR-VER-006:** The system SHALL warn users when contact's identity key changes.

**FR-VER-007:** The system SHALL allow users to compare safety numbers out-of-band.

**FR-VER-008:** The system SHALL persist verification status across sessions.

---

### 3.7 User Interface for Encryption

**Priority:** Medium
**Risk:** Low

#### 3.7.1 Description

The UI provides clear indicators of encryption status, security information, and verification tools.

#### 3.7.2 Functional Requirements

**FR-UI-001:** The system SHALL display a lock icon when E2EE is active for a conversation.

**FR-UI-002:** The system SHALL show encryption status in chat header.

**FR-UI-003:** The system SHALL provide access to security information via chat settings.

**FR-UI-004:** The system SHALL display safety numbers for verification.

**FR-UI-005:** The system SHALL show encryption initializing state during first message.

**FR-UI-006:** The system SHALL warn when sending to unverified contact (optional).

**FR-UI-007:** The system SHALL display encryption errors in user-friendly language.

**FR-UI-008:** The system SHALL provide help/FAQ about E2EE in settings.

---

### 3.8 Encrypted Message Storage

**Priority:** Medium
**Risk:** Medium

#### 3.8.1 Description

Messages are stored encrypted in the database, ensuring server cannot read message content.

#### 3.8.2 Functional Requirements

**FR-STOR-001:** The system SHALL store messages in encrypted form in the database.

**FR-STOR-002:** The system SHALL store encryption metadata (header) with each message.

**FR-STOR-003:** The system SHALL NOT store message keys in the database.

**FR-STOR-004:** The system SHALL allow decryption of stored messages when user logs in.

**FR-STOR-005:** The system SHALL handle database corruption gracefully (skip undecryptable messages).

**FR-STOR-006:** The system SHALL store message sender's identity key reference for verification.

---

### 3.9 Migration from Unencrypted Messages

**Priority:** Medium
**Risk:** Low

#### 3.9.1 Description

The system smoothly transitions from unencrypted to encrypted messaging without disrupting user experience.

#### 3.9.2 Functional Requirements

**FR-MIG-001:** The system SHALL support both encrypted and unencrypted messages during transition.

**FR-MIG-002:** The system SHALL clearly indicate which messages are encrypted vs unencrypted.

**FR-MIG-003:** The system SHALL prompt users to enable E2EE on first message send.

**FR-MIG-004:** The system SHALL handle conversations with users who haven't enabled E2EE.

**FR-MIG-005:** The system SHALL not send encrypted messages to users without E2EE enabled.

**FR-MIG-006:** The system SHALL allow disabling E2EE with clear warnings (optional, not recommended).

---

## 4. External Interface Requirements

### 4.1 User Interface Requirements

**UIR-001:** Encryption status indicator in chat header
```
┌─────────────────────────────────────┐
│ 🔒 Alice (Encrypted)          [⋮]  │  ← Lock icon + status
└─────────────────────────────────────┘
```

**UIR-002:** Security information screen
```
┌─────────────────────────────────────┐
│         Security Information        │
│                                     │
│  Encryption Status:  ✅ Active      │
│                                     │
│  Safety Number:                     │
│  12345 67890 12345 67890 12345     │
│  67890 12345 67890 12345 67890     │
│  12345 67890                        │
│                                     │
│  [QR Code]                          │
│                                     │
│  Last Verified: Never               │
│  [Mark as Verified]                 │
│                                     │
│  Identity Key Changed: No           │
└─────────────────────────────────────┘
```

**UIR-003:** Encryption initialization banner
```
┌─────────────────────────────────────┐
│  🔐 Securing conversation...        │
└─────────────────────────────────────┘
```

**UIR-004:** Warning for identity key change
```
┌─────────────────────────────────────┐
│  ⚠️ Alice's security code changed.  │
│  Tap to verify.                     │
└─────────────────────────────────────┘
```

### 4.2 API Requirements

#### 4.2.1 Prekey Bundle Endpoints

**API-001: Upload Prekey Bundle**
```
POST /api/crypto/prekeys
Authorization: Bearer {userId}

Request:
{
  "identityKey": "base64_encoded_public_key",
  "signedPrekey": {
    "keyId": 1,
    "publicKey": "base64_encoded_public_key",
    "signature": "base64_encoded_signature"
  },
  "oneTimePrekeys": [
    {
      "keyId": 1,
      "publicKey": "base64_encoded_public_key"
    },
    // ... up to 100 prekeys
  ]
}

Response: 201 Created
{
  "success": true,
  "prekeyCount": 100
}
```

**API-002: Fetch Prekey Bundle**
```
GET /api/crypto/prekeys/{userId}
Authorization: Bearer {requesterId}

Response: 200 OK
{
  "identityKey": "base64_encoded_public_key",
  "signedPrekey": {
    "keyId": 1,
    "publicKey": "base64_encoded_public_key",
    "signature": "base64_encoded_signature"
  },
  "oneTimePrekey": {
    "keyId": 42,
    "publicKey": "base64_encoded_public_key"
  }
}
```

**API-003: Get Prekey Count**
```
GET /api/crypto/prekeys/count
Authorization: Bearer {userId}

Response: 200 OK
{
  "oneTimePrekeyCount": 87,
  "signedPrekeyAge": 172800000  // milliseconds
}
```

#### 4.2.2 Encrypted Message Endpoints

**API-004: Send Encrypted Message**
```
POST /api/messages/encrypted
Authorization: Bearer {userId}

Request:
{
  "to": "recipient_user_id",
  "encryptedMessage": {
    "header": {
      "ratchetKey": "base64_encoded_public_key",
      "previousChainLength": 5,
      "messageNumber": 3,
      "identityKey": "base64_encoded_sender_identity_key"  // for initial message
    },
    "ciphertext": "base64_encoded_encrypted_content",
    "authTag": "base64_encoded_auth_tag"
  },
  "type": "text" | "image",
  "usedPrekeyId": 42  // only for initial message
}

Response: 201 Created
{
  "messageId": "uuid",
  "timestamp": 1699564800000,
  "status": "sent"
}
```

### 4.3 Hardware Interface Requirements

**HIR-001:** The system SHALL utilize hardware-accelerated cryptography when available via Web Crypto API.

**HIR-002:** The system SHOULD use Secure Enclave on supported iOS devices for key storage (future enhancement).

### 4.4 Software Interface Requirements

**SIR-001:** Web Crypto API for cryptographic operations
- Algorithm: ECDH with Curve25519 (X25519)
- Algorithm: AES-GCM-256 for symmetric encryption
- Algorithm: HKDF for key derivation
- Algorithm: ECDSA with Ed25519 for signatures

**SIR-002:** IndexedDB for persistent key storage
- Database: "E2EEKeyStorage"
- Object Stores: "identityKeys", "sessionStates", "prekeyBundles"

**SIR-003:** WebSocket for encrypted message transport
- Protocol: WSS (WebSocket Secure)
- Message format: JSON with base64-encoded binary data

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

**NFR-PERF-001:** Message encryption SHALL complete within 100ms on standard hardware (2GHz CPU).

**NFR-PERF-002:** Message decryption SHALL complete within 150ms on standard hardware.

**NFR-PERF-003:** Key generation during registration SHALL complete within 5 seconds.

**NFR-PERF-004:** Prekey bundle upload SHALL complete within 2 seconds on typical network.

**NFR-PERF-005:** The system SHALL support encryption throughput of at least 10 messages per second.

**NFR-PERF-006:** IndexedDB operations SHALL complete within 50ms for 99% of operations.

**NFR-PERF-007:** The system SHALL handle 10,000 stored session states without performance degradation.

### 5.2 Safety Requirements

**NFR-SAFE-001:** The system SHALL never expose private keys in logs, console, or error messages.

**NFR-SAFE-002:** The system SHALL clear sensitive data from memory after use (where possible in JavaScript).

**NFR-SAFE-003:** The system SHALL fail secure: encryption failures prevent message sending, not fallback to plaintext.

**NFR-SAFE-004:** The system SHALL validate all cryptographic inputs before processing.

**NFR-SAFE-005:** The system SHALL limit resource consumption to prevent DoS attacks (max skipped keys, max sessions).

### 5.3 Security Requirements

*(See detailed Security Requirements section below)*

### 5.4 Software Quality Attributes

#### 5.4.1 Reliability

**NFR-REL-001:** The system SHALL maintain 99.9% successful encryption rate under normal conditions.

**NFR-REL-002:** The system SHALL recover from transient failures (network errors, etc.) without data loss.

**NFR-REL-003:** The system SHALL handle browser crashes gracefully with persistent key storage.

#### 5.4.2 Availability

**NFR-AVAIL-001:** E2EE functionality SHALL be available whenever the application is running.

**NFR-AVAIL-002:** Offline key generation SHALL be supported (keys uploaded when connectivity restored).

#### 5.4.3 Maintainability

**NFR-MAIN-001:** Cryptographic code SHALL be modular and separated from business logic.

**NFR-MAIN-002:** The system SHALL support algorithm migration (e.g., Curve25519 → post-quantum).

**NFR-MAIN-003:** Code SHALL be thoroughly documented with security considerations.

#### 5.4.4 Portability

**NFR-PORT-001:** The system SHALL work across all browsers supporting Web Crypto API.

**NFR-PORT-002:** The system SHALL not depend on browser-specific features.

#### 5.4.5 Usability

**NFR-USE-001:** E2EE SHALL be transparent to users (automatic encryption/decryption).

**NFR-USE-002:** Advanced security features (verification) SHALL be accessible but not mandatory.

**NFR-USE-003:** Error messages SHALL be user-friendly while being informative for debugging.

---

## 6. Security Requirements

### 6.1 Confidentiality

**SEC-CONF-001:** The server SHALL NOT have access to message plaintext at any time.

**SEC-CONF-002:** Only the intended recipient SHALL be able to decrypt messages.

**SEC-CONF-003:** Private keys SHALL NEVER be transmitted over the network.

**SEC-CONF-004:** Session keys SHALL be ephemeral and destroyed after use.

**SEC-CONF-005:** Database administrators SHALL NOT be able to read encrypted messages.

### 6.2 Integrity

**SEC-INT-001:** The system SHALL detect any tampering with encrypted messages.

**SEC-INT-002:** The system SHALL verify message authenticity using AEAD or HMAC.

**SEC-INT-003:** The system SHALL reject messages that fail integrity checks.

**SEC-INT-004:** Public key signatures SHALL be verified before use.

### 6.3 Authentication

**SEC-AUTH-001:** The system SHALL authenticate message senders using identity keys.

**SEC-AUTH-002:** The system SHALL verify signed prekeys using identity key signatures.

**SEC-AUTH-003:** The system SHALL prevent impersonation attacks through key verification.

### 6.4 Forward Secrecy

**SEC-FS-001:** Compromise of current keys SHALL NOT compromise past messages.

**SEC-FS-002:** Message keys SHALL be deleted immediately after encryption/decryption.

**SEC-FS-003:** The system SHALL use ephemeral keys in the Double Ratchet.

### 6.5 Backward Secrecy (Future Secrecy)

**SEC-BS-001:** Compromise of current keys SHALL NOT compromise future messages.

**SEC-BS-002:** The system SHALL perform DH ratchet to establish new ephemeral keys.

### 6.6 Replay Attack Prevention

**SEC-REP-001:** The system SHALL detect and reject replayed messages.

**SEC-REP-002:** The system SHALL use message numbers to enforce ordering.

**SEC-REP-003:** The system SHALL limit acceptance window for out-of-order messages.

### 6.7 Man-in-the-Middle (MITM) Prevention

**SEC-MITM-001:** The system SHALL provide safety numbers for out-of-band verification.

**SEC-MITM-002:** The system SHALL warn users of identity key changes.

**SEC-MITM-003:** The system SHALL use signed prekeys to prevent key substitution.

### 6.8 Denial of Service (DoS) Prevention

**SEC-DOS-001:** The system SHALL limit skipped message keys to 1000 per session.

**SEC-DOS-002:** The system SHALL limit total sessions to 10,000 per user.

**SEC-DOS-003:** The system SHALL rate-limit prekey generation requests.

**SEC-DOS-004:** The system SHALL validate message size before decryption.

---

## 7. Cryptographic Specifications

### 7.1 Cryptographic Algorithms

| Purpose | Algorithm | Key Size | Notes |
|---------|-----------|----------|-------|
| **Identity Keys** | Curve25519 (X25519) | 256-bit | Long-term key pair |
| **Ephemeral Keys** | Curve25519 (X25519) | 256-bit | Session-specific |
| **Symmetric Encryption** | AES-256-GCM | 256-bit | AEAD mode |
| **Key Derivation** | HKDF-SHA-256 | - | Based on HMAC-SHA-256 |
| **Signature** | Ed25519 | 256-bit | For signed prekeys |
| **Hash Function** | SHA-256 | - | For fingerprints |

### 7.2 Key Derivation Functions

#### 7.2.1 Root Key Derivation
```
Input: Root Key (RK), Diffie-Hellman Output (DHO)
Output: New Root Key (RK'), Chain Key (CK)

(RK', CK) = HKDF(RK, DHO, "WhatsAppCloneRootKey", 64)
```

#### 7.2.2 Chain Key Derivation
```
Input: Chain Key (CK)
Output: New Chain Key (CK'), Message Key (MK)

CK' = HMAC-SHA256(CK, 0x01)
MK  = HMAC-SHA256(CK, 0x02)
```

#### 7.2.3 Message Key Derivation
```
Input: Message Key (MK)
Output: Encryption Key (EK), Authentication Key (AK), IV

Output = HKDF(MK, NULL, "WhatsAppCloneMessageKey", 80)
EK = Output[0:32]   // 256 bits
AK = Output[32:64]  // 256 bits
IV = Output[64:80]  // 128 bits
```

### 7.3 X3DH Key Agreement

```
Given:
- Alice's Identity Key: IKa (private), IKa_pub (public)
- Alice's Ephemeral Key: EKa (private), EKa_pub (public)
- Bob's Identity Key: IKb (private), IKb_pub (public)
- Bob's Signed Prekey: SPKb (private), SPKb_pub (public)
- Bob's One-Time Prekey: OPKb (private), OPKb_pub (public)

Alice computes:
DH1 = ECDH(IKa, SPKb_pub)
DH2 = ECDH(EKa, IKb_pub)
DH3 = ECDH(EKa, SPKb_pub)
DH4 = ECDH(EKa, OPKb_pub)  // if OPK available

SK = HKDF(0xFF * 32, DH1 || DH2 || DH3 || DH4, "WhatsAppCloneX3DH", 32)

Bob computes the same SK using his private keys and Alice's public keys.
```

### 7.4 Double Ratchet Algorithm

#### 7.4.1 Ratchet State
```typescript
interface RatchetState {
  // Root key
  rootKey: Uint8Array;  // 32 bytes

  // Chain keys
  sendingChainKey: Uint8Array | null;  // 32 bytes
  receivingChainKey: Uint8Array | null;  // 32 bytes

  // DH ratchet keys
  dhRatchetKeyPair: {
    publicKey: Uint8Array;   // 32 bytes
    privateKey: Uint8Array;  // 32 bytes
  };
  dhRatchetRemoteKey: Uint8Array | null;  // 32 bytes

  // Message counters
  sendingChainLength: number;
  receivingChainLength: number;
  previousSendingChainLength: number;

  // Skipped message keys
  skippedMessageKeys: Map<string, Uint8Array>;  // key: "ratchetKey:msgNum"
}
```

#### 7.4.2 Sending Messages
```
1. If sending chain doesn't exist, perform DH ratchet
2. Derive message key: MK = KDF(sendingChainKey)
3. Update chain key: sendingChainKey = KDF(sendingChainKey)
4. Increment sendingChainLength
5. Encrypt message with MK
6. Delete MK from memory
```

#### 7.4.3 Receiving Messages
```
1. If message ratchet key differs from current, perform DH ratchet
2. If message number > receivingChainLength, skip message keys
3. Derive message key: MK = KDF(receivingChainKey) or retrieve from skipped keys
4. Verify and decrypt message with MK
5. Update chain key and counter
6. Delete MK from memory
```

### 7.5 Safety Number Generation

```
Input:
- Local Identity Public Key (32 bytes)
- Remote Identity Public Key (32 bytes)
- Local User ID
- Remote User ID

Process:
1. Concatenate: localId || localIdentityKey || remoteId || remoteIdentityKey
2. Hash: digest = SHA-256(concatenated)
3. Iterate 5200 times: digest = SHA-256(digest || concatenated)
4. Convert digest to 60-digit decimal number

Output: 60-digit safety number
Format: 12345 67890 12345 67890 12345 67890 12345 67890 12345 67890 12345 67890
```

---

## 8. Data Requirements

### 8.1 Database Schema Changes

#### 8.1.1 User Keys Table
```sql
CREATE TABLE IF NOT EXISTS user_keys (
  user_id TEXT PRIMARY KEY,
  identity_key_public TEXT NOT NULL,  -- Base64 encoded
  signed_prekey_id INTEGER NOT NULL,
  signed_prekey_public TEXT NOT NULL,  -- Base64 encoded
  signed_prekey_signature TEXT NOT NULL,  -- Base64 encoded
  signed_prekey_timestamp INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_keys_user ON user_keys(user_id);
```

#### 8.1.2 One-Time Prekeys Table
```sql
CREATE TABLE IF NOT EXISTS one_time_prekeys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key_id INTEGER NOT NULL,
  public_key TEXT NOT NULL,  -- Base64 encoded
  used INTEGER DEFAULT 0,  -- 0 = unused, 1 = used
  created_at INTEGER NOT NULL,
  used_at INTEGER,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_otp_user ON one_time_prekeys(user_id);
CREATE INDEX idx_otp_unused ON one_time_prekeys(user_id, used) WHERE used = 0;
```

#### 8.1.3 Messages Table Updates
```sql
ALTER TABLE messages ADD COLUMN encrypted INTEGER DEFAULT 0;  -- 0 = plaintext, 1 = encrypted
ALTER TABLE messages ADD COLUMN encryption_header TEXT;  -- JSON: ratchet key, counters, etc.
ALTER TABLE messages ADD COLUMN sender_identity_key TEXT;  -- For verification
```

### 8.2 IndexedDB Schema

#### 8.2.1 Database Structure
```javascript
const dbName = "E2EEKeyStorage";
const version = 1;

// Object Stores:
1. "identityKeys"
   - keyPath: "userId"
   - Stores: { userId, publicKey, privateKey, fingerprint }

2. "sessionStates"
   - keyPath: "sessionId"  (e.g., "user1-user2")
   - Stores: RatchetState object
   - Index: "participantId" for queries

3. "prekeyBundles"
   - keyPath: "userId"
   - Stores: { userId, identityKey, signedPrekey, oneTimePrekeys }

4. "skippedMessageKeys"
   - keyPath: ["sessionId", "ratchetKey", "messageNumber"]
   - Stores: { sessionId, ratchetKey, messageNumber, messageKey, timestamp }
   - Index: "timestamp" for cleanup

5. "verifiedIdentities"
   - keyPath: "userId"
   - Stores: { userId, identityKey, verifiedAt, verifiedBy }
```

### 8.3 Message Format

#### 8.3.1 Encrypted Message Structure
```typescript
interface EncryptedMessage {
  header: {
    // DH Ratchet public key (sender's current ratchet key)
    ratchetKey: string;  // Base64

    // Previous sending chain length (for DH ratchet)
    previousChainLength: number;

    // Current message number in chain
    messageNumber: number;

    // Sender's identity key (included in initial message only)
    identityKey?: string;  // Base64

    // Used one-time prekey ID (initial message only)
    usedPrekeyId?: number;
  };

  // Encrypted content (AES-GCM output)
  ciphertext: string;  // Base64

  // Authentication tag (from AES-GCM)
  authTag: string;  // Base64

  // Message type
  type: 'text' | 'image';
}
```

---

## 9. System Constraints

### 9.1 Technical Constraints

**CONS-TECH-001:** Must use Web Crypto API (no native code or WebAssembly for crypto).

**CONS-TECH-002:** Limited to 5MB IndexedDB quota in some browsers (requires quota management).

**CONS-TECH-003:** JavaScript has no secure memory wiping (best-effort clearing only).

**CONS-TECH-004:** Browser limitations on concurrent crypto operations.

**CONS-TECH-005:** No access to hardware security modules (HSM) from browser.

### 9.2 Regulatory Constraints

**CONS-REG-001:** Must comply with export control regulations for cryptography.

**CONS-REG-002:** Must comply with GDPR for EU users (right to erasure of keys).

**CONS-REG-003:** Must comply with local data protection laws.

**CONS-REG-004:** May be restricted in some jurisdictions with encryption bans.

### 9.3 Operational Constraints

**CONS-OPS-001:** End users cannot recover messages if keys are lost (by design).

**CONS-OPS-002:** Server administrators cannot assist with message recovery.

**CONS-OPS-003:** Cross-device synchronization requires additional implementation.

**CONS-OPS-004:** No centralized key escrow or recovery mechanism.

---

## 10. Technical Architecture

### 10.1 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Presentation Layer                     │  │
│  │  - React Components                                       │  │
│  │  - Encryption Status Indicators                           │  │
│  │  - Security Settings UI                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Application Layer                       │  │
│  │  - Message Handling                                       │  │
│  │  - User Interaction Logic                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Cryptography Layer                       │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │  │
│  │  │ Key Manager    │  │ Ratchet Engine │  │ Crypto     │ │  │
│  │  │ - Generate     │  │ - Double       │  │ Primitives │ │  │
│  │  │ - Store        │  │   Ratchet      │  │ - AES-GCM  │ │  │
│  │  │ - Rotate       │  │ - X3DH         │  │ - ECDH     │ │  │
│  │  │ - Verify       │  │ - Chain KDF    │  │ - HKDF     │ │  │
│  │  └────────────────┘  └────────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Storage Layer                          │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │               IndexedDB                            │  │  │
│  │  │  - Identity Keys     - Session States             │  │  │
│  │  │  - Prekey Bundles    - Skipped Message Keys       │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Communication Layer                      │  │
│  │  - WebSocket Client                                       │  │
│  │  - REST API Client                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      Server (Cloudflare Worker)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  API Endpoints                            │  │
│  │  - Prekey Management                                      │  │
│  │  - Message Routing (encrypted)                            │  │
│  │  - User Key Distribution                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Database (Cloudflare D1)                     │  │
│  │  - Encrypted Messages                                     │  │
│  │  - Public Keys & Prekeys                                  │  │
│  │  - User Metadata                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Class Diagram (Key Components)

```typescript
// Key Manager
class KeyManager {
  generateIdentityKeyPair(): Promise<IdentityKeyPair>
  generateSignedPrekey(identityPrivateKey): Promise<SignedPrekey>
  generateOneTimePrekeys(count): Promise<OneTimePrekey[]>
  storeIdentityKeys(keys): Promise<void>
  loadIdentityKeys(userId): Promise<IdentityKeyPair>
  publishPrekeyBundle(bundle): Promise<void>
  fetchPrekeyBundle(userId): Promise<PrekeyBundle>
  rotatePrekeys(): Promise<void>
  calculateFingerprint(identityKey): string
}

// Ratchet Engine
class RatchetEngine {
  initializeSession(prekeyBundle): Promise<RatchetState>
  performX3DH(bundle): Promise<SharedSecret>
  initializeDoubleRatchet(sharedSecret): RatchetState
  encryptMessage(state, plaintext): Promise<EncryptedMessage>
  decryptMessage(state, encrypted): Promise<string>
  performDHRatchet(state, remoteRatchetKey): void
  skipMessageKeys(state, until): void
  advanceSendingChain(state): Uint8Array
  advanceReceivingChain(state): Uint8Array
}

// Crypto Primitives
class CryptoPrimitives {
  generateKeyPair(): Promise<CryptoKeyPair>
  ecdh(privateKey, publicKey): Promise<Uint8Array>
  hkdf(input, salt, info, length): Promise<Uint8Array>
  aesGcmEncrypt(key, iv, plaintext): Promise<{ciphertext, authTag}>
  aesGcmDecrypt(key, iv, ciphertext, authTag): Promise<Uint8Array>
  sign(privateKey, message): Promise<Uint8Array>
  verify(publicKey, message, signature): Promise<boolean>
  sha256(data): Promise<Uint8Array>
}

// Session Manager
class SessionManager {
  createSession(userId, remotePrekeyBundle): Promise<Session>
  getSession(userId): Promise<Session | null>
  updateSession(userId, state): Promise<void>
  deleteSession(userId): Promise<void>
  listSessions(): Promise<string[]>
}

// Storage Manager
class StorageManager {
  saveIdentityKeys(keys): Promise<void>
  loadIdentityKeys(userId): Promise<IdentityKeyPair>
  saveSessionState(sessionId, state): Promise<void>
  loadSessionState(sessionId): Promise<RatchetState>
  saveSkippedMessageKey(sessionId, ratchetKey, msgNum, key): Promise<void>
  loadSkippedMessageKey(sessionId, ratchetKey, msgNum): Promise<Uint8Array>
  cleanupOldSkippedKeys(): Promise<void>
}
```

### 10.3 Sequence Diagrams

#### 10.3.1 First Message (Session Establishment)

```
Alice                  KeyManager        RatchetEngine      Server              Bob
  │                        │                  │               │                  │
  │ Click Send             │                  │               │                  │
  │───────────────────────▶│                  │               │                  │
  │                        │                  │               │                  │
  │                        │ Fetch Bob's      │               │                  │
  │                        │ Prekey Bundle    │               │                  │
  │                        │──────────────────┼──────────────▶│                  │
  │                        │                  │               │                  │
  │                        │◀─────────────────┼───────────────│                  │
  │                        │ {IKb, SPKb, OPKb}│               │                  │
  │                        │                  │               │                  │
  │                        │ Perform X3DH     │               │                  │
  │                        │─────────────────▶│               │                  │
  │                        │                  │               │                  │
  │                        │ Initialize Ratchet│              │                  │
  │                        │◀─────────────────│               │                  │
  │                        │                  │               │                  │
  │ Encrypt "Hello"        │                  │               │                  │
  │───────────────────────▶│                  │               │                  │
  │                        │ Encrypt          │               │                  │
  │                        │─────────────────▶│               │                  │
  │                        │ {header, CT}     │               │                  │
  │                        │◀─────────────────│               │                  │
  │                        │                  │               │                  │
  │                        │ Send Encrypted   │               │                  │
  │                        │ Message          │               │                  │
  │                        │──────────────────┼──────────────▶│                  │
  │                        │                  │               │ Route Message    │
  │                        │                  │               │─────────────────▶│
  │                        │                  │               │                  │
  │                        │                  │               │                  │ Receive
  │                        │                  │               │                  │ Message
  │                        │                  │               │                  │────┐
  │                        │                  │               │                  │    │
  │                        │                  │               │                  │◀───┘
  │                        │                  │               │                  │
  │                        │                  │               │                  │ Perform
  │                        │                  │               │                  │ X3DH
  │                        │                  │               │                  │────┐
  │                        │                  │               │                  │    │
  │                        │                  │               │                  │◀───┘
  │                        │                  │               │                  │
  │                        │                  │               │                  │ Decrypt
  │                        │                  │               │                  │────┐
  │                        │                  │               │                  │    │
  │                        │                  │               │                  │◀───┘
  │                        │                  │               │                  │
  │                        │                  │               │                  │ Display
  │                        │                  │               │                  │ "Hello"
```

---

## 11. Implementation Plan

### 11.1 Phase 1: Foundation (Week 1-2)

**Tasks:**
1. Set up cryptographic infrastructure
   - Implement CryptoPrimitives class using Web Crypto API
   - Create utility functions for key encoding/decoding
   - Implement HKDF key derivation

2. Implement KeyManager
   - Generate identity key pairs
   - Generate signed prekeys
   - Generate one-time prekeys
   - Key storage in IndexedDB

3. Database schema updates
   - Create user_keys table
   - Create one_time_prekeys table
   - Update messages table

4. API endpoints for prekey management
   - POST /api/crypto/prekeys (upload bundle)
   - GET /api/crypto/prekeys/:userId (fetch bundle)
   - GET /api/crypto/prekeys/count

**Deliverables:**
- Working key generation
- Prekey bundle upload/fetch
- Basic IndexedDB storage

### 11.2 Phase 2: Session Establishment (Week 3-4)

**Tasks:**
1. Implement X3DH protocol
   - DH operations with prekeys
   - Shared secret derivation
   - Initial message construction

2. Implement Double Ratchet initialization
   - Root key derivation
   - Initial chain key setup
   - Session state structure

3. Session management
   - Store/load session states
   - Session initialization flow

**Deliverables:**
- Working X3DH key exchange
- Session state management
- Initial encrypted message send

### 11.3 Phase 3: Message Encryption/Decryption (Week 5-6)

**Tasks:**
1. Implement message encryption
   - Chain key advancement
   - Message key derivation
   - AES-GCM encryption
   - Header construction

2. Implement message decryption
   - DH ratchet detection
   - Key skipping for out-of-order
   - AES-GCM decryption
   - Verification

3. Integrate with message sending flow
   - Detect encryption capability
   - Encrypt before send
   - Handle encrypted message reception

**Deliverables:**
- End-to-end encrypted messaging
- Proper ratcheting on both sides
- Out-of-order message handling

### 11.4 Phase 4: Security Features (Week 7-8)

**Tasks:**
1. Identity verification
   - Fingerprint generation
   - QR code for verification
   - Verification UI

2. Key rotation
   - Prekey replenishment
   - Signed prekey rotation
   - Automated rotation scheduler

3. Security indicators
   - Encryption status in UI
   - Lock icons
   - Security info screen

**Deliverables:**
- Safety number verification
- Key rotation system
- Complete security UI

### 11.5 Phase 5: Testing & Optimization (Week 9-10)

**Tasks:**
1. Unit testing
   - Crypto primitives tests
   - Ratchet algorithm tests
   - Key derivation tests

2. Integration testing
   - Full message flow tests
   - Multi-user scenarios
   - Error handling tests

3. Performance optimization
   - Crypto operation batching
   - IndexedDB query optimization
   - Memory cleanup

4. Security audit
   - Code review
   - Penetration testing
   - Compliance check

**Deliverables:**
- Comprehensive test suite
- Performance benchmarks
- Security audit report

### 11.6 Phase 6: Migration & Deployment (Week 11-12)

**Tasks:**
1. Migration strategy
   - Gradual rollout plan
   - Backward compatibility
   - User education materials

2. Documentation
   - User guide for E2EE
   - Developer documentation
   - Security white paper

3. Deployment
   - Feature flag rollout
   - Monitoring setup
   - Incident response plan

**Deliverables:**
- Production-ready E2EE
- Complete documentation
- Deployed to users

---

## 12. Testing Requirements

### 12.1 Unit Testing

**TEST-UNIT-001:** Test key generation for all key types (identity, signed prekey, one-time prekeys).

**TEST-UNIT-002:** Test X3DH with various prekey combinations (with/without one-time prekey).

**TEST-UNIT-003:** Test HKDF key derivation with known test vectors.

**TEST-UNIT-004:** Test AES-GCM encryption/decryption with various plaintext sizes.

**TEST-UNIT-005:** Test Double Ratchet state advancement.

**TEST-UNIT-006:** Test message key derivation and deletion.

**TEST-UNIT-007:** Test fingerprint generation with known identity keys.

**TEST-UNIT-008:** Test signature creation and verification.

### 12.2 Integration Testing

**TEST-INT-001:** Test complete session establishment between two users.

**TEST-INT-002:** Test message encryption and decryption end-to-end.

**TEST-INT-003:** Test out-of-order message delivery and key skipping.

**TEST-INT-004:** Test session resumption after page reload.

**TEST-INT-005:** Test prekey bundle fetch and usage.

**TEST-INT-006:** Test key rotation and prekey replenishment.

**TEST-INT-007:** Test multiple concurrent sessions.

**TEST-INT-008:** Test error recovery (network failures, corruption).

### 12.3 Security Testing

**TEST-SEC-001:** Verify server cannot decrypt messages.

**TEST-SEC-002:** Test forward secrecy (compromise past keys, verify old messages safe).

**TEST-SEC-003:** Test backward secrecy (compromise current keys, verify future messages safe).

**TEST-SEC-004:** Test replay attack detection.

**TEST-SEC-005:** Test message integrity verification.

**TEST-SEC-006:** Test MITM detection via fingerprint changes.

**TEST-SEC-007:** Verify private keys never leave client.

**TEST-SEC-008:** Test DoS protection (skipped key limits).

### 12.4 Performance Testing

**TEST-PERF-001:** Measure encryption time for 1KB, 10KB, 100KB messages.

**TEST-PERF-002:** Measure key generation time.

**TEST-PERF-003:** Measure session initialization time.

**TEST-PERF-004:** Measure IndexedDB operation latency.

**TEST-PERF-005:** Test throughput with 100 messages in quick succession.

**TEST-PERF-006:** Test memory usage with 10,000 sessions.

### 12.5 Compatibility Testing

**TEST-COMPAT-001:** Test on Chrome, Firefox, Safari, Edge.

**TEST-COMPAT-002:** Test on mobile browsers (iOS Safari, Chrome Mobile).

**TEST-COMPAT-003:** Test with different IndexedDB implementations.

**TEST-COMPAT-004:** Test cross-browser interoperability.

### 12.6 Usability Testing

**TEST-USE-001:** Verify encryption is transparent to users.

**TEST-USE-002:** Test security information accessibility.

**TEST-USE-003:** Test verification process usability.

**TEST-USE-004:** Measure user comprehension of security indicators.

---

## 13. Appendices

### 13.1 Glossary

See Section 1.3 for definitions.

### 13.2 References

1. **Signal Protocol Specifications**
   - https://signal.org/docs/specifications/doubleratchet/
   - https://signal.org/docs/specifications/x3dh/

2. **RFC 7748** - Elliptic Curves for Security
   - https://tools.ietf.org/html/rfc7748

3. **RFC 5869** - HKDF
   - https://tools.ietf.org/html/rfc5869

4. **Web Crypto API Specification**
   - https://www.w3.org/TR/WebCryptoAPI/

5. **NIST SP 800-56A** - Recommendation for Pair-Wise Key Establishment
   - https://csrc.nist.gov/publications/detail/sp/800-56a/rev-3/final

### 13.3 Acronyms

See Section 1.3 for full list.

### 13.4 Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Development Team | Initial SRS document |

---

**End of Software Requirements Specification**

**Document Status:** Draft
**Next Review Date:** TBD
**Approval Required From:** Security Team, Product Manager, Technical Lead

