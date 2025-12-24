import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatInput from './ChatInput';

describe('ChatInput Component', () => {
  const mockOnChange = jest.fn();
  const mockOnSendMessage = jest.fn();

  const defaultProps = {
    value: '',
    onChange: mockOnChange,
    onSendMessage: mockOnSendMessage,
    disabled: false
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders textarea and send button', () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByPlaceholderText(/Type your message here/i)).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  test('displays current value in textarea', () => {
    render(<ChatInput {...defaultProps} value="Test message" />);
    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    expect(textarea).toHaveValue('Test message');
  });

  test('calls onChange when textarea value changes', () => {
    render(<ChatInput {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    expect(mockOnChange).toHaveBeenCalledWith('Hello');
  });

  test('calls onSendMessage when send button is clicked with non-empty value', () => {
    render(<ChatInput {...defaultProps} value="Test message" />);
    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  test('does not call onSendMessage when send button is clicked with empty value', () => {
    render(<ChatInput {...defaultProps} value="" />);
    const sendButton = screen.getByText('Send');
    expect(sendButton).toBeDisabled();
    fireEvent.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  test('does not call onSendMessage when send button is clicked with whitespace-only value', () => {
    render(<ChatInput {...defaultProps} value="   " />);
    const sendButton = screen.getByText('Send');
    expect(sendButton).toBeDisabled();
    fireEvent.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  test('calls onSendMessage when Enter key is pressed', () => {
    render(<ChatInput {...defaultProps} value="Test message" />);
    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  test('does not call onSendMessage when Shift+Enter is pressed', () => {
    render(<ChatInput {...defaultProps} value="Test message" />);
    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  test('disables input when disabled prop is true', () => {
    render(<ChatInput {...defaultProps} disabled={true} />);
    const textarea = screen.getByPlaceholderText(/Processing/i);
    const sendButton = screen.getByText('Wait...');
    
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  test('shows "Wait..." text on button when disabled', () => {
    render(<ChatInput {...defaultProps} disabled={true} />);
    expect(screen.getByText('Wait...')).toBeInTheDocument();
  });

  test('does not call onSendMessage when disabled and button is clicked', () => {
    render(<ChatInput {...defaultProps} value="Test" disabled={true} />);
    const sendButton = screen.getByText('Wait...');
    fireEvent.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  test('does not call onSendMessage when disabled and Enter is pressed', () => {
    render(<ChatInput {...defaultProps} value="Test" disabled={true} />);
    const textarea = screen.getByPlaceholderText(/Processing/i);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });
});



