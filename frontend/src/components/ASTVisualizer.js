import React, { useEffect, useRef, useState, useMemo, useCallback, forwardRef, useImperativeHandle } from 'react';
import logger from '../utils/logger';
import { GestureAction } from '../utils/GestureService';

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
  // Function/Class definitions
  'args': 'Arguments',
  'decorators': 'Decorators',
  'bases': 'Base Classes',
  'is_async': 'Async',
  'returns': 'Return Annotation',
  'type_params': 'Type Parameters',
  
  // Loop and control flow
  'target': 'Loop Variable',
  'has_else': 'Has Else Branch',
  'orelse': 'Else Branch',
  'body': 'Body',
  
  // Function calls
  'args_count': 'Argument Count',
  'kwargs': 'Keyword Arguments',
  'func': 'Function',
  
  // Operators
  'operator': 'Operator',
  'operators': 'Operators',
  'op': 'Operation',
  
  // Imports
  'names': 'Import Names',
  'module': 'Module',
  'level': 'Import Level',
  'asname': 'Alias Name',
  
  // Assignments
  'targets': 'Targets',
  'value': 'Value',
  'annotation': 'Type Annotation',
  
  // Comparisons
  'comparators': 'Comparators',
  'left': 'Left Operand',
  'right': 'Right Operand',
  
  // Subscript/Attribute
  'slice': 'Slice',
  'attr': 'Attribute Name',
  'ctx': 'Context',
  
  // Exception handling
  'type': 'Exception Type',
  'exc': 'Exception',
  'finalbody': 'Finally Block',
  'handlers': 'Exception Handlers',
  
  // Comprehensions
  'generators': 'Generators',
  'iter': 'Iterable',
  'ifs': 'Conditions',
  
  // Literals
  'n': 'Number Value',
  's': 'String Value',
  
  // Other
  'test': 'Condition',
  'items': 'Items',
  'keys': 'Keys',
  'elt': 'Element',
  'dims': 'Dimensions',
};

