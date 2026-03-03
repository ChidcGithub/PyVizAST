import React from 'react';
import { logReactError } from '../utils/logger';

/**
 * 错误类型枚举
 */
const ErrorType = {
  NETWORK: 'network',
  SYNTAX: 'syntax',
  RUNTIME: 'runtime',
  CHUNK_LOAD: 'chunk_load',
  UNKNOWN: 'unknown'
};

/**
 * 根据错误信息判断错误类型
 */
const getErrorType = (error) => {
  if (!error) return ErrorType.UNKNOWN;
  
  const message = error.message?.toLowerCase() || '';
  const name = error.name?.toLowerCase() || '';
  
  // Chunk load error (lazy loading failed)
  if (name === 'ChunkLoadError' || message.includes('loading chunk') || message.includes('loading css chunk')) {
    return ErrorType.CHUNK_LOAD;
  }
  
  // Network error
  if (
    message.includes('network') ||
    message.includes('fetch') ||
    message.includes('timeout') ||
    message.includes('abort') ||
    name === 'networkerror'
  ) {
    return ErrorType.NETWORK;
  }
  
  // Syntax error
  if (name === 'SyntaxError' || message.includes('syntax')) {
    return ErrorType.SYNTAX;
  }
  
  return ErrorType.RUNTIME;
};

/**
 * 获取错误类型对应的提示信息
 */
const getErrorHint = (errorType) => {
  switch (errorType) {
    case ErrorType.NETWORK:
      return {
        title: '网络连接问题',
        description: '无法连接到服务器，请检查网络连接或服务器状态。',
        action: '重试'
      };
    case ErrorType.CHUNK_LOAD:
      return {
        title: '资源加载失败',
        description: '页面资源加载失败，可能是网络问题或应用已更新。',
        action: '刷新页面'
      };
    case ErrorType.SYNTAX:
      return {
        title: '代码解析错误',
        description: '代码存在语法错误，请检查代码格式。',
        action: '检查代码'
      };
    default:
      return {
        title: '运行时错误',
        description: '应用遇到了意外错误。',
        action: '重新加载'
      };
  }
};

/**
 * 错误边界组件
 * 捕获子组件树中的 JavaScript 错误，防止整个应用崩溃
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorType: ErrorType.UNKNOWN
    };
  }

  static getDerivedStateFromError(error) {
    const errorType = getErrorType(error);
    return { hasError: true, error, errorType };
  }

  componentDidCatch(error, errorInfo) {
    // 记录错误信息到日志系统
    logReactError(error, errorInfo);
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
    
    // 在开发环境中输出详细错误
    if (process.env.NODE_ENV === 'development') {
      console.group('🔍 Error Details');
      console.error('Error:', error);
      console.error('Component Stack:', errorInfo?.componentStack);
      console.groupEnd();
    }
    
    // 调用外部错误处理回调
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorType: ErrorType.UNKNOWN
    });
    
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReload = () => {
    // 对于 chunk load 错误，直接刷新页面
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // 自定义降级 UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const hint = getErrorHint(this.state.errorType);

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2>{hint.title}</h2>
            <p className="error-description">{hint.description}</p>
            <p className="error-message">
              {this.state.error?.message || '发生了未知错误'}
            </p>
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="error-details">
                <summary>错误详情（仅开发环境可见）</summary>
                <pre>{this.state.errorInfo.componentStack}</pre>
              </details>
            )}
            <div className="error-actions">
              {this.state.errorType === ErrorType.CHUNK_LOAD ? (
                <button className="btn btn-primary" onClick={this.handleReload}>
                  刷新页面
                </button>
              ) : (
                <>
                  <button className="btn btn-primary" onClick={this.handleReset}>
                    {hint.action}
                  </button>
                  <button className="btn btn-secondary" onClick={this.handleReload}>
                    刷新页面
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * 函数式错误边界包装器
 * 用于捕获特定组件的错误
 */
export function withErrorBoundary(WrappedComponent, fallback = null, onError = null) {
  return function ErrorBoundaryWrapper(props) {
    return (
      <ErrorBoundary fallback={fallback} onError={onError}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
}

/**
 * 用于懒加载组件的错误边界
 * 专门处理 ChunkLoadError
 */
export function LazyLoadErrorBoundary({ children, onRetry }) {
  return (
    <ErrorBoundary 
      fallback={
        <div className="lazy-load-error">
          <p>组件加载失败</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>
            刷新页面
          </button>
        </div>
      }
      onReset={onRetry}
    >
      {children}
    </ErrorBoundary>
  );
}

export default ErrorBoundary;
