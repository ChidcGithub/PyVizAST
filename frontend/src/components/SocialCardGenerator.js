import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { VERSION } from '../config/version';

// Social Card Generator - Clean black/white minimalist design
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

  // Card style options
  const cardStyles = useMemo(() => [
    { id: 'brand', label: 'Brand', icon: 'logo', disabled: false },
    { id: 'preview2d', label: '2D Preview', icon: '2d', disabled: !hasAnalysis },
    { id: 'preview3d', label: '3D Preview', icon: '3d', disabled: !hasAnalysis },
  ], [hasAnalysis]);

  // Color scheme - black/white only
  const colors = useMemo(() => {
    const isDark = theme === 'dark';
    return {
      isDark,
      bg: isDark ? '#0a0a0a' : '#ffffff',
      bgAlt: isDark ? '#111111' : '#f8f8f8',
      text: isDark ? '#ffffff' : '#0a0a0a',
      textMuted: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.5)',
      textFaint: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)',
      border: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
      grid: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
    };
  }, [theme]);

  // Handle style change
  const handleStyleChange = useCallback(async (style) => {
    setCardStyle(style);
    setCapturedPreview(null);
    
    if (!hasAnalysis && style !== 'brand') return;
    
    if (style === 'preview2d' && onCapture2D) {
      const captured = await onCapture2D();
      if (captured) setCapturedPreview(captured);
    } else if (style === 'preview3d' && onCapture3D) {
      const captured = await onCapture3D();
      if (captured) setCapturedPreview(captured);
    }
  }, [hasAnalysis, onCapture2D, onCapture3D]);

  // Draw minimalist background with subtle texture
  const drawBackground = useCallback((ctx, width, height) => {
    // Base fill
    ctx.fillStyle = colors.bg;
    ctx.fillRect(0, 0, width, height);

    // Subtle gradient overlay for depth
    const gradient = ctx.createRadialGradient(
      width * 0.3, height * 0.3, 0,
      width * 0.5, height * 0.5, width * 0.8
    );
    gradient.addColorStop(0, colors.isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)');
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    // Grid pattern
    ctx.strokeStyle = colors.grid;
    ctx.lineWidth = 1;
    const gridSize = 30;
    
    for (let x = 0; x <= width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }, [colors]);

  // Draw AST tree visualization - clean geometric style
  const drawASTTree = useCallback((ctx, centerX, centerY, width, height) => {
    const nodes = [];
    const baseRadius = Math.min(width, height) * 0.3;
    
    // Generate hierarchical tree
    // Root node
    nodes.push({ x: centerX, y: centerY - baseRadius * 0.65, r: 14, level: 0 });
    
    // Level 1 - 3 nodes
    const l1Angles = [-Math.PI / 5, 0, Math.PI / 5];
    l1Angles.forEach((angle, i) => {
      nodes.push({
        x: centerX + Math.sin(angle) * baseRadius * 0.5,
        y: centerY - baseRadius * 0.1 + Math.cos(angle) * baseRadius * 0.15,
        r: 10,
        level: 1
      });
    });
    
    // Level 2 - 5 nodes
    const l2Positions = [
      { x: centerX - baseRadius * 0.75, y: centerY + baseRadius * 0.35 },
      { x: centerX - baseRadius * 0.4, y: centerY + baseRadius * 0.5 },
      { x: centerX, y: centerY + baseRadius * 0.4 },
      { x: centerX + baseRadius * 0.4, y: centerY + baseRadius * 0.5 },
      { x: centerX + baseRadius * 0.75, y: centerY + baseRadius * 0.35 },
    ];
    l2Positions.forEach(pos => {
      nodes.push({ ...pos, r: 6, level: 2 });
    });

    // Draw connections
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 1;
    
    // Root to level 1
    for (let i = 1; i <= 3; i++) {
      ctx.beginPath();
      ctx.moveTo(nodes[0].x, nodes[0].y);
      ctx.lineTo(nodes[i].x, nodes[i].y);
      ctx.stroke();
    }
    
    // Level 1 to level 2
    const connections = [[4, 5], [5, 6], [6, 7], [7, 8]];
    connections.forEach(([from, to]) => {
      const parentIdx = Math.floor((from - 4) / 2) + 1 + (from > 5 ? 1 : 0);
      const parent = nodes[Math.min(parentIdx, 3)];
      if (parent) {
        [from, to].forEach(idx => {
          if (nodes[idx]) {
            ctx.beginPath();
            ctx.moveTo(parent.x, parent.y);
            ctx.lineTo(nodes[idx].x, nodes[idx].y);
            ctx.stroke();
          }
        });
      }
    });

    // Draw nodes
    nodes.forEach(node => {
      // Node fill
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      ctx.fillStyle = colors.text;
      ctx.fill();
      
      // Inner highlight
      ctx.beginPath();
      ctx.arc(node.x - node.r * 0.25, node.y - node.r * 0.25, node.r * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = colors.isDark ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.5)';
      ctx.fill();
    });

    // Decorative orbit
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 0.5;
    ctx.setLineDash([4, 8]);
    ctx.beginPath();
    ctx.arc(centerX, centerY, baseRadius * 1.3, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  }, [colors]);

  // Draw logo
  const drawLogo = useCallback((ctx, x, y, size) => {
    ctx.save();
    ctx.translate(x, y);
    
    // Braces
    ctx.font = `bold ${size}px "SF Mono", "Fira Code", monospace`;
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('{ }', 0, 0);
    
    // Dots around
    const dots = [
      { angle: -Math.PI / 3, dist: size * 0.9 },
      { angle: -Math.PI / 6, dist: size * 1.05 },
      { angle: Math.PI / 6, dist: size * 1.05 },
      { angle: Math.PI / 3, dist: size * 0.9 },
    ];
    
    dots.forEach(dot => {
      ctx.beginPath();
      ctx.arc(
        Math.cos(dot.angle) * dot.dist,
        Math.sin(dot.angle) * dot.dist,
        2, 0, Math.PI * 2
      );
      ctx.fillStyle = colors.textMuted;
      ctx.fill();
    });
    
    ctx.restore();
  }, [colors]);

  // Draw feature items
  const drawFeatures = useCallback((ctx, y, width, features) => {
    const itemWidth = width / features.length;
    const startX = itemWidth / 2;
    
    features.forEach((feature, i) => {
      const x = startX + i * itemWidth;
      
      // Icon circle
      ctx.beginPath();
      ctx.arc(x, y - 12, 6, 0, Math.PI * 2);
      ctx.fillStyle = colors.text;
      ctx.fill();
      
      // Label
      ctx.font = '500 14px "SF Pro Text", -apple-system, sans-serif';
      ctx.fillStyle = colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(feature, x, y + 4);
    });
  }, [colors]);

  // Generate brand card
  const generateBrandCard = useCallback((ctx, width, height) => {
    const padding = 48;

    // Background
    drawBackground(ctx, width, height);

    // Logo and title
    drawLogo(ctx, padding + 28, padding + 28, 26);
    
    ctx.font = '700 32px "SF Pro Display", -apple-system, sans-serif';
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('PyVizAST', padding + 70, padding + 28);

    // Version
    ctx.font = '500 14px "SF Pro Text", -apple-system, sans-serif';
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'right';
    ctx.fillText(`v${VERSION}`, width - padding - 40, padding + 28);

    // Tagline
    ctx.font = '400 15px "SF Pro Text", -apple-system, sans-serif';
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'left';
    ctx.fillText('Python AST Visualizer & Static Analyzer', padding + 70, padding + 56);

    // Center AST visualization
    drawASTTree(ctx, width / 2, height / 2, width * 0.6, height * 0.45);

    // Features
    const features = ['3D Visualization', 'Code Analysis', 'Security Scan', 'Auto-Fix'];
    drawFeatures(ctx, height - padding - 30, width, features);

    // Bottom border decoration
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, height - padding - 60);
    ctx.lineTo(width - padding, height - padding - 60);
    ctx.stroke();

    // Corner decorations
    const cornerSize = 12;
    ctx.strokeStyle = colors.textFaint;
    ctx.lineWidth = 1;
    
    // Top left
    ctx.beginPath();
    ctx.moveTo(padding, padding + cornerSize);
    ctx.lineTo(padding, padding);
    ctx.lineTo(padding + cornerSize, padding);
    ctx.stroke();
    
    // Top right
    ctx.beginPath();
    ctx.moveTo(width - padding - cornerSize, padding);
    ctx.lineTo(width - padding, padding);
    ctx.lineTo(width - padding, padding + cornerSize);
    ctx.stroke();
    
    // Bottom left
    ctx.beginPath();
    ctx.moveTo(padding, height - padding - cornerSize);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(padding + cornerSize, height - padding);
    ctx.stroke();
    
    // Bottom right
    ctx.beginPath();
    ctx.moveTo(width - padding - cornerSize, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.lineTo(width - padding, height - padding - cornerSize);
    ctx.stroke();

  }, [colors, drawBackground, drawLogo, drawASTTree, drawFeatures]);

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

  // Generate preview card
  const generatePreviewCard = useCallback((ctx, width, height, previewImage, previewType) => {
    const padding = 48;
    const headerHeight = 70;
    const footerHeight = 60;

    // Background
    drawBackground(ctx, width, height);

    // Header
    drawLogo(ctx, padding + 22, padding + 24, 22);
    
    ctx.font = '700 26px "SF Pro Display", -apple-system, sans-serif';
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('PyVizAST', padding + 60, padding + 24);

    // Preview type badge
    ctx.font = '500 13px "SF Pro Text", -apple-system, sans-serif';
    const badgeText = previewType === 'preview2d' ? '2D AST View' : '3D AST View';
    const badgeWidth = ctx.measureText(badgeText).width + 24;
    
    ctx.fillStyle = colors.isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)';
    roundRect(ctx, width - padding - badgeWidth - 10, padding + 8, badgeWidth + 10, 32, 16);
    ctx.fill();
    
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = 1;
    ctx.stroke();
    
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'center';
    ctx.fillText(badgeText, width - padding - badgeWidth / 2 - 5, padding + 24);

    // Preview area
    const previewX = padding;
    const previewY = headerHeight + 10;
    const previewWidth = width - padding * 2;
    const previewHeight = height - headerHeight - footerHeight - 30;

    // Border
    roundRect(ctx, previewX - 1, previewY - 1, previewWidth + 2, previewHeight + 2, 12);
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = 1;
    ctx.stroke();

    if (previewImage) {
      const img = new Image();
      img.src = previewImage;
      
      ctx.save();
      roundRect(ctx, previewX, previewY, previewWidth, previewHeight, 12);
      ctx.clip();
      ctx.drawImage(img, previewX, previewY, previewWidth, previewHeight);
      ctx.restore();
    } else {
      // Placeholder
      roundRect(ctx, previewX, previewY, previewWidth, previewHeight, 12);
      ctx.fillStyle = colors.bgAlt;
      ctx.fill();
      
      // Play icon
      const iconX = width / 2;
      const iconY = previewY + previewHeight / 2 - 20;
      
      ctx.strokeStyle = colors.textFaint;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(iconX - 12, iconY - 15);
      ctx.lineTo(iconX + 15, iconY);
      ctx.lineTo(iconX - 12, iconY + 15);
      ctx.closePath();
      ctx.stroke();
      
      ctx.font = '500 14px "SF Pro Text", -apple-system, sans-serif';
      ctx.fillStyle = colors.textMuted;
      ctx.textAlign = 'center';
      ctx.fillText('Run analysis to enable preview', width / 2, iconY + 40);
    }

    // Footer
    const footerY = height - padding + 8;
    ctx.font = '500 14px "SF Pro Text", -apple-system, sans-serif';
    ctx.fillStyle = colors.textMuted;
    ctx.textAlign = 'left';
    ctx.fillText('Python AST Visualizer', padding, footerY);

    ctx.textAlign = 'right';
    ctx.fillText(`v${VERSION}`, width - padding, footerY);
  }, [colors, drawBackground, drawLogo, roundRect]);

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
          <div className="social-card-header-left">
            <div className="social-card-logo">
              <span>{ }</span>
            </div>
            <div className="social-card-title-group">
              <h3>Generate Social Card</h3>
              <span className="social-card-subtitle">Export shareable image</span>
            </div>
          </div>
          <button className="btn btn-ghost btn-icon social-card-close" onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
              title={style.disabled ? 'Run analysis first' : ''}
            >
              {style.icon === 'logo' && (
                <span className="style-icon-logo">{ }</span>
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
              <span className="style-label">{style.label}</span>
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
            <span>Run code analysis first to capture preview</span>
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
