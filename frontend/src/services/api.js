import axios from 'axios';

// Get API URL from environment variables with fallback for development
const RAW_API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const NORMALIZED_API_URL = RAW_API_URL.replace(/\/+$/, '');
const API_VERSION_PREFIX = '/v2';

export const API_URL = `${NORMALIZED_API_URL}${API_VERSION_PREFIX}`;

// Optional: Log the API URL in development for debugging
if (process.env.REACT_APP_DEBUG === 'true') {
  console.log('🔗 API URL:', API_URL);
}

// Create an axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to apply the Authorization header to the axios instance
export const setAuthTokenHeader = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Apply token from storage if available on initial load
if (typeof window !== 'undefined') {
  const existingToken = localStorage.getItem('auth_token');
  if (existingToken) {
    setAuthTokenHeader(existingToken);
  }
}

// Add interceptor to add auth token to headers if available
api.interceptors.request.use(
  (config) => {
    const authToken = localStorage.getItem('auth_token');
    if (authToken) {
      config.headers['Authorization'] = `Bearer ${authToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Get available models
export const getModels = async () => {
  try {
    const response = await api.get('/meta/models');
    return response.data;
  } catch (error) {
    console.error('Error fetching models:', error);
    throw error;
  }
};

// Get all chat sessions for the current user
export const getAllChatSessions = async () => {
  try {
    const response = await api.get('/chat');
    return response.data;
  } catch (error) {
    console.error('Error fetching chat sessions:', error);
    throw error;
  }
};

// Send a chat message
export const sendChatMessage = async (messages, temperature = 0.7, maxTokens = 1000, personality = null, sessionId = null) => {
  try {
    const payload = {
      messages,
      temperature,
      max_tokens: maxTokens,
    };

    // Include personality if available
    if (personality) {
      payload.personality = personality;
    }

    // Include session_id if available
    if (sessionId) {
      payload.session_id = sessionId;
    }

    const response = await api.post('/chat', payload);

    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

// User management functions

export const createUser = async (userData) => {
  try {
    const displayName = userData.display_name;
    const email = userData.email;
    const params = { };
    if (displayName) params.display_name = displayName;
    if (email) params.email = email;
    const response = await api.post('/users', null, {
      params
    });
    return response.data;
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
};

export const getCurrentUser = async () => {
  try {
    console.log('Fetching current user data...');

    const response = await api.get('/user');
    console.log('Current user response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching current user:', error);
    // Log detailed error information
    if (error.response) {
      console.error('Error response:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('No response received from server');
    }
    throw error;
  }
};

export const deleteUser = async () => {
  try {
    const response = await api.delete('/user');
    return response.data;
  } catch (error) {
    console.error('Error deleting user:', error);
    throw error;
  }
};

export const updateUserDisplayName = async (displayName) => {
  try {
    const response = await api.post('/user/display-name', { display_name: displayName });
    return response.data;
  } catch (error) {
    console.error('Error updating user display name:', error);
    throw error;
  }
};

export const updateUserEmail = async (email) => {
  try {
    const response = await api.post('/user/email', { email: email });
    return response.data;
  } catch (error) {
    console.error('Error updating user email:', error);
    throw error;
  }
};

export const updateUserPersonality = async (personality) => {
  try {
    const response = await api.post('/user/personality', personality);
    return response.data;
  } catch (error) {
    console.error('Error updating user personality:', error);
    throw error;
  }
};

export const getPersonalityPresets = async () => {
  try {
    const response = await api.get('/meta/personality-presets');
    return response.data;
  } catch (error) {
    console.error('Error fetching personality presets:', error);
    throw error;
  }
};

// Personalization API functions
export const getUserPreferences = async () => {
  try {
    const response = await api.get('/user/preferences');
    return response.data;
  } catch (error) {
    console.error('Error fetching user preferences:', error);
    throw error;
  }
};

export const updateUserPreferences = async (preferences) => {
  try {
    const response = await api.post('/user/preferences', preferences);
    return response.data;
  } catch (error) {
    console.error('Error updating user preferences:', error);
    throw error;
  }
};

export const getUserEngagementAnalytics = async () => {
  try {
    const response = await api.get('/user/engagement-analytics');
    return response.data;
  } catch (error) {
    console.error('Error fetching engagement analytics:', error);
    throw error;
  }
};

export const getUserPersonalizationHistory = async () => {
  try {
    const response = await api.get('/user/personalization-history');
    return response.data;
  } catch (error) {
    console.error('Error fetching personalization history:', error);
    throw error;
  }
};

export const getUserPersonalizationData = async () => {
  try {
    const response = await api.get('/user/personalization');
    return response.data;
  } catch (error) {
    console.error('Error fetching personalization data:', error);
    throw error;
  }
};

export const trackUserEngagement = async (interactionType, metadata) => {
  try {
    const response = await api.post('/user/engagement/track', {
      interaction_type: interactionType,
      metadata: metadata
    });
    return response.data;
  } catch (error) {
    console.error('Error tracking user engagement:', error);
    throw error;
  }
};

export const trackLinkClick = async (url, context = {}) => {
  try {
    const response = await api.post('/user/link-click', {
      url,
      context,
      timestamp: Date.now()
    });
    return response.data;
  } catch (error) {
    console.error('Error tracking link click:', error);
    throw error;
  }
};

export const overrideLearnedBehavior = async (preferenceType, overrideValue, disableLearning = false) => {
  try {
    const response = await api.post('/user/personalization/override', {
      preference_type: preferenceType,
      override_value: overrideValue,
      disable_learning: disableLearning
    });
    return response.data;
  } catch (error) {
    console.error('Error overriding learned behavior:', error);
    throw error;
  }
};

export const getPersonalizationContext = async () => {
  try {
    const response = await api.get('/user/personalization-context');
    return response.data;
  } catch (error) {
    console.error('Error fetching personalization context:', error);
    throw error;
  }
};

// Topic management functions
export const getAllTopicSuggestions = async () => {
  try {
    const response = await api.get('/topic/suggestions');
    return response.data;
  } catch (error) {
    console.error('Error fetching topic suggestions:', error);
    throw error;
  }
};

export const getSessionTopicSuggestions = async (sessionId) => {
  try {
    const response = await api.get(`/topic/suggestions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user topic suggestions:', error);
    throw error;
  }
};

export const getTopicStatistics = async () => {
  try {
    const response = await api.get('/topic/stats');
    return response.data;
  } catch (error) {
    console.error('Error fetching topic statistics:', error);
    throw error;
  }
};

export const deleteSessionTopics = async (sessionId) => {
  try {
    const response = await api.delete(`/topic/session/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting session topics:', error);
    throw error;
  }
};

export const cleanupTopics = async () => {
  try {
    const response = await api.delete('/topic/cleanup');
    return response.data;
  } catch (error) {
    console.error('Error cleaning up topics:', error);
    throw error;
  }
};

export const getTopicProcessingStatus = async (sessionId) => {
  try {
    const response = await api.get(`/topic/status/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error checking topic processing status:', error);
    throw error;
  }
};

// Conversation topics sidebar functions
export const getTopSessionTopics = async (sessionId, limit = 3) => {
  try {
    const response = await api.get(`/topic/session/${sessionId}/top`, {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching top session topics:', error);
    throw error;
  }
};

// NEW: ID-based topic deletion (SAFE - no index mismatch)
export const deleteTopicById = async (topicId) => {
  try {
    const response = await api.delete(`/topic/${topicId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting topic by ID:', error);
    throw error;
  }
};

// NEW: Delete all non-activated research topics
export const deleteNonActivatedTopics = async () => {
  try {
    const response = await api.delete('/topic/non-activated');
    return response.data;
  } catch (error) {
    console.error('Error deleting non-activated topics:', error);
    throw error;
  }
};

// NEW: Create custom research topic
export const createCustomTopic = async (topicData) => {
  try {
    const response = await api.post('/topic/custom', topicData);
    return {
      success: true,
      topic: response.data,
      error: null,
    };
  } catch (error) {
    console.error('Error creating custom topic:', error);
    return {
      success: false,
      topic: null,
      error: error.response?.data?.detail || 'Failed to create topic',
    };
  }
};

// NEW: ID-based topic research functions (SAFE - no index mismatch)
export const enableTopicResearchById = async (topicId) => {
  try {
    const response = await api.patch(`/topic/topic/${topicId}/research`, null, {
      params: { enable: true }
    });
    return response.data;
  } catch (error) {
    console.error('Error enabling topic research by ID:', error);
    throw error;
  }
};

export const disableTopicResearchById = async (topicId) => {
  try {
    const response = await api.patch(`/topic/topic/${topicId}/research`, null, {
      params: { enable: false }
    });
    return response.data;
  } catch (error) {
    console.error('Error disabling topic research by ID:', error);
    throw error;
  }
};

// Research findings functions
export const getResearchFindings = async (userId, topicName = null, unreadOnly = false) => {
  try {
    const params = {};
    if (topicName) params.topic_name = topicName;
    if (unreadOnly) params.unread_only = unreadOnly;

    const response = await api.get(`/research/findings`, { params });
    console.log('Research findings response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching research findings:', error);
    throw error;
  }
};

export const setFindingBookmarked = async (findingId, bookmarked) => {
  try {
    const response = await api.post(`/research/${findingId}/bookmark`, { bookmarked });
    return response.data;
  } catch (error) {
    console.error('Error updating finding bookmark:', error);
    throw error;
  }
};

export const markFindingAsRead = async (findingId) => {
  try {
    const response = await api.post(`/research/${findingId}/mark_read`);
    return response.data;
  } catch (error) {
    console.error('Error marking finding as read:', error);
    throw error;
  }
};

export const integrateResearchFinding = async (findingId) => {
  try {
    const response = await api.post(`/research/${findingId}/integrate`);
    return response.data;
  } catch (error) {
    console.error('Error integrating research finding:', error);
    throw error;
  }
};

// Delete research findings functions
export const deleteResearchFinding = async (findingId) => {
  try {
    const response = await api.delete(`/research/${findingId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting research finding:', error);
    throw error;
  }
};

export const deleteAllTopicFindings = async (topicName) => {
  try {
    const response = await api.delete(`/research/topic/${encodeURIComponent(topicName)}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting all topic findings:', error);
    throw error;
  }
};

export const getActiveResearchTopics = async () => {
  try {
    const response = await api.get(`/topic/user/research`);
    return response.data;
  } catch (error) {
    console.error('Error fetching active research topics:', error);
    throw error;
  }
};


// Graph API functions
export const graphApi = {
  /**
   * Fetch graph data for a user or group
   * @param {string} type - "user" or "group"
   * @param {string} id - The user or group ID
   * @returns {Promise} The graph data response
   */
  fetchGraphData: async (type, id) => {
    try {
      const response = await api.post('/graph/fetch', {
        type,
        id
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching graph data:', error);
      throw error;
    }
  },

  /**
   * Test graph connectivity for a user
   * @param {string} userId - The user ID
   * @returns {Promise} The test result
   */
  testGraphConnectivity: async (userId) => {
    try {
      // need attention: this endpoint doesn't exist
      const response = await api.get(`/graph/test/${userId}`);
      return response.data;
    } catch (error) {
      console.error('Error testing graph connectivity:', error);
      throw error;
    }
  }
};

// Authentication API functions
export const loginUser = async (email, password) => {
  try {
    const response = await api.post('/auth/login', {
      email,
      password
    });
    return response.data;
  } catch (error) {
    console.error('Error logging in:', error);
    throw error;
  }
};

export const registerUser = async (email, password, displayName = null) => {
  try {
    const response = await api.post('/auth/register', {
      email,
      password,
      display_name: displayName
    });
    return response.data;
  } catch (error) {
    console.error('Error registering user:', error);
    throw error;
  }
};

export const loginWithGoogle = async (idToken) => {
  try {
    const response = await api.post('/auth/google', {
      id_token: idToken
    });
    return response.data;
  } catch (error) {
    console.error('Error logging in with Google:', error);
    throw error;
  }
};

// Trigger user activity for motivation system
export const triggerUserActivity = async () => {
  try {
    const response = await api.post('/research/debug/trigger-user-activity');
    return response.data;
  } catch (error) {
    console.error('Error triggering user activity:', error);
    throw error;
  }
};

export default api;
