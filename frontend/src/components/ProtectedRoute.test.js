import React from 'react';
import { render, screen } from '@testing-library/react';
import ProtectedRoute from './ProtectedRoute';
import { useAuth } from '../context/AuthContext';

jest.mock('../context/AuthContext');

describe('ProtectedRoute Component', () => {
  const mockChildren = <div>Protected Content</div>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders children when authenticated', () => {
    useAuth.mockReturnValue({
      isAuthenticated: true,
      loading: false,
    });

    render(<ProtectedRoute>{mockChildren}</ProtectedRoute>);

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  test('shows loading state when checking authentication', () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      loading: true,
    });

    render(<ProtectedRoute>{mockChildren}</ProtectedRoute>);

    expect(screen.getByText(/Checking authentication/i)).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  test('shows auth modal when not authenticated', () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      loading: false,
    });

    render(<ProtectedRoute>{mockChildren}</ProtectedRoute>);

    expect(screen.getByText(/🔐 Login/i)).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });
});
