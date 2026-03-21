import axios from 'axios';
import logger from './utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 60000; // 60 seconds timeout (increased for large file analysis)
const MAX_RETRIES = 2; // Maximum retry attempts
const RETRY_DELAY = 1000; // Retry delay (milliseconds)

// Idempotent method list (safe to retry)
const IDEMPOTENT_METHODS = ['get', 'head', 'options', 'put', 'delete'];

// LLM endpoints that are safe to retry (they generate content, not modify state)
const LLM_RETRY_ENDPOINTS = [
  '/api/llm/generate/explanation',
  '/api/llm/generate/hint',
];

// Determine if error should be retried
const shouldRetry = (error, method, url) => {
  // Cases not to retry
  if (!error) return false;
  
  // Don't retry if user cancelled the request (AbortError, CanceledError)
  if (error.name === 'AbortError' || error.name === 'CanceledError' || 
      error.code === 'ERR_CANCELED' || (error.code === 'ECONNABORTED' && error.message?.includes('cancel'))) {
    return false;
  }
  
  // LLM endpoints are safe to retry even for POST requests
  if (url && LLM_RETRY_ENDPOINTS.some(endpoint => url.includes(endpoint))) {
    // Continue to retry logic below
  } else if (method && !IDEMPOTENT_METHODS.includes(method.toLowerCase())) {
    // Non-idempotent methods don't retry (avoid duplicate operations)
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
const withRetry = async (requestFn, method = 'get', url = '', retries = MAX_RETRIES) => {
  try {
    return await requestFn();
  } catch (error) {
    // If shouldn't retry or retries exhausted
    if (!shouldRetry(error, method, url) || retries <= 0) {
      throw error;
    }

    // Wait then retry
    await delay(RETRY_DELAY);
    return withRetry(requestFn, method, url, retries - 1);
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
    // Ignore cancelled requests - don't transform to error
    if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError' || error.name === 'AbortError') {
      return Promise.reject(error);
    }
    
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

// ============== LLM API Configuration ==============

const LLM_TIMEOUT = 300000; // 5 minutes for LLM operations

/**
 * Helper: Parse SSE stream from response
 */
const parseSSEStream = async (response, callbacks) => {
  const { onProgress, onError, onComplete } = callbacks;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;

        try {
          const data = JSON.parse(line.slice(6));
          onProgress?.(data);

          // Check for completion states
          if (data.status === 'completed' || data.status === 'success') {
            onComplete?.(data);
            return;
          }

          if (data.status === 'error') {
            onError?.(data.error || 'Unknown error');
            return;
          }
        } catch (e) {
          // Skip malformed JSON
          logger.debug('SSE parse skip', { line: line.slice(0, 50) });
        }
      }
    }

    // Process any remaining buffer
    if (buffer.startsWith('data: ')) {
      try {
        const data = JSON.parse(buffer.slice(6));
        onProgress?.(data);
        if (data.status === 'completed' || data.status === 'success') {
          onComplete?.(data);
        } else if (data.status === 'error') {
          onError?.(data.error);
        }
      } catch (e) {
        // Ignore final parse errors
      }
    }
  } catch (error) {
    logger.error('SSE stream error', { error: error.message });
    onError?.(error.message);
  }
};

// ============== LLM Status & Configuration ==============

/**
 * Get LLM service status
 * @returns {Promise<{status: string, enabled: boolean, model?: string, message: string}>}
 */
export const getLLMStatus = async () => {
  const response = await api.get('/api/llm/status');
  return response.data;
};

/**
 * Get LLM configuration
 * @returns {Promise<Object>}
 */
export const getLLMConfig = async () => {
  const response = await api.get('/api/llm/config');
  return response.data;
};

/**
 * Update LLM configuration
 * @param {Object} config - Configuration object
 * @returns {Promise<{status: string, config: Object, llm_status: Object}>}
 */
export const updateLLMConfig = async (config) => {
  const response = await api.post('/api/llm/config', config, { timeout: 15000 });
  return response.data;
};

// ============== Model Management ==============

/**
 * Get available (pulled) models
 * @returns {Promise<Array<{name: string, size: number, modified_at: string}>>}
 */
export const getLLMModels = async () => {
  const response = await api.get('/api/llm/models');
  return response.data;
};

/**
 * Get recommended models
 * @returns {Promise<Array<Object>>}
 */
export const getRecommendedModels = async () => {
  const response = await api.get('/api/llm/models/recommended');
  return response.data;
};

/**
 * Pull a model from Ollama registry (streaming)
 * @param {string} modelName - Model name to pull
 * @param {function} onProgress - Progress callback
 * @param {function} onError - Error callback
 * @param {function} onComplete - Completion callback
 */
