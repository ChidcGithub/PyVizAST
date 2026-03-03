import React, { useEffect, useCallback } from 'react';
import './components.css';

/**
 * 自定义确认对话框组件
 * 用于替代浏览器原生的 confirm 对话框
 */
function ConfirmDialog({ 
  isOpen, 
  title = '确认', 
  message, 
  confirmText = '确认', 
  cancelText = '取消',
  confirmVariant = 'primary', // 'primary' | 'danger'
  onConfirm, 
  onCancel 
}) {
  // ESC 键关闭对话框
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
      // 禁止背景滚动
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
