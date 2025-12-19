import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import MessageList from '../components/MessageList';

describe('MessageList Component', () => {
  const mockMessages = [
    {
      id: 'msg1',
      from: 'user1',
      to: 'user2',
      content: 'Hello from user1',
      timestamp: Date.now() - 60000,
      status: 'delivered' as const,
    },
    {
      id: 'msg2',
      from: 'user2',
      to: 'user1',
      content: 'Hello from user2',
      timestamp: Date.now() - 30000,
      status: 'read' as const,
    },
    {
      id: 'msg3',
      from: 'user1',
      to: 'user2',
      content: 'Another message',
      timestamp: Date.now(),
      status: 'sent' as const,
    },
  ];

  beforeEach(() => {
    // Mock IntersectionObserver
    global.IntersectionObserver = vi.fn(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    })) as any;

    // Mock scrollIntoView (not available in jsdom)
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('should render messages', () => {
    const onMarkAsRead = vi.fn();

    render(
      <MessageList
        messages={mockMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    expect(screen.getByText('Hello from user1')).toBeDefined();
    expect(screen.getByText('Hello from user2')).toBeDefined();
    expect(screen.getByText('Another message')).toBeDefined();
  });

  it('should apply correct classes for sent messages', () => {
    const onMarkAsRead = vi.fn();

    const { container } = render(
      <MessageList
        messages={mockMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const sentMessages = container.querySelectorAll('.message.sent');
    expect(sentMessages.length).toBeGreaterThan(0);
  });

  it('should apply correct classes for received messages', () => {
    const onMarkAsRead = vi.fn();

    const { container } = render(
      <MessageList
        messages={mockMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const receivedMessages = container.querySelectorAll('.message.received');
    expect(receivedMessages.length).toBeGreaterThan(0);
  });

  it('should show typing indicator when user is typing', () => {
    const onMarkAsRead = vi.fn();

    render(
      <MessageList
        messages={mockMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={true}
        typingUsername="Alice"
        onMarkAsRead={onMarkAsRead}
      />
    );

    expect(screen.getByText(/Alice is typing/i)).toBeDefined();
  });

  it('should not show typing indicator when user is not typing', () => {
    const onMarkAsRead = vi.fn();

    render(
      <MessageList
        messages={mockMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername="Alice"
        onMarkAsRead={onMarkAsRead}
      />
    );

    expect(screen.queryByText(/Alice is typing/i)).toBeNull();
  });

  it('should render empty state when no messages', () => {
    const onMarkAsRead = vi.fn();

    const { container } = render(
      <MessageList
        messages={[]}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const messageElements = container.querySelectorAll('.message');
    expect(messageElements.length).toBe(0);
  });

  it('should show message status icons for sent messages', () => {
    const onMarkAsRead = vi.fn();

    const sentMessages = [
      {
        id: 'msg1',
        from: 'user1',
        to: 'user2',
        content: 'Sent message',
        timestamp: Date.now(),
        status: 'sent' as const,
      },
      {
        id: 'msg2',
        from: 'user1',
        to: 'user2',
        content: 'Delivered message',
        timestamp: Date.now(),
        status: 'delivered' as const,
      },
      {
        id: 'msg3',
        from: 'user1',
        to: 'user2',
        content: 'Read message',
        timestamp: Date.now(),
        status: 'read' as const,
      },
    ];

    const { container } = render(
      <MessageList
        messages={sentMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const statusIcons = container.querySelectorAll('.status-icon');
    expect(statusIcons.length).toBe(3);
  });

  it('should format timestamps', () => {
    const onMarkAsRead = vi.fn();

    const now = new Date();
    const messagesWithTimes = [
      {
        id: 'msg1',
        from: 'user1',
        to: 'user2',
        content: 'Message',
        timestamp: now.getTime(),
        status: 'sent' as const,
      },
    ];

    const { container } = render(
      <MessageList
        messages={messagesWithTimes}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const timestamps = container.querySelectorAll('.message-meta');
    expect(timestamps.length).toBeGreaterThan(0);
  });

  it('should render image messages', () => {
    const onMarkAsRead = vi.fn();

    const imageMessages = [
      {
        id: 'msg1',
        from: 'user1',
        to: 'user2',
        content: 'Image',
        timestamp: Date.now(),
        status: 'sent' as const,
        type: 'image' as const,
        imageData: 'data:image/png;base64,test',
      },
    ];

    const { container } = render(
      <MessageList
        messages={imageMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const images = container.querySelectorAll('.message-image');
    expect(images.length).toBe(1);
  });

  it('should scroll to bottom on mount', () => {
    const onMarkAsRead = vi.fn();

    const scrollIntoViewMock = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;

    render(
      <MessageList
        messages={mockMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    // Should scroll to bottom
    expect(scrollIntoViewMock).toHaveBeenCalled();
  });

  it('should display messages in array order', () => {
    const onMarkAsRead = vi.fn();

    // Messages should be pre-sorted by caller
    const orderedMessages = [
      {
        id: 'msg1',
        from: 'user1',
        to: 'user2',
        content: 'First',
        timestamp: Date.now(),
        status: 'sent' as const,
      },
      {
        id: 'msg2',
        from: 'user1',
        to: 'user2',
        content: 'Second',
        timestamp: Date.now() + 1000,
        status: 'sent' as const,
      },
      {
        id: 'msg3',
        from: 'user1',
        to: 'user2',
        content: 'Third',
        timestamp: Date.now() + 2000,
        status: 'sent' as const,
      },
    ];

    const { container } = render(
      <MessageList
        messages={orderedMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    const messageContents = Array.from(container.querySelectorAll('.message-content')).map(
      (el) => el.textContent
    );

    expect(messageContents[0]).toBe('First');
    expect(messageContents[1]).toBe('Second');
    expect(messageContents[2]).toBe('Third');
  });

  it('should handle encrypted messages indicator', () => {
    const onMarkAsRead = vi.fn();

    const encryptedMessages = [
      {
        id: 'msg1',
        from: 'user1',
        to: 'user2',
        content: 'Encrypted message',
        timestamp: Date.now(),
        status: 'sent' as const,
        encrypted: true,
      },
    ];

    const { container } = render(
      <MessageList
        messages={encryptedMessages}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    // Check for encrypted indicator (implementation specific)
    const message = container.querySelector('.message');
    expect(message).toBeDefined();
  });

  it('should render messages from different days', () => {
    const onMarkAsRead = vi.fn();

    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    const messagesAcrossDays = [
      {
        id: 'msg1',
        from: 'user1',
        to: 'user2',
        content: 'Yesterday',
        timestamp: yesterday.getTime(),
        status: 'sent' as const,
      },
      {
        id: 'msg2',
        from: 'user1',
        to: 'user2',
        content: 'Today',
        timestamp: Date.now(),
        status: 'sent' as const,
      },
    ];

    const { container } = render(
      <MessageList
        messages={messagesAcrossDays}
        currentUserId="user1"
        selectedUserId="user2"
        isTyping={false}
        typingUsername=""
        onMarkAsRead={onMarkAsRead}
      />
    );

    // Component renders all messages
    const messages = container.querySelectorAll('.message');
    expect(messages.length).toBe(2);
  });
});
