import { render, screen, waitFor } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';
import App from './App';

// Mock the api module
jest.mock('./services/api', () => ({
  setAuthTokenHeader: jest.fn(),
  getModels: jest.fn().mockResolvedValue({ 
    models: { 'gpt-4o-mini': { name: 'GPT-4o Mini', provider: 'OpenAI' } },
    default_model: 'gpt-4o-mini'
  }),
  getUsers: jest.fn().mockResolvedValue([]),
  getUserProfile: jest.fn().mockResolvedValue(null),
}));

describe('App Component (Unit Tests)', () => {
  beforeEach(() => {
    // Set up authenticated user in localStorage
    localStorage.setItem('auth_token', 'test-token');
    localStorage.setItem('auth_user', JSON.stringify({
      id: 'test-user-id',
      email: 'test@example.com',
      display_name: 'Test User'
    }));
  });

  afterEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  test('renders AI Research Assistant heading', async () => {
    render(<App />);
    // Wait for auth to initialize
    await waitFor(() => {
      expect(screen.queryByText(/Checking authentication/i)).not.toBeInTheDocument();
    });
    const heading = screen.getByText(/AI Research Assistant/i);
    expect(heading).toBeInTheDocument();
  });

  test('renders navigation with correct links', async () => {
    render(<App />);
    // Wait for auth to initialize
    await waitFor(() => {
      expect(screen.queryByText(/Checking authentication/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText(/💬 Chat/i)).toBeInTheDocument();
    
    // Open the dashboards dropdown to see the links
    const dashboardsButton = screen.getByText(/📊 Dashboards/i);
    fireEvent.click(dashboardsButton);
    
    // Now the dropdown links should be visible
    await waitFor(() => {
      expect(screen.getByText(/🔍 Research Topics/i)).toBeInTheDocument();
      expect(screen.getByText(/📊 Research Results/i)).toBeInTheDocument();
    });
  });

  test('renders chat interface by default', async () => {
    render(<App />);
    // Wait for auth to initialize
    await waitFor(() => {
      expect(screen.queryByText(/Checking authentication/i)).not.toBeInTheDocument();
    });
    // Check for chat input which indicates chat interface is rendered
    expect(screen.getByPlaceholderText(/Type your message here/i)).toBeInTheDocument();
  });
});
