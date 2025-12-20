import React, { useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getCurrentUser } from '../../services/api';
import AuthModal from '../AuthModal';

const ProtectedAdminRoute = ({ children }) => {
  const { isAuthenticated, user, loading, updateUser, logout } = useAuth();
  const navigate = useNavigate();
  const hasAttemptedUserRefreshRef = useRef(false);
  const hasShownNoAccessToastRef = useRef(false);

  const isAdmin = useMemo(() => {
    const role = user?.role ?? user?.metadata?.role;
    return role === 'admin';
  }, [user]);

  // If we're authenticated but don't have a role yet, refresh user data once.
  useEffect(() => {
    const hasRole = typeof (user?.role ?? user?.metadata?.role) !== 'undefined';
    if (loading || !isAuthenticated || hasRole || hasAttemptedUserRefreshRef.current) return;

    hasAttemptedUserRefreshRef.current = true;
    getCurrentUser()
      .then((freshUser) => {
        if (freshUser) updateUser(freshUser);
      })
      .catch((err) => {
        // If the token is invalid, force logout so the login modal appears.
        if (err?.response?.status === 401) {
          logout();
        }
      });
  }, [loading, isAuthenticated, user, updateUser, logout]);

  useEffect(() => {
    if (!loading && isAuthenticated && !isAdmin) {
      if (!hasShownNoAccessToastRef.current) {
        hasShownNoAccessToastRef.current = true;
        window.dispatchEvent(
          new CustomEvent('showToast', {
            detail: {
              id: `access_denied_${Date.now()}`,
              type: 'access_denied',
              title: 'Access denied',
              message: "You don't have access to the admin dashboard.",
              timestamp: new Date(),
              read: true,
            },
          })
        );
      }
      navigate('/');
    }
  }, [isAuthenticated, isAdmin, loading, navigate]);

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Checking access...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthModal isOpen={true} onRequestClose={() => {}} preventClose={true} />;
  }

  if (!isAdmin) {
    return null; // Will redirect via useEffect
  }

  return children;
};

export default ProtectedAdminRoute; 