import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Navigation from './Navigation';
import { useSession } from '../context/SessionContext';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import * as api from '../services/api';

jest.mock('../context/SessionContext');
jest.mock('../context/AuthContext');
jest.mock('../context/NotificationContext');
jest.mock('../services/api');

describe('Navigation Component', () => {
  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    display_name: 'Test User',
    role: 'user',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    useSession.mockReturnValue({
      userDisplayName: 'Test User',
      userId: 'user-123',
      updateUserDisplayName: jest.fn(),
      updatePersonality: jest.fn(),
      updateMessages: jest.fn(),
      resetSession: jest.fn(),
    });
    useAuth.mockReturnValue({
      isAuthenticated: true,
      user: mockUser,
      logout: jest.fn(),
    });
    useNotifications.mockReturnValue({
      notifications: [],
      getUnreadCount: jest.fn(() => 0),
      markNotificationRead: jest.fn(),
      markAllRead: jest.fn(),
      clearNotifications: jest.fn(),
      connectionStatus: 'connected',
    });
    api.getCurrentUser.mockResolvedValue(mockUser);
  });

  test('renders navigation with brand', () => {
    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    expect(screen.getByText(/AI Research Assistant/i)).toBeInTheDocument();
  });

  test('renders chat link', () => {
    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    expect(screen.getByText(/💬 Chat/i)).toBeInTheDocument();
  });

  test('opens dashboards dropdown when clicked', () => {
    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    const dashboardsButton = screen.getByText(/📊 Dashboards/i);
    fireEvent.click(dashboardsButton);

    expect(screen.getByText(/🔍 Research Topics/i)).toBeInTheDocument();
    expect(screen.getByText(/📊 Research Results/i)).toBeInTheDocument();
  });

  test('displays user info when authenticated', () => {
    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  test('calls logout when logout button is clicked', () => {
    const mockLogout = jest.fn();
    useAuth.mockReturnValue({
      isAuthenticated: true,
      user: mockUser,
      logout: mockLogout,
    });

    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    const logoutButton = screen.getByText(/Logout/i);
    fireEvent.click(logoutButton);

    expect(mockLogout).toHaveBeenCalled();
  });

  test('shows admin link for admin users', () => {
    const adminUser = { ...mockUser, role: 'admin' };
    useAuth.mockReturnValue({
      isAuthenticated: true,
      user: adminUser,
      logout: jest.fn(),
    });

    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    expect(screen.getByText(/🛠️ Admin/i)).toBeInTheDocument();
  });

  test('prevents admin access for non-admin users', () => {
    const dispatchEventSpy = jest.spyOn(window, 'dispatchEvent');

    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    const adminLink = screen.getByText(/🛠️ Admin/i);
    fireEvent.click(adminLink);

    expect(dispatchEventSpy).toHaveBeenCalled();
  });
});
