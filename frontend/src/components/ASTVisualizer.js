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


// Helper function to format attribute keys (defined outside component to avoid recreation)
const ATTR_KEY_MAP = {
  'args': '参数',
  'decorators': '装饰器',
  'bases': '基类',
  'is_async': '异步',
  'target': '循环变量',
  'has_else': '有else分支',
  'args_count': '参数数量',
  'kwargs': '关键字参数',
  'operator': '运算符',
  'operators': '运算符',
  'names': '导入名称',
  'module': '模块',
};

function ASTVisualizer({ graph, theme }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [detailLevel, setDetailLevel] = useState('normal');
  const [isRendering, setIsRendering] = useState(false);
  const [layoutType, setLayoutType] = useState('dagre');
  const [signalParticles, setSignalParticles] = useState([]); // Particles for edge animation
  const zoomRef = useRef(1);
  const initialThemeRef = useRef(theme); // Store initial theme to avoid re-initializing
  
  // Track timers and animation frames for cleanup
  const timersRef = useRef(new Set());
  const animationFramesRef = useRef(new Set());

  // Format attribute key using memoized map
  const formatAttrKey = useCallback((key) => ATTR_KEY_MAP[key] || key, []);

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
        
        // 根据标签长度动态调整尺寸
        const labelText = node.detailed_label || node.name || node.type;
        const labelLen = labelText.length;
        
        if (type === 'module') { width = Math.max(80, labelLen * 8); height = 40; }
        else if (type === 'class') { width = Math.max(70, labelLen * 7); height = 40; }
        else if (type === 'function' || type === 'functiondef' || type === 'asyncfunctiondef') { 
          width = Math.max(65, labelLen * 7); height = 35; 
        }
        else if (['if', 'for', 'while', 'try', 'with'].includes(type)) { width = Math.max(45, labelLen * 6); height = 40; }
        else if (type === 'call') { width = Math.max(40, labelLen * 6); height = 35; }
        else if (type === 'assign') { width = Math.max(35, labelLen * 6); height = 30; }
        else { width = Math.max(30, labelLen * 6); height = 28; }
        
        // 限制最大宽度
        width = Math.min(width, 200);
        
        return {
          data: {
            id: node.id,
            // 使用详细标签或组合标签
            label: node.detailed_label || `${node.icon || ''} ${node.name || node.type}`,
            type: node.type,
            color: node.color,
            width: width,
            height: height,
            lineno: node.lineno,
            docstring: node.docstring,
            source_code: node.source_code,
            icon: node.icon,
            description: node.description,
            explanation: node.explanation,
            name: node.name,
            attributes: node.attributes,
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

  // Initialize Cytoscape once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    let mounted = true;

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

        const cy = cytoscape({
          container: containerRef.current,
          elements: { nodes: [], edges: [] },
          style: getCytoscapeStyles(initialThemeRef.current),
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
            name: nodeData.name,
            label: nodeData.label,
            lineno: nodeData.lineno,
            docstring: nodeData.docstring,
            sourceCode: nodeData.source_code,
            icon: nodeData.icon,
            description: nodeData.description,
            explanation: nodeData.explanation,
            attributes: nodeData.attributes,
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

        // Zoom handler
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

        // Long press to focus with detailed info (taphold = 500ms press)
        cy.on('taphold', 'node', (evt) => {
          const node = evt.target;
          const nodeData = node.data();
          
          // Set detailed node info for panel
          setSelectedNode({
            id: nodeData.id,
            type: nodeData.type,
            name: nodeData.name,
            label: nodeData.label,
            lineno: nodeData.lineno,
            docstring: nodeData.docstring,
            sourceCode: nodeData.source_code,
            icon: nodeData.icon,
            description: nodeData.description,
            explanation: nodeData.explanation,
            attributes: nodeData.attributes,
            isLongPress: true,
          });

          // Hide all nodes except selected and neighbors
          const neighbors = node.neighborhood('node');
          const connectedEdges = node.connectedEdges();
          
          cy.elements().addClass('dimmed');
          node.removeClass('dimmed').addClass('focused');
          neighbors.removeClass('dimmed').addClass('focused-neighbor');
          connectedEdges.removeClass('dimmed').addClass('focused-edge');

          // Animate to focus on node
          cy.animate({
            zoom: 2,
            center: { eles: node },
            duration: 400,
            easing: 'ease-out'
          });
        });

        // Release long press - trigger signal propagation animation
        cy.on('tapend', 'node', (evt) => {
          const node = evt.target;
          
          // Check if this was a long press (node has focused class)
          if (!node.hasClass('focused')) return;
          
          // Signal propagation animation with particles
          propagateSignalWithParticles(cy, node, setSignalParticles);
        });

        // Tap on background to reset
        cy.on('tap', (evt) => {
          if (evt.target === cy) {
            setSelectedNode(null);
            setSignalParticles([]);
            cy.elements().removeClass('dimmed focused focused-neighbor focused-edge highlighted highlighted-path signal-wave');
          }
        });

      } catch (error) {
        console.error('Failed to initialize Cytoscape:', error);
      }
    };

    // Signal propagation with particle animation
    function propagateSignalWithParticles(cy, sourceNode, setParticles) {
      const visitedNodes = new Set();
      const visitedEdges = new Set();
      const nodeId = sourceNode.id();
      visitedNodes.add(nodeId);
      
      // Build propagation queue: [{ sourceNode, targetNode, delay }]
      const propagationQueue = [];
      let currentNodes = [{ node: sourceNode, delay: 0 }];
      
      // Particle speed: pixels per millisecond
      const particleSpeed = 0.5; // 0.5 pixels per ms = 500 pixels per second
      
      // BFS to build propagation order
      for (let depth = 0; depth < 5 && currentNodes.length > 0; depth++) {
        const nextNodes = [];
        
        currentNodes.forEach(({ node, delay }) => {
          node.connectedEdges().forEach(edge => {
            const edgeId = edge.id();
            
            // Skip if this edge was already processed
            if (visitedEdges.has(edgeId)) return;
            visitedEdges.add(edgeId);
            
            const isOutgoing = edge.source().id() === node.id();
            const targetNode = isOutgoing ? edge.target() : edge.source();
            
            // Calculate edge length for delay
            const sourcePos = node.renderedPosition();
            const targetPos = targetNode.renderedPosition();
            const dx = targetPos.x - sourcePos.x;
            const dy = targetPos.y - sourcePos.y;
            const edgeLength = Math.sqrt(dx * dx + dy * dy);
            
            // Delay based on edge length (constant speed)
            const travelTime = edgeLength / particleSpeed;
            
            propagationQueue.push({
              sourceNode: node,
              targetNode,
              delay,
            });
            
            // Only add target node to next wave if not visited
            if (!visitedNodes.has(targetNode.id())) {
              visitedNodes.add(targetNode.id());
              nextNodes.push({ node: targetNode, delay: delay + travelTime });
            }
          });
        });
        
        currentNodes = nextNodes;
      }
      
      // Restore visibility first
      cy.elements().removeClass('dimmed focused focused-neighbor focused-edge');
      
      // Create particles that travel along edges
      let particleId = 0;
      
      propagationQueue.forEach(({ sourceNode, targetNode, delay }) => {
        // Create particle after delay (tracked for cleanup)
        const timerId = setTimeout(() => {
          // Get current positions at animation time
          const sourcePos = sourceNode.renderedPosition();
          const targetPos = targetNode.renderedPosition();
          
          // Calculate edge length
          const dx = targetPos.x - sourcePos.x;
          const dy = targetPos.y - sourcePos.y;
          const edgeLength = Math.sqrt(dx * dx + dy * dy);
          
          const particle = {
            id: particleId++,
            startX: sourcePos.x,
            startY: sourcePos.y,
            endX: targetPos.x,
            endY: targetPos.y,
            progress: 0,
            startTime: Date.now(),
            duration: edgeLength / particleSpeed,
          };
          
          // Add particle to state
          setParticles(prev => [...prev, particle]);
          
          // Add signal class to target node when particle is approaching
          let signalAdded = false;
          
          // Animate particle (tracked for cleanup)
          const animateParticle = () => {
            const elapsed = Date.now() - particle.startTime;
            const progress = Math.min(elapsed / particle.duration, 1);
            
            // Add signal class when particle is halfway
            if (progress > 0.5 && !signalAdded) {
              targetNode.addClass('signal-approaching');
              signalAdded = true;
            }
            
            if (progress < 1) {
              setParticles(prev => 
                prev.map(p => p.id === particle.id ? { ...p, progress } : p)
              );
              const frameId = requestAnimationFrame(animateParticle);
              animationFramesRef.current.add(frameId);
            } else {
              // Remove particle when done
              setParticles(prev => prev.filter(p => p.id !== particle.id));
              
              // Transition to pulse effect
              targetNode.removeClass('signal-approaching');
              targetNode.addClass('signal-pulse');
              const pulseTimerId = setTimeout(() => targetNode.removeClass('signal-pulse'), 400);
              timersRef.current.add(pulseTimerId);
            }
          };
          
          const frameId = requestAnimationFrame(animateParticle);
          animationFramesRef.current.add(frameId);
        }, delay);
        timersRef.current.add(timerId);
      });
    }

    requestAnimationFrame(initCytoscape);

    return () => {
      mounted = false;
      
      // Copy refs to local variables for cleanup
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const timers = timersRef.current;
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const animationFrames = animationFramesRef.current;
      
      // Clear all tracked timers
      timers.forEach(id => clearTimeout(id));
      timers.clear();
      
      // Clear all tracked animation frames
      animationFrames.forEach(id => cancelAnimationFrame(id));
      animationFrames.clear();
      
      if (cyRef.current) {
        try {
          cyRef.current.destroy();
        } catch (e) {}
        cyRef.current = null;
      }
    };
  }, []); // Only run once on mount

  // Update elements when data changes (incremental update)
  useEffect(() => {
    if (!cyRef.current || cytoscapeElements.nodes.length === 0) return;
    
    setIsRendering(true);
    
    const cy = cyRef.current;
    
    // Use json() for batch update - more efficient than destroy/recreate
    cy.json({ elements: cytoscapeElements });
    
    // Apply layout
    const layoutConfig = getLayoutConfig(cytoscapeElements.nodes.length, layoutType);
    const layout = cy.layout(layoutConfig);
    
    layout.on('layoutstop', () => {
      if (cyRef.current) {
        cyRef.current.fit(undefined, 50);
        setIsRendering(false);
      }
    });
    
    layout.run();
  }, [cytoscapeElements, layoutType, getLayoutConfig]);

  // Update theme without re-initializing
  useEffect(() => {
    if (cyRef.current) {
      cyRef.current.style(getCytoscapeStyles(theme));
    }
  }, [theme]);

  // Keyboard navigation (WASD and Arrow keys) - Smooth movement
  useEffect(() => {
    const keysPressed = new Set();
    let animationId = null;
    
    const handleKeyDown = (e) => {
      const key = e.key.toLowerCase();
      if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
        e.preventDefault();
        keysPressed.add(key);
        
        if (!animationId) {
          animate();
        }
      }
    };
    
    const handleKeyUp = (e) => {
      const key = e.key.toLowerCase();
      keysPressed.delete(key);
      
      if (keysPressed.size === 0 && animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
      }
    };
    
    const animate = () => {
      if (!cyRef.current || keysPressed.size === 0) {
        animationId = null;
        return;
      }
      
      const cy = cyRef.current;
      const speed = 8 / cy.zoom(); // Pixels per frame
      
      let dx = 0, dy = 0;
      
      if (keysPressed.has('w') || keysPressed.has('arrowup')) dy = speed;
      if (keysPressed.has('s') || keysPressed.has('arrowdown')) dy = -speed;
      if (keysPressed.has('a') || keysPressed.has('arrowleft')) dx = speed;
      if (keysPressed.has('d') || keysPressed.has('arrowright')) dx = -speed;
      
      if (dx !== 0 || dy !== 0) {
        cy.panBy({ x: dx, y: dy });
      }
      
      animationId = requestAnimationFrame(animate);
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, []);

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
        
        {/* Signal particles overlay */}
        <svg className="particles-overlay">
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <radialGradient id="particleGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#00ffff" stopOpacity="1"/>
              <stop offset="50%" stopColor="#00ccff" stopOpacity="0.8"/>
              <stop offset="100%" stopColor="#0088ff" stopOpacity="0"/>
            </radialGradient>
          </defs>
          {signalParticles.map(particle => {
            const x = particle.startX + (particle.endX - particle.startX) * particle.progress;
            const y = particle.startY + (particle.endY - particle.startY) * particle.progress;
            return (
              <g key={particle.id}>
                {/* Trail effect */}
                <line
                  x1={particle.startX + (particle.endX - particle.startX) * Math.max(0, particle.progress - 0.3)}
                  y1={particle.startY + (particle.endY - particle.startY) * Math.max(0, particle.progress - 0.3)}
                  x2={x}
                  y2={y}
                  stroke="url(#particleGradient)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  filter="url(#glow)"
                  opacity={0.8}
                />
                {/* Particle head */}
                <circle
                  cx={x}
                  cy={y}
                  r="6"
                  fill="#00ffff"
                  filter="url(#glow)"
                />
                <circle
                  cx={x}
                  cy={y}
                  r="3"
                  fill="#ffffff"
                />
              </g>
            );
          })}
        </svg>
        
        {selectedNode && (
          <div className="node-detail-panel">
            <div className="panel-header">
              <div className="panel-header-main">
                <span className="node-icon">{selectedNode.icon || '•'}</span>
                <h4>{selectedNode.description || selectedNode.type}</h4>
              </div>
              {selectedNode.name && <span className="node-name">{selectedNode.name}</span>}
            </div>
            
            <div className="panel-body">
              {selectedNode.label && (
                <div className="detail-item code-label">
                  <span className="detail-label">代码结构</span>
                  <code className="detail-code">{selectedNode.label}</code>
                </div>
              )}
              
              {selectedNode.lineno && (
                <div className="detail-item">
                  <span className="detail-label">位置</span>
                  <span className="detail-value">第 {selectedNode.lineno} 行</span>
                </div>
              )}
              
              {selectedNode.explanation && (
                <div className="detail-item explanation">
                  <span className="detail-label">说明</span>
                  <p className="explanation-text">{selectedNode.explanation}</p>
                </div>
              )}
              
              {selectedNode.docstring && (
                <div className="detail-item">
                  <span className="detail-label">文档字符串</span>
                  <p className="docstring">{selectedNode.docstring}</p>
                </div>
              )}
              
              {selectedNode.attributes && Object.keys(selectedNode.attributes).length > 0 && (
                <div className="detail-item">
                  <span className="detail-label">属性</span>
                  <div className="attributes-list">
                    {Object.entries(selectedNode.attributes).map(([key, value]) => {
                      if (value === null || value === undefined || (Array.isArray(value) && value.length === 0)) {
                        return null;
                      }
                      const displayValue = Array.isArray(value) 
                        ? value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join(', ')
                        : typeof value === 'object' ? JSON.stringify(value) : String(value);
                      return (
                        <div key={key} className="attribute-item">
                          <span className="attr-key">{formatAttrKey(key)}:</span>
                          <span className="attr-value">{displayValue}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              
              {selectedNode.sourceCode && (
                <div className="detail-item">
                  <span className="detail-label">源代码</span>
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
        <div className="legend-hint">双击聚焦 | 长按查看详情 | WASD/方向键移动</div>
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
      selector: 'node.focused',
      style: {
        'border-width': 4,
        'border-color': '#00ff88',
        'z-index': 1000,
        'overlay-color': '#00ff88',
        'overlay-opacity': 0.2,
        'overlay-padding': 8,
      }
    },
    {
      selector: 'node.dimmed',
      style: {
        'opacity': 0.15,
      }
    },
    {
      selector: 'node.focused-neighbor',
      style: {
        'border-width': 2,
        'border-color': '#00ff88',
        'opacity': 0.9,
        'z-index': 999,
      }
    },
    {
      selector: 'node.signal-wave',
      style: {
        'border-width': 3,
        'border-color': '#00ccff',
        'overlay-color': '#00ccff',
        'overlay-opacity': 0.4,
        'overlay-padding': 12,
        'transition-property': 'overlay-opacity, border-color',
        'transition-duration': 0.3,
      }
    },
    {
      selector: 'node.signal-approaching',
      style: {
        'border-width': 3,
        'border-color': '#00ccff',
        'overlay-color': '#00ccff',
        'overlay-opacity': 0.3,
        'overlay-padding': 10,
        'z-index': 1000,
        'transition-property': 'border-color, overlay-opacity',
        'transition-duration': 0.2,
      }
    },
    {
      selector: 'node.signal-pulse',
      style: {
        'border-width': 4,
        'border-color': '#00ccff',
        'overlay-color': '#00ccff',
        'overlay-opacity': 0.6,
        'overlay-padding': 15,
        'z-index': 1001,
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
    {
      selector: 'edge.dimmed',
      style: {
        'opacity': 0.1,
      }
    },
    {
      selector: 'edge.focused-edge',
      style: {
        'width': 2.5,
        'line-color': '#00ff88',
        'target-arrow-color': '#00ff88',
        'z-index': 997,
      }
    },
    {
      selector: 'edge.signal-wave',
      style: {
        'width': 3,
        'line-color': '#00ccff',
        'target-arrow-color': '#00ccff',
        'z-index': 999,
        'transition-property': 'line-color, width',
        'transition-duration': 0.3,
      }
    },
    {
      selector: 'edge.signal-flow',
      style: {
        'width': 3,
        'line-color': '#00ccff',
        'target-arrow-color': '#00ccff',
        'z-index': 1000,
      }
    },
  ];
}

export default ASTVisualizer;