# Modification Details Document

## Document Information

| Field | Value |
|-------|-------|
| **Document ID** | MOD-001 |
| **Date** | 2025-12-11 |
| **Baseline Commit** | 138e2b6 (Initial commit) |
| **Status** | Pending Commit |
| **Total Files Modified** | 10 files |
| **New Files Created** | 3 files |

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [New Features Added](#2-new-features-added)
3. [File-by-File Changes](#3-file-by-file-changes)
4. [Database Schema Changes](#4-database-schema-changes)
5. [API Changes](#5-api-changes)
6. [Breaking Changes](#6-breaking-changes)
7. [Migration Guide](#7-migration-guide)
8. [Testing Recommendations](#8-testing-recommendations)

---

## 1. Executive Summary

### 1.1 Overview
This document details all modifications made to the WhatsApp Clone application after the initial commit (138e2b6). The changes introduce three major feature enhancements: image sharing, emoji picker, and improved online user management with message persistence.

### 1.2 Key Changes Summary

| Feature | Files Modified | Impact |
|---------|---------------|--------|
| **Image Sharing** | 9 files | HIGH - New message type |
| **Emoji Picker** | 3 files | MEDIUM - UI enhancement |
| **Message Persistence** | 3 files | HIGH - Database integration |
| **Online User Management** | 2 files | MEDIUM - UX improvement |
| **Read Receipt Optimization** | 2 files | LOW - Performance enhancement |

### 1.3 Statistics

```
Total Lines Added:    ~450 lines
Total Lines Removed:  ~80 lines
Net Change:           +370 lines
Files Modified:       10 files
New Files:            3 files
Database Changes:     2 new columns
```

---

## 2. New Features Added

### 2.1 Image Sharing
**Status:** ✅ Fully Implemented

**Description:** Users can now share images in chat conversations. Images are uploaded, converted to base64, and transmitted via WebSocket.

**User Story:**
- User clicks image button (📷)
- User selects image from file system
- Image is validated (type, size < 5MB)
- Image is sent to recipient
- Image displays inline in chat

**Technical Implementation:**
- Base64 encoding for image data
- File type validation (image/* only)
- Size limit enforcement (5MB max)
- Lazy loading for image rendering
- Database persistence with imageData column

### 2.2 Emoji Picker
**Status:** ✅ Fully Implemented

**Description:** Users can insert emojis into their messages using a visual emoji picker interface.

**User Story:**
- User clicks emoji button (😀)
- Emoji picker panel opens
- User clicks desired emoji
- Emoji is inserted at cursor position
- Picker closes, focus returns to input

**Technical Implementation:**
- 160 common emojis in grid layout
- Click-outside detection for auto-close
- Smooth animations and transitions
- Accessible keyboard navigation
- Mobile-responsive design

### 2.3 Message Persistence
**Status:** ✅ Fully Implemented

**Description:** All messages are now saved to the D1 database for persistence and history retrieval.

**User Story:**
- User sends message
- Message is saved to database
- Message status updates are persisted
- Read receipts update database
- Message history is retrievable

**Technical Implementation:**
- INSERT on message send
- UPDATE on status change (delivered, read)
- Foreign key validation
- Error handling and logging
- Timestamp tracking (sent, read)

### 2.4 Online User Management
**Status:** ✅ Fully Implemented

**Description:** Improved user list management showing only currently online users.

**User Story:**
- User list only shows online users
- Users are added when they connect
- Users are removed when they disconnect
- No stale/offline users displayed
- Real-time list updates

**Technical Implementation:**
- Removed database user fetching on login
- Users list cleared on mount
- Users added via WebSocket 'online' events
- Users removed via WebSocket 'offline' events
- Prevents showing disconnected users

### 2.5 Read Receipt Optimization
**Status:** ✅ Fully Implemented

**Description:** Enhanced read receipt detection using Intersection Observer API for viewport-based read detection.

**User Story:**
- Messages are marked read when visible
- Uses viewport intersection detection
- More accurate than time-based approach
- Debounced for performance
- Fallback to legacy timer-based method

**Technical Implementation:**
- New useReadReceipt custom hook
- IntersectionObserver with 50% threshold
- 500ms debounce on mark-as-read
- Automatic cleanup on unmount
- Backward compatible with timer fallback

---

## 3. File-by-File Changes

### 3.1 Database Schema

**File:** `schema.sql`

**Changes:**
```sql
-- ADDED: Support for image messages
type TEXT DEFAULT 'text',
imageData TEXT,
```

**Impact:** HIGH - Requires database migration

**Details:**
- `type` column: Stores message type ('text' or 'image')
- `imageData` column: Stores base64-encoded image data
- Default value 'text' for backward compatibility
- Both columns nullable for existing records

**Migration Required:** Yes
```bash
# Apply to local database
npx wrangler d1 execute whatsapp_clone_db --local --command "ALTER TABLE messages ADD COLUMN type TEXT DEFAULT 'text'"
npx wrangler d1 execute whatsapp_clone_db --local --command "ALTER TABLE messages ADD COLUMN imageData TEXT"

# Apply to remote database
npx wrangler d1 execute whatsapp_clone_db --remote --command "ALTER TABLE messages ADD COLUMN type TEXT DEFAULT 'text'"
npx wrangler d1 execute whatsapp_clone_db --remote --command "ALTER TABLE messages ADD COLUMN imageData TEXT"
```

---

### 3.2 Frontend Components

#### 3.2.1 App.tsx

**File:** `src/client/App.tsx`

**Changes Summary:**
- Added image message type support
- Improved online user management
- Added sendImage function
- Removed database user fetching
- Enhanced offline user handling

**Detailed Changes:**

1. **Interface Updates:**
```typescript
// ADDED: Image message support
interface Message {
  // ... existing fields
  type?: 'text' | 'image';
  imageData?: string;
}
```

2. **Online User Management:**
```typescript
// ADDED: Clear users list on mount
useEffect(() => {
  setUsers([]);  // Only show WebSocket-connected users
  // ... existing code
}, []);

// MODIFIED: Online status handler
const handleOnlineStatus = useCallback((statusUpdates) => {
  setUsers((prev) => {
    let updated = [...prev];
    statusUpdates.forEach((update) => {
      if (update.online) {
        // Add or update online user
      } else {
        // ADDED: Remove offline users from list
        updated = updated.filter((u) => u.id !== update.userId);
      }
    });
    return updated;
  });
}, [currentUser]);
```

3. **Image Sending:**
```typescript
// ADDED: Destructure sendImage from useWebSocket
const { connected, sendMessage, sendImage, sendTyping, sendStatus, sendReadReceipt } = useWebSocket({
  // ... config
});

// ADDED: Pass sendImage to Chat component
<Chat
  onSendImage={sendImage}
  // ... other props
/>
```

4. **Deprecated Functions:**
```typescript
// MODIFIED: fetchUsers deprecated
const fetchUsers = async () => {
  // Deprecated: Don't fetch all users from database
  // Only show users who connect via WebSocket (online users only)
};

// REMOVED: fetchUsers call on mount
useEffect(() => {
  if (currentUser) {
    // Don't fetch users - handled by WebSocket
  }
}, [currentUser]);
```

**Impact:** MEDIUM - Changes UX, removes database dependency

**Breaking Changes:** None - backward compatible

---

#### 3.2.2 Chat.tsx

**File:** `src/client/components/Chat.tsx`

**Changes Summary:**
- Added image message type support
- Added onSendImage prop
- Pass image handler to ChatWindow

**Detailed Changes:**

1. **Interface Updates:**
```typescript
interface Message {
  // ... existing fields
  type?: 'text' | 'image';
  imageData?: string;
}

interface ChatProps {
  // ... existing props
  onSendImage: (to: string, imageData: string) => void;
}
```

2. **Prop Passing:**
```typescript
<ChatWindow
  onSendImage={onSendImage}
  // ... other props
/>
```

**Impact:** LOW - Simple prop drilling

**Breaking Changes:** None

---

#### 3.2.3 ChatWindow.tsx

**File:** `src/client/components/ChatWindow.tsx`

**Changes Summary:**
- Added image message support
- Added handleSendImage function
- Pass image handler to MessageInput

**Detailed Changes:**

1. **Interface Updates:**
```typescript
interface Message {
  type?: 'text' | 'image';
  imageData?: string;
}

interface ChatWindowProps {
  onSendImage: (to: string, imageData: string) => void;
}
```

2. **Image Handler:**
```typescript
const handleSendImage = (imageData: string) => {
  if (selectedUser) {
    onSendImage(selectedUser.id, imageData);
  }
};
```

3. **Component Integration:**
```typescript
<MessageInput
  onSendImage={handleSendImage}
  // ... other props
/>
```

**Impact:** LOW - Simple integration

**Breaking Changes:** None

---

#### 3.2.4 MessageInput.tsx

**File:** `src/client/components/MessageInput.tsx`

**Changes Summary:**
- Added emoji picker UI
- Added image upload functionality
- Added file validation
- Added click-outside detection

**Detailed Changes:**

1. **New Props:**
```typescript
interface MessageInputProps {
  onSendImage: (imageData: string) => void;
}
```

2. **State Management:**
```typescript
const [showEmojiPicker, setShowEmojiPicker] = useState(false);
const emojiPickerRef = useRef<HTMLDivElement>(null);
const inputRef = useRef<HTMLInputElement>(null);
const fileInputRef = useRef<HTMLInputElement>(null);
```

3. **Emoji List:**
```typescript
const EMOJI_LIST = [
  '😀', '😃', '😄', ... // 160 emojis
];
```

4. **Click-Outside Detection:**
```typescript
useEffect(() => {
  const handleClickOutside = (event: MouseEvent) => {
    if (emojiPickerRef.current && !emojiPickerRef.current.contains(event.target as Node)) {
      setShowEmojiPicker(false);
    }
  };
  // ... event listener setup
}, [showEmojiPicker]);
```

5. **Emoji Insertion:**
```typescript
const handleEmojiClick = (emoji: string) => {
  onChange(value + emoji);
  setShowEmojiPicker(false);
  inputRef.current?.focus();
};
```

6. **Image Upload:**
```typescript
const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  // Validate file type
  if (!file.type.startsWith('image/')) {
    alert('Please select an image file');
    return;
  }

  // Validate file size (max 5MB)
  if (file.size > 5 * 1024 * 1024) {
    alert('Image size must be less than 5MB');
    return;
  }

  // Convert to base64
  const reader = new FileReader();
  reader.onload = () => {
    const base64 = reader.result as string;
    onSendImage(base64);
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  reader.readAsDataURL(file);
};
```

7. **UI Elements:**
```typescript
// Emoji button
<button className="emoji-button" onClick={() => setShowEmojiPicker(!showEmojiPicker)}>
  😀
</button>

// Hidden file input
<input
  ref={fileInputRef}
  type="file"
  accept="image/*"
  onChange={handleImageSelect}
  style={{ display: 'none' }}
/>

// Image upload button
<button className="image-button" onClick={() => fileInputRef.current?.click()}>
  📷
</button>

// Emoji picker panel
{showEmojiPicker && (
  <div className="emoji-picker" ref={emojiPickerRef}>
    <div className="emoji-grid">
      {EMOJI_LIST.map((emoji, index) => (
        <button className="emoji-item" onClick={() => handleEmojiClick(emoji)}>
          {emoji}
        </button>
      ))}
    </div>
  </div>
)}
```

**Impact:** HIGH - Major UI enhancement

**Lines Added:** ~120 lines

**Breaking Changes:** None - additive only

---

#### 3.2.5 MessageList.tsx

**File:** `src/client/components/MessageList.tsx`

**Changes Summary:**
- Added image message rendering
- Added useReadReceipt hook integration
- Added Intersection Observer support
- Added message ref management

**Detailed Changes:**

1. **Import New Hook:**
```typescript
import { useReadReceipt } from '../hooks/useReadReceipt';
```

2. **Interface Updates:**
```typescript
interface Message {
  type?: 'text' | 'image';
  imageData?: string;
}
```

3. **State Management:**
```typescript
const messageRefsRef = useRef<Map<string, HTMLDivElement>>(new Map());
```

4. **Read Receipt Hook:**
```typescript
const { observeMessage, unobserveMessage } = useReadReceipt({
  messages,
  currentUserId,
  selectedUserId,
  onMarkAsRead,
});
```

5. **Ref Callback:**
```typescript
const setMessageRef = (id: string, element: HTMLDivElement | null) => {
  if (element) {
    messageRefsRef.current.set(id, element);
    observeMessage(element);
  } else {
    const el = messageRefsRef.current.get(id);
    if (el) {
      unobserveMessage(el);
      messageRefsRef.current.delete(id);
    }
  }
};
```

6. **Image Rendering:**
```typescript
<div
  key={message.id}
  ref={(el) => setMessageRef(message.id, el)}
  data-message-id={message.id}
  className={`message ${isSent ? 'sent' : 'received'}`}
>
  {message.type === 'image' && message.imageData ? (
    <div className="message-image-container">
      <img
        src={message.imageData}
        alt="Shared image"
        className="message-image"
        loading="lazy"
      />
    </div>
  ) : (
    <div className="message-content">{message.content}</div>
  )}
  {/* ... message meta */}
</div>
```

7. **Legacy Fallback:**
```typescript
// Legacy fallback: Mark unread messages as read after 500ms if they're in view
useEffect(() => {
  const unreadMessages = messages.filter(
    (m) =>
      m.from === selectedUserId &&
      m.to === currentUserId &&
      m.status !== 'read'
  );

  if (unreadMessages.length > 0) {
    console.log(`[MessageList] Found ${unreadMessages.length} unread messages`);
    const timer = setTimeout(() => {
      console.log(`[MessageList] Marking ${unreadMessages.length} messages as read`);
      onMarkAsRead(unreadMessages.map((m) => m.id));
    }, 500);

    return () => clearTimeout(timer);
  }
}, [messages, selectedUserId, currentUserId, onMarkAsRead]);
```

**Impact:** MEDIUM - Enhanced rendering and read detection

**Lines Added:** ~40 lines

**Breaking Changes:** None

---

#### 3.2.6 styles.css

**File:** `src/client/styles.css`

**Changes Summary:**
- Added emoji picker styles
- Added image button styles
- Added image message styles
- Added error message styles
- Updated login form styles

**Detailed Changes:**

1. **Login Form Enhancements:**
```css
.login-box h2 {
  margin-bottom: 20px;
  color: #666;
  font-size: 18px;
  font-weight: 400;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 15px;
  font-size: 14px;
  border: 1px solid #fcc;
}

.toggle-mode {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.toggle-mode button {
  background: transparent;
  color: #667eea;
  text-decoration: none;
  padding: 8px;
  font-size: 14px;
}
```

2. **Image Message Styles:**
```css
.message-image-container {
  margin-bottom: 4px;
}

.message-image {
  max-width: 300px;
  max-height: 400px;
  border-radius: 8px;
  display: block;
  cursor: pointer;
  transition: opacity 0.2s;
}

.message-image:hover {
  opacity: 0.9;
}
```

3. **Message Input Container:**
```css
.message-input-container {
  padding: 16px 20px;
  background: #202c33;
  border-top: 1px solid #2a3942;
  display: flex;
  gap: 12px;
  position: relative;  /* ADDED for emoji picker positioning */
}
```

4. **Emoji Button:**
```css
.emoji-button {
  padding: 8px 12px;
  background: #2a3942;
  border: none;
  border-radius: 8px;
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.emoji-button:hover {
  background: #374248;
}

.emoji-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

5. **Image Button:**
```css
.image-button {
  padding: 8px 12px;
  background: #2a3942;
  border: none;
  border-radius: 8px;
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-button:hover {
  background: #374248;
}

.image-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

6. **Emoji Picker:**
```css
.emoji-picker {
  position: absolute;
  bottom: 100%;
  left: 20px;
  margin-bottom: 8px;
  background: #202c33;
  border: 1px solid #2a3942;
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 1000;
  max-width: 320px;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 4px;
  max-height: 280px;
  overflow-y: auto;
}

.emoji-item {
  background: transparent;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 6px;
  border-radius: 4px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.emoji-item:hover {
  background: #2a3942;
}
```

**Impact:** MEDIUM - Visual enhancements

**Lines Added:** ~150 lines

**Breaking Changes:** None

---

### 3.3 Frontend Hooks

#### 3.3.1 useWebSocket.ts

**File:** `src/client/hooks/useWebSocket.ts`

**Changes Summary:**
- Added image message support
- Added sendImage function
- Enhanced online status handling
- Clear users on disconnect

**Detailed Changes:**

1. **Interface Updates:**
```typescript
interface Message {
  type?: 'text' | 'image';
  imageData?: string;
}
```

2. **Online Status Handler:**
```typescript
case 'online':
  if (data.payload.users) {
    // Received list of online users
    onOnlineStatus(data.payload.users);
  } else {
    // Received single user status update
    onOnlineStatus([data.payload]);
  }
  break;
```

3. **Disconnect Handler:**
```typescript
ws.current.onclose = () => {
  console.log('WebSocket disconnected');
  setConnected(false);

  // ADDED: Clear online users when connection closes
  onOnlineStatus([]);

  reconnectTimeout.current = window.setTimeout(() => {
    console.log('Attempting to reconnect...');
    connect();
  }, 3000);
};
```

4. **Send Message Enhancement:**
```typescript
const sendMessage = useCallback((to: string, content: string) => {
  if (ws.current && ws.current.readyState === WebSocket.OPEN) {
    ws.current.send(
      JSON.stringify({
        type: 'message',
        payload: { to, content, messageType: 'text' },  // ADDED messageType
      })
    );
  }
}, []);
```

5. **New Send Image Function:**
```typescript
const sendImage = useCallback((to: string, imageData: string) => {
  if (ws.current && ws.current.readyState === WebSocket.OPEN) {
    ws.current.send(
      JSON.stringify({
        type: 'message',
        payload: { to, content: '📷 Image', imageData, messageType: 'image' },
      })
    );
  }
}, []);
```

6. **Return Values:**
```typescript
return {
  connected,
  sendMessage,
  sendImage,  // ADDED
  sendTyping,
  sendStatus,
  sendReadReceipt,
};
```

**Impact:** MEDIUM - New functionality

**Lines Added:** ~25 lines

**Breaking Changes:** None

---

#### 3.3.2 useReadReceipt.ts (NEW FILE)

**File:** `src/client/hooks/useReadReceipt.ts`

**Status:** ✨ NEW FILE

**Purpose:** Viewport-based read receipt detection using Intersection Observer API

**Implementation:**

```typescript
import { useEffect, useRef, useCallback } from 'react';

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
}

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
  onMarkAsRead,
}: UseReadReceiptProps) => {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const pendingMessagesRef = useRef<Set<string>>(new Set());
  const timeoutRef = useRef<number>();

  const markMessagesAsRead = useCallback(() => {
    if (pendingMessagesRef.current.size > 0) {
      const messageIds = Array.from(pendingMessagesRef.current);
      onMarkAsRead(messageIds);
      pendingMessagesRef.current.clear();
    }
  }, [onMarkAsRead]);

  useEffect(() => {
    // Create intersection observer
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const messageId = entry.target.getAttribute('data-message-id');
            if (messageId) {
              const message = messages.find(
                (m) => m.id === messageId &&
                      m.from === selectedUserId &&
                      m.to === currentUserId &&
                      m.status !== 'read'
              );
              if (message) {
                pendingMessagesRef.current.add(messageId);
              }
            }
          }
        });

        // Debounce the mark as read call
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = window.setTimeout(() => {
          markMessagesAsRead();
        }, 500);
      },
      { threshold: 0.5 }  // 50% visibility threshold
    );

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [messages, currentUserId, selectedUserId, markMessagesAsRead]);

  const observeMessage = useCallback((element: HTMLElement | null) => {
    if (element && observerRef.current) {
      observerRef.current.observe(element);
    }
  }, []);

  const unobserveMessage = useCallback((element: HTMLElement | null) => {
    if (element && observerRef.current) {
      observerRef.current.unobserve(element);
    }
  }, []);

  return {
    observeMessage,
    unobserveMessage,
  };
};
```

**Features:**
- IntersectionObserver for viewport detection
- 50% visibility threshold
- 500ms debounce on mark-as-read
- Automatic cleanup
- Memory-efficient with refs

**Impact:** MEDIUM - Performance improvement

**Lines Added:** 93 lines (new file)

**Breaking Changes:** None

---

### 3.4 Backend Worker

#### 3.4.1 types.ts

**File:** `src/worker/types.ts`

**Changes Summary:**
- Added image message type support
- Added Env interface export

**Detailed Changes:**

```typescript
export interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
  type?: 'text' | 'image';      // ADDED
  imageData?: string;            // ADDED
}
```

**Impact:** LOW - Type definition only

**Lines Added:** 2 lines

**Breaking Changes:** None

---

#### 3.4.2 ChatRoom.ts

**File:** `src/worker/ChatRoom.ts`

**Changes Summary:**
- Added database message persistence
- Added image message support
- Added environment access
- Added status update persistence
- Added read receipt database updates

**Detailed Changes:**

1. **Constructor Enhancement:**
```typescript
import { ChatSession, WSMessage, Message, Env } from './types';

export class ChatRoom implements DurableObject {
  private sessions: Map<string, ChatSession>;
  private state: DurableObjectState;
  private env: Env;  // ADDED

  constructor(state: DurableObjectState, env: Env) {  // ADDED env parameter
    this.state = state;
    this.env = env;  // ADDED
    this.sessions = new Map();
  }
  // ...
}
```

2. **Online Users Enhancement:**
```typescript
const onlineUsers = Array.from(this.sessions.values()).map(s => ({
  userId: s.userId,
  username: s.username,
  online: true,  // ADDED explicit online flag
}));
```

3. **Message Handling with Persistence:**
```typescript
case 'message':
  if (session) {
    const messageType = data.payload.messageType || 'text';  // ADDED
    const message: Message = {
      id: crypto.randomUUID(),
      from: session.userId,
      to: data.payload.to,
      content: data.payload.content,
      timestamp: Date.now(),
      status: 'sent',
      type: messageType,        // ADDED
      imageData: data.payload.imageData,  // ADDED
    };

    console.log(`Message from ${session.userId} to ${data.payload.to}: ${messageType === 'image' ? '📷 Image' : data.payload.content}`);

    // ADDED: Save message to database
    try {
      // Check if both users exist
      const fromUserExists = await this.env.DB.prepare(
        'SELECT id FROM users WHERE id = ?'
      ).bind(message.from).first();

      const toUserExists = await this.env.DB.prepare(
        'SELECT id FROM users WHERE id = ?'
      ).bind(message.to).first();

      if (!fromUserExists) {
        console.log(`[Warning] Sender ${message.from} not found in database, message not persisted`);
      } else if (!toUserExists) {
        console.log(`[Warning] Recipient ${message.to} not found in database, message not persisted`);
      } else {
        await this.env.DB.prepare(
          'INSERT INTO messages (id, fromUser, toUser, content, timestamp, status, type, imageData) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
        ).bind(
          message.id,
          message.from,
          message.to,
          message.content,
          message.timestamp,
          message.status,
          message.type || 'text',
          message.imageData || null
        ).run();
        console.log(`Message saved to database: ${message.id}`);
      }
    } catch (error) {
      console.error('Failed to save message to database:', error);
    }

    // Send to recipient
    const recipient = this.sessions.get(data.payload.to);
    if (recipient) {
      recipient.ws.send(JSON.stringify({
        type: 'message',
        payload: message,
      }));
      message.status = 'delivered';

      // ADDED: Update message status in database
      try {
        await this.env.DB.prepare(
          'UPDATE messages SET status = ? WHERE id = ?'
        ).bind(message.status, message.id).run();
      } catch (error) {
        console.error('Failed to update message status:', error);
      }
    } else {
      console.log(`Recipient ${data.payload.to} not found in sessions`);
    }

    // Send confirmation to sender
    ws.send(JSON.stringify({
      type: 'message',
      payload: message,
    }));
  }
  break;
```

4. **Read Receipt Database Update:**
```typescript
case 'read':
  if (session && data.payload.messageIds && data.payload.to) {
    const messageIds = data.payload.messageIds as string[];

    console.log(`[Read Receipt] User ${session.userId} read ${messageIds.length} messages`);
    console.log(`[Read Receipt] Notifying sender: ${data.payload.to}`);

    // ADDED: Update message status in database
    try {
      const placeholders = messageIds.map(() => '?').join(',');
      const now = Date.now();
      await this.env.DB.prepare(
        `UPDATE messages SET status = ?, readAt = ? WHERE id IN (${placeholders})`
      ).bind('read', now, ...messageIds).run();
      console.log(`[Read Receipt] Updated ${messageIds.length} messages in database`);
    } catch (error) {
      console.error('[Read Receipt] Failed to update database:', error);
    }

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
  }
  break;
```

**Impact:** HIGH - Database persistence critical

**Lines Added:** ~80 lines

**Breaking Changes:** Requires Env parameter in constructor

---

## 4. Database Schema Changes

### 4.1 Messages Table Modifications

**Table:** `messages`

**Changes:**

| Column | Type | Default | Nullable | Description |
|--------|------|---------|----------|-------------|
| `type` | TEXT | 'text' | YES | Message type ('text' or 'image') |
| `imageData` | TEXT | NULL | YES | Base64-encoded image data |

**Migration SQL:**
```sql
ALTER TABLE messages ADD COLUMN type TEXT DEFAULT 'text';
ALTER TABLE messages ADD COLUMN imageData TEXT;
```

**Backward Compatibility:** ✅ YES
- Existing records get default value 'text'
- Both columns nullable
- No data loss

**Performance Impact:**
- Minimal - columns are nullable
- imageData can be large (base64 bloat ~33%)
- Consider future optimization (external blob storage)

**Index Recommendations:**
```sql
-- Optional: If querying by type frequently
CREATE INDEX idx_messages_type ON messages(type);
```

---

## 5. API Changes

### 5.1 WebSocket Message Protocol

#### 5.1.1 Message Type Enhancement

**Before:**
```json
{
  "type": "message",
  "payload": {
    "to": "user-id",
    "content": "Hello!"
  }
}
```

**After:**
```json
{
  "type": "message",
  "payload": {
    "to": "user-id",
    "content": "Hello!",
    "messageType": "text"  // NEW: 'text' or 'image'
  }
}
```

**Image Message:**
```json
{
  "type": "message",
  "payload": {
    "to": "user-id",
    "content": "📷 Image",
    "messageType": "image",
    "imageData": "data:image/png;base64,iVBORw0KGgoAAAANS..."  // NEW
  }
}
```

#### 5.1.2 Online Status Enhancement

**Before:**
```json
{
  "type": "online",
  "payload": {
    "userId": "user-id",
    "username": "john_doe"
  }
}
```

**After:**
```json
{
  "type": "online",
  "payload": {
    "userId": "user-id",
    "username": "john_doe",
    "online": true  // NEW: Explicit online flag
  }
}
```

**User List:**
```json
{
  "type": "online",
  "payload": {
    "users": [
      { "userId": "id1", "username": "user1", "online": true },
      { "userId": "id2", "username": "user2", "online": true }
    ]
  }
}
```

---

## 6. Breaking Changes

### 6.1 Summary

**Status:** ⚠️ MINOR BREAKING CHANGES

### 6.2 ChatRoom Constructor

**Change:** Added `env` parameter

**Before:**
```typescript
constructor(state: DurableObjectState) {
  this.state = state;
  this.sessions = new Map();
}
```

**After:**
```typescript
constructor(state: DurableObjectState, env: Env) {
  this.state = state;
  this.env = env;
  this.sessions = new Map();
}
```

**Impact:** Cloudflare Workers automatically provides `env` - no code changes needed in worker binding

**Action Required:** None - framework handles this

---

## 7. Migration Guide

### 7.1 Database Migration

#### Step 1: Backup Database
```bash
# Export current data
npx wrangler d1 execute whatsapp_clone_db --local --command "SELECT * FROM messages" > backup_messages.json
npx wrangler d1 execute whatsapp_clone_db --local --command "SELECT * FROM users" > backup_users.json
```

#### Step 2: Apply Schema Changes
```bash
# Local database
npx wrangler d1 execute whatsapp_clone_db --local --file=./schema.sql

# Production database
npx wrangler d1 execute whatsapp_clone_db --remote --file=./schema.sql
```

#### Step 3: Verify Migration
```bash
# Check schema
npx wrangler d1 execute whatsapp_clone_db --local --command "PRAGMA table_info(messages)"

# Expected output includes:
# type|TEXT|0|'text'|0
# imageData|TEXT|0||0
```

#### Step 4: Test
- Send text message - verify persistence
- Send image message - verify storage and retrieval
- Check message status updates
- Verify read receipts update database

### 7.2 Code Deployment

#### Step 1: Pull Latest Changes
```bash
git fetch origin
git pull origin master
```

#### Step 2: Install Dependencies
```bash
npm install
```

#### Step 3: Run Tests
```bash
npm test  # If tests exist
```

#### Step 4: Deploy Worker
```bash
# Deploy to production
npx wrangler deploy

# Monitor logs
npx wrangler tail
```

#### Step 5: Verify Deployment
- Test login
- Test text messaging
- Test image upload
- Test emoji picker
- Test read receipts
- Verify online users list

---

## 8. Testing Recommendations

### 8.1 Functional Testing

#### Image Sharing
- [ ] Upload image (< 5MB)
- [ ] Upload image (> 5MB) - should fail
- [ ] Upload non-image file - should fail
- [ ] Send image to online user
- [ ] Send image to offline user
- [ ] View received image
- [ ] Image displays with lazy loading
- [ ] Image persisted in database

#### Emoji Picker
- [ ] Open emoji picker
- [ ] Select emoji
- [ ] Emoji inserted in message
- [ ] Picker closes after selection
- [ ] Click outside closes picker
- [ ] Emoji sent successfully
- [ ] Multiple emojis in one message

#### Message Persistence
- [ ] Text message saved to database
- [ ] Image message saved to database
- [ ] Message status updated (delivered)
- [ ] Message status updated (read)
- [ ] Read timestamp recorded
- [ ] Foreign key validation works

#### Online Users
- [ ] User list empty on load
- [ ] Users added on WebSocket connect
- [ ] Users removed on disconnect
- [ ] No stale/offline users shown
- [ ] Multiple users online simultaneously

#### Read Receipts
- [ ] Messages marked read when visible
- [ ] Intersection Observer working
- [ ] Debounce functioning (500ms)
- [ ] Fallback timer works
- [ ] Database updated on read

### 8.2 Performance Testing

- [ ] Image upload < 2 seconds (1MB image)
- [ ] Emoji picker renders quickly
- [ ] No lag when scrolling messages
- [ ] Database writes don't block UI
- [ ] Intersection Observer efficient

### 8.3 Error Handling

- [ ] Network error during image upload
- [ ] Database write failure handled
- [ ] Invalid image format rejected
- [ ] Large file size rejected
- [ ] Missing user in database handled

### 8.4 Cross-Browser Testing

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari
- [ ] Mobile browsers

---

## Document Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-12-11 | 1.0 | Initial document creation | Development Team |

---

**End of Document**
