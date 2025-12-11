# WhatsApp Clone

A real-time chat application built with React and Cloudflare Workers, featuring WebSocket communication for instant messaging.

## Features

- Real-time messaging using WebSockets
- Online/offline status indicators
- Typing indicators
- Message delivery status (sent/delivered/read)
- User authentication
- Message persistence with Cloudflare D1
- Modern WhatsApp-inspired UI
- Cloudflare Durable Objects for WebSocket handling

## Tech Stack

### Backend
- Cloudflare Workers
- Cloudflare Durable Objects (for WebSocket connections)
- Cloudflare D1 (SQLite database)
- TypeScript

### Frontend
- React 18
- TypeScript
- Vite
- Custom WebSocket hook

## Setup Instructions

### Prerequisites
- Node.js 18+
- Cloudflare account
- Wrangler CLI

### 1. Install Dependencies

```bash
npm install
```

### 2. Create D1 Database

```bash
# Create the database
wrangler d1 create whatsapp_clone_db

# Update wrangler.toml with the database ID from the output above
```

### 3. Initialize Database Schema

```bash
wrangler d1 execute whatsapp_clone_db --file=./schema.sql
```

### 4. Update Configuration

Edit `wrangler.toml` and replace `your-database-id` with the actual database ID from step 2.

### 5. Development

Run both the Cloudflare Worker and React frontend in development mode:

```bash
npm run dev
```

This will start:
- Cloudflare Worker: http://localhost:8787
- React frontend: http://localhost:3000

### 6. Build

```bash
npm run build
```

### 7. Deploy to Cloudflare

```bash
npm run deploy
```

After deployment, update your frontend to point to the deployed worker URL.

## Project Structure

```
whatsapp-clone/
├── src/
│   ├── worker/              # Cloudflare Worker backend
│   │   ├── index.ts         # Main worker entry point
│   │   ├── ChatRoom.ts      # Durable Object for WebSocket handling
│   │   └── types.ts         # TypeScript types
│   └── client/              # React frontend
│       ├── components/      # React components
│       │   ├── Login.tsx
│       │   ├── Chat.tsx
│       │   ├── Sidebar.tsx
│       │   ├── ChatWindow.tsx
│       │   ├── MessageList.tsx
│       │   └── MessageInput.tsx
│       ├── hooks/           # Custom React hooks
│       │   └── useWebSocket.ts
│       ├── App.tsx          # Main app component
│       ├── main.tsx         # React entry point
│       ├── styles.css       # Global styles
│       └── index.html       # HTML template
├── schema.sql               # D1 database schema
├── wrangler.toml           # Cloudflare Worker configuration
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Project dependencies

```

## How It Works

### WebSocket Communication

The application uses Cloudflare Durable Objects to maintain WebSocket connections:

1. When a user logs in, they connect to the `/ws` endpoint
2. The connection is upgraded to a WebSocket and handled by a ChatRoom Durable Object
3. All active connections are maintained in the Durable Object's memory
4. Messages are broadcast in real-time to connected users

### Message Flow

1. User types a message and clicks Send
2. Frontend sends message via WebSocket to the worker
3. Worker's Durable Object receives the message
4. Message is delivered to recipient's WebSocket if online
5. Message is saved to D1 database for persistence
6. Delivery status is sent back to sender

### Data Persistence

- User information is stored in D1 (Cloudflare's SQLite database)
- Messages are persisted in D1 for chat history
- Messages can be retrieved via REST API endpoints

## API Endpoints

### REST API

- `GET /api/users` - Get all users
- `POST /api/users` - Create a new user
- `GET /api/messages/:userId?user=:currentUserId` - Get messages between two users
- `POST /api/messages` - Save a message

### WebSocket Messages

Messages sent over WebSocket follow this format:

```typescript
{
  type: 'auth' | 'message' | 'typing' | 'status' | 'online',
  payload: any
}
```

## Customization

### Styling

Edit `src/client/styles.css` to customize the appearance. The current design uses a dark theme inspired by WhatsApp.

### Adding Features

Some ideas for extending the application:

- Group chats
- File/image sharing
- Message reactions
- Message editing/deletion
- Voice messages
- Video calls
- End-to-end encryption

## Limitations

- No authentication/authorization (users can pick any username)
- Messages are stored in plain text
- No rate limiting
- Single chat room (all users share the same Durable Object)

## Production Considerations

For production deployment, consider:

1. Add proper authentication (JWT, OAuth, etc.)
2. Implement rate limiting
3. Add message encryption
4. Use multiple Durable Objects for scalability
5. Add error boundaries and better error handling
6. Implement message pagination
7. Add file upload support with R2
8. Set up monitoring and logging

## License

MIT
