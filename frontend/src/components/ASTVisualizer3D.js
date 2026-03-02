import React, { useEffect, useRef, useState, useMemo, useCallback, Suspense, forwardRef, useImperativeHandle } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Line, Billboard } from '@react-three/drei';
import * as THREE from 'three';

// Performance constants
const MAX_NODES_3D = 200;
const NODE_SPACING = 3;
const LAYOUT_ITERATIONS = 100;

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
 * 3D Force-directed layout algorithm
 */
function compute3DLayout(nodes, edges, iterations = LAYOUT_ITERATIONS) {
  if (nodes.length === 0) return [];
  
  const positions = new Map();
  const nodeMap = new Map();
  
  // Initialize positions
  nodes.forEach((node, i) => {
    // Spherical initialization based on hierarchy
    const level = getNodeLevel(node, nodes);
    const angle = (i / nodes.length) * Math.PI * 2;
    const radius = level * NODE_SPACING;
    
    positions.set(node.id, {
      x: Math.cos(angle) * radius + (Math.random() - 0.5) * 2,
      y: level * NODE_SPACING * 0.5,
      z: Math.sin(angle) * radius + (Math.random() - 0.5) * 2,
      vx: 0,
      vy: 0,
      vz: 0
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
  
  // Force simulation
  const repulsion = 15;
  const attraction = 0.05;
  const damping = 0.9;
  const gravity = 0.01;
  
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
      
      const force = (dist - NODE_SPACING * 2) * attraction;
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
    
    // Gravity toward center
    positions.forEach(p => {
      p.vx -= p.x * gravity;
      p.vy -= p.y * gravity;
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
 * 3D Node component
 */
function Node3D({ position, node, isSelected, isFocused, isDimmed, isSignal, onClick, onLongPress, theme }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);
  const longPressTimer = useRef(null);
  const pointerDownTime = useRef(0);
  const signalRef = useRef(0);
  const [signalIntensity, setSignalIntensity] = useState(0);
  // 使用 ref 追踪上次渲染的信号强度，避免频繁状态更新
  const lastSignalIntensityRef = useRef(0);
  // 状态更新阈值，只有变化超过此值才触发更新
  const SIGNAL_UPDATE_THRESHOLD = 0.05;
  
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
  
  // Animation
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.scale.lerp(new THREE.Vector3(size, size, size), 0.1);
    }
    
    // Signal wave animation - smooth fade in/out
    if (isSignal) {
      // Quick fade in
      signalRef.current = Math.min(signalRef.current + 0.08, 1);
    } else {
      // Slow fade out
      signalRef.current = Math.max(signalRef.current - 0.03, 0);
    }
    
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
  
  // Determine colors based on signal intensity (white glow theme)
  const hasSignal = signalIntensity > 0;
  const nodeColor = hasSignal 
    ? '#ffffff'
    : isFocused ? '#ffffff' : isSelected ? '#e0e0e0' : hovered ? '#d0d0d0' : color;
  const emissiveColor = hasSignal ? '#ffffff' : (isFocused || isSelected || hovered) ? '#888888' : '#000000';
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
      
      {/* Signal glow effect - single optimized mesh with white color */}
      {signalIntensity > 0 && (
        <mesh scale={1.4 + signalIntensity * 0.4}>
          <sphereGeometry args={[0.5, 8, 8]} />
          <meshBasicMaterial 
            color="#ffffff" 
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
}

/**
 * 3D Edge component
 */
function Edge3D({ start, end, isHighlighted, isDimmed, isSignal }) {
  const points = useMemo(() => {
    return [
      new THREE.Vector3(start.x, start.y, start.z),
      new THREE.Vector3(end.x, end.y, end.z)
    ];
  }, [start, end]);
  
  // White/gray theme for edges
  const color = isSignal ? '#ffffff' : isHighlighted ? '#cccccc' : 'rgba(255,255,255,0.15)';
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
}

/**
 * Signal particle that travels along edges (optimized)
 * White particle with simple glow trail
 */
function SignalParticle({ start, end, progress }) {
  // Calculate current position (no useMemo to reduce overhead)
  const x = start.x + (end.x - start.x) * progress;
  const y = start.y + (end.y - start.y) * progress;
  const z = start.z + (end.z - start.z) * progress;
  
  // Trail opacity fades based on progress
  const trailOpacity = Math.max(0, 0.8 - progress * 0.5);
  const glowSize = 0.12 + progress * 0.08;
  
  return (
    <group position={[x, y, z]}>
      {/* Core white particle - low poly sphere */}
      <mesh>
        <sphereGeometry args={[0.08, 8, 8]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      
      {/* Outer glow - single mesh instead of multiple */}
      <mesh scale={glowSize * 8}>
        <sphereGeometry args={[0.1, 8, 8]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={trailOpacity * 0.6} />
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
  
  // Expose resetCamera to parent component
  useImperativeHandle(ref, () => ({
    resetCamera
  }), [resetCamera]);
  
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
function ASTVisualizer3D({ graph, theme, onGoToLine }) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [focusedNode, setFocusedNode] = useState(null);
  const [signalParticles, setSignalParticles] = useState([]); // Particles traveling along edges
  const [detailLevel, setDetailLevel] = useState('normal');
  const [isLayoutReady, setIsLayoutReady] = useState(false);
  const particleIdRef = useRef(0);
  const sceneRef = useRef(null); // Ref to access Scene methods
  
  // Track timers and animation frames for cleanup
  const timersRef = useRef(new Set());
  const animationFramesRef = useRef(new Set());
  
  // 搜索相关状态
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [selectedSearchIndex, setSelectedSearchIndex] = useState(-1);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState(new Set());
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
  
  // 搜索节点
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    setSelectedSearchIndex(-1);
    
    if (!query.trim() || !graph) {
      setSearchResults([]);
      setHighlightedNodeIds(new Set());
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
    setHighlightedNodeIds(new Set(results.filter(n => n && n.id).map(n => n.id)));
  }, [graph]);
  
  // 清除搜索
  const clearSearch = useCallback(() => {
    setSearchQuery('');
    setSearchResults([]);
    setSelectedSearchIndex(-1);
    setIsSearchOpen(false);
    setHighlightedNodeIds(new Set());
    setFocusedNode(null);
  }, []);
  
  // 聚焦到搜索结果
  const focusSearchResult = useCallback((node, index) => {
    // 严格的空值检查
    if (!node || typeof node !== 'object' || !node.id) return;
    setSelectedSearchIndex(index);
    setSelectedNode(node);
    setFocusedNode(node);
  }, []);
  
  // 跳转到编辑器对应行
  const handleGoToLine = useCallback((node) => {
    if (node && onGoToLine && node.lineno) {
      onGoToLine(node.lineno, node.end_lineno);
    }
    clearSearch();
  }, [onGoToLine, clearSearch]);
  
  // 键盘导航搜索结果
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
    } else {
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
    const result = compute3DLayout(filteredElements.nodes, filteredElements.edges);
    setIsLayoutReady(true);
    return result;
  }, [filteredElements]);
  
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
            <option value="overview">Overview</option>
            <option value="normal">Normal</option>
            <option value="detail">Detail</option>
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
      
      <div className="visualizer-3d-content">
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
                placeholder="搜索函数、类、变量名..."
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
                        console.warn('Search result click error:', e);
                      }
                    }}
                    onMouseEnter={() => {
                      try {
                        if (node && node.id) focusSearchResult(node, index);
                      } catch (e) {
                        console.warn('Search result hover error:', e);
                      }
                    }}
                  >
                    <span className="result-icon">{node.icon || '•'}</span>
                    <div className="result-content">
                      <span className="result-name">{node.name || node.type}</span>
                      <span className="result-type">{node.description || node.type}</span>
                    </div>
                    {node.lineno && <span className="result-line">行 {node.lineno}</span>}
                  </div>
                ))}
              </div>
            )}
            
            {searchQuery && searchResults.length === 0 && (
              <div className="search-no-results">
                未找到匹配的节点
              </div>
            )}
          </div>
        )}
        
        {!isLayoutReady ? (
          <div className="rendering-overlay">
            <div className="rendering-spinner"></div>
            <span>Computing 3D layout...</span>
          </div>
        ) : (
          <Canvas
            camera={{ position: [20, 20, 20], fov: 50 }}
            gl={{ antialias: true, alpha: true }}
            style={{ background: theme === 'dark' ? '#0a0a0a' : '#ffffff' }}
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
          <div className={`node-detail-panel ${focusedNode ? 'focused-panel' : ''}`}>
            <div className="panel-header">
              <div className="panel-header-main">
                <span className="node-icon">{(focusedNode || selectedNode)?.icon || '•'}</span>
                <h4>{(focusedNode || selectedNode)?.description || (focusedNode || selectedNode)?.type}</h4>
              </div>
              {(focusedNode || selectedNode)?.name && <span className="node-name">{(focusedNode || selectedNode)?.name}</span>}
            </div>
            <div className="panel-body">
              {(focusedNode || selectedNode)?.label && (
                <div className="detail-item code-label">
                  <span className="detail-label">代码结构</span>
                  <code className="detail-code">{(focusedNode || selectedNode)?.label}</code>
                </div>
              )}
              {(focusedNode || selectedNode)?.lineno && (
                <div className="detail-item">
                  <span className="detail-label">位置</span>
                  <span className="detail-value">第 {(focusedNode || selectedNode)?.lineno} 行</span>
                </div>
              )}
              {(focusedNode || selectedNode)?.explanation && (
                <div className="detail-item explanation">
                  <span className="detail-label">说明</span>
                  <p className="explanation-text">{(focusedNode || selectedNode)?.explanation}</p>
                </div>
              )}
              {(focusedNode || selectedNode)?.docstring && (
                <div className="detail-item">
                  <span className="detail-label">文档字符串</span>
                  <p className="docstring">{(focusedNode || selectedNode)?.docstring}</p>
                </div>
              )}
              {(focusedNode || selectedNode)?.sourceCode && (
                <div className="detail-item">
                  <span className="detail-label">源代码</span>
                  <pre className="source-code">{(focusedNode || selectedNode)?.sourceCode}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <div className="visualizer-legend-3d">
        <div className="legend-item">
          <span className="legend-shape box"></span>
          <span>结构节点</span>
        </div>
        <div className="legend-item">
          <span className="legend-shape diamond"></span>
          <span>控制流</span>
        </div>
        <div className="legend-item">
          <span className="legend-shape circle"></span>
          <span>表达式</span>
        </div>
        <div className="legend-hint">拖动旋转 | 滚轮缩放 | 点击选中 | 长按聚焦 | WASD移动 | 空格上升 | Shift下降</div>
      </div>
    </div>
  );
}

export default ASTVisualizer3D;
