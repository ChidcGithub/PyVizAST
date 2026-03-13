import React, { useState, useCallback, useEffect, useRef, Suspense, lazy } from 'react';
import CodeEditor from './components/CodeEditor';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoadingOverlay from './components/LoadingOverlay';
import ErrorBoundary from './components/ErrorBoundary';
import ProjectAnalysisView from './components/ProjectAnalysisView';
import ProjectVisualization from './components/ProjectVisualization';
import LearnView from './components/LearnView';
import ChallengeView from './components/ChallengeView';
import GestureControl from './components/GestureControl';
import { GestureType } from './utils/GestureService';
import { analyzeCode, checkServerHealth, getApiBaseUrl } from './api';
import { setupGlobalErrorHandlers } from './utils/logger';
import './App.css';
import './components/components.css';
import './components/AnalysisPanel.css';
import './components/LearnChallenge.css';
import './components/GestureControl.css';

// Lazy load heavy components for code splitting
const ASTVisualizer = lazy(() => import('./components/ASTVisualizer'));
const ASTVisualizer3D = lazy(() => import('./components/ASTVisualizer3D'));
const AnalysisPanel = lazy(() => import('./components/AnalysisPanel'));

// Loading fallback for lazy components
const ComponentLoader = () => (
  <div className="component-loader">
    <div className="loader-spinner"></div>
    <span>Loading component...</span>
  </div>
);

// Share URL utilities
const compressCode = (code) => {
  try {
    // Use base64 encoding for URL-safe sharing
    return btoa(encodeURIComponent(code));
  } catch (e) {
    return null;
  }
};

const decompressCode = (encoded) => {
  try {
    return decodeURIComponent(atob(encoded));
  } catch (e) {
    return null;
  }
};

