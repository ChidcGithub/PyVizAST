import React, { useState, useEffect, useCallback } from 'react';
import CodeEditor from './CodeEditor';
import { getChallenges, getChallenge, submitChallenge, getChallengeCategories } from '../api';
import logger from '../utils/logger';
import { useToast } from './ToastContext';

/**
 * Difficulty badge classes
 */
const DIFFICULTY_CLASSES = {
  easy: 'difficulty-easy',
  medium: 'difficulty-medium',
  hard: 'difficulty-hard'
};

/**
 * Issue type definitions for selection
 */
const ISSUE_TYPES = [
  { id: 'nested_loop', label: 'Nested Loop', description: 'Nested loops causing O(n²) or worse complexity' },
  { id: 'list_membership', label: 'List Membership', description: 'Inefficient membership check on list' },
  { id: 'eval_usage', label: 'eval() Usage', description: 'Dangerous use of eval() function' },
  { id: 'sql_injection', label: 'SQL Injection', description: 'Vulnerable SQL string concatenation' },
  { id: 'deep_nesting', label: 'Deep Nesting', description: 'Excessive nesting depth (>3 levels)' },
  { id: 'high_complexity', label: 'High Complexity', description: 'Cyclomatic complexity too high' },
  { id: 'long_parameter_list', label: 'Long Parameter List', description: 'Too many function parameters' },
  { id: 'unused_variable', label: 'Unused Variable', description: 'Variable declared but never used' },
  { id: 'empty_list_iteration', label: 'Empty Iteration', description: 'Iterating over always-empty collection' },
  { id: 'dead_code', label: 'Dead Code', description: 'Unreachable or never-executed code' },
  { id: 'string_concat_in_loop', label: 'String Concat in Loop', description: 'Inefficient string concatenation in loop' },
  { id: 'bare_except', label: 'Bare Except', description: 'Catching all exceptions without specifying type' },
  { id: 'resource_leak', label: 'Resource Leak', description: 'File/resource not properly closed' },
  { id: 'broadException', label: 'Broad Exception', description: 'Catching too general Exception type' },
  { id: 'inefficient_recursion', label: 'Inefficient Recursion', description: 'Recursive solution without memoization' },
  { id: 'no_memoization', label: 'No Memoization', description: 'Repeated calculations that could be cached' },
  { id: 'missing_type_hints', label: 'Missing Type Hints', description: 'Function lacks type annotations' },
  { id: 'magic_string', label: 'Magic String', description: 'Hardcoded string values instead of constants' },
  { id: 'no_enum', label: 'No Enum', description: 'Should use Enum instead of string constants' },
  { id: 'memory_inefficient', label: 'Memory Inefficient', description: 'Loading entire file/data into memory' },
  { id: 'no_generator', label: 'No Generator', description: 'Could use generator for lazy evaluation' },
  { id: 'race_condition', label: 'Race Condition', description: 'Thread-unsafe shared resource access' },
  { id: 'thread_unsafe', label: 'Thread Unsafe', description: 'Non-atomic read-modify-write operation' },
  { id: 'hardcoded_dependency', label: 'Hardcoded Dependency', description: 'Direct coupling to external service' },
  { id: 'boilerplate_code', label: 'Boilerplate Code', description: 'Repetitive code that could be simplified' },
  { id: 'missing_dataclass', label: 'Missing Dataclass', description: 'Could use @dataclass decorator' },
  { id: 'manual_methods', label: 'Manual Methods', description: 'Manually implementing __init__, __eq__, etc.' },
  { id: 'list_membership_check', label: 'List Membership Check', description: 'Using list for membership testing (use set)' }
];

/**
 * ChallengeView Component - Interactive code challenge mode
 */
