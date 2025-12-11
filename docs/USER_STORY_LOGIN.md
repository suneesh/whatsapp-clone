# User Story: User Login

## Story Overview

**As a** user wanting to use the chat application
**I want to** log in with a username
**So that** I can identify myself and start chatting with other users

## Story Details

**Story ID:** US-002
**Epic:** User Authentication & Identity
**Priority:** P0 (Critical)
**Story Points:** 3
**Status:** Implemented

## Acceptance Criteria

### AC1: Username Input Form
**Given** a user visits the application for the first time
**When** they see the login screen
**Then** they should see:
- A welcoming heading with the application name
- A text input field for entering their username
- A "Login" button to submit
- The form should have an attractive, modern design

### AC2: Username Validation
**Given** a user is on the login screen
**When** they attempt to log in
**Then** the system should validate:
- Username is not empty (after trimming whitespace)
- Username meets minimum length requirements
- Button should be disabled if username is invalid
- Button should be enabled when username is valid

### AC3: New User Registration
**Given** a user enters a username that doesn't exist in the system
**When** they click the Login button
**Then** the system should:
- Create a new user account with a unique UUID
- Store the user information in the database (id, username, avatar, lastSeen)
- Set the lastSeen timestamp to the current time
- Return the user object with all required fields
- Automatically log the user into the application
- Show the main chat interface

### AC4: Existing User Login
**Given** a user enters a username that already exists in the system
**When** they click the Login button
**Then** the system should:
- Retrieve the existing user account from the database
- Update the lastSeen timestamp to the current time
- Return the existing user object (preserving the original UUID)
- Log the user into the application
- Show the main chat interface with previous chat history

### AC5: Login State Persistence
**Given** a user has successfully logged in
**When** they refresh the page or close and reopen the browser
**Then** the system should:
- Remember their login state (using localStorage)
- Automatically log them back in without requiring re-entry of username
- Restore their user session

### AC6: Loading States
**Given** a user clicks the Login button
**When** the system is processing the login request
**Then** the system should:
- Disable the Login button to prevent double-submission
- Show visual feedback that processing is occurring
- Handle the login within a reasonable timeframe (< 2 seconds typical)

### AC7: Error Handling
**Given** a user attempts to log in
**When** an error occurs (network failure, server error, etc.)
**Then** the system should:
- Display a user-friendly error message
- Keep the login form accessible for retry
- Not store incomplete or invalid user data
- Log the error for debugging purposes

### AC8: Username Uniqueness
**Given** multiple users try to log in with the same username
**When** they submit the login form
**Then** the system should:
- Allow all users to log in with the same username
- Treat them as the same user (share the same UUID)
- Update the lastSeen timestamp for each login
- Show consistent user identity across sessions

## Technical Requirements

### Frontend Components

#### Login Component (`src/client/components/Login.tsx`)
```typescript
interface LoginProps {
  onLogin: (username: string) => void;
}

function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (username.trim()) {
      onLogin(username.trim());
    }
  };

  // Render login form with username input and submit button
}
```

#### App Component Integration (`src/client/App.tsx`)
- Manage authentication state (currentUser)
- Store user data in localStorage
- Retrieve user from localStorage on mount
- Handle login/logout operations
- Conditionally render Login or Chat component based on auth state

### Backend API

#### Endpoint: POST /api/users

**Request:**
```json
{
  "username": "john_doe"
}
```

**Response (New User):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "lastSeen": 1699564800000
}
```

**Response (Existing User):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "lastSeen": 1699568400000
}
```

**Status Codes:**
- 200: Existing user login successful
- 201: New user created and logged in
- 400: Invalid request (missing username)
- 500: Server error

### Database Schema

#### Users Table
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  avatar TEXT,
  lastSeen INTEGER NOT NULL
);

