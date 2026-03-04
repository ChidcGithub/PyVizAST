import React from 'react';
import {
  GitBranch,
  Activity,
  Shield,
  Lightbulb,
  BookOpen,
  Trophy,
  Zap,
  Wand2,
  Box,
  LayoutGrid
} from 'lucide-react';

function Sidebar({ isOpen, activeTab, onTabChange, analysisResult, viewMode, onViewModeChange }) {
  const tabs = [
    { id: 'ast', label: 'AST Visualization', icon: <GitBranch size={18} /> },
    { id: 'complexity', label: 'Complexity', icon: <Activity size={18} /> },
    { id: 'performance', label: 'Performance', icon: <Zap size={18} /> },
    { id: 'security', label: 'Security', icon: <Shield size={18} /> },
    { id: 'suggestions', label: 'Suggestions', icon: <Lightbulb size={18} /> },
    { id: 'patches', label: 'Auto Fix', icon: <Wand2 size={18} /> },
    { id: 'learn', label: 'Learn', icon: <BookOpen size={18} /> },
    { id: 'challenges', label: 'Challenges', icon: <Trophy size={18} /> },
  ];

  const getTabCount = (tabId) => {
    if (!analysisResult) return null;
    
    switch (tabId) {
      case 'complexity':
        return analysisResult.issues?.filter(i => i.type === 'complexity').length || 0;
      case 'performance':
        return analysisResult.performance_hotspots?.length || 0;
      case 'security':
        return analysisResult.issues?.filter(i => i.type === 'security').length || 0;
      case 'suggestions':
        return analysisResult.suggestions?.length || 0;
      case 'patches':
        // Display count of auto-fixable suggestions
        return analysisResult.suggestions?.filter(s => s.auto_fixable).length || 0;
      default:
        return null;
    }
  };

  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <nav className="sidebar-nav">
        {tabs.map((tab) => {
          const count = getTabCount(tab.id);
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              className={`sidebar-tab ${isActive ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
              {count !== null && count > 0 && (
                <span className="tab-count">{count}</span>
              )}
            </button>
          );
        })}
      </nav>
      
      {/* View mode toggle - only show when AST tab is active */}
      {activeTab === 'ast' && (
        <div className="view-mode-toggle">
          <h4>View Mode</h4>
          <div className="view-mode-buttons">
            <button
              className={`view-mode-btn ${viewMode === '2d' ? 'active' : ''}`}
              onClick={() => onViewModeChange('2d')}
              title="2D View"
            >
              <LayoutGrid size={16} />
              <span>2D</span>
            </button>
            <button
              className={`view-mode-btn ${viewMode === '3d' ? 'active' : ''}`}
              onClick={() => onViewModeChange('3d')}
              title="3D View"
            >
              <Box size={16} />
              <span>3D</span>
            </button>
          </div>
        </div>
      )}
      
      {analysisResult && (
        <div className="sidebar-stats">
          <h4>Summary</h4>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-value">{analysisResult.total_lines}</span>
              <span className="stat-label">Lines</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{analysisResult.complexity?.cyclomatic_complexity || 0}</span>
              <span className="stat-label">Complexity</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{analysisResult.summary?.total_issues || 0}</span>
              <span className="stat-label">Issues</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{analysisResult.ast_graph?.metadata?.total_nodes || 0}</span>
              <span className="stat-label">Nodes</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;