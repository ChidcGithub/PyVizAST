import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

const ToastContext = createContext(null);

/**
 * Toast Provider - provides global toast state management
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idCounterRef = useRef(0);

  // Show toast message
  const showToast = useCallback((message, type = 'info', options = {}) => {
    const id = `toast-${Date.now()}-${idCounterRef.current++}`;
    
    const toast = {
      id,
      message,
      type,
      title: options.title,
      duration: options.duration ?? 4000,
      action: options.action,
      onClick: options.onClick,
    };

    setToasts(prev => {
      // Add new toast to the beginning of array (top position in column layout)
      const newToasts = [toast, ...prev];
      // Limit max display count, remove oldest (from the end)
      if (newToasts.length > 15) {
        return newToasts.slice(0, 15);
      }
      return newToasts;
    });

    return id;
  }, []);

  // Dismiss specific toast
  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  // Dismiss all toasts
  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  // Convenience methods
  const success = useCallback((message, options = {}) => {
    return showToast(message, 'success', options);
  }, [showToast]);

  const error = useCallback((message, options = {}) => {
    return showToast(message, 'error', { ...options, duration: options.duration ?? 6000 });
  }, [showToast]);

  const warning = useCallback((message, options = {}) => {
    return showToast(message, 'warning', options);
  }, [showToast]);

  const info = useCallback((message, options = {}) => {
    return showToast(message, 'info', options);
  }, [showToast]);

  const value = {
    toasts,
    showToast,
    dismissToast,
    dismissAll,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
    </ToastContext.Provider>
  );
}

/**
 * Hook for using Toast Context
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export default ToastContext;
