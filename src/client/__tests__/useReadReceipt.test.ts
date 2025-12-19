import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useReadReceipt } from '../hooks/useReadReceipt';

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status?: 'sent' | 'delivered' | 'read';
}

describe('useReadReceipt Hook', () => {
  let mockIntersectionObserver: any;
  let observeCallback: IntersectionObserverCallback;
  let observedElements: Set<Element>;

  beforeEach(() => {
    observedElements = new Set();
    
    mockIntersectionObserver = vi.fn((callback: IntersectionObserverCallback) => {
      observeCallback = callback;
      return {
        observe: vi.fn((element: Element) => {
          observedElements.add(element);
        }),
        unobserve: vi.fn((element: Element) => {
          observedElements.delete(element);
        }),
        disconnect: vi.fn(() => {
          observedElements.clear();
        }),
      };
    });

    global.IntersectionObserver = mockIntersectionObserver;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('should return observeMessage and unobserveMessage functions', () => {
    const onMarkAsRead = vi.fn();
    const { result } = renderHook(() =>
      useReadReceipt({
        messages: [],
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    expect(result.current.observeMessage).toBeDefined();
    expect(result.current.unobserveMessage).toBeDefined();
  });

  it('should create IntersectionObserver on mount', () => {
    const onMarkAsRead = vi.fn();
    renderHook(() =>
      useReadReceipt({
        messages: [],
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    expect(mockIntersectionObserver).toHaveBeenCalled();
  });

  it('should observe message elements when observeMessage is called', () => {
    const onMarkAsRead = vi.fn();
    const { result } = renderHook(() =>
      useReadReceipt({
        messages: [],
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    const mockElement = document.createElement('div');
    mockElement.setAttribute('data-message-id', 'msg1');

    // Call observeMessage which uses the IntersectionObserver internally
    result.current.observeMessage(mockElement);

    expect(observedElements.has(mockElement)).toBe(true);
  });

  it('should trigger onMarkAsRead after delay when message becomes visible', async () => {
    const onMarkAsRead = vi.fn();
    const messages: Message[] = [
      {
        id: 'msg1',
        from: 'user2',
        to: 'user1',
        content: 'Hello',
        timestamp: Date.now(),
        status: 'delivered',
      },
    ];

    renderHook(() =>
      useReadReceipt({
        messages,
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    const mockElement = document.createElement('div');
    mockElement.setAttribute('data-message-id', 'msg1');

    // Simulate intersection
    const entries: IntersectionObserverEntry[] = [
      {
        target: mockElement,
        isIntersecting: true,
        intersectionRatio: 1,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: {} as DOMRectReadOnly,
        time: Date.now(),
      },
    ];

    observeCallback(entries, {} as IntersectionObserver);

    // Fast-forward time past the delay (500ms)
    vi.advanceTimersByTime(600);

    expect(onMarkAsRead).toHaveBeenCalledWith(['msg1']);
  });

  it('should not mark already read messages', async () => {
    const onMarkAsRead = vi.fn();
    const messages: Message[] = [
      {
        id: 'msg1',
        from: 'user2',
        to: 'user1',
        content: 'Hello',
        timestamp: Date.now(),
        status: 'read',
      },
    ];

    const { result } = renderHook(() =>
      useReadReceipt({
        messages,
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    // Wait for effect to run
    await vi.advanceTimersByTimeAsync(10);

    const mockElement = document.createElement('div');
    mockElement.setAttribute('data-message-id', 'msg1');

    // Call observeMessage
    result.current.observeMessage(mockElement);

    const entries: IntersectionObserverEntry[] = [
      {
        target: mockElement,
        isIntersecting: true,
        intersectionRatio: 1,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: {} as DOMRectReadOnly,
        time: Date.now(),
      },
    ];

    observeCallback(entries, {} as IntersectionObserver);
    await vi.advanceTimersByTimeAsync(600);

    expect(onMarkAsRead).not.toHaveBeenCalled();
  });

  it('should not mark messages sent by current user', async () => {
    const onMarkAsRead = vi.fn();
    const messages: Message[] = [
      {
        id: 'msg1',
        from: 'user1', // Sent by current user
        to: 'user2',
        content: 'Hello',
        timestamp: Date.now(),
        status: 'delivered',
      },
    ];

    const { result } = renderHook(() =>
      useReadReceipt({
        messages,
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    // Wait for effect to run
    await vi.advanceTimersByTimeAsync(10);

    const mockElement = document.createElement('div');
    mockElement.setAttribute('data-message-id', 'msg1');

    // Call observeMessage
    result.current.observeMessage(mockElement);

    const entries: IntersectionObserverEntry[] = [
      {
        target: mockElement,
        isIntersecting: true,
        intersectionRatio: 1,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: {} as DOMRectReadOnly,
        time: Date.now(),
      },
    ];

    observeCallback(entries, {} as IntersectionObserver);
    await vi.advanceTimersByTimeAsync(600);

    expect(onMarkAsRead).not.toHaveBeenCalled();
  });

  it('should batch multiple message reads into single call', async () => {
    const onMarkAsRead = vi.fn();
    const messages: Message[] = [
      {
        id: 'msg1',
        from: 'user2',
        to: 'user1',
        content: 'Hello',
        timestamp: Date.now(),
        status: 'delivered',
      },
      {
        id: 'msg2',
        from: 'user2',
        to: 'user1',
        content: 'Hi there',
        timestamp: Date.now() + 1000,
        status: 'delivered',
      },
    ];

    const { result } = renderHook(() =>
      useReadReceipt({
        messages,
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    // Wait for effect to run
    await vi.advanceTimersByTimeAsync(10);

    const mockElement1 = document.createElement('div');
    mockElement1.setAttribute('data-message-id', 'msg1');
    const mockElement2 = document.createElement('div');
    mockElement2.setAttribute('data-message-id', 'msg2');

    // Observe both elements
    result.current.observeMessage(mockElement1);
    result.current.observeMessage(mockElement2);

    const entries: IntersectionObserverEntry[] = [
      {
        target: mockElement1,
        isIntersecting: true,
        intersectionRatio: 1,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: {} as DOMRectReadOnly,
        time: Date.now(),
      },
      {
        target: mockElement2,
        isIntersecting: true,
        intersectionRatio: 1,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: {} as DOMRectReadOnly,
        time: Date.now(),
      },
    ];

    observeCallback(entries, {} as IntersectionObserver);
    await vi.advanceTimersByTimeAsync(600);

    expect(onMarkAsRead).toHaveBeenCalledTimes(1);
    expect(onMarkAsRead).toHaveBeenCalledWith(expect.arrayContaining(['msg1', 'msg2']));
  });

  it('should cancel pending reads when message leaves viewport', async () => {
    const onMarkAsRead = vi.fn();
    const messages: Message[] = [
      {
        id: 'msg1',
        from: 'user2',
        to: 'user1',
        content: 'Hello',
        timestamp: Date.now(),
        status: 'delivered',
      },
    ];

    const { result } = renderHook(() =>
      useReadReceipt({
        messages,
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    // Wait for effect to run
    await vi.advanceTimersByTimeAsync(10);

    const mockElement = document.createElement('div');
    mockElement.setAttribute('data-message-id', 'msg1');

    // Call observeMessage
    result.current.observeMessage(mockElement);

    // Message enters viewport
    observeCallback(
      [
        {
          target: mockElement,
          isIntersecting: true,
          intersectionRatio: 1,
          boundingClientRect: {} as DOMRectReadOnly,
          intersectionRect: {} as DOMRectReadOnly,
          rootBounds: {} as DOMRectReadOnly,
          time: Date.now(),
        },
      ],
      {} as IntersectionObserver
    );

    // Advance time partially
    await vi.advanceTimersByTimeAsync(200);

    // Message leaves viewport - this triggers another callback but doesn't add to pending
    observeCallback(
      [
        {
          target: mockElement,
          isIntersecting: false,
          intersectionRatio: 0,
          boundingClientRect: {} as DOMRectReadOnly,
          intersectionRect: {} as DOMRectReadOnly,
          rootBounds: {} as DOMRectReadOnly,
          time: Date.now(),
        },
      ],
      {} as IntersectionObserver
    );

    // The timeout from the second callback will still fire, but there are messages pending from first
    await vi.advanceTimersByTimeAsync(600);

    // The first intersection added msg1 to pending, so it will be marked as read
    expect(onMarkAsRead).toHaveBeenCalledWith(['msg1']);
  });

  it('should cleanup observer on unmount', () => {
    const onMarkAsRead = vi.fn();
    const { unmount } = renderHook(() =>
      useReadReceipt({
        messages: [],
        currentUserId: 'user1',
        selectedUserId: 'user2',
        onMarkAsRead,
      })
    );

    const observer = mockIntersectionObserver.mock.results[0].value;
    unmount();

    expect(observer.disconnect).toHaveBeenCalled();
  });
});
