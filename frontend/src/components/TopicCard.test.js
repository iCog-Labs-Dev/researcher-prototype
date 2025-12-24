import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TopicCard from './TopicCard';

describe('TopicCard Component', () => {
  const mockTopic = {
    name: 'Test Topic',
    description: 'This is a test topic description that might be long enough to truncate',
    confidence_score: 0.85,
    suggested_at: Math.floor(Date.now() / 1000) - 86400, // 1 day ago
    is_active_research: false,
    session_id: 'session-12345678'
  };

  const defaultProps = {
    topic: mockTopic,
    index: 0,
    isSelected: false,
    onSelect: jest.fn(),
    onDelete: jest.fn(),
    onEnableResearch: jest.fn().mockResolvedValue(undefined),
    onDisableResearch: jest.fn().mockResolvedValue(undefined)
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders topic name', () => {
    render(<TopicCard {...defaultProps} />);
    expect(screen.getByText('Test Topic')).toBeInTheDocument();
  });

  test('renders topic description', () => {
    render(<TopicCard {...defaultProps} />);
    expect(screen.getByText(/This is a test topic description/i)).toBeInTheDocument();
  });

  test('displays confidence score', () => {
    render(<TopicCard {...defaultProps} />);
    expect(screen.getByText(/85%/i)).toBeInTheDocument();
  });

  test('shows formatted date', () => {
    render(<TopicCard {...defaultProps} />);
    expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
  });

  test('renders checkbox for selection', () => {
    render(<TopicCard {...defaultProps} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  test('checkbox is checked when isSelected is true', () => {
    render(<TopicCard {...defaultProps} isSelected={true} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeChecked();
  });

  test('calls onSelect when checkbox is clicked', () => {
    render(<TopicCard {...defaultProps} />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(defaultProps.onSelect).toHaveBeenCalledWith(true);
  });

  test('shows research button when research is not active', () => {
    render(<TopicCard {...defaultProps} />);
    expect(screen.getByText(/Research/i)).toBeInTheDocument();
  });

  test('shows stop button when research is active', () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    render(<TopicCard {...defaultProps} topic={activeTopic} />);
    expect(screen.getByText(/Stop/i)).toBeInTheDocument();
    // Research button should not be visible, but RESEARCHING badge contains "Research" text
    const researchButton = screen.queryByText(/^Research$/i);
    expect(researchButton).not.toBeInTheDocument();
  });

  test('shows research status badge when research is active', () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    render(<TopicCard {...defaultProps} topic={activeTopic} />);
    expect(screen.getByText(/RESEARCHING/i)).toBeInTheDocument();
  });

  test('calls onEnableResearch when research button is clicked', async () => {
    render(<TopicCard {...defaultProps} />);
    const researchButton = screen.getByText(/Research/i);
    fireEvent.click(researchButton);
    
    await waitFor(() => {
      expect(defaultProps.onEnableResearch).toHaveBeenCalled();
    });
  });

  test('calls onDisableResearch when stop button is clicked', async () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    render(<TopicCard {...defaultProps} topic={activeTopic} />);
    const stopButton = screen.getByText(/Stop/i);
    fireEvent.click(stopButton);
    
    await waitFor(() => {
      expect(defaultProps.onDisableResearch).toHaveBeenCalled();
    });
  });

  test('calls onDelete when delete button is clicked', () => {
    render(<TopicCard {...defaultProps} />);
    const deleteButton = screen.getByTitle(/Delete this topic/i);
    fireEvent.click(deleteButton);
    expect(defaultProps.onDelete).toHaveBeenCalled();
  });

  test('truncates long descriptions', () => {
    const longDescription = 'A'.repeat(150);
    const topicWithLongDesc = { ...mockTopic, description: longDescription };
    render(<TopicCard {...defaultProps} topic={topicWithLongDesc} />);
    
    const description = screen.getByText(/^A{120}\.\.\.$/);
    expect(description).toBeInTheDocument();
  });

  test('shows expand/collapse button for long descriptions', () => {
    const longDescription = 'A'.repeat(150);
    const topicWithLongDesc = { ...mockTopic, description: longDescription };
    render(<TopicCard {...defaultProps} topic={topicWithLongDesc} />);
    
    expect(screen.getByText(/Show more/i)).toBeInTheDocument();
  });

  test('expands description when show more is clicked', () => {
    const longDescription = 'A'.repeat(150);
    const topicWithLongDesc = { ...mockTopic, description: longDescription };
    render(<TopicCard {...defaultProps} topic={topicWithLongDesc} />);
    
    const expandButton = screen.getByText(/Show more/i);
    fireEvent.click(expandButton);
    
    expect(screen.getByText(/Show less/i)).toBeInTheDocument();
    expect(screen.getByText(longDescription)).toBeInTheDocument();
  });

  test('expands description when card is clicked', () => {
    const longDescription = 'A'.repeat(150);
    const topicWithLongDesc = { ...mockTopic, description: longDescription };
    const { container } = render(<TopicCard {...defaultProps} topic={topicWithLongDesc} />);
    
    const card = container.querySelector('.topic-card');
    fireEvent.click(card);
    
    expect(screen.getByText(/Show less/i)).toBeInTheDocument();
  });

  test('does not expand when clicking on interactive elements', () => {
    const longDescription = 'A'.repeat(150);
    const topicWithLongDesc = { ...mockTopic, description: longDescription };
    render(<TopicCard {...defaultProps} topic={topicWithLongDesc} />);
    
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    
    // Description should still be truncated
    expect(screen.queryByText(/Show less/i)).not.toBeInTheDocument();
  });

  test('shows session ID when available', () => {
    render(<TopicCard {...defaultProps} />);
    // Session ID is truncated to first 8 characters: "session-12345678" -> "session-1..."
    // The text is split across multiple nodes, so we check for the element by title and verify it contains the truncated session ID
    const sessionElement = screen.getByTitle(/Session: session-12345678/i);
    expect(sessionElement).toBeInTheDocument();
    expect(sessionElement.textContent).toMatch(/session-.*\.\.\./i);
  });

  test('shows context preview when available', () => {
    const topicWithContext = { 
      ...mockTopic, 
      conversation_context: 'This is the conversation context'
    };
    render(<TopicCard {...defaultProps} topic={topicWithContext} />);
    expect(screen.getByText(/Context:/i)).toBeInTheDocument();
    expect(screen.getByText(/This is the conversation context/i)).toBeInTheDocument();
  });

  test('applies correct confidence color class', () => {
    const { container } = render(<TopicCard {...defaultProps} />);
    const card = container.querySelector('.topic-card');
    expect(card).toHaveClass('high');
  });

  test('applies selected class when selected', () => {
    const { container } = render(<TopicCard {...defaultProps} isSelected={true} />);
    const card = container.querySelector('.topic-card');
    expect(card).toHaveClass('selected');
  });

  test('applies active-research class when research is active', () => {
    const activeTopic = { ...mockTopic, is_active_research: true };
    const { container } = render(<TopicCard {...defaultProps} topic={activeTopic} />);
    const card = container.querySelector('.topic-card');
    expect(card).toHaveClass('active-research');
  });
});



