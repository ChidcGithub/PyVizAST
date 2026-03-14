/**
 * GestureService - Hand gesture recognition service
 * Real-time gesture detection using MediaPipe Gesture Recognizer
 * 
 * Supported gestures (6 gestures):
 * - Thumb_Up: Zoom in
 * - Thumb_Down: Zoom out
 * - Closed_Fist: Pan mode
 * - Open_Palm: Reset view
 * - Victory: Select node (V sign)
 * - Pointing_Up: Point to select (tracks pointing direction)
 * 
 * Stability improvements:
 * - A. Stability filter: Requires N consecutive frames with same gesture
 * - B. Confidence threshold: Raised to 0.7
 * - C. Cooldown period: Prevents rapid gesture switching
 */

import { FilesetResolver, GestureRecognizer } from '@mediapipe/tasks-vision';
import logger from './logger';

// Gesture types
export const GestureType = {
  NONE: 'None',
  CLOSED_FIST: 'Closed_Fist',
  OPEN_PALM: 'Open_Palm',
  THUMB_DOWN: 'Thumb_Down',
  THUMB_UP: 'Thumb_Up',
  VICTORY: 'Victory',
  POINTING_UP: 'Pointing_Up',
};

// Gesture action types
export const GestureAction = {
  NONE: 'none',
  ZOOM_IN: 'zoom_in',
  ZOOM_OUT: 'zoom_out',
  PAN: 'pan',
  RESET: 'reset',
  SELECT: 'select',
  PINCH: 'pinch',
};

/**
 * Gesture stability configuration
 * These values can be adjusted to fine-tune gesture recognition behavior
 */
export const GestureConfig = {
  // A. Stability filter: Number of consecutive frames with same gesture required
  STABLE_FRAMES_REQUIRED: 5,
  // B. Confidence threshold: Minimum confidence for gesture acceptance
  CONFIDENCE_THRESHOLD: 0.7,
  // C. Cooldown period: Milliseconds between gesture changes
  COOLDOWN_MS: 300,
  // Smoothing factor for hand position (0-1, higher = smoother but more lag)
  SMOOTHING_FACTOR: 0.3,
  // Pinch zoom sensitivity multiplier
  PINCH_SENSITIVITY: 5,
  // Pan sensitivity multiplier (converts normalized coordinates to pixels)
  PAN_SENSITIVITY: 500,
};

class GestureService {
  constructor() {
    this.gestureRecognizer = null;
    this.videoElement = null;
    this.isInitialized = false;
    this.isRunning = false;
    this.animationFrameId = null;
    this.lastVideoTime = -1;
    
    // Callbacks
    this.onGestureCallback = null;
    this.onHandPositionCallback = null;
    this.onTwoHandsCallback = null;
    this.onStatusChangeCallback = null;
    this.onPointingDirectionCallback = null;
    
    // State tracking
    this.currentGesture = GestureType.NONE;
    this.lastStableGesture = GestureType.NONE;
    this.gestureStartTime = 0;
    this.gestureHoldTime = 0;
    
    // Pointing direction tracking
    this.currentPointingDirection = null;
    this.pointingOrigin = null;
    
    // A. Gesture stability - history buffer
    this.gestureHistory = [];
    this.maxHistoryLength = GestureConfig.STABLE_FRAMES_REQUIRED;
    
    // C. Gesture cooldown
    this.lastGestureChangeTime = 0;
    this.isInCooldown = false;
    
    // Two hands tracking (for pinch zoom)
    this.previousHandDistance = null;
    this.previousHandCenter = null;
    
    // Hand positions
    this.handPositions = {
      left: null,
      right: null,
    };
    
    // Smoothing
    this.smoothingFactor = GestureConfig.SMOOTHING_FACTOR;
    this.smoothedPosition = null;
  }

