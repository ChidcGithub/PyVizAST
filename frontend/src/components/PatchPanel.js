import React, { useState, useCallback, useEffect } from 'react';
import {
  Wand2,
  Check,
  ChevronRight,
  ChevronDown,
  AlertCircle,
  CheckCircle,
  Loader,
  Code,
  ArrowRight,
  Copy,
  CheckCheck
} from 'lucide-react';
import { generatePatches } from '../api';
import logger from '../utils/logger';

// Backend API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Call backend API to apply patch
 */
async function applyPatchViaAPI(code, patch) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/apply-patch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code, patch }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Patch application failed');
    }
    
    const data = await response.json();
    return data.fixed_code;
  } catch (error) {
    logger.warn('Backend patch API unavailable, using frontend fallback', { error: error.message });
    // If backend is unavailable, try frontend fallback
    return applyPatchFallback(code, patch);
  }
}

/**
 * Frontend fallback patch application logic (used when backend is unavailable)
 * Keeps implementation consistent with backend patches.py
 */
function applyPatchFallback(originalCode, patchContent) {
  if (!patchContent || typeof patchContent !== 'string') {
    logger.warn('Invalid patch content provided');
    return null;
  }
  
  if (!originalCode || typeof originalCode !== 'string') {
    logger.warn('Invalid original code provided');
    return null;
  }
  
  try {
    // Unified newline handling (cross-platform compatible)
    const lines = originalCode.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    const patchLines = patchContent.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    
    // Validate diff format
    const hasValidHeader = patchLines.some(line => line.startsWith('---')) && 
                           patchLines.some(line => line.startsWith('+++'));
    if (!hasValidHeader) {
      logger.warn('Invalid unified diff format: missing file headers');
      return null;
    }
    
    // Parse hunks - consistent with backend patches.py
    const hunks = [];
    let currentHunk = null;
    
    for (let i = 0; i < patchLines.length; i++) {
      const line = patchLines[i];
      
      if (line.startsWith('@@')) {
        // Save previous hunk
        if (currentHunk) {
          hunks.push(currentHunk);
        }
        
        // Parse @@ -start,count +start,count @@
        const match = line.match(/@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/);
        if (match) {
          currentHunk = {
            oldStart: parseInt(match[1], 10),
            oldCount: match[2] ? parseInt(match[2], 10) : 1,
            newStart: parseInt(match[3], 10),
            newCount: match[4] ? parseInt(match[4], 10) : 1,
            additions: [],
            removals: [],
            context: [],
            deleted: 0,
            added: 0,
            lines: [],
          };
        } else {
          logger.warn('Invalid hunk header format', { line: line.substring(0, 50) });
          return null;
        }
      } else if (currentHunk) {
        // Parse hunk content - consistent with backend patches.py
        if (line.startsWith('+++') || line.startsWith('---')) {
          continue;
        } else if (line.startsWith('+')) {
          // Added line
          const content = line.substring(1);
          currentHunk.additions.push(content);
          currentHunk.lines.push(content);
          currentHunk.added++;
        } else if (line.startsWith('-')) {
          // Deleted line
          const content = line.substring(1);
          currentHunk.removals.push(content);
          currentHunk.deleted++;
        } else if (line.startsWith('\\')) {
          // Continuation indicator, ignore
          continue;
        } else if (line.startsWith(' ') || line !== '') {
          // Context line
          const content = line.startsWith(' ') ? line.substring(1) : line;
          currentHunk.context.push(content);
          currentHunk.lines.push(content);
        } else if (line === '') {
          // Empty line as context
          currentHunk.lines.push('');
        }
      }
    }
    
    // Save last hunk
    if (currentHunk) {
      hunks.push(currentHunk);
    }
    
    // Validate there are valid hunks
    if (hunks.length === 0) {
      logger.warn('No valid hunks found in patch content');
      return null;
    }
    
    // Apply hunks from back to front to avoid line number offset (consistent with backend)
    hunks.sort((a, b) => b.newStart - a.newStart);
    
    for (const hunk of hunks) {
      const startIdx = hunk.oldStart - 1;
      
      // Boundary check
      if (startIdx < 0 || startIdx > lines.length) {
        logger.warn('Invalid start line number in patch', { oldStart: hunk.oldStart, linesLength: lines.length });
        return null;
      }
      
      // Calculate number of lines to delete
      const deletedCount = hunk.deleted;
      const newLines = hunk.lines;
      
      // Validate deletion range
      if (startIdx + deletedCount > lines.length) {
        logger.debug('Deletion range exceeds code line count, adjusting', { startIdx, deletedCount, linesLength: lines.length });
      }
      
      // Execute replacement
      lines.splice(startIdx, deletedCount, ...newLines);
    }
    
    return lines.join('\n');
    
  } catch (err) {
    logger.error('Failed to parse patch', { error: err.message, stack: err.stack });
    return null;
  }
}

/**
 * Patch Application Panel Component
 * Displays auto-fixable optimization suggestions and allows users to preview and apply patches
 */