CREATE INDEX idx_users_username ON users(username);
```

### Data Flow

1. **User enters username and clicks Login**
   - Frontend validates input
   - Sends POST request to `/api/users` with username

2. **Backend processes login**
   - Queries database for existing user by username
   - If found: Updates lastSeen, returns existing user
   - If not found: Creates new user with UUID, returns new user

3. **Frontend receives response**
   - Stores user object in component state
   - Stores user object in localStorage for persistence
   - Transitions to main chat interface

4. **WebSocket connection established**
   - Frontend automatically connects WebSocket
   - Sends 'auth' message with userId and username
   - Server registers user as online

## UI/UX Design

### Login Screen Layout
```
┌─────────────────────────────────────────┐
│                                         │
│          [Gradient Background]          │
│                                         │
│         ┌─────────────────┐            │
│         │   WhatsApp      │            │
│         │     Clone       │            │
│         │                 │            │
│         │  ┌───────────┐  │            │
│         │  │ Username  │  │            │
│         │  └───────────┘  │            │
│         │                 │            │
│         │  [Login Button] │            │
│         │                 │            │
│         └─────────────────┘            │
│                                         │
└─────────────────────────────────────────┘
```

### Design Specifications
- **Background:** Linear gradient (purple/blue theme)
- **Login Box:** White background, rounded corners, shadow
- **Input Field:** Border, focus state with color change
- **Button:** Gradient background, hover effect, disabled state
- **Typography:** Modern, clean sans-serif font
- **Responsive:** Center-aligned, works on all screen sizes

## Non-Functional Requirements

### Performance
- Login process should complete within 2 seconds under normal conditions
- Database query should be optimized with index on username field
- Frontend should show immediate feedback on button click

### Security
- Username input should be sanitized on backend
- Prevent SQL injection with parameterized queries
- Rate limiting on login endpoint to prevent abuse
- No sensitive data stored in localStorage (no passwords)

### Reliability
- Handle network failures gracefully
- Retry logic for failed API calls
- Database connection pooling for high concurrency
- Atomic database operations (create or update)

### Usability
- Clear, intuitive interface
- Immediate visual feedback on interactions
- Error messages should be user-friendly
- Accessible via keyboard (Enter key to submit)

## Edge Cases & Error Scenarios

### Edge Case 1: Empty Username
**Scenario:** User clicks Login with empty username field
**Expected:** Button should be disabled, preventing submission

### Edge Case 2: Whitespace-only Username
**Scenario:** User enters only spaces and clicks Login
**Expected:** Frontend trims whitespace, treats as empty, prevents submission

### Edge Case 3: Network Failure During Login
**Scenario:** Network disconnects while login request is in flight
**Expected:** Show error message, allow user to retry

### Edge Case 4: Database Connection Failure
**Scenario:** Database is unavailable when user tries to log in
**Expected:** Return 500 error, show user-friendly message, log error

### Edge Case 5: Concurrent Logins
**Scenario:** Same user logs in from multiple devices simultaneously
**Expected:** Both succeed, both get same UUID, last login updates lastSeen

### Edge Case 6: Special Characters in Username
**Scenario:** User enters username with special characters (emoji, symbols)
**Expected:** System accepts valid Unicode characters, stores correctly

### Edge Case 7: Very Long Username
**Scenario:** User enters extremely long username (>100 characters)
**Expected:** System should enforce reasonable length limit

## Testing Strategy

### Unit Tests

#### Frontend Tests
- ✅ Login component renders correctly
- ✅ Username input updates state
- ✅ Form submission calls onLogin with trimmed username
- ✅ Button is disabled when username is empty
- ✅ Button is enabled when username is valid
- ✅ Form submission is prevented when username is empty

#### Backend Tests
- ✅ POST /api/users creates new user when username doesn't exist
- ✅ POST /api/users returns existing user when username exists
- ✅ lastSeen timestamp is updated on existing user login
- ✅ UUID is preserved for existing users
- ✅ Invalid requests return 400 status
- ✅ Server errors return 500 status

### Integration Tests
- ✅ End-to-end login flow for new user
- ✅ End-to-end login flow for existing user
- ✅ User data persists in localStorage after login
- ✅ User is automatically logged in on page refresh
- ✅ WebSocket connection establishes after login
- ✅ User appears as online to other users after login

### Manual Testing Checklist
- [ ] Login with new username creates account
- [ ] Login with existing username logs in successfully
- [ ] Username persists after page refresh
- [ ] Multiple tabs with same user work correctly
- [ ] Network error shows appropriate message
- [ ] Login button disabled state works correctly
- [ ] Keyboard navigation (Tab, Enter) works
- [ ] Mobile responsive design works

## Dependencies

### Technical Dependencies
- React 18+ (useState, useEffect, FormEvent)
- TypeScript 5+
- Cloudflare Workers API
- Cloudflare D1 Database
- Fetch API for HTTP requests
- localStorage API for persistence

### Feature Dependencies
- ✅ Database schema created (users table)
- ✅ Backend API endpoint implemented
- ✅ CORS headers configured for cross-origin requests
- ✅ Frontend styling system in place

### Blocking Issues
None - Feature is fully implemented and operational

## Success Metrics

### Quantitative Metrics
- **Login Success Rate:** > 99% of login attempts succeed
- **Login Performance:** < 2 seconds average login time
- **Error Rate:** < 1% of logins result in errors
- **User Retention:** Users successfully return to application

### Qualitative Metrics
- **User Satisfaction:** Users find login process intuitive
- **Accessibility:** Login works with keyboard and screen readers
- **Visual Polish:** Login screen looks professional and modern

## Implementation Notes

### Current Implementation Status
✅ **COMPLETED** - This feature has been fully implemented and is operational.

### Key Implementation Details

1. **Username-based Authentication:**
   - Simple, password-less authentication
   - Username acts as primary identifier
   - No email or phone verification required
   - Suitable for demo/prototype applications

2. **User ID Strategy:**
   - UUID generated on server using `crypto.randomUUID()`
   - UUID persisted in database and returned to client
   - UUID stored in localStorage for session persistence
   - UUID used for WebSocket authentication and message routing

3. **Database Query Pattern:**
   ```sql
   -- Check for existing user
   SELECT id, username, avatar, lastSeen
   FROM users
   WHERE username = ?

   -- Create new user if not exists
   INSERT INTO users (id, username, avatar, lastSeen)
   VALUES (?, ?, ?, ?)

   -- Update existing user
   UPDATE users
   SET lastSeen = ?
   WHERE id = ?
   ```

4. **State Management:**
   - User object stored in React state (App.tsx)
   - User object persisted to localStorage as JSON
   - On app mount, attempt to load user from localStorage
   - On logout, clear localStorage and reset state

5. **Error Handling:**
   - Try-catch blocks around API calls
   - Console logging for debugging
   - User-friendly error messages (to be enhanced)

## Future Enhancements

### Phase 2 Improvements (Not Currently Planned)
- **User Profiles:** Add avatar upload, bio, display name
- **Password Protection:** Add optional password for username
- **Email Verification:** Add email-based account verification
- **OAuth Integration:** Support login with Google, GitHub, etc.
- **Username Availability Check:** Real-time check as user types
- **Forgot Password:** Password reset flow
- **2FA:** Two-factor authentication option
- **Session Management:** Explicit session expiration and refresh
- **Multi-device Management:** View and manage active sessions
- **Username Restrictions:** Enforce username format rules (length, characters)

## Related Stories

- **US-001:** User Registration (merged into this story)
- **US-003:** User Logout
- **US-004:** User Profile Management (future)
- **US-005:** Online Status Tracking (implemented)
- **US-006:** Read Receipts (implemented)

## Appendix

### Relevant Code Files
- `src/client/components/Login.tsx` - Login form component
- `src/client/App.tsx` - Authentication state management
- `src/worker/index.ts` - Login API endpoint (lines 52-91)
- `schema.sql` - Users table definition

### API Documentation Reference
See `docs/API.md` for complete API documentation (to be created)

### Design Mockups
Login screen follows WhatsApp's clean, minimal design philosophy with modern gradients and card-based UI.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-11
**Author:** Development Team
**Status:** Implemented & Operational