  /**
   * Initialize gesture recognizer
   */
  async initialize() {
    if (this.isInitialized) return true;
    
    try {
      this.notifyStatus('loading', 'Loading gesture recognition model...');
      
      // Create Vision FilesetResolver
      const vision = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
      );
      
      // Create GestureRecognizer with higher confidence thresholds
      // Note: GPU delegate is preferred, but some ops may fall back to CPU (XNNPACK)
      this.gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: 'https://storage.googleapis.com/mediapipe-tasks/gesture_recognizer/gesture_recognizer.task',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        numHands: 2,
        minHandDetectionConfidence: GestureConfig.CONFIDENCE_THRESHOLD,
        minHandPresenceConfidence: GestureConfig.CONFIDENCE_THRESHOLD,
        minTrackingConfidence: GestureConfig.CONFIDENCE_THRESHOLD,
      });
      
      this.isInitialized = true;
      // Note: MediaPipe may log warnings about CPU-only ops - this is normal behavior
      // The framework automatically uses XNNPACK (optimized CPU) for unsupported GPU ops
      logger.info('Gesture recognizer initialized', { 
        delegate: 'GPU (with CPU fallback for unsupported ops)',
        note: 'XNNPACK CPU acceleration is used for ops not supported on GPU'
      });
      this.notifyStatus('ready', 'Gesture recognition ready (GPU/CPU hybrid)');
      return true;
    } catch (error) {
      logger.error('Failed to initialize GestureRecognizer', { error: error.message, stack: error.stack });
      this.notifyStatus('error', `Failed to load: ${error.message}`);
      return false;
    }
  }

  /**
   * Start camera and gesture recognition
   */
  async start(videoElement) {
    if (!this.isInitialized) {
      const success = await this.initialize();
      if (!success) return false;
    }
    
    if (this.isRunning) return true;
    
    try {
      this.videoElement = videoElement;
      
      // Get camera stream
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
      });
      
      videoElement.srcObject = stream;
      await videoElement.play();
      
      // Wait for video to have valid dimensions before starting detection
      // This prevents MediaPipe "ROI width and height must be > 0" error
      let attempts = 0;
      const maxAttempts = 50; // 5 seconds max (50 * 100ms)
      while ((!videoElement.videoWidth || !videoElement.videoHeight) && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }
      
      if (!videoElement.videoWidth || !videoElement.videoHeight) {
        logger.error('Video element has no valid dimensions after waiting');
        this.notifyStatus('error', 'Camera failed to initialize properly');
        return false;
      }
      
      this.isRunning = true;
      this.lastVideoTime = -1;
      
      // Reset stability state
      this.gestureHistory = [];
      this.lastGestureChangeTime = 0;
      this.isInCooldown = false;
      
      // Start detection loop
      this.detectLoop();
      
      this.notifyStatus('running', 'Gesture control active');
      return true;
    } catch (error) {
      logger.error('Failed to start camera', { error: error.message });
      this.notifyStatus('error', `Camera error: ${error.message}`);
      return false;
    }
  }

  /**
   * Stop gesture recognition
   */
  stop() {
    this.isRunning = false;
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    if (this.videoElement && this.videoElement.srcObject) {
      const tracks = this.videoElement.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      this.videoElement.srcObject = null;
    }
    
    this.currentGesture = GestureType.NONE;
    this.lastStableGesture = GestureType.NONE;
    this.previousHandDistance = null;
    this.previousHandCenter = null;
    this.handPositions = { left: null, right: null };
    this.gestureHistory = [];
    this.smoothedPosition = null;
    this.isInCooldown = false;
    this.lastGestureChangeTime = 0;
    this.gestureStartTime = 0;
    this.gestureHoldTime = 0;
    
    this.notifyStatus('stopped', 'Gesture control stopped');
  }

  /**
   * Detection loop
   */
  detectLoop() {
    if (!this.isRunning || !this.videoElement || !this.gestureRecognizer) {
      return;
    }
    
    const video = this.videoElement;
    
    // Skip if video has no valid dimensions (prevents ROI width/height = 0 error)
    if (!video.videoWidth || !video.videoHeight) {
      this.animationFrameId = requestAnimationFrame(() => this.detectLoop());
      return;
    }
    
    // Process only when video frame updates
    if (video.currentTime !== this.lastVideoTime) {
      this.lastVideoTime = video.currentTime;
      
      try {
        const results = this.gestureRecognizer.recognizeForVideo(video, performance.now());
        this.processResults(results);
      } catch (error) {
        // Silently ignore ROI errors which can occur during video initialization
        if (!error.message?.includes('ROI')) {
          logger.error('Gesture recognition error', { error: error.message });
        }
      }
    }
    
    this.animationFrameId = requestAnimationFrame(() => this.detectLoop());
  }

  /**
   * Process recognition results
   */
  processResults(results) {
    const { gestures, landmarks, handedness } = results;
    
    // Reset hand positions
    this.handPositions = { left: null, right: null };
    
    // No hand detected - fast reset for responsiveness
    if (!gestures || gestures.length === 0) {
      // Fast reset: clear history immediately for quick response
      this.gestureHistory = [];
      this.currentGesture = GestureType.NONE;
      this.lastStableGesture = GestureType.NONE;
      this.previousHandDistance = null;
      this.previousHandCenter = null;
      this.smoothedPosition = null;
      this.isInCooldown = false;
      this.gestureHoldTime = 0;
      
      if (this.onGestureCallback) {
        this.onGestureCallback({
          gesture: GestureType.NONE,
          action: GestureAction.NONE,
          holdTime: 0,
        });
      }
      return;
    }
    
    // Process each hand
    for (let i = 0; i < gestures.length; i++) {
      const gesture = gestures[i][0]; // Get highest confidence gesture
      const handLandmarks = landmarks[i];
      const hand = handedness[i][0];
      
      if (!gesture || !handLandmarks || !hand) continue;
      
      // B. Check confidence threshold
      if (gesture.score < GestureConfig.CONFIDENCE_THRESHOLD) continue;
      
      // Get palm center position (using wrist and middle finger base)
      const wrist = handLandmarks[0];
      const middleMcp = handLandmarks[9];
      const palmCenter = {
        x: (wrist.x + middleMcp.x) / 2,
        y: (wrist.y + middleMcp.y) / 2,
        z: (wrist.z + middleMcp.z) / 2,
      };
      
      // Apply smoothing
      if (!this.smoothedPosition) {
        this.smoothedPosition = { ...palmCenter };
      } else {
        this.smoothedPosition.x += (palmCenter.x - this.smoothedPosition.x) * this.smoothingFactor;
        this.smoothedPosition.y += (palmCenter.y - this.smoothedPosition.y) * this.smoothingFactor;
        this.smoothedPosition.z += (palmCenter.z - this.smoothedPosition.z) * this.smoothingFactor;
      }
      
      // Record hand position
      const handLabel = hand.categoryName.toLowerCase(); // 'left' or 'right'
      
      // Calculate pointing direction (index finger: MCP=5, TIP=8)
      const indexMcp = handLandmarks[5];
      const indexTip = handLandmarks[8];
      const pointingDirection = {
        x: indexTip.x - indexMcp.x,
        y: indexTip.y - indexMcp.y,
        z: (indexTip.z - indexMcp.z) * 2, // Z is usually small, amplify
      };
      
      // Normalize pointing direction
      const length = Math.sqrt(
        pointingDirection.x * pointingDirection.x +
        pointingDirection.y * pointingDirection.y +
        pointingDirection.z * pointingDirection.z
      );
      if (length > 0.001) {
        pointingDirection.x /= length;
        pointingDirection.y /= length;
        pointingDirection.z /= length;
      }
      
      this.handPositions[handLabel] = {
        landmarks: handLandmarks,
        center: { ...this.smoothedPosition },
        gesture: gesture.categoryName,
        pointingDirection,
        indexTip: { x: indexTip.x, y: indexTip.y, z: indexTip.z },
      };
    }
    
    // Two hands gesture handling
    if (this.handPositions.left && this.handPositions.right) {
      this.handleTwoHands();
      return;
    }
    
    // Single hand gesture handling
    const activeHand = this.handPositions.left || this.handPositions.right;
    if (activeHand) {
      this.handleSingleHand(activeHand);
      
      // Call position callback
      if (this.onHandPositionCallback) {
        this.onHandPositionCallback(activeHand.center, activeHand.landmarks);
      }
    }
  }

  /**
   * A. Add gesture to history and return stable gesture
   */
  addToGestureHistory(gesture) {
    this.gestureHistory.push(gesture);
    
    // Keep only last N frames
    if (this.gestureHistory.length > this.maxHistoryLength) {
      this.gestureHistory.shift();
    }
    
    // Check if we have stable gesture (all N frames are the same)
    if (this.gestureHistory.length === this.maxHistoryLength) {
      const allSame = this.gestureHistory.every(g => g === gesture);
      if (allSame) {
        return gesture;
      }
    }
    
    return null; // Not stable yet
  }

  /**
   * Handle single hand gesture
   */
  handleSingleHand(handData) {
    const rawGesture = handData.gesture;
    const now = Date.now();
    
    // D. Simplify - only accept certain gestures
    const allowedGestures = [
      GestureType.THUMB_UP,
      GestureType.THUMB_DOWN,
      GestureType.CLOSED_FIST,
      GestureType.OPEN_PALM,
      GestureType.VICTORY,
      GestureType.POINTING_UP,
    ];
    
    // Filter out unsupported gestures
    const gestureName = allowedGestures.includes(rawGesture) ? rawGesture : GestureType.NONE;
    
    // A. Stability filter - add to history
    const stableGesture = this.addToGestureHistory(gestureName);
    
    // If no stable gesture, use NONE
    const effectiveGesture = stableGesture || GestureType.NONE;
    
    // Always send pointing direction if hand is detected with pointing gesture
    // This should be independent of stability filter and cooldown for smooth tracking
    if (rawGesture === GestureType.POINTING_UP && this.onPointingDirectionCallback) {
      this.onPointingDirectionCallback({
        origin: handData.indexTip,
        direction: handData.pointingDirection,
        gesture: rawGesture, // Use raw gesture for immediate feedback
        isStable: stableGesture !== null, // Indicate stability status
      });
    }
    
    // C. Check cooldown - still process position during cooldown
    if (this.isInCooldown) {
      const timeSinceLastChange = now - this.lastGestureChangeTime;
      if (timeSinceLastChange < GestureConfig.COOLDOWN_MS) {
        // Still in cooldown - keep current gesture but continue position tracking
        if (this.onHandPositionCallback) {
          this.onHandPositionCallback(handData.center, handData.landmarks);
        }
        // Don't return early - still update gesture callback for other actions
        // But skip the gesture action processing below
        this.currentGesture = this.lastStableGesture;
        return;
      }
      this.isInCooldown = false;
    }
    
    // Gesture change detection
    if (effectiveGesture !== this.lastStableGesture) {
      // C. Start cooldown on gesture change
      this.lastGestureChangeTime = now;
      this.isInCooldown = true;
      this.lastStableGesture = effectiveGesture;
      this.gestureStartTime = now;
      this.gestureHoldTime = 0;
    } else if (effectiveGesture !== GestureType.NONE) {
      this.gestureHoldTime = now - this.gestureStartTime;
    }
    
    this.currentGesture = effectiveGesture;
    
    // Map gesture to action
    const action = this.gestureToAction(effectiveGesture, this.gestureHoldTime);
    
    // Check if raw gesture is Pointing_Up (for continuous pointing tracking)
    const isPointing = rawGesture === GestureType.POINTING_UP;
    
    if (this.onGestureCallback) {
      this.onGestureCallback({
        gesture: effectiveGesture,
        action,
        holdTime: this.gestureHoldTime,
        position: handData.center,
        confidence: stableGesture ? 1.0 : 0.5, // Indicate stability
        pointingDirection: handData.pointingDirection,
        indexTip: handData.indexTip,
        isPointing, // Add flag to indicate pointing state (independent of stability)
      });
    }
  }

  /**
   * Handle two hands gesture (zoom)
   */
  handleTwoHands() {
    const left = this.handPositions.left;
    const right = this.handPositions.right;
    
    if (!left || !right) return;
    
    // Calculate distance between hands
    const dx = right.center.x - left.center.x;
    const dy = right.center.y - left.center.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // Calculate center point
    const centerX = (left.center.x + right.center.x) / 2;
    const centerY = (left.center.y + right.center.y) / 2;
    const center = { x: centerX, y: centerY };
    
    // Calculate zoom and pan - default to zero
    let pinchScale = 0;
    let panDelta = { x: 0, y: 0 };
    
    if (this.previousHandDistance !== null && this.previousHandCenter !== null) {
      // Zoom - based on distance change
      const distanceDelta = distance - this.previousHandDistance;
      pinchScale = distanceDelta * GestureConfig.PINCH_SENSITIVITY;
      
      // Pan - based on center point movement
      panDelta = {
        x: (centerX - this.previousHandCenter.x) * GestureConfig.PAN_SENSITIVITY,
        y: (centerY - this.previousHandCenter.y) * GestureConfig.PAN_SENSITIVITY,
      };
    }
    
    // Update state
    this.previousHandDistance = distance;
    this.previousHandCenter = center;
    this.currentGesture = 'PINCH';
    
    // Call callbacks - variables are used here
    if (this.onTwoHandsCallback) {
      this.onTwoHandsCallback({
        pinchScale,
        panDelta,
        distance,
        center,
        leftGesture: left.gesture,
        rightGesture: right.gesture,
      });
    }
    
    if (this.onGestureCallback) {
      this.onGestureCallback({
        gesture: 'PINCH',
        action: pinchScale > 0.01 ? GestureAction.ZOOM_IN : 
                pinchScale < -0.01 ? GestureAction.ZOOM_OUT : 
                GestureAction.PAN,
        holdTime: 0,
        pinchScale,
        panDelta,
      });
    }
  }

  /**
   * Map gesture to action (6 gestures)
   */
  gestureToAction(gesture, holdTime) {
    switch (gesture) {
      case GestureType.THUMB_UP:
        return GestureAction.ZOOM_IN;
      
      case GestureType.THUMB_DOWN:
        return GestureAction.ZOOM_OUT;
      
      case GestureType.CLOSED_FIST:
        return GestureAction.PAN;
      
      case GestureType.OPEN_PALM:
        return GestureAction.RESET;
      
      case GestureType.VICTORY:
        return GestureAction.SELECT;
      
      case GestureType.POINTING_UP:
        return GestureAction.SELECT;
      
      default:
        return GestureAction.NONE;
    }
  }

  /**
   * Set callbacks
   */
  onGesture(callback) {
    this.onGestureCallback = callback;
  }

  onHandPosition(callback) {
    this.onHandPositionCallback = callback;
  }

  onTwoHands(callback) {
    this.onTwoHandsCallback = callback;
  }

  onStatusChange(callback) {
    this.onStatusChangeCallback = callback;
  }

  onPointingDirection(callback) {
    this.onPointingDirectionCallback = callback;
  }

  /**
   * Clear all callbacks - call this when component unmounts
   */
  clearCallbacks() {
    this.onGestureCallback = null;
    this.onHandPositionCallback = null;
    this.onTwoHandsCallback = null;
    this.onStatusChangeCallback = null;
    this.onPointingDirectionCallback = null;
  }

  /**
   * Notify status change
   */
  notifyStatus(status, message) {
    if (this.onStatusChangeCallback) {
      this.onStatusChangeCallback({ status, message });
    }
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      isInitialized: this.isInitialized,
      isRunning: this.isRunning,
      currentGesture: this.currentGesture,
      isInCooldown: this.isInCooldown,
    };
  }

  /**
   * Destroy
   */
  destroy() {
    this.stop();
    this.clearCallbacks();
    this.gestureRecognizer = null;
    this.isInitialized = false;
    this.videoElement = null;
    this.gestureHistory = [];
    this.handPositions = { left: null, right: null };
    this.smoothedPosition = null;
  }
}

// Export singleton
export const gestureService = new GestureService();
export default gestureService;
