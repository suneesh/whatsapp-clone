import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useWebSocket } from '../hooks/useWebSocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  
  sentMessages: string[] = [];

  constructor(public url: string) {
    // Simulate connection opening after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // Always accept messages when readyState is OPEN
    if (this.readyState === MockWebSocket.OPEN) {
      this.sentMessages.push(data);
    } else {
      console.warn('MockWebSocket: Cannot send, readyState is', this.readyState);
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    // Don't use setTimeout - call onclose synchronously to avoid timer issues in tests
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper to simulate error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

describe('useWebSocket Hook', () => {
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    
    const MockWebSocketConstructor = vi.fn((url: string) => {
      mockWebSocket = new MockWebSocket(url);
      return mockWebSocket as any;
    }) as any;
    
    // Add static properties that the hook uses
    MockWebSocketConstructor.CONNECTING = 0;
    MockWebSocketConstructor.OPEN = 1;
    MockWebSocketConstructor.CLOSING = 2;
    MockWebSocketConstructor.CLOSED = 3;
    
    global.WebSocket = MockWebSocketConstructor;
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('should connect to WebSocket when enabled', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    expect(global.WebSocket).toHaveBeenCalled();
    
    // Fast-forward to connection open
    await vi.advanceTimersByTimeAsync(20);
    
    expect(mockWebSocket.readyState).toBe(MockWebSocket.OPEN);
  });

  it('should not connect when disabled', () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: false,
      })
    );

    expect(global.WebSocket).not.toHaveBeenCalled();
  });

  it('should send auth message after connection', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    const authMessage = mockWebSocket.sentMessages.find((msg) => {
      const parsed = JSON.parse(msg);
      return parsed.type === 'auth';
    });

    expect(authMessage).toBeDefined();
    const parsed = JSON.parse(authMessage!);
    expect(parsed.payload.userId).toBe('user1');
    expect(parsed.payload.username).toBe('Alice');
  });

  it('should handle incoming message', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    mockWebSocket.simulateMessage({
      type: 'message',
      payload: {
        id: 'msg1',
        from: 'user2',
        to: 'user1',
        content: 'Hello!',
        timestamp: Date.now(),
      },
    });

    expect(onMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'msg1',
        from: 'user2',
        content: 'Hello!',
      })
    );
  });

  it('should handle typing indicator', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    mockWebSocket.simulateMessage({
      type: 'typing',
      payload: {
        from: 'user2',
        typing: true,
      },
    });

    expect(onTyping).toHaveBeenCalledWith('user2', true);
  });

  it('should handle online status update', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    const users = [
      { userId: 'user2', username: 'Bob', online: true },
      { userId: 'user3', username: 'Charlie', online: false },
    ];

    mockWebSocket.simulateMessage({
      type: 'online',
      payload: { users },
    });

    expect(onOnlineStatus).toHaveBeenCalledWith(users);
  });

  it('should handle read receipt', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    mockWebSocket.simulateMessage({
      type: 'read',
      payload: {
        messageIds: ['msg1', 'msg2'],
      },
    });

    expect(onReadReceipt).toHaveBeenCalledWith(['msg1', 'msg2']);
  });

  it('should send message via WebSocket', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    const { result } = renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    result.current.sendMessage('user2', 'Hello Bob!');

    const messageMsg = mockWebSocket.sentMessages.find((msg) => {
      const parsed = JSON.parse(msg);
      return parsed.type === 'message';
    });

    expect(messageMsg).toBeDefined();
    const parsed = JSON.parse(messageMsg!);
    expect(parsed.payload.to).toBe('user2');
    expect(parsed.payload.content).toBe('Hello Bob!');
  });

  it('should send typing indicator', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    const { result } = renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    result.current.sendTyping('user2', true);

    const typingMsg = mockWebSocket.sentMessages.find((msg) => {
      const parsed = JSON.parse(msg);
      return parsed.type === 'typing';
    });

    expect(typingMsg).toBeDefined();
    const parsed = JSON.parse(typingMsg!);
    expect(parsed.payload.to).toBe('user2');
    expect(parsed.payload.typing).toBe(true);
  });

  it('should send read receipt', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    const { result } = renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    result.current.sendReadReceipt(['msg1', 'msg2'], 'user2');

    const readMsg = mockWebSocket.sentMessages.find((msg) => {
      const parsed = JSON.parse(msg);
      return parsed.type === 'read';
    });

    expect(readMsg).toBeDefined();
    const parsed = JSON.parse(readMsg!);
    expect(parsed.payload.messageIds).toEqual(['msg1', 'msg2']);
    expect(parsed.payload.to).toBe('user2');
  });

  it('should reconnect on connection close', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    // Wait for initial connection
    await vi.advanceTimersByTimeAsync(20);
    
    expect(mockWebSocket.readyState).toBe(MockWebSocket.OPEN);
    expect(global.WebSocket).toHaveBeenCalledTimes(1);

    // Simulate connection close - trigger onclose directly
    if (mockWebSocket.onclose) {
      mockWebSocket.readyState = MockWebSocket.CLOSED;
      mockWebSocket.onclose(new CloseEvent('close'));
    }

    // Should attempt reconnect after 3 seconds
    await vi.advanceTimersByTimeAsync(3100);

    // New WebSocket should be created
    expect(global.WebSocket).toHaveBeenCalledTimes(2);
  });

  it('should cleanup on unmount', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    const { unmount } = renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    const closeSpy = vi.spyOn(mockWebSocket, 'close');
    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  it('should return connected status', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();

    const { result } = renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        enabled: true,
      })
    );

    // Initially not connected
    expect(result.current.connected).toBe(false);

    // Wait for connection to open
    await vi.advanceTimersByTimeAsync(20);

    // Now should be connected
    expect(result.current.connected).toBe(true);
  });

  it('should handle group messages when callback provided', async () => {
    const onMessage = vi.fn();
    const onTyping = vi.fn();
    const onOnlineStatus = vi.fn();
    const onReadReceipt = vi.fn();
    const onGroupMessage = vi.fn();

    renderHook(() =>
      useWebSocket({
        userId: 'user1',
        username: 'Alice',
        onMessage,
        onTyping,
        onOnlineStatus,
        onReadReceipt,
        onGroupMessage,
        enabled: true,
      })
    );

    await vi.advanceTimersByTimeAsync(20);

    mockWebSocket.simulateMessage({
      type: 'group_message',
      payload: {
        id: 'gmsg1',
        groupId: 'group1',
        from: 'user2',
        content: 'Group hello!',
        timestamp: Date.now(),
      },
    });

    expect(onGroupMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'gmsg1',
        groupId: 'group1',
        content: 'Group hello!',
      })
    );
  });
});
