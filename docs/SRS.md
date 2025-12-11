# Software Requirements Specification (SRS)
## WhatsApp Clone Application

**Version:** 1.0
**Date:** December 11, 2025
**Project Name:** WhatsApp Clone
**Document Status:** Draft

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Features](#3-system-features)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [System Requirements](#5-system-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Data Requirements](#7-data-requirements)
8. [Appendices](#8-appendices)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document provides a comprehensive description of the WhatsApp Clone application. It defines the functional and non-functional requirements for the real-time messaging platform built using Cloudflare Workers and React.

### 1.2 Scope

The WhatsApp Clone is a web-based real-time messaging application that enables users to:
- Create user accounts with usernames
- Send and receive instant messages
- See online/offline status of other users
- View typing indicators
- Track message delivery status
- Maintain persistent chat history

**In Scope:**
- User authentication (username-based)
- Real-time bidirectional messaging
- Online presence indicators
- Typing indicators
- Message persistence
- Message delivery status (sent/delivered/read)

**Out of Scope:**
- End-to-end encryption
- File/media sharing
- Voice/video calls
- Group chats
- User profile customization beyond username
- Password-based authentication
- Mobile native applications

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| SRS | Software Requirements Specification |
| UI | User Interface |
| API | Application Programming Interface |
| WebSocket | Full-duplex communication protocol over TCP |
| REST | Representational State Transfer |
| D1 | Cloudflare's SQLite database service |
| Durable Objects | Cloudflare's stateful serverless objects |
| HMR | Hot Module Replacement |
| CRUD | Create, Read, Update, Delete |

### 1.4 References

- Cloudflare Workers Documentation: https://developers.cloudflare.com/workers/
- Cloudflare Durable Objects: https://developers.cloudflare.com/durable-objects/
- Cloudflare D1 Database: https://developers.cloudflare.com/d1/
- React Documentation: https://react.dev/
- WebSocket Protocol (RFC 6455): https://tools.ietf.org/html/rfc6455

### 1.5 Overview

This document is organized into sections covering system description, functional requirements, external interfaces, system features, and non-functional requirements. It serves as the primary reference for developers, testers, and stakeholders.

---

## 2. Overall Description

### 2.1 Product Perspective

The WhatsApp Clone is a standalone web application consisting of:
- **Frontend**: Single-page React application
- **Backend**: Cloudflare Worker with Durable Objects
- **Database**: Cloudflare D1 (SQLite)
- **Real-time Communication**: WebSocket via Durable Objects

#### System Context Diagram

```
┌─────────────────┐
│   Web Browser   │
│    (Client)     │
└────────┬────────┘
         │ HTTP/WebSocket
         │
┌────────▼────────────────────────────┐
│    Cloudflare Global Network        │
│  ┌──────────────────────────────┐   │
│  │  Cloudflare Worker           │   │
│  │  - REST API                  │   │
│  │  - WebSocket Router          │   │
│  └────────┬─────────────────────┘   │
│           │                          │
│  ┌────────▼──────────┐               │
│  │ Durable Object    │               │
│  │  (ChatRoom)       │               │
│  │  - WebSocket Mgmt │               │
│  │  - Message Routing│               │
│  └────────┬──────────┘               │
│           │                          │
│  ┌────────▼──────────┐               │
│  │  Cloudflare D1    │               │
│  │  - Users Table    │               │
│  │  - Messages Table │               │
│  └───────────────────┘               │
└─────────────────────────────────────┘
```

### 2.2 Product Functions

The application provides the following major functions:

1. **User Management**
   - User registration with unique username
   - User authentication
   - User session management

2. **Real-time Messaging**
   - Send text messages
   - Receive messages instantly
   - Message delivery confirmation
   - Message persistence

3. **Presence Management**
   - Online/offline status tracking
   - Real-time presence updates
   - User availability indicators

4. **Typing Indicators**
   - Display when users are typing
   - Auto-hide after inactivity

5. **Chat Interface**
   - User list display
   - Chat window with message history
   - Message input and sending

### 2.3 User Characteristics

**Primary Users:**
- General public with basic web browsing skills
- Age: 13+ years
- Technical expertise: Basic to intermediate
- Device: Desktop/laptop with modern web browser

**Expected User Behavior:**
- Casual messaging with friends/colleagues
- Short to medium message length
- Frequent status checking
- Multi-tab/window usage for multiple conversations

### 2.4 Constraints

**Technical Constraints:**
- Must use Cloudflare Workers for backend
- Limited to Cloudflare D1 database capabilities
- WebSocket connections limited by Durable Objects
- Browser must support WebSocket API
- No persistent storage on client side

**Business Constraints:**
- Free tier Cloudflare account limitations
- No budget for third-party services
- Open-source project (MIT License)

**Regulatory Constraints:**
- Must comply with data privacy regulations
- No sensitive data storage without encryption
- User consent for data storage

### 2.5 Assumptions and Dependencies

**Assumptions:**
- Users have stable internet connection
- Users have modern web browsers (Chrome, Firefox, Safari, Edge)
- JavaScript is enabled in browser
- WebSocket protocol is supported
- Users understand basic chat application UX

**Dependencies:**
- Cloudflare Workers runtime
- Cloudflare Durable Objects
- Cloudflare D1 database service
- Node.js and npm for development
- Wrangler CLI for deployment
- Vite for frontend build

---

## 3. System Features

### 3.1 User Authentication

**Priority:** High
**Description:** Users can create accounts and authenticate using a unique username.

#### 3.1.1 Functional Requirements

**FR-AUTH-001:** The system shall allow users to enter a username to create an account.

**FR-AUTH-002:** The system shall validate that usernames are between 1-30 characters.

**FR-AUTH-003:** The system shall generate a unique user ID for each new user.

**FR-AUTH-004:** The system shall store user information in the database with ID, username, avatar (optional), and last seen timestamp.

**FR-AUTH-005:** The system shall maintain user session throughout the browser session.

**FR-AUTH-006:** The system shall allow users to logout and clear session data.

**FR-AUTH-007:** The system shall trim whitespace from usernames before validation.

#### 3.1.2 Use Case: User Login

**Actor:** End User
**Preconditions:** User has opened the application in web browser
**Main Flow:**
1. User navigates to application URL
2. System displays login screen with username input field
3. User enters desired username
4. User clicks "Continue" button
5. System validates username
6. System creates user record in database
7. System establishes WebSocket connection
8. System displays chat interface

**Alternative Flows:**
- 5a. Username is empty or invalid
  - System keeps "Continue" button disabled
  - User cannot proceed

**Postconditions:** User is authenticated and can access chat features

### 3.2 Real-time Messaging

**Priority:** High
**Description:** Users can send and receive text messages in real-time.

#### 3.2.1 Functional Requirements

**FR-MSG-001:** The system shall allow authenticated users to send text messages to other users.

**FR-MSG-002:** The system shall deliver messages to recipients in real-time if they are online.

**FR-MSG-003:** The system shall display sent messages immediately in sender's chat window.

**FR-MSG-004:** The system shall generate unique message IDs for each message.

**FR-MSG-005:** The system shall record message metadata: ID, sender, recipient, content, timestamp, status.

**FR-MSG-006:** The system shall support message status: sent, delivered, read.

**FR-MSG-007:** The system shall update message status when delivered to recipient.

**FR-MSG-008:** The system shall persist all messages to database.

**FR-MSG-009:** The system shall support messages up to reasonable length (no hard limit specified).

**FR-MSG-010:** The system shall display messages in chronological order.

**FR-MSG-011:** The system shall show message timestamp in 12-hour format.

**FR-MSG-012:** The system shall visually differentiate sent vs received messages.

**FR-MSG-013:** The system shall auto-scroll to latest message when new messages arrive.

#### 3.2.2 Use Case: Send Message

**Actor:** Authenticated User
**Preconditions:**
- User is logged in
- User has selected a recipient from user list
- WebSocket connection is active

**Main Flow:**
1. User types message in input field
2. User clicks "Send" button or presses Enter
3. System creates message object with metadata
4. System sends message via WebSocket to server
5. System displays message in chat window with "sent" status
6. Server receives message
7. Server identifies recipient session
8. Server delivers message to recipient
9. Server sends delivery confirmation to sender
10. System updates message status to "delivered"
11. System persists message to database

**Alternative Flows:**
- 3a. Message is empty (only whitespace)
  - System keeps send button disabled
  - Message is not sent
- 7a. Recipient is not online
  - Message remains in "sent" status
  - Message is still persisted for later retrieval

**Postconditions:**
- Message is delivered to recipient (if online)
- Message is persisted in database
- Both users see the message in their chat history

### 3.3 User Presence Management

**Priority:** High
**Description:** System tracks and displays online/offline status of users.

#### 3.3.1 Functional Requirements

**FR-PRES-001:** The system shall mark users as "online" when they establish WebSocket connection.

**FR-PRES-002:** The system shall mark users as "offline" when WebSocket connection closes.

**FR-PRES-003:** The system shall broadcast presence changes to all connected users.

**FR-PRES-004:** The system shall display online status with green "online" text.

**FR-PRES-005:** The system shall display offline status with gray "offline" text.

**FR-PRES-006:** The system shall show list of currently online users to newly connected users.

**FR-PRES-007:** The system shall update presence indicators in real-time.

**FR-PRES-008:** The system shall handle presence state on page refresh/reload.

### 3.4 Typing Indicators

**Priority:** Medium
**Description:** System shows when users are typing messages.

#### 3.4.1 Functional Requirements

**FR-TYPE-001:** The system shall detect when user is typing in message input field.

**FR-TYPE-002:** The system shall send typing notification to recipient user.

**FR-TYPE-003:** The system shall display "[Username] is typing..." indicator to recipient.

**FR-TYPE-004:** The system shall hide typing indicator after 1 second of inactivity.

**FR-TYPE-005:** The system shall hide typing indicator when message is sent.

**FR-TYPE-006:** The system shall only show typing indicator for currently selected chat.

### 3.5 Chat User Interface

**Priority:** High
**Description:** Graphical interface for viewing users and exchanging messages.

#### 3.5.1 Functional Requirements

**FR-UI-001:** The system shall display a sidebar with list of all users.

**FR-UI-002:** The system shall exclude current user from user list.

**FR-UI-003:** The system shall highlight selected user in user list.

**FR-UI-004:** The system shall display user avatars as initials in colored circles.

**FR-UI-005:** The system shall show main chat area with header, messages, and input.

**FR-UI-006:** The system shall display empty state when no user is selected.

**FR-UI-007:** The system shall show chat header with recipient name and status.

**FR-UI-008:** The system shall provide message input field with send button.

**FR-UI-009:** The system shall disable send button when message is empty.

**FR-UI-010:** The system shall disable send button when WebSocket is disconnected.

**FR-UI-011:** The system shall show connection status in input field placeholder.

**FR-UI-012:** The system shall provide logout button in sidebar header.

**FR-UI-013:** The system shall display current user's username in sidebar.

**FR-UI-014:** The system shall use dark theme color scheme.

**FR-UI-015:** The system shall be responsive to window resizing.

### 3.6 Message History Retrieval

**Priority:** Medium
**Description:** Users can view previous messages from database.

#### 3.6.1 Functional Requirements

**FR-HIST-001:** The system shall provide API endpoint to retrieve messages between two users.

**FR-HIST-002:** The system shall return messages in chronological order.

**FR-HIST-003:** The system shall filter messages to only show relevant conversation.

**FR-HIST-004:** The system shall load message history when user selects a chat.

**FR-HIST-005:** The system shall combine real-time and historical messages seamlessly.

---

## 4. External Interface Requirements

### 4.1 User Interfaces

#### 4.1.1 Login Screen

**Components:**
- Application title "WhatsApp Clone"
- Username input field
- "Continue" button
- Gradient purple background

**Behavior:**
- Button disabled when username is empty
- Button enabled when username has content
- Auto-focus on username input
- Form submission on Enter key

#### 4.1.2 Chat Interface

**Layout:**
```
┌─────────────────────────────────────────────┐
│ ┌─────────────┐ ┌─────────────────────────┐ │
│ │  Sidebar    │ │    Chat Window          │ │
│ │             │ │                         │ │
│ │  Header     │ │    Chat Header          │ │
│ │  User List  │ │    Messages Area        │ │
│ │             │ │    Message Input        │ │
│ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**Sidebar Components:**
- Header with "Chats" title
- Current username display
- Logout button
- Scrollable user list
- User items showing: avatar, name, status

**Chat Window Components:**
- Chat header with recipient info
- Messages container with auto-scroll
- Message bubbles (sent: right-aligned green, received: left-aligned gray)
- Typing indicator
- Message input field
- Send button

**Color Scheme:**
- Background: #111b21, #0b141a
- Card background: #202c33, #222e35
- Text: #e9edef
- Secondary text: #8696a0
- Sent messages: #005c4b
- Received messages: #202c33
- Online indicator: #25d366
- Send button: #25d366

#### 4.1.3 Accessibility

**Requirements:**
- Keyboard navigation support
- Enter key to send messages
- Tab navigation through interface
- Focus indicators on interactive elements

### 4.2 Hardware Interfaces

Not applicable. This is a web-based application with no direct hardware interfaces.

### 4.3 Software Interfaces

#### 4.3.1 Backend API Endpoints

**REST API:**

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/api/users` | GET | Get all users | None | Array of user objects |
| `/api/users` | POST | Create new user | `{username, avatar?}` | User object with ID |
| `/api/messages/:userId` | GET | Get messages | `?user=currentUserId` | Array of messages |
| `/api/messages` | POST | Save message | Message object | `{success: true}` |

**WebSocket Interface:**

| Message Type | Direction | Payload | Description |
|--------------|-----------|---------|-------------|
| `auth` | Client → Server | `{userId, username}` | Authenticate connection |
| `message` | Bidirectional | `{to, content}` or Message object | Send/receive message |
| `typing` | Bidirectional | `{to, typing}` or `{from, username, typing}` | Typing notification |
| `status` | Bidirectional | `{to, messageId, status}` | Message status update |
| `online` | Server → Client | `{userId, username, online}` or `{users: [...]}` | Presence update |
| `error` | Server → Client | `{message}` | Error notification |

#### 4.3.2 Database Schema

**Users Table:**
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  avatar TEXT,
  lastSeen INTEGER NOT NULL
);
```

**Messages Table:**
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);
```

#### 4.3.3 External Services

**Cloudflare Services:**
- Cloudflare Workers (Runtime)
- Cloudflare Durable Objects (WebSocket state)
- Cloudflare D1 (Database)
- Cloudflare Global Network (CDN)

### 4.4 Communication Interfaces

**Protocols:**
- HTTP/HTTPS for REST API
- WebSocket (WS/WSS) for real-time communication
- TCP/IP as transport layer

**Data Formats:**
- JSON for all API requests/responses
- JSON for WebSocket messages
- UTF-8 text encoding

**Security:**
- HTTPS in production
- WSS (WebSocket Secure) in production
- CORS headers configured
- Origin validation

---

## 5. System Requirements

### 5.1 Functional Requirements Summary

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | User authentication with username | High |
| FR-002 | Real-time message sending | High |
| FR-003 | Real-time message receiving | High |
| FR-004 | Message persistence | High |
| FR-005 | Online/offline status | High |
| FR-006 | User list display | High |
| FR-007 | Chat interface | High |
| FR-008 | Typing indicators | Medium |
| FR-009 | Message status tracking | Medium |
| FR-010 | Message history retrieval | Medium |
| FR-011 | Session management | High |
| FR-012 | WebSocket connection management | High |

### 5.2 Performance Requirements

**PR-001:** Message delivery latency shall not exceed 500ms under normal conditions.

**PR-002:** The system shall support at least 100 concurrent WebSocket connections per Durable Object.

**PR-003:** Database queries shall complete within 100ms for 95% of requests.

**PR-004:** The web application shall load initial page within 3 seconds on standard broadband connection.

**PR-005:** The system shall handle message throughput of at least 10 messages/second per user.

**PR-006:** UI interactions shall provide feedback within 100ms.

**PR-007:** WebSocket reconnection shall occur within 3 seconds of disconnection.

### 5.3 Safety Requirements

**SR-001:** The system shall not lose messages during WebSocket reconnection.

**SR-002:** The system shall gracefully handle database connection failures.

**SR-003:** The system shall prevent duplicate message delivery.

**SR-004:** The system shall sanitize user inputs to prevent XSS attacks.

**SR-005:** The system shall handle WebSocket errors without crashing.

### 5.4 Security Requirements

**SEC-001:** The system shall validate all user inputs on both client and server.

**SEC-002:** The system shall use HTTPS/WSS in production environment.

**SEC-003:** The system shall implement CORS headers to restrict origins.

**SEC-004:** The system shall not expose sensitive system information in error messages.

**SEC-005:** The system shall prevent SQL injection through parameterized queries.

**SEC-006:** The system shall rate-limit API requests to prevent abuse.

**SEC-007:** The system shall validate WebSocket message types and payloads.

### 5.5 Software Quality Attributes

#### 5.5.1 Reliability

- **Uptime:** 99% availability target
- **Error Rate:** < 1% of requests should fail
- **Data Integrity:** Zero data loss under normal operations
- **Fault Recovery:** Automatic reconnection on WebSocket failure

#### 5.5.2 Maintainability

- **Code Structure:** Modular component architecture
- **Documentation:** Inline comments, README, setup guides
- **Testing:** Unit tests for critical functions
- **Debugging:** Console logging for development mode
- **Version Control:** Git-based source control

#### 5.5.3 Portability

- **Browser Support:** Chrome, Firefox, Safari, Edge (latest 2 versions)
- **Device Support:** Desktop and laptop computers
- **Deployment:** Cloudflare global network
- **Environment:** Development and production configurations

#### 5.5.4 Usability

- **Learning Curve:** Users should understand interface within 5 minutes
- **Consistency:** UI follows familiar chat application patterns
- **Feedback:** Immediate visual feedback for all actions
- **Error Messages:** Clear, user-friendly error descriptions
- **Help:** Self-explanatory interface with minimal need for documentation

#### 5.5.5 Scalability

- **Horizontal Scaling:** Cloudflare Workers auto-scale globally
- **Database Scaling:** D1 supports up to 10GB per database
- **Connection Scaling:** Multiple Durable Objects for load distribution
- **Geographic Distribution:** Cloudflare edge network reduces latency

---

## 6. Non-Functional Requirements

### 6.1 Performance

**NFR-PERF-001:** The application shall load within 3 seconds on a 10 Mbps connection.

**NFR-PERF-002:** Message delivery shall occur within 500ms of sending.

**NFR-PERF-003:** UI shall render at minimum 30 FPS during interactions.

**NFR-PERF-004:** Database queries shall execute within 100ms for 95th percentile.

**NFR-PERF-005:** WebSocket messages shall be processed within 50ms.

### 6.2 Availability

**NFR-AVAIL-001:** The system shall maintain 99% uptime monthly.

**NFR-AVAIL-002:** Scheduled maintenance shall not exceed 1 hour per month.

**NFR-AVAIL-003:** The system shall automatically recover from transient failures.

**NFR-AVAIL-004:** WebSocket connections shall auto-reconnect on failure.

### 6.3 Compatibility

**NFR-COMPAT-001:** The application shall support Chrome 90+, Firefox 88+, Safari 14+, Edge 90+.

**NFR-COMPAT-002:** The application shall work on screen resolutions from 1024x768 to 4K.

**NFR-COMPAT-003:** The application shall support WebSocket protocol RFC 6455.

**NFR-COMPAT-004:** The application shall function with JavaScript enabled.

### 6.4 Usability

**NFR-USE-001:** Users shall be able to send a message within 3 clicks of login.

**NFR-USE-002:** The interface shall follow familiar chat application patterns.

**NFR-USE-003:** Error messages shall be displayed in plain language.

**NFR-USE-004:** The interface shall provide visual feedback for all user actions.

**NFR-USE-005:** Keyboard shortcuts shall be supported (Enter to send).

### 6.5 Maintainability

**NFR-MAINT-001:** Code shall follow TypeScript strict mode standards.

**NFR-MAINT-002:** Functions shall be documented with clear purpose comments.

**NFR-MAINT-003:** Components shall be modular and reusable.

**NFR-MAINT-004:** Configuration shall be externalized in separate files.

**NFR-MAINT-005:** Logs shall be available for debugging and monitoring.

### 6.6 Portability

**NFR-PORT-001:** The backend shall deploy to Cloudflare Workers without modification.

**NFR-PORT-002:** The frontend shall build with standard npm commands.

**NFR-PORT-003:** Development environment shall run on Windows, macOS, and Linux.

**NFR-PORT-004:** Database migrations shall be version-controlled.

---

## 7. Data Requirements

### 7.1 Data Models

#### 7.1.1 User Entity

```typescript
interface User {
  id: string;           // UUID
  username: string;     // 1-30 characters, unique
  avatar?: string;      // Optional avatar URL or initial
  lastSeen: number;     // Unix timestamp
  online?: boolean;     // Runtime state (not persisted)
}
```

#### 7.1.2 Message Entity

```typescript
interface Message {
  id: string;                              // UUID
  from: string;                            // User ID (sender)
  to: string;                              // User ID (recipient)
  content: string;                         // Message text
  timestamp: number;                       // Unix timestamp
  status: 'sent' | 'delivered' | 'read';  // Delivery status
}
```

#### 7.1.3 Chat Session Entity (Runtime Only)

```typescript
interface ChatSession {
  userId: string;      // User ID
  username: string;    // Username
  ws: WebSocket;       // WebSocket connection
}
```

### 7.2 Data Storage

**Database:** Cloudflare D1 (SQLite)

**Storage Locations:**
- **Production Data:** Cloudflare D1 remote database
- **Development Data:** Local D1 database (.wrangler/state/v3/d1)
- **Session Data:** Durable Objects memory (ephemeral)

**Data Retention:**
- **Users:** Indefinite (until manual deletion)
- **Messages:** Indefinite (until manual deletion)
- **Sessions:** Duration of WebSocket connection

### 7.3 Data Integrity

**DI-001:** User IDs shall be unique UUIDs.

**DI-002:** Usernames shall be unique within the system.

**DI-003:** Message IDs shall be unique UUIDs.

**DI-004:** Foreign key constraints shall maintain referential integrity.

**DI-005:** Timestamps shall be stored as Unix epoch milliseconds.

**DI-006:** All text shall be stored as UTF-8.

### 7.4 Data Backup and Recovery

**DB-001:** Database backups are managed by Cloudflare D1 service.

**DB-002:** Development database can be recreated from schema.sql.

**DB-003:** Data can be cleared using provided npm scripts.

**DB-004:** Database schema migrations are version-controlled.

---

## 8. Appendices

### 8.1 Technology Stack

**Frontend:**
- React 18.2.0
- TypeScript 5.3.3
- Vite 5.0.8
- Custom CSS (no framework)

**Backend:**
- Cloudflare Workers
- Cloudflare Durable Objects
- Cloudflare D1
- TypeScript 5.3.3

**Development Tools:**
- Wrangler CLI 3.22.1+
- Node.js 18+
- npm
- Concurrently (parallel processes)
- Git (version control)

### 8.2 Project Structure

```
whatsapp-clone/
├── src/
│   ├── worker/              # Backend
│   │   ├── index.ts         # Main worker
│   │   ├── ChatRoom.ts      # Durable Object
│   │   └── types.ts         # Type definitions
│   └── client/              # Frontend
│       ├── components/      # React components
│       ├── hooks/           # Custom hooks
│       ├── App.tsx          # Root component
│       ├── main.tsx         # Entry point
│       └── styles.css       # Styles
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── schema.sql              # Database schema
├── wrangler.toml           # Worker config
├── vite.config.ts          # Vite config
├── tsconfig.json           # TypeScript config
└── package.json            # Dependencies
```

### 8.3 Development Commands

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies |
| `npm run dev` | Start dev servers |
| `npm run dev:worker` | Start worker only |
| `npm run dev:client` | Start client only |
| `npm run build` | Build for production |
| `npm run deploy` | Deploy to Cloudflare |
| `npm run db:create` | Create D1 database |
| `npm run db:init` | Initialize schema (local) |
| `npm run db:init:remote` | Initialize schema (remote) |
| `npm run db:clear` | Clear all data (local) |
| `npm run db:clear:remote` | Clear all data (remote) |

### 8.4 Deployment Process

1. Build frontend: `npm run build:client`
2. Deploy worker: `npm run deploy`
3. Update environment variables if needed
4. Initialize remote database: `npm run db:init:remote`
5. Test deployed application
6. Monitor logs and performance

### 8.5 Known Limitations

**Current Limitations:**
1. No user authentication beyond username
2. No password protection
3. No end-to-end encryption
4. No file/media sharing
5. No group chats
6. No message editing or deletion
7. No message search functionality
8. No notification system
9. No read receipts (status tracking exists but not fully implemented)
10. Single Durable Object limits scalability
11. No message pagination (all messages loaded at once)
12. No rate limiting on message sending
13. No profanity filtering
14. No user blocking functionality
15. No emoji support beyond Unicode

### 8.6 Future Enhancements

**Potential Features:**
- Password-based authentication
- End-to-end encryption
- File and image sharing
- Group chat support
- Voice and video calls
- Message search
- Push notifications
- Read receipts
- Message editing/deletion
- User profiles with avatars
- Status messages
- Last seen timestamps
- Message reactions
- Chat archiving
- Multiple Durable Objects for scaling
- Message pagination
- Mobile app (React Native)
- Desktop app (Electron)

### 8.7 Glossary

**Chat Session:** Active WebSocket connection representing a logged-in user

**Delivery Status:** State of message transmission (sent, delivered, read)

**Durable Object:** Cloudflare's stateful serverless compute primitive

**Hot Module Replacement (HMR):** Live code updates without full page reload

**Presence:** Online/offline status of users

**Real-time:** Immediate data transmission without polling

**WebSocket:** Persistent bidirectional communication protocol

**Worker:** Serverless function running on Cloudflare's edge network

### 8.8 Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-11 | System | Initial SRS document creation |

### 8.9 Approval

This document requires approval from:

- [ ] Project Manager
- [ ] Lead Developer
- [ ] QA Lead
- [ ] Product Owner
- [ ] Technical Architect

---

**End of Software Requirements Specification**
