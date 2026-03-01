import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';

// Performance constants
const MAX_NODES_FULL = 300;
const MAX_NODES_MEDIUM = 800;

// Priority node types
const PRIORITY_TYPES = new Set([
  'function', 'class', 'FunctionDef', 'AsyncFunctionDef', 'ClassDef',
  'if', 'for', 'while', 'try', 'with', 'If', 'For', 'While', 'Try', 'With',
  'Module'
]);

// Secondary node types
const SECONDARY_TYPES = new Set([
  'call', 'return', 'yield', 'Call', 'Return', 'Yield',
  'import', 'Import', 'ImportFrom', 'Assign', 'AugAssign'
]);


function ASTVisualizer({ graph, theme }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [detailLevel, setDetailLevel] = useState('normal');
  const [isRendering, setIsRendering] = useState(false);
  const [layoutType, setLayoutType] = useState('dagre');
  const zoomRef = useRef(1);

  // Filter elements based on detail level
  const filteredElements = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    
    const totalNodes = graph.nodes.length;
    const nodeIds = new Set();
    let filteredNodes;
    
    if (detailLevel === 'detail' || totalNodes <= MAX_NODES_FULL) {
      filteredNodes = graph.nodes;
      filteredNodes.forEach(n => nodeIds.add(n.id));
    } else if (detailLevel === 'normal' || totalNodes <= MAX_NODES_MEDIUM) {
      filteredNodes = graph.nodes.filter(node => {
        const keep = PRIORITY_TYPES.has(node.type) || SECONDARY_TYPES.has(node.type);
        if (keep) nodeIds.add(node.id);
        return keep;
      });
    } else {
      filteredNodes = graph.nodes.filter(node => {
        const keep = PRIORITY_TYPES.has(node.type);
        if (keep) nodeIds.add(node.id);
        return keep;
      });
    }
    
    const filteredEdges = graph.edges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );
    
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graph, detailLevel]);

  // Prepare Cytoscape elements with fixed sizes
  const cytoscapeElements = useMemo(() => {
    return {
      nodes: filteredElements.nodes.map(node => {
        let width = 50, height = 50;
        const type = node.type?.toLowerCase();
        
        if (type === 'module') { width = 80; height = 40; }
        else if (type === 'class') { width = 70; height = 40; }
        else if (type === 'function' || type === 'functiondef' || type === 'asyncfunctiondef') { width = 65; height = 35; }
        else if (['if', 'for', 'while', 'try', 'with'].includes(type)) { width = 40; height = 40; }
        else if (type === 'call') { width = 35; height = 35; }
        else if (type === 'assign') { width = 30; height = 30; }
        else { width = 28; height = 28; }
        
        return {
          data: {
            id: node.id,
            label: node.name || node.type,
            type: node.type,
            color: node.color,
            width: width,
            height: height,
            lineno: node.lineno,
            docstring: node.docstring,
            source_code: node.source_code,
          }
        };
      }),
      edges: filteredElements.edges.map(edge => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: edge.edge_type,
        }
      }))
    };
  }, [filteredElements]);

  // Get layout config
  const getLayoutConfig = useCallback((nodeCount, layoutName = 'dagre') => {
    const baseSpacing = Math.max(80, 150 - nodeCount * 0.3);
    
    if (layoutName === 'dagre') {
      return {
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: baseSpacing * 1.2,
        rankSep: baseSpacing * 1.5,
        padding: 40,
      };
    } else if (layoutName === 'fcose') {
      return {
        name: 'fcose',
        quality: 'proof',
        randomize: false,
        animate: false,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: baseSpacing * 2,
        nodeRepulsion: 8000,
        padding: 40,
      };
    } else {
      return {
        name: 'breadthfirst',
        directed: true,
        spacingX: baseSpacing * 1.5,
        spacingY: baseSpacing * 2,
        padding: 40,
      };
    }
  }, []);

  // Initialize Cytoscape once
  useEffect(() => {
    if (!graph || !containerRef.current) return;
    if (cytoscapeElements.nodes.length === 0) return;

    let mounted = true;
    setIsRendering(true);

    const initCytoscape = async () => {
      try {
        const cytoscape = (await import('cytoscape')).default;
        
        const [dagre, fcose] = await Promise.all([
          import('cytoscape-dagre').then(m => m.default),
          import('cytoscape-fcose').then(m => m.default)
        ]);
        
        cytoscape.use(dagre);
        cytoscape.use(fcose);

        if (!mounted) return;

        // Destroy existing instance
        if (cyRef.current) {
          cyRef.current.destroy();
          cyRef.current = null;
        }

        const nodeCount = cytoscapeElements.nodes.length;
        const layoutConfig = getLayoutConfig(nodeCount, layoutType);

        const cy = cytoscape({
          container: containerRef.current,
          elements: cytoscapeElements,
          style: getCytoscapeStyles(theme),
          layout: layoutConfig,
          userZoomingEnabled: true,
          userPanningEnabled: true,
          boxSelectionEnabled: true,
          minZoom: 0.1,
          maxZoom: 5,
        });

        cyRef.current = cy;

        // Node click handler
        cy.on('tap', 'node', (evt) => {
          const node = evt.target;
          const nodeData = node.data();
          
          setSelectedNode({
            id: nodeData.id,
            type: nodeData.type,
            name: nodeData.label,
            lineno: nodeData.lineno,
            docstring: nodeData.docstring,
            sourceCode: nodeData.source_code,
          });

          cy.elements().removeClass('highlighted highlighted-path');
          node.addClass('highlighted');
          node.neighborhood('edge').addClass('highlighted-path');
          node.neighborhood('node').addClass('highlighted-path');
        });

        // Click background
        cy.on('tap', (evt) => {
          if (evt.target === cy) {
            setSelectedNode(null);
            cy.elements().removeClass('highlighted highlighted-path');
          }
        });

        // Zoom handler - only update zoom display, don't re-render
        cy.on('zoom', () => {
          const currentZoom = cy.zoom();
          zoomRef.current = currentZoom;
          setZoom(currentZoom);
        });

        // Double click to focus
        cy.on('dbltap', 'node', (evt) => {
          const node = evt.target;
          cy.animate({
            zoom: 2,
            center: { eles: node },
            duration: 300
          });
        });

        cy.ready(() => {
          if (mounted) {
            cy.fit(undefined, 50);
            setIsRendering(false);
          }
        });

      } catch (error) {
        console.error('Failed to initialize Cytoscape:', error);
        if (mounted) setIsRendering(false);
      }
    };

    // Delay init to avoid ResizeObserver issues
    const timer = setTimeout(() => {
      requestAnimationFrame(initCytoscape);
    }, 50);

    return () => {
      mounted = false;
      clearTimeout(timer);
      if (cyRef.current) {
        try {
          cyRef.current.destroy();
        } catch (e) {}
        cyRef.current = null;
      }
    };
  }, [cytoscapeElements, theme, layoutType, getLayoutConfig, graph]);

  // Update theme without re-initializing
  useEffect(() => {
    if (cyRef.current) {
      cyRef.current.style(getCytoscapeStyles(theme));
    }
  }, [theme]);

  // Re-layout when layout type changes
  useEffect(() => {
    if (cyRef.current && cytoscapeElements.nodes.length > 0) {
      const layoutConfig = getLayoutConfig(cytoscapeElements.nodes.length, layoutType);
      cyRef.current.layout(layoutConfig).run();
    }
  }, [layoutType, getLayoutConfig, cytoscapeElements.nodes.length]);

  const handleZoomIn = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.4);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() / 1.4);
    }
  }, []);

  const handleFit = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 50);
    }
  }, []);

  const totalNodes = graph?.nodes?.length || 0;
  const displayedNodes = filteredElements.nodes.length;
  const isSimplified = totalNodes !== displayedNodes;

  return (
    <div className="ast-visualizer">
      <div className="visualizer-toolbar">
        <div className="toolbar-left">
          <span className="toolbar-title">AST Structure</span>
          <span className="node-count">
            {displayedNodes} nodes
            {isSimplified && <span className="simplified-badge"> / {totalNodes} total</span>}
          </span>
        </div>
        <div className="toolbar-right">
          <select 
            className="simplify-select"
            value={layoutType}
            onChange={(e) => setLayoutType(e.target.value)}
            title="Layout algorithm"
          >
            <option value="dagre">Hierarchical</option>
            <option value="fcose">Force-directed</option>
            <option value="breadthfirst">Breadth-first</option>
          </select>
          
          <select 
            className="simplify-select"
            value={detailLevel}
            onChange={(e) => setDetailLevel(e.target.value)}
            title="Detail level"
          >
            <option value="overview">Overview</option>
            <option value="normal">Normal</option>
            <option value="detail">Detail</option>
          </select>
          
          <div className="toolbar-divider"></div>
          
          <button className="btn btn-ghost" onClick={handleZoomOut} title="Zoom out">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </button>
          <span className="zoom-level">{Math.round(zoom * 100)}%</span>
          <button className="btn btn-ghost" onClick={handleZoomIn} title="Zoom in">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="11" y1="8" x2="11" y2="14" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </button>
          <button className="btn btn-ghost" onClick={handleFit} title="Fit all">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
            </svg>
          </button>
        </div>
      </div>
      
      <div className="visualizer-content">
        {isRendering && (
          <div className="rendering-overlay">
            <div className="rendering-spinner"></div>
            <span>Rendering {displayedNodes} nodes...</span>
          </div>
        )}
        <div className="cytoscape-container" ref={containerRef}></div>
        
        {selectedNode && (
          <div className="node-detail-panel">
            <div className="panel-header">
              <h4>{selectedNode.type}</h4>
              {selectedNode.name && <span className="node-name">{selectedNode.name}</span>}
            </div>
            
            <div className="panel-body">
              {selectedNode.lineno && (
                <div className="detail-item">
                  <span className="detail-label">Line</span>
                  <span className="detail-value">{selectedNode.lineno}</span>
                </div>
              )}
              
              {selectedNode.docstring && (
                <div className="detail-item">
                  <span className="detail-label">Docstring</span>
                  <p className="docstring">{selectedNode.docstring}</p>
                </div>
              )}
              
              {selectedNode.sourceCode && (
                <div className="detail-item">
                  <span className="detail-label">Source</span>
                  <pre className="source-code">{selectedNode.sourceCode}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <div className="visualizer-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#ffffff' }}></span>
          <span>Function</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#e0e0e0' }}></span>
          <span>Class</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#a0a0a0' }}></span>
          <span>Control Flow</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#707070' }}></span>
          <span>Call</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#505050' }}></span>
          <span>Assignment</span>
        </div>
        <div className="legend-hint">Double-click node to focus</div>
      </div>
    </div>
  );
}

function getCytoscapeStyles(theme) {
  const isDark = theme === 'dark';
  
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'label': 'data(label)',
        'width': 'data(width)',
        'height': 'data(height)',
        'font-size': 11,
        'font-family': 'Inter, system-ui, sans-serif',
        'font-weight': '500',
        'color': isDark ? '#ffffff' : '#0a0a0a',
        'text-valign': 'center',
        'text-halign': 'center',
        'text-outline-color': isDark ? '#000000' : '#ffffff',
        'text-outline-width': 3,
        'border-width': 1.5,
        'border-color': isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
        'text-wrap': 'wrap',
        'text-max-width': 80,
      }
    },
    {
      selector: 'node.highlighted',
      style: {
        'border-width': 3,
        'border-color': '#ffffff',
        'z-index': 999,
      }
    },
    {
      selector: 'node.highlighted-path',
      style: {
        'border-width': 2,
        'border-color': isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.3)',
        'opacity': 0.8,
      }
    },
    {
      selector: 'node[type="function"], node[type="FunctionDef"], node[type="AsyncFunctionDef"]',
      style: { 'shape': 'roundrectangle' }
    },
    {
      selector: 'node[type="class"], node[type="ClassDef"]',
      style: { 'shape': 'roundrectangle' }
    },
    {
      selector: 'node[type="module"], node[type="Module"]',
      style: { 'shape': 'roundrectangle' }
    },
    {
      selector: 'node[type="if"], node[type="If"], node[type="for"], node[type="For"], node[type="while"], node[type="While"]',
      style: { 'shape': 'diamond' }
    },
    {
      selector: 'edge',
      style: {
        'width': 1.5,
        'line-color': isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
        'target-arrow-color': isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 0.6,
      }
    },
    {
      selector: 'edge.highlighted',
      style: {
        'width': 2.5,
        'line-color': isDark ? '#ffffff' : '#000000',
        'target-arrow-color': isDark ? '#ffffff' : '#000000',
        'z-index': 998,
      }
    },
    {
      selector: 'edge.highlighted-path',
      style: {
        'width': 2,
        'line-color': isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.3)',
        'target-arrow-color': isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.3)',
      }
    },
    {
      selector: 'edge[type="call"]',
      style: {
        'line-color': isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.2)',
        'target-arrow-color': isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.2)',
        'line-style': 'dashed',
      }
    },
  ];
}

export default ASTVisualizer;