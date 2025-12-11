# User Story: Secure User Authentication

## Story Overview

**As a** user wanting to use the chat application  
**I want to** register with a username and password, then log in securely  
**So that** my account is protected and only I can access my messages

## Story Details

**Story ID:** US-002-v2  
**Epic:** User Authentication & Security  
**Priority:** P0 (Critical)  
**Story Points:** 8  
**Status:** Implemented  
**Version:** 2.0 (Password-Based Authentication)

## Acceptance Criteria

### AC1: User Registration Form
**Given** a new user visits the application  
**When** they see the login screen  
**Then** they should see:
- A toggle to switch between "Sign In" and "Sign Up" modes
- Username input field (minimum 3 characters)
- Password input field (minimum 6 characters, masked)
- Clear button labels ("Sign In" or "Sign Up")
- Error messages for invalid input
- Loading state during authentication

### AC2: Registration Validation
**Given** a user is registering a new account  
**When** they submit the registration form  
**Then** the system should validate:
- Username is at least 3 characters
- Username is unique (not already taken)
- Password is at least 6 characters
- All fields are filled
- Display specific error messages for each validation failure

### AC3: Password Security
**Given** a user creates an account  
**When** their password is stored  
**Then** the system should:
- Hash the password using bcrypt with salt rounds of 10
- Never store the plain-text password
- Never return the password hash in API responses
- Use secure comparison for password verification

### AC4: New User Registration
**Given** a user enters valid credentials for registration  
**When** they click the Sign Up button  
**Then** the system should:
- Validate username uniqueness
- Hash the password securely
- Create a new user account with a unique UUID
- Store username, password_hash, avatar, lastSeen, and created_at
- Return user object (without password hash)
- Automatically log the user into the application
- Save session to localStorage
- Show the main chat interface

### AC5: Existing User Login
**Given** a registered user enters their credentials  
**When** they click the Sign In button  
**Then** the system should:
- Validate username and password are provided
- Query database for user by username
- Verify password matches the stored hash
- Update lastSeen timestamp
- Return user object (without password hash)
- Save session to localStorage
- Show the main chat interface

### AC6: Authentication Errors
**Given** a user attempts to authenticate  
**When** invalid credentials are provided  
**Then** the system should:
- Return 401 Unauthorized for invalid login
- Return 409 Conflict for username already taken
- Display user-friendly error messages
- Not reveal whether username or password was incorrect (for login)
- Keep the form accessible for retry
- Clear sensitive data from memory

### AC7: Session Persistence
**Given** a user has successfully logged in  
**When** they refresh the page or close and reopen the browser  
**Then** the system should:
- Remember their login state (using localStorage)
- Automatically restore their session without requiring re-login
- Reconnect to WebSocket with stored credentials

### AC8: Logout
**Given** a logged-in user clicks logout  
**When** the logout action completes  
**Then** the system should:
- Clear user session from localStorage
- Clear all application state
- Close WebSocket connection
- Return to login screen
- Prevent access to protected features

## Technical Requirements

### Frontend Components

#### Enhanced Login Component (`src/client/components/Login.tsx`)
```typescript
interface LoginProps {
  onLogin: (username: string, password: string) => void;
  onRegister: (username: string, password: string) => void;
}

function Login({ onLogin, onRegister }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Form validation and submission
  // Toggle between login/register modes
  // Display error messages
}
```

#### App Component Integration (`src/client/App.tsx`)
- Manage authentication state (currentUser)
- Handle both login and registration
- Store user data in localStorage
- Retrieve user from localStorage on mount
- Handle logout operations
- Pass error messages to UI
- Conditionally render Login or Chat component

### Backend API

#### Endpoint: POST /api/auth/register

**Request:**
```json
{
  "username": "john_doe",
  "password": "securepass123"
}
```

**Success Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "avatar": null,
  "lastSeen": 1699564800000
}
```

**Error Responses:**
- 400: Missing username or password
- 400: Username too short (< 3 characters)
- 400: Password too short (< 6 characters)
- 409: Username already taken
- 500: Server error

#### Endpoint: POST /api/auth/login

**Request:**
```json
{
  "username": "john_doe",
  "password": "securepass123"
}
```

**Success Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "avatar": null,
  "lastSeen": 1699568400000
}
```

**Error Responses:**
- 400: Missing username or password
- 401: Invalid username or password
- 500: Server error

### Database Schema

#### Users Table (Updated)
```sql
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  avatar TEXT,
  lastSeen INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
```

**New Fields:**
- `password_hash`: bcrypt hashed password (never returned in API)
- `created_at`: Account creation timestamp

### Security Implementation

#### Password Hashing (bcrypt)
```typescript
import bcrypt from 'bcryptjs';

// Registration: Hash password with 10 salt rounds
const passwordHash = await bcrypt.hash(password, 10);

// Login: Verify password against stored hash
const passwordMatch = await bcrypt.compare(password, storedHash);
```

