import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import fcose from 'cytoscape-fcose';
import { useResizeObserver } from '../hooks/useResizeObserver';
import './components.css';

// 注册 Cytoscape 布局扩展
cytoscape.use(dagre);
cytoscape.use(fcose);

// 颜色映射
const NODE_COLORS = {
  file: '#3b82f6',      // 蓝色 - 文件
  module: '#8b5cf6',    // 紫色 - 模块
  external: '#6b7280',  // 灰色 - 外部依赖
  circular: '#ef4444',  // 红色 - 循环依赖
};

const EDGE_COLORS = {
  import: '#4ade80',    // 绿色 - 导入
  circular: '#ef4444',  // 红色 - 循环依赖
};

/**
 * 项目依赖可视化组件
 * 使用 Cytoscape.js 显示项目文件的依赖关系图
 */
function ProjectVisualization({ projectResult, theme, viewMode = '2d' }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [isReady, setIsReady] = useState(false);

  // 处理依赖数据转换为图形数据
  const graphData = useMemo(() => {
    if (!projectResult) return { nodes: [], edges: [] };

    const nodes = [];
    const edges = [];
    const deps = projectResult.dependencies || {};
    const depGraph = deps.dependency_graph || {};
    const circularDeps = projectResult.global_issues?.filter(
      issue => issue.issue_type === 'circular_dependency'
    ) || [];

    // 创建循环依赖集合用于高亮
    const circularPairs = new Set();
    circularDeps.forEach(issue => {
      if (issue.locations?.length >= 2) {
        const pair = issue.locations.map(l => l.file_path).sort().join('<->');
        circularPairs.add(pair);
      }
    });

    // 添加所有文件节点
    const filePaths = new Set();
    Object.keys(depGraph).forEach(file => filePaths.add(file));
    Object.values(depGraph).flat().forEach(file => filePaths.add(file));

    filePaths.forEach((file) => {
      const isCircular = circularDeps.some(issue => 
        issue.locations?.some(loc => loc.file_path === file)
      );
      
      nodes.push({
        data: {
          id: file,
          label: file.split('/').pop(),
          fullPath: file,
          type: isCircular ? 'circular' : 'file',
        },
      });
    });

    // 添加依赖关系
    Object.entries(depGraph).forEach(([source, targets]) => {
      targets.forEach(target => {
        // 检查是否是循环依赖
        const pair = [source, target].sort().join('<->');
        const isCircular = circularPairs.has(pair);
        
        edges.push({
          data: {
            id: `${source}->${target}`,
            source,
            target,
            type: isCircular ? 'circular' : 'import',
          },
        });
      });
    });

    return { nodes, edges };
  }, [projectResult]);

  // 初始化 Cytoscape
  const initCytoscape = useCallback(() => {
    if (!containerRef.current || graphData.nodes.length === 0) return;
    
    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    
    // 确保容器有有效尺寸
    if (rect.width === 0 || rect.height === 0) {
      return false;
    }

    // 销毁旧的实例
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const isDark = theme === 'dark';
    
    try {
      const cy = cytoscape({
        container: container,
        elements: [...graphData.nodes, ...graphData.edges],
        
        style: [
          {
            selector: 'node',
            style: {
              'background-color': function(ele) {
                const type = ele.data('type');
                return NODE_COLORS[type] || NODE_COLORS.file;
              },
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'font-size': '11px',
              'font-family': 'Inter, sans-serif',
              'color': isDark ? '#e5e7eb' : '#374151',
              'width': 60,
              'height': 60,
              'text-wrap': 'wrap',
              'text-max-width': 80,
              'border-width': 2,
              'border-color': isDark ? '#374151' : '#d1d5db',
            },
          },
          {
            selector: 'node:selected',
            style: {
              'border-width': 3,
              'border-color': '#ffffff',
              'line-color': '#ffffff',
            },
          },
          {
            selector: 'node[type="circular"]',
            style: {
              'background-color': NODE_COLORS.circular,
              'border-color': '#fca5a5',
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': function(ele) {
                const type = ele.data('type');
                return EDGE_COLORS[type] || EDGE_COLORS.import;
              },
              'target-arrow-color': function(ele) {
                const type = ele.data('type');
                return EDGE_COLORS[type] || EDGE_COLORS.import;
              },
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.8,
            },
          },
          {
            selector: 'edge[type="circular"]',
            style: {
              'line-color': EDGE_COLORS.circular,
              'target-arrow-color': EDGE_COLORS.circular,
              'line-style': 'dashed',
            },
          },
        ],
        
        layout: {
          name: 'fcose',
          quality: 'proof',
          animate: true,
          animationDuration: 500,
          fit: true,
          padding: 50,
          nodeDimensionsIncludeLabels: true,
          idealEdgeLength: 100,
          nodeRepulsion: 4500,
        },
        
        minZoom: 0.3,
        maxZoom: 2,
        wheelSensitivity: 0.3,
      });

      // 事件处理
      cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        setSelectedNode({
          id: node.id(),
          label: node.data('label'),
          fullPath: node.data('fullPath'),
          type: node.data('type'),
        });
      });

      cy.on('mouseover', 'node', (evt) => {
        const node = evt.target;
        setHoverNode({
          id: node.id(),
          label: node.data('label'),
          fullPath: node.data('fullPath'),
        });
      });

      cy.on('mouseout', 'node', () => {
        setHoverNode(null);
      });

      cyRef.current = cy;
      setIsReady(true);
      return true;
    } catch (error) {
      console.error('Cytoscape initialization error:', error);
      return false;
    }
  }, [graphData, theme]);

  // 延迟初始化，确保容器尺寸正确
  useEffect(() => {
    if (graphData.nodes.length === 0) return;

    // 使用 requestAnimationFrame 延迟初始化
    let animationFrameId = null;
    let timeoutId = null;
    let attempts = 0;
    const maxAttempts = 10;
    let isResizing = false;

    const tryInit = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          initCytoscape();
          return;
        }
      }
      
      attempts++;
      if (attempts < maxAttempts) {
        animationFrameId = requestAnimationFrame(tryInit);
      }
    };

    // 首次尝试
    animationFrameId = requestAnimationFrame(tryInit);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      if (cyRef.current) {
        try {
          cyRef.current.destroy();
        } catch (e) {}
        cyRef.current = null;
      }
      setIsReady(false);
    };
  }, [initCytoscape, graphData.nodes.length]);

  // 使用安全的 ResizeObserver hook 监听容器尺寸变化
  useResizeObserver(containerRef, () => {
    if (cyRef.current && cyRef.current.elements().length > 0) {
      cyRef.current.fit(undefined, 30);
    }
  }, { debounce: 150 });

  // 如果没有数据，显示占位符
  if (!projectResult || graphData.nodes.length === 0) {
    return (
      <div className="project-viz-panel">
        <div className="project-viz-toolbar">
          <div className="project-viz-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            <h3>Project Visualization</h3>
          </div>
        </div>
        <div className="project-viz-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="placeholder">
            <div className="placeholder-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
            </div>
            <h3>Dependency Visualization</h3>
            <p>分析项目后查看依赖关系图</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="project-viz-panel">
      <div className="project-viz-toolbar">
        <div className="project-viz-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          <h3>Dependency Graph</h3>
        </div>
        <div className="project-viz-stats">
          <div className="viz-stat">
            <span>节点:</span>
            <span className="viz-stat-value">{graphData.nodes.length}</span>
          </div>
          <div className="viz-stat">
            <span>依赖:</span>
            <span className="viz-stat-value">{graphData.edges.length}</span>
          </div>
        </div>
      </div>

      <div className="project-viz-content" ref={containerRef}>
        {/* Cytoscape 容器 */}
      </div>

      {/* 节点详情面板 */}
      {selectedNode && (
        <div className="node-detail-panel">
          <div className="panel-header">
            <div className="panel-header-main">
              <span className="node-icon">📄</span>
              <div>
                <h4>节点详情</h4>
                <span className="node-name">{selectedNode.label}</span>
              </div>
            </div>
            <button 
              className="close-btn"
              onClick={() => setSelectedNode(null)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div className="panel-body">
            <div className="detail-item">
              <span className="detail-label">路径</span>
              <span className="detail-value code">{selectedNode.fullPath}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">类型</span>
              <span className="detail-value">{selectedNode.type === 'circular' ? '循环依赖' : '文件'}</span>
            </div>
          </div>
        </div>
      )}

      <div className="project-viz-legend">
        <div className="viz-legend-item">
          <div className="viz-legend-color" style={{ background: NODE_COLORS.file }}></div>
          <span>文件</span>
        </div>
        <div className="viz-legend-item">
          <div className="viz-legend-color" style={{ background: NODE_COLORS.circular }}></div>
          <span>循环依赖</span>
        </div>
        <div className="viz-legend-item">
          <div className="viz-legend-color" style={{ background: EDGE_COLORS.import }}></div>
          <span>导入</span>
        </div>
        <div className="viz-legend-item">
          <div className="viz-legend-color" style={{ background: EDGE_COLORS.circular }}></div>
          <span>循环引用</span>
        </div>
      </div>
    </div>
  );
}

export default ProjectVisualization;