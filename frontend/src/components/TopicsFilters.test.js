import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TopicsFilters from './TopicsFilters';

describe('TopicsFilters Component', () => {
  const mockOnFiltersChange = jest.fn();
  const defaultFilters = {
    searchTerm: '',
    sortBy: 'confidence',
    sortOrder: 'desc',
    autoOnly: false,
    groupBy: 'none'
  };

  const defaultProps = {
    filters: defaultFilters,
    onFiltersChange: mockOnFiltersChange,
    topicsCount: 10
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders all filter controls', () => {
    render(<TopicsFilters {...defaultProps} />);
    expect(screen.getByLabelText(/Search Topics/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Sort By/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Group/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Auto expansions only/i)).toBeInTheDocument();
  });

  test('displays topics count', () => {
    render(<TopicsFilters {...defaultProps} topicsCount={5} />);
    expect(screen.getByText(/5 topic/i)).toBeInTheDocument();
  });

  test('displays plural form for multiple topics', () => {
    render(<TopicsFilters {...defaultProps} topicsCount={2} />);
    expect(screen.getByText(/2 topics/i)).toBeInTheDocument();
  });

  test('updates search term when input changes', () => {
    render(<TopicsFilters {...defaultProps} />);
    const searchInput = screen.getByPlaceholderText(/Search by name or description/i);
    
    fireEvent.change(searchInput, { target: { value: 'test' } });
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    expect(typeof lastCall).toBe('function');
  });

  test('clears search when clear button is clicked', () => {
    render(<TopicsFilters {...defaultProps} filters={{ ...defaultFilters, searchTerm: 'test' }} />);
    const clearButton = screen.getByTitle(/Clear search/i);
    fireEvent.click(clearButton);
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    const result = lastCall(defaultFilters);
    expect(result.searchTerm).toBe('');
  });

  test('clear search button is disabled when search is empty', () => {
    render(<TopicsFilters {...defaultProps} />);
    const clearButton = screen.getByTitle(/No search to clear/i);
    expect(clearButton).toBeDisabled();
  });

  test('updates sort by when select changes', () => {
    render(<TopicsFilters {...defaultProps} />);
    const sortSelect = screen.getByLabelText(/Sort By/i);
    fireEvent.change(sortSelect, { target: { value: 'date' } });
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
  });

  test('toggles sort order when button is clicked', () => {
    render(<TopicsFilters {...defaultProps} />);
    const sortOrderButton = screen.getByTitle(/Sort ascending/i);
    fireEvent.click(sortOrderButton);
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    const result = lastCall(defaultFilters);
    expect(result.sortOrder).toBe('asc');
  });

  test('updates group by when select changes', () => {
    render(<TopicsFilters {...defaultProps} />);
    const groupSelect = screen.getByLabelText(/Group/i);
    fireEvent.change(groupSelect, { target: { value: 'parent' } });
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
  });

  test('toggles auto only checkbox', () => {
    render(<TopicsFilters {...defaultProps} />);
    const autoCheckbox = screen.getByLabelText(/Auto expansions only/i);
    fireEvent.click(autoCheckbox);
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    const result = lastCall(defaultFilters);
    expect(result.autoOnly).toBe(true);
  });

  test('shows clear filters button when search term is active', () => {
    render(<TopicsFilters {...defaultProps} filters={{ ...defaultFilters, searchTerm: 'test' }} />);
    expect(screen.getByText(/Clear Search/i)).toBeInTheDocument();
  });

  test('clears all filters when clear button is clicked', () => {
    render(<TopicsFilters {...defaultProps} filters={{ ...defaultFilters, searchTerm: 'test', sortBy: 'date' }} />);
    const clearButton = screen.getByText(/Clear Search/i);
    fireEvent.click(clearButton);
    
    expect(mockOnFiltersChange).toHaveBeenCalled();
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    const result = lastCall({ ...defaultFilters, searchTerm: 'test', sortBy: 'date' });
    expect(result.searchTerm).toBe('');
    expect(result.sortBy).toBe('confidence');
    expect(result.sortOrder).toBe('desc');
    expect(result.autoOnly).toBe(false);
  });

  test('shows filtered indicator when filters are active', () => {
    render(<TopicsFilters {...defaultProps} filters={{ ...defaultFilters, searchTerm: 'test' }} />);
    expect(screen.getByText(/\(filtered\)/i)).toBeInTheDocument();
  });

  test('does not show filtered indicator when no filters are active', () => {
    render(<TopicsFilters {...defaultProps} />);
    expect(screen.queryByText(/\(filtered\)/i)).not.toBeInTheDocument();
  });
});



