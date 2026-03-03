import { useEffect, useRef, useCallback, useState } from 'react';

/**
 * 安全的 ResizeObserver Hook
 * 自动处理 ResizeObserver 的常见问题，包括：
 * 1. 循环通知错误
 * 2. 组件卸载时的清理
 * 3. 防抖处理
 * 
 * @param {React.RefObject} elementRef - 要观察的元素 ref
 * @param {Function} callback - resize 回调函数
 * @param {Object} options - 配置选项
 * @param {number} options.debounce - 防抖延迟（毫秒），默认 100
 * @param {boolean} options.immediate - 是否立即执行一次回调
 */
export function useResizeObserver(elementRef, callback, options = {}) {
  const { debounce = 100, immediate = false } = options;
  const observerRef = useRef(null);
  const timeoutRef = useRef(null);
  const callbackRef = useRef(callback);
  const rafRef = useRef(null);

  // 更新回调引用
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // 清理函数
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
        // 忽略 disconnect 错误
      }
      observerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    // 清理之前的 observer
    cleanup();

    // 创建 ResizeObserver
    const handleResize = (entries) => {
      // 取消之前的 RAF
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }

      // 使用 RAF 确保在浏览器绘制后执行
      rafRef.current = requestAnimationFrame(() => {
        // 清除之前的防抖计时器
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        // 防抖处理
        timeoutRef.current = setTimeout(() => {
          try {
            if (callbackRef.current && observerRef.current) {
              callbackRef.current(entries);
            }
          } catch (e) {
            // 忽略回调中的错误，避免触发 ResizeObserver 循环
            if (process.env.NODE_ENV === 'development') {
              console.debug('ResizeObserver callback error (suppressed):', e);
            }
          }
        }, debounce);
      });
    };

    try {
      observerRef.current = new ResizeObserver(handleResize);
      observerRef.current.observe(element);

      // 立即执行一次
      if (immediate) {
        const rect = element.getBoundingClientRect();
        callbackRef.current([{
          target: element,
          contentRect: rect,
          borderBoxSize: [{ inlineSize: rect.width, blockSize: rect.height }],
          contentBoxSize: [{ inlineSize: rect.width, blockSize: rect.height }],
        }]);
      }
    } catch (e) {
      if (process.env.NODE_ENV === 'development') {
        console.debug('ResizeObserver creation error:', e);
      }
    }

    return cleanup;
  }, [elementRef, debounce, immediate, cleanup]);

  return observerRef;
}

/**
 * 获取元素尺寸的 Hook
 * 基于 useResizeObserver 的简化版本
 * 
 * @param {React.RefObject} elementRef - 要观察的元素 ref
 * @returns {Object} 包含 width, height 的尺寸对象
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
