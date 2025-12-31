# Frontend Handover Document
## Qwestor AI Research Assistant - Frontend

**Version:** 1.0.0  
**Date:** January 2025  
**Framework:** React 19.1.0  
**Build Tool:** Create React App (react-scripts 5.0.1)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Application Architecture](#application-architecture)
5. [State Management](#state-management)
6. [Key Components](#key-components)
7. [API Integration](#api-integration)
8. [Routing](#routing)
9. [Testing](#testing)
10. [Development Workflow](#development-workflow)
11. [Build & Deployment](#build--deployment)
12. [Configuration](#configuration)
13. [Styling](#styling)
14. [Troubleshooting](#troubleshooting)
15. [Important Notes](#important-notes)

---

## Executive Summary

The **Qwestor Frontend** is a React 19 Single Page Application (SPA) that provides a comprehensive interface for an AI research assistant. The application features:

- **Chat Interface**: Real-time conversation with AI assistant
- **Research Topics Management**: Create, manage, and monitor research topics
- **Knowledge Graph Visualization**: Interactive D3.js-powered graph viewer
- **User Personalization**: Three-tab interface for personality and preferences
- **Admin Console**: Prompt management and system monitoring (admin-only)
- **Session Management**: Multi-session chat history
- **Real-time Notifications**: Toast notifications and notification panel

**Key Statistics:**
- **23 Test Suites** with **246 unit tests** + **2 integration tests**
- **100% Test Pass Rate** ✅
- **30+ React Components**
- **4 Context Providers** for state management
- **Zero Class Components** (100% functional with hooks)

---

## Technology Stack

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **react** | ^19.1.0 | UI framework |
| **react-dom** | ^19.1.0 | React DOM renderer |
| **react-router-dom** | ^6.28.1 | Client-side routing |
| **axios** | ^1.9.0 | HTTP client for API calls |
| **d3** | ^7.9.0 | Knowledge graph visualization |
| **react-markdown** | ^9.0.1 | Markdown rendering in chat |
| **react-modal** | ^3.16.3 | Modal dialogs |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **react-scripts** | 5.0.1 | Create React App build tool |
| **@testing-library/react** | ^16.3.0 | React component testing |
| **@testing-library/jest-dom** | ^6.6.3 | DOM matchers for Jest |
| **@testing-library/user-event** | ^13.5.0 | User interaction simulation |
| **eslint** | (via react-scripts) | Code linting |

### Build & Tooling

- **Create React App**: Zero-configuration build setup
- **Webpack**: Bundling (via react-scripts)
- **Babel**: JavaScript transpilation
- **Jest**: Test runner
- **ESLint**: Code quality (react-app config)

---

## Project Structure

```
frontend/
├── public/                          # Static assets
│   ├── index.html                   # HTML template
│   ├── favicon.ico
│   └── logo*.png                    # App logos
│
├── src/
│   ├── App.jsx                      # Root component & routing
│   ├── App.css                      # Global styles
│   ├── index.js                     # Application entry point
│   ├── setupTests.js                # Test configuration & mocks
│   │
│   ├── components/                  # React components
│   │   ├── ChatPage.jsx             # Main chat interface
│   │   ├── ChatInput.jsx            # Message input component
│   │   ├── ChatMessage.jsx          # Individual message display
│   │   ├── TopicsDashboard.jsx      # Research topics management
│   │   ├── UserProfile.jsx           # Personalization settings
│   │   ├── Navigation.jsx           # Main navigation bar
│   │   ├── Layout.jsx               # App layout wrapper
│   │   ├── ProtectedRoute.jsx       # Auth-protected routes
│   │   │
│   │   ├── admin/                   # Admin components
│   │   │   ├── AdminDashboard.jsx   # Admin console
│   │   │   ├── AdminLogin.jsx       # Admin login
│   │   │   ├── PromptEditor.jsx     # Prompt management
│   │   │   ├── FlowVisualization.jsx # Graph diagrams
│   │   │   └── ProtectedAdminRoute.jsx
│   │   │
│   │   ├── graph/                   # Knowledge graph
│   │   │   ├── KnowledgeGraphViewer.jsx
│   │   │   ├── GraphVisualization.jsx
│   │   │   ├── Graph.jsx
│   │   │   └── GraphPopovers.jsx
│   │   │
│   │   └── *.test.js                # Component tests (23 files)
│   │
│   ├── context/                     # React Context providers
│   │   ├── AuthContext.jsx          # Authentication state
│   │   ├── SessionContext.jsx       # Chat session state
│   │   ├── NotificationContext.jsx   # Notifications state
│   │   └── AdminContext.jsx         # Admin authentication
│   │
│   ├── services/                    # API services
│   │   ├── api.js                   # Main API client (605 lines)
│   │   ├── adminApi.js              # Admin API client
│   │   └── api.simple.test.js       # API tests
│   │
│   ├── styles/                      # CSS files (28 files)
│   │   ├── *.css                    # Component styles
│   │   └── *.module.css             # CSS modules (if any)
│   │
│   └── utils/                       # Utility functions
│       ├── engagementTracker.js     # User engagement tracking
│       └── testDataIsolation.js     # Test utilities
│
├── package.json                     # Dependencies & scripts
├── .env.example                     # Environment template
├── .env.development                 # Development config
├── .env.production                  # Production config
├── Dockerfile                       # Docker configuration
└── README.md                        # Frontend README
```

---

## Application Architecture

### Component Hierarchy

```
App
├── AuthProvider
│   ├── SessionProvider
│   │   ├── NotificationProvider
│   │   │   └── Router
│   │   │       ├── Routes
│   │   │       │   ├── /admin/login → AdminLogin
│   │   │       │   ├── /admin → ProtectedAdminRoute → AdminDashboard
│   │   │       │   └── / → ProtectedRoute → Layout
│   │   │       │           ├── Navigation
│   │   │       │           └── Outlet
│   │   │       │               ├── / → ChatPage
│   │   │       │               ├── /topics → TopicsDashboard
│   │   │       │               └── /research-results → ResearchResultsDashboard
│   │   │       └── ToastNotifications
```

### Key Architectural Patterns

1. **Context API for State Management**
   - Global state via React Context
   - No Redux or external state library
   - Provider pattern for dependency injection

2. **Functional Components with Hooks**
   - 100% functional components
   - No class components
   - Custom hooks for reusable logic

3. **Protected Routes**
   - `ProtectedRoute`: User authentication required
   - `ProtectedAdminRoute`: Admin role required
   - Automatic redirect to login if unauthorized

4. **API Client Pattern**
   - Centralized Axios instance
   - Automatic token injection
   - Error handling middleware
   - Versioned API endpoints (`/v2`)

5. **Component Composition**
   - Small, focused components
   - Props-based communication
   - Context for cross-cutting concerns

---

## State Management

### Context Providers

#### 1. AuthContext (`context/AuthContext.jsx`)

**Purpose:** User authentication and profile management

**State:**
- `isAuthenticated`: Boolean authentication status
- `token`: JWT token string
- `user`: User object with profile data
- `loading`: Initialization loading state
- `error`: Error message string

**Methods:**
- `login(token, userData)`: Authenticate user
- `logout()`: Clear authentication
- `updateUser(updater)`: Update user profile
- `setError(message)`: Set error message

**Storage:**
- `localStorage.getItem('auth_token')`: JWT token
- `localStorage.getItem('auth_user')`: User JSON

**Usage:**
```javascript
import { useAuth } from '../context/AuthContext';

const { user, isAuthenticated, login, logout } = useAuth();
```

#### 2. SessionContext (`context/SessionContext.jsx`)

**Purpose:** Chat session and message management

**State:**
- `messages`: Array of chat messages
- `sessionId`: Current session ID
- `conversationTopics`: Suggested topics
- `personality`: User personality settings
- `userDisplayName`: Current user's display name

**Methods:**
- `addMessage(message)`: Add message to chat
- `setMessages(messages)`: Replace all messages
- `setSessionId(id)`: Set current session
- `setConversationTopics(topics)`: Update topic suggestions
- `clearSession()`: Reset session

**Usage:**
```javascript
import { useSession } from '../context/SessionContext';

const { messages, sessionId, addMessage } = useSession();
```

#### 3. NotificationContext (`context/NotificationContext.jsx`)

**Purpose:** Real-time notification management

**State:**
- `notifications`: Array of notification objects
- `unreadCount`: Number of unread notifications

**Methods:**
- `addNotification(notification)`: Add new notification
- `markAsRead(id)`: Mark notification as read
- `clearNotifications()`: Clear all notifications

**Usage:**
```javascript
import { useNotifications } from '../context/NotificationContext';

const { notifications, addNotification } = useNotifications();
```

#### 4. AdminContext (`context/AdminContext.jsx`)

**Purpose:** Admin authentication (separate from user auth)

**State:**
- `isAdminAuthenticated`: Admin login status
- `adminToken`: Admin JWT token

**Methods:**
- `adminLogin(token)`: Authenticate admin
- `adminLogout()`: Clear admin auth

---

## Key Components

### Core Application Components

#### 1. App.jsx

**Purpose:** Root component with routing and providers

**Key Features:**
- Sets up all Context providers
- Configures React Router
- Defines route structure
- Renders global components (ToastNotifications)

**Routes:**
- `/` → ChatPage (protected)
- `/topics` → TopicsDashboard (protected)
- `/research-results` → ResearchResultsDashboard (protected)
- `/admin` → AdminDashboard (admin-protected)
- `/admin/login` → AdminLogin

#### 2. ChatPage.jsx

**Purpose:** Main chat interface

**Features:**
- Message display with markdown rendering
- Chat input with send button
- Session management
- Topic sidebar integration
- Typing indicators
- Auto-scroll with user scroll detection
- Follow-up question suggestions
- Routing info display

**State Management:**
- Uses `SessionContext` for messages
- Uses `AuthContext` for user data
- Local state for UI (typing, input value)

**Key Functionality:**
- Sends messages via `sendChatMessage` API
- Handles streaming responses
- Manages session creation/loading
- Displays conversation topics

#### 3. TopicsDashboard.jsx

**Purpose:** Research topics management interface

**Features:**
- Topic listing with filters
- Create custom topics
- Enable/disable research per topic
- Research engine controls (admin-only)
- Topic statistics
- Research timing configuration
- Bulk operations

**Admin-Only Features:**
- Research Engine Status section (only visible to admins)
- Engine toggle controls
- Immediate research trigger
- Engine settings

**State:**
- Topics list from API
- Filter state (active/inactive/all)
- Research engine status

#### 4. UserProfile.jsx

**Purpose:** Personalization settings interface

**Tabs:**
1. **Personality**: Communication style and tone
2. **Preferences**: Research depth, source types, format
3. **What I've Learned**: Transparent view of learned behaviors

**Features:**
- Real-time preference updates
- Personality presets (Academic, Business, Creative, Technical)
- Learning transparency
- Override controls for learned behaviors
- Engagement analytics display

#### 5. Navigation.jsx

**Purpose:** Main navigation bar

**Features:**
- Route navigation links
- User profile dropdown
- Admin access control (role-based)
- Notification panel toggle
- Knowledge graph viewer link
- Logout functionality

**Role-Based Rendering:**
- Admin link only visible to admin users
- Research Engine Status only for admins (in TopicsHeader)

### Admin Components

#### 6. AdminDashboard.jsx

**Purpose:** Admin console main interface

**Features:**
- Prompt editor integration
- Flow visualization
- System status panel
- User management
- Debug tools

#### 7. PromptEditor.jsx

**Purpose:** Visual prompt management

**Features:**
- Edit system prompts
- Version history
- Live testing
- Category organization
- Save/restore functionality

### Graph Components

#### 8. KnowledgeGraphViewer.jsx

**Purpose:** Interactive knowledge graph visualization

**Technology:** D3.js force-directed graph

**Features:**
- Zoom and pan navigation
- Node filtering
- Relationship exploration
- Export capabilities
- Responsive layout

---

## API Integration

### API Client (`services/api.js`)

**Base Configuration:**
```javascript
const API_URL = `${REACT_APP_API_URL}/v2`;
```

**Axios Instance:**
- Base URL: `/v2` (version 2 API)
- Automatic token injection via interceptor
- Error handling

**Token Management:**
```javascript
setAuthTokenHeader(token)  // Set Authorization header
```

**Key API Functions:**

#### Chat APIs
- `sendChatMessage(messages, temperature, maxTokens, personality, sessionId)`
- `getChatHistory(chatId, limit)`
- `getAllChatSessions()`

#### Topic APIs
- `getAllTopicSuggestions()`
- `getTopicSuggestionsBySession(sessionId)`
- `createCustomTopic(name, description, confidence, enableResearch)`
- `enableResearchForTopic(topicId)`
- `disableResearchForTopic(topicId)`
- `deleteTopic(topicId)`

#### Research APIs
- `getResearchStatus()`
- `getResearchFindings(topicId, limit, offset)`
- `triggerResearch(userId)` (admin)

#### User APIs
- `registerUser(email, password, displayName)`
- `loginUser(email, password)`
- `getUserProfile()`
- `updateUserPersonality(personality)`
- `updateUserPreferences(preferences)`

#### Admin APIs (via `services/adminApi.js`)
- `adminLogin(password)`
- `getAllPrompts()`
- `updatePrompt(name, content)`
- `getFlowDiagrams()`
- `generateFlowDiagrams(forceRegenerate)`

### API Error Handling

**Pattern:**
```javascript
try {
  const response = await api.get('/endpoint');
  return response.data;
} catch (error) {
  console.error('Error:', error);
  throw error;
}
```

**Error Types:**
- Network errors (connection refused)
- Authentication errors (401)
- Authorization errors (403)
- Validation errors (400)
- Server errors (500)

### Request Interceptors

**Automatic Token Injection:**
```javascript
api.interceptors.request.use((config) => {
  const authToken = localStorage.getItem('auth_token');
  if (authToken) {
    config.headers['Authorization'] = `Bearer ${authToken}`;
  }
  return config;
});
```

---

## Routing

### Route Structure

**Protected Routes (User Auth Required):**
- `/` → ChatPage
- `/topics` → TopicsDashboard
- `/research-results` → ResearchResultsDashboard

**Admin Routes (Admin Role Required):**
- `/admin` → AdminDashboard
- `/admin/login` → AdminLogin (public)

**Route Protection:**
- `ProtectedRoute`: Checks `isAuthenticated` from AuthContext
- `ProtectedAdminRoute`: Checks admin role from AuthContext
- Redirects to login if unauthorized

### Navigation

**React Router v6:**
- `BrowserRouter` for client-side routing
- `Routes` and `Route` for route definition
- `Link` and `useNavigate` for navigation
- `Outlet` for nested routes

**Example:**
```javascript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
navigate('/topics');
```

---

## Testing

### Test Setup (`setupTests.js`)

**Global Mocks:**
- `react-markdown`: Mocked to avoid ESM issues
- `d3`: Comprehensive mock for graph visualization
- `scrollIntoView`: Mocked for refs
- Console suppression: Logs suppressed, errors kept

**Test Configuration:**
- Jest as test runner (via react-scripts)
- React Testing Library for component testing
- Custom matchers from `@testing-library/jest-dom`

### Test Structure

**Test Files:**
- `*.test.js`: Unit tests (mocked APIs)
- `*.integration.test.js`: Integration tests (real backend)

**Test Commands:**
```bash
npm run test              # Interactive test runner
npm run test:unit         # Unit tests only (fast)
npm run test:integration  # Integration tests (requires backend)
npm run test:all         # All tests
```

### Test Coverage

**Statistics:**
- **23 Test Suites**
- **246 Unit Tests**
- **2 Integration Tests**
- **100% Pass Rate** ✅

**Key Test Files:**
- `ChatPage.comprehensive.test.js`: Main chat functionality (comprehensive)
- `AuthModal.test.js`: Authentication flows
- `TopicsDashboard.test.js`: Topic management
- `ConversationTopics.test.js`: Topic sidebar
- `SessionHistory.test.js`: Session management
- Plus 18+ component tests

### Testing Patterns

**Component Testing:**
```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '../context/AuthContext';

test('renders component', async () => {
  render(
    <AuthProvider>
      <Component />
    </AuthProvider>
  );
  
  await waitFor(() => {
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

**API Mocking:**
```javascript
jest.mock('../services/api', () => ({
  sendChatMessage: jest.fn().mockResolvedValue({ data: {...} }),
}));
```

**Context Mocking:**
```javascript
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'test-user' }, isAuthenticated: true }),
}));
```

---

## Development Workflow

### Starting Development Server

```bash
# Install dependencies (first time)
npm install

# Start development server
npm start
```

**Development Server:**
- URL: http://localhost:3000
- Hot reload enabled
- API proxy to backend (if configured)

### Code Quality Checks

```bash
# Linting
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

**ESLint Configuration:**
- Extends `react-app` and `react-app/jest`
- Enforces React best practices
- Catches common errors

### Running Tests

```bash
# Interactive test runner (watch mode)
npm test

# Unit tests only (fast, mocked)
npm run test:unit

# Integration tests (requires backend running)
npm run test:integration

# All tests
npm run test:all
```

### Building for Production

```bash
# Create production build
npm run build

# Build output: build/
# - Optimized JavaScript bundles
# - Minified CSS
# - Static assets
```

---

## Build & Deployment

### Production Build

**Build Process:**
1. Transpiles JavaScript (Babel)
2. Bundles with Webpack
3. Minifies code
4. Optimizes assets
5. Generates source maps

**Build Output:**
```
build/
├── static/
│   ├── css/
│   ├── js/
│   └── media/
├── index.html
└── asset-manifest.json
```

### Docker Deployment

**Dockerfile:**
- Multi-stage build
- Nginx for serving static files
- Production-optimized

**Build Command:**
```bash
docker build -t qwestor-frontend .
```

### Environment-Specific Builds

**Development:**
- `.env.development`: Development API URL
- Hot reload enabled
- Source maps enabled

**Production:**
- `.env.production`: Production API URL
- Code minification
- Asset optimization

### Deployment Checklist

- [ ] Set `REACT_APP_API_URL` in production environment
- [ ] Run `npm run build`
- [ ] Test production build locally
- [ ] Verify API connectivity
- [ ] Check CORS configuration
- [ ] Test authentication flow
- [ ] Verify admin routes work
- [ ] Test knowledge graph (if Zep enabled)

---

## Configuration

### Environment Variables

**Required:**
```bash
REACT_APP_API_URL=http://localhost:8000  # Backend API URL
```

**Optional:**
```bash
REACT_APP_DEBUG=true                     # Enable debug logging
REACT_APP_GOOGLE_CLIENT_ID=<key>        # Google OAuth (if used)
```

**⚠️ Important:** 
- All frontend env vars must start with `REACT_APP_`
- Variables are embedded at build time
- Restart dev server after changing `.env` files

### Environment Files

**`.env.development`:**
- Used in development mode (`npm start`)
- Local backend URL

**`.env.production`:**
- Used in production build (`npm run build`)
- Production backend URL

**`.env.example`:**
- Template for environment variables
- Documented options

### API Configuration

**API Version:**
- Currently using `/v2` API endpoints
- Configured in `services/api.js`:
  ```javascript
  const API_VERSION_PREFIX = '/v2';
  ```

**Base URL:**
- Read from `REACT_APP_API_URL`
- Fallback: `http://localhost:8000`
- Normalized (removes trailing slashes)

---

## Styling

### CSS Organization

**Structure:**
- `src/styles/`: Component-specific CSS files
- `src/App.css`: Global styles
- Component-level CSS files (e.g., `ChatPage.css`)

**Approach:**
- Plain CSS (no CSS-in-JS)
- Component-scoped styles
- Global styles in `App.css`
- No Tailwind (utility classes in CSS if needed)

### Styling Patterns

**Component Styles:**
```javascript
import './ChatPage.css';

function ChatPage() {
  return <div className="chat-page">...</div>;
}
```

**CSS Classes:**
- BEM-like naming convention
- Component-prefixed classes
- Semantic class names

### Responsive Design

**Breakpoints:**
- Mobile-first approach
- Media queries in CSS
- Flexible layouts

---

## Troubleshooting

### Common Issues

#### 1. API Connection Errors

**Symptom:** "Network Error" or "ECONNREFUSED"

**Solutions:**
- Verify backend is running on port 8000
- Check `REACT_APP_API_URL` in `.env.development`
- Verify CORS configuration on backend
- Check browser console for specific errors

#### 2. Authentication Not Working

**Symptom:** User can't login or stays logged out

**Solutions:**
- Check `localStorage` for `auth_token`
- Verify token is being sent in API requests
- Check backend authentication endpoint
- Clear browser cache and localStorage

#### 3. Tests Failing

**Symptom:** Tests fail with "Cannot find module" or mock errors

**Solutions:**
- Run `npm install` to ensure dependencies
- Check `setupTests.js` for missing mocks
- Verify test file imports are correct
- Clear Jest cache: `npm test -- --clearCache`

#### 4. Build Failures

**Symptom:** `npm run build` fails

**Solutions:**
- Check for ESLint errors: `npm run lint`
- Verify all imports are correct
- Check for undefined variables
- Ensure environment variables are set

#### 5. Knowledge Graph Not Loading

**Symptom:** Graph shows empty or error

**Solutions:**
- Verify Zep is enabled on backend
- Check API endpoint `/v2/graph/fetch`
- Verify D3.js is installed: `npm install d3`
- Check browser console for errors

#### 6. Admin Routes Not Accessible

**Symptom:** Can't access `/admin` even as admin

**Solutions:**
- Verify user role is `admin` in backend
- Check `ProtectedAdminRoute` component
- Verify admin token in localStorage
- Check backend admin authentication

### Debug Tools

**Browser DevTools:**
- React DevTools extension
- Network tab for API calls
- Console for errors
- Application tab for localStorage

**React DevTools:**
- Inspect component tree
- View props and state
- Profile performance

**Debug Mode:**
```bash
# Enable debug logging
REACT_APP_DEBUG=true npm start
```

---

## Important Notes

### 1. Research Engine Status Visibility

**⚠️ Important:** The Research Engine Status section in `TopicsDashboard` is **only visible to admin users**.

**Implementation:**
- `TopicsDashboard` checks user role via `useAuth()`
- Determines `isAdmin` from user role
- Passes `isAdmin` prop to `TopicsHeader`
- Conditional rendering: `{isAdmin && researchEngineStatus && (...)}`

**Files:**
- `components/TopicsDashboard.jsx`: Admin check
- `components/TopicsHeader.jsx`: Conditional rendering

### 2. API Version

**Current:** Using `/v2` API endpoints

**Migration:**
- All API calls use `/v2` prefix
- Configured in `services/api.js`
- Legacy `/api/*` endpoints may still exist but not used

### 3. Authentication Flow

**User Authentication:**
- JWT tokens stored in `localStorage` as `auth_token`
- Token automatically added to API requests via interceptor
- `AuthContext` manages authentication state
- Logout clears token and user data

**Admin Authentication:**
- Separate JWT system
- Token stored as `admin_token` in localStorage
- `AdminContext` manages admin auth
- Role checked on backend

### 4. Session Management

**Behavior:**
- Sessions created automatically on first message
- Session ID returned in chat response
- Session history loaded when switching sessions
- Session state managed by `SessionContext`

### 5. Component Testing

**Mock Requirements:**
- All API calls must be mocked in tests
- Context providers must be mocked or provided
- D3.js is globally mocked in `setupTests.js`
- `react-markdown` is mocked to avoid ESM issues

**Test Patterns:**
- Use `waitFor` for async operations
- Mock contexts with `jest.mock`
- Use `screen` queries from Testing Library
- Clean up after each test

### 6. Environment Variables

**⚠️ Critical:** 
- Variables must start with `REACT_APP_` to be accessible
- Variables are embedded at **build time**
- Changes require rebuild
- Never commit `.env` files with secrets

### 7. Build Optimization

**Production Build:**
- Code splitting enabled
- Minification enabled
- Tree shaking for unused code
- Asset optimization

**Bundle Size:**
- Monitor bundle size with `npm run build`
- Use React DevTools Profiler
- Consider code splitting for large components

### 8. Browser Compatibility

**Supported Browsers:**
- Chrome (last 1 version)
- Firefox (last 1 version)
- Safari (last 1 version)
- Edge (modern versions)

**Polyfills:**
- Included via react-scripts
- No additional polyfills needed for modern browsers

### 9. State Management Philosophy

**No Redux:**
- Using React Context API only
- Simpler state management
- No external dependencies
- Easier to understand and maintain

**When to Use Context:**
- Global state (auth, session, notifications)
- Cross-component communication
- Avoid prop drilling

**When to Use Local State:**
- Component-specific UI state
- Form inputs
- Toggle states

### 10. Code Style

**Conventions:**
- Functional components only
- Hooks for state and effects
- Named exports for utilities
- Default exports for components
- PascalCase for components
- camelCase for functions/variables

---

## Quick Reference

### Essential Commands

```bash
# Development
npm install              # Install dependencies
npm start                # Start dev server
npm run lint             # Check code quality

# Testing
npm run test:unit        # Unit tests
npm run test:integration # Integration tests
npm run test:all         # All tests

# Build
npm run build            # Production build
```

### Key Files

**Configuration:**
- `package.json`: Dependencies and scripts
- `.env.development`: Development config
- `.env.production`: Production config
- `setupTests.js`: Test configuration

**Core Application:**
- `App.jsx`: Root component and routing
- `services/api.js`: API client (605 lines)
- `context/*.jsx`: State management

**Key Components:**
- `components/ChatPage.jsx`: Main chat
- `components/TopicsDashboard.jsx`: Topics management
- `components/UserProfile.jsx`: Personalization
- `components/Navigation.jsx`: Navigation bar

### Common Patterns

**Using Context:**
```javascript
import { useAuth } from '../context/AuthContext';
const { user, isAuthenticated } = useAuth();
```

**API Calls:**
```javascript
import { sendChatMessage } from '../services/api';
const response = await sendChatMessage(messages);
```

**Navigation:**
```javascript
import { useNavigate } from 'react-router-dom';
const navigate = useNavigate();
navigate('/topics');
```

**Protected Routes:**
```javascript
<ProtectedRoute>
  <Component />
</ProtectedRoute>
```

---

## Support & Resources

### Documentation

- **Component Tests**: See `*.test.js` files for usage examples
- **API Documentation**: Backend `/docs` endpoint
- **React Docs**: https://react.dev
- **React Router**: https://reactrouter.com
- **Testing Library**: https://testing-library.com/react

### Getting Help

1. **Check Tests**: Test files show expected behavior
2. **Browser Console**: Check for errors
3. **React DevTools**: Inspect component state
4. **Network Tab**: Verify API calls
5. **Backend Logs**: Check backend for API errors

---

## Success Metrics

✅ **All Tests Passing**: 246 unit + 2 integration tests  
✅ **Build Successful**: Production build works  
✅ **Zero Class Components**: 100% functional components  
✅ **Comprehensive Coverage**: 23 test suites  
✅ **Clean Code**: ESLint passing  
✅ **Documentation**: This handover document  

---

**Good luck with the frontend! 🚀**

For backend information, see the main project `HANDOVER.md` or `AGENTS.md`.


