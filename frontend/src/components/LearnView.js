import React, { useState, useCallback, useEffect } from 'react';
import CodeEditor from './CodeEditor';
import ASTVisualizer from './ASTVisualizer';
import { analyzeCode, explainNode, getLLMStatus } from '../api';
import logger from '../utils/logger';
import { useToast } from './ToastContext';

/**
 * Node type icons for visual representation
 */
const NODE_ICONS = {
  module: '📦',
  function: '⚡',
  class: '🏗️',
  if: '❓',
  for: '🔄',
  while: '🔁',
  try: '🛡️',
  with: '📥',
  call: '📞',
  binary_op: '➕',
  compare: '⚖️',
  lambda: 'λ',
  list: '📋',
  dict: '📖',
  set: '🎲',
  tuple: '📦',
  assign: '📝',
  name: '🏷️',
  import: '📦',
  return: '↩️',
  yield: '⏸️',
  other: '•'
};

/**
 * Sample code for learning
 */
const LEARN_SAMPLE_CODE = `# Python AST Learning Sample
# Explore different Python syntax structures

# 1. Import statement
import os
from typing import List, Optional

# 2. Global variable assignment
CONFIG = {"debug": True, "version": "1.0"}

# 3. Class definition
class Calculator:
    """A simple calculator class"""
    
    def __init__(self, name: str):
        self.name = name
        self.history = []
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers"""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

# 4. Function with various constructs
def process_items(items: List[int]) -> dict:
    """Process a list of items"""
    result = {"sum": 0, "evens": []}
    
    # For loop
    for item in items:
        result["sum"] += item
        # If-else
        if item % 2 == 0:
            result["evens"].append(item)
    
    # List comprehension
    squares = [x ** 2 for x in items if x > 0]
    
    # Try-except
    try:
        value = items[0] / len(items)
    except ZeroDivisionError:
        value = 0
    
    return result

# 5. Generator with yield
def fibonacci_generator(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# Main execution
if __name__ == "__main__":
    calc = Calculator("MyCalc")
    print(calc.add(5, 3))
`;

/**
 * LearnView Component - Interactive AST learning mode
 */
