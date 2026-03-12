import React, { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle } from 'react';
import gestureService, { GestureType, GestureAction } from '../utils/GestureService';
import './GestureControl.css';

// SVG gesture icon components
const ThumbUpIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
  </svg>
);

const ThumbDownIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
  </svg>
);

const FistIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="8" />
    <path d="M12 8v8M8 10h8M8 14h8" />
  </svg>
);

const PalmIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0" />
    <path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2" />
    <path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8" />
    <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15" />
  </svg>
);

const VictoryIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 3v10M16 3v10" />
    <path d="M8 13c0 2 2 4 4 4s4-2 4-4" />
    <path d="M4 21l4-4M20 21l-4-4" />
  </svg>
);

const PointingIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2v10" />
    <circle cx="12" cy="14" r="2" />
    <path d="M12 16v6" />
  </svg>
);

const PinchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="3" />
    <circle cx="16" cy="16" r="3" />
    <path d="M10.5 10.5l3 3" />
    <path d="M6 8h4M8 6v4" />
    <path d="M14 16h4M16 14v4" />
  </svg>
);

// Gesture icon mapping
const GESTURE_ICONS = {
  [GestureType.THUMB_UP]: ThumbUpIcon,
  [GestureType.THUMB_DOWN]: ThumbDownIcon,
  [GestureType.CLOSED_FIST]: FistIcon,
  [GestureType.OPEN_PALM]: PalmIcon,
  [GestureType.VICTORY]: VictoryIcon,
  [GestureType.POINTING_UP]: PointingIcon,
  'PINCH': PinchIcon,
};

// Gesture guide (6 core gestures + PINCH)
const GESTURE_GUIDE = [
  { gesture: GestureType.THUMB_UP, action: 'Zoom In', description: 'Thumb up' },
  { gesture: GestureType.THUMB_DOWN, action: 'Zoom Out', description: 'Thumb down' },
  { gesture: GestureType.CLOSED_FIST, action: 'Pan', description: 'Fist drag' },
  { gesture: GestureType.OPEN_PALM, action: 'Reset', description: 'Open palm' },
  { gesture: GestureType.VICTORY, action: 'Select', description: 'V sign' },
  { gesture: GestureType.POINTING_UP, action: 'Point Select', description: 'Point to select' },
  { gesture: 'PINCH', action: 'Zoom', description: 'Two hands pinch' },
];

/**
 * Gesture control component
 * Displays camera feed and gesture recognition status
 */
