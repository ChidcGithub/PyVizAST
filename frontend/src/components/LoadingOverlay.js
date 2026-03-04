import React from 'react';

function LoadingOverlay() {
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="loading-spinner">
          <div className="spinner-ring"></div>
          <div className="spinner-ring"></div>
          <div className="spinner-ring"></div>
        </div>
        <h3>Analyzing code...</h3>
        <p>Parsing AST structure and detecting issues</p>
      </div>
    </div>
  );
}

export default LoadingOverlay;