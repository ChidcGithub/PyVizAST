import React, { useState, useCallback, useEffect, useRef, Suspense, lazy } from 'react';
import CodeEditor from './components/CodeEditor';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoadingOverlay from './components/LoadingOverlay';
import ErrorBoundary from './components/ErrorBoundary';
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
const SAMPLE_CODE = `# PyVizAST 示例代码
# 这个文件展示了各种Python语法结构

import os
from typing import List, Optional

# 全局配置
CONFIG = {
    "debug": True,
    "max_items": 100
}

class DataProcessor:
    """数据处理类"""
    
    def __init__(self, name: str):
        self.name = name
        self.data = []
    
    def process(self, items: List[int]) -> List[int]:
        """处理数据列表"""
        result = []
        
        # 嵌套循环示例
        for item in items:
            if item > 0:
                for i in range(item):
                    if i % 2 == 0:
                        result.append(i * 2)
        
        return result
    
    def calculate_average(self, numbers: List[float]) -> Optional[float]:
        """计算平均值"""
        if not numbers:
            return None
        
        total = sum(numbers)
        return total / len(numbers)


def fibonacci(n: int) -> int:
    """递归计算斐波那契数"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def find_duplicates(arr: List[int]) -> List[int]:
    """找出重复元素"""
    seen = set()
    duplicates = []
    
    for item in arr:
        if item in seen:
            if item not in duplicates:
                duplicates.append(item)
        else:
            seen.add(item)
    
    return duplicates


# 主函数
def main():
    processor = DataProcessor("test")
    
    # 生成测试数据
    data = [i for i in range(20)]
    
    # 处理数据
    result = processor.process(data)
    print(f"处理结果: {result[:10]}...")
    
    # 计算斐波那契
    fib = fibonacci(10)
    print(f"斐波那契(10) = {fib}")


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
  
  // 分割线拖动状态
  const [splitPosition, setSplitPosition] = useState(50); // 百分比
  const [isDragging, setIsDragging] = useState(false);
  const mainContentRef = useRef(null);
  
  // 用于取消请求的 AbortController
  const abortControllerRef = useRef(null);
  
  // 编辑器 ref，用于调用编辑器方法（如跳转到指定行）
  const editorRef = useRef(null);
  
  // 初始化全局错误处理器
  useEffect(() => {
    setupGlobalErrorHandlers();
  }, []);
  
  // 分割线拖动处理
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);
  
  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !mainContentRef.current) return;
    
    const rect = mainContentRef.current.getBoundingClientRect();
    const newPosition = ((e.clientX - rect.left) / rect.width) * 100;
    
    // 限制最小和最大位置
    const clampedPosition = Math.min(Math.max(newPosition, 20), 80);
    setSplitPosition(clampedPosition);
  }, [isDragging]);
  
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);
  
  // 添加全局鼠标事件监听
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

  // 检查服务器连接状态
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
    // 每30秒检查一次连接
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // 组件卸载时取消正在进行的请求
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!code.trim()) {
      setError('请输入Python代码');
      return;
    }

    // 检查服务器连接
    if (!serverStatus.connected) {
      setError(`无法连接到服务器 (${getApiBaseUrl()})。请确保后端正在运行: python run.py backend`);
      return;
    }

    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // 创建新的 AbortController
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      const result = await analyzeCode(code, {}, abortControllerRef.current.signal);
      setAnalysisResult(result);
    } catch (err) {
      // 如果是取消的请求，不显示错误
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        return;
      }
      // 提供更详细的错误信息
      if (err.message?.includes('Network Error') || err.message?.includes('无法连接')) {
        setError(`无法连接到服务器 (${getApiBaseUrl()})。请确保后端正在运行: python run.py backend`);
      } else {
        setError(err.message || '分析失败，请检查代码语法');
      }
    } finally {
      setIsLoading(false);
    }
  }, [code, serverStatus.connected]);

  const handleCodeChange = useCallback((newCode) => {
    setCode(newCode);
    setAnalysisResult(null);
    setError(null);
  }, []);
  
  /**
   * 跳转到编辑器指定行
   * @param {number} lineNumber - 行号（从1开始）
   * @param {number} [endLine] - 可选的结束行号
   */
  const handleGoToLine = useCallback((lineNumber, endLine) => {
    if (editorRef.current) {
      editorRef.current.goToLine(lineNumber, 1, endLine);
    }
  }, []);

  return (
    <div className={`app ${theme}`}>
      {isLoading && <LoadingOverlay />}
      
      <Header 
        onAnalyze={handleAnalyze}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        isLoading={isLoading}
        theme={theme}
        onThemeChange={setTheme}
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
          
          {/* 可拖动的分割线 */}
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
            {/* 服务器连接状态 */}
            {!serverStatus.checking && !serverStatus.connected && (
              <div className="server-status-error">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                  <line x1="6" y1="6" x2="6.01" y2="6" />
                  <line x1="6" y1="18" x2="6.01" y2="18" />
                </svg>
                <div className="status-content">
                  <strong>无法连接到后端服务器</strong>
                  <p>API地址: {getApiBaseUrl()}</p>
                  <p className="status-hint">请在终端运行: <code>python run.py backend</code></p>
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
      </div>
    </div>
  );
}

export default App;
