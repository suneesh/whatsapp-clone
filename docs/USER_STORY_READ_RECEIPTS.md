# User Story: Read Receipts

## Epic
Real-time Messaging Enhancements

## User Story
**As a** messaging app user
**I want to** see when my messages have been read by the recipient
**So that** I know if the other person has seen my message and can expect a response

## Story ID
US-001

## Priority
Medium

## Story Points
5

## Acceptance Criteria

### AC1: Visual Read Receipt Indicators
**Given** I have sent a message to another user
**When** the recipient reads my message
**Then** the message status should update from "delivered" (✓✓ gray) to "read" (✓✓ blue)

### AC2: Automatic Read Detection
**Given** I am viewing a chat with unread messages
**When** the messages are visible in my viewport
**Then** the system should automatically mark them as "read" and notify the sender

### AC3: Real-time Status Updates
**Given** I am viewing my sent messages
**When** the recipient reads any message
**Then** I should see the read status update in real-time without refreshing

### AC4: Read Status Persistence
**Given** messages have been marked as read
**When** I close and reopen the chat
**Then** the read status should persist and display correctly

### AC5: Bulk Read Updates
**Given** I open a chat with multiple unread messages
**When** all messages become visible
**Then** all unread messages should be marked as read in a single batch operation

### AC6: Read Receipt Indication in Sender View
**Given** I am the sender viewing my sent messages
**When** a message is in "read" status
**Then** I should see blue checkmarks (✓✓) next to the timestamp

### AC7: No Read Receipt on Own Messages
**Given** I am viewing received messages in a chat
**When** I look at messages I received
**Then** I should NOT see any read receipt indicators (only on messages I sent)

## Technical Requirements

### Frontend Changes

#### 1. Message Status Component Update
```typescript
// Update MessageList.tsx to handle read status
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'sent':
      return '✓';  // Single gray checkmark
    case 'delivered':
      return '✓✓'; // Double gray checkmarks
    case 'read':
      return '✓✓'; // Double blue checkmarks
    default:
      return '';
  }
};

const getStatusClass = (status: string) => {
  return status === 'read' ? 'status-icon read' : 'status-icon delivered';
};
```

#### 2. Read Detection Hook
```typescript
// Create useReadReceipt.ts hook
interface UseReadReceiptProps {
  messages: Message[];
  currentUserId: string;
  selectedUserId: string;
  onMarkAsRead: (messageIds: string[]) => void;
}

export const useReadReceipt = ({
  messages,
  currentUserId,
  selectedUserId,
  onMarkAsRead
}: UseReadReceiptProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Use Intersection Observer to detect visible messages
    const unreadMessages = messages.filter(
      m => m.from === selectedUserId &&
           m.to === currentUserId &&
           m.status !== 'read'
    );

    if (unreadMessages.length > 0) {
      // Mark messages as read after brief delay
      const timer = setTimeout(() => {
        onMarkAsRead(unreadMessages.map(m => m.id));
      }, 500); // 500ms delay to ensure user is actually viewing

      return () => clearTimeout(timer);
    }
  }, [messages, selectedUserId, currentUserId]);
};
```

#### 3. WebSocket Read Event
```typescript
// Update useWebSocket.ts to send read receipts
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

// Handle incoming read receipts
case 'read':
  if (data.payload.messageIds) {
    data.payload.messageIds.forEach((messageId: string) => {
      onMessageStatusUpdate(messageId, 'read');
    });
  }
  break;
```

#### 4. App State Management
```typescript
// Update App.tsx
const handleMessageStatusUpdate = useCallback((messageId: string, status: 'read') => {
  setMessages((prev) =>
    prev.map((m) =>
      m.id === messageId ? { ...m, status } : m
    )
  );
}, []);

// Add to WebSocket hook
const { connected, sendMessage, sendTyping, sendStatus, sendReadReceipt } = useWebSocket({
  userId: currentUser?.id || '',
  username: currentUser?.username || '',
  onMessage: handleMessage,
  onTyping: handleTyping,
  onOnlineStatus: handleOnlineStatus,
  onMessageStatusUpdate: handleMessageStatusUpdate,
  enabled: websocketEnabled,
});
```

#### 5. CSS Updates
```css
/* Update styles.css */
.status-icon.read {
  color: #53bdeb; /* Blue color for read receipts */
}

.status-icon.delivered {
  color: #8696a0; /* Gray color for delivered */
}

.status-icon.sent {
  color: #8696a0; /* Gray color for sent */
}
```

### Backend Changes

#### 1. WebSocket Message Handler
```typescript
// Update ChatRoom.ts
case 'read':
  if (session && data.payload.messageIds) {
    const messageIds = data.payload.messageIds as string[];

    console.log(`Marking messages as read: ${messageIds.join(', ')}`);

    // Update message status in database
    // (Can be done asynchronously, no need to block)

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
    }
  }
  break;
```

#### 2. Database Update API
```typescript
// Update index.ts to add batch update endpoint
// Update message status
if (path === '/messages/status' && request.method === 'PUT') {
  const body = await request.json() as {
    messageIds: string[];
    status: 'read';
  };

  // Update all messages in a single query
  const placeholders = body.messageIds.map(() => '?').join(',');
  await env.DB.prepare(
    `UPDATE messages SET status = ? WHERE id IN (${placeholders})`
  ).bind(body.status, ...body.messageIds).run();

  return new Response(JSON.stringify({ success: true }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    status: 200,
  });
}
```

#### 3. Type Definitions
```typescript
// Update types.ts
export interface WSMessage {
  type: 'auth' | 'message' | 'typing' | 'status' | 'online' | 'read' | 'error';
  payload: any;
}

export interface ReadReceiptPayload {
  messageIds: string[];
  to: string;
  readBy?: string;
}
```

