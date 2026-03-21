/**
 * LLMExplanationPanel - AI-powered node explanation component
 * Premium Black & White Design
 * 
 * Features:
 * - Automatic explanation generation when node is selected
 * - Elegant loading state with animated progress
 * - Error handling with retry capability
 * - Fullscreen modal for detailed view
 */

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { generateExplanation } from '../api';
import './LLMExplanationPanel.css';

// Status constants
const STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error'
};

/**
 * LLMExplanationPanel Component
 */
const LLMExplanationPanel = ({ llmConfig, selectedNode, fullCode }) => {
  // State
  const [status, setStatus] = useState(STATUS.IDLE);
  const [explanation, setExplanation] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [progress, setProgress] = useState(0);
  const [showModal, setShowModal] = useState(false);

  // Refs for request management
  const abortControllerRef = useRef(null);
  const lastFetchedKeyRef = useRef(null);

  // Check if LLM is available and enabled
  const isLLMAvailable = useMemo(() => {
    return llmConfig?.enabled && 
           llmConfig?.use_for_explanations && 
           llmConfig?.status === 'ready';
  }, [llmConfig?.enabled, llmConfig?.use_for_explanations, llmConfig?.status]);

  // Generate unique node key
  const nodeKey = useMemo(() => {
    if (!selectedNode) return null;
    return `${selectedNode.type}:${selectedNode.name || 'anonymous'}:${selectedNode.lineno || 0}`;
  }, [selectedNode]);

  // Effect: Fetch explanation when node changes
  useEffect(() => {
    // Reset if no node
    if (!nodeKey) {
      setStatus(STATUS.IDLE);
      setExplanation(null);
      return;
    }

    // Skip Module nodes
    if (selectedNode?.type === 'Module' || selectedNode?.type === 'module') {
      return;
    }

    // Skip if LLM not available
    if (!isLLMAvailable) {
      return;
    }

    // Skip if already fetched this node
    if (lastFetchedKeyRef.current === nodeKey && status === STATUS.SUCCESS) {
      return;
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Track this fetch
    lastFetchedKeyRef.current = nodeKey;

    // Start loading
    setStatus(STATUS.LOADING);
    setProgress(5);
    setErrorMessage('');

    // Build request data
    const requestData = {
      node_type: selectedNode.type,
      node_name: selectedNode.name || null,
      code_context: selectedNode.sourceCode || selectedNode.source_code || selectedNode.label || '',
      node_info: {
        name: selectedNode.name,
        description: selectedNode.description,
        label: selectedNode.label || selectedNode.detailed_label,
        lineno: selectedNode.lineno,
        end_lineno: selectedNode.end_lineno,
        docstring: selectedNode.docstring,
        attributes: selectedNode.attributes
      },
      full_code: fullCode || ''
    };

    // Make request
    generateExplanation(requestData, controller.signal)
      .then(result => {
        if (!controller.signal.aborted) {
          setExplanation(result);
          setStatus(STATUS.SUCCESS);
          setProgress(100);
        }
      })
      .catch(err => {
        // Ignore cancelled requests
        if (err.name === 'AbortError' || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
          return;
        }
        
        if (!controller.signal.aborted) {
          setErrorMessage(err.message || 'Failed to generate explanation');
          setStatus(STATUS.ERROR);
        }
      });

    // Cleanup
    return () => {
      controller.abort();
    };
  }, [nodeKey, isLLMAvailable]); // Only depend on stable values

  // Effect: Simulate progress during loading
  useEffect(() => {
    if (status !== STATUS.LOADING) {
      setProgress(0);
      return;
    }

    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 85) return prev;
        return prev + Math.random() * 8;
      });
    }, 500);

    return () => clearInterval(interval);
  }, [status]);

  // Retry handler
  const handleRetry = useCallback(() => {
    lastFetchedKeyRef.current = null; // Force refetch
    setStatus(STATUS.IDLE);
  }, []);

  // Determine unavailable reason for user feedback (must be before early returns)
  const unavailableReason = useMemo(() => {
    if (!llmConfig) return 'not_configured';
    if (!llmConfig.enabled) return 'disabled';
    if (!llmConfig.use_for_explanations) return 'explanations_disabled';
    if (llmConfig.status !== 'ready') return 'not_ready';
    return null;
  }, [llmConfig]);

  // Don't render for Module nodes
  if (selectedNode?.type === 'Module' || selectedNode?.type === 'module') {
    return null;
  }

  // Check if has content to display
  const hasContent = explanation && (
    explanation.explanation || 
    explanation.python_doc || 
    (explanation.examples && explanation.examples.length > 0) ||
    (explanation.related_concepts && explanation.related_concepts.length > 0)
  );

  return (
    <div className="llm-explanation-panel">
      {/* Unavailable State - Show prompt to enable LLM */}
      {unavailableReason && selectedNode && selectedNode.type !== 'Module' && selectedNode.type !== 'module' && (
        <div className="llm-unavailable-state">
          <div className="llm-unavailable-icon">
            <AIIcon size={18} />
          </div>
          <div className="llm-unavailable-content">
            <span className="llm-unavailable-title">AI Explanation</span>
            <span className="llm-unavailable-desc">
              {unavailableReason === 'not_configured' && 'Configure LLM in settings to enable AI explanations'}
              {unavailableReason === 'disabled' && 'Enable LLM in settings to get AI explanations'}
              {unavailableReason === 'explanations_disabled' && 'Enable explanations in LLM settings'}
              {unavailableReason === 'not_ready' && 'Start Ollama and load a model to use AI explanations'}
            </span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {status === STATUS.LOADING && (
        <div className="llm-loading-state">
          <div className="llm-loading-animation">
            <div className="llm-loading-ring">
              <svg viewBox="0 0 50 50">
                <circle className="llm-progress-bg" cx="25" cy="25" r="20" fill="none" strokeWidth="2" />
                <circle 
                  className="llm-progress-fill" 
                  cx="25" cy="25" r="20" 
                  fill="none" strokeWidth="2"
                  strokeDasharray={`${progress * 1.256} 125.6`}
                  transform="rotate(-90 25 25)"
                />
              </svg>
              <div className="llm-loading-icon">
                <AIIcon />
              </div>
            </div>
          </div>
          <div className="llm-loading-info">
            <span className="llm-loading-title">AI Generating</span>
            <span className="llm-loading-subtitle">
              <span className="llm-model-name">{llmConfig?.model || 'LLM'}</span>
              <LoadingDots />
            </span>
          </div>
          <div className="llm-progress-bar">
            <div className="llm-progress-fill-bar" style={{ width: `${Math.min(progress, 90)}%` }} />
          </div>
        </div>
      )}

      {/* Content Display */}
      {status === STATUS.SUCCESS && hasContent && (
        <div className="llm-content-section">
          <div className="llm-content-header">
            <div className="llm-content-title">
              <AIIcon size={14} />
              <span>AI Explanation</span>
              <span className="llm-badge">{llmConfig?.model || 'LLM'}</span>
            </div>
            <button className="llm-expand-btn" onClick={() => setShowModal(true)} title="View fullscreen">
              <ExpandIcon />
            </button>
          </div>
          
          {explanation.explanation && (
            <div className="llm-section">
              <p className="llm-explanation-text">{explanation.explanation}</p>
            </div>
          )}
          
          {explanation.related_concepts?.length > 0 && (
            <div className="llm-section llm-section-compact">
              <div className="llm-concepts-list">
                {explanation.related_concepts.slice(0, 6).map((concept, idx) => (
                  <span key={idx} className="llm-concept-tag">{concept}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error State */}
      {status === STATUS.ERROR && (
        <div className="llm-error-state">
          <div className="llm-error-icon">
            <ErrorIcon />
          </div>
          <div className="llm-error-content">
            <span className="llm-error-title">Generation Failed</span>
            <span className="llm-error-detail">{errorMessage}</span>
          </div>
          <button className="llm-retry-action-btn" onClick={handleRetry}>
            <RetryIcon />
            Retry
          </button>
        </div>
      )}

      {/* Fullscreen Modal */}
      {showModal && explanation && (
        <FullscreenModal 
          explanation={explanation} 
          selectedNode={selectedNode}
          modelName={llmConfig?.model}
          onClose={() => setShowModal(false)} 
        />
      )}
    </div>
  );
};

// ============== Sub-Components ==============

const AIIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
    <circle cx="7.5" cy="14.5" r="1.5"/>
    <circle cx="16.5" cy="14.5" r="1.5"/>
  </svg>
);

const ExpandIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="15 3 21 3 21 9"/>
    <polyline points="9 21 3 21 3 15"/>
    <line x1="21" y1="3" x2="14" y2="10"/>
    <line x1="3" y1="21" x2="10" y2="14"/>
  </svg>
);

const ErrorIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="8" x2="12" y2="12"/>
    <line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);

const RetryIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="23 4 23 10 17 10"/>
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
);

const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const LoadingDots = () => (
  <span className="llm-loading-dots">
    <span></span><span></span><span></span>
  </span>
);

const SectionIcon = ({ type }) => {
  const icons = {
    info: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 16v-4"/>
        <path d="M12 8h.01"/>
      </svg>
    ),
    doc: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
    ),
    code: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="16 18 22 12 16 6"/>
        <polyline points="8 6 2 12 8 18"/>
      </svg>
    ),
    star: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
      </svg>
    )
  };
  return icons[type] || icons.info;
};

