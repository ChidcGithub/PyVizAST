import React, { useState, useCallback, useRef, forwardRef, useImperativeHandle, useEffect } from 'react';
import { analyzeProject } from '../api';
import './ProjectAnalysisView.css';

/**
 * Project Analysis View Component
 * Displays in the left panel, responsible for:
 * 1. Upload area (when not uploaded)
 * 2. File list preview (after upload)
 * 
 * Single click on file: select
 * Click again on selected file: enter edit mode
 */
const ProjectAnalysisView = forwardRef(function ProjectAnalysisView(
  { 
    theme, 
    activeTab, 
    onAnalysisStateChange, 
    onResultChange, 
    onFileSelect,
    onFileDoubleClick,  // Enter edit mode callback
    editedFilePath = null, // Currently edited file path
    hasUnsavedChanges = false, // Whether there are unsaved changes
    onSaveFile,  // Save file callback
  }, 
  ref
) {
  // Upload state
  const [uploadedFile, setUploadedFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  
  // Analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  
  // UI state
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [quickMode, setQuickMode] = useState(false);
  const [selectedFileIndex, setSelectedFileIndex] = useState(null);

  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);
  
  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      // Cancel ongoing requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    analyze: async () => {
      if (!uploadedFile) {
        setError('Please upload a project file first');
        return;
      }
      await performAnalysis();
    },
    canAnalyze: () => !!uploadedFile && !isAnalyzing,
    getState: () => ({
      hasFile: !!uploadedFile,
      hasScanResult: !!scanResult,
      hasAnalysisResult: !!analysisResult,
      isAnalyzing,
      isUploading
    })
  }));

  // Perform full analysis (upload and analyze in one step)
  const performAnalysis = useCallback(async () => {
    if (!uploadedFile) return;

    setIsAnalyzing(true);
    setError(null);

    if (onAnalysisStateChange) {
      onAnalysisStateChange(true);
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      // Directly call analyzeProject, complete upload and analysis in one step
      const result = await analyzeProject(
        uploadedFile,
        quickMode,
        abortControllerRef.current.signal
      );
      
      setAnalysisResult(result);
      
      // Extract scan info from analysis result
      if (result.scan_result) {
        setScanResult({
          total_files: result.scan_result.total_files,
          file_paths: result.scan_result.file_paths,
          skipped_count: result.scan_result.skipped_count,
        });
      }
      
      // Notify parent component of result change
      if (onResultChange) {
        onResultChange(result);
      }
    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        return;
      }
      setError(err.message || 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
      if (onAnalysisStateChange) {
        onAnalysisStateChange(false);
      }
    }
  }, [uploadedFile, quickMode, onAnalysisStateChange, onResultChange]);

  // Handle file selection
  const handleFileSelect = useCallback(async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Please upload a .zip format project archive');
      return;
    }

    // Clear previous state
    setError(null);
    setScanResult(null);
    setAnalysisResult(null);
    setSelectedFileIndex(null);
    setUploadedFile(file);

    // Notify parent component to clear results and selected file
    if (onResultChange) {
      onResultChange(null);
    }
    if (onFileSelect) {
      onFileSelect(null, null);
    }
  }, [onResultChange, onFileSelect]);

  // Clear file
  const handleClearFile = useCallback(() => {
    setUploadedFile(null);
    setScanResult(null);
    setAnalysisResult(null);
    setError(null);
    setSelectedFileIndex(null);
    
    if (onResultChange) {
      onResultChange(null);
    }
    if (onFileSelect) {
      onFileSelect(null, null);
    }
  }, [onResultChange, onFileSelect]);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();

    const file = event.dataTransfer.files?.[0];
    if (file) {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      if (fileInputRef.current) {
        fileInputRef.current.files = dataTransfer.files;
        fileInputRef.current.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsAnalyzing(false);
      setError('Analysis cancelled');
    }
  }, []);

  // Handle file click (single click to select, click again to edit)
  const handleFileClick = useCallback((index, path) => {
    // If clicking on already selected file, enter edit mode
    if (selectedFileIndex === index && analysisResult && onFileDoubleClick) {
      const fileAnalysis = analysisResult.files?.find(f => f.file?.relative_path === path);
      if (fileAnalysis) {
        onFileDoubleClick(fileAnalysis, index);
      }
      return;
    }
    
    // Otherwise select the file
    setSelectedFileIndex(index);
    
    // Notify parent component of selected file
    if (analysisResult && onFileSelect) {
      const fileAnalysis = analysisResult.files?.find(f => f.file?.relative_path === path);
      if (fileAnalysis) {
        onFileSelect(fileAnalysis, index);
      }
    }
  }, [analysisResult, onFileSelect, onFileDoubleClick, selectedFileIndex]);

  // Render upload area
  if (!uploadedFile) {
    return (
      <div className="project-upload-panel">
        <div 
          className="upload-area-compact"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <div className="upload-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <h3>Upload Python Project</h3>
          <p>Drag and drop or click to select a ZIP file</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <button 
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? 'Uploading...' : 'Select File'}
          </button>
        </div>

        {error && (
          <div className="error-message-compact">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </div>
        )}
      </div>
    );
  }

  // Render file list
  return (
    <div className="project-file-panel">
      {/* Header */}
      <div className="panel-header">
        <div className="project-name">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span>{uploadedFile.name}</span>
        </div>
        <div className="panel-header-actions">
          {hasUnsavedChanges && onSaveFile && (
            <button 
              className="save-btn-header"
              onClick={onSaveFile}
              title="Save changes"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                <polyline points="17 21 17 13 7 13 7 21" />
                <polyline points="7 3 7 8 15 8" />
              </svg>
            </button>
          )}
          <button className="clear-button" onClick={handleClearFile} title="Reselect">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Quick mode option */}
      <div className="panel-options">
        <label className="quick-mode-toggle">
          <input
            type="checkbox"
            checked={quickMode}
            onChange={(e) => setQuickMode(e.target.checked)}
          />
          <span>Quick Mode</span>
        </label>
      </div>

      {/* File statistics */}
      {scanResult && (
        <div className="file-stats">
          <span className="stat">{scanResult.total_files} Python files</span>
          {scanResult.skipped_count > 0 && (
            <span className="stat skipped">{scanResult.skipped_count} skipped</span>
          )}
        </div>
      )}

      {/* Analyzing state */}
      {isAnalyzing && (
        <div className="analyzing-indicator">
          <div className="loader-spinner small"></div>
          <span>Analyzing...</span>
          <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="error-message-compact">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {/* File list */}
      {scanResult && (
        <div className="file-tree">
          <div className="file-tree-header">
            <span>File List</span>
            <div className="file-tree-header-actions">
              {analysisResult && <span className="hint">Click to select · Click again to edit</span>}
            </div>
          </div>
          <div className="file-tree-content">
            {scanResult.file_paths?.map((path, index) => {
              const fileAnalysis = analysisResult?.files?.find(f => f.file?.relative_path === path);
              const issueCount = fileAnalysis?.summary?.issue_count || 0;
              const complexity = fileAnalysis?.summary?.cyclomatic_complexity;
              const isSelected = selectedFileIndex === index;
              
              return (
                <div 
                  key={index} 
                  className={`file-tree-item ${isSelected ? 'selected' : ''} ${analysisResult ? 'clickable' : ''}`}
                  onClick={() => analysisResult && handleFileClick(index, path)}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span className="file-name">{path}</span>
                  {analysisResult && (
                    <span className="file-info">
                      {complexity !== undefined && (
                        <span className="complexity-badge">C:{complexity}</span>
                      )}
                      {issueCount > 0 && (
                        <span className="issue-badge">{issueCount}</span>
                      )}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Analysis hint */}
      {uploadedFile && !analysisResult && !isAnalyzing && (
        <div className="analyze-hint-compact">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>Click Analyze to start analysis</span>
        </div>
      )}
    </div>
  );
});

export default ProjectAnalysisView;
