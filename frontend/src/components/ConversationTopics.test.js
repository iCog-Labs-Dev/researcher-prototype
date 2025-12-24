import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ConversationTopics from './ConversationTopics';
import { useSession } from '../context/SessionContext';
import * as api from '../services/api';
import * as engagementTracker from '../utils/engagementTracker';

jest.mock('../context/SessionContext');
jest.mock('../services/api');
jest.mock('../utils/engagementTracker');

describe('ConversationTopics Component', () => {
  const mockSessionId = 'session-123';
  const mockOnToggleCollapse = jest.fn();
  const mockOnTopicUpdate = jest.fn();

  const mockTopics = [
    {
      topic_id: 'topic-1',
      name: 'Topic 1',
      description: 'Description 1',
      confidence_score: 0.9,
      is_active_research: false,
      suggested_at: Math.floor(Date.now() / 1000) - 100,
    },
    {
      topic_id: 'topic-2',
      name: 'Topic 2',
      description: 'Description 2',
      confidence_score: 0.8,
      is_active_research: true,
      suggested_at: Math.floor(Date.now() / 1000) - 200,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    useSession.mockReturnValue({
      sessionId: mockSessionId,
    });
    api.getSessionTopicSuggestions.mockResolvedValue({
      topic_suggestions: mockTopics,
    });
  });

  test('renders collapsed view when isCollapsed is true', () => {
    render(
      <ConversationTopics
        isCollapsed={true}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    const expandButton = screen.getByTitle(/Show research topics/i);
    expect(expandButton).toBeInTheDocument();
    expect(screen.queryByText(/Proposed Research Topics/i)).not.toBeInTheDocument();
  });

  test('renders expanded view when isCollapsed is false', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Proposed Research Topics/i)).toBeInTheDocument();
    });
  });

  test('fetches topics on mount', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(api.getSessionTopicSuggestions).toHaveBeenCalledWith(mockSessionId);
    });
  });

  test('displays loading state initially', () => {
    api.getSessionTopicSuggestions.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ topic_suggestions: [] }), 100))
    );

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    expect(screen.getByText(/Loading topics/i)).toBeInTheDocument();
  });

  test('displays empty state when no topics', async () => {
    api.getSessionTopicSuggestions.mockResolvedValue({
      topic_suggestions: [],
    });

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/No research topics yet/i)).toBeInTheDocument();
    });
  });

  test('displays topics when available', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Topic 1')).toBeInTheDocument();
      expect(screen.getByText('Topic 2')).toBeInTheDocument();
    });
  });

  test('calls onTopicUpdate when topics are fetched', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(mockOnTopicUpdate).toHaveBeenCalled();
    });
  });

  test('handles enable research', async () => {
    api.enableTopicResearchById.mockResolvedValue({});

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Topic 1')).toBeInTheDocument();
    });

    // Find the research button for Topic 1
    const researchButtons = screen.getAllByTitle(/Start researching this topic/i);
    fireEvent.click(researchButtons[0]);

    await waitFor(() => {
      expect(api.enableTopicResearchById).toHaveBeenCalledWith('topic-1');
      expect(engagementTracker.trackEngagement).toHaveBeenCalled();
    });
  });

  test('handles disable research', async () => {
    api.disableTopicResearchById.mockResolvedValue({});

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Topic 2')).toBeInTheDocument();
    });

    // Find the stop button for Topic 2 (active research)
    const stopButtons = screen.getAllByTitle(/Stop researching this topic/i);
    fireEvent.click(stopButtons[0]);

    await waitFor(() => {
      expect(api.disableTopicResearchById).toHaveBeenCalledWith('topic-2');
    });
  });

  test('handles delete topic', async () => {
    window.confirm = jest.fn(() => true);
    api.deleteTopicById.mockResolvedValue({});

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Topic 1')).toBeInTheDocument();
    });

    // Find delete buttons
    const deleteButtons = screen.getAllByTitle(/Remove this topic/i);
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(api.deleteTopicById).toHaveBeenCalledWith('topic-1');
    });
  });

  test('handles refresh button click', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Topic 1')).toBeInTheDocument();
    });

    const refreshButton = screen.getByTitle(/Refresh topics/i);
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(api.getSessionTopicSuggestions).toHaveBeenCalledTimes(2);
    });
  });

  test('handles collapse button click', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Proposed Research Topics/i)).toBeInTheDocument();
    });

    const collapseButton = screen.getByTitle(/Hide topics panel/i);
    fireEvent.click(collapseButton);

    expect(mockOnToggleCollapse).toHaveBeenCalled();
  });

  test('displays error modal on error', async () => {
    api.getSessionTopicSuggestions.mockRejectedValue(new Error('API Error'));

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load topics/i)).toBeInTheDocument();
    });
  });

  test('handles error when enabling research', async () => {
    api.enableTopicResearchById.mockRejectedValue({
      response: {
        data: {
          detail: { error: 'Active topics limit reached' },
        },
      },
    });

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Topic 1')).toBeInTheDocument();
    });

    const researchButtons = screen.getAllByTitle(/Start researching this topic/i);
    fireEvent.click(researchButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Active topics limit reached/i)).toBeInTheDocument();
    });
  });

  test('clears topics when sessionId is null', async () => {
    useSession.mockReturnValue({
      sessionId: null,
    });

    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/No research topics yet/i)).toBeInTheDocument();
    });

    expect(api.getSessionTopicSuggestions).not.toHaveBeenCalled();
  });

  test('shows last update time', async () => {
    render(
      <ConversationTopics
        isCollapsed={false}
        onToggleCollapse={mockOnToggleCollapse}
        onTopicUpdate={mockOnTopicUpdate}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Updated/i)).toBeInTheDocument();
    });
  });
});
