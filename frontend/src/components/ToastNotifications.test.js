import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ToastNotifications from './ToastNotifications';

describe('ToastNotifications Component', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  test('renders nothing when no toasts', () => {
    const { container } = render(<ToastNotifications />);
    expect(container.firstChild).toBeNull();
  });

  test('displays toast when showToast event is fired', async () => {
    render(<ToastNotifications />);

    const event = new CustomEvent('showToast', {
      detail: {
        title: 'Test Title',
        message: 'Test Message',
        type: 'new_research',
      },
    });

    window.dispatchEvent(event);

    await waitFor(() => {
      expect(screen.getByText('Test Title')).toBeInTheDocument();
      expect(screen.getByText('Test Message')).toBeInTheDocument();
    });
  });

  test('displays correct icon for different notification types', async () => {
    render(<ToastNotifications />);

    const types = [
      { type: 'new_research', icon: '🔬' },
      { type: 'research_complete', icon: '✅' },
      { type: 'system_status', icon: '⚙️' },
      { type: 'access_denied', icon: '🚫' },
      { type: 'unknown', icon: '📢' },
    ];

    types.forEach(({ type, icon }) => {
      const event = new CustomEvent('showToast', {
        detail: {
          title: 'Test',
          message: 'Test',
          type,
        },
      });
      window.dispatchEvent(event);
    });

    await waitFor(() => {
      expect(screen.getByText('🔬')).toBeInTheDocument();
      expect(screen.getByText('✅')).toBeInTheDocument();
      expect(screen.getByText('⚙️')).toBeInTheDocument();
      expect(screen.getByText('🚫')).toBeInTheDocument();
      expect(screen.getByText('📢')).toBeInTheDocument();
    });
  });

  test('auto-removes toast after 5 seconds', async () => {
    render(<ToastNotifications />);

    const event = new CustomEvent('showToast', {
      detail: {
        title: 'Test Title',
        message: 'Test Message',
        type: 'new_research',
      },
    });

    window.dispatchEvent(event);

    await waitFor(() => {
      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });

    // Fast-forward time
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
    });
  });

  test('removes toast when clicked', async () => {
    render(<ToastNotifications />);

    const event = new CustomEvent('showToast', {
      detail: {
        title: 'Test Title',
        message: 'Test Message',
        type: 'new_research',
      },
    });

    window.dispatchEvent(event);

    await waitFor(() => {
      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });

    const toast = screen.getByText('Test Title');
    fireEvent.click(toast);

    await waitFor(() => {
      expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
    });
  });

  test('removes toast when close button is clicked', async () => {
    render(<ToastNotifications />);

    const event = new CustomEvent('showToast', {
      detail: {
        title: 'Test Title',
        message: 'Test Message',
        type: 'new_research',
      },
    });

    window.dispatchEvent(event);

    await waitFor(() => {
      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });

    const closeButton = screen.getByText('×');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
    });
  });

  test('handles multiple toasts', async () => {
    render(<ToastNotifications />);

    // Fire multiple toast events
    for (let i = 0; i < 3; i++) {
      const event = new CustomEvent('showToast', {
        detail: {
          title: `Toast ${i}`,
          message: `Message ${i}`,
          type: 'new_research',
        },
      });
      window.dispatchEvent(event);
    }

    await waitFor(() => {
      expect(screen.getByText('Toast 0')).toBeInTheDocument();
      expect(screen.getByText('Toast 1')).toBeInTheDocument();
      expect(screen.getByText('Toast 2')).toBeInTheDocument();
    });
  });

  test('cleans up event listener on unmount', () => {
    const { unmount } = render(<ToastNotifications />);

    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith('showToast', expect.any(Function));
  });
});