## User Flow

### Scenario 1: Reading Messages
1. **Alice** sends a message to **Bob**
2. Message shows "sent" (✓) for Alice
3. Bob is online, message delivers, Alice sees "delivered" (✓✓ gray)
4. Bob opens the chat with Alice
5. Bob's messages are visible in viewport for 500ms
6. System marks messages as "read" automatically
7. WebSocket sends read receipt to Alice
8. Alice sees "read" status (✓✓ blue) in real-time

### Scenario 2: Bulk Read on Chat Open
1. **Alice** sends 5 messages to **Bob** while Bob is offline
2. Bob comes online and opens chat with Alice
3. All 5 messages become visible
4. After 500ms delay, all 5 messages marked as "read" in batch
5. Single WebSocket event sent with all 5 message IDs
6. Alice sees all 5 messages update to "read" status

### Scenario 3: Read Status Persistence
1. **Alice** sends message to **Bob**
2. Bob reads the message (shows blue checkmarks for Alice)
3. Alice closes and reopens the app
4. Alice logs back in and opens chat with Bob
5. Previously read message still shows blue checkmarks
6. Status is persisted in database

## Out of Scope
- Read receipt privacy settings (turn off read receipts)
- Group chat read receipts
- Read by multiple people indicators
- Timestamp of when message was read
- "Seen by" detailed information

## Dependencies
- Existing WebSocket infrastructure
- Current message status system
- Database message table

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance impact from frequent status updates | Medium | Medium | Batch read receipts, use debouncing |
| WebSocket message loss | High | Low | Fall back to polling API endpoint |
| Database write load | Medium | Medium | Async updates, batch operations |
| Race conditions on status updates | Medium | Medium | Use optimistic UI updates |
| Memory leak from observers | Low | Low | Proper cleanup in useEffect |

## Testing Criteria

### Unit Tests
- [ ] Read status detection logic
- [ ] Batch message ID collection
- [ ] WebSocket read message formatting
- [ ] Status icon rendering with different states
- [ ] Status persistence in message state

### Integration Tests
- [ ] Send read receipt via WebSocket
- [ ] Receive read receipt and update UI
- [ ] Database status update
- [ ] Multiple messages batch update
- [ ] Reconnection preserves read status

### E2E Tests
- [ ] User A sends message, User B reads it, User A sees blue checkmarks
- [ ] User opens chat with 10 unread messages, all marked read
- [ ] Read status persists after logout/login
- [ ] Read receipts work across browser tabs
- [ ] No read receipts shown on received messages

### Manual Testing Checklist
- [ ] Visual appearance matches WhatsApp style
- [ ] Smooth transition from delivered to read
- [ ] No flickering or UI jumps
- [ ] Works on slow network connections
- [ ] Works when multiple messages sent quickly
- [ ] Read status updates without page refresh

## UI/UX Mockups

### Message Status States

```
┌─────────────────────────────────┐
│ Sent Messages (Right-aligned)   │
├─────────────────────────────────┤
│  Hello there!            ✓      │ ← Sent (gray)
│                    10:23 AM      │
├─────────────────────────────────┤
│  How are you?           ✓✓      │ ← Delivered (gray)
│                    10:24 AM      │
├─────────────────────────────────┤
│  See you soon!          ✓✓      │ ← Read (blue)
│                    10:25 AM      │
└─────────────────────────────────┘
```

### Color Specifications
- **Sent (✓)**: #8696a0 (gray)
- **Delivered (✓✓)**: #8696a0 (gray)
- **Read (✓✓)**: #53bdeb (blue)

## Implementation Plan

### Phase 1: Frontend Foundation (2 hours)
1. Update Message type definitions
2. Modify getStatusIcon to include read state
3. Add CSS for blue read checkmarks
4. Update MessageList component

### Phase 2: Read Detection (3 hours)
1. Create useReadReceipt hook
2. Implement Intersection Observer for visibility
3. Add 500ms delay before marking as read
4. Integrate with App.tsx

### Phase 3: WebSocket Communication (2 hours)
1. Add 'read' message type to WebSocket
2. Implement sendReadReceipt function
3. Handle incoming read receipts
4. Update message state on receipt

### Phase 4: Backend Implementation (2 hours)
1. Add 'read' case to ChatRoom handler
2. Implement batch status update API
3. Update database schema if needed
4. Add logging for debugging

### Phase 5: Testing & Polish (3 hours)
1. Write unit tests
2. Perform integration testing
3. E2E testing with two users
4. Fix bugs and edge cases
5. Performance optimization

**Total Estimated Time**: 12 hours (1.5 days)

## Definition of Done
- [ ] All acceptance criteria met
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] No console errors
- [ ] Performance meets requirements (< 100ms status update)
- [ ] Works on Chrome, Firefox, Safari, Edge
- [ ] Deployed to development environment
- [ ] Product owner approval

## Notes
- Consider adding animation/transition for status changes
- May want to add sound notification when message is read
- Future enhancement: Show "Read at [timestamp]"
- Consider privacy implications (some users prefer to disable read receipts)

## Related Stories
- US-002: Read Receipt Privacy Settings
- US-003: Group Chat Read Receipts
- US-004: Message Reactions
- US-005: Message Delivery Notifications

## References
- WhatsApp read receipts behavior
- [Material Design - Status Indicators](https://material.io/)
- WebSocket RFC 6455
- Existing SRS document: `docs/SRS.md`

---

**Created**: 2025-12-11
**Last Updated**: 2025-12-11
**Author**: Development Team
**Status**: Ready for Development