const ASTVisualizer = forwardRef(function ASTVisualizer({ graph, theme, onGoToLine, gestureEnabled = false }, ref) {
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
  
  // Gesture control state
  const gestureStateRef = useRef({
    isPanning: false,
    lastPanPosition: null,
    isRotating: false,
    lastRotationAngle: null,
  });
  
  // Track timers and animation frames for cleanup
  const timersRef = useRef(new Set());
  const animationFramesRef = useRef(new Set());
  const particleCleanupRef = useRef([]); // Use ref instead of global variable to store particle cleanup functions
  
  // Track Cytoscape initialization state
  const isInitializedRef = useRef(false);
  const pendingElementsRef = useRef(null);
  
  // Search related state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [selectedSearchIndex, setSelectedSearchIndex] = useState(-1);
  const [isSearching, setIsSearching] = useState(false);
  const searchInputRef = useRef(null);

  // Format attribute key using memoized map
  const formatAttrKey = useCallback((key) => ATTR_KEY_MAP[key] || key, []);
  
  // Search debounce ref
  const searchDebounceRef = useRef(null);
  
  // Pointing cursor state
  const [pointingPosition, setPointingPosition] = useState(null); // Screen position in graph
  const [hoveredNode, setHoveredNode] = useState(null); // Currently hovered node
  const [hoverProgress, setHoverProgress] = useState(0); // 0-100 progress
  const hoverTimerRef = useRef(null);
  const hoverStartTimeRef = useRef(null);
  const HOVER_SELECT_TIME = 2000; // 2 seconds to select
  
  // Performance optimization: refs for direct DOM updates
  const cursorDotRef = useRef(null);
  const cursorRingRef = useRef(null);
  const cursorProgressRingRef = useRef(null);
  const lastPositionUpdateRef = useRef(0);
  const POSITION_UPDATE_THROTTLE = 16; // ~60fps
  
  // Clear debounce timer
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, []);
  
  // Gesture control handlers - exposed via ref
  const handleGesture = useCallback((gestureData) => {
    if (!cyRef.current || !gestureEnabled) return;
    
    const cy = cyRef.current;
    const { action, position } = gestureData;
    
    switch (action) {
      case GestureAction.ZOOM_IN:
        cy.zoom(cy.zoom() * 1.05);
        break;
        
      case GestureAction.ZOOM_OUT:
        cy.zoom(cy.zoom() / 1.05);
        break;
        
      case GestureAction.PAN:
        // Pan based on hand position change
        if (gestureStateRef.current.isPanning && gestureStateRef.current.lastPanPosition) {
          const dx = (position.x - gestureStateRef.current.lastPanPosition.x) * 500;
          const dy = (position.y - gestureStateRef.current.lastPanPosition.y) * 500;
          cy.panBy({ x: -dx, y: -dy });
        }
        gestureStateRef.current.isPanning = true;
        gestureStateRef.current.lastPanPosition = position;
        break;
        
      case GestureAction.RESET:
        cy.fit(undefined, 50);
        gestureStateRef.current = {
          isPanning: false,
          lastPanPosition: null,
          isRotating: false,
          lastRotationAngle: null,
        };
        break;
        
      case GestureAction.SELECT:
        // Select node at hand position
        if (position) {
          // Convert normalized position to screen coordinates
          const containerRect = containerRef.current?.getBoundingClientRect();
          if (containerRect) {
            const screenX = containerRect.left + position.x * containerRect.width;
            const screenY = containerRect.top + position.y * containerRect.height;
            
            // Find node at position
            const nodesAtPoint = cy.elements('node').filter(node => {
              const pos = node.renderedPosition();
              const nodeWidth = node.width() / 2;
              const nodeHeight = node.height() / 2;
              const renderedX = containerRect.left + pos.x;
              const renderedY = containerRect.top + pos.y;
              
              return Math.abs(screenX - renderedX) < nodeWidth &&
                     Math.abs(screenY - renderedY) < nodeHeight;
            });
            
            if (nodesAtPoint.length > 0) {
              const node = nodesAtPoint[0];
              node.select();
              setSelectedNode({
                id: node.data().id,
                type: node.data().type,
                name: node.data().name,
                label: node.data().label,
                lineno: node.data().lineno,
                docstring: node.data().docstring,
                sourceCode: node.data().source_code,
                icon: node.data().icon,
                description: node.data().description,
                explanation: node.data().explanation,
                attributes: node.data().attributes,
              });
            }
          }
        }
        break;
        
      case GestureAction.NONE:
      default:
        // Reset gesture state
        gestureStateRef.current.isPanning = false;
        gestureStateRef.current.lastPanPosition = null;
        break;
    }
  }, [gestureEnabled]);
  
  const handleTwoHands = useCallback((twoHandsData) => {
    if (!cyRef.current || !gestureEnabled) return;
    
    const cy = cyRef.current;
    const { pinchScale, panDelta } = twoHandsData;
    
    // Pinch to zoom
    if (Math.abs(pinchScale) > 0.01) {
      const zoomFactor = 1 + pinchScale * 2;
      cy.zoom(cy.zoom() * zoomFactor);
    }
    
    // Pan with two hands
    if (panDelta && (Math.abs(panDelta.x) > 1 || Math.abs(panDelta.y) > 1)) {
      cy.panBy({ x: -panDelta.x, y: -panDelta.y });
    }
  }, [gestureEnabled]);
  
  // Ref to track the current hovering node ID (avoids closure stale state issues)
  const currentHoveredNodeIdRef = useRef(null);
  
  // Pointing cursor handler - converts pointing direction to graph coordinates
  // Performance optimized: direct DOM updates for position, throttled state updates
  const handlePointingDirection = useCallback((pointingData) => {
    if (!cyRef.current || !gestureEnabled || !containerRef.current) return;
    
    // Cancel any pending clear cursor timer (user is pointing again)
    if (clearPointingCursorTimerRef.current) {
      clearTimeout(clearPointingCursorTimerRef.current);
      clearPointingCursorTimerRef.current = null;
    }
    
    const cy = cyRef.current;
    const container = containerRef.current;
    const containerRect = container.getBoundingClientRect();
    
    // Calculate pointing position in graph coordinates
    const graphX = containerRect.width * (1 - pointingData.origin.x);
    const graphY = containerRect.height * pointingData.origin.y;
    
    // Direct DOM update for cursor position (avoids React re-render)
    const now = performance.now();
    if (now - lastPositionUpdateRef.current >= POSITION_UPDATE_THROTTLE) {
      lastPositionUpdateRef.current = now;
      
      // Update cursor dot position via DOM
      if (cursorDotRef.current) {
        cursorDotRef.current.style.left = `${graphX}px`;
        cursorDotRef.current.style.top = `${graphY}px`;
      }
      // Update cursor ring position via DOM
      if (cursorRingRef.current) {
        cursorRingRef.current.style.left = `${graphX}px`;
        cursorRingRef.current.style.top = `${graphY}px`;
      }
      // Update progress ring position via DOM
      if (cursorProgressRingRef.current) {
        cursorProgressRingRef.current.style.left = `${graphX}px`;
        cursorProgressRingRef.current.style.top = `${graphY}px`;
      }
    }
    
    // Initialize cursor if not visible
    if (!pointingPosition) {
      setPointingPosition({ x: graphX, y: graphY });
    }
    
    // Find node at pointing position
    const renderedPosition = cy.pan();
    const zoom = cy.zoom();
    const modelX = (graphX - renderedPosition.x) / zoom;
    const modelY = (graphY - renderedPosition.y) / zoom;
    
    // Find the nearest node (optimized - early exit)
    let nearestNode = null;
    let nearestDistance = Infinity;
    
    const nodes = cy.nodes();
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const nodePos = node.position();
      const nodeWidth = node.width() / 2;
      const nodeHeight = node.height() / 2;
      
      const dx = modelX - nodePos.x;
      const dy = modelY - nodePos.y;
      
      // Quick bounds check before distance calculation
      if (Math.abs(dx) > nodeWidth * 1.5 || Math.abs(dy) > nodeHeight * 1.5) continue;
      
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestNode = node;
      }
    }
    
    // Handle hover state changes
    if (nearestNode) {
      const nodeId = nearestNode.data().id;
      const isNewNode = currentHoveredNodeIdRef.current !== nodeId;
      
      if (isNewNode) {
        currentHoveredNodeIdRef.current = nodeId;
        setHoveredNode({
          id: nodeId,
          type: nearestNode.data().type,
          name: nearestNode.data().name,
        });
        setHoverProgress(0);
        hoverStartTimeRef.current = Date.now();
        
        if (hoverTimerRef.current) {
          cancelAnimationFrame(hoverTimerRef.current);
          hoverTimerRef.current = null;
        }
        
        // Start progress animation (throttled to 30fps for performance)
        let lastProgressUpdate = 0;
        const PROGRESS_UPDATE_INTERVAL = 33; // ~30fps
        
        const updateProgress = () => {
          const now = performance.now();
          if (now - lastProgressUpdate >= PROGRESS_UPDATE_INTERVAL) {
            lastProgressUpdate = now;
            const elapsed = Date.now() - hoverStartTimeRef.current;
            const progress = Math.min(100, (elapsed / HOVER_SELECT_TIME) * 100);
            setHoverProgress(progress);
            
            if (progress >= 100) {
              const currentNodeId = currentHoveredNodeIdRef.current;
              if (currentNodeId) {
                const nodeToSelect = cy.getElementById(currentNodeId);
                if (nodeToSelect) {
                  nodeToSelect.select();
                  setSelectedNode({
                    id: nodeToSelect.data().id,
                    type: nodeToSelect.data().type,
                    name: nodeToSelect.data().name,
                    label: nodeToSelect.data().label,
                    lineno: nodeToSelect.data().lineno,
                    docstring: nodeToSelect.data().docstring,
                    sourceCode: nodeToSelect.data().source_code,
                    icon: nodeToSelect.data().icon,
                    description: nodeToSelect.data().description,
                    explanation: nodeToSelect.data().explanation,
                    attributes: nodeToSelect.data().attributes,
                  });
                }
              }
              currentHoveredNodeIdRef.current = null;
              setHoveredNode(null);
              setHoverProgress(0);
              setPointingPosition(null);
              hoverTimerRef.current = null;
              return;
            }
          }
          hoverTimerRef.current = requestAnimationFrame(updateProgress);
        };
        
        hoverTimerRef.current = requestAnimationFrame(updateProgress);
      }
    } else {
      currentHoveredNodeIdRef.current = null;
      if (hoveredNode) {
        setHoveredNode(null);
        setHoverProgress(0);
        if (hoverTimerRef.current) {
          cancelAnimationFrame(hoverTimerRef.current);
          hoverTimerRef.current = null;
        }
      }
    }
  }, [gestureEnabled, hoveredNode, pointingPosition]);
  
  // Clear pointing cursor with a small delay to avoid flickering during gesture instability
  const clearPointingCursor = useCallback(() => {
    // Don't clear immediately - wait a short moment to see if pointing resumes
    // This prevents the progress animation from being interrupted by brief gesture instability
    const clearTimer = setTimeout(() => {
      // Only clear if we're still not pointing (check via ref)
      if (!currentHoveredNodeIdRef.current) {
        setPointingPosition(null);
        setHoveredNode(null);
        setHoverProgress(0);
        if (hoverTimerRef.current) {
          cancelAnimationFrame(hoverTimerRef.current);
          hoverTimerRef.current = null;
        }
      }
    }, 150); // 150ms grace period
    
    // Store timer for cleanup
    clearPointingCursorTimerRef.current = clearTimer;
  }, []);
  
  // Ref for clear cursor timer
  const clearPointingCursorTimerRef = useRef(null);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) {
        cancelAnimationFrame(hoverTimerRef.current);
      }
    };
  }, []);
  
  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    handleGesture,
    handleTwoHands,
    handlePointingDirection,
    clearPointingCursor,
    zoomIn: () => cyRef.current?.zoom(cyRef.current.zoom() * 1.4),
    zoomOut: () => cyRef.current?.zoom(cyRef.current.zoom() / 1.4),
    fit: () => cyRef.current?.fit(undefined, 50),
    getZoom: () => cyRef.current?.zoom(),
  }), [handleGesture, handleTwoHands, handlePointingDirection, clearPointingCursor]);
  
  // Clear debounce timer
  
  // Search nodes (with debounce)
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    setSelectedSearchIndex(-1);
    
    // Clear previous debounce timer
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    
    // Empty query clears immediately
    if (!query.trim() || !graph) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    
    // Show searching indicator
    setIsSearching(true);
    
    // Set debounce (200ms)
    searchDebounceRef.current = setTimeout(() => {
      const lowerQuery = query.toLowerCase().trim();
      const results = graph.nodes.filter(node => {
        // Ensure node is a valid object
        if (!node || !node.id) return false;
        
        const name = (node.name || '').toLowerCase();
        const type = (node.type || '').toLowerCase();
        const label = (node.detailed_label || '').toLowerCase();
        const description = (node.description || '').toLowerCase();
        
        return name.includes(lowerQuery) ||
               type.includes(lowerQuery) ||
               label.includes(lowerQuery) ||
               description.includes(lowerQuery);
      }).slice(0, 20); // Limit result count
      
      setSearchResults(results);
      setIsSearching(false);
    }, 200);
  }, [graph]);
  
  // Clear search
  const clearSearch = useCallback(() => {
    setSearchQuery('');
    setSearchResults([]);
    setSelectedSearchIndex(-1);
    setIsSearchOpen(false);
    
    // Remove all highlights
    if (cyRef.current) {
      cyRef.current.elements().removeClass('search-highlight search-selected');
    }
  }, []);
  
  // Focus on search result
  const focusSearchResult = useCallback((node, index) => {
    // Strict null check
    if (!cyRef.current) return;
    if (!node || typeof node !== 'object' || !node.id) return;
    
    setSelectedSearchIndex(index);
    
    // Remove previous highlight
    cyRef.current.elements().removeClass('search-selected');
    
    // Highlight selected node
    const cyNode = cyRef.current.getElementById(node.id);
    if (cyNode) {
      cyNode.addClass('search-selected');
      
      // Animate focus to node
      cyRef.current.animate({
        zoom: 1.5,
        center: { eles: cyNode },
        duration: 300
      });
      
      // Update selected node info
      const nodeData = cyNode.data();
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
    }
  }, []);
  
  // Jump to editor line
  const handleGoToLine = useCallback((node) => {
    if (node && onGoToLine && node.lineno) {
      onGoToLine(node.lineno, node.end_lineno);
    }
    // Clear search
    clearSearch();
  }, [onGoToLine, clearSearch]);
  
  // Keyboard navigation for search results
  const handleSearchKeyDown = useCallback((e) => {
    if (searchResults.length === 0) return;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        const nextIndex = (selectedSearchIndex + 1) % searchResults.length;
        focusSearchResult(searchResults[nextIndex], nextIndex);
        break;
      case 'ArrowUp':
        e.preventDefault();
        const prevIndex = selectedSearchIndex <= 0 ? searchResults.length - 1 : selectedSearchIndex - 1;
        focusSearchResult(searchResults[prevIndex], prevIndex);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedSearchIndex >= 0 && searchResults[selectedSearchIndex]) {
          handleGoToLine(searchResults[selectedSearchIndex]);
        } else if (searchResults.length > 0) {
          focusSearchResult(searchResults[0], 0);
        }
        break;
      case 'Escape':
        clearSearch();
        break;
      default:
        break;
    }
  }, [searchResults, selectedSearchIndex, focusSearchResult, handleGoToLine, clearSearch]);
  
  // Highlight search results
  useEffect(() => {
    if (!cyRef.current) return;
    
    // Remove previous search highlights
    cyRef.current.elements().removeClass('search-highlight');
    
    // Highlight new search results
    searchResults.forEach(node => {
      if (!node || !node.id) return;
      const cyNode = cyRef.current.getElementById(node.id);
      if (cyNode) {
        cyNode.addClass('search-highlight');
      }
    });
  }, [searchResults]);

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
        
        // Dynamically adjust size based on label length
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
        
        // Limit max width
        width = Math.min(width, 200);
        
        return {
          data: {
            id: node.id,
            // Use detailed label or combined label
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
        
        // Mark initialization complete
        isInitializedRef.current = true;
        
        // If there are pending elements, apply immediately
        if (pendingElementsRef.current) {
          const pending = pendingElementsRef.current;
          pendingElementsRef.current = null;
          
          setIsRendering(true);
          cy.json({ elements: pending });
          const layoutConfig = getLayoutConfig(pending.nodes.length, 'dagre');
          const layout = cy.layout(layoutConfig);
          layout.on('layoutstop', () => {
            if (cyRef.current) {
              cyRef.current.fit(undefined, 50);
              setIsRendering(false);
            }
          });
          layout.run();
        }

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
        logger.error('Failed to initialize Cytoscape', { error: error.message });
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
      // Use global counter + random number to ensure unique ID, avoiding conflicts during rapid operations
      const particleIdCounter = { current: 0 };
      const generateParticleId = () => {
        particleIdCounter.current += 1;
        return `particle_${Date.now()}_${particleIdCounter.current}_${Math.random().toString(36).substr(2, 5)}`;
      };
      
      propagationQueue.forEach(({ sourceNode, targetNode, delay }) => {
        // Create particle after delay (tracked for cleanup)
        const timerId = setTimeout(() => {
          // Check if component is still mounted
          if (!cyRef.current) return;
          
          // Get current positions at animation time
          const sourcePos = sourceNode.renderedPosition();
          const targetPos = targetNode.renderedPosition();
          
          // Calculate edge length
          const dx = targetPos.x - sourcePos.x;
          const dy = targetPos.y - sourcePos.y;
          const edgeLength = Math.sqrt(dx * dx + dy * dy);
          
          // Create unique particle ID using the generator function
          const uniqueParticleId = generateParticleId();
          
          const particle = {
            id: uniqueParticleId,
            sourceId: sourceNode.id(),
            targetId: targetNode.id(),
            startX: sourcePos.x,
            startY: sourcePos.y,
            endX: targetPos.x,
            endY: targetPos.y,
            progress: 0,
            startTime: Date.now(),
            duration: edgeLength / particleSpeed,
          };
          
          // Add particle to state
          setSignalParticles(prev => [...prev, particle]);
          
          // Add signal class to target node when particle is approaching
          let signalAdded = false;
          let animationCancelled = false;
          let currentFrameId = null;
          
          // Animate particle (tracked for cleanup)
          const animateParticle = () => {
            // Check if animation was cancelled or component unmounted
            if (animationCancelled || !cyRef.current) return;
            
            const elapsed = Date.now() - particle.startTime;
            const progress = Math.min(elapsed / particle.duration, 1);
            
            // Add signal class when particle is halfway
            if (progress > 0.5 && !signalAdded) {
              targetNode.addClass('signal-approaching');
              signalAdded = true;
            }
            
            if (progress < 1) {
              setSignalParticles(prev => 
                prev.map(p => p.id === uniqueParticleId ? { ...p, progress } : p)
              );
              currentFrameId = requestAnimationFrame(animateParticle);
              animationFramesRef.current.add(currentFrameId);
            } else {
              // Remove particle when done
              setSignalParticles(prev => prev.filter(p => p.id !== uniqueParticleId));
              
              // Transition to pulse effect
              targetNode.removeClass('signal-approaching');
              targetNode.addClass('signal-pulse');
              const pulseTimerId = setTimeout(() => {
                targetNode.removeClass('signal-pulse');
                timersRef.current.delete(pulseTimerId);
              }, 400);
              timersRef.current.add(pulseTimerId);
            }
          };
          
          currentFrameId = requestAnimationFrame(animateParticle);
          animationFramesRef.current.add(currentFrameId);
          
          // Register cleanup function
          const cancelAnimation = () => {
            animationCancelled = true;
            if (currentFrameId) {
              cancelAnimationFrame(currentFrameId);
              animationFramesRef.current.delete(currentFrameId);
            }
          };
          particleCleanupRef.current.push(cancelAnimation);
        }, delay);
        timersRef.current.add(timerId);
      });
    }

    requestAnimationFrame(initCytoscape);

    return () => {
      mounted = false;
      
      // Clear search debounce timer
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
      
      // Cancel all particle animations
      if (particleCleanupRef.current) {
        particleCleanupRef.current.forEach(cancel => cancel());
        particleCleanupRef.current = [];
      }
      
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
          // Remove all event listeners before destroy to prevent memory leaks
          cyRef.current.removeAllListeners();
          cyRef.current.destroy();
        } catch (e) {
          // Log warning but don't crash - destroy may fail if already destroyed
          logger.warn('Cytoscape cleanup error', { message: e.message });
        }
        cyRef.current = null;
      }
      
      // Reset initialization state so component can reinitialize on remount
      isInitializedRef.current = false;
      pendingElementsRef.current = null;
    };
  }, [getLayoutConfig]); // Include getLayoutConfig since it's used inside

  // Update elements when data changes (incremental update)
  useEffect(() => {
    if (cytoscapeElements.nodes.length === 0) return;
    
    // If Cytoscape hasn't initialized yet, save elements and wait
    if (!isInitializedRef.current || !cyRef.current) {
      pendingElementsRef.current = cytoscapeElements;
      return;
    }
    
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
      // Don't handle keyboard navigation if search box or any input is focused
      const activeElement = document.activeElement;
      const isInputFocused = activeElement && (
        activeElement.tagName === 'INPUT' ||
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.isContentEditable
      );
      
      if (isInputFocused) {
        return;
      }
      
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
          {/* Search button */}
          <button 
            className={`btn btn-ghost ${isSearchOpen ? 'active' : ''}`}
            onClick={() => {
              setIsSearchOpen(!isSearchOpen);
              if (!isSearchOpen) {
                setTimeout(() => searchInputRef.current?.focus(), 100);
              } else {
                clearSearch();
              }
            }}
            title="Search nodes (Ctrl+F)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </button>
          
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
        {/* Search panel */}
        {isSearchOpen && (
          <div className="search-panel">
            <div className="search-input-wrapper">
              <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                ref={searchInputRef}
                type="text"
                className="search-input"
                placeholder="Search functions, classes, variables..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                onKeyDown={handleSearchKeyDown}
              />
              {searchQuery && (
                <button className="search-clear" onClick={clearSearch}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
            
            {/* Search results list */}
            {isSearching ? (
              <div className="search-loading">
                <div className="search-loading-spinner"></div>
                <span>Searching...</span>
              </div>
            ) : searchResults.length > 0 ? (
              <div className="search-results">
                <div className="search-results-header">
                  <span>Found {searchResults.length} results</span>
                  <span className="search-hint">Up/Down to navigate - Enter to jump - Esc to close</span>
                </div>
                <div className="search-results-list">
                  {searchResults.filter(node => node && node.id).map((node, index) => (
                    <div
                      key={node.id}
                      className={`search-result-item ${index === selectedSearchIndex ? 'selected' : ''}`}
                      onClick={() => {
                        try {
                          if (node && node.id) {
                            focusSearchResult(node, index);
                            handleGoToLine(node);
                          }
                        } catch (e) {
                          logger.warn('Search result click error', { error: e.message });
                        }
                      }}
                      onMouseEnter={() => {
                        try {
                          if (node && node.id) {
                            focusSearchResult(node, index);
                          }
                        } catch (e) {
                          logger.warn('Search result hover error', { error: e.message });
                        }
                      }}
                    >
                      <span className="result-icon">{node.icon || '•'}</span>
                      <div className="result-content">
                        <span className="result-name">{node.name || node.type}</span>
                        <span className="result-type">{node.description || node.type}</span>
                      </div>
                      {node.lineno && (
                        <span className="result-line">Line {node.lineno}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : searchQuery ? (
              <div className="search-no-results">
                <span>No matching nodes found</span>
              </div>
            ) : null}
          </div>
        )}
        
        {isRendering && (
          <div className="rendering-overlay">
            <div className="rendering-spinner"></div>
            <span>Rendering {displayedNodes} nodes...</span>
          </div>
        )}
        <div className="cytoscape-container" ref={containerRef}></div>
        
        {/* Pointing cursor overlay - optimized for performance */}
        {pointingPosition && gestureEnabled && (
          <div className="pointing-cursor-overlay">
            {/* Outer ring - indicates hoverable area */}
            {hoveredNode && (
              <div 
                ref={cursorRingRef}
                className="pointing-cursor-ring"
                style={{
                  left: pointingPosition.x,
                  top: pointingPosition.y,
                }}
              />
            )}
            {/* Center dot */}
            <div 
              ref={cursorDotRef}
              className="pointing-cursor-dot"
              style={{
                left: pointingPosition.x,
                top: pointingPosition.y,
              }}
            />
            {/* Progress ring - only render when hovering a node with progress */}
            {hoveredNode && hoverProgress > 0 && (
              <svg 
                ref={cursorProgressRingRef}
                className="pointing-progress-ring"
                style={{
                  left: pointingPosition.x,
                  top: pointingPosition.y,
                  transform: 'translate(-50%, -50%)',
                }}
                width="50" 
                height="50"
                viewBox="0 0 50 50"
              >
                <circle
                  className="progress-ring-bg"
                  cx="25"
                  cy="25"
                  r="20"
                  strokeWidth="3"
                />
                <circle
                  className="progress-ring-fill"
                  cx="25"
                  cy="25"
                  r="20"
                  strokeWidth="3"
                  strokeDasharray={`${hoverProgress * 1.256} 125.6`}
                  transform="rotate(-90 25 25)"
                />
              </svg>
            )}
          </div>
        )}
        
        {/* Hover progress indicator on node */}
        {hoveredNode && hoverProgress > 0 && (
          <div className="hover-progress-indicator">
            <div 
              className="hover-progress-bar"
              style={{ width: `${hoverProgress}%` }}
            />
            <span className="hover-progress-text">{hoveredNode.name || hoveredNode.type}</span>
          </div>
        )}
        
        {/* Signal particles overlay */}
        <svg className="particles-overlay">
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <radialGradient id="particleGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1"/>
              <stop offset="50%" stopColor="#ffffff" stopOpacity="0.6"/>
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
            </radialGradient>
          </defs>
          {signalParticles.map(particle => {
            const x = particle.startX + (particle.endX - particle.startX) * particle.progress;
            const y = particle.startY + (particle.endY - particle.startY) * particle.progress;
            // Use more unique key: sourceId-targetId-timestamp combination
            const uniqueKey = `${particle.sourceId || 'src'}-${particle.targetId || 'tgt'}-${particle.id}-${particle.startTime || 0}`;
            return (
              <g key={uniqueKey}>
                {/* Trail effect - simplified */}
                <line
                  x1={particle.startX + (particle.endX - particle.startX) * Math.max(0, particle.progress - 0.2)}
                  y1={particle.startY + (particle.endY - particle.startY) * Math.max(0, particle.progress - 0.2)}
                  x2={x}
                  y2={y}
                  stroke="url(#particleGradient)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  opacity={0.7}
                />
                {/* Particle head - white */}
                <circle
                  cx={x}
                  cy={y}
                  r="5"
                  fill="#ffffff"
                  filter="url(#glow)"
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
                  <span className="detail-label">Code Structure</span>
                  <code className="detail-code">{selectedNode.label}</code>
                </div>
              )}
              
              {selectedNode.lineno && (
                <div className="detail-item">
                  <span className="detail-label">Location</span>
                  <span className="detail-value">Line {selectedNode.lineno}</span>
                </div>
              )}
              
              {selectedNode.explanation && (
                <div className="detail-item explanation">
                  <span className="detail-label">Description</span>
                  <p className="explanation-text">{selectedNode.explanation}</p>
                </div>
              )}
              
              {selectedNode.docstring && (
                <div className="detail-item">
                  <span className="detail-label">Docstring</span>
                  <p className="docstring">{selectedNode.docstring}</p>
                </div>
              )}
              
              {selectedNode.attributes && Object.keys(selectedNode.attributes).length > 0 && (
                <div className="detail-item">
                  <span className="detail-label">Attributes</span>
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
                  <span className="detail-label">Source Code</span>
                  <pre className="source-code">{selectedNode.sourceCode}</pre>
                </div>
              )}
              
              {/* NEW: Inheritance Relationships */}
              {selectedNode.baseClasses && selectedNode.baseClasses.length > 0 && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Inherits From</span>
                  <div className="relationship-list">
                    {selectedNode.baseClasses.map((base, idx) => (
                      <span key={idx} className="relationship-tag inheritance">{base}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedNode.derivedClasses && selectedNode.derivedClasses.length > 0 && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Derived By</span>
                  <div className="relationship-list">
                    {selectedNode.derivedClasses.map((derived, idx) => (
                      <span key={idx} className="relationship-tag derived">{derived}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedNode.inheritanceDepth !== undefined && selectedNode.inheritanceDepth > 0 && (
                <div className="detail-item">
                  <span className="detail-label">Inheritance Depth</span>
                  <span className="detail-value metric">{selectedNode.inheritanceDepth}</span>
                </div>
              )}
              
              {/* NEW: Class Methods */}
              {selectedNode.methods && selectedNode.methods.length > 0 && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Methods ({selectedNode.methods.length})</span>
                  <div className="relationship-list methods">
                    {selectedNode.methods.slice(0, 8).map((method, idx) => (
                      <span key={idx} className="relationship-tag method">{method}</span>
                    ))}
                    {selectedNode.methods.length > 8 && (
                      <span className="relationship-tag more">+{selectedNode.methods.length - 8} more</span>
                    )}
                  </div>
                </div>
              )}
              
              {selectedNode.overriddenMethods && selectedNode.overriddenMethods.length > 0 && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Overrides</span>
                  <div className="relationship-list">
                    {selectedNode.overriddenMethods.map((method, idx) => (
                      <span key={idx} className="relationship-tag override">{method}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* NEW: Decorators */}
              {selectedNode.decorators && selectedNode.decorators.length > 0 && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Decorators</span>
                  <div className="relationship-list">
                    {selectedNode.decorators.map((dec, idx) => (
                      <span key={idx} className="relationship-tag decorator">@{dec}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* NEW: Function Call Relationships */}
              {selectedNode.functionsCalled && selectedNode.functionsCalled.length > 0 && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Calls</span>
                  <div className="relationship-list">
                    {selectedNode.functionsCalled.slice(0, 6).map((func, idx) => (
                      <span key={idx} className="relationship-tag call">{func}</span>
                    ))}
                    {selectedNode.functionsCalled.length > 6 && (
                      <span className="relationship-tag more">+{selectedNode.functionsCalled.length - 6} more</span>
                    )}
                  </div>
                </div>
              )}
              
              {selectedNode.isCalledCount !== undefined && selectedNode.isCalledCount > 0 && (
                <div className="detail-item">
                  <span className="detail-label">Called Count</span>
                  <span className="detail-value metric">{selectedNode.isCalledCount} times</span>
                </div>
              )}
              
              {/* NEW: Code Patterns */}
              {(selectedNode.branchCount > 0 || selectedNode.loopCount > 0 || selectedNode.exceptionHandlers > 0) && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Code Patterns</span>
                  <div className="relationship-list patterns">
                    {selectedNode.branchCount > 0 && (
                      <span className="relationship-tag pattern">branches: {selectedNode.branchCount}</span>
                    )}
                    {selectedNode.loopCount > 0 && (
                      <span className="relationship-tag pattern">loops: {selectedNode.loopCount}</span>
                    )}
                    {selectedNode.exceptionHandlers > 0 && (
                      <span className="relationship-tag pattern">excepts: {selectedNode.exceptionHandlers}</span>
                    )}
                  </div>
                </div>
              )}
              
              {/* NEW: Scope Info */}
              {selectedNode.scopeLevel !== undefined && selectedNode.scopeLevel > 0 && (
                <div className="detail-item">
                  <span className="detail-label">Scope Level</span>
                  <span className="detail-value metric">{selectedNode.scopeLevel}</span>
                </div>
              )}
              
              {/* NEW: Code Flags */}
              {(selectedNode.isAsync || selectedNode.isGenerator || selectedNode.hasRecursion) && (
                <div className="detail-item relationship-section">
                  <span className="detail-label">Special Flags</span>
                  <div className="relationship-list flags">
                    {selectedNode.isAsync && (
                      <span className="relationship-tag flag async">async</span>
                    )}
                    {selectedNode.isGenerator && (
                      <span className="relationship-tag flag generator">generator</span>
                    )}
                    {selectedNode.hasRecursion && (
                      <span className="relationship-tag flag recursion">recursive</span>
                    )}
                  </div>
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
        <div className="legend-hint">Double-click to focus | Long-press for details | WASD/Arrow keys to move</div>
      </div>
    </div>
  );
});

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
        'border-color': '#ffffff',
        'z-index': 1000,
        'overlay-color': '#ffffff',
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
        'border-color': '#ffffff',
        'opacity': 0.9,
        'z-index': 999,
      }
    },
    {
      selector: 'node.signal-wave',
      style: {
        'border-width': 3,
        'border-color': '#ffffff',
        'overlay-color': '#ffffff',
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
        'border-color': '#ffffff',
        'overlay-color': '#ffffff',
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
        'border-color': '#ffffff',
        'overlay-color': '#ffffff',
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
        'line-color': '#ffffff',
        'target-arrow-color': '#ffffff',
        'z-index': 997,
      }
    },
    {
      selector: 'edge.signal-wave',
      style: {
        'width': 2,
        'line-color': '#ffffff',
        'target-arrow-color': '#ffffff',
        'z-index': 999,
        'transition-property': 'line-color, width',
        'transition-duration': 0.3,
      }
    },
    {
      selector: 'edge.signal-flow',
      style: {
        'width': 2,
        'line-color': '#ffffff',
        'target-arrow-color': '#ffffff',
        'z-index': 1000,
      }
    },
  ];
}

export default ASTVisualizer;
