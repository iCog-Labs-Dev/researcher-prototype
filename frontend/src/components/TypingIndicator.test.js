import React from 'react';
import { render, screen } from '@testing-library/react';
import TypingIndicator from './TypingIndicator';

describe('TypingIndicator Component', () => {
  test('renders typing indicator', () => {
    const { container } = render(<TypingIndicator />);
    const indicator = container.querySelector('#typing-indicator');
    expect(indicator).toBeInTheDocument();
  });

  test('has correct CSS classes', () => {
    const { container } = render(<TypingIndicator />);
    const indicator = container.querySelector('.typing-indicator');
    expect(indicator).toBeInTheDocument();
    expect(indicator).toHaveClass('message', 'assistant', 'typing-indicator');
  });

  test('renders three animation spans', () => {
    const { container } = render(<TypingIndicator />);
    const spans = container.querySelectorAll('.typing-indicator span');
    expect(spans).toHaveLength(3);
  });
});



