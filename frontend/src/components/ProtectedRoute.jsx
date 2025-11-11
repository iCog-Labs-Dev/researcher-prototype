import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useSession } from '../context/SessionContext';
import AuthModal from './AuthModal';

const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();
    const { updateUserId, updateUserDisplayName } = useSession();

    // Show loading state while checking authentication
    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                flexDirection: 'column',
                gap: '20px',
                background: 'radial-gradient(1200px circle at 20% 10%, rgba(99, 102, 241, 0.15), transparent 40%), radial-gradient(900px circle at 80% 20%, rgba(16, 185, 129, 0.12), transparent 40%), linear-gradient(180deg, rgba(17, 24, 39, 0.9), rgba(17, 24, 39, 0.95))'
            }}>
                <div className="loading-spinner" style={{
                    width: '40px',
                    height: '40px',
                    border: '4px solid rgba(255, 255, 255, 0.1)',
                    borderTopColor: '#6366f1',
                    borderRadius: '50%',
                    animation: 'spin 0.6s linear infinite'
                }}></div>
                <p style={{ color: '#e5e7eb' }}>Checking authentication...</p>
            </div>
        );
    }

    // If not authenticated, show auth modal and don't render children
    if (!isAuthenticated) {
        return (
            <AuthModal
                isOpen={true}
                onRequestClose={() => {}}
                onAuthenticated={(userId, displayName) => {
                    if (userId) {
                        updateUserId(userId);
                        if (displayName) updateUserDisplayName(displayName);
                    }
                }}
                preventClose={true}
            />
        );
    }

    // If authenticated, render the protected content
    return children;
};

export default ProtectedRoute;

