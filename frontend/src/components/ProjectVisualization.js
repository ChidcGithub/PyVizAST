import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import fcose from 'cytoscape-fcose';
import { useResizeObserver } from '../hooks/useResizeObserver';
import './components.css';

// Register Cytoscape layout extensions
cytoscape.use(dagre);
cytoscape.use(fcose);

// Color mapping - black and white gray tones
const NODE_COLORS = {
  file: '#ffffff',      // White fill - regular module
  module: '#f3f4f6',    // Light gray - module
  external: '#9ca3af',  // Gray - external dependency
  circular: '#fecaca',  // Light red - circular dependency
};

const NODE_BORDER_COLORS = {
  file: '#374151',      // Dark gray border - regular module
  module: '#4b5563',    // Gray border
  external: '#6b7280',  // Gray border
  circular: '#dc2626',  // Red border - circular dependency
};

const EDGE_COLORS = {
  import: '#4b5563',    // Dark gray - regular import
  circular: '#dc2626',  // Red - circular dependency
};

/**
 * Project Dependency Visualization Component
 * Uses Cytoscape.js to display project file dependency graphs
 */
function ProjectVisualization({ projectResult, theme, viewMode = '2d' }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [isReady, setIsReady] = useState(false);

  // Process dependency data into graph data
  const graphData = useMemo(() => {
    if (!projectResult) return { nodes: [], edges: [] };

    const nodes = [];
    const edges = [];
    const deps = projectResult.dependencies || {};
    const depGraph = deps.dependency_graph || {};
    const circularDeps = projectResult.global_issues?.filter(
      issue => issue.issue_type === 'circular_dependency'
    ) || [];

    // Create circular dependency set for highlighting
    const circularPairs = new Set();
    circularDeps.forEach(issue => {
      if (issue.locations?.length >= 2) {
        const pair = issue.locations.map(l => l.file_path).sort().join('<->');
        circularPairs.add(pair);
      }
    });

    // Add all file nodes
    // Note: Backend returns module name format (e.g. backend.main), not file path format
    const moduleNames = new Set();
    Object.keys(depGraph).forEach(module => moduleNames.add(module));
    Object.values(depGraph).flat().forEach(module => moduleNames.add(module));

    moduleNames.forEach((moduleName) => {
      const isCircular = circularDeps.some(issue => 
        issue.locations?.some(loc => loc.file_path === module)
      );
      
      // Module name is dot-separated, take last part as label
      const label = moduleName.split('.').pop() || moduleName;
      
      nodes.push({
        data: {
          id: moduleName,
          label: label,
          fullPath: moduleName,
          type: isCircular ? 'circular' : 'file',
        },
      });
    });

    // Add dependency relationships
    Object.entries(depGraph).forEach(([source, targets]) => {
      targets.forEach(target => {
        // Check if it's a circular dependency
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

  // Initialize Cytoscape
  const initCytoscape = useCallback(() => {
    if (!containerRef.current || graphData.nodes.length === 0) return;
    
    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    
    // Ensure container has valid dimensions
    if (rect.width === 0 || rect.height === 0) {
      return false;
    }

    // Destroy old instance
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
          // Regular module nodes - rectangle
          {
            selector: 'node[type="file"]',
            style: {
              'shape': 'roundrectangle',
              'background-color': isDark ? '#1f2937' : '#ffffff',
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'font-size': '11px',
              'font-family': 'Inter, sans-serif',
              'color': isDark ? '#e5e7eb' : '#374151',
              'width': 80,
              'height': 40,
              'text-wrap': 'wrap',
              'text-max-width': 70,
              'border-width': 2,
              'border-color': isDark ? '#4b5563' : '#374151',
              'corner-radius': 4,
            },
          },
          // Circular dependency nodes - diamond
          {
            selector: 'node[type="circular"]',
            style: {
              'shape': 'diamond',
              'background-color': isDark ? '#7f1d1d' : '#fecaca',
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'font-size': '11px',
              'font-family': 'Inter, sans-serif',
              'color': isDark ? '#fca5a5' : '#991b1b',
              'width': 70,
              'height': 70,
              'text-wrap': 'wrap',
              'text-max-width': 60,
              'border-width': 2,
              'border-color': '#dc2626',
            },
          },
          // Selected state
          {
            selector: 'node:selected',
            style: {
              'border-width': 3,
              'border-color': isDark ? '#60a5fa' : '#2563eb',
            },
          },
          // Regular import edges - solid line
          {
            selector: 'edge[type="import"]',
            style: {
              'width': 1.5,
              'line-color': isDark ? '#6b7280' : '#9ca3af',
              'target-arrow-color': isDark ? '#6b7280' : '#9ca3af',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.6,
              'line-style': 'solid',
            },
          },
          // Circular dependency edges - dashed line
          {
            selector: 'edge[type="circular"]',
            style: {
              'width': 2,
              'line-color': '#dc2626',
              'target-arrow-color': '#dc2626',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.7,
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

      // Event handling
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

  // Delayed initialization to ensure container dimensions are correct
  useEffect(() => {
    if (graphData.nodes.length === 0) return;

    // Use requestAnimationFrame for delayed initialization
    let animationFrameId = null;
    let timeoutId = null;
    let attempts = 0;
    const maxAttempts = 10;

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

    // First attempt
    animationFrameId = requestAnimationFrame(tryInit);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      if (timeoutId) {
        clearTimeout(timeoutId);
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

  // Use safe ResizeObserver hook to monitor container dimension changes
  useResizeObserver(containerRef, () => {
    if (cyRef.current && cyRef.current.elements().length > 0) {
      cyRef.current.fit(undefined, 30);
    }
  }, { debounce: 150 });

  // If no data, show placeholder
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
            <p>View dependency graph after analyzing project</p>
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
            <span>Nodes:</span>
            <span className="viz-stat-value">{graphData.nodes.length}</span>
          </div>
          <div className="viz-stat">
            <span>Dependencies:</span>
            <span className="viz-stat-value">{graphData.edges.length}</span>
          </div>
        </div>
      </div>

      <div className="project-viz-content" ref={containerRef}>
        {/* Cytoscape container */}
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <div className="node-detail-panel">
          <div className="panel-header">
            <div className="panel-header-main">
              <span className="node-icon">📄</span>
              <div>
                <h4>Node Details</h4>
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
              <span className="detail-label">Path</span>
              <span className="detail-value code">{selectedNode.fullPath}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Type</span>
              <span className="detail-value">{selectedNode.type === 'circular' ? 'Circular Dependency' : 'File'}</span>
            </div>
          </div>
        </div>
      )}

      <div className="project-viz-legend">
        <div className="viz-legend-item">
          <div className="viz-legend-shape rectangle" title="Regular module"></div>
          <span>Module</span>
        </div>
        <div className="viz-legend-item">
          <div className="viz-legend-shape diamond" title="Circular dependency"></div>
          <span>Circular Dep</span>
        </div>
        <div className="viz-legend-item">
          <div className="viz-legend-line solid" title="Regular import"></div>
          <span>Import</span>
        </div>
        <div className="viz-legend-item">
          <div className="viz-legend-line dashed" title="Circular reference"></div>
          <span>Circular Ref</span>
        </div>
      </div>
    </div>
  );
}

export default ProjectVisualization;
