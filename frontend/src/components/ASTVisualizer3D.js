import React, { useEffect, useRef, useState, useMemo, useCallback, Suspense, forwardRef, useImperativeHandle, memo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Line, Billboard } from '@react-three/drei';
import * as THREE from 'three';
import logger from '../utils/logger';
import { GestureAction } from '../utils/GestureService';

// Performance constants
const MAX_NODES_3D = 200;
const NODE_SPACING = 3;

/**
 * Check if WebGL is supported and available
 * @returns {{ supported: boolean, reason: string|null }}
 */
function checkWebGLSupport() {
  try {
    // Check if we're in a browser environment
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return { supported: false, reason: 'Not in browser environment' };
    }
    
    // Create a test canvas
    const testCanvas = document.createElement('canvas');
    
    // Try to get WebGL context
    const gl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');
    
    if (!gl) {
      // Try WebGL2
      const gl2 = testCanvas.getContext('webgl2');
      if (!gl2) {
        return { supported: false, reason: 'WebGL is not supported by your browser or GPU' };
      }
    }
    
    // Check for WebGL extensions
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    if (debugInfo) {
      const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
      // Check for software renderers that might have issues
      if (renderer && (
        renderer.includes('SwiftShader') || 
        renderer.includes('llvmpipe') ||
        renderer.includes('Software')
      )) {
        logger.warn('WebGL running in software mode, performance may be limited', { renderer });
      }
    }
    
    // Clean up
    const ext = gl.getExtension('WEBGL_lose_context');
    if (ext) {
      ext.loseContext();
    }
    
    return { supported: true, reason: null };
  } catch (e) {
    return { supported: false, reason: `WebGL check failed: ${e.message}` };
  }
}

// Layout types
const LAYOUT_TYPES = {
  HIERARCHICAL: 'hierarchical',
  SCOPE_GROUPED: 'scope-grouped',
  FORCE_DIRECTED: 'force-directed'
};

// Color palette for different node types
const NODE_COLORS = {
  module: '#ffffff',
  function: '#e0e0e0',
  class: '#c0c0c0',
  if: '#a0a0a0',
  for: '#a0a0a0',
  while: '#a0a0a0',
  try: '#909090',
  with: '#909090',
  call: '#707070',
  assign: '#505050',
  return: '#606060',
  import: '#808080',
  default: '#404040'
};

// Node type to category mapping
const TYPE_CATEGORIES = {
  module: 'structure',
  function: 'structure',
  class: 'structure',
  if: 'control',
  for: 'control',
  while: 'control',
  try: 'control',
  with: 'control',
  call: 'expression',
  assign: 'expression',
  return: 'expression',
  import: 'other',
  default: 'other'
};

/**
 * Get node hierarchy level
 */
function getNodeLevel(node, allNodes) {
  let level = 0;
  let current = node;
  const visited = new Set();
  const nodeMap = new Map(allNodes.map(n => [n.id, n]));
  
  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    if (current.parent) {
      const parent = nodeMap.get(current.parent);
      if (parent) {
        current = parent;
        level++;
      } else {
        break;
      }
    } else {
      break;
    }
  }
  
  return level;
}

/**
 * Hierarchical tree layout - clean vertical tree structure
 */
function computeHierarchicalLayout(nodes, edges) {
  if (nodes.length === 0) return new Map();
  
  const positions = new Map();
  
  // Build children map
  const childrenMap = new Map();
  nodes.forEach(n => childrenMap.set(n.id, []));
  edges.forEach(edge => {
    if (edge.type === 'parent-child' && childrenMap.has(edge.source)) {
      childrenMap.get(edge.source).push(edge.target);
    }
  });
  
  // Calculate subtree widths
  const subtreeWidths = new Map();
  
  function calculateSubtreeWidth(nodeId) {
    const children = childrenMap.get(nodeId) || [];
    if (children.length === 0) {
      subtreeWidths.set(nodeId, 1);
      return 1;
    }
    let width = 0;
    children.forEach(childId => {
      width += calculateSubtreeWidth(childId);
    });
    subtreeWidths.set(nodeId, width);
    return width;
  }
  
  // Find root (module or node without parent)
  const root = nodes.find(n => !n.parent) || nodes[0];
  if (root) {
    calculateSubtreeWidth(root.id);
  }
  
  // Position nodes using Reingold-Tilford style algorithm
  function positionNode(nodeId, x, y, z, leftBound, rightBound) {
    const children = childrenMap.get(nodeId) || [];
    
    // Position current node
    positions.set(nodeId, { x, y, z, vx: 0, vy: 0, vz: 0 });
    
    if (children.length === 0) return;
    
    const childSpacing = (rightBound - leftBound) / children.length;
    const levelHeight = NODE_SPACING * 1.5;
    
    children.forEach((childId, index) => {
      const childLeft = leftBound + index * childSpacing;
      const childRight = childLeft + childSpacing;
      const childX = (childLeft + childRight) / 2;
      const childZ = 0;
      
      positionNode(childId, childX, y - levelHeight, childZ, childLeft, childRight);
    });
  }
  
  // Start positioning from root
  const totalWidth = subtreeWidths.get(root?.id) || nodes.length;
  positionNode(root?.id, 0, 0, 0, -totalWidth * NODE_SPACING / 2, totalWidth * NODE_SPACING / 2);
  
  // Handle orphan nodes
  let orphanZ = 10;
  nodes.forEach(node => {
    if (!positions.has(node.id)) {
      positions.set(node.id, {
        x: (Math.random() - 0.5) * 20,
        y: -getNodeLevel(node, nodes) * NODE_SPACING * 1.5,
        z: orphanZ,
        vx: 0, vy: 0, vz: 0
      });
      orphanZ += 2;
    }
  });
  
  return positions;
}

/**
 * Scope-grouped layout - groups nodes by their scope (function/class)
 */
function computeScopeGroupedLayout(nodes, edges) {
  if (nodes.length === 0) return new Map();
  
  const positions = new Map();
  
  // Group nodes by scope
  const scopeGroups = new Map(); // scope_name -> [nodes]
  const scopePositions = new Map(); // scope_name -> {x, y, z}
  
  nodes.forEach(node => {
    const scopeName = node.scope_name || '__root__';
    if (!scopeGroups.has(scopeName)) {
      scopeGroups.set(scopeName, []);
    }
    scopeGroups.get(scopeName).push(node);
  });
  
  // Arrange scope groups in a grid
  const scopeNames = Array.from(scopeGroups.keys());
  const gridCols = Math.ceil(Math.sqrt(scopeNames.length));
  const gridSpacing = 15;
  
  scopeNames.forEach((scopeName, index) => {
    const row = Math.floor(index / gridCols);
    const col = index % gridCols;
    scopePositions.set(scopeName, {
      x: (col - gridCols / 2) * gridSpacing,
      y: -row * gridSpacing * 0.8,
      z: 0
    });
  });
  
  // Position nodes within each scope group in a circle
  scopeGroups.forEach((groupNodes, scopeName) => {
    const scopePos = scopePositions.get(scopeName);
    const radius = Math.max(3, groupNodes.length * 0.5);
    
    groupNodes.forEach((node, index) => {
      const angle = (index / groupNodes.length) * Math.PI * 2;
      const innerRadius = groupNodes.length > 1 ? radius : 0;
      
      positions.set(node.id, {
        x: scopePos.x + Math.cos(angle) * innerRadius,
        y: scopePos.y + Math.sin(angle) * innerRadius * 0.5,
        z: scopePos.z + (index % 2 === 0 ? 1 : -1) * (index * 0.2),
        vx: 0, vy: 0, vz: 0
      });
    });
  });
  
  return positions;
}

/**
 * Optimized force-directed layout with better parameters
 */
