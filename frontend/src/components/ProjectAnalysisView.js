import React, { useState, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { analyzeProject, uploadProject } from '../api';
import './ProjectAnalysisView.css';

/**
 * 项目分析视图组件
 * 支持上传 zip 文件，展示项目分析结果
 * 
 * 工作流程：
 * 1. 用户上传 zip 文件 -> 调用 uploadProject 扫描文件
 * 2. 显示文件列表概览
 * 3. 用户点击 Analyze -> 调用 analyzeProject 进行完整分析
 * 4. 显示分析结果
 */
const ProjectAnalysisView = forwardRef(function ProjectAnalysisView({ theme, onAnalysisStateChange }, ref) {
  // 上传状态
  const [uploadedFile, setUploadedFile] = useState(null);  // 已上传的文件对象
  const [scanResult, setScanResult] = useState(null);       // 扫描结果（文件列表）
  
  // 分析状态
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);  // 完整分析结果
  
  // UI 状态
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('summary');
  const [expandedFile, setExpandedFile] = useState(null);
  const [quickMode, setQuickMode] = useState(false);

  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    // 执行分析
    analyze: async () => {
      if (!uploadedFile) {
        setError('请先上传项目文件');
        return;
      }
      await performAnalysis();
    },
    // 检查是否可以分析
    canAnalyze: () => !!uploadedFile && !isAnalyzing,
    // 获取当前状态
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

    // 通知父组件分析状态变化
    if (onAnalysisStateChange) {
      onAnalysisStateChange(true);
    }

    // 取消之前的请求
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
  }, [uploadedFile, quickMode, onAnalysisStateChange]);

  // 处理文件选择（仅上传扫描）
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

    try {
      // 先上传并扫描文件
      const result = await uploadProject(file);
      
      setUploadedFile(file);
      setScanResult(result);
    } catch (err) {
      setError(err.message || '上传失败');
    } finally {
      setIsUploading(false);
    }
  }, []);

  // 删除已上传的文件，返回上传界面
  const handleClearFile = useCallback(() => {
    setUploadedFile(null);
    setScanResult(null);
    setAnalysisResult(null);
    setError(null);
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();

    const file = event.dataTransfer.files?.[0];
    if (file) {
      // 创建一个新的 change 事件
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

  const formatNumber = (num) => {
    if (typeof num !== 'number') return '0';
    return num.toLocaleString();
  };

  const getSeverityClass = (severity) => {
    const map = {
      critical: 'severity-critical',
      error: 'severity-error',
      warning: 'severity-warning',
      info: 'severity-info',
    };
    return map[severity] || 'severity-info';
  };

  const getIssueTypeLabel = (type) => {
    const labels = {
      circular_dependency: '循环依赖',
      unused_export: '未使用导出',
      duplicate_code: '重复代码',
    };
    return labels[type] || type;
  };

  const getHealthGradeClass = (grade) => {
    const classes = {
      A: 'grade-a',
      B: 'grade-b',
      C: 'grade-c',
      D: 'grade-d',
      F: 'grade-f',
    };
    return classes[grade] || '';
  };

  // 渲染摘要卡片
  const renderSummary = () => {
    if (!analysisResult) return null;

    const summary = analysisResult.summary || {};
    const healthScore = summary.health_score || { score: 0, grade: 'F', factors: [] };

    return (
      <div className="summary-section">
        {/* 健康评分卡片 */}
        <div className="health-score-card">
          <div className={`health-score-circle ${getHealthGradeClass(healthScore.grade)}`}>
            <span className="health-score-value">{healthScore.score}</span>
            <span className="health-score-grade">{healthScore.grade}</span>
          </div>
          <div className="health-factors">
            <h4>评分因素</h4>
            {healthScore.factors?.map((factor, index) => (
              <div key={index} className={`health-factor ${factor.impact > 0 ? 'positive' : 'negative'}`}>
                <span className="factor-name">{factor.name}</span>
                <span className="factor-impact">{factor.impact > 0 ? '+' : ''}{factor.impact.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">📄</div>
            <div className="stat-value">{formatNumber(summary.total_files)}</div>
            <div className="stat-label">文件数</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📝</div>
            <div className="stat-value">{formatNumber(summary.total_lines)}</div>
            <div className="stat-label">代码行数</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">⚡</div>
            <div className="stat-value">{summary.avg_cyclomatic_complexity?.toFixed(1) || '0'}</div>
            <div className="stat-label">平均复杂度</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔧</div>
            <div className="stat-value">{formatNumber(summary.total_functions)}</div>
            <div className="stat-label">函数数</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📦</div>
            <div className="stat-value">{formatNumber(summary.total_classes)}</div>
            <div className="stat-label">类数</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔗</div>
            <div className="stat-value">{formatNumber(summary.internal_dependencies)}</div>
            <div className="stat-label">内部依赖</div>
          </div>
        </div>

        {/* 问题统计 */}
        <div className="issues-summary">
          <h4>问题统计</h4>
          <div className="issues-stats">
            {summary.critical_issues > 0 && (
              <span className="issue-stat critical">{summary.critical_issues} 严重</span>
            )}
            {summary.error_issues > 0 && (
              <span className="issue-stat error">{summary.error_issues} 错误</span>
            )}
            {summary.warning_issues > 0 && (
              <span className="issue-stat warning">{summary.warning_issues} 警告</span>
            )}
            {summary.info_issues > 0 && (
              <span className="issue-stat info">{summary.info_issues} 提示</span>
            )}
            {summary.total_issues === 0 && (
              <span className="issue-stat none">没有发现问题</span>
            )}
          </div>
        </div>

        {/* 排名 */}
        {summary.most_complex_files?.length > 0 && (
          <div className="ranking-section">
            <h4>最复杂的文件</h4>
            <div className="ranking-list">
              {summary.most_complex_files.map((file, index) => (
                <div key={index} className="ranking-item">
                  <span className="ranking-position">#{file.rank}</span>
                  <span className="ranking-file">{file.file_path}</span>
                  <span className="ranking-value">{file.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // 渲染文件列表
  const renderFiles = () => {
    if (!analysisResult?.files) return null;

    return (
      <div className="files-section">
        <div className="files-header">
          <h4>文件列表 ({analysisResult.files.length} 个文件)</h4>
        </div>
        <div className="files-list">
          {analysisResult.files.map((fileAnalysis, index) => (
            <div key={index} className="file-item">
              <div 
                className="file-header"
                onClick={() => setExpandedFile(expandedFile === index ? null : index)}
              >
                <span className="file-expand-icon">
                  {expandedFile === index ? '▼' : '▶'}
                </span>
                <span className="file-path">{fileAnalysis.file.path}</span>
                <span className="file-stats">
                  {fileAnalysis.summary.line_count} 行 | 
                  复杂度 {fileAnalysis.summary.cyclomatic_complexity} |
                  {fileAnalysis.summary.issue_count > 0 && (
                    <span className="file-issues"> {fileAnalysis.summary.issue_count} 个问题</span>
                  )}
                </span>
              </div>
              {expandedFile === index && (
                <div className="file-details">
                  <div className="file-metrics">
                    <div className="metric">
                      <span className="metric-label">圈复杂度</span>
                      <span className="metric-value">{fileAnalysis.summary.cyclomatic_complexity}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">认知复杂度</span>
                      <span className="metric-value">{fileAnalysis.summary.cognitive_complexity}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">函数数</span>
                      <span className="metric-value">{fileAnalysis.summary.function_count}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">类数</span>
                      <span className="metric-value">{fileAnalysis.summary.class_count}</span>
                    </div>
                  </div>
                  {fileAnalysis.issues?.length > 0 && (
                    <div className="file-issues-list">
                      <h5>问题 ({fileAnalysis.issues.length})</h5>
                      {fileAnalysis.issues.slice(0, 10).map((issue, i) => (
                        <div key={i} className={`issue-item ${getSeverityClass(issue.severity)}`}>
                          <span className="issue-severity">{issue.severity}</span>
                          <span className="issue-message">{issue.message}</span>
                          {issue.lineno && <span className="issue-line">行 {issue.lineno}</span>}
                        </div>
                      ))}
                      {fileAnalysis.issues.length > 10 && (
                        <div className="more-issues">还有 {fileAnalysis.issues.length - 10} 个问题...</div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 渲染全局问题
  const renderGlobalIssues = () => {
    if (!analysisResult?.global_issues) return null;

    const issuesByType = analysisResult.global_issues.reduce((acc, issue) => {
      const type = issue.issue_type;
      if (!acc[type]) acc[type] = [];
      acc[type].push(issue);
      return acc;
    }, {});

    return (
      <div className="global-issues-section">
        <h4>全局问题 ({analysisResult.global_issues.length} 个)</h4>
        {Object.entries(issuesByType).map(([type, issues]) => (
          <div key={type} className="issue-type-group">
            <h5>{getIssueTypeLabel(type)} ({issues.length})</h5>
            <div className="issue-type-list">
              {issues.map((issue, index) => (
                <div key={index} className={`global-issue-item ${getSeverityClass(issue.severity)}`}>
                  <div className="issue-header">
                    <span className="issue-severity">{issue.severity}</span>
                    <span className="issue-message">{issue.message}</span>
                  </div>
                  {issue.locations?.length > 0 && (
                    <div className="issue-locations">
                      {issue.locations.map((loc, i) => (
                        <span key={i} className="issue-location">
                          {loc.file_path}{loc.line ? `:${loc.line}` : ''}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // 渲染依赖图
  const renderDependencies = () => {
    if (!analysisResult?.dependencies) return null;

    const deps = analysisResult.dependencies;

    return (
      <div className="dependencies-section">
        <h4>依赖分析</h4>
        
        {/* 外部依赖 */}
        {deps.external?.length > 0 && (
          <div className="dep-group">
            <h5>外部依赖 ({deps.external.length})</h5>
            <div className="dep-list">
              {deps.external.map((dep, index) => (
                <span key={index} className="dep-tag external">{dep}</span>
              ))}
            </div>
          </div>
        )}

        {/* 内部依赖图 */}
        {Object.keys(deps.dependency_graph || {}).length > 0 && (
          <div className="dep-group">
            <h5>内部依赖关系</h5>
            <div className="dependency-graph">
              {Object.entries(deps.dependency_graph).map(([file, dependencies], index) => (
                dependencies.length > 0 && (
                  <div key={index} className="dependency-row">
                    <span className="dep-source">{file}</span>
                    <span className="dep-arrow">→</span>
                    <span className="dep-targets">
                      {dependencies.map((d, i) => (
                        <span key={i} className="dep-tag internal">{d}</span>
                      ))}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>
        )}

        {/* 循环依赖警告 */}
        {analysisResult.global_issues?.some(i => i.issue_type === 'circular_dependency') && (
          <div className="circular-deps-warning">
            <span className="warning-icon">⚠️</span>
            <span>检测到循环依赖，请查看全局问题详情</span>
          </div>
        )}
      </div>
    );
  };

  // 渲染文件预览（上传后、分析前）
  const renderFilePreview = () => {
    if (!scanResult) return null;

    return (
      <div className="file-preview-container">
        <div className="preview-header">
          <button className="back-button" onClick={handleClearFile}>
            ← 重新选择
          </button>
          <h3>{uploadedFile?.name || '项目预览'}</h3>
        </div>
        
        <div className="preview-content">
          <div className="preview-stats">
            <div className="preview-stat">
              <span className="stat-value">{scanResult.total_files}</span>
              <span className="stat-label">Python 文件</span>
            </div>
            {scanResult.skipped_count > 0 && (
              <div className="preview-stat skipped">
                <span className="stat-value">{scanResult.skipped_count}</span>
                <span className="stat-label">已跳过</span>
              </div>
            )}
          </div>
          
          <div className="preview-files-list">
            <h4>文件列表</h4>
            <div className="files-preview">
              {scanResult.file_paths?.map((path, index) => (
                <div key={index} className="file-preview-item">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span>{path}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="preview-options">
            <label className="quick-mode-toggle">
              <input
                type="checkbox"
                checked={quickMode}
                onChange={(e) => setQuickMode(e.target.checked)}
              />
              <span>快速模式（仅复杂度分析）</span>
            </label>
          </div>

          <div className="analyze-hint">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>点击右上角 "Analyze" 按钮开始分析</span>
          </div>

          {isAnalyzing && (
            <div className="analyzing-overlay">
              <div className="analyzing-content">
                <div className="loader-spinner"></div>
                <span>正在分析项目...</span>
                <button className="cancel-button" onClick={handleCancel}>
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`project-analysis-view ${theme}`}>
      {/* 上传区域 - 居中显示 */}
      {!uploadedFile && (
        <div 
          className="upload-area"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <div className="upload-content">
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <h3>上传 Python 项目</h3>
            <p>拖拽 zip 文件到此处，或点击选择文件</p>
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
              {isUploading ? '上传中...' : '选择 zip 文件'}
            </button>
          </div>
        </div>
      )}

      {/* 错误提示 */}
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

      {/* 文件预览（上传后、分析前） */}
      {uploadedFile && !analysisResult && renderFilePreview()}

      {/* 分析结果 */}
      {analysisResult && (
        <div className="analysis-result">
          {/* 项目名称和返回按钮 */}
          <div className="result-header">
            <button className="back-button" onClick={handleClearFile}>
              ← 上传新项目
            </button>
            <h3>{analysisResult.project_name || '项目分析结果'}</h3>
          </div>

          {/* 导航标签 */}
          <div className="section-tabs">
            <button 
              className={activeSection === 'summary' ? 'active' : ''}
              onClick={() => setActiveSection('summary')}
            >
              摘要
            </button>
            <button 
              className={activeSection === 'files' ? 'active' : ''}
              onClick={() => setActiveSection('files')}
            >
              文件 ({analysisResult.files?.length || 0})
            </button>
            <button 
              className={activeSection === 'issues' ? 'active' : ''}
              onClick={() => setActiveSection('issues')}
            >
              全局问题 ({analysisResult.global_issues?.length || 0})
            </button>
            <button 
              className={activeSection === 'dependencies' ? 'active' : ''}
              onClick={() => setActiveSection('dependencies')}
            >
              依赖
            </button>
          </div>

          {/* 内容区域 */}
          <div className="section-content">
            {activeSection === 'summary' && renderSummary()}
            {activeSection === 'files' && renderFiles()}
            {activeSection === 'issues' && renderGlobalIssues()}
            {activeSection === 'dependencies' && renderDependencies()}
          </div>
        </div>
      )}
    </div>
  );
});

export default ProjectAnalysisView;