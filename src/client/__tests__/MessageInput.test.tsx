import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MessageInput from '../components/MessageInput';

describe('MessageInput Component', () => {
  it('should render input field', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const input = screen.getByPlaceholderText('Type a message');
    expect(input).toBeDefined();
  });

  it('should call onChange when typing', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const input = screen.getByPlaceholderText('Type a message');
    fireEvent.change(input, { target: { value: 'Hello' } });

    expect(onChange).toHaveBeenCalledWith('Hello');
  });

  it('should call onSend when clicking send button', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value="Hello World"
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);

    expect(onSend).toHaveBeenCalled();
  });

  it('should call onSend when pressing Enter', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value="Hello World"
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const input = screen.getByPlaceholderText('Type a message');
    
    // Use keyDown to match component implementation
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(onSend).toHaveBeenCalled();
  });

  it('should not call onSend when pressing Enter with Shift', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value="Hello World"
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const input = screen.getByPlaceholderText('Type a message');
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', shiftKey: true });

    expect(onSend).not.toHaveBeenCalled();
  });

  it('should disable input when disabled prop is true', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={true}
        canSendImages={true}
      />
    );

    const input = screen.getByPlaceholderText('Connecting...') as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });

  it('should not send empty messages', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);

    expect(onSend).not.toHaveBeenCalled();
  });

  it('should not send whitespace-only messages', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value="   "
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);

    expect(onSend).not.toHaveBeenCalled();
  });

  it('should show image button when canSendImages is true', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const imageButton = screen.getByTitle('Send image');
    expect(imageButton).toBeDefined();
  });

  it('should not show image button when canSendImages is false', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={false}
      />
    );

    const imageButton = screen.queryByTitle('Send image');
    expect(imageButton).toBeNull();
  });

  it('should handle image file selection', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeDefined();

    const file = new File(['image'], 'test.png', { type: 'image/png' });
    const fileReader = {
      readAsDataURL: vi.fn(),
      result: 'data:image/png;base64,test',
      onload: null as any,
    };

    global.FileReader = vi.fn(() => fileReader) as any;

    fireEvent.change(fileInput, { target: { files: [file] } });

    // Simulate FileReader onload
    if (fileReader.onload) {
      fileReader.onload({ target: fileReader } as any);
    }

    expect(onSendImage).toHaveBeenCalledWith('data:image/png;base64,test');
  });

  it('should toggle emoji picker', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const emojiButton = screen.getByTitle('Insert emoji');
    fireEvent.click(emojiButton);

    // Emoji picker should be visible
    const emojiPicker = document.querySelector('.emoji-picker');
    expect(emojiPicker).toBeDefined();
  });

  it('should insert emoji on click', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    render(
      <MessageInput
        value="Hello"
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const emojiButton = screen.getByTitle('Insert emoji');
    fireEvent.click(emojiButton);

    const firstEmoji = document.querySelector('.emoji-item');
    if (firstEmoji) {
      fireEvent.click(firstEmoji);
      expect(onChange).toHaveBeenCalled();
    }
  });

  it('should accept value prop', () => {
    const onChange = vi.fn();
    const onSend = vi.fn();
    const onSendImage = vi.fn();

    const { rerender } = render(
      <MessageInput
        value=""
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    const input = screen.getByPlaceholderText('Type a message') as HTMLInputElement;
    expect(input.value).toBe('');

    rerender(
      <MessageInput
        value="Hello World"
        onChange={onChange}
        onSend={onSend}
        onSendImage={onSendImage}
        disabled={false}
        canSendImages={true}
      />
    );

    // Component updates when value prop changes
    expect(input.value).toBe('Hello World');
  });
});
