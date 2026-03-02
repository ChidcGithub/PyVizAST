import React, { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import Editor from '@monaco-editor/react';

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

const CodeEditor = forwardRef(function CodeEditor({ code, onChange, theme }, ref) {
  const editorRef = useRef(null);
  const monacoRef = useRef(null);

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    /**
     * 跳转到指定行并高亮
     * @param {number} lineNumber - 行号（从1开始）
     * @param {number} [column] - 可选的列号
     * @param {number} [endLine] - 可选的结束行号（用于选中多行）
     */
    goToLine: (lineNumber, column = 1, endLine = null) => {
      if (!editorRef.current) return;
      
      const editor = editorRef.current;
      const model = editor.getModel();
      if (!model) return;
      
      // 确保行号在有效范围内
      const lineCount = model.getLineCount();
      const targetLine = Math.max(1, Math.min(lineNumber, lineCount));
      const targetColumn = Math.max(1, column);
      
      // 设置选区
      if (endLine && endLine > targetLine) {
        const endLineNumber = Math.min(endLine, lineCount);
        editor.setSelection({
          startLineNumber: targetLine,
          startColumn: 1,
          endLineNumber: endLineNumber,
          endColumn: model.getLineContent(endLineNumber).length + 1
        });
      } else {
        // 选中整行
        editor.setSelection({
          startLineNumber: targetLine,
          startColumn: 1,
          endLineNumber: targetLine,
          endColumn: model.getLineContent(targetLine).length + 1
        });
      }
      
      // 滚动到该行并居中显示
      editor.revealLineInCenter(targetLine);
      
      // 聚焦编辑器
      editor.focus();
    },
    
    /**
     * 高亮指定行范围（添加装饰）
     * @param {number} startLine - 起始行
     * @param {number} endLine - 结束行
     * @returns {string} 装饰ID，用于后续清除
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
      
      // 添加行高亮装饰
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
     * 清除高亮装饰
     * @param {string} decorationId - 装饰ID
     */
    clearHighlight: (decorationId) => {
      if (!editorRef.current || !decorationId) return;
      editorRef.current.deltaDecorations([decorationId], []);
    },
    
    /**
     * 获取编辑器实例
     */
    getEditor: () => editorRef.current
  }));

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    
    // Define custom themes
    monaco.editor.defineTheme('monochrome-dark', monochromeDarkTheme);
    monaco.editor.defineTheme('monochrome-light', monochromeLightTheme);
    
    // Set initial theme
    monaco.editor.setTheme(theme === 'dark' ? 'monochrome-dark' : 'monochrome-light');
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
          </div>
        </div>
        <div className="editor-actions">
          <button className="btn btn-ghost" title="格式化代码">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10H3M21 6H3M21 14H3M21 18H3" />
            </svg>
          </button>
          <button className="btn btn-ghost" title="清空" onClick={() => onChange('')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </div>
      <div className="editor-container">
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
          options={{
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            lineHeight: 22,
            padding: { top: 16, bottom: 16 },
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            renderLineHighlight: 'all',
            cursorBlinking: 'smooth',
            smoothScrolling: true,
            folding: true,
            foldingHighlight: true,
            bracketPairColorization: { enabled: false },
            guides: {
              bracketPairs: false,
              indentation: true,
            },
            scrollbar: {
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8,
            },
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            overviewRulerBorder: false,
          }}
        />
      </div>
    </div>
  );
});

export default CodeEditor;
