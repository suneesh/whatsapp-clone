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
  role?: string;
  is_active?: number;
  can_send_images?: number;
  created_at?: number;
  disabled_at?: number;
  disabled_by?: string;
}

export interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
  type?: 'text' | 'image';
  imageData?: string;
  encrypted?: boolean; // Server-validated E2EE flag
}

export interface WSMessage {
  type: 'auth' | 'message' | 'typing' | 'status' | 'online' | 'read' | 'error' | 'group_message' | 'group_read' | 'group_typing' | 'group_event';
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

export interface Group {
  id: string;
  name: string;
  description?: string;
  avatar?: string;
  owner_id: string;
  created_at: number;
  updated_at: number;
  settings: GroupSettings;
}

export interface GroupSettings {
  messagePermission: 'everyone' | 'admins_only';
  metadataPermission: 'everyone' | 'admins_only';
  joinApproval: boolean;
  maxMembers: number;
}

export interface GroupMember {
  group_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'member';
  joined_at: number;
  added_by?: string;
  username?: string;
  avatar?: string;
}

export interface GroupMessage {
  id: string;
  group_id: string;
  from_user: string;
  content: string;
  timestamp: number;
  type: 'text' | 'image' | 'system';
  imageData?: string;
  system_event?: 'member_added' | 'member_removed' | 'member_left' | 'admin_promoted' | 'admin_demoted' | 'metadata_updated' | 'group_created';
  metadata?: any;
  from_username?: string;
}

export interface GroupInviteLink {
  id: string;
  group_id: string;
  link_code: string;
  created_by: string;
  created_at: number;
  expires_at?: number;
  max_uses?: number;
  current_uses: number;
  is_active: number;
}
