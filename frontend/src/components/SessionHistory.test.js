import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SessionHistory from './SessionHistory';
import { useSession } from '../context/SessionContext';
import * as api from '../services/api';

jest.mock('../context/SessionContext');
jest.mock('../services/api');

describe('SessionHistory Component', () => {
  const mockSessionId = 'session-123';
  const mockSwitchSession = jest.fn();
  const mockStartNewSession = jest.fn();

  const mockSessions = [
    { id: 'session-1', name: 'Session 1' },
    { id: 'session-2', name: 'Session 2' },
    { id: 'session-123', name: 'Current Session' },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    useSession.mockReturnValue({
      sessionId: mockSessionId,
      switchSession: mockSwitchSession,
      startNewSession: mockStartNewSession,
    });
    api.getAllChatSessions.mockResolvedValue(mockSessions);
  });

  test('renders session history', () => {
    render(<SessionHistory />);
    const sessionsHeaders = screen.getAllByText(/Sessions/i);
    expect(sessionsHeaders.length).toBeGreaterThan(0);
  });

  test('displays loading state initially', () => {
    api.getAllChatSessions.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve([]), 100))
    );

    render(<SessionHistory />);
    expect(screen.getByText(/Loading sessions/i)).toBeInTheDocument();
  });

  test('displays sessions when loaded', async () => {
    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText('Session 1')).toBeInTheDocument();
      expect(screen.getByText('Session 2')).toBeInTheDocument();
      expect(screen.getByText('Current Session')).toBeInTheDocument();
    });
  });

  test('displays empty state when no sessions', async () => {
    api.getAllChatSessions.mockResolvedValue([]);

    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText(/No sessions yet/i)).toBeInTheDocument();
    });
  });

  test('highlights active session', async () => {
    render(<SessionHistory />);

    await waitFor(() => {
      const currentSessionButton = screen.getByText('Current Session');
      const parent = currentSessionButton.closest('li');
      expect(parent).toHaveClass('active');
    });
  });

  test('handles session click', async () => {
    const mockHistory = [
      { question: 'Hello', answer: 'Hi there!', created_at: '2024-01-01' },
    ];

    api.getChatHistory = jest.fn().mockResolvedValue(mockHistory);
    api.getAllChatSessions.mockResolvedValue(mockSessions);

    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText('Session 1')).toBeInTheDocument();
    });

    const sessionButton = screen.getByText('Session 1');
    fireEvent.click(sessionButton);

    await waitFor(() => {
      expect(api.getChatHistory).toHaveBeenCalled();
      expect(mockSwitchSession).toHaveBeenCalled();
    });
  });

  test('does not switch when clicking current session', async () => {
    api.getChatHistory = jest.fn();
    
    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText('Current Session')).toBeInTheDocument();
    });

    const currentSessionButton = screen.getByText('Current Session');
    fireEvent.click(currentSessionButton);

    expect(api.getChatHistory).not.toHaveBeenCalled();
  });

  test('handles new session creation', () => {
    render(<SessionHistory />);

    const newSessionButton = screen.getByText(/New Session/i);
    fireEvent.click(newSessionButton);

    expect(mockStartNewSession).toHaveBeenCalled();
  });

  test('displays error message on fetch failure', async () => {
    api.getAllChatSessions.mockRejectedValue(new Error('API Error'));

    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load sessions/i)).toBeInTheDocument();
    });
  });

  test('handles error on switch failure', async () => {
    api.getChatHistory = jest.fn().mockRejectedValue(new Error('Switch failed'));
    api.getAllChatSessions.mockResolvedValue(mockSessions);

    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText('Session 1')).toBeInTheDocument();
    });

    const sessionButton = screen.getByText('Session 1');
    fireEvent.click(sessionButton);

    // Component should handle error without crashing
    await waitFor(() => {
      expect(api.getChatHistory).toHaveBeenCalled();
    });
  });

  test('uses untitled session name when name is missing', async () => {
    const sessionsWithoutName = [
      { id: 'session-1' },
      { id: 'session-2', name: 'Named Session' },
    ];

    api.getAllChatSessions.mockResolvedValue(sessionsWithoutName);

    render(<SessionHistory />);

    await waitFor(() => {
      expect(screen.getByText(/Untitled Session/i)).toBeInTheDocument();
      expect(screen.getByText('Named Session')).toBeInTheDocument();
    });
  });

  test('exposes refresh function on window', async () => {
    render(<SessionHistory />);

    await waitFor(() => {
      expect(window.refreshSessionsList).toBeDefined();
    });

    expect(typeof window.refreshSessionsList).toBe('function');
  });

  test('refreshes sessions when refresh function is called', async () => {
    render(<SessionHistory />);

    await waitFor(() => {
      expect(window.refreshSessionsList).toBeDefined();
    });

    const updatedSessions = [{ id: 'session-new', name: 'New Session' }];
    api.getAllChatSessions.mockResolvedValue(updatedSessions);

    window.refreshSessionsList();

    await waitFor(() => {
      expect(api.getAllChatSessions).toHaveBeenCalledTimes(2);
    });
  });
});
