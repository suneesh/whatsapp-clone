export interface Env {
  CHAT_ROOM: DurableObjectNamespace;
  DB: D1Database;
  ENVIRONMENT: string;
}

export interface User {
  id: string;
  username: string;
  avatar?: string;
  lastSeen: number;
}

export interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
}

export interface WSMessage {
  type: 'auth' | 'message' | 'typing' | 'status' | 'online' | 'read' | 'error';
  payload: any;
}

export interface ReadReceiptPayload {
  messageIds: string[];
  to: string;
  readBy?: string;
}

export interface ChatSession {
  userId: string;
  username: string;
  ws: WebSocket;
}
