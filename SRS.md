# Software Requirements Specification (SRS)
## WhatsApp Clone - Real-time Chat Application

**Version:** 1.0
**Date:** December 11, 2025
**Prepared by:** Development Team

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Features and Requirements](#3-system-features-and-requirements)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Technical Requirements](#6-technical-requirements)
7. [Data Requirements](#7-data-requirements)
8. [Appendices](#8-appendices)

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) document describes the functional and non-functional requirements for the WhatsApp Clone application, a real-time messaging platform built with Cloudflare Workers and React.

### 1.2 Scope
The WhatsApp Clone is a web-based instant messaging application that enables users to:
- Register with a username
- Send and receive real-time text messages
- View online/offline status of other users
- See typing indicators
- Track message delivery status
- Maintain chat history

### 1.3 Definitions, Acronyms, and Abbreviations
- **SRS**: Software Requirements Specification
- **WebSocket**: A protocol providing full-duplex communication channels over a single TCP connection
- **D1**: Cloudflare's serverless SQL database
- **Durable Objects**: Cloudflare's stateful serverless compute primitives
- **UI**: User Interface
- **API**: Application Programming Interface
- **REST**: Representational State Transfer
- **UUID**: Universally Unique Identifier

### 1.4 References
- Cloudflare Workers Documentation
- WebSocket Protocol (RFC 6455)
- React Documentation
- TypeScript Documentation

### 1.5 Overview
This document is organized into sections covering system description, functional requirements, interface requirements, non-functional requirements, and technical specifications.

---

## 2. Overall Description

### 2.1 Product Perspective
The WhatsApp Clone is a standalone web application consisting of:
- **Frontend**: React-based single-page application (SPA)
- **Backend**: Cloudflare Workers with Durable Objects
- **Database**: Cloudflare D1 (SQLite)
- **Communication**: WebSocket for real-time messaging, REST API for data operations

### 2.2 Product Functions
The major functions of the system include:
1. User registration and authentication
2. Real-time one-to-one messaging
3. Online presence management
4. Typing indicators
5. Message delivery tracking
6. Message persistence and history
7. User discovery

### 2.3 User Classes and Characteristics

#### 2.3.1 End Users
- **Description**: Individuals using the chat application
- **Technical Expertise**: Basic web browsing skills
- **Privileges**: Send/receive messages, view user lists, manage own profile

### 2.4 Operating Environment
- **Client-side**: Modern web browsers (Chrome, Firefox, Safari, Edge)
- **Server-side**: Cloudflare's global edge network
- **Database**: Cloudflare D1
- **Protocols**: HTTPS, WSS (WebSocket Secure)

### 2.5 Design and Implementation Constraints
- Must use Cloudflare Workers for backend processing
- Must support WebSocket connections via Durable Objects
- Browser must support JavaScript ES2022
- Database operations limited to D1 capabilities
- Maximum message size: Defined by Cloudflare Worker request limits

### 2.6 Assumptions and Dependencies
- Users have stable internet connectivity
- Browsers support WebSocket protocol
- Cloudflare services remain operational
- Users access the application from supported browsers

---

## 3. System Features and Requirements

### 3.1 User Authentication

#### 3.1.1 Description
Users can register and log in using a unique username.

#### 3.1.2 Functional Requirements

**FR-AUTH-001**: Username Registration
- **Priority**: High
- **Description**: System shall allow users to create an account with a unique username
- **Input**: Username (string, 1-30 characters)
- **Processing**:
  - Validate username is not empty
  - Generate unique UUID for user
  - Store user in database
- **Output**: User object with ID, username, and timestamp

**FR-AUTH-002**: Username Uniqueness
- **Priority**: High
- **Description**: System shall enforce unique usernames
- **Input**: Username
- **Processing**: Check database for existing username
- **Output**: Success or error message

**FR-AUTH-003**: User Session
- **Priority**: High
- **Description**: System shall maintain user session in browser
- **Input**: User credentials
- **Processing**: Store user data in React state
- **Output**: Authenticated user session

**FR-AUTH-004**: Logout
- **Priority**: Medium
- **Description**: Users shall be able to log out
- **Input**: Logout action
- **Processing**: Clear user session and close WebSocket
- **Output**: Redirect to login screen

### 3.2 Real-time Messaging

#### 3.2.1 Description
Users can send and receive text messages in real-time through WebSocket connections.

#### 3.2.2 Functional Requirements

**FR-MSG-001**: Send Message
- **Priority**: High
- **Description**: Users shall be able to send text messages to other users
- **Input**: Message content (string), recipient ID
- **Processing**:
  - Generate unique message ID
  - Create message object with timestamp
  - Send via WebSocket to Durable Object
  - Deliver to recipient if online
- **Output**: Message confirmation with delivery status

**FR-MSG-002**: Receive Message
- **Priority**: High
- **Description**: Users shall receive messages in real-time when online
- **Input**: WebSocket message event
- **Processing**: Parse message, update UI
- **Output**: Display message in chat window

**FR-MSG-003**: Message Format
- **Priority**: High
- **Description**: Messages shall contain required fields
- **Fields**:
  - `id`: UUID
  - `from`: Sender user ID
  - `to`: Recipient user ID
  - `content`: Message text
  - `timestamp`: Unix timestamp
  - `status`: 'sent' | 'delivered' | 'read'

**FR-MSG-004**: Message Delivery Status
- **Priority**: Medium
- **Description**: System shall track message delivery status
- **States**:
  - **Sent**: Message sent from sender
  - **Delivered**: Message received by recipient's client
  - **Read**: Message viewed by recipient (future enhancement)

**FR-MSG-005**: Offline Message Handling
- **Priority**: Medium
- **Description**: Messages sent to offline users shall be marked as 'sent' only
- **Input**: Message to offline user
- **Processing**: Store in database, mark as 'sent'
- **Output**: Sender receives 'sent' status

### 3.3 User Presence

#### 3.3.1 Description
System tracks and displays online/offline status of users.

#### 3.3.2 Functional Requirements

**FR-PRES-001**: Online Status Detection
- **Priority**: High
- **Description**: System shall detect when users come online
- **Input**: WebSocket connection established
- **Processing**: Add user to active sessions
- **Output**: Broadcast online status to all users

**FR-PRES-002**: Offline Status Detection
- **Priority**: High
- **Description**: System shall detect when users go offline
- **Input**: WebSocket connection closed
- **Processing**: Remove user from active sessions
- **Output**: Broadcast offline status to all users

**FR-PRES-003**: Online User List
- **Priority**: High
- **Description**: Users shall see list of online users
- **Input**: User authentication
- **Processing**: Query active sessions
- **Output**: Display online users in sidebar

**FR-PRES-004**: Status Indicators
- **Priority**: Medium
- **Description**: UI shall display visual status indicators
- **Display**:
  - Green text for online users
  - Gray text for offline users

### 3.4 Typing Indicators

#### 3.4.1 Description
Users can see when others are typing a message.

#### 3.4.2 Functional Requirements

**FR-TYPE-001**: Typing Detection
- **Priority**: Low
- **Description**: System shall detect when user is typing
- **Input**: Keypress in message input
- **Processing**: Send typing event via WebSocket
- **Output**: Recipient sees typing indicator

**FR-TYPE-002**: Typing Indicator Display
- **Priority**: Low
- **Description**: Display typing indicator in chat window
- **Format**: "[Username] is typing..."
- **Duration**: Clear after 1 second of inactivity

**FR-TYPE-003**: Typing Status Transmission
- **Priority**: Low
- **Description**: Typing status shall be sent to specific recipient only
- **Input**: Typing event, recipient ID
- **Processing**: Send to recipient's WebSocket
- **Output**: Typing notification

### 3.5 User Discovery

#### 3.5.1 Description
Users can view and select other users to chat with.

#### 3.5.2 Functional Requirements

**FR-USER-001**: User List Retrieval
- **Priority**: High
- **Description**: System shall provide list of all registered users
- **Endpoint**: GET /api/users
- **Processing**: Query database for all users
- **Output**: Array of user objects

**FR-USER-002**: User List Display
- **Priority**: High
- **Description**: Display users in sidebar with avatars
- **Display**:
  - Username
  - Avatar (first letter of username)
  - Online/offline status

**FR-USER-003**: User Selection
- **Priority**: High
- **Description**: Users shall be able to select another user to chat
- **Input**: Click on user in sidebar
- **Processing**: Set selected user, load chat history
- **Output**: Display chat window for selected user

### 3.6 Message Persistence

#### 3.6.1 Description
Messages are stored in database for history and retrieval.

#### 3.6.2 Functional Requirements

**FR-PERSIST-001**: Message Storage
- **Priority**: Medium
- **Description**: All messages shall be stored in database
- **Endpoint**: POST /api/messages
- **Input**: Message object
- **Processing**: Insert into messages table
- **Output**: Success confirmation

**FR-PERSIST-002**: Message History Retrieval
- **Priority**: Medium
- **Description**: Users shall retrieve conversation history
- **Endpoint**: GET /api/messages/:userId
- **Input**: Current user ID, other user ID
- **Processing**: Query messages between two users
- **Output**: Ordered list of messages

**FR-PERSIST-003**: Message Ordering
- **Priority**: Medium
- **Description**: Messages shall be ordered by timestamp
- **Processing**: ORDER BY timestamp ASC
- **Output**: Chronologically ordered messages

---

## 4. External Interface Requirements

### 4.1 User Interfaces

#### 4.1.1 Login Screen
- **Components**:
  - Application title
  - Username input field
  - Continue button
- **Validation**: Disable button if username is empty
- **Design**: Centered card with gradient background

#### 4.1.2 Chat Interface
- **Layout**: Two-column layout
  - **Left Sidebar** (400px):
    - Header with current username
    - Logout button
    - Scrollable user list
  - **Right Panel** (Flexible):
    - Chat header with recipient info
    - Message list (scrollable)
    - Message input area

#### 4.1.3 User List Item
- **Components**:
  - Circular avatar with initial
  - Username
  - Online/offline status
- **Interaction**: Click to open chat

#### 4.1.4 Message Display
- **Sent Messages**:
  - Aligned right
  - Green background (#005c4b)
  - Delivery status icon
- **Received Messages**:
  - Aligned left
  - Dark gray background (#202c33)

#### 4.1.5 Message Input
- **Components**:
  - Text input field
  - Send button
- **Behavior**:
  - Enter key sends message
  - Disabled when disconnected

### 4.2 Hardware Interfaces
Not applicable - web-based application.

### 4.3 Software Interfaces

#### 4.3.1 Cloudflare D1 Database
- **Interface Type**: SQL Database
- **Purpose**: Store users and messages
- **Protocol**: SQL queries via Cloudflare Workers binding

#### 4.3.2 Cloudflare Durable Objects
- **Interface Type**: Stateful compute
- **Purpose**: Maintain WebSocket connections
- **Binding**: CHAT_ROOM

#### 4.3.3 Browser APIs
- **WebSocket API**: Real-time communication
- **Fetch API**: HTTP requests
- **LocalStorage**: Future session persistence

### 4.4 Communication Interfaces

#### 4.4.1 REST API Endpoints

**User Management**
- `GET /api/users` - Retrieve all users
- `POST /api/users` - Create new user

**Message Management**
- `GET /api/messages/:userId?user=:currentUserId` - Get conversation
- `POST /api/messages` - Save message

#### 4.4.2 WebSocket Protocol

**Connection**
- **URL**: `/ws`
- **Protocol**: WebSocket (wss:// in production)
- **Upgrade**: HTTP 101 Switching Protocols

**Message Types**

1. **Authentication**
```json
{
  "type": "auth",
  "payload": {
    "userId": "string",
    "username": "string"
  }
}
```

2. **Text Message**
```json
{
  "type": "message",
  "payload": {
    "to": "string",
    "content": "string"
  }
}
```

3. **Typing Indicator**
```json
{
  "type": "typing",
  "payload": {
    "to": "string",
    "typing": boolean
  }
}
```

4. **Online Status**
```json
{
  "type": "online",
  "payload": {
    "userId": "string",
    "username": "string",
    "online": boolean
  }
}
```

5. **Message Status Update**
```json
{
  "type": "status",
  "payload": {
    "to": "string",
    "messageId": "string",
    "status": "sent" | "delivered" | "read"
  }
}
```

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

**NFR-PERF-001**: Message Latency
- **Requirement**: Messages shall be delivered within 500ms under normal conditions
- **Measurement**: Time from send to receive
- **Conditions**: Both users online, normal network

**NFR-PERF-002**: WebSocket Connection
- **Requirement**: WebSocket connection shall establish within 2 seconds
- **Measurement**: Time to receive auth confirmation

**NFR-PERF-003**: User List Loading
- **Requirement**: User list shall load within 1 second
- **Measurement**: Time from login to user list display

**NFR-PERF-004**: Concurrent Users
- **Requirement**: System shall support minimum 100 concurrent users
- **Limitation**: Subject to Cloudflare Durable Object limits

### 5.2 Security Requirements

**NFR-SEC-001**: Transport Security
- **Requirement**: All communication shall use HTTPS/WSS in production
- **Implementation**: Cloudflare SSL/TLS

**NFR-SEC-002**: Data Validation
- **Requirement**: All user inputs shall be validated
- **Implementation**: Client and server-side validation

**NFR-SEC-003**: SQL Injection Prevention
- **Requirement**: All database queries shall use parameterized statements
- **Implementation**: D1 prepared statements with bindings

**NFR-SEC-004**: XSS Prevention
- **Requirement**: User-generated content shall be sanitized
- **Implementation**: React's built-in XSS protection

**NFR-SEC-005**: CORS Policy
- **Requirement**: API shall implement CORS headers
- **Current**: Allows all origins (development)
- **Production**: Should restrict to specific domains

### 5.3 Reliability Requirements

**NFR-REL-001**: WebSocket Reconnection
- **Requirement**: Client shall automatically reconnect on connection loss
- **Implementation**: 3-second retry interval

**NFR-REL-002**: Message Persistence
- **Requirement**: Messages shall be persisted before delivery confirmation
- **Implementation**: Database write before WebSocket send

**NFR-REL-003**: Error Handling
- **Requirement**: System shall handle errors gracefully
- **Implementation**: Try-catch blocks, error messages to users

**NFR-REL-004**: Session Recovery
- **Requirement**: Users shall maintain session on page refresh (future)
- **Current**: Session lost on refresh

### 5.4 Availability Requirements

**NFR-AVAIL-001**: Uptime
- **Requirement**: Service shall maintain 99.9% uptime
- **Dependency**: Cloudflare Workers availability

**NFR-AVAIL-002**: Global Availability
- **Requirement**: Service shall be accessible from Cloudflare edge locations
- **Implementation**: Cloudflare's global network

### 5.5 Maintainability Requirements

**NFR-MAINT-001**: Code Documentation
- **Requirement**: Code shall include TypeScript type definitions
- **Current**: Fully typed

**NFR-MAINT-002**: Modular Architecture
- **Requirement**: Frontend components shall be modular and reusable
- **Implementation**: React component architecture

**NFR-MAINT-003**: Database Migrations
- **Requirement**: Database schema changes shall be versioned
- **Implementation**: SQL migration files

### 5.6 Usability Requirements

**NFR-USE-001**: Responsive Design
- **Requirement**: Interface shall be usable on desktop browsers
- **Current**: Optimized for desktop (1600px max width)

**NFR-USE-002**: Visual Feedback
- **Requirement**: UI shall provide feedback for all user actions
- **Implementation**:
  - Message status indicators
  - Typing indicators
  - Connection status

**NFR-USE-003**: Error Messages
- **Requirement**: Error messages shall be user-friendly
- **Implementation**: Console logging (should add UI notifications)

**NFR-USE-004**: Loading States
- **Requirement**: UI shall indicate loading/processing states
- **Implementation**: Disabled buttons, connection status

### 5.7 Scalability Requirements

**NFR-SCALE-001**: Horizontal Scaling
- **Requirement**: Backend shall scale automatically with load
- **Implementation**: Cloudflare Workers auto-scaling

**NFR-SCALE-002**: Database Scaling
- **Requirement**: Database shall handle growing message volume
- **Current**: D1 database with indexes on messages table

**NFR-SCALE-003**: Message History
- **Requirement**: System shall handle conversations with 10,000+ messages
- **Future**: Implement pagination

---

## 6. Technical Requirements

### 6.1 Technology Stack

#### 6.1.1 Frontend
- **Framework**: React 18.2.0
- **Language**: TypeScript 5.3.3
- **Build Tool**: Vite 5.0.8
- **Styling**: CSS (custom, no framework)
- **Routing**: React Router DOM 6.20.0

#### 6.1.2 Backend
- **Runtime**: Cloudflare Workers
- **Language**: TypeScript (ES2022)
- **WebSocket**: Durable Objects
- **Database**: Cloudflare D1 (SQLite)

#### 6.1.3 Development Tools
- **Package Manager**: npm
- **CLI**: Wrangler 3.114.15+
- **Concurrency**: concurrently (dev server orchestration)

### 6.2 Browser Compatibility
- Chrome/Edge: Version 90+
- Firefox: Version 88+
- Safari: Version 14+

### 6.3 Development Environment
- **Node.js**: 18.x or higher
- **Operating Systems**: Windows, macOS, Linux
- **Required Tools**:
  - npm
  - Wrangler CLI
  - Modern code editor

### 6.4 Deployment Environment
- **Platform**: Cloudflare Workers
- **Edge Locations**: Global (Cloudflare's network)
- **Domain**: Custom domain or workers.dev subdomain

---

## 7. Data Requirements

### 7.1 Database Schema

#### 7.1.1 Users Table
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,           -- UUID
  username TEXT NOT NULL UNIQUE, -- User's display name
  avatar TEXT,                   -- Avatar URL (optional)
  lastSeen INTEGER NOT NULL      -- Unix timestamp
);
```

**Constraints**:
- `id`: Primary key, UUID format
- `username`: Unique, not null
- `lastSeen`: Not null, Unix timestamp in milliseconds

#### 7.1.2 Messages Table
```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,           -- UUID
  fromUser TEXT NOT NULL,        -- Sender user ID
  toUser TEXT NOT NULL,          -- Recipient user ID
  content TEXT NOT NULL,         -- Message content
  timestamp INTEGER NOT NULL,    -- Unix timestamp
  status TEXT NOT NULL,          -- 'sent' | 'delivered' | 'read'
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);
```

**Indexes**:
- `idx_messages_users`: ON (fromUser, toUser)
- `idx_messages_timestamp`: ON (timestamp)

**Constraints**:
- `id`: Primary key, UUID format
- Foreign keys to users table
- All fields not null

### 7.2 Data Retention
- **Messages**: Indefinite (no automatic deletion)
- **Users**: Indefinite
- **Cleanup**: Manual via `npm run db:clear`

### 7.3 Data Volume Estimates
- **Users**: Small scale (100s to 1000s)
- **Messages**: Variable (depends on usage)
- **Growth Rate**: Linear with user activity

---

## 8. Appendices

### 8.1 Acronyms and Abbreviations
- **API**: Application Programming Interface
- **CORS**: Cross-Origin Resource Sharing
- **CSS**: Cascading Style Sheets
- **D1**: Cloudflare D1 Database
- **FR**: Functional Requirement
- **HTTP**: Hypertext Transfer Protocol
- **HTTPS**: HTTP Secure
- **NFR**: Non-Functional Requirement
- **REST**: Representational State Transfer
- **SPA**: Single Page Application
- **SQL**: Structured Query Language
- **SRS**: Software Requirements Specification
- **SSL**: Secure Sockets Layer
- **TLS**: Transport Layer Security
- **UI**: User Interface
- **URL**: Uniform Resource Locator
- **UUID**: Universally Unique Identifier
- **WebSocket**: Full-duplex communication protocol
- **WSS**: WebSocket Secure
- **XSS**: Cross-Site Scripting

### 8.2 Project Structure
```
whatsapp-clone/
├── src/
│   ├── worker/              # Backend (Cloudflare Workers)
│   │   ├── index.ts         # Main worker, REST API
│   │   ├── ChatRoom.ts      # Durable Object for WebSocket
│   │   └── types.ts         # TypeScript interfaces
│   └── client/              # Frontend (React)
│       ├── components/      # React components
│       ├── hooks/           # Custom React hooks
│       ├── App.tsx          # Root component
│       ├── main.tsx         # Entry point
│       └── styles.css       # Global styles
├── scripts/                 # Utility scripts
├── schema.sql              # Database schema
├── wrangler.toml           # Cloudflare configuration
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies and scripts
```

### 8.3 Future Enhancements

#### 8.3.1 Phase 2 Features
1. **Group Chats**
   - Create group conversations
   - Multiple participants
   - Group admin functionality

2. **Media Sharing**
   - Image uploads
   - File attachments
   - Voice messages

3. **Enhanced Status**
   - Read receipts (message.status = 'read')
   - Last seen timestamps
   - Custom status messages

4. **User Profiles**
   - Profile pictures (upload to R2)
   - Bio/about section
   - Privacy settings

#### 8.3.2 Phase 3 Features
1. **Advanced Features**
   - End-to-end encryption
   - Voice/video calls
   - Message search
   - Message reactions
   - Message editing/deletion

2. **User Experience**
   - Push notifications
   - Desktop notifications
   - Mobile responsive design
   - Dark/light theme toggle
   - Message pagination

3. **Administration**
   - User management
   - Content moderation
   - Analytics dashboard
   - Rate limiting
   - Spam detection

### 8.4 Known Limitations

1. **Authentication**
   - No password protection
   - No email verification
   - Users can impersonate others with same username

2. **Message Features**
   - No message editing
   - No message deletion
   - No read receipts
   - No message search

3. **Scalability**
   - Single Durable Object for all users
   - No message pagination
   - No lazy loading of user list

4. **Security**
   - Messages not encrypted
   - No rate limiting
   - CORS allows all origins

5. **User Experience**
   - Session lost on page refresh
   - No offline message notifications
   - No unread message counters
   - Desktop only (not mobile optimized)

### 8.5 System Commands

**Development**
```bash
npm run dev              # Start dev servers
npm run dev:worker       # Worker only
npm run dev:client       # Client only
```

**Database**
```bash
npm run db:create        # Create D1 database
npm run db:init          # Initialize schema (local)
npm run db:init:remote   # Initialize schema (remote)
npm run db:clear         # Clear all data (local)
npm run db:clear:remote  # Clear all data (remote)
```

**Build & Deploy**
```bash
npm run build            # Build everything
npm run build:client     # Build frontend
npm run build:worker     # Deploy worker
npm run deploy           # Deploy to Cloudflare
```

### 8.6 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-11 | Development Team | Initial release |

---

**Document End**
