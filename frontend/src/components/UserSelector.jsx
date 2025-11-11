import React, { useState, useEffect, useCallback } from 'react';
import { getCurrentUser, updateUserDisplayName } from '../services/api';
import '../styles/UserSelector.css';

const UserSelector = ({ onUserSelected }) => {
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [editingUserId, setEditingUserId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Wrap the user selection handler in useCallback to prevent recreating it on each render
  const handleUserSelect = useCallback((userId) => {
    setSelectedUserId(userId);
    localStorage.setItem('user_id', userId);
    onUserSelected(userId);
  }, [onUserSelected]);

  // Load current user only once when component mounts
  useEffect(() => {
    let isMounted = true;
    
    const loadCurrentUser = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const userData = await getCurrentUser();
        
        // Only update state if component is still mounted
        if (isMounted) {
          if (userData && userData.user_id) {
            setUsers([userData]);
            setSelectedUserId(userData.user_id);
            handleUserSelect(userData.user_id);
          }
        }
      } catch (error) {
        console.error('Error loading current user:', error);
        if (isMounted) {
          setError('Failed to load user. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    
    loadCurrentUser();
    
    // Cleanup function to prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, [handleUserSelect]); // Include handleUserSelect in dependency array

  // Note: User creation is now handled through registration in AuthModal
  const handleCreateUser = async () => {
    alert('Please use the Login/Register button to create a new account.');
    setIsCreatingUser(false);
  };

  const handleEditName = async (userId) => {
    if (!editingName.trim()) {
      alert('Please enter a name');
      return;
    }

    try {
      setIsLoading(true);
      await updateUserDisplayName(editingName.trim());
      
      // Update local users list using functional update to avoid stale state
      setUsers(prevUsers => prevUsers.map(user => 
        user.user_id === userId 
          ? { ...user, display_name: editingName.trim() } 
          : user
      ));
      
      setEditingUserId(null);
      setEditingName('');
    } catch (error) {
      console.error('Error updating user name:', error);
      alert('Failed to update user name');
    } finally {
      setIsLoading(false);
    }
  };

  const startEditingName = (userId, currentName) => {
    setEditingUserId(userId);
    setEditingName(currentName);
  };

  if (isLoading && users.length === 0) {
    return <div className="user-selector-loading">Loading users...</div>;
  }

  if (error) {
    return <div className="user-selector-error">{error}</div>;
  }

  return (
    <div className="user-selector">
      <div className="user-selector-header">
        <h3>Current User</h3>
      </div>
      
      <div className="user-list">
        {users.length === 0 ? (
          <div className="no-users">No users found. Create a new user to get started.</div>
        ) : (
          users.map(user => (
            <div 
              key={user.user_id} 
              className={`user-item ${selectedUserId === user.user_id ? 'selected' : ''}`}
              onClick={() => !isLoading && handleUserSelect(user.user_id)}
            >
              <div className="user-info">
                {editingUserId === user.user_id ? (
                  <div className="edit-name-form">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      disabled={isLoading}
                    />
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditName(user.user_id);
                      }}
                      disabled={isLoading}
                    >
                      Save
                    </button>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingUserId(null);
                      }}
                      disabled={isLoading}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="user-name">
                    <span>{user.display_name}</span>
                    <button 
                      className="edit-name-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        startEditingName(user.user_id, user.display_name);
                      }}
                      disabled={isLoading}
                    >
                      ✏️
                    </button>
                  </div>
                )}
                <div className="user-details">
                  <span>Style: {user.personality?.style || 'helpful'}</span>
                  <span>Tone: {user.personality?.tone || 'friendly'}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default UserSelector; 