function computeOptimizedForceLayout(nodes, edges, iterations = 150) {
  if (nodes.length === 0) return new Map();
  
  const positions = new Map();
  const nodeMap = new Map();
  
  // Initialize positions based on hierarchy
  nodes.forEach((node, i) => {
    const level = getNodeLevel(node, nodes);
    const angle = (i / nodes.length) * Math.PI * 2;
    const radius = level * NODE_SPACING * 1.5;
    
    positions.set(node.id, {
      x: Math.cos(angle) * radius,
      y: -level * NODE_SPACING * 1.2, // Negative for downward tree
      z: Math.sin(angle) * radius * 0.3, // Flatter in Z
      vx: 0, vy: 0, vz: 0
    });
    nodeMap.set(node.id, node);
  });
  
  // Build adjacency list
  const adjacency = new Map();
  nodes.forEach(node => adjacency.set(node.id, new Set()));
  edges.forEach(edge => {
    if (adjacency.has(edge.source)) {
      adjacency.get(edge.source).add(edge.target);
    }
    if (adjacency.has(edge.target)) {
      adjacency.get(edge.target).add(edge.source);
    }
  });
  
  // Optimized force parameters
  const repulsion = 25; // Increased repulsion
  const attraction = 0.03; // Decreased attraction
  const damping = 0.85;
  const gravity = 0.02;
  const levelSpacing = 5; // Strong level separation
  
  for (let iter = 0; iter < iterations; iter++) {
    // Repulsion between all nodes
    const posArray = Array.from(positions.entries());
    for (let i = 0; i < posArray.length; i++) {
      for (let j = i + 1; j < posArray.length; j++) {
        const [, p1] = posArray[i];
        const [, p2] = posArray[j];
        
        const dx = p1.x - p2.x;
        const dy = p1.y - p2.y;
        const dz = p1.z - p2.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        
        const force = repulsion / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const fz = (dz / dist) * force;
        
        p1.vx += fx;
        p1.vy += fy;
        p1.vz += fz;
        p2.vx -= fx;
        p2.vy -= fy;
        p2.vz -= fz;
      }
    }
    
    // Attraction along edges
    edges.forEach(edge => {
      const p1 = positions.get(edge.source);
      const p2 = positions.get(edge.target);
      if (!p1 || !p2) return;
      
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const dz = p2.z - p1.z;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
      
      const force = (dist - NODE_SPACING * 2.5) * attraction;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      const fz = (dz / dist) * force;
      
      p1.vx += fx;
      p1.vy += fy;
      p1.vz += fz;
      p2.vx -= fx;
      p2.vy -= fy;
      p2.vz -= fz;
    });
    
    // Level-based Y position constraint
    positions.forEach((p, nodeId) => {
      const node = nodeMap.get(nodeId);
      const targetY = -getNodeLevel(node, nodes) * levelSpacing;
      p.vy += (targetY - p.y) * 0.1; // Pull towards level position
    });
    
    // Gravity toward center
    positions.forEach(p => {
      p.vx -= p.x * gravity;
      p.vy -= p.y * gravity * 0.3; // Less vertical gravity
      p.vz -= p.z * gravity;
    });
    
    // Apply velocity with damping
    positions.forEach(p => {
      p.vx *= damping;
      p.vy *= damping;
      p.vz *= damping;
      p.x += p.vx;
      p.y += p.vy;
      p.z += p.vz;
    });
  }
  
  return positions;
}

/**
 * Main layout function dispatcher
 */
function computeLayout(nodes, edges, layoutType) {
  switch (layoutType) {
    case LAYOUT_TYPES.HIERARCHICAL:
      return computeHierarchicalLayout(nodes, edges);
    case LAYOUT_TYPES.SCOPE_GROUPED:
      return computeScopeGroupedLayout(nodes, edges);
    case LAYOUT_TYPES.FORCE_DIRECTED:
    default:
      return computeOptimizedForceLayout(nodes, edges);
  }
}

/**
 * 3D Node component - memoized for performance
 */
const Node3D = memo(function Node3D({ position, node, isSelected, isFocused, isDimmed, isSignal, onClick, onLongPress, theme }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);
  const longPressTimer = useRef(null);
  const pointerDownTime = useRef(0);
  const signalRef = useRef(0);
  const [signalIntensity, setSignalIntensity] = useState(0);
  // Use ref to track last rendered signal intensity to avoid frequent state updates
  const lastSignalIntensityRef = useRef(0);
  // Use ref to store target scale vector to avoid creating new objects each frame
  const targetScaleRef = useRef(new THREE.Vector3(0.5, 0.5, 0.5));
  // State update threshold, only trigger update when change exceeds this value
  const SIGNAL_UPDATE_THRESHOLD = 0.05;
  // Throttle update counter
  const frameCountRef = useRef(0);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (longPressTimer.current) {
        clearTimeout(longPressTimer.current);
        longPressTimer.current = null;
      }
    };
  }, []);
  
  const color = NODE_COLORS[node.type?.toLowerCase()] || NODE_COLORS.default;
  const category = TYPE_CATEGORIES[node.type?.toLowerCase()] || TYPE_CATEGORIES.default;
  
  // Node size based on category and state
  const baseSize = category === 'structure' ? 0.5 : 
                   category === 'control' ? 0.4 : 0.3;
  const size = isFocused ? baseSize * 1.5 : isSelected ? baseSize * 1.3 : hovered ? baseSize * 1.15 : baseSize;
  
  // 更新目标缩放向量（只在 size 变化时）
  useEffect(() => {
    targetScaleRef.current.set(size, size, size);
  }, [size]);
  
  // Animation - 优化版本
  useFrame(() => {
    if (meshRef.current) {
      // 使用预先创建的向量进行插值
      meshRef.current.scale.lerp(targetScaleRef.current, 0.1);
    }
    
    // Signal wave animation - smooth fade in/out
    if (isSignal) {
      // Quick fade in
      signalRef.current = Math.min(signalRef.current + 0.08, 1);
    } else {
      // Slow fade out
      signalRef.current = Math.max(signalRef.current - 0.03, 0);
    }
    
    // 节流更新：每3帧检查一次信号强度
    frameCountRef.current++;
    if (frameCountRef.current % 3 !== 0) return;
    
    // 仅在信号强度变化超过阈值时才更新状态，减少不必要的重渲染
    const intensityDiff = Math.abs(signalRef.current - lastSignalIntensityRef.current);
    if (intensityDiff >= SIGNAL_UPDATE_THRESHOLD || 
        (signalRef.current === 0 && lastSignalIntensityRef.current !== 0) ||
        (signalRef.current === 1 && lastSignalIntensityRef.current !== 1)) {
      lastSignalIntensityRef.current = signalRef.current;
      setSignalIntensity(signalRef.current);
    }
  });
  const handlePointerDown = useCallback((e) => {
    e.stopPropagation();
    pointerDownTime.current = Date.now();
    longPressTimer.current = setTimeout(() => {
      onLongPress(node);
    }, 500); // 500ms for long press
  }, [node, onLongPress]);
  
  const handlePointerUp = useCallback((e) => {
    e.stopPropagation();
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
    // If it was a short press (not long), trigger click
    const pressDuration = Date.now() - pointerDownTime.current;
    if (pressDuration < 500) {
      onClick(node);
    }
  }, [node, onClick]);
  
  const handlePointerLeave = useCallback(() => {
    setHovered(false);
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);
  
  // Shape based on type (optimized with lower poly count)
  const geometry = category === 'structure' ? 
    <boxGeometry args={[1, 0.6, 0.6]} /> :
    category === 'control' ?
    <octahedronGeometry args={[0.5]} /> :
    <sphereGeometry args={[0.4, 12, 12]} />;
  
  // Calculate opacity
  const opacity = isDimmed ? 0.2 : 1;
  
  // Determine colors based on signal intensity (theme-adaptive)
  const hasSignal = signalIntensity > 0;
  const signalColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const signalEmissive = theme === 'dark' ? '#ffffff' : '#666666';
  
  const nodeColor = hasSignal 
    ? signalColor
    : isFocused ? signalColor : isSelected ? '#e0e0e0' : hovered ? '#d0d0d0' : color;
  const emissiveColor = hasSignal ? signalEmissive : (isFocused || isSelected || hovered) ? '#888888' : '#000000';
  const emissiveIntensityValue = hasSignal 
    ? 0.6 + signalIntensity * 0.6 
    : isFocused ? 0.6 : isSelected ? 0.4 : hovered ? 0.2 : 0;
  
  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onPointerOver={() => setHovered(true)}
        onPointerOut={handlePointerLeave}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        transparent
      >
        {geometry}
        <meshStandardMaterial 
          color={nodeColor}
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensityValue}
          metalness={0.3}
          roughness={0.7}
          transparent
          opacity={opacity}
        />
      </mesh>
      
      {/* Signal glow effect - single optimized mesh with theme-adaptive color */}
      {signalIntensity > 0 && (
        <mesh scale={1.4 + signalIntensity * 0.4}>
          <sphereGeometry args={[0.5, 8, 8]} />
          <meshBasicMaterial 
            color={theme === 'dark' ? '#ffffff' : '#1a1a1a'} 
            transparent 
            opacity={0.35 * signalIntensity} 
          />
        </mesh>
      )}
      
      {/* Node label */}
      <Billboard>
        <Text
          position={[0, 0.8, 0]}
          fontSize={0.25}
          color={theme === 'dark' ? '#ffffff' : '#000000'}
          anchorX="center"
          anchorY="bottom"
          maxWidth={2}
          fillOpacity={opacity}
        >
          {node.detailed_label || node.name || node.type}
        </Text>
      </Billboard>
    </group>
  );
});

