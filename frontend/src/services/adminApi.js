import axios from 'axios';

const RAW_API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const NORMALIZED_API_URL = RAW_API_URL.replace(/\/+$/, '');
const API_BASE_URL = `${NORMALIZED_API_URL}/v2/admin`;

// Create axios instance for admin requests
const adminApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add the normal user auth token
adminApi.interceptors.request.use(
  (config) => {
    const authToken = localStorage.getItem('auth_token');
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token expiration
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Not authorized for admin endpoints (or token expired).
      // We no longer have a separate /admin/login password flow.
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Prompt management APIs
export const getAllPrompts = async () => {
  try {
    const response = await adminApi.get('/prompts');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const deleteAllUsers = async () => {
  try {
    const response = await adminApi.delete('/users');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPrompt = async (promptName) => {
  try {
    const response = await adminApi.get(`/prompts/${promptName}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const updatePrompt = async (promptName, content) => {
  try {
    const response = await adminApi.put(`/prompts/${promptName}`, { content });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPromptHistory = async (promptName) => {
  try {
    const response = await adminApi.get(`/prompts/${promptName}/history`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const restorePrompt = async (promptName, backupFilename) => {
  try {
    const response = await adminApi.post(`/prompts/${promptName}/restore`, {
      backup_filename: backupFilename
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const testPrompt = async (promptName, variables) => {
  try {
    const response = await adminApi.post(`/prompts/${promptName}/test`, {
      variables
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getAdminStatus = async () => {
  try {
    const response = await adminApi.get('/status');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Flow visualization APIs
export const getFlowSummary = async () => {
  try {
    const response = await adminApi.get('/flows');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getFlowData = async (graphType) => {
  try {
    const response = await adminApi.get(`/flows/${graphType}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getNodeInfo = async (nodeId) => {
  try {
    const response = await adminApi.get(`/flows/nodes/${nodeId}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const generateFlowDiagrams = async (forceRegenerate = false) => {
  try {
    const response = await adminApi.post('/flows/diagrams/generate', null, {
      params: { force_regenerate: forceRegenerate }
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPromptUsageMap = async () => {
  try {
    const response = await adminApi.get('/flows/prompt-usage');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Debug APIs (moved from api.js - these are now in /v2/admin/debug/*)
export const getMotivationStatus = async () => {
  try {
    const response = await adminApi.get('/debug/status');
    return response.data;
  } catch (error) {
    console.error('Error fetching motivation status:', error);
    throw error;
  }
};

export const adjustMotivationDrives = async (drives) => {
  try {
    const response = await adminApi.post('/debug/adjust-drives', drives);
    return response.data;
  } catch (error) {
    console.error('Error adjusting motivation drives:', error);
    throw error;
  }
};

export const updateMotivationConfig = async (config) => {
  try {
    const response = await adminApi.post('/debug/update-config', config);
    return response.data;
  } catch (error) {
    console.error('Error updating motivation config:', error);
    throw error;
  }
};


export const simulateResearchCompletion = async (qualityScore = 0.7) => {
  try {
    const response = await adminApi.post('/debug/simulate-research-completion', null, {
      params: { quality_score: qualityScore }
    });
    return response.data;
  } catch (error) {
    console.error('Error simulating research completion:', error);
    throw error;
  }
};

// Research engine control functions (moved from api.js - these are now in /v2/admin/debug/control/*)
export const startResearchEngine = async () => {
  try {
    const response = await adminApi.post('/debug/control/start');
    return response.data;
  } catch (error) {
    console.error('Error starting research engine:', error);
    throw error;
  }
};

export const stopResearchEngine = async () => {
  try {
    const response = await adminApi.post('/debug/control/stop');
    return response.data;
  } catch (error) {
    console.error('Error stopping research engine:', error);
    throw error;
  }
};

export const restartResearchEngine = async () => {
  try {
    const response = await adminApi.post('/debug/control/restart');
    return response.data;
  } catch (error) {
    console.error('Error restarting research engine:', error);
    throw error;
  }
};

export const triggerManualResearch = async (userId) => {
  try {
    const response = await adminApi.post(`/debug/trigger/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Error triggering manual research:', error);
    throw error;
  }
};

export const getResearchEngineStatus = async () => {
  try {
    const response = await adminApi.get('/debug/status');
    return response.data;
  } catch (error) {
    console.error('Error fetching research engine status:', error);
    throw error;
  }
};
