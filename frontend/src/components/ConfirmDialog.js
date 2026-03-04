import React, { useEffect, useCallback } from 'react';
import './components.css';

/**
 * Custom Confirmation Dialog Component
 * Used as a replacement for the browser's native confirm dialog
 */
function ConfirmDialog({ 
  isOpen, 
  title = 'Confirm', 
  message, 
  confirmText = 'Confirm', 
  cancelText = 'Cancel',
  confirmVariant = 'primary', // 'primary' | 'danger'
  onConfirm, 
  onCancel 
}) {
  // ESC key to close dialog
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      onCancel?.();
    } else if (e.key === 'Enter') {
      onConfirm?.();
    }
  }, [onConfirm, onCancel]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Disable background scrolling
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog-container" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3 className="dialog-title">{title}</h3>
        </div>
        <div className="dialog-body">
          <p className="dialog-message">{message}</p>
        </div>
        <div className="dialog-footer">
          <button 
            className="dialog-btn dialog-btn-cancel"
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button 
            className={`dialog-btn dialog-btn-confirm ${confirmVariant === 'danger' ? 'danger' : ''}`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;