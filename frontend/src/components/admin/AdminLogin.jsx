import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AuthModal from '../AuthModal';
import '../../styles/Admin.css';

const AdminLogin = () => {
  const { isAuthenticated, user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading) return;

    const role = user?.role ?? user?.metadata?.role;

    if (!isAuthenticated) {
      // We no longer support a separate admin password. Push to /admin which will show login if needed.
      navigate('/admin');
      return;
    }

    if (role === 'admin') {
      navigate('/admin');
    } else {
      navigate('/');
    }
  }, [isAuthenticated, loading, navigate, user]);

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Redirecting...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // If someone opens /admin/login directly, show the normal login modal.
    return <AuthModal isOpen={true} onRequestClose={() => {}} preventClose={true} />;
  }

  return null;
};

export default AdminLogin; 