import React, { useState, useCallback, useEffect, useRef, Suspense, lazy } from 'react';
import CodeEditor from './components/CodeEditor';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoadingOverlay from './components/LoadingOverlay';
import ErrorBoundary from './components/ErrorBoundary';
import ProjectAnalysisView from './components/ProjectAnalysisView';
import ProjectVisualization from './components/ProjectVisualization';
import { analyzeCode, checkServerHealth, getApiBaseUrl } from './api';
import { setupGlobalErrorHandlers } from './utils/logger';
import './App.css';
import './components/components.css';
import './components/AnalysisPanel.css';

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
  
  // Project analysis state
  const [projectResult, setProjectResult] = useState(null);
  const [isProjectAnalyzing, setIsProjectAnalyzing] = useState(false);
  const projectAnalysisRef = useRef(null);
  
  // Selected file in project mode
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileIndex, setSelectedFileIndex] = useState(null);
  const [isFileEditMode, setIsFileEditMode] = useState(false);
  
  // Splitter drag state
  const [splitPosition, setSplitPosition] = useState(50); // Percentage
  const [isDragging, setIsDragging] = useState(false);
  const mainContentRef = useRef(null);
  
  // AbortController for canceling requests
  const abortControllerRef = useRef(null);
  
  // Editor ref for calling editor methods (e.g., jump to line)
  const editorRef = useRef(null);
  
  // Initialize global error handlers
  useEffect(() => {
    setupGlobalErrorHandlers();
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
    setSelectedFileIndex(index);
    setIsFileEditMode(false);
  }, []);

  // File double-click callback (enter edit mode)
  const handleFileDoubleClick = useCallback((fileAnalysis, index) => {
    setSelectedFile(fileAnalysis);
    setSelectedFileIndex(index);
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
    setSelectedFileIndex(null);
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

  return (
    <div className={`app ${theme}`}>
      {(isLoading || isProjectAnalyzing) && <LoadingOverlay />}
      
      <Header 
        onAnalyze={handleAnalyze}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        isLoading={isLoading || isProjectAnalyzing}
        theme={theme}
        onThemeChange={setTheme}
        analysisMode={analysisMode}
        onAnalysisModeChange={handleAnalysisModeChange}
      />
      
      <div className="app-body">
        <Sidebar 
          isOpen={sidebarOpen}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          analysisResult={analysisResult}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
        
        {/* Project analysis mode */}
        {analysisMode === 'project' ? (
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
                        graph={analysisResult.ast_graph}
                        theme={theme}
                        onGoToLine={handleGoToLine}
                      />
                    ) : (
                      <ASTVisualizer 
                        graph={analysisResult.ast_graph}
                        theme={theme}
                        onGoToLine={handleGoToLine}
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
    </div>
  );
}

export default App;