/**
 * 3D Edge component - memoized for performance
 */
const Edge3D = memo(function Edge3D({ start, end, isHighlighted, isDimmed, isSignal, theme }) {
  const points = useMemo(() => {
    return [
      new THREE.Vector3(start.x, start.y, start.z),
      new THREE.Vector3(end.x, end.y, end.z)
    ];
  }, [start, end]);
  
  // Theme-adaptive colors for edges
  const signalColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const highlightColor = theme === 'dark' ? '#cccccc' : '#444444';
  const defaultColor = theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)';
  
  const color = isSignal ? signalColor : isHighlighted ? highlightColor : defaultColor;
  const opacity = isDimmed ? 0.1 : isSignal ? 1 : isHighlighted ? 0.8 : 0.3;
  const lineWidth = isSignal ? 2 : isHighlighted ? 2 : 1;
  
  return (
    <Line
      points={points}
      color={color}
      lineWidth={lineWidth}
      transparent
      opacity={opacity}
    />
  );
});

/**
 * Signal particle that travels along edges (optimized)
 * Particle color adapts to theme: white in dark mode, black in light mode
 */
function SignalParticle({ start, end, progress, theme }) {
  // Calculate current position (no useMemo to reduce overhead)
  const x = start.x + (end.x - start.x) * progress;
  const y = start.y + (end.y - start.y) * progress;
  const z = start.z + (end.z - start.z) * progress;
  
  // Trail opacity fades based on progress
  const trailOpacity = Math.max(0, 0.8 - progress * 0.5);
  const glowSize = 0.12 + progress * 0.08;
  
  // Theme-adaptive colors
  const coreColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const glowColor = theme === 'dark' ? '#ffffff' : '#333333';
  
  return (
    <group position={[x, y, z]}>
      {/* Core particle - low poly sphere */}
      <mesh>
        <sphereGeometry args={[0.08, 8, 8]} />
        <meshBasicMaterial color={coreColor} />
      </mesh>
      
      {/* Outer glow - single mesh instead of multiple */}
      <mesh scale={glowSize * 8}>
        <sphereGeometry args={[0.1, 8, 8]} />
        <meshBasicMaterial color={glowColor} transparent opacity={trailOpacity * 0.6} />
      </mesh>
    </group>
  );
}

/**
 * Scene component
 */
const Scene = forwardRef(({ nodes, edges, positions, selectedNode, focusedNode, signalParticles, onNodeClick, onNodeLongPress, theme }, ref) => {
  const { camera } = useThree();
  const controlsRef = useRef();
  const targetPosition = useRef(new THREE.Vector3());
  const isAnimating = useRef(false);
  const isResetting = useRef(false); // Track reset animation state
  const resetTarget = useRef({ position: null, lookAt: null });
  const keysPressed = useRef(new Set());
  
  // Calculate which nodes should be dimmed (when focused)
  const visibleNodeIds = useMemo(() => {
    if (!focusedNode) return null;
    
    const visible = new Set([focusedNode.id]);
    edges.forEach(edge => {
      if (edge.source === focusedNode.id) visible.add(edge.target);
      if (edge.target === focusedNode.id) visible.add(edge.source);
    });
    
    return visible;
  }, [focusedNode, edges]);
  
  // Get nodes that have active signals (particles approaching or at the node)
  const signalNodeIds = useMemo(() => {
    const ids = new Set();
    signalParticles.forEach(p => {
      // Signal starts when particle is halfway (0.5) and continues until it's done
      if (p.progress > 0.5) {
        ids.add(p.targetId);
      }
    });
    return ids;
  }, [signalParticles]);
  
  // Reset camera when data changes
  useEffect(() => {
    if (positions.size > 0) {
      // Calculate bounding box
      let minX = Infinity, maxX = -Infinity;
      let minY = Infinity, maxY = -Infinity;
      let minZ = Infinity, maxZ = -Infinity;
      
      positions.forEach(p => {
        minX = Math.min(minX, p.x);
        maxX = Math.max(maxX, p.x);
        minY = Math.min(minY, p.y);
        maxY = Math.max(maxY, p.y);
        minZ = Math.min(minZ, p.z);
        maxZ = Math.max(maxZ, p.z);
      });
      
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const centerZ = (minZ + maxZ) / 2;
      const maxDist = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
      
      camera.position.set(centerX, centerY + maxDist, centerZ + maxDist);
      camera.lookAt(centerX, centerY, centerZ);
    }
  }, [positions, camera]);
  
  // Animate camera to focused node
  useEffect(() => {
    if (focusedNode && positions.has(focusedNode.id)) {
      const pos = positions.get(focusedNode.id);
      targetPosition.current.set(pos.x, pos.y, pos.z);
      isAnimating.current = true;
    }
  }, [focusedNode, positions]);
  
  // Keyboard event handlers
  useEffect(() => {
    const handleKeyDown = (e) => {
      // 如果搜索框或任何输入框聚焦，不处理键盘导航
      const activeElement = document.activeElement;
      const isInputFocused = activeElement && (
        activeElement.tagName === 'INPUT' ||
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.isContentEditable
      );
      
      if (isInputFocused) {
        return;
      }
      
      keysPressed.current.add(e.key.toLowerCase());
    };
    
    const handleKeyUp = (e) => {
      keysPressed.current.delete(e.key.toLowerCase());
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);
  
  // Camera animation and keyboard movement loop
  useFrame((_, delta) => {
    const controls = controlsRef.current;
    
    // Handle reset camera animation (priority over other animations)
    if (isResetting.current && controls && resetTarget.current.position) {
      const targetPos = resetTarget.current.position;
      const targetLookAt = resetTarget.current.lookAt;
      
      // Smooth interpolation
      camera.position.lerp(targetPos, 0.05);
      controls.target.lerp(targetLookAt, 0.05);
      
      // Check if animation is complete
      if (camera.position.distanceTo(targetPos) < 0.1 && controls.target.distanceTo(targetLookAt) < 0.1) {
        isResetting.current = false;
        resetTarget.current = { position: null, lookAt: null };
      }
      return; // Skip other animations during reset
    }
    
    // Handle focused node animation
    if (isAnimating.current && controls) {
      const target = targetPosition.current;
      controls.target.lerp(target, 0.08);
      
      // Also move camera to follow the target (maintain viewing distance)
      const cameraOffset = camera.position.clone().sub(controls.target);
      const desiredPosition = target.clone().add(cameraOffset.normalize().multiplyScalar(
        Math.max(15, camera.position.distanceTo(controls.target))
      ));
      camera.position.lerp(desiredPosition, 0.05);
      
      if (controls.target.distanceTo(target) < 0.01) {
        isAnimating.current = false;
      }
    }
    
    // Handle keyboard movement
    if (controls && keysPressed.current.size > 0) {
      const moveSpeed = 10 * delta; // Movement speed
      const keys = keysPressed.current;
      
      // Get camera direction vectors
      const forward = new THREE.Vector3();
      const right = new THREE.Vector3();
      
      camera.getWorldDirection(forward);
      right.crossVectors(forward, camera.up).normalize();
      
      // Flatten for horizontal movement (no y-axis movement)
      forward.y = 0;
      forward.normalize();
      
      const moveVector = new THREE.Vector3();
      
      // WASD and Arrow keys for horizontal movement
      if (keys.has('w') || keys.has('arrowup')) {
        moveVector.add(forward);
      }
      if (keys.has('s') || keys.has('arrowdown')) {
        moveVector.sub(forward);
      }
      if (keys.has('a') || keys.has('arrowleft')) {
        moveVector.sub(right);
      }
      if (keys.has('d') || keys.has('arrowright')) {
        moveVector.add(right);
      }
      
      // Space for up, Shift for down
      if (keys.has(' ')) {
        moveVector.y += 1;
      }
      if (keys.has('shift')) {
        moveVector.y -= 1;
      }
      
      if (moveVector.length() > 0) {
        moveVector.normalize().multiplyScalar(moveSpeed);
        
        // Move both camera and controls target
        camera.position.add(moveVector);
        controls.target.add(moveVector);
      }
    }
  });
  
  // Reset camera to initial position (integrated with useFrame)
  const resetCamera = useCallback(() => {
    if (!positions || positions.size === 0) return;
    
    // Calculate bounding box
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    
    positions.forEach(p => {
      minX = Math.min(minX, p.x);
      maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y);
      maxY = Math.max(maxY, p.y);
      minZ = Math.min(minZ, p.z);
      maxZ = Math.max(maxZ, p.z);
    });
    
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const centerZ = (minZ + maxZ) / 2;
    const maxDist = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
    
    // Set reset target for useFrame animation
    resetTarget.current = {
      position: new THREE.Vector3(centerX, centerY + maxDist, centerZ + maxDist),
      lookAt: new THREE.Vector3(centerX, centerY, centerZ)
    };
    isResetting.current = true;
    isAnimating.current = false; // Cancel any ongoing focus animation
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positions]);
  
  // Zoom in camera
  const zoomIn = useCallback((factor = 1.2) => {
    if (!controlsRef.current) return;
    
    const controls = controlsRef.current;
    const direction = new THREE.Vector3();
    camera.getWorldDirection(direction);
    
    const distance = camera.position.distanceTo(controls.target);
    const moveDistance = distance * (1 - 1/factor);
    
    camera.position.add(direction.multiplyScalar(moveDistance));
  }, [camera]);
  
  // Zoom out camera
  const zoomOut = useCallback((factor = 1.2) => {
    if (!controlsRef.current) return;
    
    const controls = controlsRef.current;
    const direction = new THREE.Vector3();
    camera.getWorldDirection(direction);
    
    const distance = camera.position.distanceTo(controls.target);
    const moveDistance = distance * (factor - 1);
    
    camera.position.sub(direction.multiplyScalar(moveDistance));
  }, [camera]);
  
  // Pan camera
  const pan = useCallback((dx, dy) => {
    if (!controlsRef.current) return;
    
    const right = new THREE.Vector3();
    const up = new THREE.Vector3(0, 1, 0);
    
    camera.getWorldDirection(right);
    right.cross(up).normalize();
    
    const moveX = right.multiplyScalar(-dx);
    const moveY = up.multiplyScalar(dy);
    
    camera.position.add(moveX).add(moveY);
    controlsRef.current.target.add(moveX).add(moveY);
  }, [camera]);
  
  // Rotate camera
  const rotate = useCallback((dx, dy) => {
    if (!controlsRef.current) return;
    
    const controls = controlsRef.current;
    
    // Rotate around target
    const offset = camera.position.clone().sub(controls.target);
    
    // Horizontal rotation (around Y axis)
    const spherical = new THREE.Spherical().setFromVector3(offset);
    spherical.theta -= dx;
    spherical.phi += dy;
    
    // Clamp vertical rotation
    spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
    
    offset.setFromSpherical(spherical);
    camera.position.copy(controls.target).add(offset);
    camera.lookAt(controls.target);
  }, [camera]);
  
  // Get camera reference for 3D to screen projection
  const getCamera = useCallback(() => camera, [camera]);
  
  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    resetCamera,
    zoomIn,
    zoomOut,
    pan,
    rotate,
    getCamera,
  }), [resetCamera, zoomIn, zoomOut, pan, rotate, getCamera]);
  
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 10, 5]} intensity={0.8} />
      <pointLight position={[-10, -10, -5]} intensity={0.3} />
      
      {/* Nodes */}
      {nodes.map(node => {
        const pos = positions.get(node.id);
        if (!pos) return null;
        
        const isDimmed = visibleNodeIds && !visibleNodeIds.has(node.id);
        const isSignal = signalNodeIds.has(node.id);
        
        return (
          <Node3D
            key={node.id}
            position={[pos.x, pos.y, pos.z]}
            node={node}
            isSelected={selectedNode?.id === node.id}
            isFocused={focusedNode?.id === node.id}
            isDimmed={isDimmed}
            isSignal={isSignal}
            onClick={onNodeClick}
            onLongPress={onNodeLongPress}
            theme={theme}
          />
        );
      })}
      
      {/* Edges */}
      {edges.map(edge => {
        const start = positions.get(edge.source);
        const end = positions.get(edge.target);
        if (!start || !end) return null;
        
        const isConnectedToFocused = focusedNode && 
          (edge.source === focusedNode.id || edge.target === focusedNode.id);
        const isDimmed = visibleNodeIds && !isConnectedToFocused;
        
        return (
          <Edge3D
            key={edge.id}
            start={start}
            end={end}
            isHighlighted={isConnectedToFocused}
            isDimmed={isDimmed}
            isSignal={false}
            theme={theme}
          />
        );
      })}
      
      {/* Signal Particles */}
      {signalParticles.map(particle => (
        <SignalParticle
          key={particle.id}
          start={particle.startPos}
          end={particle.endPos}
          progress={particle.progress}
          theme={theme}
        />
      ))}
      
      {/* Controls */}
      <OrbitControls 
        ref={controlsRef}
        enableDamping 
        dampingFactor={0.05}
        minDistance={2}
        maxDistance={100}
      />
      
      {/* Click on empty space to deselect */}
      <mesh onClick={() => { onNodeClick(null); onNodeLongPress(null); }}>
        <sphereGeometry args={[500, 8, 8]} />
        <meshBasicMaterial transparent opacity={0} side={THREE.BackSide} />
      </mesh>
    </>
  );
});

