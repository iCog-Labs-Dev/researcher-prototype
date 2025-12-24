import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AuthModal from './AuthModal';
import { useAuth } from '../context/AuthContext';
import * as api from '../services/api';

// Mock dependencies
jest.mock('../context/AuthContext');
jest.mock('../services/api');

describe('AuthModal Component', () => {
  const mockLogin = jest.fn();
  const mockSetError = jest.fn();
  const mockOnRequestClose = jest.fn();
  const mockOnAuthenticated = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      login: mockLogin,
      setError: mockSetError,
    });
    
    // Mock window.google for Google Sign-In
    global.window.google = {
      accounts: {
        id: {
          initialize: jest.fn(),
          renderButton: jest.fn(),
        },
      },
    };
  });

  afterEach(() => {
    delete global.window.google;
  });

  describe('Login Mode', () => {
    test('renders login form when isLoginMode is true', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
          onAuthenticated={mockOnAuthenticated}
        />
      );

      expect(screen.getByText(/🔐 Login/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Login/i })).toBeInTheDocument();
    });

    test('disables submit button when email or password is empty', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const submitButton = screen.getByRole('button', { name: /Login/i });
      expect(submitButton).toBeDisabled();
    });

    test('enables submit button when email and password are filled', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByLabelText(/Password/i);
      const submitButton = screen.getByRole('button', { name: /Login/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });

      expect(submitButton).not.toBeDisabled();
    });

    test('handles successful login', async () => {
      const mockUserData = {
        id: 'user-123',
        email: 'test@example.com',
        display_name: 'Test User',
      };

      api.loginUser.mockResolvedValue({ access_token: 'token-123' });
      api.getCurrentUser.mockResolvedValue(mockUserData);

      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
          onAuthenticated={mockOnAuthenticated}
        />
      );

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByLabelText(/Password/i);
      const submitButton = screen.getByRole('button', { name: /Login/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(api.loginUser).toHaveBeenCalledWith('test@example.com', 'password123');
      });

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('token-123', mockUserData);
        expect(mockOnAuthenticated).toHaveBeenCalledWith('user-123', 'Test User');
        expect(mockOnRequestClose).toHaveBeenCalled();
      });
    });

    test('displays error message on login failure', async () => {
      api.loginUser.mockRejectedValue({
        response: { data: { detail: 'Invalid credentials' } },
      });

      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByLabelText(/Password/i);
      const submitButton = screen.getByRole('button', { name: /Login/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
      });
    });

    test('shows loading state during login', async () => {
      api.loginUser.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ access_token: 'token' }), 100))
      );

      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByLabelText(/Password/i);
      const submitButton = screen.getByRole('button', { name: /Login/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);

      expect(screen.getByText(/Logging in/i)).toBeInTheDocument();
    });
  });

  describe('Register Mode', () => {
    test('switches to register mode when toggle button is clicked', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const toggleButton = screen.getByRole('button', { name: /Register/i });
      fireEvent.click(toggleButton);

      expect(screen.getByText(/✏️ Register/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Confirm Password/i)).toBeInTheDocument();
    });

    test('validates password match on registration', async () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      // Switch to register mode
      const toggleButton = screen.getByRole('button', { name: /Register/i });
      fireEvent.click(toggleButton);

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByPlaceholderText(/Enter your password \(min 6 characters\)/i);
      const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
      const submitButton = screen.getByRole('button', { name: /Register/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(confirmPasswordInput, { target: { value: 'different' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
      });

      expect(api.registerUser).not.toHaveBeenCalled();
    });

    test('validates password length on registration', async () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      // Switch to register mode
      const toggleButton = screen.getByRole('button', { name: /Register/i });
      fireEvent.click(toggleButton);

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByPlaceholderText(/Enter your password \(min 6 characters\)/i);
      const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
      const submitButton = screen.getByRole('button', { name: /Register/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: '12345' } });
      fireEvent.change(confirmPasswordInput, { target: { value: '12345' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Password must be at least 6 characters/i)).toBeInTheDocument();
      });
    });

    test('handles successful registration', async () => {
      const mockUserData = {
        id: 'user-123',
        email: 'newuser@example.com',
        display_name: 'New User',
      };

      api.registerUser.mockResolvedValue({ access_token: 'token-123' });
      api.getCurrentUser.mockResolvedValue(mockUserData);

      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
          onAuthenticated={mockOnAuthenticated}
        />
      );

      // Switch to register mode
      const toggleButton = screen.getByRole('button', { name: /Register/i });
      fireEvent.click(toggleButton);

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByPlaceholderText(/Enter your password \(min 6 characters\)/i);
      const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
      const submitButton = screen.getByRole('button', { name: /Register/i });

      fireEvent.change(emailInput, { target: { value: 'newuser@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(api.registerUser).toHaveBeenCalledWith('newuser@example.com', 'password123', null);
      });

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('token-123', mockUserData);
        expect(mockOnAuthenticated).toHaveBeenCalled();
        expect(mockOnRequestClose).toHaveBeenCalled();
      });
    });
  });

  describe('Modal Behavior', () => {
    test('does not render when isOpen is false', () => {
      const { container } = render(
        <AuthModal
          isOpen={false}
          onRequestClose={mockOnRequestClose}
        />
      );

      expect(container.querySelector('.auth-modal')).not.toBeInTheDocument();
    });

    test('calls onRequestClose when close button is clicked', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const closeButton = screen.getByLabelText(/Close/i);
      fireEvent.click(closeButton);

      expect(mockOnRequestClose).toHaveBeenCalled();
    });

    test('does not close when preventClose is true', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
          preventClose={true}
        />
      );

      const closeButton = screen.queryByLabelText(/Close/i);
      expect(closeButton).not.toBeInTheDocument();
    });

    test('clears form when switching modes', () => {
      render(
        <AuthModal
          isOpen={true}
          onRequestClose={mockOnRequestClose}
        />
      );

      const emailInput = screen.getByLabelText(/Email/i);
      const passwordInput = screen.getByLabelText(/Password/i);

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });

      const toggleButton = screen.getByRole('button', { name: /Register/i });
      fireEvent.click(toggleButton);

      // Switch back to login
      const loginToggle = screen.getByRole('button', { name: /Login/i });
      fireEvent.click(loginToggle);

      expect(emailInput.value).toBe('');
      expect(passwordInput.value).toBe('');
    });
  });
});
