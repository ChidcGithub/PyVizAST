import axios from 'axios';
import logger from './utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 60000; // 60 seconds timeout (increased for large file analysis)
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
      error.code === 'ERR_CANCELED' || (error.code === 'ECONNABORTED' && error.message?.includes('cancel'))) {
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
    logger.debug('API Request', { method: config.method?.toUpperCase(), url: config.url });
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
  
  // Object format (new error format from backend)
  if (typeof detail === 'object') {
    // New format: {detail: string, error_type: string}
    if (detail.detail && typeof detail.detail === 'string') {
      return detail.detail;
    }
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
 * @param {string} taskId - Optional task ID for progress tracking
 * @returns {Promise<Object>} Project analysis result
 */
export const analyzeProject = async (file, quickMode = false, signal = null, taskId = null) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('quick_mode', quickMode.toString());
  if (taskId) {
    formData.append('task_id', taskId);
  }
  
  const response = await api.post('/api/project/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    signal,
    timeout: 300000, // Project analysis may take a long time (5 minutes)
  });
  
  return response.data;
};

/**
 * Get current progress for a task
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>} Progress state
 */
export const getProgress = async (taskId) => {
  const response = await api.get(`/api/progress/${taskId}`, { timeout: 5000 });
  return response.data;
};

/**
 * Create EventSource for SSE progress updates
 * @param {string} taskId - Task ID
 * @param {function} onProgress - Callback for progress updates
 * @param {function} onError - Callback for errors
 * @returns {Object} Object with eventSource and close method
 * @example
 * const { eventSource, close } = createProgressStream(taskId, onProgress, onError);
 * // When done, call close() to clean up
 * close();
 */
export const createProgressStream = (taskId, onProgress, onError) => {
  const eventSource = new EventSource(`${API_BASE_URL}/api/progress/${taskId}/stream`);
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onProgress(data);
      
      // Close connection when complete or error
      if (data.stage === 'complete' || data.stage === 'error') {
        eventSource.close();
      }
    } catch (e) {
      logger.error('Failed to parse progress data', { error: e.message });
    }
  };
  
  eventSource.onerror = (error) => {
    logger.error('SSE connection error', { taskId });
    if (onError) {
      onError(error);
    }
    eventSource.close();
  };
  
  // Return object with close method for easy cleanup
  return {
    eventSource,
    close: () => {
      if (eventSource.readyState !== EventSource.CLOSED) {
        eventSource.close();
      }
    }
  };
};

/**
 * Generate a unique task ID using crypto.randomUUID if available
 * @returns {string} Unique task ID
 */
export const generateTaskId = () => {
  // Use crypto.randomUUID() if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `task_${crypto.randomUUID()}`;
  }
  // Fallback for older browsers
  return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// ============== LLM API Functions ==============

/**
 * Get LLM service status
 */
export const getLLMStatus = async () => {
  const response = await api.get('/api/llm/status');
  return response.data;
};

/**
 * Get LLM configuration
 */
export const getLLMConfig = async () => {
  const response = await api.get('/api/llm/config');
  return response.data;
};

/**
 * Update LLM configuration
 */
export const updateLLMConfig = async (config) => {
  const response = await api.post('/api/llm/config', config);
  return response.data;
};

/**
 * Get available models
 */
export const getLLMModels = async () => {
  const response = await api.get('/api/llm/models');
  return response.data;
};

/**
 * Get recommended models
 */
export const getRecommendedModels = async () => {
  const response = await api.get('/api/llm/models/recommended');
  return response.data;
};

/**
 * Pull a model (uses POST with streaming response)
 */
export const pullModel = async (modelName, onProgress, onError, onComplete) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/models/pull`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model_name: modelName }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n').filter(line => line.startsWith('data: '));

      for (const line of lines) {
        try {
          const data = JSON.parse(line.slice(6));
          onProgress(data);

          // Handle completion (success or completed status)
          if (data.status === 'success' || data.status === 'completed') {
            if (onComplete) onComplete(data);
            return;
          }
          
          // Handle error
          if (data.status === 'error') {
            if (onError) onError(data.error || 'Unknown error');
            return;
          }
        } catch (e) {
          // Ignore parse errors for incomplete lines
        }
      }
    }
    
    // If we exit the loop without completion, call onComplete
    if (onComplete) onComplete({ status: 'completed', model: modelName });
  } catch (error) {
    logger.error('Model pull error', { model: modelName, error: error.message });
    if (onError) onError(error.message || 'Unknown error');
  }
};

/**
 * Delete a model
 */
export const deleteModel = async (modelName) => {
  const response = await api.delete(`/api/llm/models/${encodeURIComponent(modelName)}`);
  return response.data;
};

/**
 * Generate node explanation using LLM
 */
export const generateExplanation = async (nodeType, nodeName, codeContext) => {
  const response = await api.post('/api/llm/generate/explanation', {
    node_type: nodeType,
    node_name: nodeName,
    code_context: codeContext,
  });
  return response.data;
};

/**
 * Generate challenge using LLM
 */
export const generateChallenge = async (category, difficulty = 'medium', topic = null, focusIssues = null) => {
  const response = await api.post('/api/llm/generate/challenge', {
    category,
    difficulty,
    topic,
    focus_issues: focusIssues,
  });
  return response.data;
};

/**
 * Generate hint using LLM
 */
export const generateHint = async (code, issues, userProgress = '') => {
  const response = await api.post('/api/llm/generate/hint', {
    code,
    issues,
    user_progress: userProgress,
  });
  return response.data;
};

/**
 * Get aria2 status
 */
export const getAria2Status = async () => {
  const response = await api.get('/api/llm/downloads/aria2/status');
  return response.data;
};

/**
 * Get aria2 install instructions
 */
export const getAria2InstallInstructions = async () => {
  const response = await api.get('/api/llm/downloads/aria2/install');
  return response.data;
};

/**
 * Get Ollama download info
 */
export const getOllamaDownloadInfo = async () => {
  const response = await api.get('/api/llm/downloads/ollama');
  return response.data;
};

/**
 * Get Ollama installation status
 */
export const getOllamaStatus = async () => {
  const response = await api.get('/api/llm/ollama/status');
  return response.data;
};

/**
 * Get Ollama download info for installation
 */
export const getOllamaInstallInfo = async () => {
  const response = await api.get('/api/llm/ollama/download-info');
  return response.data;
};

/**
 * Install Ollama (returns streaming progress)
 */
export const installOllama = async (onProgress, onError, onComplete) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/ollama/install`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n').filter(line => line.startsWith('data: '));

      for (const line of lines) {
        try {
          const data = JSON.parse(line.slice(6));
          onProgress(data);

          if (data.status === 'completed' || data.status === 'error') {
            if (data.status === 'completed' && onComplete) onComplete(data);
            if (data.status === 'error' && onError) onError(data.error);
            return;
          }
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  } catch (error) {
    logger.error('Ollama install error', { error: error.message });
    if (onError) onError(error.message);
  }
};

/**
 * Start Ollama server
 */
export const startOllamaServer = async (port = 11434) => {
  const response = await api.post('/api/llm/ollama/start', { port });
  return response.data;
};

/**
 * Stop Ollama server
 */
export const stopOllamaServer = async () => {
  const response = await api.post('/api/llm/ollama/stop');
  return response.data;
};

export default api;