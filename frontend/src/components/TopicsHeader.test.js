import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TopicsHeader from './TopicsHeader';

describe('TopicsHeader Component', () => {
  const defaultStats = {
    total_topics: 10,
    total_sessions: 5,
    average_confidence_score: 0.75
  };

  const defaultResearchEngineStatus = {
    running: false
  };

  const defaultProps = {
    stats: defaultStats,
    selectedCount: 0,
    totalCount: 10,
    onCleanup: jest.fn(),
    onBulkDelete: jest.fn(),
    onSelectAll: jest.fn(),
    loading: false,
    researchEngineStatus: defaultResearchEngineStatus,
    onToggleGlobalResearch: jest.fn(),
    researchEngineLoading: false,
    activeTopicsCount: 3,
    onImmediateResearch: jest.fn(),
    immediateResearchLoading: false,
    onShowMotivation: jest.fn(),
    onShowEngineSettings: jest.fn(),
    onDeleteNonActivated: jest.fn(),
    onAddCustomTopic: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders header title and subtitle', () => {
    render(<TopicsHeader {...defaultProps} />);
    expect(screen.getByText('Research Topics')).toBeInTheDocument();
    expect(screen.getByText(/Discover and manage AI-suggested research topics/i)).toBeInTheDocument();
  });

  test('displays stats overview', () => {
    render(<TopicsHeader {...defaultProps} />);
    expect(screen.getByText('3')).toBeInTheDocument(); // Active Research
    expect(screen.getByText('10')).toBeInTheDocument(); // Total Topics
    expect(screen.getByText('5')).toBeInTheDocument(); // Sessions
    expect(screen.getByText('0.8')).toBeInTheDocument(); // Avg Confidence (rounded)
  });

  test('displays research engine status', () => {
    render(<TopicsHeader {...defaultProps} />);
    expect(screen.getByText(/Research Engine: Inactive/i)).toBeInTheDocument();
  });

  test('shows active status when engine is running', () => {
    const runningStatus = { running: true };
    render(<TopicsHeader {...defaultProps} researchEngineStatus={runningStatus} />);
    expect(screen.getByText(/Research Engine: Active/i)).toBeInTheDocument();
  });

  test('calls onToggleGlobalResearch when engine toggle is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const toggleButton = screen.getByText(/Enable/i);
    fireEvent.click(toggleButton);
    expect(defaultProps.onToggleGlobalResearch).toHaveBeenCalled();
  });

  test('shows stop button when engine is running', () => {
    const runningStatus = { running: true };
    render(<TopicsHeader {...defaultProps} researchEngineStatus={runningStatus} />);
    expect(screen.getByText(/Stop/i)).toBeInTheDocument();
  });

  test('calls onImmediateResearch when run now button is clicked', () => {
    const runningStatus = { running: true };
    render(<TopicsHeader {...defaultProps} researchEngineStatus={runningStatus} />);
    const runNowButton = screen.getByText(/Run/i);
    fireEvent.click(runNowButton);
    expect(defaultProps.onImmediateResearch).toHaveBeenCalled();
  });

  test('disables immediate research when engine is not running', () => {
    render(<TopicsHeader {...defaultProps} />);
    const runNowButton = screen.getByText(/Run/i);
    expect(runNowButton.closest('button')).toBeDisabled();
  });

  test('disables immediate research when no active topics', () => {
    const runningStatus = { running: true };
    render(<TopicsHeader {...defaultProps} researchEngineStatus={runningStatus} activeTopicsCount={0} />);
    const runNowButton = screen.getByText(/Run/i);
    expect(runNowButton.closest('button')).toBeDisabled();
  });

  test('calls onShowMotivation when view drives button is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const viewDrivesButton = screen.getByText(/View/i);
    fireEvent.click(viewDrivesButton);
    expect(defaultProps.onShowMotivation).toHaveBeenCalled();
  });

  test('calls onShowEngineSettings when research timing button is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const timingButton = screen.getByTitle(/Configure research timing/i);
    fireEvent.click(timingButton);
    expect(defaultProps.onShowEngineSettings).toHaveBeenCalled();
  });

  test('displays selection count when topics are selected', () => {
    render(<TopicsHeader {...defaultProps} selectedCount={3} />);
    expect(screen.getByText(/3 of 10 selected/i)).toBeInTheDocument();
  });

  test('displays total count when no topics are selected', () => {
    render(<TopicsHeader {...defaultProps} selectedCount={0} />);
    expect(screen.getByText(/10 topics shown/i)).toBeInTheDocument();
  });

  test('displays singular form for single topic', () => {
    render(<TopicsHeader {...defaultProps} totalCount={1} />);
    expect(screen.getByText(/1 topic shown/i)).toBeInTheDocument();
  });

  test('calls onAddCustomTopic when add topic button is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const addButton = screen.getByText(/Add Topic/i);
    fireEvent.click(addButton);
    expect(defaultProps.onAddCustomTopic).toHaveBeenCalled();
  });

  test('calls onSelectAll when select all button is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const selectAllButton = screen.getByText(/Select All/i);
    fireEvent.click(selectAllButton);
    expect(defaultProps.onSelectAll).toHaveBeenCalled();
  });

  test('shows deselect all when all topics are selected', () => {
    render(<TopicsHeader {...defaultProps} selectedCount={10} totalCount={10} />);
    expect(screen.getByText(/Deselect All/i)).toBeInTheDocument();
  });

  test('calls onBulkDelete when delete selected button is clicked', () => {
    render(<TopicsHeader {...defaultProps} selectedCount={3} />);
    const deleteButton = screen.getByText(/Delete Selected/i);
    fireEvent.click(deleteButton);
    expect(defaultProps.onBulkDelete).toHaveBeenCalled();
  });

  test('shows selected count in delete button', () => {
    render(<TopicsHeader {...defaultProps} selectedCount={5} />);
    expect(screen.getByText(/Delete Selected \(5\)/i)).toBeInTheDocument();
  });

  test('calls onCleanup when cleanup button is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const cleanupButton = screen.getByText(/Cleanup/i);
    fireEvent.click(cleanupButton);
    expect(defaultProps.onCleanup).toHaveBeenCalled();
  });

  test('calls onDeleteNonActivated when delete inactive button is clicked', () => {
    render(<TopicsHeader {...defaultProps} />);
    const deleteInactiveButton = screen.getByText(/Delete Inactive/i);
    fireEvent.click(deleteInactiveButton);
    expect(defaultProps.onDeleteNonActivated).toHaveBeenCalled();
  });

  test('disables buttons when loading', () => {
    render(<TopicsHeader {...defaultProps} loading={true} />);
    const addButton = screen.getByText(/Add Topic/i);
    expect(addButton).toBeDisabled();
  });

  test('disables engine toggle when research engine is loading', () => {
    render(<TopicsHeader {...defaultProps} researchEngineLoading={true} />);
    const toggleButton = screen.getByText(/Starting/i);
    expect(toggleButton.closest('button')).toBeDisabled();
  });

  test('shows loading state for immediate research', () => {
    const runningStatus = { running: true };
    render(
      <TopicsHeader 
        {...defaultProps} 
        researchEngineStatus={runningStatus}
        immediateResearchLoading={true}
      />
    );
    expect(screen.getByText(/Searching/i)).toBeInTheDocument();
  });

  test('does not show select all button when no topics', () => {
    render(<TopicsHeader {...defaultProps} totalCount={0} />);
    expect(screen.queryByText(/Select All/i)).not.toBeInTheDocument();
  });

  test('does not show bulk delete button when no topics selected', () => {
    render(<TopicsHeader {...defaultProps} selectedCount={0} />);
    expect(screen.queryByText(/Delete Selected/i)).not.toBeInTheDocument();
  });
});



