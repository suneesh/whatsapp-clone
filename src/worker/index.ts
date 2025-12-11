import { Env } from './types';
import { ChatRoom } from './ChatRoom';
import bcrypt from 'bcryptjs';

export { ChatRoom };

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // WebSocket connection
    if (url.pathname === '/ws') {
      const id = env.CHAT_ROOM.idFromName('main-chat');
      const chatRoom = env.CHAT_ROOM.get(id);
      const newUrl = new URL(request.url);
      newUrl.pathname = '/websocket';
      // Forward the original request to the Durable Object with the updated pathname
      const forwarded = new Request(newUrl.toString(), request);
      return chatRoom.fetch(forwarded);
    }

    // REST API endpoints
    if (url.pathname.startsWith('/api')) {
      return handleAPI(request, env, corsHeaders);
    }

    return new Response('Not found', { status: 404 });
  },
};

async function handleAPI(request: Request, env: Env, corsHeaders: Record<string, string>): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname.replace('/api', '');

  try {
    // Get all users
    if (path === '/users' && request.method === 'GET') {
      const users = await env.DB.prepare('SELECT id, username, avatar, lastSeen FROM users').all();
      return new Response(JSON.stringify(users.results), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Register new user
    if (path === '/auth/register' && request.method === 'POST') {
      const body = await request.json() as { username: string; password: string; avatar?: string };

      // Validation
      if (!body.username || !body.password) {
        return new Response(JSON.stringify({ error: 'Username and password are required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      if (body.username.length < 3) {
        return new Response(JSON.stringify({ error: 'Username must be at least 3 characters' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      if (body.password.length < 6) {
        return new Response(JSON.stringify({ error: 'Password must be at least 6 characters' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Check if user already exists
      const existingUser = await env.DB.prepare(
        'SELECT id FROM users WHERE username = ?'
      ).bind(body.username).first();

      if (existingUser) {
        return new Response(JSON.stringify({ error: 'Username already taken' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 409,
        });
      }

      // Hash password
      const passwordHash = await bcrypt.hash(body.password, 10);

      // Create new user
      const id = crypto.randomUUID();
      const now = Date.now();

      await env.DB.prepare(
        'INSERT INTO users (id, username, password_hash, avatar, lastSeen, created_at) VALUES (?, ?, ?, ?, ?, ?)'
      ).bind(id, body.username, passwordHash, body.avatar || null, now, now).run();

      return new Response(JSON.stringify({ 
        id, 
        username: body.username, 
        avatar: body.avatar,
        lastSeen: now 
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 201,
      });
    }

    // Login user
    if (path === '/auth/login' && request.method === 'POST') {
      const body = await request.json() as { username: string; password: string };

      // Validation
      if (!body.username || !body.password) {
        return new Response(JSON.stringify({ error: 'Username and password are required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Find user
      const user = await env.DB.prepare(
        'SELECT id, username, password_hash, avatar, lastSeen FROM users WHERE username = ?'
      ).bind(body.username).first();

      if (!user) {
        return new Response(JSON.stringify({ error: 'Invalid username or password' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      // Verify password
      const passwordMatch = await bcrypt.compare(body.password, user.password_hash as string);

      if (!passwordMatch) {
        return new Response(JSON.stringify({ error: 'Invalid username or password' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      // Update last seen
      const lastSeen = Date.now();
      await env.DB.prepare(
        'UPDATE users SET lastSeen = ? WHERE id = ?'
      ).bind(lastSeen, user.id).run();

      return new Response(JSON.stringify({
        id: user.id,
        username: user.username,
        avatar: user.avatar,
        lastSeen
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      });
    }

    // Get messages between two users
    if (path.startsWith('/messages/') && request.method === 'GET') {
      const userId = url.searchParams.get('user');
      const otherUserId = path.split('/')[2];

      if (!userId || !otherUserId) {
        return new Response(JSON.stringify({ error: 'Missing user parameters' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      const messages = await env.DB.prepare(
        `SELECT * FROM messages
         WHERE (fromUser = ? AND toUser = ?) OR (fromUser = ? AND toUser = ?)
         ORDER BY timestamp ASC`
      ).bind(userId, otherUserId, otherUserId, userId).all();

      return new Response(JSON.stringify(messages.results), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Save message
    if (path === '/messages' && request.method === 'POST') {
      const body = await request.json() as {
        id: string;
        fromUser: string;
        toUser: string;
        content: string;
        timestamp: number;
        status: string;
      };

      await env.DB.prepare(
        'INSERT INTO messages (id, fromUser, toUser, content, timestamp, status) VALUES (?, ?, ?, ?, ?, ?)'
      ).bind(body.id, body.fromUser, body.toUser, body.content, body.timestamp, body.status).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 201,
      });
    }

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
      const now = Date.now();
      
      // Update status and set readAt timestamp if status is 'read'
      let query: string;
      let params: any[];
      
      if (body.status === 'read') {
        query = `UPDATE messages SET status = ?, readAt = ? WHERE id IN (${placeholders})`;
        params = [body.status, now, ...body.messageIds];
      } else {
        query = `UPDATE messages SET status = ? WHERE id IN (${placeholders})`;
        params = [body.status, ...body.messageIds];
      }

      await env.DB.prepare(query)
        .bind(...params)
        .run();

      return new Response(JSON.stringify({
        success: true,
        updated: body.messageIds.length
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      });
    }

    return new Response('Not found', { status: 404, headers: corsHeaders });
  } catch (error) {
    return new Response(JSON.stringify({ error: (error as Error).message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    });
  }
}
