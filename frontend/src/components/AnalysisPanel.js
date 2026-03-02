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
  // 统一的空值检查
  const complexity = result?.complexity;
  const issues = result?.issues;
  const complexityIssues = issues?.filter(i => i?.type === 'complexity') || [];

  // 提取复杂度指标，使用默认值防止 undefined
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
          title="圈复杂度"
          value={metrics.cyclomatic_complexity}
          status={getComplexityStatus(metrics.cyclomatic_complexity)}
          description="代码分支数量"
        />
        <MetricCard
          title="认知复杂度"
          value={metrics.cognitive_complexity}
          status={getComplexityStatus(metrics.cognitive_complexity)}
          description="理解代码的难度"
        />
        <MetricCard
          title="可维护性指数"
          value={metrics.maintainability_index.toFixed(1)}
          status={getMaintainabilityStatus(metrics.maintainability_index)}
          description="越高越好"
          suffix="/100"
        />
        <MetricCard
          title="最大嵌套深度"
          value={metrics.max_nesting_depth}
          status={getNestingStatus(metrics.max_nesting_depth)}
          description="层级嵌套数"
        />
      </div>

      <div className="section">
        <h3 className="section-title">详细指标</h3>
        <div className="detail-list">
          <DetailItem label="代码行数" value={metrics.lines_of_code} />
          <DetailItem label="函数数量" value={metrics.function_count} />
          <DetailItem label="类数量" value={metrics.class_count} />
          <DetailItem label="平均函数长度" value={`${metrics.avg_function_length.toFixed(1)} 行`} />
          <DetailItem label="Halstead 容量" value={metrics.halstead_volume.toFixed(1)} />
          <DetailItem label="Halstead 难度" value={metrics.halstead_difficulty.toFixed(1)} />
        </div>
      </div>

      {complexityIssues.length > 0 && (
        <div className="section">
          <h3 className="section-title">复杂度问题 ({complexityIssues.length})</h3>
          <IssueList issues={complexityIssues} />
        </div>
      )}
    </div>
  );
});

