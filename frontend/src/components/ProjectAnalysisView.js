import React, { useState, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { analyzeProject, uploadProject } from '../api';
import './ProjectAnalysisView.css';

/**
 * 项目分析视图组件
 * 显示在左侧面板，负责：
 * 1. 上传区域（未上传时）
 * 2. 文件列表预览（上传后）
 * 
 * 单击文件：选中并显示分析
 * 双击文件：进入编辑模式
 */
const ProjectAnalysisView = forwardRef(function ProjectAnalysisView(
  { 
    theme, 
    activeTab, 
    onAnalysisStateChange, 
    onResultChange, 
    onFileSelect,
    onFileDoubleClick,  // 双击进入编辑模式
    isEditMode = false,  // 是否处于编辑模式
    editedFilePath = null, // 当前编辑的文件路径
    hasUnsavedChanges = false, // 是否有未保存的更改
    onSaveFile,  // 保存文件回调
  }, 
  ref
) {
  // 上传状态
  const [uploadedFile, setUploadedFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  
  // 分析状态
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  
  // UI 状态
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [quickMode, setQuickMode] = useState(false);
  const [selectedFileIndex, setSelectedFileIndex] = useState(null);

  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    analyze: async () => {
      if (!uploadedFile) {
        setError('请先上传项目文件');
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

  // 执行完整分析
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
      const result = await analyzeProject(
        uploadedFile,
        quickMode,
        abortControllerRef.current.signal
      );
      
      setAnalysisResult(result);
      
      // 通知父组件结果变化
      if (onResultChange) {
        onResultChange(result);
      }
    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        return;
      }
      setError(err.message || '分析失败');
    } finally {
      setIsAnalyzing(false);
      if (onAnalysisStateChange) {
        onAnalysisStateChange(false);
      }
    }
  }, [uploadedFile, quickMode, onAnalysisStateChange, onResultChange]);

  // 处理文件选择
  const handleFileSelect = useCallback(async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('请上传 .zip 格式的项目压缩包');
      return;
    }

    setIsUploading(true);
    setError(null);
    setScanResult(null);
    setAnalysisResult(null);
    setSelectedFileIndex(null);

    // 通知父组件清除结果和选中的文件
    if (onResultChange) {
      onResultChange(null);
    }
    if (onFileSelect) {
      onFileSelect(null, null);
    }

    try {
      const result = await uploadProject(file);
      
      setUploadedFile(file);
      setScanResult(result);
    } catch (err) {
      setError(err.message || '上传失败');
    } finally {
      setIsUploading(false);
    }
  }, [onResultChange, onFileSelect]);

  // 清除文件
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
      setError('分析已取消');
    }
  }, []);

  // 处理文件单击（选中）
  const handleFileClick = useCallback((index, path) => {
    // 如果在编辑模式，不响应单击
    if (isEditMode) return;
    
    setSelectedFileIndex(index);
    
    // 如果已经有分析结果，通知父组件选中的文件
    if (analysisResult && onFileSelect) {
      const fileAnalysis = analysisResult.files?.find(f => f.file.path === path);
      if (fileAnalysis) {
        onFileSelect(fileAnalysis, index);
      }
    }
  }, [analysisResult, onFileSelect, isEditMode]);

  // 处理文件双击（进入编辑模式）
  const handleFileDoubleClick = useCallback((index, path) => {
    setSelectedFileIndex(index);
    
    // 通知父组件进入编辑模式
    if (analysisResult && onFileDoubleClick) {
      const fileAnalysis = analysisResult.files?.find(f => f.file.path === path);
      if (fileAnalysis) {
        onFileDoubleClick(fileAnalysis, index);
      }
    }
  }, [analysisResult, onFileDoubleClick]);

  // 渲染上传区域
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
          <h3>上传 Python 项目</h3>
          <p>拖拽或点击选择 ZIP 文件</p>
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
            {isUploading ? '上传中...' : '选择文件'}
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

  // 渲染文件列表
  return (
    <div className="project-file-panel">
      {/* 头部 */}
      <div className="panel-header">
        <div className="project-name">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span>{uploadedFile.name}</span>
        </div>
        <button className="clear-button" onClick={handleClearFile} title="重新选择">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* 快速模式选项 */}
      <div className="panel-options">
        <label className="quick-mode-toggle">
          <input
            type="checkbox"
            checked={quickMode}
            onChange={(e) => setQuickMode(e.target.checked)}
          />
          <span>快速模式</span>
        </label>
      </div>

      {/* 文件统计 */}
      {scanResult && (
        <div className="file-stats">
          <span className="stat">{scanResult.total_files} 个 Python 文件</span>
          {scanResult.skipped_count > 0 && (
            <span className="stat skipped">{scanResult.skipped_count} 个已跳过</span>
          )}
        </div>
      )}

      {/* 分析中状态 */}
      {isAnalyzing && (
        <div className="analyzing-indicator">
          <div className="loader-spinner small"></div>
          <span>正在分析...</span>
          <button className="cancel-btn" onClick={handleCancel}>取消</button>
        </div>
      )}

      {/* 错误提示 */}
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

      {/* 文件列表 */}
      {scanResult && (
        <div className="file-tree">
          <div className="file-tree-header">
            <span>文件列表</span>
            <div className="file-tree-header-actions">
              {analysisResult && <span className="hint">单击查看 · 双击编辑</span>}
              {hasUnsavedChanges && onSaveFile && (
                <button 
                  className="save-btn small"
                  onClick={onSaveFile}
                  title="保存更改"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                    <polyline points="17 21 17 13 7 13 7 21" />
                    <polyline points="7 3 7 8 15 8" />
                  </svg>
                  保存
                </button>
              )}
            </div>
          </div>
          <div className="file-tree-content">
            {scanResult.file_paths?.map((path, index) => {
              const fileAnalysis = analysisResult?.files?.find(f => f.file.path === path);
              const issueCount = fileAnalysis?.summary?.issue_count || 0;
              const complexity = fileAnalysis?.summary?.cyclomatic_complexity;
              const isEditing = editedFilePath === path;
              
              return (
                <div 
                  key={index} 
                  className={`file-tree-item ${selectedFileIndex === index ? 'selected' : ''} ${analysisResult ? 'clickable' : ''} ${isEditing ? 'editing' : ''}`}
                  onClick={() => analysisResult && handleFileClick(index, path)}
                  onDoubleClick={() => analysisResult && handleFileDoubleClick(index, path)}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span className="file-name">{path}</span>
                  {isEditing && <span className="edit-badge">编辑中</span>}
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

      {/* 分析提示 */}
      {scanResult && !analysisResult && !isAnalyzing && (
        <div className="analyze-hint-compact">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>点击 Analyze 开始分析</span>
        </div>
      )}
    </div>
  );
});

export default ProjectAnalysisView;