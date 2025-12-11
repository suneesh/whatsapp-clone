import { useState, useRef } from 'react';

interface GroupMessageInputProps {
  onSendMessage: (content: string) => void;
  onSendImage: (imageData: string) => void;
  onTyping: (typing: boolean) => void;
  disabled?: boolean;
  disabledMessage?: string;
}

export default function GroupMessageInput({
  onSendMessage,
  onSendImage,
  onTyping,
  disabled,
  disabledMessage,
}: GroupMessageInputProps) {
  const [message, setMessage] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<number | null>(null);

  const emojis = [
    '😀', '😃', '😄', '😁', '😅', '😂', '🤣', '😊', '😇', '🙂',
    '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋',
    '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳',
    '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖',
    '😫', '😩', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬', '🤯',
    '😳', '🥵', '🥶', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔',
    '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦',
    '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴',
    '🤢', '🤮', '🤧', '😷', '🤒', '🤕', '🤑', '🤠', '👍', '👎',
    '👏', '🙌', '👋', '🤝', '🙏', '💪', '🎉', '🎊', '🎈', '🎁',
    '🏆', '🥇', '🥈', '🥉', '⭐', '🌟', '✨', '💫', '🔥', '💥',
    '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔',
    '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️',
    '✝️', '☪️', '🕉️', '☸️', '✡️', '🔯', '🕎', '☯️', '☦️', '🛐',
    '⛎', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐',
    '♑', '♒', '♓', '🆔', '⚛️', '🉑', '☢️', '☣️', '📴', '📳',
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      onTyping(false);
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setMessage(value);

    if (!disabled) {
      // Send typing indicator
      onTyping(true);

      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      // Stop typing after 2 seconds of no input
      typingTimeoutRef.current = setTimeout(() => {
        onTyping(false);
      }, 2000);
    }
  };

  const handleEmojiSelect = (emoji: string) => {
    setMessage(prev => prev + emoji);
    setShowEmojiPicker(false);
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be less than 5MB');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result as string;
      onSendImage(result);
    };
    reader.readAsDataURL(file);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="group-message-input-container">
      {disabled && disabledMessage && (
        <div className="input-disabled-message">{disabledMessage}</div>
      )}
      <form onSubmit={handleSubmit} className="group-message-input-form">
        <button
          type="button"
          onClick={() => setShowEmojiPicker(!showEmojiPicker)}
          className="emoji-btn"
          disabled={disabled}
          title="Add emoji"
        >
          😊
        </button>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="image-btn"
          disabled={disabled}
          title="Send image"
        >
          📷
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageSelect}
          style={{ display: 'none' }}
        />

        <input
          type="text"
          value={message}
          onChange={handleInputChange}
          placeholder={disabled ? disabledMessage || 'Messaging disabled' : 'Type a message...'}
          disabled={disabled}
          className="message-input"
        />

        <button type="submit" disabled={!message.trim() || disabled} className="send-btn">
          Send
        </button>
      </form>

      {showEmojiPicker && !disabled && (
        <div className="emoji-picker">
          {emojis.map((emoji, index) => (
            <span
              key={index}
              onClick={() => handleEmojiSelect(emoji)}
              className="emoji-option"
            >
              {emoji}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
