import React, { useState, useCallback, useEffect, useRef } from 'react';
import CodeEditor from './components/CodeEditor';
import ASTVisualizer from './components/ASTVisualizer';
import AnalysisPanel from './components/AnalysisPanel';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoadingOverlay from './components/LoadingOverlay';
import { analyzeCode } from './api';
import './App.css';
import './components/components.css';
import './components/AnalysisPanel.css';

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
  
  // 用于取消请求的 AbortController
  const abortControllerRef = useRef(null);

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
      setError(err.message || '分析失败，请检查代码语法');
    } finally {
      setIsLoading(false);
    }
  }, [code]);

  const handleCodeChange = useCallback((newCode) => {
    setCode(newCode);
    setAnalysisResult(null);
    setError(null);
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
        />
        
        <main className="main-content">
          <div className="editor-panel">
            <CodeEditor 
              code={code}
              onChange={handleCodeChange}
              theme={theme}
            />
          </div>
          
          <div className="visualization-panel">
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
            
            {analysisResult ? (
              activeTab === 'ast' ? (
                <ASTVisualizer 
                  graph={analysisResult.ast_graph}
                  theme={theme}
                />
              ) : (
                <AnalysisPanel 
                  result={analysisResult}
                  activeTab={activeTab}
                />
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
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