/**
 * Main 3D Visualizer component
 */
const ASTVisualizer3D = forwardRef(function ASTVisualizer3D({ graph, theme, onGoToLine, gestureEnabled = false }, ref) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [focusedNode, setFocusedNode] = useState(null);
  const [signalParticles, setSignalParticles] = useState([]); // Particles traveling along edges
  const [detailLevel, setDetailLevel] = useState('normal');
  const [layoutType, setLayoutType] = useState(LAYOUT_TYPES.HIERARCHICAL);
  const [isLayoutReady, setIsLayoutReady] = useState(false);
  const particleIdRef = useRef(0);
  const sceneRef = useRef(null); // Ref to access Scene methods
  
  // WebGL support state
  const [webglSupported, setWebglSupported] = useState(true);
  const [webglError, setWebglError] = useState(null);
  
  // Check WebGL support on mount
  useEffect(() => {
    const { supported, reason } = checkWebGLSupport();
    setWebglSupported(supported);
    if (!supported) {
      setWebglError(reason);
      logger.warn('WebGL not available for 3D visualization', { reason });
    }
  }, []);
  
  // Gesture control state
  const gestureStateRef = useRef({
    isPanning: false,
    lastPanPosition: null,
    isRotating: false,
    lastRotationAngle: null,
  });
  
  // Pointing cursor state and refs
  const containerRef = useRef(null);
  const cursorDotRef = useRef(null);
  const cursorRingRef = useRef(null);
  const cursorProgressRef = useRef(null);
  const cursorSnapRef = useRef(null);
  const cursorAnimFrameRef = useRef(null);
  const nodePositionsCacheRef = useRef([]);
  
  const cursorStateRef = useRef({
    visible: false,
    x: 0,
    y: 0,
    targetX: 0,
    targetY: 0,
    snapped: false,
    snapX: 0,
    snapY: 0,
    snapTargetX: 0,
    snapTargetY: 0,
    hoveredNodeId: null,
    progress: 0,
    hoverStartTime: 0,
  });
  
  // Pointing constants
  const SNAP_DISTANCE = 50;
  const HOVER_SELECT_TIME = 800;
  
  // Track timers and animation frames for cleanup
  const timersRef = useRef(new Set());
  const animationFramesRef = useRef(new Set());
  
  // Search related state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [selectedSearchIndex, setSelectedSearchIndex] = useState(-1);
  const [isSearchResultHovered, setIsSearchResultHovered] = useState(false); // 跟踪搜索结果悬停
  const [isPanelExpanded, setIsPanelExpanded] = useState(false); // 详细面板放大状态
  const searchInputRef = useRef(null);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
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
    };
  }, []);
  
  // Gesture control handlers - exposed via ref
  const handleGesture = useCallback((gestureData) => {
    if (!sceneRef.current || !gestureEnabled) return;
    
    const { action, position } = gestureData;
    
    switch (action) {
      case GestureAction.ZOOM_IN:
        // Zoom in camera
        if (sceneRef.current.zoomIn) {
          sceneRef.current.zoomIn();
        }
        break;
        
      case GestureAction.ZOOM_OUT:
        // Zoom out camera
        if (sceneRef.current.zoomOut) {
          sceneRef.current.zoomOut();
        }
        break;
        
      case GestureAction.PAN:
        // Pan based on hand position change
        if (gestureStateRef.current.isPanning && gestureStateRef.current.lastPanPosition && position) {
          const dx = (position.x - gestureStateRef.current.lastPanPosition.x) * 10;
          const dy = (position.y - gestureStateRef.current.lastPanPosition.y) * 10;
          if (sceneRef.current.pan) {
            sceneRef.current.pan(dx, dy);
          }
        }
        gestureStateRef.current.isPanning = true;
        gestureStateRef.current.lastPanPosition = position;
        break;
        
      case GestureAction.RESET:
        // Reset camera
        if (sceneRef.current.resetCamera) {
          sceneRef.current.resetCamera();
        }
        gestureStateRef.current = {
          isPanning: false,
          lastPanPosition: null,
          isRotating: false,
          lastRotationAngle: null,
        };
        break;
        
      case GestureAction.ROTATE:
        // Enable rotation mode - position controls rotation
        if (position) {
          const rotationSpeed = 0.02;
          if (gestureStateRef.current.isRotating && gestureStateRef.current.lastPanPosition) {
            const dx = (position.x - gestureStateRef.current.lastPanPosition.x) * rotationSpeed;
            const dy = (position.y - gestureStateRef.current.lastPanPosition.y) * rotationSpeed;
            if (sceneRef.current.rotate) {
              sceneRef.current.rotate(dx, dy);
            }
          }
          gestureStateRef.current.isRotating = true;
          gestureStateRef.current.lastPanPosition = position;
        }
        break;
        
      case GestureAction.NONE:
      default:
        // Reset gesture state
        gestureStateRef.current.isPanning = false;
        gestureStateRef.current.lastPanPosition = null;
        gestureStateRef.current.isRotating = false;
        break;
    }
  }, [gestureEnabled]);
  
  const handleTwoHands = useCallback((twoHandsData) => {
    if (!sceneRef.current || !gestureEnabled) return;
    
    const { pinchScale, panDelta } = twoHandsData;
    
    // Pinch to zoom
    if (Math.abs(pinchScale) > 0.005) {
      if (pinchScale > 0) {
        if (sceneRef.current.zoomIn) {
          sceneRef.current.zoomIn(Math.abs(pinchScale) * 5);
        }
      } else {
        if (sceneRef.current.zoomOut) {
          sceneRef.current.zoomOut(Math.abs(pinchScale) * 5);
        }
      }
    }
    
    // Pan with two hands
    if (panDelta && (Math.abs(panDelta.x) > 0.5 || Math.abs(panDelta.y) > 0.5)) {
      if (sceneRef.current.pan) {
        sceneRef.current.pan(panDelta.x * 0.01, panDelta.y * 0.01);
      }
    }
  }, [gestureEnabled]);
  
  // Search nodes
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    setSelectedSearchIndex(-1);
    
    if (!query.trim() || !graph) {
      setSearchResults([]);
      return;
    }
    
    const lowerQuery = query.toLowerCase().trim();
    const results = graph.nodes.filter(node => {
      // 确保 node 是有效对象
      if (!node || !node.id) return false;
      
      const name = (node.name || '').toLowerCase();
      const type = (node.type || '').toLowerCase();
      const label = (node.detailed_label || '').toLowerCase();
      const description = (node.description || '').toLowerCase();
      
      return name.includes(lowerQuery) ||
             type.includes(lowerQuery) ||
             label.includes(lowerQuery) ||
             description.includes(lowerQuery);
    }).slice(0, 20);
    
    setSearchResults(results);
  }, [graph]);
  
  // Clear search
  const clearSearch = useCallback(() => {
    setSearchQuery('');
    setSearchResults([]);
    setSelectedSearchIndex(-1);
    setIsSearchOpen(false);
    setFocusedNode(null);
    setIsSearchResultHovered(false);
  }, []);
  
  // Focus on search result
  const focusSearchResult = useCallback((node, index) => {
    // Strict null check
    if (!node || typeof node !== 'object' || !node.id) return;
    setSelectedSearchIndex(index);
    setSelectedNode(node);
    setFocusedNode(node);
  }, []);
  
  // Find node by ID
  const findNodeById = useCallback((nodeId) => {
    if (!graph || !graph.nodes) return null;
    return graph.nodes.find(n => n && n.id === nodeId) || null;
  }, [graph]);
  
  // Find node by name (for function calls)
  const findNodeByName = useCallback((name) => {
    if (!graph || !graph.nodes || !name) return null;
    // Prefer function/class nodes with matching name
    return graph.nodes.find(n => 
      n && n.name === name && 
      ['function', 'FunctionDef', 'AsyncFunctionDef', 'class', 'ClassDef'].includes(n.type)
    ) || graph.nodes.find(n => n && n.name === name) || null;
  }, [graph]);
  
  // Navigate to a node (set as selected and focused)
  const navigateToNode = useCallback((node) => {
    if (!node || !node.id) return;
    setSelectedNode(node);
    setFocusedNode(node);
  }, []);
  
  // Jump to editor line
  const handleGoToLine = useCallback((node) => {
    if (node && onGoToLine && node.lineno) {
      onGoToLine(node.lineno, node.end_lineno);
    }
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
  
  // Filter nodes based on detail level
  const filteredElements = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    
    const totalNodes = graph.nodes.length;
    const nodeIds = new Set();
    let filteredNodes;
    
    const priorityTypes = new Set([
      'function', 'class', 'FunctionDef', 'AsyncFunctionDef', 'ClassDef',
      'if', 'for', 'while', 'try', 'with', 'If', 'For', 'While', 'Try', 'With',
      'Module'
    ]);
    
    const secondaryTypes = new Set([
      'call', 'return', 'yield', 'Call', 'Return', 'Yield',
      'import', 'Import', 'ImportFrom', 'Assign', 'AugAssign'
    ]);
    
    if (detailLevel === 'detail' || totalNodes <= MAX_NODES_3D) {
      filteredNodes = graph.nodes;
      filteredNodes.forEach(n => nodeIds.add(n.id));
    } else if (detailLevel === 'normal') {
      filteredNodes = graph.nodes.filter(node => {
        const keep = priorityTypes.has(node.type) || secondaryTypes.has(node.type);
        if (keep) nodeIds.add(node.id);
        return keep;
      });
    } else if (detailLevel === 'minimal') {
      // Minimal: only functions and classes
      filteredNodes = graph.nodes.filter(node => {
        const keep = ['function', 'FunctionDef', 'AsyncFunctionDef', 'class', 'ClassDef', 'Module'].includes(node.type);
        if (keep) nodeIds.add(node.id);
        return keep;
      });
    } else {
      // Overview: priority types only
      filteredNodes = graph.nodes.filter(node => {
        const keep = priorityTypes.has(node.type);
        if (keep) nodeIds.add(node.id);
        return keep;
      });
    }
    
    const filteredEdges = graph.edges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );
    
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graph, detailLevel]);
  
  // Compute 3D layout
  const positions = useMemo(() => {
    setIsLayoutReady(false);
    const result = computeLayout(filteredElements.nodes, filteredElements.edges, layoutType);
    setIsLayoutReady(true);
    return result;
  }, [filteredElements, layoutType]);
  
  // Cursor animation loop for pointing gesture
  const runCursorAnimation = useCallback(() => {
    const state = cursorStateRef.current;
    if (!state.visible) {
      cursorAnimFrameRef.current = null;
      return;
    }
    
    // Smooth interpolation to target
    state.x += (state.targetX - state.x) * 0.25;
    state.y += (state.targetY - state.y) * 0.25;
    
    // Handle snap animation
    if (state.snapped) {
      state.snapX += (state.snapTargetX - state.snapX) * 0.35;
      state.snapY += (state.snapTargetY - state.snapY) * 0.35;
    }
    
    // Update DOM elements
    const dot = cursorDotRef.current;
    const ring = cursorRingRef.current;
    const progress = cursorProgressRef.current;
    const snap = cursorSnapRef.current;
    
    // Center offsets: element size / 2
    // dot: 10px -> -5, ring: 44px -> -22, progress: 52px -> -26
    if (dot) {
      dot.style.transform = `translate(${state.x - 5}px, ${state.y - 5}px)`;
    }
    if (ring) {
      ring.style.transform = `translate(${state.x - 22}px, ${state.y - 22}px)`;
    }
    
    // Handle hover progress for auto-select
    if (state.hoveredNodeId && state.hoverStartTime > 0) {
      const elapsed = Date.now() - state.hoverStartTime;
      state.progress = Math.min(elapsed / HOVER_SELECT_TIME, 1);
      
      if (progress) {
        progress.style.transform = `translate(${state.x - 26}px, ${state.y - 26}px)`;
        progress.style.opacity = '0.8';
        const circumference = 2 * Math.PI * 24;
        const progressCircle = progress.querySelector('circle');
        if (progressCircle) {
          progressCircle.style.strokeDasharray = `${state.progress * circumference} ${circumference}`;
        }
      }
      
      // Auto-select when progress complete
      if (state.progress >= 1) {
        const node = filteredElements.nodes.find(n => n.id === state.hoveredNodeId);
        if (node) {
          setSelectedNode(node);
          setFocusedNode(node);
          if (onGoToLine && node.lineno) {
            onGoToLine(node.lineno, node.end_lineno);
          }
        }
        state.hoveredNodeId = null;
        state.progress = 0;
        state.hoverStartTime = 0;
      }
    } else if (progress) {
      progress.style.opacity = '0';
    }
    
    // Update snap indicator
    if (snap) {
      if (state.snapped) {
        snap.style.transform = `translate(${state.snapX - 30}px, ${state.snapY - 30}px)`;
        snap.style.opacity = '0.6';
      } else {
        snap.style.opacity = '0';
      }
    }
    
    // Continue animation
    cursorAnimFrameRef.current = requestAnimationFrame(runCursorAnimation);
  }, [filteredElements.nodes, onGoToLine]);
  
  // Pointing direction handler for gesture-based node selection
  const handlePointingDirection = useCallback((pointingData) => {
    if (!gestureEnabled || !containerRef.current || positions.size === 0) return;
    
    const container = containerRef.current;
    const state = cursorStateRef.current;
    
    // Get container dimensions for all calculations
    const rect = container.getBoundingClientRect();
    
    // Calculate target position (mirror X for natural feel)
    const targetX = rect.width * (1 - pointingData.origin.x);
    const targetY = rect.height * pointingData.origin.y;
    
    // Initialize or update target
    if (!state.visible) {
      state.visible = true;
      state.x = targetX;
      state.y = targetY;
      if (cursorDotRef.current) cursorDotRef.current.style.opacity = '1';
      if (cursorRingRef.current) cursorRingRef.current.style.opacity = '0.8';
    }
    state.targetX = targetX;
    state.targetY = targetY;
    
    // Get camera info from scene ref for projecting 3D positions
    const camera = sceneRef.current?.getCamera?.();
    if (!camera) return;
    
    // Build node positions cache for hit testing
    nodePositionsCacheRef.current = [];
    filteredElements.nodes.forEach(node => {
      const pos = positions.get(node.id);
      if (pos) {
        // Project 3D position to NDC coordinates
        const vector = new THREE.Vector3(pos.x, pos.y, pos.z);
        vector.project(camera);
        
        // NDC to screen coordinates using container dimensions
        // This matches the cursor overlay coordinate system
        const screenX = (vector.x * 0.5 + 0.5) * rect.width;
        const screenY = (-vector.y * 0.5 + 0.5) * rect.height;
        
        // Only include nodes in front of camera (z < 1 means in front)
        if (vector.z < 1) {
          nodePositionsCacheRef.current.push({
            node,
            screenX,
            screenY,
            z: vector.z,
          });
        }
      }
    });
    
    // Find nearest node to cursor
    let nearestNode = null;
    let nearestDist = Infinity;
    let nearestScreenPos = null;
    
    const snapRadius = SNAP_DISTANCE;
    const cache = nodePositionsCacheRef.current;
    
    for (let i = 0; i < cache.length; i++) {
      const item = cache[i];
      const dx = targetX - item.screenX;
      const dy = targetY - item.screenY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      
      if (dist < snapRadius && dist < nearestDist) {
        nearestDist = dist;
        nearestNode = item.node;
        nearestScreenPos = { x: item.screenX, y: item.screenY };
      }
    }
    
    // Update snap state
    const isSnapped = nearestNode && nearestDist < snapRadius;
    const wasSnapped = state.snapped;
    state.snapped = isSnapped;
    
    if (isSnapped && nearestScreenPos) {
      state.snapTargetX = nearestScreenPos.x;
      state.snapTargetY = nearestScreenPos.y;
      if (!wasSnapped) {
        state.snapX = nearestScreenPos.x;
        state.snapY = nearestScreenPos.y;
      }
    }
    
    // Update hover state
    if (isSnapped && nearestNode) {
      const nodeId = nearestNode.id;
      if (state.hoveredNodeId !== nodeId) {
        state.hoveredNodeId = nodeId;
        state.progress = 0;
        state.hoverStartTime = Date.now();
      }
    } else {
      state.hoveredNodeId = null;
      state.progress = 0;
      state.hoverStartTime = 0;
    }
    
    // Start animation loop
    if (!cursorAnimFrameRef.current) {
      cursorAnimFrameRef.current = requestAnimationFrame(runCursorAnimation);
    }
  }, [gestureEnabled, positions, filteredElements.nodes, runCursorAnimation]);
  
  // Clear pointing cursor
  const clearPointingCursor = useCallback(() => {
    const state = cursorStateRef.current;
    state.visible = false;
    state.hoveredNodeId = null;
    state.progress = 0;
    state.hoverStartTime = 0;
    state.snapped = false;
    
    if (cursorAnimFrameRef.current) {
      cancelAnimationFrame(cursorAnimFrameRef.current);
      cursorAnimFrameRef.current = null;
    }
    
    // Hide DOM elements
    if (cursorDotRef.current) cursorDotRef.current.style.opacity = '0';
    if (cursorRingRef.current) cursorRingRef.current.style.opacity = '0';
    if (cursorProgressRef.current) cursorProgressRef.current.style.opacity = '0';
    if (cursorSnapRef.current) cursorSnapRef.current.style.opacity = '0';
  }, []);
  
  // Cleanup cursor animation on unmount
  useEffect(() => {
    return () => {
      if (cursorAnimFrameRef.current) {
        cancelAnimationFrame(cursorAnimFrameRef.current);
      }
    };
  }, []);
  
  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    handleGesture,
    handleTwoHands,
    handlePointingDirection,
    clearPointingCursor,
    zoomIn: () => sceneRef.current?.zoomIn?.(),
    zoomOut: () => sceneRef.current?.zoomOut?.(),
    resetCamera: () => sceneRef.current?.resetCamera?.(),
  }), [handleGesture, handleTwoHands, handlePointingDirection, clearPointingCursor]);
  
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
    if (!node) {
      setFocusedNode(null);
      setSignalParticles([]);
    }
  }, []);
  
  const handleLongPress = useCallback((node) => {
    setFocusedNode(node);
    setSelectedNode(node);
  }, []);
  
  // Signal propagation with particles traveling along edges
  const propagateSignalWithParticles = useCallback((sourceId, edges, positions) => {
    const visitedNodes = new Set([sourceId]);
    const visitedEdges = new Set();
    const propagationQueue = [];
    let currentNodes = [{ id: sourceId, delay: 0 }];
    
    // Build propagation queue using BFS
    for (let depth = 0; depth < 5 && currentNodes.length > 0; depth++) {
      const nextNodes = [];
      
      currentNodes.forEach(({ id, delay }) => {
        edges.forEach(edge => {
          // Skip if this edge was already processed
          if (visitedEdges.has(edge.id)) return;
          
          let targetId = null;
          let startPos = null;
          let endPos = null;
          
          if (edge.source === id) {
            targetId = edge.target;
            startPos = positions.get(edge.source);
            endPos = positions.get(edge.target);
          } else if (edge.target === id) {
            targetId = edge.source;
            startPos = positions.get(edge.target);
            endPos = positions.get(edge.source);
          }
          
          // Only process if this edge is connected to current node
          if (targetId && startPos && endPos) {
            visitedEdges.add(edge.id);
            
            // Calculate edge length (3D distance)
            const dx = endPos.x - startPos.x;
            const dy = endPos.y - startPos.y;
            const dz = endPos.z - startPos.z;
            const edgeLength = Math.sqrt(dx * dx + dy * dy + dz * dz);
            
            // Copy position values to avoid reference issues during layout updates
            propagationQueue.push({
              sourceId: id,
              targetId,
              startPos: { x: startPos.x, y: startPos.y, z: startPos.z },
              endPos: { x: endPos.x, y: endPos.y, z: endPos.z },
              delay,
              edgeLength,
              targetNode: filteredElements.nodes.find(n => n.id === targetId)
            });
            
            // Only add target node to next wave if not visited
            if (!visitedNodes.has(targetId)) {
              visitedNodes.add(targetId);
              // Delay based on edge length (constant speed)
              const travelTime = edgeLength * 30; // 30ms per unit distance
              nextNodes.push({ id: targetId, delay: delay + travelTime });
            }
          }
        });
      });
      
      currentNodes = nextNodes;
    }
    
    // Restore visibility
    setFocusedNode(null);
    
    // Particle speed: units per millisecond
    const particleSpeed = 0.03; // 0.03 units per ms = 30 units per second
    
    // Create particles for each edge
    propagationQueue.forEach(({ sourceId, targetId, startPos, endPos, delay, edgeLength, targetNode }) => {
      const timerId = setTimeout(() => {
        const particleId = particleIdRef.current++;
        const startTime = Date.now();
        // Duration based on edge length and constant speed
        const duration = edgeLength / particleSpeed;
        
        // Add new particle
        const newParticle = {
          id: particleId,
          sourceId,
          targetId,
          startPos,
          endPos,
          startTime,
          duration,
          progress: 0
        };
        
        setSignalParticles(prev => [...prev, newParticle]);
        
        // Animate particle
        const animateParticle = () => {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          
          if (progress < 1) {
            setSignalParticles(prev => 
              prev.map(p => p.id === particleId ? { ...p, progress } : p)
            );
            const frameId = requestAnimationFrame(animateParticle);
            animationFramesRef.current.add(frameId);
          } else {
            // Remove particle when done
            setSignalParticles(prev => prev.filter(p => p.id !== particleId));
          }
        };
        
        const frameId = requestAnimationFrame(animateParticle);
        animationFramesRef.current.add(frameId);
      }, delay);
      timersRef.current.add(timerId);
    });
  }, [filteredElements.nodes]);
  
  // Signal propagation effect when focusedNode changes to null (released)
  useEffect(() => {
    if (focusedNode === null && selectedNode && positions.size > 0) {
      // Trigger signal propagation with particles
      propagateSignalWithParticles(selectedNode.id, filteredElements.edges, positions);
    }
  }, [focusedNode, selectedNode, filteredElements.edges, positions, propagateSignalWithParticles]);
  
  if (!graph) {
    return (
      <div className="ast-3d-placeholder">
        <p>No AST data to visualize</p>
      </div>
    );
  }
  
  return (
    <div className="ast-visualizer-3d">
      <div className="visualizer-toolbar">
        <div className="toolbar-left">
          <span className="toolbar-title">3D AST View</span>
          <span className="node-count">
            {filteredElements.nodes.length} nodes
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
            value={detailLevel}
            onChange={(e) => setDetailLevel(e.target.value)}
            title="Detail level"
          >
            <option value="minimal">Minimal</option>
            <option value="overview">Overview</option>
            <option value="normal">Normal</option>
            <option value="detail">Detail</option>
          </select>
          
          <select 
            className="simplify-select layout-select"
            value={layoutType}
            onChange={(e) => setLayoutType(e.target.value)}
            title="Layout type"
          >
            <option value={LAYOUT_TYPES.HIERARCHICAL}>Tree</option>
            <option value={LAYOUT_TYPES.SCOPE_GROUPED}>Grouped</option>
            <option value={LAYOUT_TYPES.FORCE_DIRECTED}>Force</option>
          </select>
          
          <div className="toolbar-divider"></div>
          
          <button 
            className="btn btn-ghost" 
            onClick={() => sceneRef.current?.resetCamera()}
            title="Reset View"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
          </button>
        </div>
      </div>
      
      <div className="visualizer-3d-content" ref={containerRef}>
        {/* Search Panel */}
        {isSearchOpen && (
          <div className="search-panel">
            <div className="search-input-container">
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
            
            {searchResults.length > 0 && (
              <div className="search-results">
                {searchResults.filter(node => node && node.id).map((node, index) => (
                  <div
                    key={node.id}
                    className={`search-result-item ${index === selectedSearchIndex ? 'selected' : ''}`}
                    onClick={() => {
                      try {
                        if (node && node.id) handleGoToLine(node);
                      } catch (e) {
                        logger.warn('Search result click error', { error: e.message });
                      }
                    }}
                    onMouseEnter={() => {
                      try {
                        if (node && node.id) {
                          focusSearchResult(node, index);
                          setIsSearchResultHovered(true);
                        }
                      } catch (e) {
                        logger.warn('Search result hover error', { error: e.message });
                      }
                    }}
                    onMouseLeave={() => {
                      setIsSearchResultHovered(false);
                    }}
                  >
                    <span className="result-icon">{node.icon || '•'}</span>
                    <div className="result-content">
                      <span className="result-name">{node.name || node.type}</span>
                      <span className="result-type">{node.description || node.type}</span>
                    </div>
                    {node.lineno && <span className="result-line">Line {node.lineno}</span>}
                  </div>
                ))}
              </div>
            )}
            
            {searchQuery && searchResults.length === 0 && (
              <div className="search-no-results">
                No matching nodes found
              </div>
            )}
          </div>
        )}
        
        {!webglSupported ? (
          <div className="webgl-error">
            <div className="webgl-error-content">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <h3>3D Visualization Unavailable</h3>
              <p>{webglError || 'WebGL is not supported by your browser or GPU.'}</p>
              <p className="webgl-hint">
                Try using the 2D view instead, or check if hardware acceleration is enabled in your browser settings.
              </p>
              <div className="webgl-troubleshoot">
                <details>
                  <summary>Troubleshooting Tips</summary>
                  <ul>
                    <li>Update your GPU drivers</li>
                    <li>Enable hardware acceleration in browser settings</li>
                    <li>Try a different browser (Chrome, Firefox, Edge)</li>
                    <li>Close other tabs that may use WebGL</li>
                  </ul>
                </details>
              </div>
            </div>
          </div>
        ) : !isLayoutReady ? (
          <div className="rendering-overlay">
            <div className="rendering-spinner"></div>
            <span>Computing 3D layout...</span>
          </div>
        ) : (
          <Canvas
            camera={{ position: [20, 20, 20], fov: 50 }}
            gl={{ 
              antialias: true, 
              alpha: true,
              powerPreference: 'high-performance',
              failIfMajorPerformanceCaveat: false,
            }}
            style={{ background: theme === 'dark' ? '#0a0a0a' : '#ffffff' }}
            onCreated={({ gl }) => {
              // Handle WebGL context loss
              gl.domElement.addEventListener('webglcontextlost', (e) => {
                e.preventDefault();
                logger.error('WebGL context lost', { event: e });
                setWebglSupported(false);
                setWebglError('WebGL context was lost. Please refresh the page.');
              });
            }}
            onError={(error) => {
              logger.error('Canvas error', { error });
              setWebglSupported(false);
              setWebglError(error.message || 'Failed to initialize WebGL');
            }}
          >
            <Suspense fallback={null}>
              <Scene
                ref={sceneRef}
                nodes={filteredElements.nodes}
                edges={filteredElements.edges}
                positions={positions}
                selectedNode={selectedNode}
                focusedNode={focusedNode}
                signalParticles={signalParticles}
                onNodeClick={handleNodeClick}
                onNodeLongPress={handleLongPress}
                theme={theme}
              />
            </Suspense>
          </Canvas>
        )}
        
        {/* Node detail panel */}
        {(selectedNode || focusedNode) && (
          <div className={`node-detail-panel ${focusedNode ? 'focused-panel' : ''} ${isSearchResultHovered ? 'dimmed' : ''} ${isPanelExpanded ? 'expanded' : ''}`}>
            <div className="panel-header">
              <div className="panel-header-left">
                <div className="panel-header-main">
                  <span className="node-icon">{(focusedNode || selectedNode)?.icon || '•'}</span>
                  <h4>{(focusedNode || selectedNode)?.description || (focusedNode || selectedNode)?.type}</h4>
                </div>
                {(focusedNode || selectedNode)?.name && <span className="node-name">{(focusedNode || selectedNode)?.name}</span>}
              </div>
              <div className="panel-header-actions">
                <button 
                  className="panel-action-btn" 
                  onClick={() => setIsPanelExpanded(!isPanelExpanded)}
                  title={isPanelExpanded ? 'Collapse panel' : 'Expand panel'}
                >
                  {isPanelExpanded ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="15 18 9 12 15 6" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  )}
                </button>
                <button 
                  className="panel-action-btn panel-close-btn" 
                  onClick={() => { setSelectedNode(null); setFocusedNode(null); setIsPanelExpanded(false); }}
                  title="Close panel"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="panel-body">
              {/* Code Structure */}
              {(focusedNode || selectedNode)?.detailed_label && (
                <div className="detail-item code-label">
                  <span className="detail-label">Code Structure</span>
                  <code className="detail-code">{(focusedNode || selectedNode)?.detailed_label}</code>
                </div>
              )}
              
              {/* Location with line count */}
              {(focusedNode || selectedNode)?.lineno && (
                <div className="detail-item">
                  <span className="detail-label">Location</span>
                  <span className="detail-value">
                    Line {(focusedNode || selectedNode)?.lineno}
                    {(focusedNode || selectedNode)?.end_lineno && (focusedNode || selectedNode)?.end_lineno !== (focusedNode || selectedNode)?.lineno && 
                      ` - ${(focusedNode || selectedNode)?.end_lineno}`}
                    {(focusedNode || selectedNode)?.line_count > 0 && ` (${(focusedNode || selectedNode)?.line_count} lines)`}
                  </span>
                </div>
              )}
              
              {/* Structure Info */}
              {((focusedNode || selectedNode)?.child_count > 0 || (focusedNode || selectedNode)?.depth > 0 || (focusedNode || selectedNode)?.scope_name) && (
                <div className="detail-section">
                  <span className="detail-section-title">Structure</span>
                  <div className="detail-tags">
                    {(focusedNode || selectedNode)?.child_count > 0 && (
                      <span 
                        className="detail-tag clickable" 
                        title="Click to view children"
                        onClick={() => {
                          const children = (focusedNode || selectedNode)?.children;
                          if (children && children.length > 0) {
                            const firstChild = findNodeById(children[0]);
                            if (firstChild) navigateToNode(firstChild);
                          }
                        }}
                      >
                        {(focusedNode || selectedNode)?.child_count} children
                      </span>
                    )}
                    {(focusedNode || selectedNode)?.total_descendants > 0 && (
                      <span className="detail-tag" title="Total descendants">{(focusedNode || selectedNode)?.total_descendants} descendants</span>
                    )}
                    {(focusedNode || selectedNode)?.depth > 0 && (
                      <span className="detail-tag" title="Depth in tree">depth: {(focusedNode || selectedNode)?.depth}</span>
                    )}
                    {(focusedNode || selectedNode)?.scope_name && (
                      <span 
                        className="detail-tag scope clickable" 
                        title="Click to view parent scope"
                        onClick={() => {
                          const scopeNode = findNodeByName((focusedNode || selectedNode)?.scope_name);
                          if (scopeNode) navigateToNode(scopeNode);
                        }}
                      >
                        in {(focusedNode || selectedNode)?.scope_name}
                      </span>
                    )}
                  </div>
                </div>
              )}
              
              {/* Function-specific info */}
              {['function', 'FunctionDef', 'AsyncFunctionDef'].includes((focusedNode || selectedNode)?.type) && (
                <div className="detail-section">
                  <span className="detail-section-title">Function Details</span>
                  <div className="detail-function-info">
                    {/* Return type */}
                    {(focusedNode || selectedNode)?.return_type && (
                      <div className="detail-row">
                        <span className="detail-key">Return Type:</span>
                        <code className="detail-value-code">{(focusedNode || selectedNode)?.return_type}</code>
                      </div>
                    )}
                    
                    {/* Parameters with types and defaults */}
                    {((focusedNode || selectedNode)?.attributes?.args?.length > 0) && (
                      <div className="detail-row">
                        <span className="detail-key">Parameters:</span>
                        <div className="param-list">
                          {(focusedNode || selectedNode)?.attributes?.args?.map((arg, i) => {
                            const paramType = (focusedNode || selectedNode)?.parameter_types?.[arg];
                            const defaultVal = (focusedNode || selectedNode)?.default_values?.[arg];
                            return (
                              <span key={i} className="param-item">
                                {arg}
                                {paramType && <code className="param-type">: {paramType}</code>}
                                {defaultVal && <span className="param-default"> = {defaultVal}</span>}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                    
                    {/* Function metrics */}
                    <div className="detail-tags">
                      {(focusedNode || selectedNode)?.local_var_count > 0 && (
                        <span className="detail-tag">{(focusedNode || selectedNode)?.local_var_count} local vars</span>
                      )}
                      {(focusedNode || selectedNode)?.is_called_count > 0 && (
                        <span className="detail-tag" title="Called this many times">called {(focusedNode || selectedNode)?.is_called_count}x</span>
                      )}
                      {(focusedNode || selectedNode)?.is_async && (
                        <span className="detail-tag async">async</span>
                      )}
                      {(focusedNode || selectedNode)?.is_generator && (
                        <span className="detail-tag generator">generator</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Class-specific info */}
              {['class', 'ClassDef'].includes((focusedNode || selectedNode)?.type) && (
                <div className="detail-section">
                  <span className="detail-section-title">Class Details</span>
                  <div className="detail-tags">
                    {(focusedNode || selectedNode)?.method_count > 0 && (
                      <span className="detail-tag">{(focusedNode || selectedNode)?.method_count} methods</span>
                    )}
                    {(focusedNode || selectedNode)?.attribute_count > 0 && (
                      <span className="detail-tag">{(focusedNode || selectedNode)?.attribute_count} attributes</span>
                    )}
                    {(focusedNode || selectedNode)?.attributes?.bases?.length > 0 && (
                      <span className="detail-tag" title="Inherits from">
                        extends {(focusedNode || selectedNode)?.attributes?.bases?.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              )}
              
              {/* Code Patterns */}
              {((focusedNode || selectedNode)?.has_try_except || (focusedNode || selectedNode)?.has_loop || (focusedNode || selectedNode)?.has_recursion) && (
                <div className="detail-section">
                  <span className="detail-section-title">Code Patterns</span>
                  <div className="detail-tags">
                    {(focusedNode || selectedNode)?.has_try_except && (
                      <span className="detail-tag pattern">try/except</span>
                    )}
                    {(focusedNode || selectedNode)?.has_loop && (
                      <span className="detail-tag pattern">loop</span>
                    )}
                    {(focusedNode || selectedNode)?.has_recursion && (
                      <span className="detail-tag pattern warning">recursion</span>
                    )}
                  </div>
                </div>
              )}
              
              {/* Functions Called */}
              {(focusedNode || selectedNode)?.functions_called?.length > 0 && (
                <div className="detail-section">
                  <span className="detail-section-title">Calls</span>
                  <div className="detail-tags">
                    {(focusedNode || selectedNode)?.functions_called?.slice(0, 8).map((fn, i) => {
                      const targetNode = findNodeByName(fn);
                      return (
                        <span 
                          key={i} 
                          className={`detail-tag callable ${targetNode ? 'clickable' : ''}`}
                          title={targetNode ? `Click to view ${fn}` : fn}
                          onClick={() => {
                            if (targetNode) {
                              navigateToNode(targetNode);
                            }
                          }}
                        >
                          {fn}()
                        </span>
                      );
                    })}
                    {(focusedNode || selectedNode)?.functions_called?.length > 8 && (
                      <span className="detail-tag">+{(focusedNode || selectedNode)?.functions_called?.length - 8} more</span>
                    )}
                  </div>
                </div>
              )}
              
              {/* Explanation */}
              {(focusedNode || selectedNode)?.explanation && (
                <div className="detail-item explanation">
                  <span className="detail-label">Description</span>
                  <p className="explanation-text">{(focusedNode || selectedNode)?.explanation}</p>
                </div>
              )}
              
              {/* Docstring */}
              {(focusedNode || selectedNode)?.docstring && (
                <div className="detail-item">
                  <span className="detail-label">Docstring</span>
                  <p className="docstring">{(focusedNode || selectedNode)?.docstring}</p>
                </div>
              )}
              
              {/* Source Code */}
              {(focusedNode || selectedNode)?.source_code && (
                <div className="detail-item">
                  <span className="detail-label">Source Code</span>
                  <pre className="source-code">{(focusedNode || selectedNode)?.source_code}</pre>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Pointing cursor overlay for gesture control */}
        <div className="pointing-cursor-overlay">
          {/* Cursor dot - shows finger position */}
          <div ref={cursorDotRef} className="cursor-dot" style={{ opacity: 0 }} />
          
          {/* Cursor ring - outer ring */}
          <div ref={cursorRingRef} className="cursor-ring" style={{ opacity: 0 }} />
          
          {/* Progress ring - shows selection progress */}
          <svg ref={cursorProgressRef} className="cursor-progress" width="52" height="52" style={{ opacity: 0 }}>
            <circle
              cx="26"
              cy="26"
              r="24"
              fill="none"
              stroke={theme === 'dark' ? '#ffffff' : '#000000'}
              strokeWidth="2"
              strokeDasharray="0 150.8"
              transform="rotate(-90 26 26)"
            />
          </svg>
          
          {/* Snap indicator - shows when cursor snaps to node */}
          <div ref={cursorSnapRef} className="cursor-snap-3d" style={{ opacity: 0 }}>
            <svg width="60" height="60" viewBox="0 0 60 60">
              <circle
                cx="30"
                cy="30"
                r="28"
                fill="none"
                stroke={theme === 'dark' ? '#ffffff' : '#000000'}
                strokeWidth="1"
                strokeDasharray="6 4"
              />
            </svg>
          </div>
        </div>
      </div>
      
      <div className="visualizer-legend-3d">
        <div className="legend-item">
          <span className="legend-shape box"></span>
          <span>Structure Node</span>
        </div>
        <div className="legend-item">
          <span className="legend-shape diamond"></span>
          <span>Control Flow</span>
        </div>
        <div className="legend-item">
          <span className="legend-shape circle"></span>
          <span>Expression</span>
        </div>
        <div className="legend-hint">Drag to rotate | Scroll to zoom | Click to select | Long press to focus | WASD to move | Space to go up | Shift to go down</div>
      </div>
    </div>
  );
});

export default ASTVisualizer3D;
