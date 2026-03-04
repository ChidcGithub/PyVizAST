import React from 'react';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  XCircle,
  CheckCircle,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import PatchPanel from './PatchPanel';

function AnalysisPanel({ result, activeTab, code, onApplyPatch }) {
  if (!result) return null;

  const renderContent = () => {
    switch (activeTab) {
      case 'complexity':
        return <ComplexityPanel result={result} />;
      case 'performance':
        return <PerformancePanel result={result} />;
      case 'security':
        return <SecurityPanel result={result} />;
      case 'suggestions':
        return <SuggestionsPanel result={result} />;
      case 'patches':
        return <PatchPanel code={code} onApplyPatch={onApplyPatch} />;
      case 'learn':
        return <LearnPanel result={result} />;
      case 'challenges':
        return <ChallengesPanel />;
      default:
        return null;
    }
  };

  return (
    <div className="analysis-panel">
      {renderContent()}
    </div>
  );
}

const ComplexityPanel = React.memo(function ComplexityPanel({ result }) {
  // Unified null check
  const complexity = result?.complexity;
  const issues = result?.issues;
  const complexityIssues = issues?.filter(i => i?.type === 'complexity') || [];

  // Extract complexity metrics, use default values to prevent undefined
  const metrics = {
    cyclomatic_complexity: complexity?.cyclomatic_complexity ?? 0,
    cognitive_complexity: complexity?.cognitive_complexity ?? 0,
    maintainability_index: complexity?.maintainability_index ?? 100,
    max_nesting_depth: complexity?.max_nesting_depth ?? 0,
    lines_of_code: complexity?.lines_of_code ?? 0,
    function_count: complexity?.function_count ?? 0,
    class_count: complexity?.class_count ?? 0,
    avg_function_length: complexity?.avg_function_length ?? 0,
    halstead_volume: complexity?.halstead_volume ?? 0,
    halstead_difficulty: complexity?.halstead_difficulty ?? 0,
  };

  return (
    <div className="panel-content">
      <div className="metrics-grid">
        <MetricCard
          title="Cyclomatic Complexity"
          value={metrics.cyclomatic_complexity}
          status={getComplexityStatus(metrics.cyclomatic_complexity)}
          description="Number of code branches"
        />
        <MetricCard
          title="Cognitive Complexity"
          value={metrics.cognitive_complexity}
          status={getComplexityStatus(metrics.cognitive_complexity)}
          description="Code understanding difficulty"
        />
        <MetricCard
          title="Maintainability Index"
          value={metrics.maintainability_index.toFixed(1)}
          status={getMaintainabilityStatus(metrics.maintainability_index)}
          description="Higher is better"
          suffix="/100"
        />
        <MetricCard
          title="Max Nesting Depth"
          value={metrics.max_nesting_depth}
          status={getNestingStatus(metrics.max_nesting_depth)}
          description="Nested levels count"
        />
      </div>

      <div className="section">
        <h3 className="section-title">Detailed Metrics</h3>
        <div className="detail-list">
          <DetailItem label="Lines of Code" value={metrics.lines_of_code} />
          <DetailItem label="Function Count" value={metrics.function_count} />
          <DetailItem label="Class Count" value={metrics.class_count} />
          <DetailItem label="Avg Function Length" value={`${metrics.avg_function_length.toFixed(1)} lines`} />
          <DetailItem label="Halstead Volume" value={metrics.halstead_volume.toFixed(1)} />
          <DetailItem label="Halstead Difficulty" value={metrics.halstead_difficulty.toFixed(1)} />
        </div>
      </div>

      {complexityIssues.length > 0 && (
        <div className="section">
          <h3 className="section-title">Complexity Issues ({complexityIssues.length})</h3>
          <IssueList issues={complexityIssues} />
        </div>
      )}
    </div>
  );
});

