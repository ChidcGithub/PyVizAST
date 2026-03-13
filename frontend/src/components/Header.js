import React, { useState, useCallback, useEffect, useRef } from 'react';

const DECRYPT_KEY = 42;

// Simple XOR-based decryption
const decrypt = (encrypted) => {
  try {
    const decoded = atob(encrypted);
    return decoded.split('').map(c => String.fromCharCode(c.charCodeAt(0) ^ DECRYPT_KEY)).join('');
  } catch {
    return '';
  }
};

// Version info
const APP_VERSION = '0.7.0-rc3';
const APP_BUILD = '2102';

// Get actual encrypted values (these are pre-encrypted)
const AUTHOR_DATA = {
  author: decrypt('aUJDTkk='),
  link: decrypt('TUNeQl9IBElFRwVJQkNOSW1DXkJfSA=='),
};

// Morandi color palette (low saturation, elegant tones)
const CONFETTI_COLORS = [
  '#a7a0b1', '#b8a99a', '#8e9aaf', '#c4b7a6', '#9ca8b8',
  '#c9b1af', '#a8b0b5', '#b5b8a6', '#a0a8b0', '#b0a8a0',
];

// Advanced Physics-based Confetti Component with realistic flutter
function Confetti({ show }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    if (!show) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    canvas.width = width;
    canvas.height = height;

    // Create 300 particles
    const particles = [];
    for (let i = 0; i < 300; i++) {
      const fromLeft = i < 150;
      
      // Spray angle: left corner sprays right, right corner sprays left
      const angleBase = fromLeft ? 15 : 165;
      const angleSpread = 130;
      const angle = (angleBase + Math.random() * angleSpread) * (Math.PI / 180);
      
      // Variable spray speed for depth effect
      const speed = 350 + Math.random() * 350;
      
      // Particle size
      const size = 7 + Math.random() * 8;
      
      particles.push({
        // Position
        x: fromLeft ? -20 : width + 20,
        y: -20,
        
        // Velocity
        vx: Math.cos(angle) * speed,
        vy: -Math.abs(Math.sin(angle)) * speed * 0.6 - 150 - Math.random() * 200,
        
        // Physical properties
        size: size,
        width: size * (0.5 + Math.random() * 0.5),
        height: size * (0.7 + Math.random() * 0.6),
        color: CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)],
        mass: 0.5 + Math.random() * 0.5,
        
        // Rotation (3D flip effect)
        rotation: Math.random() * 360,
        rotationVelocity: (Math.random() - 0.5) * 8,
        tilt: Math.random() * 360,
        tiltVelocity: (Math.random() - 0.5) * 15,
        
        // Flutter/wobble for realistic paper fall
        flutterPhase: Math.random() * Math.PI * 2,
        flutterSpeed: 3 + Math.random() * 4,
        flutterAmplitude: 40 + Math.random() * 80,
        
        // Sway for curved path
        swayPhase: Math.random() * Math.PI * 2,
        swaySpeed: 0.5 + Math.random() * 1,
        swayAmplitude: 20 + Math.random() * 40,
        
        // Bend/Fold effect (natural paper curling)
        bendPhase: Math.random() * Math.PI * 2,
        bendSpeed: 1.5 + Math.random() * 2,
        bendAmount: 0.15 + Math.random() * 0.25, // How much the paper bends
        bendDirection: Math.random() > 0.5 ? 1 : -1,
        foldPhase: Math.random() * Math.PI * 2,
        foldSpeed: 0.8 + Math.random() * 1.2,
        
        // Shape variation
        shape: Math.floor(Math.random() * 3), // 0: paper strip, 1: curled paper, 2: folded rectangle
        
        // State
        opacity: 1,
        delay: Math.random() * 0.6,
        active: false,
        
        // Trail for motion blur effect
        prevX: 0,
        prevY: 0,
      });
    }

    const startTime = performance.now();
    let lastTime = startTime;

    const animate = (currentTime) => {
      const elapsed = (currentTime - startTime) / 1000;
      const dt = Math.min((currentTime - lastTime) / 1000, 0.025);
      lastTime = currentTime;
      
      ctx.clearRect(0, 0, width, height);
      
      let activeCount = 0;
      
      for (const p of particles) {
        // Delay start
        if (elapsed < p.delay) {
          activeCount++;
          continue;
        }
        
        if (!p.active) {
          p.active = true;
          p.prevX = p.x;
          p.prevY = p.y;
        }
        
        // Store previous position for trail
        p.prevX = p.x;
        p.prevY = p.y;
        
        // === ADVANCED PHYSICS ===
        
        // Gravity (reduced for slower, floaty fall)
        const gravity = 120 * p.mass;
        p.vy += gravity * dt;
        
        // Air resistance / drag
        const dragX = 0.985;
        const dragY = 0.995;
        p.vx *= dragX;
        p.vy *= dragY;
        
        // Flutter effect (rapid oscillation like falling paper)
        p.flutterPhase += p.flutterSpeed * dt;
        const flutterForce = Math.sin(p.flutterPhase) * p.flutterAmplitude;
        
        // Sway effect (slower curved path)
        p.swayPhase += p.swaySpeed * dt;
        const swayForce = Math.sin(p.swayPhase) * p.swayAmplitude;
        
        // Combined horizontal drift
        const totalDrift = (flutterForce + swayForce) * dt;
        
        // Terminal velocity limiting
        const terminalVelocity = 300;
        if (p.vy > terminalVelocity) {
          p.vy = terminalVelocity + (p.vy - terminalVelocity) * 0.1;
        }
        
        // Update position
        p.x += p.vx * dt + totalDrift;
        p.y += p.vy * dt;
        
        // Rotation (spinning)
        p.rotation += p.rotationVelocity * (1 + Math.abs(p.vy) * 0.002);
        
        // Tilt (3D flip)
        p.tilt += p.tiltVelocity;
        
        // Update bend/fold phases
        p.bendPhase += p.bendSpeed * dt;
        p.foldPhase += p.foldSpeed * dt;
        
        // === FADE OUT EFFECT ===
        // Position-based fade (starts at 50% screen height)
        if (p.y > height * 0.5) {
          const positionFade = 1 - (p.y - height * 0.5) / (height * 0.5);
          p.opacity = Math.min(p.opacity, Math.max(0, positionFade));
        }
        
        // Time-based fade (smooth fade near animation end)
        const timeFadeStart = 8; // seconds
        const timeFadeDuration = 4; // seconds
        if (elapsed > timeFadeStart) {
          const timeFade = 1 - (elapsed - timeFadeStart) / timeFadeDuration;
          p.opacity = Math.min(p.opacity, Math.max(0, timeFade));
        }
        
        // Smooth opacity decay
        p.opacity = Math.max(0, p.opacity);
        
        // Keep rendering if on screen
        if (p.y < height + 100 && p.opacity > 0.01) {
          activeCount++;
          
          // === RENDERING ===
          ctx.save();
          
          // Motion blur trail (subtle)
          if (p.vy > 50 && p.opacity > 0.3) {
            ctx.globalAlpha = p.opacity * 0.25;
            ctx.translate(p.prevX, p.prevY);
            ctx.rotate((p.rotation - p.rotationVelocity * 2) * Math.PI / 180);
            drawParticle(ctx, p, true);
            ctx.setTransform(1, 0, 0, 1, 0, 0);
          }
          
          // Main particle
          ctx.globalAlpha = p.opacity;
          ctx.translate(p.x, p.y);
          
          // Combined rotation for 3D effect
          const rotRad = p.rotation * Math.PI / 180;
          const tiltRad = p.tilt * Math.PI / 180;
          
          // 3D transformation
          const scaleX = Math.cos(tiltRad) * 0.5 + 0.5;
          const scaleY = Math.abs(Math.sin(tiltRad)) * 0.3 + 0.7;
          
          ctx.rotate(rotRad);
          ctx.scale(scaleX, scaleY);
          
          ctx.fillStyle = p.color;
          drawParticle(ctx, p, false);
          
          ctx.restore();
        }
      }
      
      // Continue animation
      if (activeCount > 0 && elapsed < 12) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };
    
    // Helper to draw curved/folded particle
    function drawParticle(ctx, p, isTrail) {
      const w = p.width;
      const h = p.height;
      const alpha = isTrail ? 0.5 : 1;
      
      ctx.globalAlpha *= alpha;
      
      // Calculate current bend amount (oscillating for natural feel)
      const currentBend = Math.sin(p.bendPhase) * p.bendAmount * p.bendDirection;
      const currentFold = Math.sin(p.foldPhase) * 0.3;
      
      switch (p.shape) {
        case 0: // Curved paper strip (realistic flutter)
          drawCurvedStrip(ctx, w, h, currentBend, currentFold);
          break;
          
        case 1: // Folding paper (like a small note)
          drawFoldedPaper(ctx, w, h, currentBend, currentFold);
          break;
          
        case 2: // Wavy ribbon
          drawWavyRibbon(ctx, w, h, currentBend, p.bendPhase);
          break;
          
        default:
          drawCurvedStrip(ctx, w, h, currentBend, currentFold);
          break;
      }
    }
    
    // Draw a curved paper strip with natural bend
    function drawCurvedStrip(ctx, w, h, bend, fold) {
      const halfH = h / 2;
      const halfW = w / 2;
      
      ctx.beginPath();
      
      // Create curved edges using bezier curves
      // Left edge with bend
      ctx.moveTo(-halfW, -halfH);
      const leftMidBend = bend * h * 0.8;
      ctx.bezierCurveTo(
        -halfW + bend * w, -halfH * 0.5,      // control point 1
        -halfW + bend * w * 1.5, 0,           // control point 2
        -halfW + leftMidBend, halfH           // end point (bottom left)
      );
      
      // Bottom edge with slight curve
      ctx.bezierCurveTo(
        -halfW * 0.3 + bend * w, halfH + fold * h * 0.3,
        halfW * 0.3 + bend * w, halfH + fold * h * 0.3,
        halfW - leftMidBend, halfH
      );
      
      // Right edge with bend
      ctx.bezierCurveTo(
        halfW - bend * w * 1.5, 0,
        halfW - bend * w, -halfH * 0.5,
        halfW, -halfH
      );
      
      // Top edge
      ctx.bezierCurveTo(
        halfW * 0.5, -halfH - fold * h * 0.2,
        -halfW * 0.5, -halfH - fold * h * 0.2,
        -halfW, -halfH
      );
      
      ctx.closePath();
      ctx.fill();
      
      // Add subtle highlight for 3D effect
      ctx.save();
      ctx.globalAlpha *= 0.15;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.moveTo(-halfW + bend * w * 0.5, -halfH * 0.8);
      ctx.bezierCurveTo(
        0, -halfH * 0.6,
        halfW * 0.3, -halfH * 0.4,
        halfW * 0.5, -halfH * 0.2
      );
      ctx.bezierCurveTo(
        halfW * 0.3, -halfH * 0.5,
        -halfW * 0.3, -halfH * 0.7,
        -halfW + bend * w * 0.5, -halfH * 0.8
      );
      ctx.fill();
      ctx.restore();
    }
    
    // Draw a folded paper (like origami)
    function drawFoldedPaper(ctx, w, h, bend, fold) {
      const halfH = h / 2;
      const halfW = w / 2;
      const foldAmount = Math.abs(fold) * h * 0.4;
      
      ctx.beginPath();
      
      // Create folded shape
      ctx.moveTo(-halfW, -halfH);
      ctx.lineTo(halfW, -halfH);
      
      // Fold in the paper at one point
      if (fold > 0) {
        ctx.lineTo(halfW * 0.7, -halfH + foldAmount);
        ctx.lineTo(halfW, 0);
        ctx.lineTo(halfW * 0.8, halfH * 0.5);
      } else {
        ctx.lineTo(halfW, 0);
        ctx.lineTo(halfW * 0.6, -halfH * 0.3 + foldAmount);
      }
      
      // Bottom with bend
      ctx.bezierCurveTo(
        halfW * 0.3 + bend * w, halfH * 0.8,
        -halfW * 0.3 + bend * w, halfH * 0.8,
        -halfW, halfH
      );
      
      // Left edge
      ctx.bezierCurveTo(
        -halfW + bend * w * 0.5, 0,
        -halfW + bend * w * 0.3, -halfH * 0.5,
        -halfW, -halfH
      );
      
      ctx.closePath();
      ctx.fill();
      
      // Add fold line highlight
      ctx.save();
      ctx.globalAlpha *= 0.2;
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(halfW, -halfH);
      ctx.lineTo(halfW * 0.7, -halfH + foldAmount * 0.5);
      ctx.stroke();
      ctx.restore();
    }
    
    // Draw a wavy ribbon
    function drawWavyRibbon(ctx, w, h, bend, phase) {
      const halfH = h / 2;
      const halfW = w / 2;
      const segments = 8;
      const segmentHeight = h / segments;
      
      ctx.beginPath();
      
      // Draw wavy top edge
      ctx.moveTo(-halfW, -halfH);
      for (let i = 0; i <= segments; i++) {
        const y = -halfH + i * segmentHeight;
        const wave = Math.sin(phase + i * 0.5) * bend * w * 2;
        const x = -halfW + wave;
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      // Draw wavy bottom edge (offset)
      for (let i = segments; i >= 0; i--) {
        const y = -halfH + i * segmentHeight;
        const wave = Math.sin(phase + i * 0.5 + 0.3) * bend * w * 2;
        const x = halfW + wave;
        ctx.lineTo(x, y);
      }
      
      ctx.closePath();
      ctx.fill();
      
      // Add shimmer effect
      ctx.save();
      ctx.globalAlpha *= 0.1;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      for (let i = 0; i < segments; i += 2) {
        const y = -halfH + i * segmentHeight;
        const wave = Math.sin(phase + i * 0.5) * bend * w;
        ctx.fillRect(-halfW * 0.3 + wave, y, w * 0.6, segmentHeight);
      }
      ctx.restore();
    }

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [show]);

  if (!show) return null;

  return (
    <canvas
      ref={canvasRef}
      className="confetti-canvas"
    />
  );
}

