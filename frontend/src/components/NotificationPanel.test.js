import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import NotificationPanel from './NotificationPanel';
import { useNotifications } from '../context/NotificationContext';

jest.mock('../context/NotificationContext');

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('NotificationPanel Component', () => {
  const mockNavigate = jest.fn();
  const mockMarkNotificationRead = jest.fn();
  const mockMarkAllRead = jest.fn();
  const mockClearNotifications = jest.fn();

  const mockNotifications = [
    {
      id: 'notif-1',
      title: 'New Research',
      message: 'Research started',
      type: 'new_research',
      read: false,
      timestamp: Date.now() - 1000,
    },
    {
      id: 'notif-2',
      title: 'Research Complete',
      message: 'Research finished',
      type: 'research_complete',
      read: true,
      timestamp: Date.now() - 2000,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockClear();
    useNotifications.mockReturnValue({
      notifications: mockNotifications,
      getUnreadCount: jest.fn(() => 1),
      markNotificationRead: mockMarkNotificationRead,
      markAllRead: mockMarkAllRead,
      clearNotifications: mockClearNotifications,
      connectionStatus: 'connected',
    });
  });

  test('renders notification trigger button', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    expect(screen.getByTitle(/Notifications/i)).toBeInTheDocument();
  });

  test('displays unread count badge', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  test('displays 99+ when unread count exceeds 99', () => {
    useNotifications.mockReturnValue({
      notifications: mockNotifications,
      getUnreadCount: jest.fn(() => 150),
      markNotificationRead: mockMarkNotificationRead,
      markAllRead: mockMarkAllRead,
      clearNotifications: mockClearNotifications,
      connectionStatus: 'connected',
    });

    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    expect(screen.getByText('99+')).toBeInTheDocument();
  });

  test('opens panel when trigger is clicked', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    expect(screen.getByText(/Notifications/i)).toBeInTheDocument();
  });

  test('displays notifications when panel is open', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    expect(screen.getByText('New Research')).toBeInTheDocument();
    expect(screen.getByText('Research Complete')).toBeInTheDocument();
  });

  test('displays empty state when no notifications', () => {
    useNotifications.mockReturnValue({
      notifications: [],
      getUnreadCount: jest.fn(() => 0),
      markNotificationRead: mockMarkNotificationRead,
      markAllRead: mockMarkAllRead,
      clearNotifications: mockClearNotifications,
      connectionStatus: 'connected',
    });

    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    expect(screen.getByText(/No notifications yet/i)).toBeInTheDocument();
  });

  test('marks notification as read when clicked', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    const notification = screen.getByText('New Research');
    fireEvent.click(notification);

    expect(mockMarkNotificationRead).toHaveBeenCalledWith('notif-1');
  });

  test('marks all as read when button is clicked', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    const markAllButton = screen.getByTitle(/Mark all as read/i);
    fireEvent.click(markAllButton);

    expect(mockMarkAllRead).toHaveBeenCalled();
  });

  test('clears all notifications when button is clicked', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    const clearButton = screen.getByTitle(/Clear all notifications/i);
    fireEvent.click(clearButton);

    expect(mockClearNotifications).toHaveBeenCalled();
  });

  test('closes panel when clicking outside', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    expect(screen.getByText(/Notifications/i)).toBeInTheDocument();

    // Click outside
    fireEvent.mouseDown(document.body);

    expect(screen.queryByText(/Notifications/i)).not.toBeInTheDocument();
  });

  test('formats timestamps correctly', () => {
    const recentNotification = {
      ...mockNotifications[0],
      timestamp: Date.now() - 30000, // 30 seconds ago
    };

    useNotifications.mockReturnValue({
      notifications: [recentNotification],
      getUnreadCount: jest.fn(() => 1),
      markNotificationRead: mockMarkNotificationRead,
      markAllRead: mockMarkAllRead,
      clearNotifications: mockClearNotifications,
      connectionStatus: 'connected',
    });

    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    // Should show "Just now" or "1m ago" for recent notifications
    expect(screen.getByText(/ago|Just now/i)).toBeInTheDocument();
  });

  test('displays correct icons for notification types', () => {
    render(
      <BrowserRouter>
        <NotificationPanel />
      </BrowserRouter>
    );

    const trigger = screen.getByTitle(/Notifications/i);
    fireEvent.click(trigger);

    expect(screen.getByText('🔬')).toBeInTheDocument(); // new_research
    expect(screen.getByText('✅')).toBeInTheDocument(); // research_complete
  });
});
