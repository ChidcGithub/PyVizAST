import React, { useEffect, useRef } from 'react';

function Header({ onAnalyze, onToggleSidebar, isLoading, theme, onThemeChange, viewMode, onViewModeChange }) {
  const tabsRef = useRef(null);

  // 更新滑动指示器位置
  useEffect(() => {
    if (tabsRef.current) {
      if (viewMode === 'project') {
        tabsRef.current.classList.add('slide-right');
      } else {
        tabsRef.current.classList.remove('slide-right');
      }
    }
  }, [viewMode]);

  return (
    <header className="header">
      <div className="header-left">
        <button className="btn btn-ghost menu-toggle" onClick={onToggleSidebar}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        
        <div className="logo">
          <span className="logo-icon">PV</span>
          <span className="logo-text">PyVizAST</span>
        </div>
      </div>
      
      <div className="header-center">
        {/* 视图切换标签 */}
        <div className="view-tabs" ref={tabsRef}>
          <button 
            className={`view-tab ${viewMode === 'single' ? 'active' : ''}`}
            onClick={() => onViewModeChange('single')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            单文件
          </button>
          <button 
            className={`view-tab ${viewMode === 'project' ? 'active' : ''}`}
            onClick={() => onViewModeChange('project')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            项目分析
          </button>
        </div>
      </div>
      
      <div className="header-right">
        <button 
          className="btn btn-ghost theme-toggle"
          onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>
        
        {viewMode === 'single' && (
          <button 
            className="btn btn-primary analyze-btn"
            onClick={onAnalyze}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                Analyzing...
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Analyze
              </>
            )}
          </button>
        )}
        {viewMode === 'project' && (
          <button 
            className="btn btn-primary analyze-btn"
            onClick={onAnalyze}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                Analyzing...
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Analyze
              </>
            )}
          </button>
        )}
      </div>
    </header>
  );
}

export default Header;
