import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';

// App version
const APP_VERSION = '0.7.0';

// Social Card Generator - creates beautiful black/white themed image cards
function SocialCardGenerator({ 
  isOpen, 
  onClose, 
  theme,
  hasAnalysis,
  viewMode,
  onCapture2D,
  onCapture3D,
}) {
  const canvasRef = useRef(null);
  const [cardStyle, setCardStyle] = useState('brand');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);

  // Card style options - computed based on analysis state
  const cardStyles = useMemo(() => [
    { id: 'brand', label: 'Brand', icon: 'logo', disabled: false },
    { id: 'preview2d', label: '2D Preview', icon: '2d', disabled: !hasAnalysis },
    { id: 'preview3d', label: '3D Preview', icon: '3d', disabled: !hasAnalysis },
  ], [hasAnalysis]);

  // Color scheme - black/white only - memoized
  const colors = useMemo(() => {
    const isDark = theme === 'dark';
    return {
      isDark,
      bg: isDark ? '#0a0a0a' : '#ffffff',
      bgAlt: isDark ? '#141414' : '#f5f5f5',
      text: isDark ? '#ffffff' : '#0a0a0a',
      textMuted: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.5)',
      textFaint: isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.2)',
      border: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
      grid: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)',
      accent: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.08)',
    };
  }, [theme]);

  // Handle style change and capture previews
  const handleStyleChange = useCallback(async (style) => {
    setCardStyle(style);
    setCapturedPreview(null);
    
    if (!hasAnalysis && style !== 'brand') {
      return;
    }
    
    if (style === 'preview2d' && onCapture2D) {
      const captured = await onCapture2D();
      if (captured) {
        setCapturedPreview(captured);
      }
    } else if (style === 'preview3d' && onCapture3D) {
      const captured = await onCapture3D();
      if (captured) {
        setCapturedPreview(captured);
      }
    }
  }, [hasAnalysis, onCapture2D, onCapture3D]);

  // Draw AST node graph for brand card
  const drawASTGraph = useCallback((ctx, centerX, centerY, width, height) => {
    const nodes = [];
    const radius = Math.min(width, height) * 0.35;
    
    // Root node
    nodes.push({ x: centerX, y: centerY - radius * 0.6, r: 18, level: 0 });
    
    // Second level
    for (let i = 0; i < 3; i++) {
      const angle = -Math.PI / 3 + (i * Math.PI / 3);
      nodes.push({
        x: centerX + Math.cos(angle) * radius * 0.5,
        y: centerY - radius * 0.1 + Math.sin(angle) * radius * 0.3,
        r: 12,
        level: 1
      });
    }
    
    // Third level
    for (let i = 0; i < 5; i++) {
      const angle = -Math.PI / 2.5 + (i * Math.PI / 5);
      nodes.push({
        x: centerX + Math.cos(angle) * radius * 0.9,
        y: centerY + radius * 0.35 + Math.sin(angle) * radius * 0.3,
        r: 8,
        level: 2
      });
    }

    // Draw connections
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 1;
    
    for (let i = 1; i <= 3; i++) {
      ctx.beginPath();
      ctx.moveTo(nodes[0].x, nodes[0].y);
      ctx.lineTo(nodes[i].x, nodes[i].y);
      ctx.stroke();
    }
    
    const level2Start = 4;
    const level2Connections = [[0], [1, 2], [3, 4]];
    for (let i = 0; i < 3; i++) {
      const parentNode = nodes[i + 1];
      level2Connections[i].forEach(offset => {
        const childNode = nodes[level2Start + offset];
        if (childNode) {
          ctx.beginPath();
          ctx.moveTo(parentNode.x, parentNode.y);
          ctx.lineTo(childNode.x, childNode.y);
          ctx.stroke();
        }
      });
    }

    // Draw nodes with glow
    nodes.forEach((node) => {
      // Glow effect
      const glowGradient = ctx.createRadialGradient(
        node.x, node.y, 0,
        node.x, node.y, node.r * 2
      );
      glowGradient.addColorStop(0, colors.isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)');
      glowGradient.addColorStop(1, 'transparent');
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r * 2, 0, Math.PI * 2);
      ctx.fillStyle = glowGradient;
      ctx.fill();
      
      // Node
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      const gradient = ctx.createRadialGradient(
        node.x - node.r * 0.3, node.y - node.r * 0.3, 0,
        node.x, node.y, node.r
      );
      gradient.addColorStop(0, colors.isDark ? 'rgba(255,255,255,1)' : 'rgba(0,0,0,1)');
      gradient.addColorStop(1, colors.isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)');
      ctx.fillStyle = gradient;
      ctx.fill();
    });

    // Outer ring
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 0.5;
    ctx.setLineDash([4, 8]);
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 1.5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  }, [colors]);

  // Draw feature icon
  const drawFeatureIcon = useCallback((ctx, x, y, type, color) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    switch (type) {
      case 'gesture': // 3D cube
        ctx.beginPath();
        ctx.rect(-10, -10, 20, 20);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(-10, -10);
        ctx.lineTo(-5, -15);
        ctx.lineTo(15, -15);
        ctx.lineTo(15, 5);
        ctx.lineTo(10, 10);
        ctx.moveTo(-10, -10);
        ctx.lineTo(-5, -15);
        ctx.moveTo(10, -10);
        ctx.lineTo(15, -15);
        ctx.moveTo(10, 10);
        ctx.lineTo(15, 5);
        ctx.stroke();
        break;

      case 'analysis': // Magnifying glass with chart
        ctx.beginPath();
        ctx.arc(-3, -3, 9, 0, Math.PI * 1.5);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(3, 3);
        ctx.lineTo(10, 10);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(-6, 1);
        ctx.lineTo(-2, -4);
        ctx.lineTo(2, 2);
        ctx.stroke();
        break;

      case 'performance': // Speed gauge
        ctx.beginPath();
        ctx.arc(0, 4, 12, Math.PI, 0, false);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, 4);
        ctx.lineTo(6, -3);
        ctx.stroke();
        break;

      case 'autofix': // Magic wand
        ctx.beginPath();
        ctx.moveTo(-10, 10);
        ctx.lineTo(10, -10);
        ctx.stroke();
        [[-5, -6], [6, 5], [-2, -12], [12, 0]].forEach(([sx, sy]) => {
          ctx.beginPath();
          ctx.moveTo(sx - 2, sy);
          ctx.lineTo(sx + 2, sy);
          ctx.moveTo(sx, sy - 2);
          ctx.lineTo(sx, sy + 2);
          ctx.stroke();
        });
        break;

      default:
        ctx.beginPath();
        ctx.arc(0, 0, 8, 0, Math.PI * 2);
        ctx.stroke();
        break;
    }
    ctx.restore();
  }, []);

  // Draw logo
  const drawLogo = useCallback((ctx, x, y, size) => {
    ctx.save();
    ctx.translate(x, y);
    
    // Braces {}
    ctx.font = `bold ${size}px "SF Mono", "Fira Code", monospace`;
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('{}', 0, 0);
    
    // Radiating nodes
    [
      { angle: -Math.PI / 3, dist: size * 0.85, r: 2.5 },
      { angle: -Math.PI / 6, dist: size * 1.0, r: 2 },
      { angle: 0, dist: size * 0.9, r: 3 },
      { angle: Math.PI / 6, dist: size * 1.0, r: 2 },
      { angle: Math.PI / 3, dist: size * 0.85, r: 2.5 },
    ].forEach(node => {
      const nx = Math.cos(node.angle) * node.dist;
      const ny = Math.sin(node.angle) * node.dist;
      
      ctx.beginPath();
      ctx.strokeStyle = colors.textMuted;
      ctx.lineWidth = 0.8;
      ctx.moveTo(Math.cos(node.angle) * size * 0.4, Math.sin(node.angle) * size * 0.4);
      ctx.lineTo(nx, ny);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.arc(nx, ny, node.r, 0, Math.PI * 2);
      ctx.fillStyle = colors.text;
      ctx.fill();
    });
    
    ctx.restore();
  }, [colors]);

  // Round rect helper
  const roundRect = useCallback((ctx, x, y, w, h, r) => {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }, []);

  // Generate brand card
  const generateBrandCard = useCallback((ctx, width, height) => {
    const edgePadding = 40;

    // Background
    ctx.fillStyle = colors.bg;
    ctx.fillRect(0, 0, width, height);

    // Subtle gradient overlay
    const bgGradient = ctx.createRadialGradient(
      width * 0.3, height * 0.3, 0,
      width * 0.5, height * 0.5, width * 0.8
    );
    bgGradient.addColorStop(0, colors.accent);
    bgGradient.addColorStop(1, 'transparent');
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, width, height);

    // Bottom-left grid
    ctx.save();
    ctx.translate(edgePadding, height - edgePadding - 100);
    ctx.strokeStyle = colors.grid;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 7; i++) {
      ctx.beginPath();
      ctx.moveTo(i * 15, 0);
      ctx.lineTo(i * 15, -100);
      ctx.stroke();
    }
    for (let j = 0; j <= 7; j++) {
      ctx.beginPath();
      ctx.moveTo(0, -j * 15);
      ctx.lineTo(100, -j * 15);
      ctx.stroke();
    }
    ctx.restore();

    // Top decoration circles
    ctx.save();
    ctx.translate(width - edgePadding - 40, edgePadding + 40);
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.arc(0, 0, 15 + i * 12, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();

    // Logo
    drawLogo(ctx, edgePadding + 30, edgePadding + 32, 24);
    
    // Project name
    ctx.font = '700 36px "SF Pro Display", -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('PyVizAST', edgePadding + 70, edgePadding + 32);
    
    // Version badge
    ctx.font = '500 16px "SF Pro Text", -apple-system, sans-serif';
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'right';
    ctx.fillText(`v${APP_VERSION}`, width - edgePadding - 50, edgePadding + 32);

    // Center AST visualization
    drawASTGraph(ctx, width / 2, height / 2 - 20, width * 0.6, height * 0.45);

    // Features
    const featuresY = height - edgePadding - 45;
    const features = [
      { icon: 'gesture', label: '3D Gesture Control' },
      { icon: 'analysis', label: 'Code Analysis' },
      { icon: 'performance', label: 'Performance Hotspots' },
      { icon: 'autofix', label: 'Auto-Fix Patches' },
    ];
    
    const featureWidth = 200;
    const startFeatureX = (width - features.length * featureWidth) / 2 + featureWidth / 2;

    features.forEach((feature, i) => {
      const fx = startFeatureX + i * featureWidth;
      drawFeatureIcon(ctx, fx, featuresY - 18, feature.icon, colors.text);
      
      ctx.font = '500 16px "SF Pro Text", -apple-system, sans-serif';
      ctx.fillStyle = colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(feature.label, fx, featuresY + 12);
    });

    // Bottom-right GitHub star
    ctx.save();
    ctx.translate(width - edgePadding - 22, height - edgePadding - 22);
    ctx.beginPath();
    ctx.moveTo(0, -10);
    ctx.lineTo(3, -3);
    ctx.lineTo(10, -3);
    ctx.lineTo(5, 2);
    ctx.lineTo(6, 9);
    ctx.lineTo(0, 5);
    ctx.lineTo(-6, 9);
    ctx.lineTo(-5, 2);
    ctx.lineTo(-10, -3);
    ctx.lineTo(-3, -3);
    ctx.closePath();
    ctx.strokeStyle = colors.textMuted;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
  }, [colors, drawLogo, drawASTGraph, drawFeatureIcon]);

  // Generate preview card (with captured screenshot)
  const generatePreviewCard = useCallback((ctx, width, height, previewImage, previewType) => {
    const edgePadding = 40;
    const headerHeight = 70;
    const footerHeight = 60;

    // Background
    ctx.fillStyle = colors.bg;
    ctx.fillRect(0, 0, width, height);

    // Header section
    // Logo
    drawLogo(ctx, edgePadding + 24, edgePadding + 28, 20);
    
    // Project name
    ctx.font = '700 28px "SF Pro Display", -apple-system, sans-serif';
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('PyVizAST', edgePadding + 60, edgePadding + 28);

    // Preview type badge
    ctx.font = '500 14px "SF Pro Text", -apple-system, sans-serif';
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'right';
    ctx.fillText(previewType === 'preview2d' ? '2D AST View' : '3D AST View', width - edgePadding - 40, edgePadding + 28);

    // Preview area with border
    const previewX = edgePadding;
    const previewY = headerHeight + 10;
    const previewWidth = width - edgePadding * 2;
    const previewHeight = height - headerHeight - footerHeight - 30;

    // Preview container with subtle border
    roundRect(ctx, previewX - 1, previewY - 1, previewWidth + 2, previewHeight + 2, 12);
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Draw captured preview image
    if (previewImage) {
      const img = new Image();
      img.src = previewImage;
      
      // Clip to rounded rect
      ctx.save();
      roundRect(ctx, previewX, previewY, previewWidth, previewHeight, 12);
      ctx.clip();
      
      // Draw image scaled to fit
      ctx.drawImage(img, previewX, previewY, previewWidth, previewHeight);
      ctx.restore();
    } else {
      // Placeholder if no image - show run analysis hint
      roundRect(ctx, previewX, previewY, previewWidth, previewHeight, 12);
      ctx.fillStyle = colors.bgAlt;
      ctx.fill();
      
      // Draw a subtle icon
      const iconCenterX = width / 2;
      const iconCenterY = previewY + previewHeight / 2 - 20;
      ctx.strokeStyle = colors.textFaint;
      ctx.lineWidth = 1.5;
      
      // Play/analyze icon
      ctx.beginPath();
      ctx.moveTo(iconCenterX - 12, iconCenterY - 15);
      ctx.lineTo(iconCenterX + 15, iconCenterY);
      ctx.lineTo(iconCenterX - 12, iconCenterY + 15);
      ctx.closePath();
      ctx.stroke();
      
      ctx.font = '500 16px "SF Pro Text", -apple-system, sans-serif';
      ctx.fillStyle = colors.textMuted;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('Run analysis to enable preview capture', width / 2, iconCenterY + 40);
    }

    // Footer
    const footerY = height - footerHeight + 15;
    ctx.font = '500 14px "SF Pro Text", -apple-system, sans-serif';
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'left';
    ctx.fillText('Python AST Visualizer & Static Analyzer', edgePadding, footerY);

    ctx.textAlign = 'right';
    ctx.fillText(`v${APP_VERSION}`, width - edgePadding, footerY);
  }, [colors, drawLogo, roundRect]);

  // Generate card image
  const generateCard = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    setIsGenerating(true);
    const ctx = canvas.getContext('2d');
    const width = 1200;
    const height = 630;

    canvas.width = width;
    canvas.height = height;

    if (cardStyle === 'brand') {
      generateBrandCard(ctx, width, height);
      const imageData = canvas.toDataURL('image/png');
      setGeneratedImage(imageData);
      setIsGenerating(false);
    } else {
      // Preview cards - use capturedPreview
      if (capturedPreview) {
        const img = new Image();
        img.onload = () => {
          generatePreviewCard(ctx, width, height, capturedPreview, cardStyle);
          const imageData = canvas.toDataURL('image/png');
          setGeneratedImage(imageData);
          setIsGenerating(false);
        };
        img.onerror = () => {
          generatePreviewCard(ctx, width, height, null, cardStyle);
          const imageData = canvas.toDataURL('image/png');
          setGeneratedImage(imageData);
          setIsGenerating(false);
        };
        img.src = capturedPreview;
      } else {
        generatePreviewCard(ctx, width, height, null, cardStyle);
        const imageData = canvas.toDataURL('image/png');
        setGeneratedImage(imageData);
        setIsGenerating(false);
      }
    }
  }, [cardStyle, capturedPreview, generateBrandCard, generatePreviewCard]);

  // Download image
  const handleDownload = useCallback(() => {
    if (!generatedImage) return;

    const link = document.createElement('a');
    link.download = `pyvizast-card-${cardStyle}-${Date.now()}.png`;
    link.href = generatedImage;
    link.click();
  }, [generatedImage, cardStyle]);

  // Generate on open or style change
  useEffect(() => {
    if (isOpen) {
      generateCard();
    }
  }, [isOpen, cardStyle, capturedPreview, theme, generateCard]);

  // Reset on close
  useEffect(() => {
    if (!isOpen) {
      setCapturedPreview(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="social-card-overlay" onClick={onClose}>
      <div className="social-card-modal" onClick={e => e.stopPropagation()}>
        <div className="social-card-header">
          <h3>Generate Social Card</h3>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="social-card-style-selector">
          {cardStyles.map(style => (
            <button
              key={style.id}
              className={`style-btn ${cardStyle === style.id ? 'active' : ''}`}
              onClick={() => handleStyleChange(style.id)}
              disabled={style.disabled}
              title={style.disabled ? 'Run analysis first to enable this option' : ''}
            >
              {style.icon === 'logo' && (
                <span className="style-icon-text">PV</span>
              )}
              {style.icon === '2d' && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <circle cx="15.5" cy="8.5" r="1.5" />
                  <circle cx="8.5" cy="15.5" r="1.5" />
                  <circle cx="15.5" cy="15.5" r="1.5" />
                </svg>
              )}
              {style.icon === '3d' && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              )}
              {style.label}
            </button>
          ))}
        </div>

        {!hasAnalysis && cardStyle !== 'brand' && (
          <div className="social-card-hint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>Run code analysis first to capture visualization preview</span>
          </div>
        )}

        <div className="social-card-preview">
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          {isGenerating ? (
            <div className="card-loading">
              <div className="spinner"></div>
              <span>Generating...</span>
            </div>
          ) : generatedImage ? (
            <img src={generatedImage} alt="PyVizAST Social Card" className="preview-image" />
          ) : null}
        </div>

        <div className="social-card-actions">
          <button
            className="btn btn-secondary"
            onClick={generateCard}
            disabled={isGenerating}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" />
            </svg>
            Regenerate
          </button>
          <button
            className="btn btn-primary"
            onClick={handleDownload}
            disabled={!generatedImage || isGenerating}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download PNG
          </button>
        </div>
      </div>
    </div>
  );
}

export default SocialCardGenerator;
