import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30 seconds timeout
const MAX_RETRIES = 2; // Maximum retry attempts
const RETRY_DELAY = 1000; // Retry delay (milliseconds)

// Idempotent method list (safe to retry)
const IDEMPOTENT_METHODS = ['get', 'head', 'options', 'put', 'delete'];

// Determine if error should be retried
const shouldRetry = (error, method) => {
  // Cases not to retry
  if (!error) return false;
  
  // Don't retry if user cancelled the request (AbortError, CanceledError)
  if (error.name === 'AbortError' || error.name === 'CanceledError' || 
      error.code === 'ERR_CANCELED' || error.code === 'ECONNABORTED' && error.message?.includes('cancel')) {
    return false;
  }
  
  // Non-idempotent methods don't retry (avoid duplicate operations)
  if (method && !IDEMPOTENT_METHODS.includes(method.toLowerCase())) {
    return false;
  }
  
  // 4xx errors don't retry (client errors)
  if (error.response?.status >= 400 && error.response?.status < 500) {
    return false;
  }
  
  // Timeout, network errors, 5xx server errors can retry
  return (
    error.code === 'ECONNABORTED' ||
    error.code === 'ERR_NETWORK' ||
    error.code === 'ECONNRESET' ||
    error.message?.includes('timeout') ||
    error.message?.includes('Network Error') ||
    (error.response?.status >= 500)
  );
};

// Delay function
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Request wrapper with retry
const withRetry = async (requestFn, method = 'get', retries = MAX_RETRIES) => {
  try {
    return await requestFn();
  } catch (error) {
    // If shouldn't retry or retries exhausted
    if (!shouldRetry(error, method) || retries <= 0) {
      throw error;
    }

    // Wait then retry
    await delay(RETRY_DELAY);
    return withRetry(requestFn, method, retries - 1);
  }
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Can add auth token here
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Helper function: Extract readable error message from detail
const extractErrorMessage = (detail) => {
  if (!detail) return null;
  
  // String returned directly
  if (typeof detail === 'string') return detail;
  
  // Pydantic validation error array format: [{type, loc, msg, ...}, ...]
  if (Array.isArray(detail)) {
    const messages = detail.map(err => {
      // Extract field name and error message
      const field = err.loc?.join('.') || '';
      const msg = err.msg || err.message || JSON.stringify(err);
      return field ? `${field}: ${msg}` : msg;
    });
    return messages.join('; ');
  }
  
  // Object format
  if (typeof detail === 'object') {
    // Try to extract common fields
    if (detail.message) return detail.message;
    if (detail.msg) return detail.msg;
    if (detail.error) return detail.error;
    // Convert to JSON string
    try {
      return JSON.stringify(detail);
    } catch {
      return 'Unknown error';
    }
  }
  
  return String(detail);
};

// Response interceptor - unified error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let errorMessage = 'Request failed';
    
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      errorMessage = 'Request timeout, please check network connection or try again later';
    } else if (error.response) {
      // Server returned error
      const status = error.response.status;
      const detail = error.response.data?.detail;
      const extractedMsg = extractErrorMessage(detail);
      
      switch (status) {
        case 400:
          errorMessage = extractedMsg || 'Invalid request parameters';
          break;
        case 401:
          errorMessage = 'Unauthorized, please login first';
          break;
        case 403:
          errorMessage = 'Access denied';
          break;
        case 404:
          errorMessage = extractedMsg || 'Requested resource not found';
          break;
        case 422:
          // Pydantic validation error
          errorMessage = extractedMsg || 'Request parameter validation failed';
          break;
        case 500:
          errorMessage = extractedMsg || 'Internal server error';
          break;
        default:
          errorMessage = extractedMsg || `Request failed (${status})`;
      }
    } else if (error.request) {
      // Request was made but no response received
      errorMessage = 'Cannot connect to server, please check if server is running';
    }
    
    // Create error object with friendly message
    const friendlyError = new Error(errorMessage);
    friendlyError.originalError = error;
    friendlyError.status = error.response?.status;
    
    return Promise.reject(friendlyError);
  }
);

/**
 * Analyze Python code
 * @param {string} code - Python code
 * @param {Object} options - Analysis options
 * @param {AbortSignal} signal - Optional cancel signal
 */
