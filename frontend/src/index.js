import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

/**
 * Globally suppress benign ResizeObserver errors
 * This is normal browser behavior, not a real error
 * 
 * Important: This IIFE must execute before React renders
 * It prevents errors from triggering webpack-dev-server's error overlay
 */
(function suppressResizeObserverErrors() {
  const ERROR_PATTERNS = ['ResizeObserver loop', 'ResizeObserver'];

  const shouldSuppress = (message) => {
    if (!message) return false;
    const msg = typeof message === 'string' ? message : String(message);
    return ERROR_PATTERNS.some(pattern => msg.includes(pattern));
  };

  // 1. Override window.onerror - the earliest error capture point
  const originalOnError = window.onerror;
  window.onerror = function(message, source, lineno, colno, error) {
    if (shouldSuppress(message)) {
      return true; // Return true to prevent default behavior and propagation
    }
    if (originalOnError) {
      return originalOnError.call(this, message, source, lineno, colno, error);
    }
    return false;
  };

  // 2. Capturing phase error event handler - before React error boundaries
  window.addEventListener('error', (event) => {
    if (shouldSuppress(event.message)) {
      event.stopImmediatePropagation();
      event.preventDefault();
      return false;
    }
  }, true); // true = capturing phase

  // 3. Capture unhandled Promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    let message = '';
    
    if (reason?.message) {
      message = reason.message;
    } else if (typeof reason === 'string') {
      message = reason;
    } else if (reason?.toString) {
      message = reason.toString();
    }
    
    if (shouldSuppress(message)) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  }, true); // true = capturing phase

  // 4. Override console.error to filter output
  const originalConsoleError = console.error;
  console.error = function(...args) {
    const firstArg = args[0];
    let message = '';
    
    if (typeof firstArg === 'string') {
      message = firstArg;
    } else if (firstArg?.message) {
      message = firstArg.message;
    } else if (firstArg?.toString) {
      message = firstArg.toString();
    }
    
    if (shouldSuppress(message)) {
      return;
    }
    originalConsoleError.apply(console, args);
  };
})();

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);