function PatchPanel({ code, onApplyPatch }) {
  const [patches, setPatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedPatch, setExpandedPatch] = useState(null);
  const [appliedPatches, setAppliedPatches] = useState(new Set());
  const [copiedPatch, setCopiedPatch] = useState(null);
  const [applying, setApplying] = useState(false);

  // Fetch patch list
  useEffect(() => {
    if (!code || code.trim().length === 0) {
      setPatches([]);
      return;
    }

    const fetchPatches = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await generatePatches(code);
        setPatches(result.patches || []);
      } catch (err) {
        setError(err.message || 'Failed to fetch patches');
        setPatches([]);
      } finally {
        setLoading(false);
      }
    };

    // Delay fetch to avoid frequent requests
    const timer = setTimeout(fetchPatches, 300);
    return () => clearTimeout(timer);
  }, [code]);

  // Toggle patch expansion state
  const togglePatch = useCallback((patchId) => {
    setExpandedPatch(prev => prev === patchId ? null : patchId);
  }, []);

  // Apply patch - prefer backend API
  const handleApply = useCallback(async (patch) => {
    if (onApplyPatch && !applying) {
      setApplying(true);
      try {
        // Prefer calling backend API
        const fixedCode = await applyPatchViaAPI(code, patch.patch);
        if (fixedCode) {
          onApplyPatch(fixedCode);
          setAppliedPatches(prev => new Set([...prev, patch.suggestion_id]));
        } else {
          setError('Patch application failed. Please check if the patch format is correct');
        }
      } catch (err) {
        logger.error('Failed to apply patch', { error: err.message, patchId: patch.suggestion_id });
        setError(err.message || 'Patch application failed');
      } finally {
        setApplying(false);
      }
    }
  }, [code, onApplyPatch, applying]);

  // Copy patch
  const handleCopy = useCallback(async (patchId, patchContent) => {
    try {
      await navigator.clipboard.writeText(patchContent);
      setCopiedPatch(patchId);
      setTimeout(() => setCopiedPatch(null), 2000);
    } catch (err) {
      logger.warn('Failed to copy patch to clipboard', { error: err.message });
    }
  }, []);

  // Render patch diff
  const renderDiff = (patchContent) => {
    if (!patchContent) return null;
    
    const lines = patchContent.split('\n');
    
    return (
      <div className="patch-diff">
        {lines.map((line, index) => {
          let className = 'diff-line';
          
          if (line.startsWith('+++') || line.startsWith('---')) {
            className += ' diff-header';
          } else if (line.startsWith('@@')) {
            className += ' diff-hunk';
          } else if (line.startsWith('+')) {
            className += ' diff-add';
          } else if (line.startsWith('-')) {
            className += ' diff-remove';
          } else if (line.startsWith(' ')) {
            className += ' diff-context';
          }
          
          return (
            <div key={index} className={className}>
              <span className="line-content">{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="patch-panel loading">
        <Loader className="spinner" size={24} />
        <span>Analyzing fixable issues...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="patch-panel error">
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
    );
  }

  if (patches.length === 0) {
    return (
      <div className="patch-panel empty">
        <CheckCircle size={48} className="success-icon" />
        <h4>No Auto-Fix Required</h4>
        <p>No auto-fixable issues found in the code</p>
      </div>
    );
  }

  return (
    <div className="patch-panel">
      <div className="patch-header">
        <Wand2 size={18} />
        <h3>Auto-Fix Suggestions</h3>
        <span className="patch-count">{patches.length} fixable</span>
      </div>

      <div className="patch-list">
        {patches.map((patch) => {
          const isExpanded = expandedPatch === patch.suggestion_id;
          const isApplied = appliedPatches.has(patch.suggestion_id);
          
          return (
            <div 
              key={patch.suggestion_id} 
              className={`patch-item ${isExpanded ? 'expanded' : ''} ${isApplied ? 'applied' : ''}`}
            >
              <div 
                className="patch-item-header"
                onClick={() => togglePatch(patch.suggestion_id)}
              >
                <div className="patch-item-title">
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span className="patch-category">{getCategoryIcon(patch.category)}</span>
                  <span className="patch-title">{patch.title}</span>
                </div>
                <div className="patch-item-actions">
                  {isApplied ? (
                    <span className="applied-badge">
                      <Check size={14} />
                      Applied
                    </span>
                  ) : (
                    <span className="auto-fix-badge">
                      <Wand2 size={12} />
                      Fixable
                    </span>
                  )}
                </div>
              </div>

              {isExpanded && (
                <div className="patch-item-body">
                  <p className="patch-description">{patch.description}</p>
                  
                  {patch.patch && (
                    <div className="patch-diff-container">
                      <div className="patch-diff-header">
                        <span>
                          <Code size={14} />
                          Patch Preview (Unified Diff)
                        </span>
                        <button 
                          className="btn-copy"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCopy(patch.suggestion_id, patch.patch);
                          }}
                        >
                          {copiedPatch === patch.suggestion_id ? (
                            <>
                              <CheckCheck size={14} />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy size={14} />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      {renderDiff(patch.patch)}
                    </div>
                  )}

                  <div className="patch-actions">
                    {!isApplied && (
                      <button 
                        className="btn btn-primary btn-apply"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApply(patch);
                        }}
                        disabled={applying}
                      >
                        <Wand2 size={14} />
                        {applying ? 'Applying...' : 'Apply This Fix'}
                        {!applying && <ArrowRight size={14} />}
                      </button>
                    )}
                    <span className="patch-hint">
                      Applying will update the content in the code editor
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Get category icon
function getCategoryIcon(category) {
  const icons = {
    performance: 'Performance',
    readability: 'Readability',
    security: 'Security',
    best_practice: 'Best Practice',
  };
  return icons[category] || 'Suggestion';
}

export default PatchPanel;
