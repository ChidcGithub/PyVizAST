import React, { useRef, useEffect, forwardRef, useImperativeHandle, useCallback, useMemo, useState } from 'react';
import Editor from '@monaco-editor/react';
import { useResizeObserver } from '../hooks/useResizeObserver';

// Performance thresholds
const LARGE_FILE_LINES = 2000;
const VERY_LARGE_FILE_LINES = 5000;

// Minimalist Monochrome Theme Definitions
const monochromeDarkTheme = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'comment', foreground: '505050', fontStyle: 'italic' },
    { token: 'keyword', foreground: 'e0e0e0', fontStyle: 'bold' },
    { token: 'string', foreground: 'a0a0a0' },
    { token: 'number', foreground: 'b0b0b0' },
    { token: 'type', foreground: 'd0d0d0' },
    { token: 'function', foreground: 'ffffff' },
    { token: 'variable', foreground: 'c0c0c0' },
    { token: 'operator', foreground: '909090' },
    { token: 'delimiter', foreground: '707070' },
  ],
  colors: {
    'editor.background': '#0a0a0a',
    'editor.foreground': '#d0d0d0',
    'editor.lineHighlightBackground': '#141414',
    'editorLineNumber.foreground': '#303030',
    'editorLineNumber.activeForeground': '#606060',
    'editor.selectionBackground': '#ffffff20',
    'editor.inactiveSelectionBackground': '#ffffff10',
    'editorCursor.foreground': '#ffffff',
    'editorIndentGuide.background': '#1a1a1a',
    'editorIndentGuide.activeBackground': '#252525',
    'editorWhitespace.foreground': '#1a1a1a',
    'editorBracketMatch.background': '#ffffff15',
    'editorBracketMatch.border': '#ffffff30',
  }
};

const monochromeLightTheme = {
  base: 'vs',
  inherit: true,
  rules: [
    { token: 'comment', foreground: 'a0a0a0', fontStyle: 'italic' },
    { token: 'keyword', foreground: '202020', fontStyle: 'bold' },
    { token: 'string', foreground: '606060' },
    { token: 'number', foreground: '505050' },
    { token: 'type', foreground: '303030' },
    { token: 'function', foreground: '000000' },
    { token: 'variable', foreground: '404040' },
  ],
  colors: {
    'editor.background': '#ffffff',
    'editor.foreground': '#1a1a1a',
    'editor.lineHighlightBackground': '#f5f5f5',
    'editorLineNumber.foreground': '#d0d0d0',
    'editorLineNumber.activeForeground': '#808080',
    'editor.selectionBackground': '#00000015',
    'editorCursor.foreground': '#000000',
  }
};

