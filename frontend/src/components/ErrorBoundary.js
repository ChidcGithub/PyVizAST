import React from 'react';
import { logReactError } from '../utils/logger';

/**
 * Error type enumeration
 */
const ErrorType = {
  NETWORK: 'network',
  SYNTAX: 'syntax',
  RUNTIME: 'runtime',
  CHUNK_LOAD: 'chunk_load',
  UNKNOWN: 'unknown'
};

/**
 * Determine error type based on error message
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
 * Get hint message for error type
 */
const getErrorHint = (errorType) => {
  switch (errorType) {
    case ErrorType.NETWORK:
      return {
        title: 'Network Connection Issue',
        description: 'Unable to connect to the server. Please check your network connection or server status.',
        action: 'Retry'
      };
    case ErrorType.CHUNK_LOAD:
      return {
        title: 'Resource Loading Failed',
        description: 'Page resource loading failed. This may be due to network issues or the application has been updated.',
        action: 'Refresh Page'
      };
    case ErrorType.SYNTAX:
      return {
        title: 'Code Parsing Error',
        description: 'There is a syntax error in the code. Please check the code format.',
        action: 'Check Code'
      };
    default:
      return {
        title: 'Runtime Error',
        description: 'The application encountered an unexpected error.',
        action: 'Reload'
      };
  }
};

/**
 * Error Boundary Component
 * Catches JavaScript errors in child component tree to prevent the entire app from crashing
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
    // Log error to the logging system
    logReactError(error, errorInfo);
    this.setState({ errorInfo });
    
    // Call external error handling callback
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
    // For chunk load errors, directly refresh the page
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
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
              {this.state.error?.message || 'An unknown error occurred'}
            </p>
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="error-details">
                <summary>Error details (visible in development only)</summary>
                <pre>{this.state.errorInfo.componentStack}</pre>
              </details>
            )}
            <div className="error-actions">
              {this.state.errorType === ErrorType.CHUNK_LOAD ? (
                <button className="btn btn-primary" onClick={this.handleReload}>
                  Refresh Page
                </button>
              ) : (
                <>
                  <button className="btn btn-primary" onClick={this.handleReset}>
                    {hint.action}
                  </button>
                  <button className="btn btn-secondary" onClick={this.handleReload}>
                    Refresh Page
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
 * Functional Error Boundary Wrapper
 * Used to catch errors in specific components
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
 * Error Boundary for Lazy Loaded Components
 * Specifically handles ChunkLoadError
 */
export function LazyLoadErrorBoundary({ children, onRetry }) {
  return (
    <ErrorBoundary 
      fallback={
        <div className="lazy-load-error">
          <p>Component loading failed</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>
            Refresh Page
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