// Export utilities
const generateHTMLReport = (result, code) => {
  const issues = result?.issues || [];
  const suggestions = result?.suggestions || [];
  const complexity = result?.complexity || {};
  
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PyVizAST Analysis Report</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; line-height: 1.6; padding: 40px; }
    .container { max-width: 1000px; margin: 0 auto; }
    h1 { font-size: 24px; margin-bottom: 8px; }
    h2 { font-size: 18px; margin: 24px 0 12px; color: #fff; border-bottom: 1px solid #333; padding-bottom: 8px; }
    .meta { color: #888; font-size: 13px; margin-bottom: 24px; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
    .stat { background: #141414; padding: 16px; border-radius: 8px; text-align: center; }
    .stat-value { font-size: 24px; font-weight: 600; color: #fff; }
    .stat-label { font-size: 11px; color: #888; text-transform: uppercase; margin-top: 4px; }
    .issue { background: #141414; padding: 14px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #f87171; }
    .issue.warning { border-left-color: #facc15; }
    .issue.info { border-left-color: #94a3b8; }
    .issue-title { font-weight: 500; margin-bottom: 4px; }
    .issue-location { font-size: 12px; color: #888; }
    .suggestion { background: #141414; padding: 14px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #4ade80; }
    pre { background: #0a0a0a; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; margin-top: 16px; border: 1px solid #222; }
    code { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #222; text-align: center; color: #666; font-size: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>PyVizAST Analysis Report</h1>
    <p class="meta">Generated on ${new Date().toLocaleString()}</p>
    
    <div class="stats">
      <div class="stat">
        <div class="stat-value">${complexity.lines_of_code || 0}</div>
        <div class="stat-label">Lines of Code</div>
      </div>
      <div class="stat">
        <div class="stat-value">${complexity.cyclomatic_complexity || 0}</div>
        <div class="stat-label">Cyclomatic Complexity</div>
      </div>
      <div class="stat">
        <div class="stat-value">${issues.length}</div>
        <div class="stat-label">Issues Found</div>
      </div>
      <div class="stat">
        <div class="stat-value">${suggestions.length}</div>
        <div class="stat-label">Suggestions</div>
      </div>
    </div>
    
    ${issues.length > 0 ? `
    <h2>Issues (${issues.length})</h2>
    ${issues.map(issue => `
      <div class="issue ${issue.severity?.toLowerCase() || 'info'}">
        <div class="issue-title">${issue.message || issue.type}</div>
        <div class="issue-location">Line ${issue.lineno || '?'} • ${issue.severity || 'INFO'}</div>
      </div>
    `).join('')}
    ` : '<p>No issues found.</p>'}
    
    ${suggestions.length > 0 ? `
    <h2>Suggestions (${suggestions.length})</h2>
    ${suggestions.slice(0, 20).map(s => `
      <div class="suggestion">
        <div class="issue-title">${s.message || s.title}</div>
      </div>
    `).join('')}
    ` : ''}
    
    <h2>Source Code</h2>
    <pre><code>${(code || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>
    
    <div class="footer">
      Generated by <strong>PyVizAST</strong> - Python AST Visualizer & Static Analyzer
    </div>
  </div>
</body>
</html>`;
};

// Sample code for demo
const SAMPLE_CODE = `# PyVizAST Sample Code
# This file demonstrates various Python syntax structures

import os
from typing import List, Optional

# Global configuration
CONFIG = {
    "debug": True,
    "max_items": 100
}

class DataProcessor:
    """Data processor class"""
    
    def __init__(self, name: str):
        self.name = name
        self.data = []
    
    def process(self, items: List[int]) -> List[int]:
        """Process data list"""
        result = []
        
        # Nested loop example
        for item in items:
            if item > 0:
                for i in range(item):
                    if i % 2 == 0:
                        result.append(i * 2)
        
        return result
    
    def calculate_average(self, numbers: List[float]) -> Optional[float]:
        """Calculate average value"""
        if not numbers:
            return None
        
        total = sum(numbers)
        return total / len(numbers)


def fibonacci(n: int) -> int:
    """Recursively calculate Fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def find_duplicates(arr: List[int]) -> List[int]:
    """Find duplicate elements"""
    seen = set()
    duplicates = []
    
    for item in arr:
        if item in seen:
            if item not in duplicates:
                duplicates.append(item)
        else:
            seen.add(item)
    
    return duplicates


# Main function
def main():
    processor = DataProcessor("test")
    
    # Generate test data
    data = [i for i in range(20)]
    
    # Process data
    result = processor.process(data)
    print(f"Processing result: {result[:10]}...")
    
    # Calculate Fibonacci
    fib = fibonacci(10)
    print(f"Fibonacci(10) = {fib}")


if __name__ == "__main__":
    main()
`;


function App() {
  const [code, setCode] = useState(SAMPLE_CODE);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('ast');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState('dark');
  const [viewMode, setViewMode] = useState('2d'); // '2d' or '3d'
  const [serverStatus, setServerStatus] = useState({ checking: true, connected: false });
  
  // Analysis mode: 'file' or 'project'
  const [analysisMode, setAnalysisMode] = useState('file');
  
  // Progress tracking
  const [progress, setProgress] = useState(null);
  
  // Share & Export state
  const [shareUrl, setShareUrl] = useState(null);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  
  // Toast notification state
  const [toast, setToast] = useState(null);
  
  // Project analysis state
  const [projectResult, setProjectResult] = useState(null);
  const [isProjectAnalyzing, setIsProjectAnalyzing] = useState(false);
  const projectAnalysisRef = useRef(null);
  
  // Selected file in project mode
  const [selectedFile, setSelectedFile] = useState(null);
  const [isFileEditMode, setIsFileEditMode] = useState(false);
  
  // Splitter drag state
  const [splitPosition, setSplitPosition] = useState(50); // Percentage
  const [isDragging, setIsDragging] = useState(false);
  const mainContentRef = useRef(null);
  
  // AbortController for canceling requests
  const abortControllerRef = useRef(null);
  
  // Editor ref for calling editor methods (e.g., jump to line)
  const editorRef = useRef(null);
  
  // Gesture control state
  const [gestureEnabled, setGestureEnabled] = useState(false);
  const gestureControlRef = useRef(null);
  const visualizerRef = useRef(null); // For receiving gesture commands
  
  // Initialize global error handlers
  useEffect(() => {
    setupGlobalErrorHandlers();
  }, []);
  
  // Load shared code from URL on mount
  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.startsWith('#code=')) {
      const encoded = hash.slice(6);
      const decoded = decompressCode(encoded);
      if (decoded) {
        setCode(decoded);
        // Clear the hash to avoid re-loading on refresh
        window.history.replaceState(null, '', window.location.pathname);
      }
    }
  }, []);
  
  // Save theme preference
  useEffect(() => {
    localStorage.setItem('pyvizast-theme', theme);
    // Apply theme class to body
    document.body.classList.toggle('light-theme', theme === 'light');
  }, [theme]);
  
  // Load theme preference on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('pyvizast-theme');
    if (savedTheme) {
      setTheme(savedTheme);
    }
  }, []);
  
  // Splitter drag handling
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);
  
  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !mainContentRef.current) return;
    
    const rect = mainContentRef.current.getBoundingClientRect();
    const newPosition = ((e.clientX - rect.left) / rect.width) * 100;
    
    // Limit minimum and maximum position
    const clampedPosition = Math.min(Math.max(newPosition, 20), 80);
    setSplitPosition(clampedPosition);
  }, [isDragging]);
  
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);
  
  // Add global mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Check server connection status
  useEffect(() => {
    const checkConnection = async () => {
      const result = await checkServerHealth();
      setServerStatus({ 
        checking: false, 
        connected: result.connected,
        error: result.error,
        hint: result.hint
      });
    };
    
    checkConnection();
    // Check connection every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Cancel ongoing requests when component unmounts
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Single file analysis
  const handleAnalyze = useCallback(async () => {
    // In project mode, call project analysis
    if (analysisMode === 'project') {
      if (projectAnalysisRef.current?.canAnalyze()) {
        projectAnalysisRef.current.analyze();
      }
      return;
    }

    if (!code.trim()) {
      setError('Please enter Python code');
      return;
    }

    // Check server connection
    if (!serverStatus.connected) {
      setError(`Unable to connect to server (${getApiBaseUrl()}). Please ensure the backend is running: python run.py backend`);
      return;
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Create new AbortController
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      const result = await analyzeCode(code, {}, abortControllerRef.current.signal);
      setAnalysisResult(result);
    } catch (err) {
      // If request was cancelled, don't show error
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        return;
      }
      // Provide more detailed error information
      if (err.message?.includes('Network Error') || err.message?.includes('Unable to connect')) {
        setError(`Unable to connect to server (${getApiBaseUrl()}). Please ensure the backend is running: python run.py backend`);
      } else {
        setError(err.message || 'Analysis failed, please check code syntax');
      }
    } finally {
      setIsLoading(false);
    }
  }, [code, serverStatus.connected, analysisMode]);

  // Project analysis result callback
  const handleProjectResultChange = useCallback((result) => {
    setProjectResult(result);
  }, []);

  // Project analysis state change callback
  const handleProjectAnalysisStateChange = useCallback((isAnalyzing) => {
    setIsProjectAnalyzing(isAnalyzing);
    setIsLoading(isAnalyzing);
  }, []);

  // File selection callback (single click)
  const handleFileSelect = useCallback((fileAnalysis, index) => {
    setSelectedFile(fileAnalysis);
    setIsFileEditMode(false);
  }, []);

  // File double-click callback (enter edit mode)
  const handleFileDoubleClick = useCallback((fileAnalysis, index) => {
    setSelectedFile(fileAnalysis);
    setIsFileEditMode(true);
    // Set file content to editor (content is at fileAnalysis root level)
    if (fileAnalysis?.content) {
      setCode(fileAnalysis.content);
    }
  }, []);

  // Exit edit mode callback
  const handleExitEditMode = useCallback(() => {
    setIsFileEditMode(false);
    setSelectedFile(null);
  }, []);

  // Switch analysis mode
  const handleAnalysisModeChange = useCallback((mode) => {
    setAnalysisMode(mode);
    setError(null);
    // Clear previous results when switching modes
    if (mode === 'file') {
      setProjectResult(null);
    } else {
      setAnalysisResult(null);
    }
  }, []);

  const handleCodeChange = useCallback((newCode) => {
    setCode(newCode);
    setAnalysisResult(null);
    setError(null);
  }, []);
  
  /**
   * Jump to specified line in editor
   * @param {number} lineNumber - Line number (1-based)
   * @param {number} [endLine] - Optional end line number
   */
  const handleGoToLine = useCallback((lineNumber, endLine) => {
    if (editorRef.current) {
      editorRef.current.goToLine(lineNumber, 1, endLine);
    }
  }, []);

  /**
   * Navigate to challenges tab
   */
  const handleNavigateToChallenges = useCallback(() => {
    setActiveTab('challenges');
  }, []);

  // Gesture control toggle
  const handleGestureToggle = useCallback(() => {
    setGestureEnabled(prev => {
      const newValue = !prev;
      // Clear pointing cursor when disabling gesture control
      if (!newValue && visualizerRef.current && visualizerRef.current.clearPointingCursor) {
        visualizerRef.current.clearPointingCursor();
      }
      return newValue;
    });
  }, []);

  // Gesture callback - receives gesture data and forwards to visualizer
  const handleGesture = useCallback((gestureData) => {
    if (visualizerRef.current && visualizerRef.current.handleGesture) {
      visualizerRef.current.handleGesture(gestureData);
    }
    // Clear pointing cursor when not pointing (check isPointing flag for immediate feedback)
    // isPointing is true when raw gesture is Pointing_Up, even if stability filter hasn't confirmed
    if (!gestureData.isPointing && visualizerRef.current && visualizerRef.current.clearPointingCursor) {
      visualizerRef.current.clearPointingCursor();
    }
  }, []);

  // Two hands gesture callback - for pinch zoom
  const handleTwoHandsGesture = useCallback((twoHandsData) => {
    if (visualizerRef.current && visualizerRef.current.handleTwoHands) {
      visualizerRef.current.handleTwoHands(twoHandsData);
    }
  }, []);

  // Pointing direction callback - for gesture-based node selection
  const handlePointingDirection = useCallback((pointingData) => {
    if (visualizerRef.current && visualizerRef.current.handlePointingDirection) {
      visualizerRef.current.handlePointingDirection(pointingData);
    }
  }, []);

  // Toast notification helper
  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // Share functionality
  const handleShare = useCallback(() => {
    const compressed = compressCode(code);
    if (compressed) {
      const url = `${window.location.origin}${window.location.pathname}#code=${compressed}`;
      setShareUrl(url);
      setShowShareDialog(true);
    }
  }, [code]);

  const handleCopyShareUrl = useCallback(async () => {
    if (shareUrl) {
      try {
        await navigator.clipboard.writeText(shareUrl);
        showToast('Link copied to clipboard!', 'success');
      } catch (err) {
        showToast('Failed to copy link. Please copy manually.', 'error');
      }
    }
  }, [shareUrl, showToast]);

  // Export functionality
  const handleExport = useCallback((format) => {
    if (format === 'html') {
      const html = generateHTMLReport(analysisResult, code);
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pyvizast-report.html';
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === 'json') {
      const json = JSON.stringify(analysisResult, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pyvizast-analysis.json';
      a.click();
      URL.revokeObjectURL(url);
    }
    setShowExportDialog(false);
  }, [analysisResult, code]);

  return (
    <div className={`app ${theme}`}>
      {(isLoading || isProjectAnalyzing) && <LoadingOverlay progress={progress} />}
      
      {/* Toast Notification */}
      {toast && (
        <div className={`toast-notification toast-${toast.type}`}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {toast.type === 'success' ? (
              <>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </>
            ) : (
              <>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </>
            )}
          </svg>
          <span>{toast.message}</span>
        </div>
      )}
      
      <Header 
        onAnalyze={handleAnalyze}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        isLoading={isLoading || isProjectAnalyzing}
        theme={theme}
        onThemeChange={setTheme}
        analysisMode={analysisMode}
        onAnalysisModeChange={handleAnalysisModeChange}
        onShare={handleShare}
        onExport={() => setShowExportDialog(true)}
        canExport={!!analysisResult}
        gestureEnabled={gestureEnabled}
        onGestureToggle={handleGestureToggle}
      />
      
      {/* Share Dialog */}
      {showShareDialog && (
        <div className="share-dialog">
          <div className="share-dialog-header">
            <h4>Share Code</h4>
            <button className="btn btn-ghost btn-icon" onClick={() => setShowShareDialog(false)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div className="share-dialog-content">
            <p className="share-url-preview">{shareUrl}</p>
            <button className="btn btn-secondary share-copy-btn" onClick={handleCopyShareUrl}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy Link
            </button>
          </div>
        </div>
      )}
      
      {/* Export Dialog */}
      {showExportDialog && (
        <div className="export-dialog">
          <div className="export-dialog-header">
            <h4>Export Report</h4>
            <button className="btn btn-ghost btn-icon" onClick={() => setShowExportDialog(false)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div className="export-options">
            <button className="export-option" onClick={() => handleExport('html')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>HTML Report</span>
              <span className="format">.html</span>
            </button>
            <button className="export-option" onClick={() => handleExport('json')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </svg>
              <span>JSON Data</span>
              <span className="format">.json</span>
            </button>
          </div>
        </div>
      )}
      
      <div className="app-body">
        <Sidebar 
          isOpen={sidebarOpen}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          analysisResult={analysisResult}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
        
        {/* Learn tab content */}
        {activeTab === 'learn' ? (
          <main className="main-content learn-mode">
            <ErrorBoundary>
              <LearnView theme={theme} />
            </ErrorBoundary>
          </main>
        ) : activeTab === 'challenges' ? (
          /* Challenges tab content */
          <main className="main-content challenges-mode">
            <ErrorBoundary>
              <ChallengeView theme={theme} />
            </ErrorBoundary>
          </main>
        ) : analysisMode === 'project' ? (
          /* Project analysis mode */
          <main className="main-content project-mode" ref={mainContentRef}
            style={{ 
              '--split-position': `${splitPosition}%`,
              cursor: isDragging ? 'col-resize' : 'default'
            }}>
            <div className="project-left-panel" style={{ width: `calc(var(--split-position, 35%) - 4px)` }}>
              <ProjectAnalysisView
                ref={projectAnalysisRef}
                theme={theme}
                activeTab={activeTab}
                onAnalysisStateChange={handleProjectAnalysisStateChange}
                onResultChange={handleProjectResultChange}
                onFileSelect={handleFileSelect}
                onFileDoubleClick={handleFileDoubleClick}
                editedFilePath={selectedFile?.file?.relative_path}
                onProgressChange={setProgress}
              />
            </div>
            
            <div 
              className={`resize-divider ${isDragging ? 'dragging' : ''}`}
              onMouseDown={handleMouseDown}
            >
              <div className="resize-handle">
                <svg width="4" height="24" viewBox="0 0 4 24" fill="none">
                  <circle cx="2" cy="6" r="1" fill="currentColor" />
                  <circle cx="2" cy="12" r="1" fill="currentColor" />
                  <circle cx="2" cy="18" r="1" fill="currentColor" />
                </svg>
              </div>
            </div>
            
            <div className="visualization-panel">
              {/* Edit mode - show editor */}
              {isFileEditMode && selectedFile ? (
                <div className="project-edit-mode">
                  <div className="project-edit-header">
                    <button className="exit-edit-btn" onClick={handleExitEditMode} title="Exit edit">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                    <div className="edit-file-info">
                      <span className="edit-file-name">{selectedFile?.file?.relative_path?.split('/').pop() || 'File'}</span>
                      <span className="edit-file-path">{selectedFile?.file?.relative_path}</span>
                    </div>
                  </div>
                  <div className="project-edit-content">
                    <CodeEditor 
                      ref={editorRef}
                      code={code}
                      onChange={handleCodeChange}
                      theme={theme}
                    />
                  </div>
                </div>
              ) : (
                <>
                  {!serverStatus.checking && !serverStatus.connected && (
                    <div className="server-status-error">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                        <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                        <line x1="6" y1="6" x2="6.01" y2="6" />
                        <line x1="6" y1="18" x2="6.01" y2="18" />
                      </svg>
                      <div className="status-content">
                        <strong>Unable to connect to backend server</strong>
                        <p>API URL: {getApiBaseUrl()}</p>
                        <p className="status-hint">Please run in terminal: <code>python run.py backend</code></p>
                      </div>
                    </div>
                  )}
                  
                  {error && (
                    <div className="error-message error-detailed">
                      <div className="error-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                      </div>
                      <div className="error-content">
                        <div className="error-title">Analysis Error</div>
                        <div className="error-text">{error}</div>
                        <div className="error-hint">
                          Tip: Check your Python code syntax, or try with a simpler example.
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <ErrorBoundary>
                    {projectResult ? (
                      activeTab === 'ast' ? (
                        <ProjectVisualization 
                          projectResult={projectResult}
                          theme={theme}
                          viewMode={viewMode}
                        />
                      ) : (
                        <Suspense fallback={<ComponentLoader />}>
                          <AnalysisPanel 
                            result={{
                              issues: [
                                ...(projectResult.global_issues || []),
                                ...(projectResult.files?.flatMap(f => f.issues || []) || [])
                              ],
                              suggestions: projectResult.files?.flatMap(f => f.suggestions || []) || [],
                              performance_hotspots: projectResult.files?.flatMap(f => f.performance_hotspots || []) || [],
                              complexity: {
                                cyclomatic_complexity: projectResult.metrics?.avg_complexity || 0,
                                cognitive_complexity: 0,
                                maintainability_index: projectResult.metrics?.avg_maintainability || 0,
                                max_nesting_depth: 0,
                                lines_of_code: projectResult.metrics?.total_lines || 0,
                                function_count: projectResult.metrics?.total_functions || 0,
                                class_count: projectResult.metrics?.total_classes || 0,
                                avg_function_length: 0,
                                halstead_volume: 0,
                                halstead_difficulty: 0,
                              },
                              summary: {
                                total_issues: (projectResult.global_issues?.length || 0) + 
                                  (projectResult.files?.reduce((sum, f) => sum + (f.summary?.issue_count || 0), 0) || 0),
                                project_stats: projectResult.metrics
                              }
                            }}
                            activeTab={activeTab}
                            code=""
                            onApplyPatch={() => {}}
                            onNavigateToChallenges={handleNavigateToChallenges}
                            projectMode={true}
                            projectResult={projectResult}
                          />
                        </Suspense>
                      )
                    ) : (
                      <div className="placeholder">
                        <div className="placeholder-icon">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                          </svg>
                        </div>
                        <h3>Project Analysis</h3>
                        <p>Upload a ZIP file and click Analyze to begin</p>
                        <p className="placeholder-hint">
                          Dependency graph, circular dependency detection, unused exports
                        </p>
                      </div>
                    )}
                  </ErrorBoundary>
                </>
              )}
            </div>
          </main>
        ) : (
        /* Single file analysis mode */
        <main 
          className="main-content" 
          ref={mainContentRef}
          style={{ 
            '--split-position': `${splitPosition}%`,
            cursor: isDragging ? 'col-resize' : 'default'
          }}
        >
          <div className="editor-panel">
            <CodeEditor 
              ref={editorRef}
              code={code}
              onChange={handleCodeChange}
              theme={theme}
            />
          </div>
          
          {/* Draggable splitter */}
          <div 
            className={`resize-divider ${isDragging ? 'dragging' : ''}`}
            onMouseDown={handleMouseDown}
          >
            <div className="resize-handle">
              <svg width="4" height="24" viewBox="0 0 4 24" fill="none">
                <circle cx="2" cy="6" r="1" fill="currentColor" />
                <circle cx="2" cy="12" r="1" fill="currentColor" />
                <circle cx="2" cy="18" r="1" fill="currentColor" />
              </svg>
            </div>
          </div>
          
          <div className="visualization-panel">
            {/* Server connection status */}
            {!serverStatus.checking && !serverStatus.connected && (
              <div className="server-status-error">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                  <line x1="6" y1="6" x2="6.01" y2="6" />
                  <line x1="6" y1="18" x2="6.01" y2="18" />
                </svg>
                <div className="status-content">
                  <strong>Unable to connect to backend server</strong>
                  <p>API URL: {getApiBaseUrl()}</p>
                  <p className="status-hint">Please run in terminal: <code>python run.py backend</code></p>
                </div>
              </div>
            )}
            
            {error && (
              <div className="error-message">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}
            
            <ErrorBoundary>
              {analysisResult ? (
                activeTab === 'ast' ? (
                  <Suspense fallback={<ComponentLoader />}>
                    {viewMode === '3d' ? (
                      <ASTVisualizer3D 
                        ref={visualizerRef}
                        graph={analysisResult.ast_graph}
                        theme={theme}
                        onGoToLine={handleGoToLine}
                        gestureEnabled={gestureEnabled}
                      />
                    ) : (
                      <ASTVisualizer 
                        ref={visualizerRef}
                        graph={analysisResult.ast_graph}
                        theme={theme}
                        onGoToLine={handleGoToLine}
                        gestureEnabled={gestureEnabled}
                      />
                    )}
                  </Suspense>
                ) : (
                  <Suspense fallback={<ComponentLoader />}>
                    <AnalysisPanel 
                      result={analysisResult}
                      activeTab={activeTab}
                      code={code}
                      onApplyPatch={handleCodeChange}
                      onNavigateToChallenges={handleNavigateToChallenges}
                    />
                  </Suspense>
                )
              ) : (
                <div className="placeholder">
                  <div className="placeholder-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                  </div>
                  <h3>PyVizAST</h3>
                  <p>Enter Python code and click Analyze to begin</p>
                  <p className="placeholder-hint">
                    AST visualization, complexity analysis, performance detection, security scanning
                  </p>
                </div>
              )}
            </ErrorBoundary>
          </div>
        </main>
        )}
      </div>
      
      {/* Gesture Control Overlay */}
      <GestureControl
        ref={gestureControlRef}
        enabled={gestureEnabled}
        onGesture={handleGesture}
        onTwoHands={handleTwoHandsGesture}
        onPointingDirection={handlePointingDirection}
        theme={theme}
        showGuide={true}
        compact={false}
      />
    </div>
  );
}

export default App;