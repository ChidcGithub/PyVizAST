"""
Project Metrics Aggregator - Aggregate project-level metrics
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .models import ProjectMetrics, FileAnalysisResult, ProjectScanResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ProjectMetricsAggregator:
    """Project Metrics Aggregator"""
    
    def __init__(self):
        self.reset()
    
    def reset(self) -> None:
        """Reset aggregator state"""
        self.total_files = 0
        self.total_lines = 0
        self.total_functions = 0
        self.total_classes = 0
        self.total_complexity = 0
        self.total_maintainability = 0.0
        self.complexity_by_file: Dict[str, int] = {}
        self.file_count = 0  # For calculating averages
    
    def aggregate(self, file_results: List[FileAnalysisResult],
                  scan_result: ProjectScanResult,
                  global_issues: List[Any]) -> ProjectMetrics:
        """
        Aggregate analysis results from all files
        
        Args:
            file_results: List of file analysis results
            scan_result: Project scan result
            global_issues: List of global issues
        
        Returns:
            Project-level metrics
        """
        self.reset()
        
        # Basic statistics
        self.total_files = scan_result.total_files
        self.total_lines = scan_result.total_size
        
        # Iterate through all file results
        for result in file_results:
            self._aggregate_file(result)
        
        # Calculate averages
        avg_complexity = self.total_complexity / max(1, self.file_count)
        avg_maintainability = self.total_maintainability / max(1, self.file_count)
        
        # Find file with maximum complexity
        max_complexity_file = None
        max_complexity_value = 0
        for file_path, complexity in self.complexity_by_file.items():
            if complexity > max_complexity_value:
                max_complexity_value = complexity
                max_complexity_file = file_path
        
        # Count global issues
        circular_count = sum(1 for issue in global_issues 
                           if issue.issue_type == 'circular_dependency')
        unused_count = sum(1 for issue in global_issues 
                         if issue.issue_type == 'unused_export')
        
        # Estimate test coverage
        test_files = sum(1 for f in scan_result.file_infos if f.is_test)
        test_coverage = (test_files / max(1, self.total_files)) * 100
        
        return ProjectMetrics(
            total_files=self.total_files,
            total_lines=self.total_lines,
            total_functions=self.total_functions,
            total_classes=self.total_classes,
            avg_complexity=round(avg_complexity, 2),
            avg_maintainability=round(avg_maintainability, 2),
            max_complexity_file=max_complexity_file,
            max_complexity_value=max_complexity_value,
            dependency_count=self._count_dependencies(scan_result),
            circular_dependency_count=circular_count,
            unused_export_count=unused_count,
            test_coverage_estimate=round(test_coverage, 2),
        )
    
    def _aggregate_file(self, result: FileAnalysisResult) -> None:
        """Aggregate results from a single file"""
        summary = result.summary
        
        self.total_lines += summary.lines_of_code
        self.total_functions += summary.function_count
        self.total_classes += summary.class_count
        self.total_complexity += summary.cyclomatic_complexity
        self.total_maintainability += summary.maintainability_index
        
        self.complexity_by_file[result.file.relative_path] = summary.cyclomatic_complexity
        self.file_count += 1
    
    def _count_dependencies(self, scan_result: ProjectScanResult) -> int:
        """Estimate dependency count"""
        # Simple estimate: file count - 1 as minimum dependency graph
        return max(0, scan_result.total_files - 1)
    
    def get_quality_score(self, metrics: ProjectMetrics) -> float:
        """
        Calculate overall project quality score (0-100)
        
        Factors:
        - Average complexity (lower is better)
        - Average maintainability (higher is better)
        - Circular dependencies (fewer is better)
        - Unused exports (fewer is better)
        """
        score = 100.0
        
        # Complexity penalty (deduct 5 points for each point above 10, max 30)
        complexity_penalty = min(30, (metrics.avg_complexity - 10) * 5)
        if complexity_penalty > 0:
            score -= complexity_penalty
        
        # Maintainability bonus (add 3 points for each 10 points)
        maintainability_bonus = (metrics.avg_maintainability / 10) * 3
        score += min(20, maintainability_bonus)
        
        # Circular dependency penalty (5 points each, max 25)
        circular_penalty = min(25, metrics.circular_dependency_count * 5)
        score -= circular_penalty
        
        # Unused export penalty (1 point each, max 10)
        unused_penalty = min(10, metrics.unused_export_count)
        score -= unused_penalty
        
        # Test coverage bonus (2 points for each 10%, max 20)
        test_bonus = min(20, (metrics.test_coverage_estimate / 10) * 2)
        score += test_bonus
        
        return max(0, min(100, round(score, 1)))
    
    def get_risk_assessment(self, metrics: ProjectMetrics) -> Dict[str, Any]:
        """
        Get risk assessment
        
        Returns:
            Risk assessment results
        """
        risks = []
        
        # High complexity risk
        if metrics.avg_complexity > 15:
            risks.append({
                'type': 'high_complexity',
                'severity': 'high' if metrics.avg_complexity > 20 else 'medium',
                'message': f"High average cyclomatic complexity ({metrics.avg_complexity})",
                'recommendation': 'Consider refactoring complex functions into smaller units',
            })
        
        # Circular dependency risk
        if metrics.circular_dependency_count > 0:
            risks.append({
                'type': 'circular_dependency',
                'severity': 'high' if metrics.circular_dependency_count > 3 else 'medium',
                'message': f"{metrics.circular_dependency_count} circular dependencies detected",
                'recommendation': 'Refactor module structure, introduce intermediate layers to break cycles',
            })
        
        # Maintainability risk
        if metrics.avg_maintainability < 50:
            risks.append({
                'type': 'low_maintainability',
                'severity': 'high' if metrics.avg_maintainability < 30 else 'medium',
                'message': f"Low average maintainability index ({metrics.avg_maintainability})",
                'recommendation': 'Reduce code nesting, improve modularity',
            })
        
        # Test coverage risk
        if metrics.test_coverage_estimate < 20:
            risks.append({
                'type': 'low_test_coverage',
                'severity': 'medium',
                'message': f"Low estimated test coverage ({metrics.test_coverage_estimate}%)",
                'recommendation': 'Add unit tests to improve code quality',
            })
        
        # Maximum complexity file risk
        if metrics.max_complexity_value > 30:
            risks.append({
                'type': 'complex_file',
                'severity': 'high',
                'message': f"File '{metrics.max_complexity_file}' has high complexity ({metrics.max_complexity_value})",
                'recommendation': 'Prioritize refactoring this file, split responsibilities',
            })
        
        return {
            'risk_count': len(risks),
            'high_risk_count': sum(1 for r in risks if r['severity'] == 'high'),
            'risks': risks,
        }
    
    def get_summary_text(self, metrics: ProjectMetrics) -> str:
        """Generate project summary text"""
        quality_score = self.get_quality_score(metrics)
        risk = self.get_risk_assessment(metrics)
        
        lines = [
            f"The project contains {metrics.total_files} Python files with {metrics.total_lines} lines of code.",
            f"Defines {metrics.total_functions} functions and {metrics.total_classes} classes.",
            f"Average cyclomatic complexity: {metrics.avg_complexity}, average maintainability index: {metrics.avg_maintainability}.",
            f"Overall quality score: {quality_score}/100",
        ]
        
        if risk['high_risk_count'] > 0:
            lines.append(f"Found {risk['high_risk_count']} high-risk issues requiring attention.")
        
        if metrics.circular_dependency_count > 0:
            lines.append(f"{metrics.circular_dependency_count} circular dependencies need to be resolved.")
        
        return '\n'.join(lines)