export const pullModel = async (modelName, onProgress, onError, onComplete) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/models/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    await parseSSEStream(response, {
      onProgress,
      onError,
      onComplete: (data) => onComplete?.({ ...data, model: modelName }),
    });
  } catch (error) {
    logger.error('Model pull error', { model: modelName, error: error.message });
    onError?.(error.message);
  }
};

/**
 * Delete a model
 * @param {string} modelName - Model name to delete
 * @returns {Promise<{status: string, message: string}>}
 */
export const deleteModel = async (modelName) => {
  const response = await api.delete(`/api/llm/models/${encodeURIComponent(modelName)}`);
  return response.data;
};

// ============== LLM Generation ==============

/**
 * Generate node explanation using LLM
 * @param {Object} params - Request parameters
 * @param {string} params.node_type - AST node type
 * @param {string} [params.node_name] - Node name/identifier
 * @param {string} [params.code_context] - Code snippet for the node
 * @param {Object} [params.node_info] - Additional node information
 * @param {string} [params.full_code] - Full source code for context
 * @param {AbortSignal} [signal] - Optional abort signal
 * @returns {Promise<{node_type: string, explanation: string, python_doc: string, examples: string[], related_concepts: string[]}>}
 */
export const generateExplanation = async (params, signal = null) => {
  const url = '/api/llm/generate/explanation';
  return withRetry(async () => {
    const response = await api.post(url, {
      node_type: params.node_type,
      node_name: params.node_name,
      code_context: params.code_context,
      node_info: params.node_info,
      full_code: params.full_code,
    }, { timeout: LLM_TIMEOUT, signal });
    return response.data;
  }, 'post', url);
};

/**
 * Generate a new challenge using LLM
 * @param {string} category - Challenge category
 * @param {string} [difficulty='medium'] - Difficulty level
 * @param {string} [topic] - Optional topic
 * @param {string[]} [focusIssues] - Issues to focus on
 * @returns {Promise<Object>}
 */
export const generateChallenge = async (category, difficulty = 'medium', topic = null, focusIssues = null) => {
  const response = await api.post('/api/llm/generate/challenge', {
    category,
    difficulty,
    topic,
    focus_issues: focusIssues,
  }, { timeout: LLM_TIMEOUT });
  return response.data;
};

/**
 * Generate a contextual hint for a challenge
 * @param {string} code - Challenge code
 * @param {string[]} issues - Issues to find
 * @param {string} [userProgress=''] - User's current progress
 * @returns {Promise<{hint: string}>}
 */
export const generateHint = async (code, issues, userProgress = '') => {
  const response = await api.post('/api/llm/generate/hint', {
    code,
    issues,
    user_progress: userProgress,
  }, { timeout: LLM_TIMEOUT });
  return response.data;
};

// ============== Ollama Management ==============

/**
 * Get Ollama installation status
 * @returns {Promise<{installed: boolean, running: boolean, can_auto_install: boolean, version?: string}>}
 */
export const getOllamaStatus = async () => {
  const response = await api.get('/api/llm/ollama/status');
  return response.data;
};

/**
 * Get Ollama download information
 * @returns {Promise<Object>}
 */
export const getOllamaDownloadInfo = async () => {
  const response = await api.get('/api/llm/downloads/ollama');
  return response.data;
};

/**
 * Get Ollama installation info
 * @returns {Promise<Object>}
 */
export const getOllamaInstallInfo = async () => {
  const response = await api.get('/api/llm/ollama/download-info');
  return response.data;
};

/**
 * Install Ollama (streaming progress)
 * @param {function} onProgress - Progress callback
 * @param {function} onError - Error callback
 * @param {function} onComplete - Completion callback
 */
export const installOllama = async (onProgress, onError, onComplete) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/ollama/install`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    await parseSSEStream(response, { onProgress, onError, onComplete });
  } catch (error) {
    logger.error('Ollama install error', { error: error.message });
    onError?.(error.message);
  }
};

/**
 * Start Ollama server
 * @param {number} [port=11434] - Port to run on
 * @returns {Promise<{status: string, message: string}>}
 */
export const startOllamaServer = async (port = 11434) => {
  const response = await api.post('/api/llm/ollama/start', { port });
  return response.data;
};

/**
 * Stop Ollama server
 * @returns {Promise<{status: string, message: string}>}
 */
export const stopOllamaServer = async () => {
  const response = await api.post('/api/llm/ollama/stop');
  return response.data;
};

// ============== aria2 Download Manager ==============

/**
 * Get aria2 availability status
 * @returns {Promise<{available: boolean, version?: string, platform: string}>}
 */
export const getAria2Status = async () => {
  const response = await api.get('/api/llm/downloads/aria2/status');
  return response.data;
};

/**
 * Get aria2 installation instructions
 * @returns {Promise<{platform: string, instructions: string}>}
 */
export const getAria2InstallInstructions = async () => {
  const response = await api.get('/api/llm/downloads/aria2/install');
  return response.data;
};

export default api;