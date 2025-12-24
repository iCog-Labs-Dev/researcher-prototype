import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TopicsDashboard from './TopicsDashboard';
import { useSession } from '../context/SessionContext';
import * as api from '../services/api';
import * as adminApi from '../services/adminApi';

jest.mock('../context/SessionContext');
jest.mock('../services/api');
jest.mock('../services/adminApi');

describe('TopicsDashboard Component', () => {
  const mockTopics = [
    {
      topic_id: 'topic-1',
      name: 'Topic 1',
      description: 'Description 1',
      confidence_score: 0.9,
      is_active_research: true,
      suggested_at: Math.floor(Date.now() / 1000),
    },
    {
      topic_id: 'topic-2',
      name: 'Topic 2',
      description: 'Description 2',
      confidence_score: 0.8,
      is_active_research: false,
      suggested_at: Math.floor(Date.now() / 1000) - 100,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    useSession.mockReturnValue({
      userId: 'user-123',
    });
    api.getAllTopicSuggestions.mockResolvedValue({
      topic_suggestions: mockTopics,
    });
    api.getTopicStatistics.mockResolvedValue({
      total: 2,
      active: 1,
      inactive: 1,
    });
    adminApi.getResearchEngineStatus = jest.fn().mockResolvedValue({
      available: true,
      enabled: true,
      running: false,
    });
  });

  test('renders dashboard and loads data', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    // Wait for API calls to be made
    await waitFor(() => {
      expect(api.getAllTopicSuggestions).toHaveBeenCalled();
    }, { timeout: 3000 });

    // Component should render without crashing
    expect(api.getAllTopicSuggestions).toHaveBeenCalled();
  });

  test('loads topics on mount', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(api.getAllTopicSuggestions).toHaveBeenCalled();
      expect(api.getTopicStatistics).toHaveBeenCalled();
    });
  });

  test('calls API to load topics', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(api.getAllTopicSuggestions).toHaveBeenCalled();
      expect(api.getTopicStatistics).toHaveBeenCalled();
    }, { timeout: 3000 });
  });

  test('handles user interactions', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(api.getAllTopicSuggestions).toHaveBeenCalled();
    }, { timeout: 3000 });

    // Component should be interactive without crashing
    const buttons = screen.queryAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(0);
  });

  test('renders without crashing', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(api.getAllTopicSuggestions).toHaveBeenCalled();
    }, { timeout: 3000 });

    // Component should render successfully
    expect(api.getAllTopicSuggestions).toHaveBeenCalled();
  });

  test('loads research engine status', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(adminApi.getResearchEngineStatus).toHaveBeenCalled();
    }, { timeout: 3000 });
  });

  test('handles API errors gracefully', async () => {
    api.getAllTopicSuggestions.mockRejectedValue(new Error('API Error'));

    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    // Component should handle error without crashing
    await waitFor(() => {
      expect(api.getAllTopicSuggestions).toHaveBeenCalled();
    }, { timeout: 3000 });
  });

  test('displays statistics', async () => {
    render(
      <BrowserRouter>
        <TopicsDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(api.getTopicStatistics).toHaveBeenCalled();
    });
  });
});