export const analyzeCode = async (code, options = {}, signal = null) => {
  // POST requests don't retry, avoid duplicate analysis
  const response = await api.post('/api/analyze', {
    code,
    options,
  }, {
    signal,
  });
  return response.data;
};

/**
 * Get AST graph structure
 */
export const getAST = async (code, format = 'cytoscape', theme = 'default') => {
  // POST requests don't retry
  const response = await api.post('/api/ast', {
    code,
    options: { format, theme },
  });
  return response.data;
};

/**
 * Get complexity analysis
 */
export const getComplexity = async (code) => {
  // POST requests don't retry
  const response = await api.post('/api/complexity', { code });
  return response.data;
};

/**
 * Get performance issues
 */
export const getPerformanceIssues = async (code) => {
  // POST requests don't retry
  const response = await api.post('/api/performance', { code });
  return response.data;
};

/**
 * Get security issues
 */
export const getSecurityIssues = async (code) => {
  // POST requests don't retry
  const response = await api.post('/api/security', { code });
  return response.data;
};

/**
 * Get optimization suggestions
 */
export const getSuggestions = async (code) => {
  // POST requests don't retry
  const response = await api.post('/api/suggestions', { code });
  return response.data;
};

/**
 * Generate patches
 */
export const generatePatches = async (code) => {
  // POST requests don't retry
  const response = await api.post('/api/patches', { code });
  return response.data;
};

/**
 * Get node explanation (learning mode)
 */
export const explainNode = async (nodeId, code) => {
  // POST requests don't retry
  const response = await api.post(`/api/learn/node/${nodeId}`, { code });
  return response.data;
};

/**
 * Get challenge list
 */
export const getChallenges = async () => {
  // GET requests can safely retry
  return withRetry(async () => {
    const response = await api.get('/api/challenges');
    return response.data;
  }, 'get');
};

/**
 * Get challenge categories
 */
export const getChallengeCategories = async () => {
  // GET requests can safely retry
  return withRetry(async () => {
    const response = await api.get('/api/challenges/categories');
    return response.data;
  }, 'get');
};

/**
 * Get challenge details
 */
export const getChallenge = async (challengeId) => {
  // GET requests can safely retry
  return withRetry(async () => {
    const response = await api.get(`/api/challenges/${challengeId}`);
    return response.data;
  }, 'get');
};

/**
 * Submit challenge answer
 */
export const submitChallenge = async (challengeId, foundIssues) => {
  // POST requests don't retry, avoid duplicate submissions
  const response = await api.post('/api/challenges/submit', {
    challenge_id: challengeId,
    found_issues: foundIssues,
  });
  return response.data;
};

/**
 * Check server connection status
 */
export const checkServerHealth = async () => {
  try {
    // GET requests can safely retry
    return withRetry(async () => {
      const response = await api.get('/api/health', { timeout: 5000 });
      return { connected: true, data: response.data };
    }, 'get');
  } catch (error) {
    return { 
      connected: false, 
      error: error.message,
      hint: 'Please ensure the backend server is running (python run.py backend)'
    };
  }
};

/**
 * Get API base URL
 */
export const getApiBaseUrl = () => API_BASE_URL;

/**
 * Upload project ZIP file (scan project structure)
 * @param {File} file - ZIP file object
 * @param {AbortSignal} signal - Optional cancel signal
 * @returns {Promise<Object>} Scan result
 */
export const uploadProject = async (file, signal = null) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/api/project/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    signal,
    timeout: 60000, // Upload may take longer
  });
  
  return response.data;
};

/**
 * Analyze project (upload and analyze in one step)
 * @param {File} file - ZIP file object
 * @param {boolean} quickMode - Whether to use quick mode
 * @param {AbortSignal} signal - Optional cancel signal
 * @returns {Promise<Object>} Project analysis result
 */
export const analyzeProject = async (file, quickMode = false, signal = null) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('quick_mode', quickMode.toString());
  
  const response = await api.post('/api/project/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    signal,
    timeout: 300000, // Project analysis may take a long time (5 minutes)
  });
  
  return response.data;
};

export default api;