const PerformancePanel = React.memo(function PerformancePanel({ result }) {
  // 统一的空值检查
  const performance_hotspots = result?.performance_hotspots ?? [];
  const issues = result?.issues ?? [];
  const perfIssues = issues.filter(i => i?.type === 'performance');

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">性能热点 ({performance_hotspots.length})</h3>
        {performance_hotspots.length > 0 ? (
          <div className="hotspot-list">
            {performance_hotspots.map((hotspot, index) => (
              <div key={hotspot?.id ?? index} className="hotspot-card">
                <div className="hotspot-header">
                  <AlertTriangle size={18} className="warning-icon" />
                  <span className="hotspot-type">{hotspot?.hotspot_type ?? '未知类型'}</span>
                  <span className="hotspot-complexity">{hotspot?.estimated_complexity ?? 'N/A'}</span>
                </div>
                <p className="hotspot-description">{hotspot?.description ?? '无描述'}</p>
                {hotspot?.suggestion && (
                  <p className="hotspot-suggestion">建议: {hotspot.suggestion}</p>
                )}
                {hotspot?.lineno && (
                  <span className="hotspot-location">行 {hotspot.lineno}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <CheckCircle size={48} className="success-icon" />
            <p>未发现性能热点</p>
          </div>
        )}
      </div>

      {perfIssues.length > 0 && (
        <div className="section">
          <h3 className="section-title">性能问题 ({perfIssues.length})</h3>
          <IssueList issues={perfIssues} />
        </div>
      )}
    </div>
  );
});

const SecurityPanel = React.memo(function SecurityPanel({ result }) {
  // 统一的空值检查
  const securityIssues = result?.issues?.filter(i => i?.type === 'security') ?? [];

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">安全扫描结果</h3>
        
        {securityIssues.length > 0 ? (
          <>
            <div className="security-summary">
              <div className="summary-item critical">
                <span className="count">{securityIssues.filter(i => i?.severity === 'critical').length}</span>
                <span className="label">严重</span>
              </div>
              <div className="summary-item error">
                <span className="count">{securityIssues.filter(i => i?.severity === 'error').length}</span>
                <span className="label">错误</span>
              </div>
              <div className="summary-item warning">
                <span className="count">{securityIssues.filter(i => i?.severity === 'warning').length}</span>
                <span className="label">警告</span>
              </div>
            </div>
            
            <IssueList issues={securityIssues} showSeverity={true} />
          </>
        ) : (
          <div className="empty-state">
            <CheckCircle size={48} className="success-icon" />
            <p>未发现安全问题</p>
          </div>
        )}
      </div>
    </div>
  );
});

const SuggestionsPanel = React.memo(function SuggestionsPanel({ result }) {
  // 统一的空值检查
  const suggestions = result?.suggestions ?? [];
  const byCategory = groupByCategory(suggestions);

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">优化建议 ({suggestions.length})</h3>
        
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
            <p>代码质量良好，无需优化</p>
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
        <h3 className="section-title">学习模式</h3>
        <p className="section-description">
          点击AST图中的任意节点，查看该语法结构的详细解释和Python文档。
        </p>
        
        <div className="learn-tips">
          <div className="tip-card">
            <h4>函数定义</h4>
            <p>使用 <code>def</code> 关键字定义函数。函数可以接收参数并返回值。</p>
          </div>
          <div className="tip-card">
            <h4>类定义</h4>
            <p>使用 <code>class</code> 关键字定义类。类是面向对象编程的基础。</p>
          </div>
          <div className="tip-card">
            <h4>控制流</h4>
            <p>Python支持 <code>if</code>、<code>for</code>、<code>while</code> 等控制流语句。</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChallengesPanel() {
  const [challenges] = React.useState([
    { id: '1', title: '优化嵌套循环', difficulty: 'easy', completed: false },
    { id: '2', title: '修复安全问题', difficulty: 'medium', completed: false },
    { id: '3', title: '降低复杂度', difficulty: 'hard', completed: false },
  ]);

  return (
    <div className="panel-content">
      <div className="section">
        <h3 className="section-title">挑战模式</h3>
        <p className="section-description">
          通过解决实际代码问题来提升你的编程技能。
        </p>
        
        <div className="challenges-list">
          {challenges.map((challenge) => (
            <div key={challenge.id} className="challenge-card">
              <div className="challenge-info">
                <h4>{challenge.title}</h4>
                <span className={`difficulty ${challenge.difficulty}`}>
                  {getDifficultyLabel(challenge.difficulty)}
                </span>
              </div>
              <button className="btn btn-secondary">
                开始挑战
              </button>
            </div>
          ))}
        </div>
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
              <span className="issue-location">行 {issue.lineno}</span>
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
          <span className="auto-fix-badge">可自动修复</span>
        )}
      </div>
      
      {expanded && (
        <div className="suggestion-body">
          <p>{suggestion.description}</p>
          
          {suggestion.before_code && (
            <div className="code-comparison">
              <div className="code-block">
                <span className="code-label">修改前</span>
                <pre>{suggestion.before_code}</pre>
              </div>
              {suggestion.after_code && (
                <div className="code-block">
                  <span className="code-label">修改后</span>
                  <pre>{suggestion.after_code}</pre>
                </div>
              )}
            </div>
          )}
          
          {suggestion.estimated_improvement && (
            <p className="improvement">
              预估改进: {suggestion.estimated_improvement}
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
    performance: '性能优化',
    readability: '可读性',
    security: '安全性',
    best_practice: '最佳实践',
  };
  return labels[category] || category;
}

function getDifficultyLabel(difficulty) {
  const labels = {
    easy: '简单',
    medium: '中等',
    hard: '困难',
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
