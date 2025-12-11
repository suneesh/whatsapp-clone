Functional Requirements Specification (FRS)
Feature: Group Chat
System: Messaging Application (Web Client + Backend Services)
Version: 1.1
Document Owner: Product Engineering
Status: Draft
________________________________________
1. Purpose and Scope
This document defines functional requirements to introduce Group Chat into an existing messaging platform that currently offers only a web client. The scope includes UI, backend interactions, real-time messaging, membership management, notifications, and security.
Out of scope:
• Mobile applications
• Desktop-native clients
• Audio/video conferencing
________________________________________
2. Definitions
Term	Meaning
Web Client	Browser-based client (Chrome, Safari, Firefox, Edge).
Group	Multi-user conversation space.
Admin	A group member with elevated privileges.
Owner	The user who created the group.
Member	Any participant in a group.
Event Message	System-generated informational messages displayed in chat.
Media	Images, documents, videos, audio uploads.
________________________________________
3. Assumptions & Constraints
1.	Communication between client and backend uses WebSockets and HTTPS.
2.	Backend supports E2E encryption or at least encryption-in-transit; if E2EE is in roadmap, requirements note compatibility.
3.	Web browser storage is limited; large histories must be streamed incrementally.
4.	Web push notifications require user consent and HTTPS.
5.	Group size limit is configurable (default 1024).
6.	Media uploads may rely on presigned URLs or multipart upload endpoints.
________________________________________
4. Functional Requirements
4.1 Group Creation
FR-GC-01: Create Group
User can create a new group from the web client by providing:
• Group name (mandatory)
• List of initial participants (at least one)
• Optional group avatar (image upload)
• Optional description
FR-GC-02: Assign Owner
The creator becomes the group owner and an admin.
FR-GC-03: Group ID Generation
Backend generates a unique group ID and returns it to the web client.
FR-GC-04: Initial Distribution
System sends creation event and metadata to all initial participants.
________________________________________
4.2 Group Metadata Management
FR-GM-01: Edit Metadata
Admins (including owner) can update:
• Group name
• Group description
• Avatar
• Permission settings
FR-GM-02: UI Update
Web clients must update metadata in real time without requiring page refresh.
FR-GM-03: Versioned Storage
Backend stores metadata with version numbers for consistency checks.
________________________________________
4.3 Membership Management
FR-MB-01: Add Members
Admins can add users via:
• Direct selection from user list
• Email/username search
• Optional invite link (web-friendly)
FR-MB-02: Invite Link (Optional Feature)
Admins can:
• Generate unique invite URLs
• Revoke links
• Configure approval requirement
FR-MB-03: Remove Members
Admins can remove members; removed members lose message access after removal timestamp.
FR-MB-04: Leave Group
Any member can leave. A leave event is posted.
FR-MB-05: Rejoin
A user can rejoin if:
• Added again by admin
• Or uses a valid invite link
FR-MB-06: Admin Rights
Admins can promote/demote participants.
FR-MB-07: Participant List Display
Web client displays a scrollable, filterable participant list.
________________________________________
4.4 Group Messaging
FR-MS-01: Text Messaging
Group members can send and receive text messages in real time via WebSocket.
FR-MS-02: Media Messaging
User can upload and send:
• Images
• Documents
• Videos (size limits enforced)
• Audio snippets
Uploads must:
• Use resumable upload or presigned URL mechanisms
• Display progress indicators
FR-MS-03: Delivery Model
• Real-time fanout via WebSocket
• Retry mechanism for failed deliveries
• Offline messages retrieved via REST/HTTPS when client reconnects
FR-MS-04: Message Ordering
Client must maintain chronological ordering using server timestamps.
FR-MS-05: Read Receipts
Web client displays:
• Sent
• Delivered
• Read (optional aggregated indicator, e.g., number of readers)
FR-MS-06: Message Actions
Users can:
• Edit (optional feature)
• Delete for self
• Delete for everyone (within allowed window)
• Reply to a specific message
• Forward to other chats
FR-MS-07: Rich Content
Client supports:
• URL previews
• Emojis
• Markdown or limited formatting (bold, italics)
________________________________________
4.5 Group System Events
The following appear in the message timeline:
• Member added
• Member removed
• Member left
• Admin promoted/demoted
• Group metadata updated
• Invite link created/revoked
Event messages have a distinct UI style.
________________________________________
4.6 Permissions & Settings
FR-PS-01: Message Permissions
Admins can restrict:
• Who can send messages (everyone/admins only)
UI must disable message composer for restricted users.
FR-PS-02: Metadata Permissions
Admins decide who can modify metadata:
• Admins only
• Everyone (owner override always allowed)
FR-PS-03: Join Approval Mode
If enabled:
• Join requests appear in admin panel
• Admins can approve/deny
FR-PS-04: Mention Behavior
Web client supports:
• @username
• @all (admins only)
________________________________________
4.7 Notifications (Web-Specific)
FR-NT-01: Web Push Notifications
If user enabled browser notifications:
• New messages
• Mentions
• Admin changes
• Join requests (if applicable)
FR-NT-02: Mute/Notification Settings
User can mute group for:
• 1 hour
• 8 hours
• 1 week
• Permanently
Muted groups will not trigger push notifications except:
• Critical admin messages (optional requirement)
• Direct mentions (optional)
FR-NT-03: Browser Tab Indicators
Unread messages trigger:
• Highlight on tab title
• Badge count on sidebar
• Sound alert (configurable)
________________________________________
4.8 History, Loading & Synchronization
FR-HS-01: Initial Load
On entering a group chat, the client loads:
• Last 50–200 messages (configurable)
• Metadata
• Participant list
FR-HS-02: Infinite Scroll
As user scrolls up, older messages are fetched via paginated API.
FR-HS-03: Membership-Based History Access
New members cannot access messages before their join timestamp unless owners opt to allow it.
FR-HS-04: Conflict Handling
If concurrent updates occur (e.g., metadata edits), server resolves based on metadata version.
________________________________________
4.9 Security & Privacy Requirements
FR-SC-01: Encryption
• Mandatory TLS for all communications
• If E2EE is supported, group keys must be managed client-side
• The server must not store plaintext messages
FR-SC-02: Authorization
Server must validate user permissions for:
• Sending messages
• Managing membership
• Editing metadata
FR-SC-03: Link Security
Invite links must be:
• Random and unguessable
• Revocable
• Expirable (optional)
FR-SC-04: Data Retention
Deleted messages must not be retrievable via APIs.
________________________________________
4.10 Reliability & Performance
FR-RP-01: Concurrent Users
Web client must handle active participation of at least 1000 users per group.
FR-RP-02: Delivery Latency
Target delivery time for online users: 300–500 ms.
FR-RP-03: Browser Resource Efficiency
Client must:
• Avoid excessive memory usage
• Use streaming and virtualization for large message lists
• Compress media thumbnails
FR-RP-04: Reconnection Behavior
If WebSocket disconnects:
• Client retries with exponential backoff
• Fetches missed messages after reconnection
________________________________________
4.11 Logging & Monitoring
FR-LG-01: Server Logs
Log only metadata events, not message contents.
FR-LG-02: Frontend Logging
Web client logs errors (not messages) to central monitoring (Sentry, etc.).
FR-LG-03: Metrics
Track:
• Message throughput
• Fanout latency
• Group creation rate
• Membership churn
________________________________________
5. Web UI Requirements
5.1 Group Creation Dialog
• Modal window with name, description, file upload, member selection
• Validation for empty name and size limits
5.2 Chat Screen
• Virtualized message list
• Sending area with rich input features
• "New messages" separators
• Typing indicators
• Presence indicators (optional)
5.3 Group Info Panel
Must include:
• Group avatar
• Name and description
• List of participants with roles
• Admin controls
• Invite link management
• Join request queue (if enabled)
• Exit group button
5.4 Message Thread UI
• Replies nested or inline
• Hover actions (reply, forward, delete, etc.)
• Timestamps and indicators
________________________________________
6. Non-Functional Requirements
NFR-01: Usability
Web UI should remain functional across modern desktop browsers and theoretically tablet browsers.
NFR-02: Accessibility
Follow WCAG 2.1 AA standards where possible.
NFR-03: SEO
Group chat UI is behind authentication; no SEO requirements.
NFR-04: Security
Full CSP, sanitization of all user input, prevention of XSS/CSRF.
NFR-05: Internationalization
Support for LTR and RTL languages.
________________________________________
7. Acceptance Criteria (Condensed)
1.	User can successfully create and join group chats via web client.
2.	Real-time group messaging works across multiple browsers simultaneously.
3.	Admin controls modify permissions and membership correctly.
4.	Metadata updates appear instantly on all connected clients.
5.	Infinite scroll retrieves historical messages correctly.
6.	Web notifications behave according to user preferences.
7.	Group settings are persisted and enforced.
8.	Removed members lose access immediately.
9.	System handles large groups with acceptable performance.

