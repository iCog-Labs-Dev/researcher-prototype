import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorModal from './ErrorModal';

describe('ErrorModal Component', () => {
  const mockOnClose = jest.fn();
  const defaultProps = {
    isOpen: true,
    message: 'Test error message',
    onClose: mockOnClose
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('does not render when isOpen is false', () => {
    render(<ErrorModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('Unable to Activate Topic')).not.toBeInTheDocument();
  });

  test('does not render when message is empty', () => {
    render(<ErrorModal {...defaultProps} message={null} />);
    expect(screen.queryByText('Unable to Activate Topic')).not.toBeInTheDocument();
  });

  test('renders modal when open with message', () => {
    render(<ErrorModal {...defaultProps} />);
    expect(screen.getByText('Unable to Activate Topic')).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  test('displays error icon', () => {
    render(<ErrorModal {...defaultProps} />);
    expect(screen.getByText('⚠️')).toBeInTheDocument();
  });

  test('calls onClose when close button is clicked', () => {
    render(<ErrorModal {...defaultProps} />);
    const closeButton = screen.getByLabelText('Close');
    fireEvent.click(closeButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('calls onClose when "Got it" button is clicked', () => {
    render(<ErrorModal {...defaultProps} />);
    const dismissButton = screen.getByText('Got it');
    fireEvent.click(dismissButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('calls onClose when overlay is clicked', () => {
    const { container } = render(<ErrorModal {...defaultProps} />);
    const overlay = container.querySelector('.error-modal-overlay');
    fireEvent.click(overlay);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('does not call onClose when modal content is clicked', () => {
    const { container } = render(<ErrorModal {...defaultProps} />);
    const modal = container.querySelector('.error-modal');
    fireEvent.click(modal);
    expect(mockOnClose).not.toHaveBeenCalled();
  });
});



