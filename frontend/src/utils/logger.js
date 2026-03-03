/**
 * 前端日志系统
 * 捕获错误并发送到后端保存到 logs 文件夹
 */

const LOG_LEVELS = {
  DEBUG: 'debug',
  INFO: 'info',
  WARN: 'warn',
  ERROR: 'error',
};

// 日志缓冲区，用于批量发送
let logBuffer = [];
let flushTimer = null;

// 获取 API 基础 URL
const getApiBaseUrl = () => {
  return process.env.REACT_APP_API_URL || 'http://localhost:8000';
};

// 批量发送日志到后端
const flushLogs = async () => {
  if (logBuffer.length === 0) return;

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
    // 如果发送失败，将日志放回缓冲区
    console.error('Failed to send logs to server:', error);
    logBuffer = [...logsToSend, ...logBuffer];
  }
};

// 调度日志刷新
const scheduleFlush = () => {
  if (flushTimer) {
    clearTimeout(flushTimer);
  }
  
  // 如果缓冲区超过 10 条，立即发送
  if (logBuffer.length >= 10) {
    flushLogs();
    return;
  }
  
  // 否则 5 秒后发送
  flushTimer = setTimeout(flushLogs, 5000);
};

// 应该忽略的错误模式
const IGNORED_ERROR_PATTERNS = [
  'ResizeObserver',
  'Network request failed',
];

// 检查是否应该忽略该日志
const shouldIgnoreLog = (message, data = {}) => {
  const fullMessage = `${message} ${Object.values(data).join(' ')}`;
  return IGNORED_ERROR_PATTERNS.some(pattern => fullMessage.includes(pattern));
};

// 添加日志到缓冲区
const addLog = (level, message, data = {}) => {
  // 过滤掉应该忽略的错误
  if (shouldIgnoreLog(message, data)) {
    return;
  }

  const logEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...data,
    userAgent: navigator.userAgent,
    url: window.location.href,
  };

  logBuffer.push(logEntry);

  // 错误级别立即发送
  if (level === LOG_LEVELS.ERROR) {
    flushLogs();
  } else {
    scheduleFlush();
  }

  // 同时在控制台输出
  const consoleMethod = level === LOG_LEVELS.ERROR ? 'error' : 
                        level === LOG_LEVELS.WARN ? 'warn' : 'log';
  console[consoleMethod](`[${level.toUpperCase()}] ${message}`, data);
};

// 导出日志函数
export const logger = {
  debug: (message, data) => addLog(LOG_LEVELS.DEBUG, message, data),
  info: (message, data) => addLog(LOG_LEVELS.INFO, message, data),
  warn: (message, data) => addLog(LOG_LEVELS.WARN, message, data),
  error: (message, data) => addLog(LOG_LEVELS.ERROR, message, data),
  
  // 手动刷新日志
  flush: flushLogs,
};

// 全局错误处理
export const setupGlobalErrorHandlers = () => {
  // 捕获未处理的 Promise 拒绝
  window.addEventListener('unhandledrejection', (event) => {
    // 忽略 ResizeObserver 相关错误
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

  // 捕获全局 JavaScript 错误
  window.addEventListener('error', (event) => {
    // 忽略资源加载错误（如图片加载失败）
    if (event.target && event.target !== window) {
      return;
    }

    // 忽略 ResizeObserver 良性错误
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
  }, true); // 使用捕获阶段

  // 页面卸载前发送剩余日志
  window.addEventListener('beforeunload', () => {
    if (logBuffer.length > 0) {
      // 使用 sendBeacon 确保日志被发送
      const data = JSON.stringify({ logs: logBuffer });
      navigator.sendBeacon(`${getApiBaseUrl()}/api/logs/frontend`, data);
    }
  });
};

// React 错误边界日志助手
export const logReactError = (error, errorInfo) => {
  logger.error('React Error Boundary Caught', {
    message: error.message,
    stack: error.stack,
    componentStack: errorInfo?.componentStack,
  });
};

export default logger;
