import { useEffect, useRef, useCallback, useState } from 'react';

/**
 * Safe ResizeObserver Hook
 * Automatically handles common ResizeObserver issues, including:
 * 1. Circular notification errors
 * 2. Cleanup on component unmount
 * 3. Debounce handling
 * 
 * @param {React.RefObject} elementRef - Element ref to observe
 * @param {Function} callback - Resize callback function
 * @param {Object} options - Configuration options
 * @param {number} options.debounce - Debounce delay (milliseconds), default 100
 * @param {boolean} options.immediate - Whether to execute callback immediately
 */
export function useResizeObserver(elementRef, callback, options = {}) {
  const { debounce = 100, immediate = false } = options;
  const observerRef = useRef(null);
  const timeoutRef = useRef(null);
  const callbackRef = useRef(callback);
  const rafRef = useRef(null);

  // Update callback reference
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (observerRef.current) {
      try {
        observerRef.current.disconnect();
      } catch (e) {
        // Ignore disconnect errors
      }
      observerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    // Cleanup previous observer
    cleanup();

    // Create ResizeObserver
    const handleResize = (entries) => {
      // Cancel previous RAF
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }

      // Use RAF to ensure execution after browser paint
      rafRef.current = requestAnimationFrame(() => {
        // Clear previous debounce timer
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        // Debounce handling
        timeoutRef.current = setTimeout(() => {
          try {
            if (callbackRef.current && observerRef.current) {
              callbackRef.current(entries);
            }
          } catch (e) {
            // Ignore errors in callback to avoid triggering ResizeObserver loop
            // but log them for debugging purposes
            if (process.env.NODE_ENV === 'development') {
              // Use console.warn for visibility in development without breaking the app
              console.warn('ResizeObserver callback error (suppressed):', e.message || e);
            }
          }
        }, debounce);
      });
    };

    try {
      observerRef.current = new ResizeObserver(handleResize);
      observerRef.current.observe(element);

      // Execute immediately once
      if (immediate) {
        const rect = element.getBoundingClientRect();
        try {
          callbackRef.current([{
            target: element,
            contentRect: rect,
            borderBoxSize: [{ inlineSize: rect.width, blockSize: rect.height }],
            contentBoxSize: [{ inlineSize: rect.width, blockSize: rect.height }],
          }]);
        } catch (e) {
          // Ignore errors in immediate callback
          if (process.env.NODE_ENV === 'development') {
            console.warn('ResizeObserver immediate callback error (suppressed):', e.message || e);
          }
        }
      }
    } catch (e) {
      // Log creation errors for debugging
      if (process.env.NODE_ENV === 'development') {
        console.warn('ResizeObserver creation error:', e.message || e);
      }
    }

    return cleanup;
  }, [elementRef, debounce, immediate, cleanup]);

  return observerRef;
}

/**
 * Hook to get element dimensions
 * Simplified version based on useResizeObserver
 * 
 * @param {React.RefObject} elementRef - Element ref to observe
 * @returns {Object} Size object containing width and height
 */
export function useElementSize(elementRef) {
  const [size, setSize] = useState({ width: 0, height: 0 });

  useResizeObserver(elementRef, (entries) => {
    if (entries[0]) {
      const { width, height } = entries[0].contentRect;
      setSize({ width, height });
    }
  });

  return size;
}