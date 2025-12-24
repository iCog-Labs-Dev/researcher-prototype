import React from 'react';
import { render, screen } from '@testing-library/react';
import NotificationBadge from './NotificationBadge';
import { NotificationProvider, useNotifications } from '../context/NotificationContext';

// Mock the NotificationContext
jest.mock('../context/NotificationContext', () => ({
  useNotifications: jest.fn(),
  NotificationProvider: ({ children }) => children
}));

describe('NotificationBadge Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('does not render when unread count is 0', () => {
    useNotifications.mockReturnValue({
      getUnreadCount: () => 0
    });

    const { container } = render(<NotificationBadge />);
    expect(container.firstChild).toBeNull();
  });

  test('renders badge with unread count', () => {
    useNotifications.mockReturnValue({
      getUnreadCount: () => 5
    });

    render(<NotificationBadge />);
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  test('displays 99+ for counts over 99', () => {
    useNotifications.mockReturnValue({
      getUnreadCount: () => 100
    });

    render(<NotificationBadge />);
    expect(screen.getByText('99+')).toBeInTheDocument();
  });

  test('displays correct title for single notification', () => {
    useNotifications.mockReturnValue({
      getUnreadCount: () => 1
    });

    render(<NotificationBadge />);
    const badge = screen.getByTitle('1 unread notification');
    expect(badge).toBeInTheDocument();
  });

  test('displays correct title for multiple notifications', () => {
    useNotifications.mockReturnValue({
      getUnreadCount: () => 5
    });

    render(<NotificationBadge />);
    const badge = screen.getByTitle('5 unread notifications');
    expect(badge).toBeInTheDocument();
  });

  test('applies custom className', () => {
    useNotifications.mockReturnValue({
      getUnreadCount: () => 3
    });

    const { container } = render(<NotificationBadge className="custom-class" />);
    const badge = container.querySelector('.notification-badge');
    expect(badge).toHaveClass('custom-class');
  });

  test('calls onClick when provided and badge is clicked', () => {
    const mockOnClick = jest.fn();
    useNotifications.mockReturnValue({
      getUnreadCount: () => 2
    });

    render(<NotificationBadge onClick={mockOnClick} />);
    const badge = screen.getByText('2');
    badge.click();
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });
});



