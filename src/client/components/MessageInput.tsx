interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
}

function MessageInput({ value, onChange, onSend, disabled }: MessageInputProps) {
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="message-input-container">
      <input
        type="text"
        className="message-input"
        placeholder={disabled ? 'Connecting...' : 'Type a message'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
      />
      <button
        className="send-button"
        onClick={onSend}
        disabled={!value.trim() || disabled}
      >
        Send
      </button>
    </div>
  );
}

export default MessageInput;
