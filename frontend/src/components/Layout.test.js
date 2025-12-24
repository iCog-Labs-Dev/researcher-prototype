import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Layout from './Layout';

// Mock Navigation component
jest.mock('./Navigation', () => {
  return function MockNavigation() {
    return <nav>Navigation</nav>;
  };
});

describe('Layout Component', () => {
  test('renders navigation', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    );

    expect(screen.getByText('Navigation')).toBeInTheDocument();
  });

  test('renders main content area', () => {
    const { container } = render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    );

    const mainContent = container.querySelector('.main-content');
    expect(mainContent).toBeInTheDocument();
  });
});