function LearnView({ theme }) {
  const [code, setCode] = useState(LEARN_SAMPLE_CODE);
  const [astGraph, setAstGraph] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [llmEnabled, setLlmEnabled] = useState(false);
  const [useLLM, setUseLLM] = useState(true);
  const toast = useToast();

  // Check LLM status on mount
  useEffect(() => {
    const checkLLM = async () => {
      try {
        const status = await getLLMStatus();
        setLlmEnabled(status.status === 'ready' && status.enabled);
      } catch (err) {
        logger.debug('LLM status check failed', { error: err.message });
      }
    };
    checkLLM();
  }, []);

  // Analyze code
  const handleAnalyze = useCallback(async () => {
    if (!code.trim()) {
      toast.error('Please enter Python code');
      return;
    }

    setAnalyzing(true);
    setSelectedNode(null);
    setExplanation(null);

    try {
      const result = await analyzeCode(code);
      setAstGraph(result.ast_graph);
      toast.success('AST visualization ready! Click nodes to learn more.');
    } catch (err) {
      toast.error(err.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }, [code, toast]);

  // Handle node click for explanation
  const handleNodeClick = useCallback(async (node) => {
    setSelectedNode(node);
    setLoading(true);

    try {
      const result = await explainNode(node.id, code, { use_llm: llmEnabled && useLLM });
      setExplanation(result);
    } catch (err) {
      toast.error('Failed to get explanation');
      logger.error('Failed to get node explanation', { nodeId: node.id, error: err.message });
    } finally {
      setLoading(false);
    }
  }, [code, toast, llmEnabled, useLLM]);

  // Handle code change
  const handleCodeChange = useCallback((newCode) => {
    setCode(newCode);
    setAstGraph(null);
    setSelectedNode(null);
    setExplanation(null);
  }, []);

  return (
    <div className={`learn-view ${theme}`}>
      {/* Header */}
      <div className="learn-header">
        <div className="learn-header-left">
          <h2>AST Learning Mode</h2>
          <p>Write Python code, visualize AST, and click nodes to learn</p>
        </div>
        <div className="learn-header-actions">
          {llmEnabled && (
            <label className="llm-toggle">
              <input
                type="checkbox"
                checked={useLLM}
                onChange={(e) => setUseLLM(e.target.checked)}
              />
              <span className="llm-toggle-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                LLM
              </span>
            </label>
          )}
          <button 
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={analyzing}
          >
            {analyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="learn-body">
        {/* Left Panel - Code Editor */}
        <div className="learn-left-panel">
          <div className="panel-header">
            <span className="panel-title">Code Editor</span>
          </div>
          <div className="learn-editor">
            <CodeEditor
              code={code}
              onChange={handleCodeChange}
              theme={theme}
            />
          </div>
        </div>

        {/* Right Panel - AST + Explanation */}
        <div className="learn-right-panel">
          {/* AST Visualization */}
          <div className="learn-ast-panel">
            <div className="panel-header">
              <span className="panel-title">AST Visualization</span>
              {astGraph && <span className="panel-hint">Click a node to explore</span>}
            </div>
            <div className="learn-visualization">
              {analyzing ? (
                <div className="learn-placeholder">
                  <div className="loader-spinner"></div>
                  <p>Analyzing...</p>
                </div>
              ) : astGraph ? (
                <ASTVisualizer
                  graph={astGraph}
                  theme={theme}
                  onNodeClick={handleNodeClick}
                />
              ) : (
                <div className="learn-placeholder">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <circle cx="10" cy="13" r="2" />
                    <circle cx="14" cy="17" r="2" />
                    <line x1="10" y1="15" x2="12" y2="16" />
                  </svg>
                  <p>Click "Analyze" to visualize AST</p>
                </div>
              )}
            </div>
          </div>

          {/* Node Explanation */}
          <div className="learn-explanation-panel">
            <div className="panel-header">
              <span className="panel-title">Node Explanation</span>
              {selectedNode && (
                <span className="node-badge">
                  {NODE_ICONS[selectedNode.type] || '•'} {selectedNode.type}
                  {selectedNode.name && ` : ${selectedNode.name}`}
                </span>
              )}
            </div>
            <div className="learn-explanation">
              {loading ? (
                <div className="learn-placeholder">
                  <div className="loader-spinner"></div>
                  <p>Loading...</p>
                </div>
              ) : explanation ? (
                <div className="explanation-content">
                  <div className="explanation-main">
                    <span className="explanation-icon">{NODE_ICONS[selectedNode?.type] || '•'}</span>
                    <div className="explanation-header">
                      <h3>{selectedNode?.type?.toUpperCase()}</h3>
                      <p>{explanation.explanation}</p>
                    </div>
                  </div>

                  {explanation.python_doc && (
                    <div className="explanation-block">
                      <h4>Documentation</h4>
                      <p>{explanation.python_doc}</p>
                    </div>
                  )}

                  {explanation.examples && explanation.examples.length > 0 && (
                    <div className="explanation-block">
                      <h4>Examples</h4>
                      <div className="examples-grid">
                        {explanation.examples.map((example, i) => (
                          <pre key={i} className="example-code">
                            <code>{example}</code>
                          </pre>
                        ))}
                      </div>
                    </div>
                  )}

                  {explanation.related_concepts && explanation.related_concepts.length > 0 && (
                    <div className="explanation-block">
                      <h4>Related</h4>
                      <div className="related-tags">
                        {explanation.related_concepts.map((concept, i) => (
                          <span key={i} className="related-tag">{concept}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="learn-placeholder small">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                  <p>Select a node to see explanation</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LearnView;