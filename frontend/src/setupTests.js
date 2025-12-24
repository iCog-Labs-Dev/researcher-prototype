// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock react-markdown to avoid ESM issues in tests
jest.mock('react-markdown', () => {
  return function ReactMarkdown({ children }) {
    return <div>{children}</div>;
  };
});

// Mock d3 to avoid ES module issues in tests
jest.mock('d3', () => {
  const mockForceSimulation = () => ({
    force: jest.fn().mockReturnThis(),
    nodes: jest.fn().mockReturnThis(),
    links: jest.fn().mockReturnThis(),
    alpha: jest.fn().mockReturnThis(),
    restart: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
    stop: jest.fn().mockReturnThis(),
  });

  const mockSelection = () => ({
    append: jest.fn().mockReturnThis(),
    attr: jest.fn().mockReturnThis(),
    style: jest.fn().mockReturnThis(),
    call: jest.fn().mockReturnThis(),
    selectAll: jest.fn().mockReturnThis(),
    data: jest.fn().mockReturnThis(),
    enter: jest.fn().mockReturnThis(),
    exit: jest.fn().mockReturnThis(),
    remove: jest.fn().mockReturnThis(),
    text: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
  });

  return {
    forceSimulation: jest.fn(mockForceSimulation),
    forceLink: jest.fn(() => ({
      id: jest.fn().mockReturnThis(),
      distance: jest.fn().mockReturnThis(),
      strength: jest.fn().mockReturnThis(),
    })),
    forceManyBody: jest.fn(() => ({
      strength: jest.fn().mockReturnThis(),
    })),
    forceCenter: jest.fn(() => ({
      x: jest.fn().mockReturnThis(),
      y: jest.fn().mockReturnThis(),
    })),
    select: jest.fn(mockSelection),
    drag: jest.fn(() => ({
      on: jest.fn().mockReturnThis(),
    })),
    zoom: jest.fn(() => ({
      on: jest.fn().mockReturnThis(),
      scaleExtent: jest.fn().mockReturnThis(),
    })),
    zoomIdentity: jest.fn(),
    event: {
      transform: { x: 0, y: 0, k: 1 },
    },
  };
});

// Mock scrollIntoView for refs in tests
Element.prototype.scrollIntoView = jest.fn();

// Create a root element for react-modal if it doesn't exist
if (!document.getElementById('root')) {
  const root = document.createElement('div');
  root.id = 'root';
  document.body.appendChild(root);
}

// Suppress console.log during tests but keep errors for debugging
const originalConsole = global.console;
global.console = {
  ...console,
  log: jest.fn(), // Suppress debug logs
  // Keep error and warn for important issues, but filter out expected test errors
  error: (...args) => {
    const message = args[0]?.toString() || '';
    // Suppress expected network errors during testing
    if (message.includes('Network Error') || message.includes('ECONNREFUSED')) {
      return;
    }
    originalConsole.error(...args);
  }
};
