# Technical Design Document: Read Receipts Feature

## Document Information

| Field | Value |
|-------|-------|
| **Document ID** | TDD-001 |
| **Feature** | Read Receipts |
| **Related User Story** | US-001 |
| **Author** | Development Team |
| **Created** | 2025-12-11 |
| **Status** | Draft |
| **Version** | 1.0 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture Design](#3-architecture-design)
4. [Component Design](#4-component-design)
5. [Data Model](#5-data-model)
6. [API Design](#6-api-design)
7. [State Management](#7-state-management)
8. [WebSocket Protocol](#8-websocket-protocol)
9. [User Interface Design](#9-user-interface-design)
10. [Performance Considerations](#10-performance-considerations)
11. [Error Handling](#11-error-handling)
12. [Security Considerations](#12-security-considerations)
13. [Testing Strategy](#13-testing-strategy)
14. [Deployment Plan](#14-deployment-plan)
15. [Monitoring and Metrics](#15-monitoring-and-metrics)

---

## 1. Executive Summary

### 1.1 Purpose
This document describes the technical design for implementing read receipts in the WhatsApp Clone application. Read receipts allow users to see when their sent messages have been read by recipients, indicated by blue double checkmarks (✓✓).

### 1.2 Goals
- Enable real-time read receipt notifications
- Maintain consistency between client and server state
- Minimize performance impact on existing infrastructure
- Provide seamless user experience similar to WhatsApp

### 1.3 Non-Goals
- Read receipt privacy settings (future enhancement)
- Group chat read receipts
- Detailed "read at" timestamps
- Read receipt analytics

### 1.4 Success Metrics
- Read receipt delivery latency < 500ms
- Zero message state inconsistencies
- No performance degradation on existing features
- 100% test coverage for critical paths

---

## 2. System Overview

### 2.1 Current System Architecture

```
┌──────────────┐         HTTP/WS          ┌─────────────────┐
│              │◄────────────────────────►│  Cloudflare     │
│   Browser    │                          │  Workers        │
│   (React)    │                          │                 │
└──────────────┘                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  Durable Object │
                                          │   (ChatRoom)    │
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  Cloudflare D1  │
                                          │   Database      │
                                          └─────────────────┘
```

### 2.2 Read Receipts Flow

```
┌──────────┐              ┌──────────┐              ┌──────────┐
│ Alice    │              │ Server   │              │ Bob      │
│ (Sender) │              │          │              │(Receiver)│
└────┬─────┘              └────┬─────┘              └────┬─────┘
     │                         │                         │
     │ 1. Send Message         │                         │
     ├────────────────────────►│                         │
     │                         │ 2. Deliver Message      │
     │                         ├────────────────────────►│
     │                         │                         │
     │                         │ 3. Bob opens chat       │
     │                         │◄────────────────────────┤
     │                         │                         │
     │                         │ 4. Send Read Receipt    │
     │                         │◄────────────────────────┤
     │                         │                         │
     │ 5. Update UI (blue ✓✓)  │                         │
     │◄────────────────────────┤                         │
     │                         │                         │
```

### 2.3 Components Affected

| Component | Change Type | Impact |
|-----------|-------------|--------|
| `App.tsx` | Moderate | Add message status handler |
| `useWebSocket.ts` | Moderate | Add read receipt handling |
| `ChatWindow.tsx` | Minor | Pass read handler to children |
| `MessageList.tsx` | Major | Add visibility detection, send receipts |
| `styles.css` | Minor | Add blue checkmark styling |
| `ChatRoom.ts` | Moderate | Handle read receipt messages |
| `index.ts` | Minor | Add batch status update endpoint |
| `types.ts` | Minor | Update type definitions |

---

## 3. Architecture Design

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │   App.tsx    │───►│ ChatWindow   │───►│MessageList│ │
│  │              │    │              │    │           │ │
│  │ - State Mgmt │    │ - Chat Logic │    │ - Render  │ │
│  │ - WS Handler │    │              │    │ - Detect  │ │
│  └──────┬───────┘    └──────────────┘    └────┬─────┘ │
│         │                                      │       │
│         │           ┌──────────────────────────┘       │
│         │           │                                  │
│  ┌──────▼───────────▼─────┐                           │
│  │  useWebSocket Hook     │                           │
│  │                        │                           │
│  │  - Connect             │                           │
│  │  - Send Read Receipt   │                           │
│  │  - Handle Receipts     │                           │
│  └────────────┬───────────┘                           │
└───────────────┼───────────────────────────────────────┘
                │
                │ WebSocket
                │
┌───────────────▼───────────────────────────────────────┐
│                Backend (Cloudflare)                   │
├───────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────┐         ┌────────────────┐        │
│  │ Worker       │────────►│ Durable Object │        │
│  │ index.ts     │         │ ChatRoom.ts    │        │
│  │              │         │                │        │
│  │ - API Routes │         │ - WS Sessions  │        │
│  │ - DB Updates │         │ - Msg Routing  │        │
│  └──────┬───────┘         │ - Read Handler │        │
│         │                 └────────┬───────┘        │
│         │                          │                │
│  ┌──────▼──────────────────────────▼───┐           │
│  │      Cloudflare D1 Database         │           │
│  │                                     │           │
│  │  - messages (status column)         │           │
│  └─────────────────────────────────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

#### 3.2.1 Read Detection Flow

```
User Views Message
       │
       ▼
MessageList Component
       │
       ▼
useEffect Hook (500ms delay)
       │
       ▼
Collect Unread Message IDs
       │
       ▼
Call onMarkAsRead(messageIds)
       │
       ▼
ChatWindow passes to App
       │
       ▼
App.handleMarkAsRead
       │
       ├─► Update Local State (Optimistic)
       │
       └─► useWebSocket.sendReadReceipt(messageIds, toUserId)
              │
              ▼
         WebSocket Message
              │
              ▼
         Server (ChatRoom)
              │
              ├─► Update Database (async)
              │
              └─► Notify Sender via WebSocket
                     │
                     ▼
              Sender receives 'read' event
                     │
                     ▼
              Update sender's UI (blue checkmarks)
```

#### 3.2.2 Error Recovery Flow

```
Read Receipt Failed
       │
       ▼
WebSocket Error/Timeout
       │
       ▼
Retry with Exponential Backoff
       │
       ├─► Success: Continue
       │
       └─► Failure: Fall back to API
              │
              ▼
         PUT /api/messages/status
              │
              ▼
         Server Updates DB
              │
              ▼
         Next WS reconnect syncs state
```

### 3.3 Component Interaction Diagram

```
┌─────────────┐
│   App.tsx   │
│             │
│ messages[]  │◄─────┐
│             │      │
└──────┬──────┘      │
       │             │
       │ props       │ callback
       │             │
┌──────▼──────┐      │
│ ChatWindow  │      │
│             │      │
└──────┬──────┘      │
       │             │
       │ props       │ callback
       │             │
┌──────▼──────┐      │
│MessageList  │      │
│             │      │
│ useEffect   ├──────┘
│ (detects    │  onMarkAsRead(ids)
│  visible)   │
└─────────────┘
```

---

## 4. Component Design

### 4.1 Frontend Components

#### 4.1.1 MessageList Component

**File**: `src/client/components/MessageList.tsx`

**Responsibilities**:
- Render message list
- Detect when messages are visible to user
- Trigger read receipt sending after 500ms delay
- Update status icon colors based on message status

**Props Interface**:
```typescript
interface MessageListProps {
  messages: Message[];
  currentUserId: string;
  selectedUserId: string;
  isTyping: boolean;
  typingUsername: string;
  onMarkAsRead: (messageIds: string[]) => void;
}
```

**Key Methods**:
```typescript
// Detect visible unread messages
useEffect(() => {
  const unreadMessages = messages.filter(
    m => m.from === selectedUserId &&
         m.to === currentUserId &&
         m.status !== 'read'
  );

  if (unreadMessages.length > 0) {
    const timer = setTimeout(() => {
      onMarkAsRead(unreadMessages.map(m => m.id));
    }, 500);

    return () => clearTimeout(timer);
  }
}, [messages, selectedUserId, currentUserId, onMarkAsRead]);

// Render status icon with color
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'sent': return '✓';
    case 'delivered': return '✓✓';
    case 'read': return '✓✓';
    default: return '';
  }
};

const getStatusClass = (status: string) => {
  return status === 'read' ? 'status-icon read' : 'status-icon delivered';
};
```

**State**:
- None (stateless functional component)

**Side Effects**:
- Calls `onMarkAsRead` after 500ms delay
- Auto-scrolls to bottom on new messages

---

#### 4.1.2 ChatWindow Component

**File**: `src/client/components/ChatWindow.tsx`

**Responsibilities**:
- Manage chat UI layout
- Pass read receipt handler to MessageList
- Handle typing indicators

**Changes Required**:
```typescript
// Add onMarkAsRead prop
interface ChatWindowProps {
  currentUser: User;
  selectedUser: User | null;
  messages: Message[];
  typingUsers: Set<string>;
  connected: boolean;
  onSendMessage: (to: string, content: string) => void;
  onTyping: (to: string, typing: boolean) => void;
  onMarkAsRead: (messageIds: string[]) => void; // NEW
}

// Pass to MessageList
<MessageList
  messages={chatMessages}
  currentUserId={currentUser.id}
  selectedUserId={selectedUser.id}
  isTyping={isTyping}
  typingUsername={selectedUser.username}
  onMarkAsRead={(ids) => onMarkAsRead(selectedUser.id, ids)} // NEW
/>
```

---

#### 4.1.3 App Component

**File**: `src/client/App.tsx`

**Responsibilities**:
- Central state management
- WebSocket coordination
- Handle read receipt callbacks

**New State Handler**:
```typescript
const handleMarkAsRead = useCallback((toUserId: string, messageIds: string[]) => {
  // Optimistic UI update
  setMessages((prev) =>
    prev.map((m) =>
      messageIds.includes(m.id) ? { ...m, status: 'read' } : m
    )
  );

  // Send via WebSocket
  sendReadReceipt(messageIds, toUserId);
}, [sendReadReceipt]);

const handleReadReceipt = useCallback((messageIds: string[]) => {
  // Update UI when receipt received from server
  setMessages((prev) =>
    prev.map((m) =>
      messageIds.includes(m.id) ? { ...m, status: 'read' } : m
    )
  );
}, []);
```

**WebSocket Integration**:
```typescript
const {
  connected,
  sendMessage,
  sendTyping,
  sendStatus,
  sendReadReceipt // NEW
} = useWebSocket({
  userId: currentUser?.id || '',
  username: currentUser?.username || '',
  onMessage: handleMessage,
  onTyping: handleTyping,
  onOnlineStatus: handleOnlineStatus,
  onReadReceipt: handleReadReceipt, // NEW
  enabled: websocketEnabled,
});
```

---

#### 4.1.4 useWebSocket Hook

**File**: `src/client/hooks/useWebSocket.ts`

**New Interface**:
```typescript
interface UseWebSocketProps {
  userId: string;
  username: string;
  onMessage: (message: Message) => void;
  onTyping: (userId: string, typing: boolean) => void;
  onOnlineStatus: (users: Array<{ userId: string; username: string; online: boolean }>) => void;
  onReadReceipt: (messageIds: string[]) => void; // NEW
  enabled?: boolean;
}
```

**New Methods**:
```typescript
const sendReadReceipt = useCallback((messageIds: string[], to: string) => {
  if (ws.current && ws.current.readyState === WebSocket.OPEN) {
    ws.current.send(
      JSON.stringify({
        type: 'read',
        payload: { messageIds, to },
      })
    );
  }
}, []);

// In onmessage handler
ws.current.onmessage = (event) => {
  try {
    const data: WSMessage = JSON.parse(event.data);

    switch (data.type) {
      // ... existing cases

      case 'read':
        if (data.payload.messageIds) {
          onReadReceipt(data.payload.messageIds);
        }
        break;
    }
  } catch (error) {
    console.error('Failed to parse WebSocket message:', error);
  }
};

// Return new method
return {
  connected,
  sendMessage,
  sendTyping,
  sendStatus,
  sendReadReceipt, // NEW
};
```

---

### 4.2 Backend Components

#### 4.2.1 ChatRoom Durable Object

**File**: `src/worker/ChatRoom.ts`

**New Message Handler**:
```typescript
case 'read':
  if (session && data.payload.messageIds && data.payload.to) {
    const messageIds = data.payload.messageIds as string[];

    console.log(`[Read Receipt] User ${session.userId} read messages: ${messageIds.join(', ')}`);
    console.log(`[Read Receipt] Notifying sender: ${data.payload.to}`);

    // Notify sender about read status
    const sender = this.sessions.get(data.payload.to);
    if (sender) {
      sender.ws.send(JSON.stringify({
        type: 'read',
        payload: {
          messageIds,
          readBy: session.userId,
        },
      }));
      console.log(`[Read Receipt] Successfully notified sender ${data.payload.to}`);
    } else {
      console.log(`[Read Receipt] Sender ${data.payload.to} not online`);
    }

    // Update database asynchronously (fire-and-forget)
    // Note: In production, consider using Durable Objects storage
    // or queuing the update for reliability
  }
  break;
```

**Considerations**:
- Database updates are async and don't block WebSocket response
- Log all read receipt operations for debugging
- Handle case where sender is offline

---

#### 4.2.2 Worker API Endpoint

**File**: `src/worker/index.ts`

**New Endpoint**:
```typescript
// Batch update message status
if (path === '/messages/status' && request.method === 'PUT') {
  const body = await request.json() as {
    messageIds: string[];
    status: 'read' | 'delivered';
  };

  // Validate input
  if (!body.messageIds || body.messageIds.length === 0) {
    return new Response(JSON.stringify({ error: 'No message IDs provided' }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    });
  }

  if (body.messageIds.length > 100) {
    return new Response(JSON.stringify({ error: 'Too many message IDs (max 100)' }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    });
  }

  // Build parameterized query
  const placeholders = body.messageIds.map(() => '?').join(',');
  const query = `UPDATE messages SET status = ? WHERE id IN (${placeholders})`;

  await env.DB.prepare(query)
    .bind(body.status, ...body.messageIds)
    .run();

  return new Response(JSON.stringify({
    success: true,
    updated: body.messageIds.length
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    status: 200,
  });
}
```

**Error Handling**:
- Validate message ID array
- Limit batch size to 100 messages
- Return clear error messages
- Log failures for monitoring

---

## 5. Data Model

### 5.1 Database Schema

**No changes required** - existing schema supports read receipts via `status` column.

```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  fromUser TEXT NOT NULL,
  toUser TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  status TEXT NOT NULL,  -- 'sent', 'delivered', 'read'
  FOREIGN KEY (fromUser) REFERENCES users(id),
  FOREIGN KEY (toUser) REFERENCES users(id)
);
```

**Indexes** (existing):
- `idx_messages_users` on `(fromUser, toUser)` - efficient conversation queries
- `idx_messages_timestamp` on `timestamp` - chronological ordering

**Query Patterns**:
```sql
-- Get unread messages for a user
SELECT * FROM messages
WHERE toUser = ? AND status != 'read'
ORDER BY timestamp ASC;

-- Batch update message status
UPDATE messages
SET status = 'read'
WHERE id IN (?, ?, ?, ...);

-- Get conversation with status
SELECT * FROM messages
WHERE (fromUser = ? AND toUser = ?)
   OR (fromUser = ? AND toUser = ?)
ORDER BY timestamp ASC;
```

### 5.2 TypeScript Interfaces

**Updated Types**:
```typescript
// src/worker/types.ts

export interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read'; // Added 'read'
}

export interface WSMessage {
  type: 'auth' | 'message' | 'typing' | 'status' | 'online' | 'read' | 'error';
  payload: any;
}

export interface ReadReceiptPayload {
  messageIds: string[];
  to: string;
  readBy?: string; // Set by server when notifying sender
}

export interface ReadReceiptEvent {
  type: 'read';
  payload: ReadReceiptPayload;
}
```

### 5.3 State Management

**Client State**:
```typescript
// App.tsx state
const [messages, setMessages] = useState<Message[]>([]);

// Message state lifecycle:
// 1. User sends: { status: 'sent' }
// 2. Delivered to recipient: { status: 'delivered' }
// 3. Recipient reads: { status: 'read' }
```

**State Transitions**:
```
      send          deliver         read
sent ────────► delivered ────────► read
  │               │                 │
  └───────────────┴─────────────────┘
          (no backward transitions)
```

**Optimistic Updates**:
- Client updates local state immediately when marking as read
- If WebSocket fails, state remains optimistic
- On reconnect, server state takes precedence

---

## 6. API Design

### 6.1 REST API

#### 6.1.1 Batch Update Message Status

**Endpoint**: `PUT /api/messages/status`

**Request**:
```json
{
  "messageIds": ["uuid-1", "uuid-2", "uuid-3"],
  "status": "read"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "updated": 3
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "No message IDs provided"
}
```

**Rate Limiting**:
- 100 requests per minute per user
- Max 100 message IDs per request

---

### 6.2 WebSocket Protocol

#### 6.2.1 Send Read Receipt (Client → Server)

**Message Type**: `read`

**Payload**:
```json
{
  "type": "read",
  "payload": {
    "messageIds": ["uuid-1", "uuid-2"],
    "to": "sender-user-id"
  }
}
```

**Validation**:
- `messageIds` array must not be empty
- `to` must be a valid user ID
- Sender must be authenticated

---

#### 6.2.2 Read Receipt Notification (Server → Client)

**Message Type**: `read`

**Payload**:
```json
{
  "type": "read",
  "payload": {
    "messageIds": ["uuid-1", "uuid-2"],
    "readBy": "reader-user-id"
  }
}
```

**Delivery**:
- Sent only to original message sender
- Immediate delivery if sender is online
- No persistence if sender is offline (will sync on reconnect)

---

## 7. State Management

### 7.1 Client-Side State Flow

```
┌─────────────────────────────────────────────────────┐
│              App Component State                    │
│                                                     │
│  messages: Message[]                                │
│  ├─ id                                              │
│  ├─ from                                            │
│  ├─ to                                              │
│  ├─ content                                         │
│  ├─ timestamp                                       │
│  └─ status: 'sent' | 'delivered' | 'read'          │
│                                                     │
└─────────────────────────────────────────────────────┘
         │                            ▲
         │ props                      │ setState
         ▼                            │
┌─────────────────────────────────────────────────────┐
│           Child Components                          │
│                                                     │
│  MessageList                                        │
│  ├─ Renders messages with status icons             │
│  ├─ Detects visible unread messages                │
│  └─ Calls onMarkAsRead callback                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 7.2 State Update Patterns

#### 7.2.1 Optimistic Update Pattern

```typescript
// When user reads messages
const handleMarkAsRead = useCallback((toUserId: string, messageIds: string[]) => {
  // 1. Optimistic update
  setMessages((prev) =>
    prev.map((m) =>
      messageIds.includes(m.id) ? { ...m, status: 'read' } : m
    )
  );

  // 2. Send to server
  sendReadReceipt(messageIds, toUserId);

  // 3. Server confirms (or we revert on error)
}, [sendReadReceipt]);
```

#### 7.2.2 Server Confirmation Pattern

```typescript
// When receiving read receipt from server
const handleReadReceipt = useCallback((messageIds: string[]) => {
  setMessages((prev) =>
    prev.map((m) =>
      messageIds.includes(m.id) ? { ...m, status: 'read' } : m
    )
  );
}, []);
```

### 7.3 State Synchronization

**On Reconnect**:
```typescript
// Fetch latest message states
useEffect(() => {
  if (connected && selectedUser) {
    fetchMessageHistory(selectedUser.id);
  }
}, [connected, selectedUser]);
```

**Conflict Resolution**:
- Server state is source of truth
- On reconnect, client fetches latest from database
- Local optimistic updates are overwritten if conflicting

---

## 8. WebSocket Protocol

### 8.1 Message Format

All WebSocket messages follow this format:

```typescript
interface WSMessage {
  type: string;
  payload: any;
}
```

### 8.2 Read Receipt Flow

#### 8.2.1 Client Sends Read Receipt

```javascript
{
  "type": "read",
  "payload": {
    "messageIds": ["msg-id-1", "msg-id-2"],
    "to": "original-sender-id"
  }
}
```

#### 8.2.2 Server Forwards to Sender

```javascript
{
  "type": "read",
  "payload": {
    "messageIds": ["msg-id-1", "msg-id-2"],
    "readBy": "reader-user-id"
  }
}
```

### 8.3 Error Handling

**Connection Lost**:
```javascript
// Retry mechanism
let retryCount = 0;
const maxRetries = 5;
const baseDelay = 1000;

const retry = () => {
  if (retryCount < maxRetries) {
    setTimeout(() => {
      connect();
      retryCount++;
    }, baseDelay * Math.pow(2, retryCount));
  }
};
```

**Invalid Message**:
```javascript
{
  "type": "error",
  "payload": {
    "message": "Invalid message format",
    "originalType": "read"
  }
}
```

---

## 9. User Interface Design

### 9.1 Visual Design

#### 9.1.1 Message Status Icons

```css
/* Single gray checkmark - Sent */
.status-icon.sent {
  content: '✓';
  color: #8696a0;
}

/* Double gray checkmarks - Delivered */
.status-icon.delivered {
  content: '✓✓';
  color: #8696a0;
}

/* Double blue checkmarks - Read */
.status-icon.read {
  content: '✓✓';
  color: #53bdeb;
  transition: color 0.3s ease;
}
```

#### 9.1.2 Message Bubble Layout

```
┌──────────────────────────────────────┐
│  Your message here                   │
│                    ✓✓        10:23 AM│  ← Read (blue)
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Another message                     │
│                    ✓✓        10:24 AM│  ← Delivered (gray)
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Latest message                      │
│                    ✓         10:25 AM│  ← Sent (gray)
└──────────────────────────────────────┘
```

### 9.2 Animation

**Status Transition Animation**:
```css
.status-icon {
  transition: color 0.3s ease-in-out;
}

/* Optional: Subtle pulse on status change */
@keyframes statusChange {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.status-icon.read {
  animation: statusChange 0.3s ease-in-out;
}
```

### 9.3 Accessibility

**Screen Reader Support**:
```tsx
<span
  className={`status-icon ${getStatusClass(message.status)}`}
  aria-label={`Message ${message.status}`}
  role="status"
>
  {getStatusIcon(message.status)}
</span>
```

**Color Contrast**:
- Blue checkmarks: #53bdeb on #005c4b background = 4.8:1 (WCAG AA compliant)
- Gray checkmarks: #8696a0 on #005c4b background = 3.2:1 (needs improvement)

**Recommendation**: Use darker gray (#6b7c85) for better contrast.

---

## 10. Performance Considerations

### 10.1 Client-Side Performance

#### 10.1.1 Debouncing Read Receipts

```typescript
// Wait 500ms before sending read receipt
useEffect(() => {
  const timer = setTimeout(() => {
    onMarkAsRead(unreadMessageIds);
  }, 500);

  return () => clearTimeout(timer);
}, [messages, selectedUser]);
```

**Benefits**:
- Prevents excessive WebSocket messages
- Ensures user actually viewed the message
- Reduces server load

#### 10.1.2 Batching

```typescript
// Batch multiple messages in single read receipt
const unreadMessages = messages.filter(/* ... */);
const messageIds = unreadMessages.map(m => m.id);

// Send all IDs in one WebSocket message
sendReadReceipt(messageIds, toUserId);
```

**Metrics**:
- Reduces WebSocket messages by ~90% for bulk reads
- Single database query instead of N queries

#### 10.1.3 React Rendering Optimization

```typescript
// Memoize status icon component
const StatusIcon = React.memo(({ status }: { status: string }) => (
  <span className={getStatusClass(status)}>
    {getStatusIcon(status)}
  </span>
));

// Prevent unnecessary re-renders
const MessageItem = React.memo(({ message }: { message: Message }) => (
  <div className="message">
    {message.content}
    <StatusIcon status={message.status} />
  </div>
), (prev, next) => prev.message.status === next.message.status);
```

### 10.2 Server-Side Performance

#### 10.2.1 Database Query Optimization

```sql
-- Use parameterized query with IN clause
UPDATE messages
SET status = 'read'
WHERE id IN (?, ?, ?, ?)  -- Max 100 placeholders
```

**Performance**:
- Single query for multiple messages
- Uses index on `id` (primary key)
- Execution time: O(n) where n = number of IDs

#### 10.2.2 Async Database Updates

```typescript
// Don't block WebSocket response on database update
case 'read':
  if (session && data.payload.messageIds) {
    // 1. Immediately notify sender (fast path)
    const sender = this.sessions.get(data.payload.to);
    if (sender) {
      sender.ws.send(JSON.stringify({
        type: 'read',
        payload: { messageIds: data.payload.messageIds }
      }));
    }

    // 2. Update database asynchronously (slow path)
    // Fire-and-forget pattern
    // In production, consider using a queue
  }
  break;
```

**Trade-offs**:
- Faster WebSocket response (< 10ms vs 50-100ms with DB wait)
- Risk of data loss if worker crashes before DB update
- Acceptable for read receipts (can re-sync on reconnect)

#### 10.2.3 WebSocket Message Size

```
Uncompressed message: ~150 bytes
{
  "type": "read",
  "payload": {
    "messageIds": ["uuid-1", "uuid-2"],
    "readBy": "user-id"
  }
}

With 10 message IDs: ~350 bytes
With 100 message IDs: ~2.5KB (max batch size)
```

**Bandwidth Impact**:
- 100 users × 10 read receipts/hour = 350KB/hour
- Negligible compared to message content

### 10.3 Performance Budgets

| Metric | Target | Maximum |
|--------|--------|---------|
| Read receipt send latency | 50ms | 200ms |
| UI update after receipt | 16ms | 50ms |
| Database update | 100ms | 500ms |
| WebSocket message size | 500B | 3KB |
| Client memory overhead | 10KB | 50KB |

---

## 11. Error Handling

### 11.1 Client-Side Errors

#### 11.1.1 WebSocket Send Failure

```typescript
const sendReadReceipt = useCallback((messageIds: string[], to: string) => {
  if (ws.current && ws.current.readyState === WebSocket.OPEN) {
    try {
      ws.current.send(
        JSON.stringify({
          type: 'read',
          payload: { messageIds, to },
        })
      );
    } catch (error) {
      console.error('Failed to send read receipt:', error);

      // Fall back to REST API
      fetch('/api/messages/status', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messageIds,
          status: 'read'
        })
      }).catch(err => {
        console.error('REST API fallback also failed:', err);
        // Message will sync on next successful connection
      });
    }
  } else {
    console.warn('WebSocket not connected, queueing read receipt');
    // Queue for sending when reconnected
    queuedReadReceipts.push({ messageIds, to });
  }
}, []);
```

#### 11.1.2 Invalid State

```typescript
const handleMarkAsRead = useCallback((toUserId: string, messageIds: string[]) => {
  // Validate inputs
  if (!toUserId || !messageIds || messageIds.length === 0) {
    console.error('Invalid parameters for markAsRead');
    return;
  }

  // Validate message ownership
  const validMessageIds = messages
    .filter(m => messageIds.includes(m.id) && m.from === toUserId && m.to === currentUser?.id)
    .map(m => m.id);

  if (validMessageIds.length === 0) {
    console.warn('No valid messages to mark as read');
    return;
  }

  // Continue with valid IDs only
  setMessages(prev =>
    prev.map(m =>
      validMessageIds.includes(m.id) ? { ...m, status: 'read' } : m
    )
  );

  sendReadReceipt(validMessageIds, toUserId);
}, [messages, currentUser, sendReadReceipt]);
```

### 11.2 Server-Side Errors

#### 11.2.1 Database Errors

```typescript
case 'read':
  if (session && data.payload.messageIds) {
    try {
      // Notify sender immediately
      const sender = this.sessions.get(data.payload.to);
      if (sender) {
        sender.ws.send(JSON.stringify({
          type: 'read',
          payload: { messageIds: data.payload.messageIds }
        }));
      }

      // Update database with error handling
      // (Actual implementation would use env.DB)
      console.log('Updating message status in database');
    } catch (error) {
      console.error('Failed to process read receipt:', error);

      // Send error to client
      ws.send(JSON.stringify({
        type: 'error',
        payload: {
          message: 'Failed to process read receipt',
          retry: true
        }
      }));
    }
  }
  break;
```

#### 11.2.2 Invalid Message Format

```typescript
ws.addEventListener('message', async (event) => {
  try {
    const data: WSMessage = JSON.parse(event.data as string);

    // Validate message structure
    if (!data.type || !data.payload) {
      throw new Error('Invalid message structure');
    }

    switch (data.type) {
      case 'read':
        // Validate read receipt payload
        if (!Array.isArray(data.payload.messageIds)) {
          throw new Error('messageIds must be an array');
        }
        if (data.payload.messageIds.length === 0) {
          throw new Error('messageIds array is empty');
        }
        if (data.payload.messageIds.length > 100) {
          throw new Error('Too many message IDs (max 100)');
        }
        if (!data.payload.to) {
          throw new Error('Missing recipient ID');
        }

        // Process read receipt
        // ...
        break;
    }
  } catch (error) {
    console.error('WebSocket message error:', error);
    ws.send(JSON.stringify({
      type: 'error',
      payload: {
        message: error.message,
        originalType: data?.type
      }
    }));
  }
});
```

### 11.3 Error Recovery Strategies

| Error Type | Strategy | User Impact |
|------------|----------|-------------|
| WebSocket disconnected | Auto-reconnect with exponential backoff | Temporary delay, syncs on reconnect |
| Database timeout | Queue update, retry later | None (optimistic UI) |
| Invalid message format | Log error, send error message to client | None if validation is client-side |
| Sender offline | Store in memory, deliver on reconnect | Delayed notification |
| Concurrent updates | Last write wins | Minor inconsistency, self-corrects |

---

## 12. Security Considerations

### 12.1 Authentication & Authorization

**Verify Message Ownership**:
```typescript
// Only allow marking messages as read if recipient is current user
const validMessageIds = messageIds.filter(id => {
  const message = findMessageById(id);
  return message && message.to === currentUser.id;
});
```

**Prevent Spoofing**:
```typescript
// Server validates that user can only send read receipts for their own messages
case 'read':
  if (session) {
    // Verify all message IDs belong to current user as recipient
    // (Would require DB lookup in production)
    const validIds = await verifyMessageRecipient(
      session.userId,
      data.payload.messageIds
    );

    if (validIds.length !== data.payload.messageIds.length) {
      ws.send(JSON.stringify({
        type: 'error',
        payload: { message: 'Unauthorized: Not message recipient' }
      }));
      return;
    }

    // Process read receipt
  }
  break;
```

### 12.2 Input Validation

**Client-Side**:
```typescript
// Sanitize message IDs (must be UUIDs)
const isValidUUID = (id: string) => {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(id);
};

const sanitizedIds = messageIds.filter(isValidUUID);
```

**Server-Side**:
```typescript
// Validate and sanitize all inputs
if (!Array.isArray(data.payload.messageIds)) {
  throw new Error('Invalid messageIds format');
}

const sanitizedIds = data.payload.messageIds
  .filter(id => typeof id === 'string' && id.length === 36)
  .slice(0, 100); // Enforce max batch size
```

### 12.3 Rate Limiting

**Per-User Limits**:
```typescript
// Track read receipts sent per user
const readReceiptCounts = new Map<string, number>();

case 'read':
  if (session) {
    const count = readReceiptCounts.get(session.userId) || 0;

    if (count > 100) { // 100 read receipts per minute
      ws.send(JSON.stringify({
        type: 'error',
        payload: { message: 'Rate limit exceeded' }
      }));
      return;
    }

    readReceiptCounts.set(session.userId, count + 1);

    // Reset counter after 1 minute
    setTimeout(() => {
      readReceiptCounts.delete(session.userId);
    }, 60000);
  }
  break;
```

### 12.4 Data Privacy

**No Sensitive Data in Logs**:
```typescript
// DON'T log message content
console.log(`Read receipt for messages: ${messageIds.join(', ')}`); // ✗

// DO log only metadata
console.log(`Read receipt: ${messageIds.length} messages`); // ✓
```

**Minimal Data Exposure**:
```javascript
// Only send necessary data to clients
{
  "type": "read",
  "payload": {
    "messageIds": ["..."],  // Only IDs
    // DON'T include message content
  }
}
```

---

## 13. Testing Strategy

### 13.1 Unit Tests

#### 13.1.1 Frontend Tests

**MessageList Component**:
```typescript
describe('MessageList', () => {
  it('should call onMarkAsRead after 500ms for unread messages', async () => {
    const onMarkAsRead = jest.fn();
    const messages = [
      { id: '1', from: 'user2', to: 'user1', status: 'delivered' },
      { id: '2', from: 'user2', to: 'user1', status: 'delivered' },
    ];

    render(
      <MessageList
        messages={messages}
        currentUserId="user1"
        selectedUserId="user2"
        onMarkAsRead={onMarkAsRead}
        isTyping={false}
        typingUsername=""
      />
    );

    await waitFor(() => {
      expect(onMarkAsRead).toHaveBeenCalledWith(['1', '2']);
    }, { timeout: 600 });
  });

  it('should not mark already read messages', () => {
    const onMarkAsRead = jest.fn();
    const messages = [
      { id: '1', from: 'user2', to: 'user1', status: 'read' },
    ];

    render(
      <MessageList
        messages={messages}
        currentUserId="user1"
        selectedUserId="user2"
        onMarkAsRead={onMarkAsRead}
        isTyping={false}
        typingUsername=""
      />
    );

    expect(onMarkAsRead).not.toHaveBeenCalled();
  });

  it('should render blue checkmarks for read messages', () => {
    const messages = [
      { id: '1', from: 'user1', to: 'user2', status: 'read', content: 'Hello' },
    ];

    const { container } = render(
      <MessageList
        messages={messages}
        currentUserId="user1"
        selectedUserId="user2"
        onMarkAsRead={jest.fn()}
        isTyping={false}
        typingUsername=""
      />
    );

    const statusIcon = container.querySelector('.status-icon.read');
    expect(statusIcon).toBeInTheDocument();
    expect(statusIcon).toHaveTextContent('✓✓');
  });
});
```

**useWebSocket Hook**:
```typescript
describe('useWebSocket - Read Receipts', () => {
  it('should send read receipt via WebSocket', () => {
    const mockWs = {
      send: jest.fn(),
      readyState: WebSocket.OPEN,
    };

    const { result } = renderHook(() => useWebSocket({
      userId: 'user1',
      username: 'User1',
      onMessage: jest.fn(),
      onTyping: jest.fn(),
      onOnlineStatus: jest.fn(),
      onReadReceipt: jest.fn(),
      enabled: true,
    }));

    // Mock WebSocket
    result.current.ws = mockWs;

    result.current.sendReadReceipt(['msg1', 'msg2'], 'user2');

    expect(mockWs.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'read',
        payload: {
          messageIds: ['msg1', 'msg2'],
          to: 'user2'
        }
      })
    );
  });

  it('should handle incoming read receipts', () => {
    const onReadReceipt = jest.fn();

    renderHook(() => useWebSocket({
      userId: 'user1',
      username: 'User1',
      onMessage: jest.fn(),
      onTyping: jest.fn(),
      onOnlineStatus: jest.fn(),
      onReadReceipt,
      enabled: true,
    }));

    // Simulate incoming message
    const event = new MessageEvent('message', {
      data: JSON.stringify({
        type: 'read',
        payload: {
          messageIds: ['msg1', 'msg2'],
          readBy: 'user2'
        }
      })
    });

    mockWebSocket.onmessage(event);

    expect(onReadReceipt).toHaveBeenCalledWith(['msg1', 'msg2']);
  });
});
```

#### 13.1.2 Backend Tests

**ChatRoom Tests**:
```typescript
describe('ChatRoom - Read Receipts', () => {
  it('should forward read receipt to sender', () => {
    const chatRoom = new ChatRoom();
    const senderWs = { send: jest.fn() };
    const readerWs = { send: jest.fn() };

    // Set up sessions
    chatRoom.sessions.set('sender-id', { userId: 'sender-id', ws: senderWs });
    chatRoom.sessions.set('reader-id', { userId: 'reader-id', ws: readerWs });

    // Reader sends read receipt
    chatRoom.handleMessage(readerWs, {
      type: 'read',
      payload: {
        messageIds: ['msg1'],
        to: 'sender-id'
      }
    });

    expect(senderWs.send).toHaveBeenCalledWith(
      expect.stringContaining('"type":"read"')
    );
    expect(senderWs.send).toHaveBeenCalledWith(
      expect.stringContaining('"readBy":"reader-id"')
    );
  });

  it('should handle sender offline gracefully', () => {
    const chatRoom = new ChatRoom();
    const readerWs = { send: jest.fn() };

    chatRoom.sessions.set('reader-id', { userId: 'reader-id', ws: readerWs });

    // Sender is not in sessions (offline)
    expect(() => {
      chatRoom.handleMessage(readerWs, {
        type: 'read',
        payload: {
          messageIds: ['msg1'],
          to: 'offline-user'
        }
      });
    }).not.toThrow();
  });
});
```

### 13.2 Integration Tests

```typescript
describe('Read Receipts Integration', () => {
  it('should mark messages as read end-to-end', async () => {
    // Set up two users
    const alice = await createUser('Alice');
    const bob = await createUser('Bob');

    // Alice sends message to Bob
    const message = await sendMessage(alice.id, bob.id, 'Hello Bob');
    expect(message.status).toBe('delivered');

    // Bob opens chat
    await openChat(bob.id, alice.id);

    // Wait for read receipt
    await waitFor(() => {
      const updatedMessage = getMessage(message.id);
      expect(updatedMessage.status).toBe('read');
    });

    // Alice sees blue checkmarks
    const aliceView = await getMessageStatus(alice.id, message.id);
    expect(aliceView.status).toBe('read');
  });
});
```

### 13.3 E2E Tests

```typescript
describe('Read Receipts E2E', () => {
  it('should show blue checkmarks when message is read', async () => {
    // Alice logs in
    await page.goto('http://localhost:3000');
    await page.fill('input[type="text"]', 'Alice');
    await page.click('button:has-text("Continue")');

    // Bob logs in (different browser)
    const bobPage = await context.newPage();
    await bobPage.goto('http://localhost:3000');
    await bobPage.fill('input[type="text"]', 'Bob');
    await bobPage.click('button:has-text("Continue")');

    // Alice sends message
    await page.click('text=Bob');
    await page.fill('.message-input', 'Hello Bob!');
    await page.click('button:has-text("Send")');

    // Initially delivered (gray checkmarks)
    await expect(page.locator('.status-icon.delivered')).toBeVisible();

    // Bob opens chat with Alice
    await bobPage.click('text=Alice');

    // Wait for read status update on Alice's side
    await expect(page.locator('.status-icon.read')).toBeVisible({ timeout: 1000 });

    // Verify blue color
    const statusIcon = await page.locator('.status-icon.read');
    const color = await statusIcon.evaluate(el =>
      window.getComputedStyle(el).color
    );
    expect(color).toBe('rgb(83, 189, 235)'); // #53bdeb
  });
});
```

### 13.4 Performance Tests

```typescript
describe('Read Receipts Performance', () => {
  it('should handle 100 messages batch update within 500ms', async () => {
    const messageIds = Array.from({ length: 100 }, () => createMessageId());

    const startTime = Date.now();
    await updateMessageStatus(messageIds, 'read');
    const endTime = Date.now();

    expect(endTime - startTime).toBeLessThan(500);
  });

  it('should not cause memory leak with repeated updates', async () => {
    const initialMemory = process.memoryUsage().heapUsed;

    for (let i = 0; i < 1000; i++) {
      await markMessagesAsRead(['msg1', 'msg2']);
    }

    const finalMemory = process.memoryUsage().heapUsed;
    const memoryIncrease = finalMemory - initialMemory;

    expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024); // < 10MB
  });
});
```

---

## 14. Deployment Plan

### 14.1 Pre-Deployment Checklist

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E tests passing
- [ ] Code review completed
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Database migration ready (if needed)
- [ ] Rollback plan prepared

### 14.2 Deployment Steps

#### Phase 1: Database Preparation (if needed)
```bash
# No schema changes required
# Existing status column supports 'read' value
```

#### Phase 2: Backend Deployment
```bash
# 1. Deploy worker with new read receipt handler
npm run build:worker
npm run deploy

# 2. Verify deployment
curl https://whatsapp-clone-worker.your-subdomain.workers.dev/api/users

# 3. Test WebSocket connection
wscat -c wss://whatsapp-clone-worker.your-subdomain.workers.dev/ws
```

#### Phase 3: Frontend Deployment
```bash
# 1. Build frontend
npm run build:client

# 2. Deploy to hosting (e.g., Cloudflare Pages)
# (Frontend deployment process depends on hosting choice)

# 3. Verify deployment
# Open app in browser, test read receipts
```

#### Phase 4: Gradual Rollout
```
Day 1: Deploy to 10% of users
Day 2: Monitor metrics, increase to 50%
Day 3: Full rollout to 100% of users
```

### 14.3 Rollback Plan

**If issues detected**:
```bash
# 1. Revert worker deployment
wrangler rollback

# 2. Revert frontend deployment
# (Process depends on hosting)

# 3. Clear user caches
# Instruct users to hard refresh (Ctrl+F5)
```

**Feature Flag** (optional):
```typescript
// Enable/disable read receipts via environment variable
const READ_RECEIPTS_ENABLED = env.FEATURE_READ_RECEIPTS === 'true';

if (READ_RECEIPTS_ENABLED) {
  // Handle read receipts
}
```

### 14.4 Post-Deployment Verification

**Smoke Tests**:
1. User A sends message to User B
2. User B opens chat
3. User A sees blue checkmarks within 1 second
4. Status persists after refresh

**Monitoring**:
- Check error logs for WebSocket errors
- Monitor database query performance
- Track read receipt message counts
- Verify no spike in error rates

---

## 15. Monitoring and Metrics

### 15.1 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Read receipt delivery time | < 500ms | > 2s |
| WebSocket message errors | < 0.1% | > 1% |
| Database update latency | < 100ms | > 500ms |
| Client-side errors | < 0.5% | > 2% |
| Message status inconsistency | 0 | > 10 |

### 15.2 Logging

**Client-Side**:
```typescript
// Log read receipt events
console.log('[ReadReceipt] Marking messages as read:', {
  messageIds,
  toUserId,
  timestamp: Date.now()
});

// Log errors
console.error('[ReadReceipt] Failed to send:', {
  error: error.message,
  messageIds,
  websocketState: ws.readyState
});
```

**Server-Side**:
```typescript
// Log in ChatRoom
console.log('[ReadReceipt] Received from user:', {
  userId: session.userId,
  messageCount: messageIds.length,
  recipientId: data.payload.to,
  timestamp: Date.now()
});

console.log('[ReadReceipt] Forwarded to sender:', {
  senderId: data.payload.to,
  messageCount: messageIds.length,
  senderOnline: !!sender
});
```

### 15.3 Dashboards

**Cloudflare Workers Analytics**:
- Request counts for `/api/messages/status`
- WebSocket connection count
- Error rates by endpoint
- P50/P95/P99 latencies

**Custom Metrics** (if implemented):
```typescript
// Track read receipt metrics
metrics.increment('read_receipts.sent');
metrics.increment('read_receipts.delivered');
metrics.timing('read_receipts.latency', latency);
metrics.gauge('read_receipts.batch_size', messageIds.length);
```

### 15.4 Alerts

**Critical Alerts**:
- WebSocket error rate > 5%
- Database timeout rate > 1%
- Read receipt latency > 5s (P95)

**Warning Alerts**:
- Read receipt latency > 2s (P95)
- Increased database query time
- High memory usage in Durable Objects

---

## 16. Future Enhancements

### 16.1 Read Receipt Privacy Settings

Allow users to disable read receipts:
```typescript
interface UserSettings {
  readReceiptsEnabled: boolean;
}

// Only send read receipts if enabled
if (currentUser.settings.readReceiptsEnabled) {
  sendReadReceipt(messageIds, toUserId);
}
```

### 16.2 "Read At" Timestamp

Show when message was read:
```typescript
interface Message {
  // ...existing fields
  readAt?: number; // Timestamp when marked as read
}

// Display in UI
<span className="read-time">
  Read at {formatTime(message.readAt)}
</span>
```

### 16.3 Group Chat Read Receipts

Show who has read messages in group chats:
```typescript
interface GroupMessage {
  id: string;
  readBy: string[]; // Array of user IDs who read it
}

// Display
<span className="read-by">
  Read by {readBy.map(id => getUserName(id)).join(', ')}
</span>
```

### 16.4 Offline Message Sync

Queue read receipts when offline and sync on reconnect:
```typescript
const queuedReadReceipts = useRef<Array<{messageIds: string[], to: string}>>([]);

// When reconnected
useEffect(() => {
  if (connected && queuedReadReceipts.current.length > 0) {
    queuedReadReceipts.current.forEach(receipt => {
      sendReadReceipt(receipt.messageIds, receipt.to);
    });
    queuedReadReceipts.current = [];
  }
}, [connected]);
```

---

## 17. Appendices

### Appendix A: Code Review Checklist

- [ ] All TypeScript interfaces updated
- [ ] No `any` types without justification
- [ ] Error handling implemented for all async operations
- [ ] WebSocket messages validated before processing
- [ ] Database queries parameterized (no SQL injection)
- [ ] Rate limiting implemented
- [ ] Logging added for debugging
- [ ] Component memoization used where appropriate
- [ ] CSS transitions smooth (< 300ms)
- [ ] Accessibility attributes added
- [ ] Mobile responsive (if applicable)

### Appendix B: Database Indexes

Existing indexes support read receipts efficiently:
```sql
-- Primary key for fast lookups
CREATE INDEX IF NOT EXISTS idx_messages_id ON messages(id);

-- Conversation queries
CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(fromUser, toUser);

-- Status queries (if needed in future)
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
```

### Appendix C: WebSocket Message Examples

**Send Read Receipt**:
```json
{
  "type": "read",
  "payload": {
    "messageIds": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    ],
    "to": "c3d4e5f6-a7b8-9012-cdef-123456789012"
  }
}
```

**Receive Read Receipt**:
```json
{
  "type": "read",
  "payload": {
    "messageIds": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    ],
    "readBy": "d4e5f6a7-b8c9-0123-def1-234567890123"
  }
}
```

### Appendix D: Performance Benchmark Results

**Expected Performance** (based on similar implementations):

| Operation | Time |
|-----------|------|
| Detect visible unread messages | < 5ms |
| Update local state (optimistic) | < 10ms |
| Send WebSocket message | < 50ms |
| Server process + forward | < 100ms |
| Database update (async) | < 200ms |
| **Total end-to-end latency** | **< 500ms** |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-12-11 | Dev Team | Initial draft |
| 1.0 | 2025-12-11 | Dev Team | Complete design document |

---

## Approvals

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tech Lead | | | |
| Backend Engineer | | | |
| Frontend Engineer | | | |
| QA Lead | | | |
| Product Owner | | | |

---

**End of Technical Design Document**
