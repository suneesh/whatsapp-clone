import { ChatSession, WSMessage, Message, Env, GroupMessage } from './types';

export class ChatRoom implements DurableObject {
  private sessions: Map<string, ChatSession>;
  private state: DurableObjectState;
  private env: Env;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
    this.sessions = new Map();
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/websocket') {
      if (request.headers.get('Upgrade') !== 'websocket') {
        return new Response('Expected WebSocket', { status: 426 });
      }

      const pair = new WebSocketPair();
      const [client, server] = Object.values(pair);

      await this.handleWebSocket(server);

      return new Response(null, {
        status: 101,
        webSocket: client,
      });
    }

    return new Response('Not found', { status: 404 });
  }

  async handleWebSocket(ws: WebSocket): Promise<void> {
    ws.accept();

    let session: ChatSession | null = null;

    ws.addEventListener('message', async (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data as string);

        switch (data.type) {
          case 'auth':
            // Validate that the user exists in the database
            try {
              const userExists = await this.env.DB.prepare(
                'SELECT id FROM users WHERE id = ?'
              ).bind(data.payload.userId).first();

              if (!userExists) {
                console.log(`[Auth] User ${data.payload.userId} not found in database, rejecting connection`);
                ws.send(JSON.stringify({
                  type: 'error',
                  payload: { message: 'User not found. Please log in again.' },
                }));
                ws.close();
                return;
              }
            } catch (error) {
              console.error('[Auth] Error validating user:', error);
            }

            // Clean up any existing session for this user (e.g., after re-login)
            if (this.sessions.has(data.payload.userId)) {
              console.log(`[Auth] Cleaning up existing session for user ${data.payload.userId}`);
              const oldSession = this.sessions.get(data.payload.userId);
              if (oldSession) {
                try {
                  oldSession.ws.close();
                } catch (error) {
                  console.error('[Auth] Error closing old session:', error);
                }
              }
            }

            // Create new session
            session = {
              userId: data.payload.userId,
              username: data.payload.username,
              ws,
            };
            this.sessions.set(data.payload.userId, session);

            // Notify all users about online status
            this.broadcast({
              type: 'online',
              payload: {
                userId: data.payload.userId,
                username: data.payload.username,
                online: true,
              },
            }, data.payload.userId);

            // Send current online users to the new user
            const onlineUsers = Array.from(this.sessions.values()).map(s => ({
              userId: s.userId,
              username: s.username,
              online: true,
            }));

            ws.send(JSON.stringify({
              type: 'online',
              payload: { users: onlineUsers },
            }));
            break;

          case 'message':
            if (session) {
              const messageType = data.payload.messageType || 'text';

              // Check user permissions and status
              try {
                const sender = await this.env.DB.prepare(
                  'SELECT is_active, can_send_images FROM users WHERE id = ?'
                ).bind(session.userId).first();

                if (!sender) {
                  ws.send(JSON.stringify({
                    type: 'error',
                    payload: { message: 'User not found. Please log in again.' },
                  }));
                  ws.close();
                  return;
                }

                // Check if user is active
                if (sender.is_active === 0) {
                  ws.send(JSON.stringify({
                    type: 'error',
                    payload: { message: 'Your account has been disabled by an administrator.' },
                  }));
                  ws.close();
                  return;
                }

                // Check image sending permission
                if (messageType === 'image' && sender.can_send_images === 0) {
                  ws.send(JSON.stringify({
                    type: 'error',
                    payload: { message: 'You do not have permission to send images.' },
                  }));
                  return;
                }
              } catch (error) {
                console.error('Failed to check user permissions:', error);
              }

              const message: Message = {
                id: crypto.randomUUID(),
                from: session.userId,
                to: data.payload.to,
                content: data.payload.content,
                timestamp: Date.now(),
                status: 'sent',
                type: messageType,
                imageData: data.payload.imageData,
              };

              console.log(`Message from ${session.userId} to ${data.payload.to}: ${messageType === 'image' ? '📷 Image' : data.payload.content}`);
              console.log(`Active sessions: ${Array.from(this.sessions.keys()).join(', ')}`);

              // Save message to database
              try {
                // Check if both users exist in the database
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
                console.log(`Sending to recipient ${data.payload.to}`);
                recipient.ws.send(JSON.stringify({
                  type: 'message',
                  payload: message,
                }));
                message.status = 'delivered';
                
                // Update message status in database
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

          case 'typing':
            if (session) {
              const recipient = this.sessions.get(data.payload.to);
              if (recipient) {
                recipient.ws.send(JSON.stringify({
                  type: 'typing',
                  payload: {
                    from: session.userId,
                    username: session.username,
                    typing: data.payload.typing,
                  },
                }));
              }
            }
            break;

          case 'status':
            if (session && data.payload.messageId) {
              const recipient = this.sessions.get(data.payload.to);
              if (recipient) {
                recipient.ws.send(JSON.stringify({
                  type: 'status',
                  payload: {
                    messageId: data.payload.messageId,
                    status: data.payload.status,
                  },
                }));
              }
            }
            break;

          case 'read':
            if (session && data.payload.messageIds && data.payload.to) {
              const messageIds = data.payload.messageIds as string[];

              console.log(`[Read Receipt] User ${session.userId} read ${messageIds.length} messages`);
              console.log(`[Read Receipt] Notifying sender: ${data.payload.to}`);

              // Update message status in database
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

          case 'group_message':
            if (session) {
              const messageType = data.payload.messageType || 'text';
              const groupId = data.payload.groupId;

              // Check user permissions
              try {
                const sender = await this.env.DB.prepare(
                  'SELECT is_active, can_send_images FROM users WHERE id = ?'
                ).bind(session.userId).first();

                if (!sender || sender.is_active === 0) {
                  ws.send(JSON.stringify({
                    type: 'error',
                    payload: { message: 'Your account has been disabled.' },
                  }));
                  return;
                }

                if (messageType === 'image' && sender.can_send_images === 0) {
                  ws.send(JSON.stringify({
                    type: 'error',
                    payload: { message: 'You do not have permission to send images.' },
                  }));
                  return;
                }

                // Check group membership and permissions
                const membership = await this.env.DB.prepare(
                  'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
                ).bind(groupId, session.userId).first();

                if (!membership) {
                  ws.send(JSON.stringify({
                    type: 'error',
                    payload: { message: 'You are not a member of this group.' },
                  }));
                  return;
                }

                // Check message permissions
                const group = await this.env.DB.prepare(
                  'SELECT settings FROM groups WHERE id = ?'
                ).bind(groupId).first();

                if (group) {
                  const settings = group.settings ? JSON.parse(group.settings as string) : {};
                  if (settings.messagePermission === 'admins_only' && 
                      membership.role !== 'admin' && membership.role !== 'owner') {
                    ws.send(JSON.stringify({
                      type: 'error',
                      payload: { message: 'Only admins can send messages in this group.' },
                    }));
                    return;
                  }
                }
              } catch (error) {
                console.error('Failed to check group permissions:', error);
              }

              // Create and save group message
              const groupMessage: GroupMessage = {
                id: crypto.randomUUID(),
                group_id: groupId,
                from_user: session.userId,
                content: data.payload.content,
                timestamp: Date.now(),
                type: messageType,
                imageData: data.payload.imageData,
                from_username: session.username,
              };

              try {
                await this.env.DB.prepare(
                  'INSERT INTO group_messages (id, group_id, from_user, content, timestamp, type, imageData) VALUES (?, ?, ?, ?, ?, ?, ?)'
                ).bind(
                  groupMessage.id,
                  groupMessage.group_id,
                  groupMessage.from_user,
                  groupMessage.content,
                  groupMessage.timestamp,
                  groupMessage.type,
                  groupMessage.imageData || null
                ).run();
                console.log(`Group message saved: ${groupMessage.id} in group ${groupId}`);

                // Update group's updated_at timestamp
                await this.env.DB.prepare(
                  'UPDATE groups SET updated_at = ? WHERE id = ?'
                ).bind(groupMessage.timestamp, groupId).run();
              } catch (error) {
                console.error('Failed to save group message:', error);
              }

              // Get all group members
              try {
                const members = await this.env.DB.prepare(
                  'SELECT user_id FROM group_members WHERE group_id = ?'
                ).bind(groupId).all();

                // Broadcast to all online group members
                const memberIds = members.results.map((m: any) => m.user_id);
                for (const memberId of memberIds) {
                  const memberSession = this.sessions.get(memberId as string);
                  if (memberSession) {
                    memberSession.ws.send(JSON.stringify({
                      type: 'group_message',
                      payload: groupMessage,
                    }));
                  }
                }

                console.log(`Group message broadcasted to ${memberIds.length} members`);
              } catch (error) {
                console.error('Failed to broadcast group message:', error);
              }
            }
            break;

          case 'group_read':
            if (session && data.payload.messageId && data.payload.groupId) {
              try {
                const now = Date.now();
                await this.env.DB.prepare(
                  'INSERT OR REPLACE INTO group_message_reads (message_id, user_id, read_at) VALUES (?, ?, ?)'
                ).bind(data.payload.messageId, session.userId, now).run();

                // Get all group members
                const members = await this.env.DB.prepare(
                  'SELECT user_id FROM group_members WHERE group_id = ?'
                ).bind(data.payload.groupId).all();

                // Notify all online group members
                const memberIds = members.results.map((m: any) => m.user_id);
                for (const memberId of memberIds) {
                  const memberSession = this.sessions.get(memberId as string);
                  if (memberSession && memberId !== session.userId) {
                    memberSession.ws.send(JSON.stringify({
                      type: 'group_read',
                      payload: {
                        messageId: data.payload.messageId,
                        groupId: data.payload.groupId,
                        userId: session.userId,
                        readAt: now,
                      },
                    }));
                  }
                }
              } catch (error) {
                console.error('Failed to update group read receipt:', error);
              }
            }
            break;

          case 'group_typing':
            if (session && data.payload.groupId) {
              // Get all group members
              try {
                const members = await this.env.DB.prepare(
                  'SELECT user_id FROM group_members WHERE group_id = ?'
                ).bind(data.payload.groupId).all();

                // Notify all online group members except sender
                const memberIds = members.results.map((m: any) => m.user_id);
                for (const memberId of memberIds) {
                  if (memberId !== session.userId) {
                    const memberSession = this.sessions.get(memberId as string);
                    if (memberSession) {
                      memberSession.ws.send(JSON.stringify({
                        type: 'group_typing',
                        payload: {
                          groupId: data.payload.groupId,
                          userId: session.userId,
                          username: session.username,
                          typing: data.payload.typing,
                        },
                      }));
                    }
                  }
                }
              } catch (error) {
                console.error('Failed to broadcast group typing:', error);
              }
            }
            break;

          case 'group_event':
            // Handle group events like member added, removed, etc.
            if (session && data.payload.groupId && data.payload.event) {
              try {
                // Verify user is a member or admin
                const membership = await this.env.DB.prepare(
                  'SELECT role FROM group_members WHERE group_id = ? AND user_id = ?'
                ).bind(data.payload.groupId, session.userId).first();

                if (membership) {
                  // Get all group members
                  const members = await this.env.DB.prepare(
                    'SELECT user_id FROM group_members WHERE group_id = ?'
                  ).bind(data.payload.groupId).all();

                  // Broadcast event to all online group members
                  const memberIds = members.results.map((m: any) => m.user_id);
                  for (const memberId of memberIds) {
                    const memberSession = this.sessions.get(memberId as string);
                    if (memberSession) {
                      memberSession.ws.send(JSON.stringify({
                        type: 'group_event',
                        payload: data.payload,
                      }));
                    }
                  }
                }
              } catch (error) {
                console.error('Failed to broadcast group event:', error);
              }
            }
            break;
        }
      } catch (error) {
        ws.send(JSON.stringify({
          type: 'error',
          payload: { message: 'Invalid message format' },
        }));
      }
    });

    ws.addEventListener('close', () => {
      if (session) {
        this.sessions.delete(session.userId);

        // Notify all users about offline status
        this.broadcast({
          type: 'online',
          payload: {
            userId: session.userId,
            username: session.username,
            online: false,
          },
        });
      }
    });

    ws.addEventListener('error', () => {
      if (session) {
        this.sessions.delete(session.userId);
      }
    });
  }

  broadcast(message: WSMessage, excludeUserId?: string): void {
    const messageStr = JSON.stringify(message);
    for (const [userId, session] of this.sessions) {
      if (userId !== excludeUserId) {
        try {
          session.ws.send(messageStr);
        } catch (error) {
          this.sessions.delete(userId);
        }
      }
    }
  }
}
