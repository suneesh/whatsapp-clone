import { ChatSession, WSMessage, Message } from './types';

export class ChatRoom implements DurableObject {
  private sessions: Map<string, ChatSession>;
  private state: DurableObjectState;

  constructor(state: DurableObjectState) {
    this.state = state;
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
            }));

            ws.send(JSON.stringify({
              type: 'online',
              payload: { users: onlineUsers },
            }));
            break;

          case 'message':
            if (session) {
              const message: Message = {
                id: crypto.randomUUID(),
                from: session.userId,
                to: data.payload.to,
                content: data.payload.content,
                timestamp: Date.now(),
                status: 'sent',
              };

              console.log(`Message from ${session.userId} to ${data.payload.to}: ${data.payload.content}`);
              console.log(`Active sessions: ${Array.from(this.sessions.keys()).join(', ')}`);

              // Send to recipient
              const recipient = this.sessions.get(data.payload.to);
              if (recipient) {
                console.log(`Sending to recipient ${data.payload.to}`);
                recipient.ws.send(JSON.stringify({
                  type: 'message',
                  payload: message,
                }));
                message.status = 'delivered';
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