const CodeEditor = forwardRef(function CodeEditor({ code, onChange, theme, readOnly = false }, ref) {
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const containerRef = useRef(null);
  
  // Performance state for large files
  const [performanceMode, setPerformanceMode] = useState('normal'); // 'normal', 'large', 'very-large'
  const [showPerformanceWarning, setShowPerformanceWarning] = useState(false);
  // Monaco loading state
  const [loadError, setLoadError] = useState(null);

  // Calculate file size and set performance mode
  const lineCount = useMemo(() => {
    return code ? code.split('\n').length : 0;
  }, [code]);
  
  // Update performance mode based on file size
  useEffect(() => {
    if (lineCount > VERY_LARGE_FILE_LINES) {
      setPerformanceMode('very-large');
      setShowPerformanceWarning(true);
    } else if (lineCount > LARGE_FILE_LINES) {
      setPerformanceMode('large');
      setShowPerformanceWarning(true);
    } else {
      setPerformanceMode('normal');
      setShowPerformanceWarning(false);
    }
  }, [lineCount]);

  // Use our ResizeObserver to trigger layout updates
  // This avoids conflicts between Monaco's internal ResizeObserver and other ResizeObservers
  // Note: Only call layout after the editor is mounted
  useResizeObserver(containerRef, () => {
    if (editorRef.current && monacoRef.current) {
      try {
        editorRef.current.layout();
      } catch (e) {
        // Ignore layout errors
      }
    }
  }, { debounce: 50, immediate: false });

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    /**
     * Jump to specified line and highlight
     * @param {number} lineNumber - Line number (1-based)
     * @param {number} [column] - Optional column number
     * @param {number} [endLine] - Optional end line number (for multi-line selection)
     */
    goToLine: (lineNumber, column = 1, endLine = null) => {
      if (!editorRef.current) return;
      
      const editor = editorRef.current;
      const model = editor.getModel();
      if (!model) return;
      
      // Ensure line number is within valid range
      const lineCount = model.getLineCount();
      const targetLine = Math.max(1, Math.min(lineNumber, lineCount));
      
      // Set selection
      if (endLine && endLine > targetLine) {
        const endLineNumber = Math.min(endLine, lineCount);
        editor.setSelection({
          startLineNumber: targetLine,
          startColumn: 1,
          endLineNumber: endLineNumber,
          endColumn: model.getLineContent(endLineNumber).length + 1
        });
      } else {
        // Select entire line
        editor.setSelection({
          startLineNumber: targetLine,
          startColumn: 1,
          endLineNumber: targetLine,
          endColumn: model.getLineContent(targetLine).length + 1
        });
      }
      
      // Scroll to the line and center it
      editor.revealLineInCenter(targetLine);
      
      // Focus the editor
      editor.focus();
    },
    
    /**
     * Highlight specified line range (add decoration)
     * @param {number} startLine - Start line
     * @param {number} endLine - End line
     * @returns {string} Decoration ID for later removal
     */
    highlightLines: (startLine, endLine) => {
      if (!editorRef.current || !monacoRef.current) return null;
      
      const editor = editorRef.current;
      const monaco = monacoRef.current;
      const model = editor.getModel();
      if (!model) return null;
      
      const lineCount = model.getLineCount();
      const start = Math.max(1, Math.min(startLine, lineCount));
      const end = Math.max(start, Math.min(endLine, lineCount));
      
      // Add line highlight decoration
      const decorationIds = editor.deltaDecorations([], [
        {
          range: new monaco.Range(start, 1, end, model.getLineContent(end).length + 1),
          options: {
            isWholeLine: true,
            className: 'highlighted-line',
            glyphMarginClassName: 'highlighted-line-glyph',
          }
        }
      ]);
      
      return decorationIds[0];
    },
    
    /**
     * Clear highlight decoration
     * @param {string} decorationId - Decoration ID
     */
    clearHighlight: (decorationId) => {
      if (!editorRef.current || !decorationId) return;
      editorRef.current.deltaDecorations([decorationId], []);
    },
    
    /**
     * Get editor instance
     */
    getEditor: () => editorRef.current
  }));

  // Format code function
  const handleFormatCode = useCallback(() => {
    if (!editorRef.current || !monacoRef.current) return;
    
    const editor = editorRef.current;
    const model = editor.getModel();
    if (!model) return;
    
    // Use Monaco's built-in format action
    editor.getAction('editor.action.formatDocument').run();
  }, []);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    
    // Define custom themes
    monaco.editor.defineTheme('monochrome-dark', monochromeDarkTheme);
    monaco.editor.defineTheme('monochrome-light', monochromeLightTheme);
    
    // Set initial theme
    monaco.editor.setTheme(theme === 'dark' ? 'monochrome-dark' : 'monochrome-light');
    
    // Trigger layout on first mount to ensure editor renders correctly
    // Use setTimeout to ensure DOM is fully updated
    setTimeout(() => {
      if (editorRef.current && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          editorRef.current.layout({
            width: rect.width,
            height: rect.height
          });
        }
      }
    }, 0);
  };

  const handleEditorChange = (value) => {
    if (onChange) {
      onChange(value || '');
    }
  };

  // Update theme when prop changes
  useEffect(() => {
    if (monacoRef.current) {
      monacoRef.current.editor.setTheme(theme === 'dark' ? 'monochrome-dark' : 'monochrome-light');
    }
  }, [theme]);

  return (
    <div className="code-editor">
      <div className="editor-header">
        <div className="file-tabs">
          <div className="file-tab active">
            <span className="file-icon">PY</span>
            <span>main.py</span>
            {lineCount > LARGE_FILE_LINES && (
              <span className="file-size-indicator" title={`${lineCount} lines`}>
                {lineCount > VERY_LARGE_FILE_LINES ? '⚠️' : '📄'}
              </span>
            )}
          </div>
        </div>
        <div className="editor-actions">
          <button className="btn btn-ghost" title="Format code" onClick={handleFormatCode}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10H3M21 6H3M21 14H3M21 18H3" />
            </svg>
          </button>
          <button className="btn btn-ghost" title="Clear" onClick={() => onChange('')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </div>
      
      {/* Performance warning banner */}
      {showPerformanceWarning && (
        <div className="performance-warning">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span>
            Large file ({lineCount.toLocaleString()} lines). 
            {performanceMode === 'very-large' 
              ? ' Some features disabled for performance.' 
              : ' Performance mode enabled.'}
          </span>
          <button className="warning-dismiss" onClick={() => setShowPerformanceWarning(false)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}
      
      <div className="editor-container" ref={containerRef}>
        {loadError ? (
          <div className="editor-error-fallback">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <h4>Editor Failed to Load</h4>
            <p>{loadError}</p>
            <textarea
              className="fallback-textarea"
              value={code}
              onChange={(e) => onChange(e.target.value)}
              readOnly={readOnly}
              placeholder="Python code..."
              spellCheck={false}
            />
          </div>
        ) : (
          <Editor
            height="100%"
            language="python"
            value={code}
            onChange={handleEditorChange}
            onMount={handleEditorDidMount}
            theme="vs-dark"
            loading={
              <div className="editor-loading">
                <span>Loading editor...</span>
              </div>
            }
            onError={(error) => {
              console.error('Monaco Editor error:', error);
              setLoadError(error.message || 'Failed to load code editor');
            }}
            options={{
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace",
            lineHeight: 22,
            padding: { top: 16, bottom: 16 },
            minimap: { enabled: performanceMode === 'normal' }, // Disable minimap for large files
            scrollBeyondLastLine: false,
            automaticLayout: false, // Disable built-in ResizeObserver, use our own
            tabSize: 4,
            wordWrap: 'on',
            renderLineHighlight: performanceMode === 'normal' ? 'all' : 'line', // Simplified for large files
            cursorBlinking: 'smooth',
            smoothScrolling: performanceMode !== 'very-large', // Disable for very large files
            folding: performanceMode !== 'very-large', // Disable folding for very large files
            foldingHighlight: performanceMode === 'normal',
            bracketPairColorization: { enabled: performanceMode === 'normal' }, // Disable for large files
            guides: {
              bracketPairs: performanceMode === 'normal',
              indentation: performanceMode !== 'very-large',
            },
            scrollbar: {
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8,
              // Performance optimizations for large files
              verticalHasArrows: false,
              horizontalHasArrows: false,
            },
            overviewRulerLanes: performanceMode === 'normal' ? 3 : 0,
            hideCursorInOverviewRuler: performanceMode !== 'normal',
            overviewRulerBorder: false,
            readOnly: readOnly, // Support read-only mode from parent component
            domReadOnly: readOnly, // Also set DOM-level readonly for accessibility
            // Additional performance options for large files
            quickSuggestions: performanceMode !== 'very-large',
            suggestOnTriggerCharacters: performanceMode !== 'very-large',
            parameterHints: { enabled: performanceMode === 'normal' },
            lightbulb: { enabled: performanceMode === 'normal' },
            occurrencesHighlight: performanceMode === 'normal' ? 'singleFile' : 'off',
            selectionHighlight: performanceMode !== 'very-large',
            renderWhitespace: performanceMode === 'normal' ? 'selection' : 'none',
          }}
        />
        )}
      </div>
    </div>
  );
});

export default CodeEditor;