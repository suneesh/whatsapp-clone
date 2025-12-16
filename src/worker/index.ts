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
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
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

  const authenticateUser = async (): Promise<string | null> => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return null;
    }
    const userId = authHeader.replace('Bearer ', '').trim();
    if (!userId) {
      return null;
    }
    const user = await env.DB.prepare('SELECT id FROM users WHERE id = ?').bind(userId).first();
    if (!user) {
      return null;
    }
    return userId;
  };

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
        'INSERT INTO users (id, username, password_hash, avatar, lastSeen, created_at, role, is_active, can_send_images) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(id, body.username, passwordHash, body.avatar || null, now, now, 'user', 1, 1).run();

      return new Response(JSON.stringify({
        id,
        username: body.username,
        avatar: body.avatar,
        lastSeen: now,
        role: 'user',
        is_active: 1,
        can_send_images: 1,
        created_at: now
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
        'SELECT id, username, password_hash, avatar, lastSeen, role, is_active, can_send_images, created_at FROM users WHERE username = ?'
      ).bind(body.username).first();

      if (!user) {
        return new Response(JSON.stringify({ error: 'Invalid username or password' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      // Check if user is active
      if (user.is_active === 0) {
        return new Response(JSON.stringify({ error: 'Your account has been disabled' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
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
        lastSeen,
        role: user.role,
        is_active: user.is_active,
        can_send_images: user.can_send_images,
        created_at: user.created_at
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

    // Upload identity + prekey bundle
    if (path === '/users/prekeys' && request.method === 'POST') {
      const userId = await authenticateUser();
      if (!userId) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const body = await request.json() as {
        identityKey: string;
        signingKey: string;
        fingerprint: string;
        signedPrekey: { keyId: number; publicKey: string; signature: string } | null;
        oneTimePrekeys?: Array<{ keyId: number; publicKey: string }>;
      };

      const oneTimePrekeys = Array.isArray(body.oneTimePrekeys) ? body.oneTimePrekeys : [];

      if (!body.identityKey || !body.signingKey || !body.fingerprint) {
        return new Response(JSON.stringify({ error: 'Missing identity material' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      if (!body.signedPrekey && oneTimePrekeys.length === 0) {
        return new Response(JSON.stringify({ error: 'No prekeys provided' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      if (oneTimePrekeys.length > 200) {
        return new Response(JSON.stringify({ error: 'Too many one-time prekeys (max 200)' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      const now = Date.now();

      await env.DB.prepare(
        `INSERT INTO user_identity_keys (user_id, identity_key, signing_key, fingerprint, created_at)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT(user_id) DO UPDATE SET
           identity_key = excluded.identity_key,
           signing_key = excluded.signing_key,
           fingerprint = excluded.fingerprint,
           created_at = excluded.created_at`
      ).bind(userId, body.identityKey, body.signingKey, body.fingerprint, now).run();

      if (body.signedPrekey) {
        await env.DB.prepare(
          `INSERT INTO user_prekeys (id, user_id, key_id, prekey_type, public_key, signature, created_at, is_used)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)
           ON CONFLICT(user_id, key_id, prekey_type) DO UPDATE SET
             public_key = excluded.public_key,
             signature = excluded.signature,
             created_at = excluded.created_at,
             is_used = 0,
             used_at = NULL`
        ).bind(
          crypto.randomUUID(),
          userId,
          body.signedPrekey.keyId,
          'signed',
          body.signedPrekey.publicKey,
          body.signedPrekey.signature,
          now
        ).run();
      }

      if (oneTimePrekeys.length > 0) {
        const statements = oneTimePrekeys.map((prekey) =>
          env.DB.prepare(
            `INSERT INTO user_prekeys (id, user_id, key_id, prekey_type, public_key, created_at, is_used)
             VALUES (?, ?, ?, ?, ?, ?, 0)
             ON CONFLICT(user_id, key_id, prekey_type) DO UPDATE SET
               public_key = excluded.public_key,
               created_at = excluded.created_at,
               is_used = 0,
               used_at = NULL`
          ).bind(
            crypto.randomUUID(),
            userId,
            prekey.keyId,
            'one_time',
            prekey.publicKey,
            now
          )
        );
        await env.DB.batch(statements);
      }

      return new Response(JSON.stringify({
        success: true,
        signedPrekeyUploaded: Boolean(body.signedPrekey),
        oneTimePrekeysUploaded: oneTimePrekeys.length,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Get summary of server-side prekey availability for current user
    if (path === '/users/prekeys/status' && request.method === 'GET') {
      const userId = await authenticateUser();
      if (!userId) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const signedPrekeyRow = await env.DB.prepare(
        `SELECT key_id, created_at
         FROM user_prekeys
         WHERE user_id = ? AND prekey_type = ?
         ORDER BY created_at DESC
         LIMIT 1`
      ).bind(userId, 'signed').first();

      const oneTimeCountRow = await env.DB.prepare(
        `SELECT COUNT(*) as count
         FROM user_prekeys
         WHERE user_id = ? AND prekey_type = ? AND is_used = 0`
      ).bind(userId, 'one_time').first();

      return new Response(JSON.stringify({
        signedPrekeyKeyId: signedPrekeyRow ? signedPrekeyRow.key_id : null,
        signedPrekeyCreatedAt: signedPrekeyRow ? signedPrekeyRow.created_at : null,
        oneTimePrekeyCount: oneTimeCountRow ? Number(oneTimeCountRow.count) : 0,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Fetch recipient prekey bundle
    if (path.match(/^\/users\/[^\/]+\/prekeys$/) && request.method === 'GET') {
      const requesterId = await authenticateUser();
      if (!requesterId) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const targetUserId = path.split('/')[2];

      const identity = await env.DB.prepare(
        'SELECT identity_key, signing_key, fingerprint FROM user_identity_keys WHERE user_id = ?'
      ).bind(targetUserId).first();

      if (!identity) {
        return new Response(JSON.stringify({ error: 'Key material not found' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 404,
        });
      }

      const signedPrekey = await env.DB.prepare(
        `SELECT key_id, public_key, signature, created_at
         FROM user_prekeys
         WHERE user_id = ? AND prekey_type = ?
         ORDER BY created_at DESC
         LIMIT 1`
      ).bind(targetUserId, 'signed').first();

      const oneTimePrekey = await env.DB.prepare(
        `SELECT id, key_id, public_key
         FROM user_prekeys
         WHERE user_id = ? AND prekey_type = ? AND is_used = 0
         ORDER BY created_at ASC
         LIMIT 1`
      ).bind(targetUserId, 'one_time').first();

      if (oneTimePrekey) {
        await env.DB.prepare(
          'UPDATE user_prekeys SET is_used = 1, used_at = ? WHERE id = ?'
        ).bind(Date.now(), oneTimePrekey.id).run();
      }

      return new Response(JSON.stringify({
        identityKey: identity.identity_key,
        signingKey: identity.signing_key,
        fingerprint: identity.fingerprint,
        signedPrekey: signedPrekey
          ? {
              keyId: signedPrekey.key_id,
              publicKey: signedPrekey.public_key,
              signature: signedPrekey.signature,
              createdAt: signedPrekey.created_at,
            }
          : null,
        oneTimePrekey: oneTimePrekey
          ? {
              keyId: oneTimePrekey.key_id,
              publicKey: oneTimePrekey.public_key,
            }
          : null,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Admin: Get all users with full details
    if (path === '/admin/users' && request.method === 'GET') {
      const authHeader = request.headers.get('Authorization');
      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const adminId = authHeader.replace('Bearer ', '');
      const admin = await env.DB.prepare(
        'SELECT role FROM users WHERE id = ?'
      ).bind(adminId).first();

      if (!admin || admin.role !== 'admin') {
        return new Response(JSON.stringify({ error: 'Forbidden: Admin access required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const users = await env.DB.prepare(
        'SELECT id, username, role, is_active, can_send_images, lastSeen, created_at, disabled_at, disabled_by FROM users ORDER BY created_at DESC'
      ).all();

      return new Response(JSON.stringify(users.results), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Admin: Update user status (enable/disable)
    if (path.match(/^\/admin\/users\/[^\/]+\/status$/) && request.method === 'PUT') {
      const userId = path.split('/')[3];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const adminId = authHeader.replace('Bearer ', '');
      const admin = await env.DB.prepare(
        'SELECT role FROM users WHERE id = ?'
      ).bind(adminId).first();

      if (!admin || admin.role !== 'admin') {
        return new Response(JSON.stringify({ error: 'Forbidden: Admin access required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const body = await request.json() as { is_active: number; disabled_by: string };
      const now = Date.now();

      if (body.is_active === 0) {
        // Disabling user
        await env.DB.prepare(
          'UPDATE users SET is_active = ?, disabled_at = ?, disabled_by = ? WHERE id = ?'
        ).bind(0, now, body.disabled_by, userId).run();
      } else {
        // Enabling user
        await env.DB.prepare(
          'UPDATE users SET is_active = ?, disabled_at = NULL, disabled_by = NULL WHERE id = ?'
        ).bind(1, userId).run();
      }

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Admin: Update user permissions (image sending)
    if (path.match(/^\/admin\/users\/[^\/]+\/permissions$/) && request.method === 'PUT') {
      const userId = path.split('/')[3];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const adminId = authHeader.replace('Bearer ', '');
      const admin = await env.DB.prepare(
        'SELECT role FROM users WHERE id = ?'
      ).bind(adminId).first();

      if (!admin || admin.role !== 'admin') {
        return new Response(JSON.stringify({ error: 'Forbidden: Admin access required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const body = await request.json() as { can_send_images: number };

      await env.DB.prepare(
        'UPDATE users SET can_send_images = ? WHERE id = ?'
      ).bind(body.can_send_images, userId).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Admin: Update user role
    if (path.match(/^\/admin\/users\/[^\/]+\/role$/) && request.method === 'PUT') {
      const userId = path.split('/')[3];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const adminId = authHeader.replace('Bearer ', '');
      const admin = await env.DB.prepare(
        'SELECT role FROM users WHERE id = ?'
      ).bind(adminId).first();

      if (!admin || admin.role !== 'admin') {
        return new Response(JSON.stringify({ error: 'Forbidden: Admin access required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const body = await request.json() as { role: string };

      await env.DB.prepare(
        'UPDATE users SET role = ? WHERE id = ?'
      ).bind(body.role, userId).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // === GROUP ENDPOINTS ===

    // Create group
    if (path === '/groups' && request.method === 'POST') {
      const authHeader = request.headers.get('Authorization');
      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const body = await request.json() as {
        name: string;
        description?: string;
        avatar?: string;
        memberIds: string[];
        settings?: any;
      };

      if (!body.name || body.name.trim().length === 0) {
        return new Response(JSON.stringify({ error: 'Group name is required' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      const groupId = crypto.randomUUID();
      const now = Date.now();
      const defaultSettings = {
        messagePermission: 'everyone',
        metadataPermission: 'admins_only',
        joinApproval: false,
        maxMembers: 1024,
      };
      const settings = { ...defaultSettings, ...(body.settings || {}) };

      // Create group
      await env.DB.prepare(
        'INSERT INTO groups (id, name, description, avatar, owner_id, created_at, updated_at, settings) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(groupId, body.name, body.description || null, body.avatar || null, userId, now, now, JSON.stringify(settings)).run();

      // Add owner as admin
      await env.DB.prepare(
        'INSERT INTO group_members (group_id, user_id, role, joined_at, added_by) VALUES (?, ?, ?, ?, ?)'
      ).bind(groupId, userId, 'owner', now, userId).run();

      // Add initial members
      if (body.memberIds && body.memberIds.length > 0) {
        for (const memberId of body.memberIds) {
          if (memberId !== userId) {
            await env.DB.prepare(
              'INSERT INTO group_members (group_id, user_id, role, joined_at, added_by) VALUES (?, ?, ?, ?, ?)'
            ).bind(groupId, memberId, 'member', now, userId).run();
          }
        }
      }

      // Create system message for group creation
      await env.DB.prepare(
        'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event) VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).bind(crypto.randomUUID(), groupId, userId, 'Group created', now, 'system', 'group_created').run();

      return new Response(JSON.stringify({ id: groupId, name: body.name, owner_id: userId, created_at: now, settings }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 201,
      });
    }

    // Get user's groups
    if (path === '/groups' && request.method === 'GET') {
      const authHeader = request.headers.get('Authorization');
      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const groups = await env.DB.prepare(
        `SELECT g.*, gm.role, gm.joined_at
         FROM groups g
         INNER JOIN group_members gm ON g.id = gm.group_id
         WHERE gm.user_id = ?
         ORDER BY g.updated_at DESC`
      ).bind(userId).all();

      const groupsWithSettings = groups.results.map((g: any) => ({
        ...g,
        settings: g.settings ? JSON.parse(g.settings) : null,
      }));

      return new Response(JSON.stringify(groupsWithSettings), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Get group details
    if (path.match(/^\/groups\/[^\/]+$/) && request.method === 'GET') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');

      // Check if user is a member
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership) {
        return new Response(JSON.stringify({ error: 'Not a member of this group' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const group = await env.DB.prepare(
        'SELECT * FROM groups WHERE id = ?'
      ).bind(groupId).first();

      if (!group) {
        return new Response(JSON.stringify({ error: 'Group not found' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 404,
        });
      }

      const groupWithSettings = {
        ...group,
        settings: group.settings ? JSON.parse(group.settings as string) : null,
        userRole: membership.role,
      };

      return new Response(JSON.stringify(groupWithSettings), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Update group metadata
    if (path.match(/^\/groups\/[^\/]+$/) && request.method === 'PUT') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const body = await request.json() as {
        name?: string;
        description?: string;
        avatar?: string;
        settings?: any;
      };

      // Check permissions
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership) {
        return new Response(JSON.stringify({ error: 'Not a member of this group' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const group = await env.DB.prepare(
        'SELECT settings, owner_id FROM groups WHERE id = ?'
      ).bind(groupId).first();

      if (!group) {
        return new Response(JSON.stringify({ error: 'Group not found' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 404,
        });
      }

      const settings = group.settings ? JSON.parse(group.settings as string) : {};
      const isAdmin = membership.role === 'admin' || membership.role === 'owner';

      if (settings.metadataPermission === 'admins_only' && !isAdmin) {
        return new Response(JSON.stringify({ error: 'Only admins can update group metadata' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const now = Date.now();
      const updates: string[] = [];
      const params: any[] = [];

      if (body.name !== undefined) {
        updates.push('name = ?');
        params.push(body.name);
      }
      if (body.description !== undefined) {
        updates.push('description = ?');
        params.push(body.description);
      }
      if (body.avatar !== undefined) {
        updates.push('avatar = ?');
        params.push(body.avatar);
      }
      if (body.settings !== undefined && isAdmin) {
        updates.push('settings = ?');
        params.push(JSON.stringify(body.settings));
      }

      updates.push('updated_at = ?');
      params.push(now);
      params.push(groupId);

      await env.DB.prepare(
        `UPDATE groups SET ${updates.join(', ')} WHERE id = ?`
      ).bind(...params).run();

      // Create system message
      await env.DB.prepare(
        'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event) VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).bind(crypto.randomUUID(), groupId, userId, 'Group metadata updated', now, 'system', 'metadata_updated').run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Get group members
    if (path.match(/^\/groups\/[^\/]+\/members$/) && request.method === 'GET') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');

      // Check if user is a member
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership) {
        return new Response(JSON.stringify({ error: 'Not a member of this group' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const members = await env.DB.prepare(
        `SELECT gm.*, u.username, u.avatar
         FROM group_members gm
         INNER JOIN users u ON gm.user_id = u.id
         WHERE gm.group_id = ?
         ORDER BY gm.joined_at ASC`
      ).bind(groupId).all();

      return new Response(JSON.stringify(members.results), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Add members to group
    if (path.match(/^\/groups\/[^\/]+\/members$/) && request.method === 'POST') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const body = await request.json() as { userIds: string[] };

      // Check if user is admin
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership || (membership.role !== 'admin' && membership.role !== 'owner')) {
        return new Response(JSON.stringify({ error: 'Only admins can add members' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const now = Date.now();
      const added: string[] = [];

      for (const newUserId of body.userIds) {
        const existing = await env.DB.prepare(
          'SELECT user_id FROM group_members WHERE group_id = ? AND user_id = ?'
        ).bind(groupId, newUserId).first();

        if (!existing) {
          await env.DB.prepare(
            'INSERT INTO group_members (group_id, user_id, role, joined_at, added_by) VALUES (?, ?, ?, ?, ?)'
          ).bind(groupId, newUserId, 'member', now, userId).run();

          // Create system message
          const newUser = await env.DB.prepare(
            'SELECT username FROM users WHERE id = ?'
          ).bind(newUserId).first();

          await env.DB.prepare(
            'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
          ).bind(
            crypto.randomUUID(),
            groupId,
            userId,
            `${newUser?.username || 'User'} was added to the group`,
            now,
            'system',
            'member_added',
            JSON.stringify({ added_user_id: newUserId })
          ).run();

          added.push(newUserId);
        }
      }

      // Update group updated_at
      await env.DB.prepare(
        'UPDATE groups SET updated_at = ? WHERE id = ?'
      ).bind(now, groupId).run();

      return new Response(JSON.stringify({ success: true, added }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Remove member from group
    if (path.match(/^\/groups\/[^\/]+\/members\/[^\/]+$/) && request.method === 'DELETE') {
      const parts = path.split('/');
      const groupId = parts[2];
      const targetUserId = parts[4];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');

      // Check permissions
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership || (membership.role !== 'admin' && membership.role !== 'owner')) {
        return new Response(JSON.stringify({ error: 'Only admins can remove members' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      // Cannot remove owner
      const group = await env.DB.prepare(
        'SELECT owner_id FROM groups WHERE id = ?'
      ).bind(groupId).first();

      if (group?.owner_id === targetUserId) {
        return new Response(JSON.stringify({ error: 'Cannot remove group owner' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Remove member
      await env.DB.prepare(
        'DELETE FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, targetUserId).run();

      // Create system message
      const now = Date.now();
      const targetUser = await env.DB.prepare(
        'SELECT username FROM users WHERE id = ?'
      ).bind(targetUserId).first();

      await env.DB.prepare(
        'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(
        crypto.randomUUID(),
        groupId,
        userId,
        `${targetUser?.username || 'User'} was removed from the group`,
        now,
        'system',
        'member_removed',
        JSON.stringify({ removed_user_id: targetUserId })
      ).run();

      // Update group updated_at
      await env.DB.prepare(
        'UPDATE groups SET updated_at = ? WHERE id = ?'
      ).bind(now, groupId).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Leave group
    if (path.match(/^\/groups\/[^\/]+\/leave$/) && request.method === 'POST') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');

      // Check if user is owner
      const group = await env.DB.prepare(
        'SELECT owner_id FROM groups WHERE id = ?'
      ).bind(groupId).first();

      if (group?.owner_id === userId) {
        return new Response(JSON.stringify({ error: 'Group owner cannot leave. Transfer ownership or delete the group.' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Remove member
      await env.DB.prepare(
        'DELETE FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).run();

      // Create system message
      const now = Date.now();
      const user = await env.DB.prepare(
        'SELECT username FROM users WHERE id = ?'
      ).bind(userId).first();

      await env.DB.prepare(
        'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event) VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).bind(crypto.randomUUID(), groupId, userId, `${user?.username || 'User'} left the group`, now, 'system', 'member_left').run();

      // Update group updated_at
      await env.DB.prepare(
        'UPDATE groups SET updated_at = ? WHERE id = ?'
      ).bind(now, groupId).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Update member role
    if (path.match(/^\/groups\/[^\/]+\/members\/[^\/]+\/role$/) && request.method === 'PUT') {
      const parts = path.split('/');
      const groupId = parts[2];
      const targetUserId = parts[4];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const body = await request.json() as { role: 'admin' | 'member' };

      // Only owner can change roles
      const group = await env.DB.prepare(
        'SELECT owner_id FROM groups WHERE id = ?'
      ).bind(groupId).first();

      if (group?.owner_id !== userId) {
        return new Response(JSON.stringify({ error: 'Only group owner can change member roles' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      // Update role
      await env.DB.prepare(
        'UPDATE group_members SET role = ? WHERE group_id = ? AND user_id = ?'
      ).bind(body.role, groupId, targetUserId).run();

      // Create system message
      const now = Date.now();
      const targetUser = await env.DB.prepare(
        'SELECT username FROM users WHERE id = ?'
      ).bind(targetUserId).first();

      const event = body.role === 'admin' ? 'admin_promoted' : 'admin_demoted';
      const message = body.role === 'admin' 
        ? `${targetUser?.username || 'User'} was promoted to admin`
        : `${targetUser?.username || 'User'} was demoted to member`;

      await env.DB.prepare(
        'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(
        crypto.randomUUID(),
        groupId,
        userId,
        message,
        now,
        'system',
        event,
        JSON.stringify({ target_user_id: targetUserId, new_role: body.role })
      ).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Get group messages
    if (path.match(/^\/groups\/[^\/]+\/messages$/) && request.method === 'GET') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');

      // Check if user is a member
      const membership = await env.DB.prepare(
        'SELECT joined_at FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership) {
        return new Response(JSON.stringify({ error: 'Not a member of this group' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const limit = parseInt(url.searchParams.get('limit') || '200');
      const before = url.searchParams.get('before');

      let query = `
        SELECT gm.*, u.username as from_username
        FROM group_messages gm
        LEFT JOIN users u ON gm.from_user = u.id
        WHERE gm.group_id = ? AND gm.timestamp >= ?
      `;
      const params = [groupId, membership.joined_at];

      if (before) {
        query += ' AND gm.timestamp < ?';
        params.push(parseInt(before));
      }

      query += ' ORDER BY gm.timestamp DESC LIMIT ?';
      params.push(limit);

      const messages = await env.DB.prepare(query).bind(...params).all();

      // Parse metadata for messages that have it
      const messagesWithMetadata = messages.results.map((m: any) => ({
        ...m,
        metadata: m.metadata ? JSON.parse(m.metadata) : null,
      })).reverse();

      return new Response(JSON.stringify(messagesWithMetadata), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Create invite link
    if (path.match(/^\/groups\/[^\/]+\/invite$/) && request.method === 'POST') {
      const groupId = path.split('/')[2];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const body = await request.json() as {
        expiresIn?: number; // milliseconds
        maxUses?: number;
      };

      // Check if user is admin
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership || (membership.role !== 'admin' && membership.role !== 'owner')) {
        return new Response(JSON.stringify({ error: 'Only admins can create invite links' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      const linkId = crypto.randomUUID();
      const linkCode = crypto.randomUUID().replace(/-/g, '').substring(0, 16);
      const now = Date.now();
      const expiresAt = body.expiresIn ? now + body.expiresIn : null;

      await env.DB.prepare(
        'INSERT INTO group_invite_links (id, group_id, link_code, created_by, created_at, expires_at, max_uses, current_uses, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(linkId, groupId, linkCode, userId, now, expiresAt, body.maxUses || null, 0, 1).run();

      return new Response(JSON.stringify({
        id: linkId,
        link_code: linkCode,
        expires_at: expiresAt,
        max_uses: body.maxUses,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 201,
      });
    }

    // Join via invite link
    if (path === '/groups/join' && request.method === 'POST') {
      const authHeader = request.headers.get('Authorization');
      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');
      const body = await request.json() as { linkCode: string };

      // Get invite link
      const link = await env.DB.prepare(
        'SELECT * FROM group_invite_links WHERE link_code = ? AND is_active = 1'
      ).bind(body.linkCode).first();

      if (!link) {
        return new Response(JSON.stringify({ error: 'Invalid or expired invite link' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 404,
        });
      }

      const now = Date.now();

      // Check if link expired
      if (link.expires_at && Number(link.expires_at) < now) {
        return new Response(JSON.stringify({ error: 'Invite link has expired' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Check max uses
      if (link.max_uses && Number(link.current_uses) >= Number(link.max_uses)) {
        return new Response(JSON.stringify({ error: 'Invite link has reached maximum uses' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Check if already a member
      const existing = await env.DB.prepare(
        'SELECT user_id FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(link.group_id, userId).first();

      if (existing) {
        return new Response(JSON.stringify({ error: 'Already a member of this group' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400,
        });
      }

      // Add member
      await env.DB.prepare(
        'INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)'
      ).bind(link.group_id, userId, 'member', now).run();

      // Update link usage
      await env.DB.prepare(
        'UPDATE group_invite_links SET current_uses = current_uses + 1 WHERE id = ?'
      ).bind(link.id).run();

      // Create system message
      const user = await env.DB.prepare(
        'SELECT username FROM users WHERE id = ?'
      ).bind(userId).first();

      await env.DB.prepare(
        'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, system_event) VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).bind(
        crypto.randomUUID(),
        link.group_id,
        userId,
        `${user?.username || 'User'} joined via invite link`,
        now,
        'system',
        'member_added'
      ).run();

      return new Response(JSON.stringify({ success: true, group_id: link.group_id }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Revoke invite link
    if (path.match(/^\/groups\/[^\/]+\/invite\/[^\/]+$/) && request.method === 'DELETE') {
      const parts = path.split('/');
      const groupId = parts[2];
      const linkId = parts[4];
      const authHeader = request.headers.get('Authorization');

      if (!authHeader) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401,
        });
      }

      const userId = authHeader.replace('Bearer ', '');

      // Check if user is admin
      const membership = await env.DB.prepare(
        'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
      ).bind(groupId, userId).first();

      if (!membership || (membership.role !== 'admin' && membership.role !== 'owner')) {
        return new Response(JSON.stringify({ error: 'Only admins can revoke invite links' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 403,
        });
      }

      await env.DB.prepare(
        'UPDATE group_invite_links SET is_active = 0 WHERE id = ? AND group_id = ?'
      ).bind(linkId, groupId).run();

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
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
