import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { useAuth } from '../context/AuthContext';
// Removed unused useNotifications import
import UserProfile from './UserProfile';
import KnowledgeGraphViewer from './graph/KnowledgeGraphViewer';
import NotificationBadge from './NotificationBadge';
import NotificationPanel from './NotificationPanel';
import AuthModal from './AuthModal';
import { getCurrentUser } from '../services/api';
import { generateDisplayName } from '../utils/userUtils';
import '../styles/Navigation.css';

const Navigation = () => {
  const location = useLocation();
  const dropdownRef = useRef(null);
  const {
    userDisplayName,
    userId,
    updateUserDisplayName,
    updatePersonality,
    updateMessages,
    resetSession
  } = useSession();
  const { isAuthenticated, user: authUser, logout } = useAuth();

  // Chat-specific state (only used on chat page)
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [showKnowledgeGraph, setShowKnowledgeGraph] = useState(false);
  const [isDashboardsOpen, setIsDashboardsOpen] = useState(false);

  const isOnChatPage = location.pathname === '/';
  const appMode = process.env.REACT_APP_MODE || 'dev';
  const isTestMode = appMode === 'test';

  const handleLogout = () => {
    logout();
    resetSession();
  };

  // Sync display name and personality from AuthContext user data
  // Use id instead of whole user object to prevent rerender loops
  const authUserId = authUser?.id || '';
  const prevPersonalityRef = useRef(null);

  useEffect(() => {
    if (!isAuthenticated || !authUser) {
      return;
    }

    const displayName = authUser.metadata?.display_name || authUser.display_name || authUser.email;
    if (displayName && displayName !== userDisplayName) {
      updateUserDisplayName(displayName);
    }

    // Only update personality if it actually changed
    const currentPersonalityStr = JSON.stringify(authUser.personality);
    const prevPersonalityStr = JSON.stringify(prevPersonalityRef.current);
    if (authUser.personality && currentPersonalityStr !== prevPersonalityStr) {
      updatePersonality(authUser.personality);
      prevPersonalityRef.current = authUser.personality;
    }
  }, [isAuthenticated, authUserId, authUser?.metadata?.display_name, authUser?.display_name, authUser?.email, authUser?.personality, userDisplayName, updateUserDisplayName, updatePersonality]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDashboardsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Load fresh user data when authenticated and on chat page
  useEffect(() => {
    if (!isOnChatPage || !isAuthenticated || !authUserId) return;

    const loadUserData = async () => {
      try {
        const userData = await getCurrentUser();

        updatePersonality(userData?.personality || {
          style: 'helpful',
          tone: 'friendly',
        });

        const displayName =
          userData?.metadata?.display_name ||
          userData?.display_name ||
          userData?.email ||
          generateDisplayName(userData?.id || authUserId);

        if (displayName) {
          updateUserDisplayName(displayName);
        }
      } catch (error) {
        console.error('Error loading user data:', error);

        if (error.response && (error.response.status === 401 || error.response.status === 403)) {
          logout();
          resetSession();
        }
      }
    };

    loadUserData();
  }, [isOnChatPage, isAuthenticated, authUserId, updatePersonality, updateUserDisplayName, logout, resetSession]);

  const handleToggleUserProfile = useCallback(() => {
    setShowUserProfile(prevState => {
      const newState = !prevState;
      return newState;
    });
  }, []);

  const handleProfileUpdated = useCallback((updatedPersonality) => {
    console.log('Profile updated with new personality:', updatedPersonality);

    // Update personality in state
    updatePersonality(updatedPersonality);

    // Update the system message immediately
    const systemMessage = {
      role: 'system',
      content: `You are a ${updatedPersonality.style || 'helpful'} assistant. Please respond in a ${updatedPersonality.tone || 'friendly'} tone.`
    };

    // Update the first message if it's a system message
    updateMessages(prevMessages => {
      if (prevMessages.length > 0 && prevMessages[0].role === 'system') {
        return [systemMessage, ...prevMessages.slice(1)];
      }
      return [systemMessage, ...prevMessages];
    });
  }, [updatePersonality, updateMessages]);



  return (
    <>
      <nav className="navigation">
        <div className="nav-container">
          <div className="nav-brand">
            <h2>AI Research Assistant</h2>
          </div>

          <div className="nav-center">
            <div className="nav-links">
              <Link
                to="/"
                className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
              >
                💬 Chat
              </Link>

              <div className="nav-dropdown" ref={dropdownRef}>
                <button
                  className={`nav-link dropdown-toggle ${isDashboardsOpen ? 'active' : ''}`}
                  onClick={() => setIsDashboardsOpen(prev => !prev)}
                >
                  <span>📊 Dashboards</span>
                </button>
                {isDashboardsOpen && (
                  <div className="dropdown-menu">
                    <Link to="/topics" className="dropdown-item" onClick={() => setIsDashboardsOpen(false)}>
                      🔍 Research Topics
                    </Link>
                    <Link to="/research-results" className="dropdown-item nav-item" onClick={() => setIsDashboardsOpen(false)}>
                      📊 Research Results
                      <NotificationBadge />
                    </Link>
                    <button
                      className="dropdown-item"
                      onClick={() => {
                        setShowKnowledgeGraph(true);
                        setIsDashboardsOpen(false);
                      }}
                      title="View Knowledge Graph"
                    >
                      🕸️ Knowledge Graph
                    </button>
                  </div>
                )}
              </div>

              <Link
                to="/admin"
                className={`nav-link admin-link ${location.pathname.startsWith('/admin') ? 'active' : ''}`}
                title="Admin Panel - Prompt Management"
              >
                🛠️ Admin
              </Link>
            </div>
          </div>

          <div className="nav-right">
            <NotificationPanel />

            {/* Authentication Button */}
            {isAuthenticated ? (
              <div className="auth-controls">
                <span className="auth-user-info">
                  {authUser?.metadata?.display_name || authUser?.display_name || authUser?.email || 'User'}
                </span>
                <button
                  className="logout-button"
                  onClick={handleLogout}
                  title="Logout"
                >
                  Logout
                </button>
              </div>
            ) : (
              !isOnChatPage && (
                <button
                  className="login-button"
                  onClick={() => {
                    // Show auth modal for non-chat pages
                    // For chat page, it's already shown automatically
                  }}
                >
                  Login
                </button>
              )
            )}

            {isOnChatPage && isAuthenticated && userId && (
              <div className="chat-controls">
                <button
                  className="profile-button"
                  onClick={handleToggleUserProfile}
                >
                  {showUserProfile ? 'Hide Settings' : 'User Settings'}
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {isOnChatPage && showUserProfile && userId && (
        <div className="profile-modal-overlay" onClick={handleToggleUserProfile}>
          <div className="profile-modal-content" onClick={(e) => e.stopPropagation()}>
            <UserProfile
              userId={userId}
              onProfileUpdated={handleProfileUpdated}
            />
          </div>
        </div>
      )}

      {showKnowledgeGraph && userId && (
        <div className="profile-modal-overlay" onClick={() => setShowKnowledgeGraph(false)}>
          <div className="profile-modal-content knowledge-graph-modal" onClick={(e) => e.stopPropagation()}>
            <KnowledgeGraphViewer
              userId={userId}
              userName={userDisplayName || 'User'}
              onClose={() => setShowKnowledgeGraph(false)}
            />
          </div>
        </div>
      )}

      {/* Auth modal is now handled by ProtectedRoute globally */}

    </>
  );
};

export default Navigation;
