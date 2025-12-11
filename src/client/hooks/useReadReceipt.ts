import { useEffect, useRef, useCallback } from 'react';

interface Message {
  id: string;
  from: string;
  to: string;
  content: string;
  timestamp: number;
  status: 'sent' | 'delivered' | 'read';
}

interface UseReadReceiptProps {
  messages: Message[];
  currentUserId: string;
  selectedUserId: string;
  onMarkAsRead: (messageIds: string[]) => void;
}

export const useReadReceipt = ({
  messages,
  currentUserId,
  selectedUserId,
  onMarkAsRead,
}: UseReadReceiptProps) => {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const pendingMessagesRef = useRef<Set<string>>(new Set());
  const timeoutRef = useRef<number>();

  const markMessagesAsRead = useCallback(() => {
    if (pendingMessagesRef.current.size > 0) {
      const messageIds = Array.from(pendingMessagesRef.current);
      onMarkAsRead(messageIds);
      pendingMessagesRef.current.clear();
    }
  }, [onMarkAsRead]);

  useEffect(() => {
    // Create intersection observer to detect when messages become visible
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const messageId = entry.target.getAttribute('data-message-id');
            if (messageId) {
              const message = messages.find(
                (m) => m.id === messageId && m.from === selectedUserId && m.to === currentUserId && m.status !== 'read'
              );
              if (message) {
                pendingMessagesRef.current.add(messageId);
              }
            }
          }
        });

        // Debounce the mark as read call
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = window.setTimeout(() => {
          markMessagesAsRead();
        }, 500);
      },
      { threshold: 0.5 }
    );

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [messages, currentUserId, selectedUserId, markMessagesAsRead]);

  const observeMessage = useCallback((element: HTMLElement | null) => {
    if (element && observerRef.current) {
      observerRef.current.observe(element);
    }
  }, []);

  const unobserveMessage = useCallback((element: HTMLElement | null) => {
    if (element && observerRef.current) {
      observerRef.current.unobserve(element);
    }
  }, []);

  return {
    observeMessage,
    unobserveMessage,
  };
};