function Header({ 
  onAnalyze, 
  onToggleSidebar, 
  isLoading, 
  theme, 
  onThemeChange,
  analysisMode = 'file', // 'file' or 'project'
  onAnalysisModeChange,
  onShare,
  onExport,
  canExport = false,
  gestureEnabled = false,
  onGestureToggle,
}) {
  const [clickCount, setClickCount] = useState(0);
  const [showEasterEgg, setShowEasterEgg] = useState(false);
  const [lastClickTime, setLastClickTime] = useState(0);

  const handleLogoClick = useCallback(() => {
    const now = Date.now();
    // Reset if more than 2 seconds between clicks
    if (now - lastClickTime > 2000) {
      setClickCount(1);
    } else {
      setClickCount(prev => {
        const newCount = prev + 1;
        if (newCount >= 5) {
          setShowEasterEgg(true);
          return 0;
        }
        return newCount;
      });
    }
    setLastClickTime(now);
  }, [lastClickTime]);

  const closeEasterEgg = useCallback(() => {
    setShowEasterEgg(false);
  }, []);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && showEasterEgg) {
        closeEasterEgg();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showEasterEgg, closeEasterEgg]);

  return (
    <>
      <header className="header">
        <div className="header-left">
          <button className="btn btn-ghost menu-toggle" onClick={onToggleSidebar}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          
          <div className="logo">
            <span 
              className="logo-icon" 
              onClick={handleLogoClick}
              style={{ cursor: 'pointer', userSelect: 'none' }}
              title={clickCount > 0 ? `${5 - clickCount} more...` : ''}
            >
              PV
            </span>
            <span className="logo-text">PyVizAST</span>
          </div>

        {/* Analysis mode switch */}
        {onAnalysisModeChange && (
          <div className="mode-switch">
            <button 
              className={`mode-btn ${analysisMode === 'file' ? 'active' : ''}`}
              onClick={() => onAnalysisModeChange('file')}
              title="Single file analysis"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>File</span>
            </button>
            <button 
              className={`mode-btn ${analysisMode === 'project' ? 'active' : ''}`}
              onClick={() => onAnalysisModeChange('project')}
              title="Project-level analysis"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              <span>Project</span>
            </button>
          </div>
        )}
      </div>
      
      <div className="header-center">
        <nav className="header-nav">
          <a href="https://github.com/ChidcGithub/PyVizAST#features" className="nav-link">Features</a>
          <a href="http://localhost:8000/docs" className="nav-link">Docs</a>
          <a href="https://github.com/ChidcGithub/PyVizAST" target="_blank" rel="noopener noreferrer" className="nav-link">
            GitHub
          </a>
        </nav>
      </div>
      
      <div className="header-right">
        {/* Share button */}
        {onShare && (
          <button 
            className="btn btn-ghost share-btn"
            onClick={onShare}
            title="Share code via URL"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
            <span className="btn-text">Share</span>
          </button>
        )}
        
        {/* Export button */}
        {onExport && (
          <button 
            className="btn btn-ghost export-btn"
            onClick={onExport}
            disabled={!canExport}
            title={canExport ? "Export analysis report" : "Run analysis first to export"}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span className="btn-text">Export</span>
          </button>
        )}
        
        {/* Gesture control toggle */}
        {onGestureToggle && (
          <button 
            className={`header-gesture-btn ${gestureEnabled ? 'active' : ''}`}
            onClick={onGestureToggle}
            title={gestureEnabled ? 'Disable gesture control' : 'Enable gesture control (camera required)'}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0" />
              <path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2" />
              <path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8" />
              <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15" />
            </svg>
            <span className="btn-text">Gesture</span>
            <span className="gesture-indicator"></span>
          </button>
        )}
        
        {/* Theme toggle - more prominent */}
        <div className="theme-toggle-wrapper">
          <button 
            className={`btn btn-ghost theme-toggle ${theme}`}
            onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
            title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          >
            <div className="theme-toggle-track">
              <div className="theme-toggle-thumb">
                {theme === 'dark' ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="5" />
                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </div>
            </div>
          </button>
        </div>
        
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
      </div>
    </header>

      {/* Easter Egg Modal */}
      {showEasterEgg && (
        <>
          <Confetti show={showEasterEgg} />
          <div className="easter-egg-overlay" onClick={closeEasterEgg}>
            <div className={`easter-egg-modal ${theme}`} onClick={e => e.stopPropagation()}>
              <button className="easter-egg-close" onClick={closeEasterEgg}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
              <div className="easter-egg-content">
                <div className="easter-egg-icon">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <defs>
                      <linearGradient id="logo-gradient-dark" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#404040" />
                        <stop offset="50%" stopColor="#606060" />
                        <stop offset="100%" stopColor="#808080" />
                      </linearGradient>
                      <linearGradient id="logo-gradient-light" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#e0e0e0" />
                        <stop offset="50%" stopColor="#c0c0c0" />
                        <stop offset="100%" stopColor="#a0a0a0" />
                      </linearGradient>
                    </defs>
                    <rect x="4" y="4" width="40" height="40" rx="10" fill="url(#logo-gradient-dark)" />
                    <text x="24" y="32" textAnchor="middle" fill="#ffffff" fontSize="18" fontWeight="bold" fontFamily="system-ui">PV</text>
                  </svg>
                </div>
                <h3>You found a secret!</h3>
                <div className="easter-egg-info">
                  <div className="info-row">
                    <span className="info-label">Author</span>
                    <span className="info-value">{AUTHOR_DATA.author}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">GitHub</span>
                    <a 
                      href={`https://${AUTHOR_DATA.link}`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="info-link"
                    >
                      {AUTHOR_DATA.link}
                    </a>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Version</span>
                    <span className="info-value">v{APP_VERSION}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Build</span>
                    <span className="info-value info-build">{APP_BUILD}</span>
                  </div>
                </div>
                <p className="easter-egg-hint">
                  Thanks for exploring PyVizAST!
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

export default Header;