**Security Features:**
- Bcrypt with 10 salt rounds (industry standard)
- Passwords never stored in plain text
- Passwords never returned in API responses
- Secure password comparison prevents timing attacks
- Username uniqueness enforced at database level

### Data Flow

#### Registration Flow
1. **User fills registration form**
   - Frontend validates username (≥3 chars) and password (≥6 chars)
   - Sends POST to `/api/auth/register`

2. **Backend processes registration**
   - Validates input
   - Checks username availability
   - Hashes password with bcrypt
   - Creates new user with UUID
   - Returns user object (no password)

3. **Frontend receives response**
   - Stores user in state and localStorage
   - Transitions to main chat interface
   - Establishes WebSocket connection

#### Login Flow
1. **User enters credentials**
   - Frontend validates non-empty fields
   - Sends POST to `/api/auth/login`

2. **Backend processes login**
   - Queries user by username
   - Verifies password with bcrypt.compare()
   - Updates lastSeen timestamp
   - Returns user object (no password)

3. **Frontend receives response**
   - Stores user in state and localStorage
   - Transitions to main chat interface
   - Establishes WebSocket connection

## UI/UX Design

### Login/Registration Screen
```
┌─────────────────────────────────────────┐
│                                         │
│          [Gradient Background]          │
│                                         │
│         ┌─────────────────┐            │
│         │ WhatsApp Clone  │            │
│         │  Welcome Back   │            │
│         │                 │            │
│         │  [Error Message]│            │
│         │                 │            │
│         │  ┌───────────┐  │            │
│         │  │ Username  │  │            │
│         │  └───────────┘  │            │
│         │  ┌───────────┐  │            │
│         │  │ Password  │  │            │
│         │  └───────────┘  │            │
│         │                 │            │
│         │  [Sign In]      │            │
│         │                 │            │
│         │  Don't have an  │            │
│         │  account? Sign  │            │
│         │       Up        │            │
│         └─────────────────┘            │
│                                         │
└─────────────────────────────────────────┘
```

### Design Specifications
- **Background:** Linear gradient (purple/blue theme)
- **Login Box:** White background, rounded corners, shadow
- **Input Fields:** 
  - Username: Text input, 3+ characters
  - Password: Masked input, 6+ characters
- **Error Messages:** Red background, clear text
- **Buttons:** 
  - Primary: Gradient background, disabled when loading
  - Secondary: Transparent, underline on hover
- **Toggle Mode:** Link-style button to switch between login/register
- **Loading State:** "Please wait..." text, disabled inputs

## Non-Functional Requirements

### Security
- **Password Storage:** bcrypt with 10 salt rounds
- **Transport Security:** HTTPS required in production
- **SQL Injection:** Parameterized queries
- **XSS Protection:** React automatic escaping
- **Password Policy:** Minimum 6 characters (can be enhanced)
- **Account Lockout:** Not implemented (future enhancement)
- **Rate Limiting:** Not implemented (future enhancement)

### Performance
- **Registration:** < 500ms (bcrypt hashing overhead)
- **Login:** < 500ms (bcrypt verification overhead)
- **Database Queries:** Optimized with indexes
- **Frontend Validation:** Instant feedback

### Reliability
- **Error Handling:** Graceful degradation
- **Network Failures:** User-friendly error messages
- **Database Failures:** Proper error codes
- **Validation:** Both client and server-side

### Usability
- **Clear Instructions:** Mode-specific headings
- **Instant Feedback:** Real-time validation
- **Error Messages:** Specific and actionable
- **Keyboard Navigation:** Tab, Enter key support
- **Password Visibility:** Standard masked input

## Edge Cases & Error Scenarios

### Edge Case 1: Username Collision
**Scenario:** User tries to register with existing username  
**Expected:** 409 error, "Username already taken" message

### Edge Case 2: Weak Password
**Scenario:** User enters password < 6 characters  
**Expected:** Client-side validation prevents submission

### Edge Case 3: Network Failure
**Scenario:** Network disconnects during registration  
**Expected:** Error message, form remains accessible

### Edge Case 4: SQL Injection Attempt
**Scenario:** User enters SQL in username/password  
**Expected:** Parameterized queries prevent injection

### Edge Case 5: Concurrent Registrations
**Scenario:** Two users try same username simultaneously  
**Expected:** UNIQUE constraint prevents duplicate, one fails with 409

### Edge Case 6: Special Characters
**Scenario:** Username/password with Unicode, symbols  
**Expected:** System accepts valid UTF-8 characters

### Edge Case 7: Very Long Password
**Scenario:** User enters 100+ character password  
**Expected:** bcrypt handles up to 72 bytes, truncates safely

## Testing Strategy

### Unit Tests

