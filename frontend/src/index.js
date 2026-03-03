import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

/**
 * 全局抑制 ResizeObserver 良性错误
 * 这是浏览器的正常行为，不是真正的错误
 * 
 * 重要：这个 IIFE 必须在 React 渲染之前执行
 * 它会阻止错误触发 webpack-dev-server 的错误覆盖层
 */
(function suppressResizeObserverErrors() {
  const ERROR_PATTERNS = ['ResizeObserver loop', 'ResizeObserver'];

  const shouldSuppress = (message) => {
    if (!message) return false;
    const msg = typeof message === 'string' ? message : String(message);
    return ERROR_PATTERNS.some(pattern => msg.includes(pattern));
  };

  // 1. 重写 window.onerror - 最早的错误捕获点
  const originalOnError = window.onerror;
  window.onerror = function(message, source, lineno, colno, error) {
    if (shouldSuppress(message)) {
      return true; // 返回 true 阻止默认行为和传播
    }
    if (originalOnError) {
      return originalOnError.call(this, message, source, lineno, colno, error);
    }
    return false;
  };

  // 2. 捕获阶段的错误事件处理器 - 在 React 错误边界之前
  window.addEventListener('error', (event) => {
    if (shouldSuppress(event.message)) {
      event.stopImmediatePropagation();
      event.preventDefault();
      return false;
    }
  }, true); // true = 捕获阶段

  // 3. 捕获未处理的 Promise rejection
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
  }, true); // true = 捕获阶段

  // 4. 重写 console.error 过滤输出
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
