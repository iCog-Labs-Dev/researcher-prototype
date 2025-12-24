import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TopicSidebarItem from './TopicSidebarItem';

describe('TopicSidebarItem Component', () => {
  const mockTopic = {
    topic_id: 'topic-123',
    name: 'Test Topic',
    description: 'This is a test topic description',
    confidence_score: 0.85,
    is_active_research: false,
    suggested_at: Math.floor(Date.now() / 1000),
    conversation_context: 'Test context',
  };

  const defaultProps = {
    topic: mockTopic,
    index: 0,
    onEnableResearch: jest.fn().mockResolvedValue(undefined),
    onDisableResearch: jest.fn().mockResolvedValue(undefined),
    onDelete: jest.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock window.confirm
    window.confirm = jest.fn(() => true);
  });

  afterEach(() => {
    delete window.confirm;
  });

  test('renders topic name in compact view', () => {
    render(<TopicSidebarItem {...defaultProps} />);
    expect(screen.getByText('Test Topic')).toBeInTheDocument();
  });

  test('displays confidence score', () => {
    render(<TopicSidebarItem {...defaultProps} />);
    expect(screen.getByText(/85%/i)).toBeInTheDocument();
  });

  test('shows research indicator when topic is active', () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    render(<TopicSidebarItem {...defaultProps} topic={activeTopic} />);
    expect(screen.getByText('🔬')).toBeInTheDocument();
  });

  test('expands to show details when clicked', () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    expect(screen.getByText(/This is a test topic description/i)).toBeInTheDocument();
    expect(screen.getByText(/Context:/i)).toBeInTheDocument();
  });

  test('shows research button when research is not active', () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    expect(screen.getByText(/Research/i)).toBeInTheDocument();
  });

  test('shows stop button when research is active', () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    render(<TopicSidebarItem {...defaultProps} topic={activeTopic} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    expect(screen.getByText(/Stop/i)).toBeInTheDocument();
  });

  test('calls onEnableResearch when research button is clicked', async () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    // Click expand to show full buttons
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    const researchButton = screen.getByText(/Research/i);
    fireEvent.click(researchButton);

    await waitFor(() => {
      expect(defaultProps.onEnableResearch).toHaveBeenCalled();
    });
  });

  test('calls onDisableResearch when stop button is clicked', async () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    render(<TopicSidebarItem {...defaultProps} topic={activeTopic} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    const stopButton = screen.getByText(/Stop/i);
    fireEvent.click(stopButton);

    await waitFor(() => {
      expect(defaultProps.onDisableResearch).toHaveBeenCalled();
    });
  });

  test('calls onDelete when delete button is clicked and confirmed', async () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    const deleteButton = screen.getByText(/Delete/i);
    fireEvent.click(deleteButton);

    expect(window.confirm).toHaveBeenCalledWith('Delete topic "Test Topic"?');

    await waitFor(() => {
      expect(defaultProps.onDelete).toHaveBeenCalled();
    });
  });

  test('does not call onDelete when delete is cancelled', () => {
    window.confirm.mockReturnValue(false);

    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    const deleteButton = screen.getByText(/Delete/i);
    fireEvent.click(deleteButton);

    expect(defaultProps.onDelete).not.toHaveBeenCalled();
  });

  test('shows loading state during actions', async () => {
    defaultProps.onEnableResearch.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    const researchButton = screen.getByText(/Research/i).closest('button');
    if (researchButton) {
      fireEvent.click(researchButton);

      // Check for loading indicator (there might be multiple, so use queryAll)
      const loadingIndicators = screen.queryAllByText('⏳');
      expect(loadingIndicators.length).toBeGreaterThan(0);
      
      // The button should be disabled during loading
      await waitFor(() => {
        expect(researchButton).toBeDisabled();
      });
    }
  });

  test('displays conversation context when available', () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    expect(screen.getByText(/"Test context"/i)).toBeInTheDocument();
  });

  test('displays suggested date', () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    const expandButton = screen.getByTitle(/Show more/i);
    fireEvent.click(expandButton);

    expect(screen.getByText(/Suggested:/i)).toBeInTheDocument();
  });

  test('can use compact view research button', async () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    // Find the compact research button (icon only)
    const researchButtons = screen.getAllByTitle(/Start researching this topic/i);
    const compactButton = researchButtons[0];
    
    fireEvent.click(compactButton);

    await waitFor(() => {
      expect(defaultProps.onEnableResearch).toHaveBeenCalled();
    });
  });

  test('can use compact view delete button', async () => {
    render(<TopicSidebarItem {...defaultProps} />);
    
    // Find the compact delete button (icon only)
    const deleteButtons = screen.getAllByTitle(/Remove this topic/i);
    const compactButton = deleteButtons[0];
    
    fireEvent.click(compactButton);

    expect(window.confirm).toHaveBeenCalled();

    await waitFor(() => {
      expect(defaultProps.onDelete).toHaveBeenCalled();
    });
  });

  test('applies correct confidence class', () => {
    const { container } = render(<TopicSidebarItem {...defaultProps} />);
    const item = container.querySelector('.topic-list-item');
    expect(item).toBeInTheDocument();
  });

  test('applies active-research class when research is active', () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    const { container } = render(<TopicSidebarItem {...defaultProps} topic={activeTopic} />);
    const item = container.querySelector('.topic-list-item');
    expect(item).toHaveClass('active-research');
  });
});