#### Frontend Tests
- ✅ Login component renders with two modes
- ✅ Toggle switches between login and register
- ✅ Validation prevents short usernames
- ✅ Validation prevents short passwords
- ✅ Error messages display correctly
- ✅ Loading state disables inputs
- ✅ Form submission calls correct handler

#### Backend Tests
- ✅ POST /api/auth/register creates user with hashed password
- ✅ POST /api/auth/register rejects duplicate username
- ✅ POST /api/auth/register validates input
- ✅ POST /api/auth/login verifies password correctly
- ✅ POST /api/auth/login rejects invalid credentials
- ✅ Password hash never returned in responses
- ✅ bcrypt salt rounds set to 10

### Integration Tests
- ✅ End-to-end registration flow
- ✅ End-to-end login flow
- ✅ Session persists after page refresh
- ✅ Logout clears session completely
- ✅ Invalid login shows error message
- ✅ Duplicate registration shows error message

### Security Tests
- [ ] SQL injection attempts blocked
- [ ] Password brute force rate limiting
- [ ] HTTPS enforced in production
- [ ] Password hash complexity verification
- [ ] Session hijacking prevention
- [ ] XSS attack prevention

## Migration Guide

### Updating Existing Deployments

#### Step 1: Database Migration
```sql
-- Add new columns to users table
ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0;

-- Update existing users (one-time migration)
-- Note: Existing users will need to "register" again with a password
-- OR implement a "set password" flow for existing users

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
```

#### Step 2: Deploy Backend Code
```bash
npm install bcryptjs @types/bcryptjs
npm run build:worker
npm run deploy
```

#### Step 3: Deploy Frontend Code
```bash
npm run build:client
# Deploy static assets to CDN/hosting
```

#### Step 4: Clear User Sessions
- All users will need to log out and register/login again
- Clear localStorage on client side
- Consider adding a migration notice

## Success Metrics

### Quantitative Metrics
- **Registration Success Rate:** > 95% (excluding duplicate usernames)
- **Login Success Rate:** > 99% (valid credentials)
- **Authentication Time:** < 500ms average
- **Password Hash Strength:** bcrypt 10 rounds (industry standard)
- **Error Rate:** < 1% server errors

### Qualitative Metrics
- **Security:** Passwords never stored in plain text
- **User Experience:** Clear, intuitive registration/login flow
- **Accessibility:** Keyboard navigation, screen reader compatible

## Implementation Status

✅ **COMPLETED** - Secure password-based authentication fully implemented

### Key Security Features
1. ✅ bcrypt password hashing (10 salt rounds)
2. ✅ Unique username enforcement
3. ✅ Password validation (6+ characters)
4. ✅ Secure password comparison
5. ✅ Password hashes never exposed in API
6. ✅ Parameterized SQL queries
7. ✅ Client and server-side validation

## Future Enhancements

### Phase 2 Security Improvements
- [ ] **Password Strength Meter:** Real-time password strength indicator
- [ ] **Password Requirements:** Uppercase, lowercase, numbers, symbols
- [ ] **Account Lockout:** Temporary lock after N failed attempts
- [ ] **Rate Limiting:** Prevent brute force attacks
- [ ] **Email Verification:** Send verification email on registration
- [ ] **Password Reset:** Forgot password flow
- [ ] **Two-Factor Authentication:** SMS or authenticator app
- [ ] **Session Expiration:** Automatic logout after inactivity
- [ ] **Password History:** Prevent reusing recent passwords
- [ ] **Security Audit Log:** Track login attempts, changes

### Phase 3 Advanced Features
- [ ] **OAuth Integration:** Google, GitHub, Microsoft login
- [ ] **Biometric Authentication:** Fingerprint, Face ID
- [ ] **Multi-device Management:** View and revoke sessions
- [ ] **Suspicious Activity Alerts:** Email notifications
- [ ] **CAPTCHA:** Prevent automated attacks
- [ ] **Password Breach Detection:** Check against known breaches

## Related Stories

- **US-001:** Basic User Registration (replaced by this story)
- **US-003:** User Logout (implemented)
- **US-004:** Password Reset Flow (future)
- **US-005:** Two-Factor Authentication (future)
- **US-006:** Email Verification (future)

## Appendix

### Relevant Code Files
- `src/client/components/Login.tsx` - Enhanced login/register component
- `src/client/App.tsx` - Authentication state management
- `src/worker/index.ts` - Auth API endpoints
- `schema.sql` - Updated users table schema
- `package.json` - bcryptjs dependency

### Security Resources
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [bcrypt NPM Documentation](https://www.npmjs.com/package/bcryptjs)
- [Web Authentication Best Practices](https://w3c.github.io/webauthn/)

---

**Document Version:** 2.0  
**Last Updated:** 2025-12-11  
**Author:** Development Team  
**Status:** Implemented & Secure