const PerformancePanel = React.memo(function PerformancePanel({ result }) {
  // Unified null check
  const performance_hotspots = result?.performance_hotspots ?? [];
  const issues = result?.issues ?? [];
  const perfIssues = issues.filter(i => i?.type === 'performance');

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">Performance Hotspots ({performance_hotspots.length})</h3>
        {performance_hotspots.length > 0 ? (
          <div className="hotspot-list">
            {performance_hotspots.map((hotspot, index) => (
              <div key={hotspot?.id ?? index} className="hotspot-card">
                <div className="hotspot-header">
                  <AlertTriangle size={18} className="warning-icon" />
                  <span className="hotspot-type">{hotspot?.hotspot_type ?? 'Unknown type'}</span>
                  <span className="hotspot-complexity">{hotspot?.estimated_complexity ?? 'N/A'}</span>
                </div>
                <p className="hotspot-description">{hotspot?.description ?? 'No description'}</p>
                {hotspot?.suggestion && (
                  <p className="hotspot-suggestion">Suggestion: {hotspot.suggestion}</p>
                )}
                {hotspot?.lineno && (
                  <span className="hotspot-location">Line {hotspot.lineno}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CheckCircle size={48} className="success-icon" />
            <p>No performance hotspots found</p>
          </div>
        )}
      </div>

      {perfIssues.length > 0 && (
        <div className="section">
          <h3 className="section-title">Performance Issues ({perfIssues.length})</h3>
          <IssueList issues={perfIssues} />
        </div>
      )}
    </div>
  );
});

const SecurityPanel = React.memo(function SecurityPanel({ result }) {
  // Unified null check
  const securityIssues = result?.issues?.filter(i => i?.type === 'security') ?? [];

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">Security Scan Results</h3>
        
        {securityIssues.length > 0 ? (
          <>
            <div className="security-summary">
              <div className="summary-item critical">
                <span className="count">{securityIssues.filter(i => i?.severity === 'critical').length}</span>
                <span className="label">Critical</span>
              </div>
              <div className="summary-item error">
                <span className="count">{securityIssues.filter(i => i?.severity === 'error').length}</span>
                <span className="label">Error</span>
              </div>
              <div className="summary-item warning">
                <span className="count">{securityIssues.filter(i => i?.severity === 'warning').length}</span>
                <span className="label">Warning</span>
              </div>
            </div>
            
            <IssueList issues={securityIssues} showSeverity={true} />
          </>
        ) : (
          <div className="empty-state">
            <CheckCircle size={48} className="success-icon" />
            <p>No security issues found</p>
          </div>
        )}
      </div>
    </div>
  );
});

const SuggestionsPanel = React.memo(function SuggestionsPanel({ result }) {
  // Unified null check
  const suggestions = result?.suggestions ?? [];
  const byCategory = groupByCategory(suggestions);

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">Optimization Suggestions ({suggestions.length})</h3>
        
        {suggestions.length > 0 ? (
          <div className="suggestions-list">
            {Object.entries(byCategory).map(([category, items]) => (
              <div key={category} className="suggestion-category">
                <h4 className="category-title">
                  {getCategoryLabel(category)}
                  <span className="category-count">{items?.length ?? 0}</span>
                </h4>
                <div className="category-items">
                  {items?.map((suggestion, index) => (
                    <SuggestionCard key={suggestion?.id ?? index} suggestion={suggestion} />
                  )) ?? null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CheckCircle size={48} className="success-icon" />
            <p>Code quality is good, no optimization needed</p>
          </div>
        )}
      </div>
    </div>
  );
});

function LearnPanel({ result }) {
  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">Learning Mode</h3>
        <p className="section-description">
          Click any node in the AST graph to see detailed explanations and Python documentation for that syntax structure.
        </p>
        
        <div className="learn-tips">
          <div className="tip-card">
            <h4>Function Definition</h4>
            <p>Use the <code>def</code> keyword to define functions. Functions can receive parameters and return values.</p>
          </div>
          <div className="tip-card">
            <h4>Class Definition</h4>
            <p>Use the <code>class</code> keyword to define classes. Classes are the foundation of object-oriented programming.</p>
          </div>
          <div className="tip-card">
            <h4>Control Flow</h4>
            <p>Python supports <code>if</code>, <code>for</code>, <code>while</code> and other control flow statements.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChallengesPanel() {
  const [challenges, setChallenges] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    const fetchChallenges = async () => {
      try {
        setLoading(true);
        // Import API function dynamically to avoid circular dependencies
        const { getChallenges } = await import('../api');
        const data = await getChallenges();
        setChallenges(data || []);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch challenges:', err);
        setError('Failed to load challenges. Please check your connection.');
        // Fallback to empty array
        setChallenges([]);
      } finally {
        setLoading(false);
      }
    };

    fetchChallenges();
  }, []);

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">Challenge Mode</h3>
        <p className="section-description">
          Improve your programming skills by solving real code problems.
        </p>
        
        {loading ? (
          <div className="loading-state">
            <div className="loader-spinner"></div>
            <p>Loading challenges...</p>
          </div>
        ) : error ? (
          <div className="error-state">
            <AlertCircle size={24} className="error-icon" />
            <p>{error}</p>
          </div>
        ) : challenges.length === 0 ? (
          <div className="empty-state">
            <Info size={48} className="info-icon" />
            <p>No challenges available at the moment.</p>
          </div>
        ) : (
          <div className="challenges-list">
            {challenges.map((challenge) => (
              <div key={challenge.id} className="challenge-card">
                <div className="challenge-info">
                  <h4>{challenge.title}</h4>
                  <span className={`difficulty ${challenge.difficulty}`}>
                    {getDifficultyLabel(challenge.difficulty)}
                  </span>
                  {challenge.points && (
                    <span className="challenge-points">{challenge.points} pts</span>
                  )}
                </div>
                <button className="btn btn-secondary">
                  Start Challenge
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Helper Components
const MetricCard = React.memo(function MetricCard({ title, value, status, description, suffix = '' }) {
  return (
    <div className={`metric-card ${status}`}>
      <div className="metric-value">
        {value}{suffix}
      </div>
      <div className="metric-title">{title}</div>
      <div className="metric-description">{description}</div>
    </div>
  );
});

const DetailItem = React.memo(function DetailItem({ label, value }) {
  return (
    <div className="detail-item">
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value}</span>
    </div>
  );
});

const IssueList = React.memo(function IssueList({ issues, showSeverity = true }) {
  return (
    <div className="issue-list">
      {issues.map((issue, index) => (
        <div key={issue.id || index} className={`issue-item ${issue.severity}`}>
          {showSeverity && (
            <span className="issue-severity">
              {getSeverityIcon(issue.severity)}
            </span>
          )}
          <div className="issue-content">
            <p className="issue-message">{issue.message}</p>
            {issue.lineno && (
              <span className="issue-location">Line {issue.lineno}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
});

const SuggestionCard = React.memo(function SuggestionCard({ suggestion }) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="suggestion-card">
      <div className="suggestion-header" onClick={() => setExpanded(!expanded)}>
        <div className="suggestion-title">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span>{suggestion.title}</span>
        </div>
        {suggestion.auto_fixable && (
          <span className="auto-fix-badge">Auto-fixable</span>
        )}
      </div>
      
      {expanded && (
        <div className="suggestion-body">
          <p>{suggestion.description}</p>
          
          {suggestion.before_code && (
            <div className="code-comparison">
              <div className="code-block">
                <span className="code-label">Before</span>
                <pre>{suggestion.before_code}</pre>
              </div>
              {suggestion.after_code && (
                <div className="code-block">
                  <span className="code-label">After</span>
                  <pre>{suggestion.after_code}</pre>
                </div>
              )}
            </div>
          )}
          
          {suggestion.estimated_improvement && (
            <p className="improvement">
              Estimated Improvement: {suggestion.estimated_improvement}
            </p>
          )}
        </div>
      )}
    </div>
  );
});

// Helper Functions
function getComplexityStatus(value) {
  if (!value) return 'good';
  if (value <= 10) return 'good';
  if (value <= 20) return 'warning';
  return 'danger';
}

function getMaintainabilityStatus(value) {
  if (value >= 80) return 'good';
  if (value >= 50) return 'warning';
  return 'danger';
}

function getNestingStatus(value) {
  if (value <= 3) return 'good';
  if (value <= 5) return 'warning';
  return 'danger';
}

function getSeverityIcon(severity) {
  switch (severity) {
    case 'critical':
      return <XCircle size={18} className="critical-icon" />;
    case 'error':
      return <AlertCircle size={18} className="error-icon" />;
    case 'warning':
      return <AlertTriangle size={18} className="warning-icon" />;
    default:
      return <Info size={18} className="info-icon" />;
  }
}

function getCategoryLabel(category) {
  const labels = {
    performance: 'Performance Optimization',
    readability: 'Readability',
    security: 'Security',
    best_practice: 'Best Practices',
  };
  return labels[category] || category;
}

function getDifficultyLabel(difficulty) {
  const labels = {
    easy: 'Easy',
    medium: 'Medium',
    hard: 'Hard',
  };
  return labels[difficulty] || difficulty;
}

function groupByCategory(suggestions) {
  return suggestions.reduce((acc, item) => {
    const category = item.category || 'other';
    if (!acc[category]) acc[category] = [];
    acc[category].push(item);
    return acc;
  }, {});
}

export default AnalysisPanel;