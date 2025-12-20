import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { SessionProvider } from './context/SessionContext';
import { NotificationProvider } from './context/NotificationContext';
import ChatPage from './components/ChatPage';
import TopicsDashboard from './components/TopicsDashboard';
import ResearchResultsDashboard from './components/ResearchResultsDashboard';
import AdminLogin from './components/admin/AdminLogin';
import AdminDashboard from './components/admin/AdminDashboard';
import ProtectedAdminRoute from './components/admin/ProtectedAdminRoute';
import ProtectedRoute from './components/ProtectedRoute';
import ToastNotifications from './components/ToastNotifications';
import Layout from './components/Layout';
import './utils/testDataIsolation'; // Import test utilities for debugging
import './App.css';

function App() {
  return (
    <AuthProvider>
      <SessionProvider>
        <NotificationProvider>
          <Router>
            <div className="app">
              <Routes>
                {/* Legacy route - kept for compatibility, but no longer uses an admin password */}
                <Route path="/admin/login" element={<AdminLogin />} />

                {/* Admin routes - protected by user role */}
                <Route
                  path="/admin"
                  element={
                    <ProtectedAdminRoute>
                      <AdminDashboard />
                    </ProtectedAdminRoute>
                  }
                />

                {/* Main app routes - protected with user authentication */}
                <Route
                  element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<ChatPage />} />
                  <Route path="topics" element={<TopicsDashboard />} />
                  <Route path="research-results" element={<ResearchResultsDashboard />} />
                </Route>
              </Routes>
              <ToastNotifications />
            </div>
          </Router>
        </NotificationProvider>
      </SessionProvider>
    </AuthProvider>
  );
}

export default App; 
