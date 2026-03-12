/**
 * Frontend Logging System
 * Captures errors and sends to backend to save in logs folder
 */

const LOG_LEVELS = {
  DEBUG: 'debug',
  INFO: 'info',
  WARN: 'warn',
  ERROR: 'error',
};

// Log buffer for batch sending
let logBuffer = [];
let flushTimer = null;
let isInitialized = false;

// Check if running in browser environment
const isBrowser = () => {
  return typeof window !== 'undefined' && typeof navigator !== 'undefined';
};

// Get API base URL
const getApiBaseUrl = () => {
  return process.env.REACT_APP_API_URL || 'http://localhost:8000';
};

// Batch send logs to backend
const flushLogs = async () => {
  if (logBuffer.length === 0 || !isBrowser()) return;

  const logsToSend = [...logBuffer];
  logBuffer = [];

  try {
    await fetch(`${getApiBaseUrl()}/api/logs/frontend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ logs: logsToSend }),
    });
  } catch (error) {
    // If send fails, put logs back in buffer
    console.error('Failed to send logs to server:', error);
    logBuffer = [...logsToSend, ...logBuffer];
  }
};

// Schedule log flush
const scheduleFlush = () => {
  if (flushTimer) {
    clearTimeout(flushTimer);
  }
  
  // If buffer exceeds 10 entries, send immediately
  if (logBuffer.length >= 10) {
    flushLogs();
    return;
  }
  
  // Otherwise send after 5 seconds
  flushTimer = setTimeout(flushLogs, 5000);
};

// Error patterns to ignore
const IGNORED_ERROR_PATTERNS = [
  'ResizeObserver',
  'Network request failed',
];

// Check if log should be ignored
const shouldIgnoreLog = (message, data = {}) => {
  const fullMessage = `${message} ${Object.values(data).join(' ')}`;
  return IGNORED_ERROR_PATTERNS.some(pattern => fullMessage.includes(pattern));
};

// Add log to buffer
const addLog = (level, message, data = {}) => {
  // Filter out errors that should be ignored
  if (shouldIgnoreLog(message, data)) {
    return;
  }

  const logEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...data,
  };

  // Add browser info only if available
  if (isBrowser()) {
    logEntry.userAgent = navigator.userAgent;
    logEntry.url = window.location.href;
  }

  logBuffer.push(logEntry);

  // Error level sends immediately
  if (level === LOG_LEVELS.ERROR) {
    flushLogs();
  } else {
    scheduleFlush();
  }

  // Also output to console
  const consoleMethod = level === LOG_LEVELS.ERROR ? 'error' : 
                        level === LOG_LEVELS.WARN ? 'warn' : 'log';
  console[consoleMethod](`[${level.toUpperCase()}] ${message}`, data);
};

// Export log functions
export const logger = {
  debug: (message, data) => addLog(LOG_LEVELS.DEBUG, message, data),
  info: (message, data) => addLog(LOG_LEVELS.INFO, message, data),
  warn: (message, data) => addLog(LOG_LEVELS.WARN, message, data),
  error: (message, data) => addLog(LOG_LEVELS.ERROR, message, data),
  
  // Manual log flush
  flush: flushLogs,
};

// Global error handling
export const setupGlobalErrorHandlers = () => {
  // Skip if not in browser environment or already initialized
  if (!isBrowser() || isInitialized) {
    return;
  }
  
  isInitialized = true;

  // Capture unhandled Promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    // Ignore ResizeObserver related errors
    const reason = event.reason?.message || String(event.reason);
    if (reason.includes('ResizeObserver')) {
      event.preventDefault();
      return;
    }
    
    logger.error('Unhandled Promise Rejection', {
      reason: reason,
      stack: event.reason?.stack,
    });
  });

  // Capture global JavaScript errors
  window.addEventListener('error', (event) => {
    // Ignore resource loading errors (e.g., image load failures)
    if (event.target && event.target !== window) {
      return;
    }

    // Ignore ResizeObserver benign errors
    if (event.message?.includes('ResizeObserver')) {
      event.preventDefault();
      return;
    }

    logger.error('Uncaught JavaScript Error', {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack,
    });
  }, true); // Use capture phase

  // Send remaining logs before page unload
  window.addEventListener('beforeunload', () => {
    if (logBuffer.length > 0) {
      // Use sendBeacon to ensure logs are sent
      const data = JSON.stringify({ logs: logBuffer });
      navigator.sendBeacon(`${getApiBaseUrl()}/api/logs/frontend`, data);
    }
  });
};

// React error boundary log helper
export const logReactError = (error, errorInfo) => {
  logger.error('React Error Boundary Caught', {
    message: error.message,
    stack: error.stack,
    componentStack: errorInfo?.componentStack,
  });
};

export default logger;