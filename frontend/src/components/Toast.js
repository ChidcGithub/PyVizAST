import React, { useEffect, useCallback, useState } from 'react';
import { useToast } from './ToastContext';

/**
 * Toast message type configuration
 */
const TOAST_TYPES = {
  success: {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
    className: 'toast-success',
  },
  error: {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
    className: 'toast-error',
  },
  warning: {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
    className: 'toast-warning',
  },
  info: {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
    className: 'toast-info',
  },
};

/**
 * Single Toast message component
 */
function ToastItem({ toast, onDismiss }) {
  const [isExiting, setIsExiting] = useState(false);
  const typeConfig = TOAST_TYPES[toast.type] || TOAST_TYPES.info;
  const duration = toast.duration || 4000;

  // Dismiss animation handler
  const handleDismiss = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onDismiss(toast.id);
    }, 350);
  }, [toast.id, onDismiss]);

  // Auto dismiss
  useEffect(() => {
    if (duration === 0) return;
    
    const timer = setTimeout(() => {
      handleDismiss();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, handleDismiss]);

  // Close button click handler
  const handleCloseClick = useCallback((e) => {
    e.stopPropagation();
    handleDismiss();
  }, [handleDismiss]);

  return (
    <div 
      className={`toast-notification ${typeConfig.className} ${isExiting ? 'toast-exiting' : 'toast-entering'}`}
      onClick={toast.onClick}
      role="alert"
    >
      <div className="toast-icon">
        {typeConfig.icon}
      </div>
      <div className="toast-content">
        {toast.title && <div className="toast-title">{toast.title}</div>}
        <div className="toast-message">{toast.message}</div>
      </div>
      {toast.action && (
        <button 
          className="toast-action"
          onClick={(e) => {
            e.stopPropagation();
            toast.action.onClick();
            handleDismiss();
          }}
        >
          {toast.action.label}
        </button>
      )}
      <button 
        className="toast-close" 
        onClick={handleCloseClick}
        aria-label="Close notification"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
      {duration > 0 && (
        <div 
          className="toast-progress" 
          style={{ animationDuration: `${duration}ms` }}
        />
      )}
    </div>
  );
}

/**
 * Toast container component - displays all active toast messages
 * Simple vertical stack, newest at top
 */
export function ToastContainer() {
  const { toasts, dismissToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <ToastItem 
          key={toast.id} 
          toast={toast} 
          onDismiss={dismissToast}
        />
      ))}
    </div>
  );
}

export default ToastContainer;