import React, { useState, useEffect, useRef, useCallback } from 'react';
import Modal from 'react-modal';
import { useAuth } from '../context/AuthContext';
import { loginUser, registerUser, getCurrentUser, loginWithGoogle } from '../services/api';
import '../styles/AuthModal.css';

Modal.setAppElement('#root');

const AuthModal = ({ isOpen, onRequestClose, onAuthenticated, preventClose = false }) => {
    const { login, setError } = useAuth();
    const [isLoginMode, setIsLoginMode] = useState(true);
    const [loading, setLoading] = useState(false);
    const [localError, setLocalError] = useState('');
    const googleButtonRef = useRef(null);

    // Login form state
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    // Register form state
    const [registerEmail, setRegisterEmail] = useState('');
    const [registerPassword, setRegisterPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [displayName, setDisplayName] = useState('');

    // Handle Google Sign-In callback
    const handleGoogleSignIn = useCallback(async (response) => {
        try {
            setLoading(true);
            setLocalError('');
            setError('');
            // Send id_token to backend
            const authResponse = await loginWithGoogle(response.credential);

            if (authResponse.access_token) {
                // Save the token
                login(authResponse.access_token, { email: '' });

                // Fetch user data
                try {
                    const userData = await getCurrentUser();
                    if (userData) {
                        login(authResponse.access_token, userData);

                        if (onAuthenticated) {
                            onAuthenticated(userData.id, userData.metadata?.display_name || userData.display_name || userData.email);
                        }
                    }
                } catch (userError) {
                    console.log('Could not fetch user data, using basic info:', userError);
                }

                onRequestClose();
            } else {
                setLocalError('Invalid response from server');
            }
        } catch (error) {
            console.error('Google login error:', error);
            const errorMessage = error.response?.data?.message || error.message || 'Google login failed. Please try again.';
            setLocalError(errorMessage);
        } finally {
            setLoading(false);
        }
    }, [login, onAuthenticated, onRequestClose, setError]);

    // Initialize Google Sign-In
    useEffect(() => {
        if (!isOpen || !isLoginMode) {
            return;
        }

        const initGoogleSignIn = () => {
            if (!googleButtonRef.current) {
                return false;
            }

            if (window.google && window.google.accounts) {
                const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
                if (!clientId) {
                    console.warn('REACT_APP_GOOGLE_CLIENT_ID is not set. Google Sign-In will not work.');
                    return false;
                }

                window.google.accounts.id.initialize({
                    client_id: clientId,
                    callback: handleGoogleSignIn,
                });

                // Clear previous button if exists
                googleButtonRef.current.innerHTML = '';

                // Render button
                window.google.accounts.id.renderButton(
                    googleButtonRef.current,
                    {
                        theme: 'outline',
                        size: 'large',
                        width: '100%',
                        text: 'signin_with',
                    }
                );
                return true;
            }
            return false;
        };

        // Check if Google script is loaded and ref is available
        let checkInterval = null;
        let timeoutId = null;

        const tryInit = () => {
            if (initGoogleSignIn()) {
                // Successfully initialized
                if (checkInterval) {
                    clearInterval(checkInterval);
                    checkInterval = null;
                }
                return;
            }

            // If not initialized, set up polling
            if (!checkInterval) {
                checkInterval = setInterval(() => {
                    if (initGoogleSignIn()) {
                        clearInterval(checkInterval);
                        checkInterval = null;
                    }
                }, 50);

                // Cleanup interval after 5 seconds to avoid infinite polling
                timeoutId = setTimeout(() => {
                    if (checkInterval) {
                        clearInterval(checkInterval);
                        checkInterval = null;
                    }
                }, 5000);
            }
        };

        // Use requestAnimationFrame to ensure DOM is ready
        const rafId = requestAnimationFrame(() => {
            // Use setTimeout to ensure React has committed the render
            setTimeout(tryInit, 0);
        });

        // Cleanup function
        return () => {
            cancelAnimationFrame(rafId);
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
            if (checkInterval) {
                clearInterval(checkInterval);
            }
        };
    }, [isOpen, isLoginMode, handleGoogleSignIn]);

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setLocalError('');
        setError('');

        try {
            const response = await loginUser(email, password);

            // Check for access_token (backend returns access_token, not token)
            if (response.access_token) {
                // Save the token first (login saves token to localStorage)
                login(response.access_token, { email });

                // Try to fetch user data, but don't fail if it doesn't work
                try {
                    const userData = await getCurrentUser();
                    if (userData) {
                        // Update with full user data if available
                        login(response.access_token, userData);

                        // Notify parent component about successful authentication
                        if (onAuthenticated) {
                            onAuthenticated(userData.id, userData.display_name || userData.email);
                        }
                    }
                } catch (userError) {
                    // Silently ignore user fetch errors - we already have basic user info
                    console.log('Could not fetch user data, using basic info:', userError);
                }

                onRequestClose();
            } else {
                setLocalError('Invalid response from server');
            }
        } catch (error) {
            console.error('Login error:', error);
            const errorMessage = error.response?.data?.message || error.message || 'Login failed. Please try again.';
            setLocalError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleRegister = async (e) => {
        e.preventDefault();

        // Validate passwords match
        if (registerPassword !== confirmPassword) {
            setLocalError('Passwords do not match');
            return;
        }

        // Validate password length
        if (registerPassword.length < 6) {
            setLocalError('Password must be at least 6 characters long');
            return;
        }

        setLoading(true);
        setLocalError('');
        setError('');

        try {
            const response = await registerUser(registerEmail, registerPassword, displayName || null);

            // Check for access_token (backend returns access_token, not token)
            if (response.access_token) {
                // Save the token first (login saves token to localStorage)
                login(response.access_token, { email: registerEmail, display_name: displayName });

                // Try to fetch user data, but don't fail if it doesn't work
                try {
                    const userData = await getCurrentUser();
                    if (userData) {
                        // Update with full user data if available
                        login(response.access_token, userData);

                        // Notify parent component about successful authentication
                        if (onAuthenticated) {
                            onAuthenticated(userData.id, userData.display_name || displayName || registerEmail);
                        }
                    }
                } catch (userError) {
                    // Silently ignore user fetch errors - we already have basic user info
                    console.log('Could not fetch user data, using basic info:', userError);
                }

                onRequestClose();
            } else {
                setLocalError('Invalid response from server');
            }
        } catch (error) {
            console.error('Registration error:', error);
            const errorMessage = error.response?.data?.message || error.message || 'Registration failed. Please try again.';
            setLocalError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleToggleMode = () => {
        setIsLoginMode(!isLoginMode);
        setLocalError('');
        setEmail('');
        setPassword('');
        setRegisterEmail('');
        setRegisterPassword('');
        setConfirmPassword('');
        setDisplayName('');
    };

    const handleClose = () => {
        if (preventClose) {
            return; // Prevent closing if required
        }
        setLocalError('');
        setEmail('');
        setPassword('');
        setRegisterEmail('');
        setRegisterPassword('');
        setConfirmPassword('');
        setDisplayName('');
        onRequestClose();
    };

    return (
        <Modal
            isOpen={isOpen}
            onRequestClose={handleClose}
            className="auth-modal"
            overlayClassName="auth-modal-overlay"
            closeTimeoutMS={200}
        >
            <div className="auth-modal-header">
                <h2>{isLoginMode ? '🔐 Login' : '✏️ Register'}</h2>
                {!preventClose && (
                    <button className="auth-modal-close" onClick={handleClose} aria-label="Close">
                        ×
                    </button>
                )}
            </div>

            <div className="auth-modal-body">
                {isLoginMode ? (
                    <form onSubmit={handleLogin} className="auth-form">
                        <div className="form-group">
                            <label htmlFor="email">Email</label>
                            <input
                                type="email"
                                id="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Enter your email"
                                required
                                disabled={loading}
                                autoFocus
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input
                                type="password"
                                id="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                required
                                disabled={loading}
                            />
                        </div>

                        {localError && (
                            <div className="error-message">
                                <span className="error-icon">⚠️</span>
                                {localError}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="auth-button"
                            disabled={loading || !email || !password}
                        >
                            {loading ? (
                                <>
                                    <span className="loading-spinner"></span>
                                    Logging in...
                                </>
                            ) : (
                                'Login'
                            )}
                        </button>

                        <div className="auth-divider">
                            <span>or</span>
                        </div>

                        <div ref={googleButtonRef} className="google-signin-button"></div>
                    </form>
                ) : (
                    <form onSubmit={handleRegister} className="auth-form">
                        <div className="form-group">
                            <label htmlFor="registerEmail">Email</label>
                            <input
                                type="email"
                                id="registerEmail"
                                value={registerEmail}
                                onChange={(e) => setRegisterEmail(e.target.value)}
                                placeholder="Enter your email"
                                required
                                disabled={loading}
                                autoFocus
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="registerPassword">Password</label>
                            <input
                                type="password"
                                id="registerPassword"
                                value={registerPassword}
                                onChange={(e) => setRegisterPassword(e.target.value)}
                                placeholder="Enter your password (min 6 characters)"
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="confirmPassword">Confirm Password</label>
                            <input
                                type="password"
                                id="confirmPassword"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm your password"
                                required
                                disabled={loading}
                            />
                        </div>

                        {localError && (
                            <div className="error-message">
                                <span className="error-icon">⚠️</span>
                                {localError}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="auth-button"
                            disabled={loading || !registerEmail || !registerPassword || !confirmPassword}
                        >
                            {loading ? (
                                <>
                                    <span className="loading-spinner"></span>
                                    Registering...
                                </>
                            ) : (
                                'Register'
                            )}
                        </button>
                    </form>
                )}
            </div>

            <div className="auth-modal-footer">
                <p>
                    {isLoginMode ? "Don't have an account? " : 'Already have an account? '}
                    <button
                        type="button"
                        className="switch-mode-button"
                        onClick={handleToggleMode}
                        disabled={loading}
                    >
                        {isLoginMode ? 'Register' : 'Login'}
                    </button>
                </p>
            </div>
        </Modal>
    );
};

export default AuthModal;

