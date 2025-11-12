import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { setAuthTokenHeader } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [token, setToken] = useState(localStorage.getItem('auth_token') || '');
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Initialize auth state from localStorage
    useEffect(() => {
        const storedToken = localStorage.getItem('auth_token');
        const storedUser = localStorage.getItem('auth_user');

        if (storedToken) {
            setToken(storedToken);
            setIsAuthenticated(true);
            setAuthTokenHeader(storedToken);

            if (storedUser) {
                try {
                    setUser(JSON.parse(storedUser));
                } catch (e) {
                    console.error('Failed to parse stored user:', e);
                }
            }
        } else {
            setAuthTokenHeader(null);
        }

        setLoading(false);
    }, []);

    const login = useCallback((authToken, userData) => {
        setToken(authToken);
        setUser(userData);
        setIsAuthenticated(true);
        localStorage.setItem('auth_token', authToken);
        localStorage.setItem('auth_user', JSON.stringify(userData));
        setAuthTokenHeader(authToken);
        setError('');
    }, []);

    const logout = useCallback(() => {
        setToken('');
        setUser(null);
        setIsAuthenticated(false);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        setAuthTokenHeader(null);
        setError('');
    }, []);

    const setErrorCallback = useCallback((errorMessage) => {
        setError(errorMessage);
    }, []);

    const value = useMemo(() => ({
        isAuthenticated,
        token,
        user,
        loading,
        error,
        setError: setErrorCallback,
        login,
        logout,
    }), [isAuthenticated, token, user, loading, error, setErrorCallback, login, logout]);

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