const GestureControl = forwardRef(({ 
  enabled = false, 
  onGesture,
  onTwoHands,
  onPointingDirection,
  theme = 'dark',
  showGuide = true,
  compact = false,
}, ref) => {
  const videoRef = useRef(null);
  const [status, setStatus] = useState({ status: 'idle', message: 'Not started' });
  const [currentGesture, setCurrentGesture] = useState(null);
  const [currentAction, setCurrentAction] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isInCooldown, setIsInCooldown] = useState(false);
  
  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    getStatus: () => gestureService.getStatus(),
    getCurrentGesture: () => currentGesture,
  }), [currentGesture]);

  // Initialize gesture service callbacks
  useEffect(() => {
    gestureService.onStatusChange((newStatus) => {
      setStatus(newStatus);
    });
    
    gestureService.onGesture((gestureData) => {
      setCurrentGesture(gestureData.gesture);
      setCurrentAction(gestureData.action);
      
      // Check if gesture service is in cooldown
      const serviceStatus = gestureService.getStatus();
      setIsInCooldown(serviceStatus.isInCooldown || false);
      
      if (onGesture) {
        onGesture(gestureData);
      }
    });
    
    gestureService.onTwoHands((twoHandsData) => {
      if (onTwoHands) {
        onTwoHands(twoHandsData);
      }
    });
    
    gestureService.onPointingDirection((pointingData) => {
      if (onPointingDirection) {
        onPointingDirection(pointingData);
      }
    });
    
    return () => {
      gestureService.onStatusChange(null);
      gestureService.onGesture(null);
      gestureService.onTwoHands(null);
      gestureService.onPointingDirection(null);
    };
  }, [onGesture, onTwoHands, onPointingDirection]);

  // Start gesture control
  const startGestureControl = useCallback(async () => {
    if (!videoRef.current) return;
    
    setStatus({ status: 'loading', message: 'Loading model...' });
    
    const success = await gestureService.start(videoRef.current);
    
    if (success) {
      setStatus({ status: 'running', message: 'Gesture control active' });
    }
  }, []);

  // Stop gesture control
  const stopGestureControl = useCallback(() => {
    gestureService.stop();
    setCurrentGesture(null);
    setCurrentAction(null);
    setStatus({ status: 'stopped', message: 'Gesture control stopped' });
  }, []);

  // Start/stop gesture recognition
  useEffect(() => {
    if (enabled) {
      startGestureControl();
    } else {
      stopGestureControl();
    }
    
    return () => {
      stopGestureControl();
    };
  }, [enabled, startGestureControl, stopGestureControl]);

  // Get gesture icon component
  const getGestureIcon = (gesture) => {
    const IconComponent = GESTURE_ICONS[gesture];
    if (IconComponent) {
      return <IconComponent />;
    }
    // Default icon
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    );
  };

  // Get action description
  const getActionDescription = (action) => {
    switch (action) {
      case GestureAction.ZOOM_IN: return 'Zooming in...';
      case GestureAction.ZOOM_OUT: return 'Zooming out...';
      case GestureAction.PAN: return 'Panning...';
      case GestureAction.RESET: return 'Reset view';
      case GestureAction.SELECT: return 'Selecting...';
      case GestureAction.ROTATE: return 'Rotate mode';
      default: return '';
    }
  };

  // Status indicator color
  const getStatusColor = () => {
    switch (status.status) {
      case 'running': return '#4ade80';
      case 'loading': return '#facc15';
      case 'error': return '#f87171';
      default: return '#6b7280';
    }
  };

  if (!enabled) return null;

  return (
    <div className={`gesture-control ${theme} ${compact ? 'compact' : ''} ${isExpanded ? 'expanded' : ''}`}>
      {/* Video preview */}
      <div className="gesture-video-container">
        <video
          ref={videoRef}
          className="gesture-video"
          autoPlay
          playsInline
          muted
        />
        
        {/* Status indicator */}
        <div className="gesture-status-indicator">
          <span 
            className="status-dot" 
            style={{ backgroundColor: getStatusColor() }}
          />
          <span className="status-message">{status.message}</span>
        </div>
        
        {/* Current gesture display */}
        {currentGesture && currentGesture !== GestureType.NONE && (
          <div className={`current-gesture-display ${isInCooldown ? 'cooldown' : ''}`}>
            <span className="gesture-icon">{getGestureIcon(currentGesture)}</span>
            <span className="gesture-action">{getActionDescription(currentAction)}</span>
            {isInCooldown && <span className="cooldown-indicator">...</span>}
          </div>
        )}
        
        {/* Expand/collapse button */}
        <button 
          className="gesture-expand-btn"
          onClick={() => setIsExpanded(!isExpanded)}
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {isExpanded ? (
              <path d="M18 15l-6-6-6 6" />
            ) : (
              <path d="M6 9l6 6 6-6" />
            )}
          </svg>
        </button>
      </div>
      
      {/* Gesture guide */}
      {showGuide && isExpanded && (
        <div className="gesture-guide">
          <div className="gesture-guide-title">Gesture Guide</div>
          <div className="gesture-guide-list">
            {GESTURE_GUIDE.map((item) => (
              <div 
                key={item.gesture} 
                className={`gesture-guide-item ${currentGesture === item.gesture ? 'active' : ''}`}
              >
                <span className="guide-icon">{getGestureIcon(item.gesture)}</span>
                <div className="guide-info">
                  <span className="guide-action">{item.action}</span>
                  <span className="guide-desc">{item.description}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

GestureControl.displayName = 'GestureControl';

export default GestureControl;