function ChallengeView({ theme }) {
  const [challenges, setChallenges] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedChallenge, setSelectedChallenge] = useState(null);
  const [selectedIssues, setSelectedIssues] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('list'); // 'list', 'detail', 'result'
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterDifficulty, setFilterDifficulty] = useState('all');
  const toast = useToast();

  // Fetch challenges and categories on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [challengesData, categoriesData] = await Promise.all([
          getChallenges(),
          getChallengeCategories()
        ]);
        setChallenges(challengesData);
        setCategories(categoriesData);
      } catch (err) {
        toast.error('Failed to load challenges');
        logger.error('Failed to load challenges', { error: err.message });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [toast]);

  // Load challenge detail
  const loadChallenge = useCallback(async (challengeId) => {
    setLoading(true);
    try {
      const data = await getChallenge(challengeId);
      setSelectedChallenge(data);
      setSelectedIssues([]);
      setResult(null);
      setView('detail');
    } catch (err) {
      toast.error('Failed to load challenge');
      logger.error('Failed to load challenge detail', { challengeId, error: err.message });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // Toggle issue selection
  const toggleIssue = useCallback((issueId) => {
    setSelectedIssues(prev => 
      prev.includes(issueId) 
        ? prev.filter(id => id !== issueId)
        : [...prev, issueId]
    );
  }, []);

  // Submit challenge
  const handleSubmit = useCallback(async () => {
    if (!selectedChallenge || selectedIssues.length === 0) {
      toast.error('Please select at least one issue');
      return;
    }

    setLoading(true);
    try {
      const data = await submitChallenge(selectedChallenge.id, selectedIssues);
      setResult(data);
      setView('result');
    } catch (err) {
      toast.error('Failed to submit challenge');
      logger.error('Failed to submit challenge', { 
        challengeId: selectedChallenge.id, 
        error: err.message 
      });
    } finally {
      setLoading(false);
    }
  }, [selectedChallenge, selectedIssues, toast]);

  // Filter challenges
  const filteredChallenges = challenges.filter(c => {
    if (filterCategory !== 'all' && c.category !== filterCategory) return false;
    if (filterDifficulty !== 'all' && c.difficulty !== filterDifficulty) return false;
    return true;
  });

  // Render challenge list
  const renderList = () => (
    <div className="challenge-list-container">
      <div className="challenge-filters">
        <select 
          value={filterCategory} 
          onChange={(e) => setFilterCategory(e.target.value)}
          className="challenge-filter-select"
        >
          <option value="all">All Categories</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>{cat.name}</option>
          ))}
        </select>
        <select 
          value={filterDifficulty} 
          onChange={(e) => setFilterDifficulty(e.target.value)}
          className="challenge-filter-select"
        >
          <option value="all">All Difficulties</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      <div className="challenge-cards">
        {filteredChallenges.map(challenge => (
          <div 
            key={challenge.id} 
            className="challenge-card"
            onClick={() => loadChallenge(challenge.id)}
          >
            <div className="challenge-card-header">
              <h3 className="challenge-card-title">{challenge.title}</h3>
              <span className={`challenge-difficulty-badge ${DIFFICULTY_CLASSES[challenge.difficulty] || ''}`}>
                {challenge.difficulty}
              </span>
            </div>
            <div className="challenge-card-meta">
              <span className="challenge-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                {challenge.estimated_time_minutes} min
              </span>
              <span className="challenge-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
                {challenge.points} pts
              </span>
            </div>
          </div>
        ))}
      </div>

      {filteredChallenges.length === 0 && (
        <div className="challenge-empty">
          <p>No challenges match your filters</p>
        </div>
      )}
    </div>
  );

  // Render challenge detail
  const renderDetail = () => {
    if (!selectedChallenge) return null;

    return (
      <div className="challenge-detail-container">
        <div className="challenge-detail-header">
          <button className="back-button" onClick={() => setView('list')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Back
          </button>
          <div className="challenge-detail-info">
            <h2>{selectedChallenge.title}</h2>
            <div className="challenge-detail-meta">
              <span className={`challenge-difficulty-badge ${DIFFICULTY_CLASSES[selectedChallenge.difficulty] || ''}`}>
                {selectedChallenge.difficulty}
              </span>
              <span className="challenge-meta-item">{selectedChallenge.points} points</span>
              <span className="challenge-meta-item">{selectedChallenge.estimated_time_minutes} min</span>
            </div>
          </div>
        </div>

        <div className="challenge-detail-content">
          <div className="challenge-section">
            <h3>Description</h3>
            <p>{selectedChallenge.description}</p>
          </div>

          {selectedChallenge.learning_objectives && selectedChallenge.learning_objectives.length > 0 && (
            <div className="challenge-section">
              <h3>Learning Objectives</h3>
              <ul className="learning-objectives">
                {selectedChallenge.learning_objectives.map((obj, i) => (
                  <li key={i}>{obj}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="challenge-section">
            <h3>Code</h3>
            <div className="challenge-code-editor">
              <CodeEditor 
                code={selectedChallenge.code}
                readOnly={true}
                theme={theme}
              />
            </div>
          </div>

          <div className="challenge-section">
            <h3>Find the Issues</h3>
            <p className="issue-instruction">Select all problems you can identify in the code above:</p>
            <div className="issue-grid">
              {ISSUE_TYPES.map(issue => (
                <div
                  key={issue.id}
                  className={`issue-chip ${selectedIssues.includes(issue.id) ? 'selected' : ''}`}
                  onClick={() => toggleIssue(issue.id)}
                >
                  <div className="issue-chip-header">
                    <span className="issue-checkbox">
                      {selectedIssues.includes(issue.id) && (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </span>
                    <span className="issue-label">{issue.label}</span>
                  </div>
                  <span className="issue-description">{issue.description}</span>
                </div>
              ))}
            </div>
          </div>

          {selectedChallenge.hints && selectedChallenge.hints.length > 0 && (
            <div className="challenge-section">
              <h3>Hints</h3>
              <ul className="challenge-hints">
                {selectedChallenge.hints.map((hint, i) => (
                  <li key={i}>{hint}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="challenge-actions">
            <button 
              className="submit-button"
              onClick={handleSubmit}
              disabled={loading || selectedIssues.length === 0}
            >
              {loading ? 'Submitting...' : `Submit (${selectedIssues.length} selected)`}
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Render result
  const renderResult = () => {
    if (!result) return null;

    return (
      <div className="challenge-result-container">
        <div className={`result-header ${result.passed ? 'passed' : 'failed'}`}>
          <div className="result-icon">
            {result.passed ? (
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            ) : (
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            )}
          </div>
          <h2>{result.passed ? 'Challenge Passed!' : 'Keep Trying!'}</h2>
          <div className="result-score">
            <span className="score-value">{result.score}</span>
            <span className="score-max">/ {result.max_score}</span>
          </div>
        </div>

        <div className="result-content">
          <div className="result-section">
            <h3>Feedback</h3>
            <div className="result-feedback">{result.feedback}</div>
          </div>

          <div className="result-sections-grid">
            {result.found_issues.length > 0 && (
              <div className="result-section correct">
                <h4>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Found ({result.found_issues.length})
                </h4>
                <ul>
                  {result.found_issues.map((issue, i) => (
                    <li key={i}>{issue.replace(/_/g, ' ')}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.missed_issues.length > 0 && (
              <div className="result-section missed">
                <h4>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  Missed ({result.missed_issues.length})
                </h4>
                <ul>
                  {result.missed_issues.map((issue, i) => (
                    <li key={i}>{issue.replace(/_/g, ' ')}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="result-actions">
            <button className="retry-button" onClick={() => loadChallenge(result.challenge_id)}>
              Try Again
            </button>
            <button className="next-button" onClick={() => setView('list')}>
              More Challenges
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`challenge-view ${theme}`}>
      {loading && view === 'list' && (
        <div className="challenge-loading">
          <div className="loader-spinner"></div>
          <p>Loading challenges...</p>
        </div>
      )}

      {!loading && view === 'list' && renderList()}
      {view === 'detail' && renderDetail()}
      {view === 'result' && renderResult()}
    </div>
  );
}

export default ChallengeView;