const FullscreenModal = ({ explanation, selectedNode, modelName, onClose }) => (
  <div className="llm-fullscreen-overlay" onClick={onClose}>
    <div className="llm-fullscreen-modal" onClick={e => e.stopPropagation()}>
      <div className="llm-fullscreen-header">
        <div className="llm-fullscreen-title">
          <AIIcon size={18} />
          <span>AI Explanation</span>
          <span className="llm-badge">{modelName || 'LLM'}</span>
        </div>
        <button className="llm-close-btn" onClick={onClose}>
          <CloseIcon />
        </button>
      </div>
      
      <div className="llm-fullscreen-body">
        {/* Node Context */}
        {selectedNode && (
          <div className="llm-node-context">
            <div className="llm-node-header">
              <span className="llm-node-type">{selectedNode.description || selectedNode.type}</span>
              {selectedNode.name && (
                <span className="llm-node-name">{selectedNode.name}</span>
              )}
            </div>
            {(selectedNode.sourceCode || selectedNode.source_code) && (
              <pre className="llm-node-code">{selectedNode.sourceCode || selectedNode.source_code}</pre>
            )}
          </div>
        )}

        {/* Explanation */}
        {explanation.explanation && (
          <div className="llm-section">
            <h4 className="llm-section-title">
              <span className="llm-section-icon"><SectionIcon type="info" /></span>
              Explanation
            </h4>
            <p className="llm-explanation-text">{explanation.explanation}</p>
          </div>
        )}

        {/* Documentation */}
        {explanation.python_doc && (
          <div className="llm-section">
            <h4 className="llm-section-title">
              <span className="llm-section-icon"><SectionIcon type="doc" /></span>
              Documentation
            </h4>
            <p className="llm-python-doc">{explanation.python_doc}</p>
          </div>
        )}

        {/* Examples */}
        {explanation.examples?.length > 0 && (
          <div className="llm-section">
            <h4 className="llm-section-title">
              <span className="llm-section-icon"><SectionIcon type="code" /></span>
              Examples
            </h4>
            {explanation.examples.map((example, idx) => (
              <pre key={idx} className="llm-example-code">{example}</pre>
            ))}
          </div>
        )}

        {/* Related Concepts */}
        {explanation.related_concepts?.length > 0 && (
          <div className="llm-section">
            <h4 className="llm-section-title">
              <span className="llm-section-icon"><SectionIcon type="star" /></span>
              Related Concepts
            </h4>
            <div className="llm-concepts-list">
              {explanation.related_concepts.map((concept, idx) => (
                <span key={idx} className="llm-concept-tag">{concept}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  </div>
);

export default LLMExplanationPanel;
