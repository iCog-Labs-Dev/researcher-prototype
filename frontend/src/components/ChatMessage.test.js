import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatMessage from './ChatMessage';
import { trackEngagement } from '../utils/engagementTracker';
import { trackLinkClick } from '../services/api';

// Mock dependencies
jest.mock('../utils/engagementTracker');
jest.mock('../services/api');

describe('ChatMessage Component', () => {
  const defaultProps = {
    role: 'assistant',
    content: 'Test message content',
    messageId: 'msg-123'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    trackEngagement.mockResolvedValue(undefined);
    trackLinkClick.mockResolvedValue(undefined);
  });

  test('renders message content', () => {
    render(<ChatMessage {...defaultProps} />);
    expect(screen.getByText('Test message content')).toBeInTheDocument();
  });

  test('renders user message correctly', () => {
    render(<ChatMessage {...defaultProps} role="user" />);
    const message = screen.getByText('Test message content').closest('.message');
    expect(message).toHaveClass('user');
  });

  test('renders assistant message correctly', () => {
    render(<ChatMessage {...defaultProps} role="assistant" />);
    const message = screen.getByText('Test message content').closest('.message');
    expect(message).toHaveClass('assistant');
  });

  test('shows and hides sources when toggle is clicked', () => {
    const contentWithSources = 'Main content\n\n**Sources:**\nSource 1\nSource 2';
    render(<ChatMessage {...defaultProps} content={contentWithSources} />);
    
    const toggleButton = screen.getByText(/Show Sources/i);
    expect(toggleButton).toBeInTheDocument();
    expect(screen.queryByText(/Source 1/i)).not.toBeInTheDocument();
    
    fireEvent.click(toggleButton);
    expect(screen.getByText(/Hide Sources/i)).toBeInTheDocument();
    expect(screen.getByText(/Source 1/i)).toBeInTheDocument();
    
    fireEvent.click(screen.getByText(/Hide Sources/i));
    expect(screen.queryByText(/Source 1/i)).not.toBeInTheDocument();
  });

  test('tracks engagement when sources are shown', async () => {
    const contentWithSources = 'Main content\n\n**Sources:**\nSource 1';
    render(<ChatMessage {...defaultProps} content={contentWithSources} />);
    
    const toggleButton = screen.getByText(/Show Sources/i);
    fireEvent.click(toggleButton);
    
    await waitFor(() => {
      expect(trackEngagement).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'source_exploration',
          messageId: 'msg-123'
        })
      );
    });
  });

  test('renders follow-up questions when provided', () => {
    const followUpQuestions = ['Question 1?', 'Question 2?'];
    const mockOnFollowUpClick = jest.fn();
    render(
      <ChatMessage 
        {...defaultProps} 
        followUpQuestions={followUpQuestions}
        onFollowUpClick={mockOnFollowUpClick}
      />
    );
    
    expect(screen.getByText(/Suggested Follow-Up Questions/i)).toBeInTheDocument();
    expect(screen.getByText('Question 1?')).toBeInTheDocument();
    expect(screen.getByText('Question 2?')).toBeInTheDocument();
  });

  test('calls onFollowUpClick when follow-up question is clicked', () => {
    const followUpQuestions = ['Question 1?'];
    const mockOnFollowUpClick = jest.fn();
    render(
      <ChatMessage 
        {...defaultProps} 
        followUpQuestions={followUpQuestions}
        onFollowUpClick={mockOnFollowUpClick}
      />
    );
    
    fireEvent.click(screen.getByText('Question 1?'));
    expect(mockOnFollowUpClick).toHaveBeenCalledWith('Question 1?');
  });

  test('shows feedback buttons for assistant messages', () => {
    render(<ChatMessage {...defaultProps} role="assistant" />);
    expect(screen.getByText('👍 Helpful')).toBeInTheDocument();
    expect(screen.getByText('👎 Not helpful')).toBeInTheDocument();
  });

  test('does not show feedback buttons for user messages', () => {
    render(<ChatMessage {...defaultProps} role="user" />);
    expect(screen.queryByText(/Helpful/i)).not.toBeInTheDocument();
  });

  test('handles upvote feedback', async () => {
    render(<ChatMessage {...defaultProps} role="assistant" />);
    const upvoteButton = screen.getByText('👍 Helpful');
    
    fireEvent.click(upvoteButton);
    
    await waitFor(() => {
      expect(trackEngagement).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'feedback',
          messageId: 'msg-123',
          feedback: 'up'
        })
      );
    });
    
    expect(screen.getByText('👍 Thanks!')).toBeInTheDocument();
  });

  test('handles downvote feedback', async () => {
    render(<ChatMessage {...defaultProps} role="assistant" />);
    const downvoteButton = screen.getByText(/Not helpful/i);
    
    fireEvent.click(downvoteButton);
    
    await waitFor(() => {
      expect(trackEngagement).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'feedback',
          messageId: 'msg-123',
          feedback: 'down'
        })
      );
    });
    
    expect(screen.getByText(/Noted/i)).toBeInTheDocument();
  });

  test('shows routing info toggle for assistant messages with routingInfo', () => {
    const routingInfo = { decision: 'research', reason: 'Test reason' };
    render(<ChatMessage {...defaultProps} role="assistant" routingInfo={routingInfo} />);
    expect(screen.getByText(/Show Routing Info/i)).toBeInTheDocument();
  });

  test('shows routing info when toggle is clicked', () => {
    const routingInfo = { 
      decision: 'research', 
      reason: 'Test reason',
      model_used: 'gpt-4'
    };
    render(<ChatMessage {...defaultProps} role="assistant" routingInfo={routingInfo} />);
    
    const toggleButton = screen.getByText(/Show Routing Info/i);
    fireEvent.click(toggleButton);
    
    expect(screen.getByText(/Hide Routing Info/i)).toBeInTheDocument();
    expect(screen.getByText('research')).toBeInTheDocument();
    expect(screen.getByText('Test reason')).toBeInTheDocument();
    expect(screen.getByText('gpt-4')).toBeInTheDocument();
  });

  test('does not show routing info for user messages', () => {
    const routingInfo = { decision: 'research' };
    render(<ChatMessage {...defaultProps} role="user" routingInfo={routingInfo} />);
    expect(screen.queryByText(/Show Routing Info/i)).not.toBeInTheDocument();
  });

  test('renders markdown content correctly', () => {
    const markdownContent = '**Bold text** and *italic text*';
    render(<ChatMessage {...defaultProps} content={markdownContent} />);
    // ReactMarkdown will render this, so we check for the rendered content
    expect(screen.getByText(/Bold text/i)).toBeInTheDocument();
  });

  test('renders markdown content with links', () => {
    const contentWithLink = 'Check [this link](https://example.com)';
    render(<ChatMessage {...defaultProps} content={contentWithLink} />);
    
    // Since we're mocking react-markdown, it just renders the raw text
    // In a real scenario, react-markdown would parse and render the link
    expect(screen.getByText(/Check \[this link\]\(https:\/\/example\.com\)/)).toBeInTheDocument();
  });
});



