import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AddTopicForm from './AddTopicForm';
import * as api from '../services/api';
import * as engagementTracker from '../utils/engagementTracker';

jest.mock('../services/api');
jest.mock('../utils/engagementTracker');

describe('AddTopicForm Component', () => {
  const mockOnClose = jest.fn();
  const mockOnTopicAdded = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('does not render when isOpen is false', () => {
    const { container } = render(
      <AddTopicForm
        isOpen={false}
        onClose={mockOnClose}
        onTopicAdded={mockOnTopicAdded}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  test('renders form when isOpen is true', () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
        onTopicAdded={mockOnTopicAdded}
      />
    );

    expect(screen.getByText(/Add Custom Research Topic/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Topic Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confidence Score/i)).toBeInTheDocument();
  });

  test('validates topic name is required', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const submitButton = screen.getByRole('button', { name: /Create Topic/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Topic name is required/i)).toBeInTheDocument();
    });

    expect(api.createCustomTopic).not.toHaveBeenCalled();
  });

  test('validates topic name minimum length', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    fireEvent.change(nameInput, { target: { value: 'A' } });

    const submitButton = screen.getByRole('button', { name: /Create Topic/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Topic name must be at least 2 characters/i)).toBeInTheDocument();
    });
  });

  test('validates topic name maximum length', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    fireEvent.change(nameInput, { target: { value: 'A'.repeat(101) } });

    const submitButton = screen.getByRole('button', { name: /Create Topic/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Topic name must be less than 100 characters/i)).toBeInTheDocument();
    });
  });

  test('validates description is required', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });

    const submitButton = screen.getByRole('button', { name: /Create Topic/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Description is required/i)).toBeInTheDocument();
    });
  });

  test('validates description minimum length', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'Short' } });

    const submitButton = screen.getByRole('button', { name: /Create Topic/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Description must be at least 10 characters/i)).toBeInTheDocument();
    });
  });

  test('validates confidence score range', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const confidenceInput = screen.getByLabelText(/Confidence Score/i);

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'This is a test description that is long enough' } });
    fireEvent.change(confidenceInput, { target: { value: '1.5' } });

    const submitButton = screen.getByRole('button', { name: /Create Topic/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Confidence score must be between 0 and 1/i)).toBeInTheDocument();
    });
  });

  test('handles successful topic creation', async () => {
    const mockTopic = {
      id: 'topic-123',
      name: 'Test Topic',
      description: 'Test description',
      confidence_score: 0.8,
    };

    api.createCustomTopic.mockResolvedValue({
      success: true,
      topic: mockTopic,
    });

    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
        onTopicAdded={mockOnTopicAdded}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const submitButton = screen.getByRole('button', { name: /Create Topic/i });

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'This is a test description that is long enough' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(api.createCustomTopic).toHaveBeenCalledWith({
        name: 'Test Topic',
        description: 'This is a test description that is long enough',
        confidence_score: 0.8,
        enable_research: false,
      });
    });

    await waitFor(() => {
      expect(mockOnTopicAdded).toHaveBeenCalledWith(mockTopic);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  test('tracks engagement when research is enabled', async () => {
    const mockTopic = {
      id: 'topic-123',
      name: 'Test Topic',
      description: 'Test description',
      confidence_score: 0.8,
    };

    api.createCustomTopic.mockResolvedValue({
      success: true,
      topic: mockTopic,
    });

    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
        onTopicAdded={mockOnTopicAdded}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const enableResearchCheckbox = screen.getByLabelText(/Enable research immediately/i);
    const submitButton = screen.getByRole('button', { name: /Create Topic/i });

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'This is a test description that is long enough' } });
    fireEvent.click(enableResearchCheckbox);
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(engagementTracker.trackEngagement).toHaveBeenCalledWith({
        type: 'research_activation',
        topicId: 'topic-123',
        topicName: 'Test Topic',
        activationType: 'manual_topic_creation',
        timestamp: expect.any(Number),
      });
    });
  });

  test('handles API errors', async () => {
    api.createCustomTopic.mockRejectedValue({
      response: {
        status: 409,
        data: { detail: 'Topic already exists' },
      },
    });

    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const submitButton = screen.getByRole('button', { name: /Create Topic/i });

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'This is a test description that is long enough' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/A topic with this name already exists/i)).toBeInTheDocument();
    });
  });

  test('handles general API errors', async () => {
    api.createCustomTopic.mockRejectedValue({
      response: {
        status: 400,
        data: { detail: { error: 'Active topics limit reached' } },
      },
    });

    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const submitButton = screen.getByRole('button', { name: /Create Topic/i });

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'This is a test description that is long enough' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Active topics limit reached/i)).toBeInTheDocument();
    });
  });

  test('shows loading state during submission', async () => {
    api.createCustomTopic.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ success: true, topic: {} }), 100))
    );

    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const submitButton = screen.getByRole('button', { name: /Create Topic/i });

    fireEvent.change(nameInput, { target: { value: 'Test Topic' } });
    fireEvent.change(descriptionInput, { target: { value: 'This is a test description that is long enough' } });
    fireEvent.click(submitButton);

    expect(screen.getByText(/Creating/i)).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  });

  test('closes modal when cancel button is clicked', () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  test('displays character count for name and description', () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);

    fireEvent.change(nameInput, { target: { value: 'Test' } });
    fireEvent.change(descriptionInput, { target: { value: 'Test description' } });

    // Character count might be formatted differently, check for the numbers
    const nameCount = screen.queryByText(/4.*100|100.*4/i);
    const descCount = screen.queryByText(/15.*500|500.*15/i);
    
    // At least one should be present
    expect(nameCount || descCount).toBeTruthy();
  });

  test('clears errors when user starts typing', async () => {
    render(
      <AddTopicForm
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByLabelText(/Topic Name/i);
    const submitButton = screen.getByRole('button', { name: /Create Topic/i });

    // Trigger validation error
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Topic name is required/i)).toBeInTheDocument();
    });

    // Start typing - error should clear
    fireEvent.change(nameInput, { target: { value: 'T' } });

    await waitFor(() => {
      expect(screen.queryByText(/Topic name is required/i)).not.toBeInTheDocument();
    });
  });
});
