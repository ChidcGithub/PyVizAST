"""
项目级摘要生成器
计算项目级汇总指标
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class FileRanking:
    """文件排名信息"""
    file_path: str
    value: float
    rank: int
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectMetrics:
    """项目级指标"""
    # 基础统计
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_imports: int = 0
    
    # 复杂度统计
    avg_cyclomatic_complexity: float = 0.0
    avg_cognitive_complexity: float = 0.0
    avg_maintainability_index: float = 0.0
    max_cyclomatic_complexity: int = 0
    max_cognitive_complexity: int = 0
    
    # 问题统计
    total_issues: int = 0
    critical_issues: int = 0
    error_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0
    
    # 性能统计
    performance_hotspots: int = 0
    
    # 安全统计
    security_issues: int = 0
    
    # 依赖统计
    internal_dependencies: int = 0
    external_dependencies: int = 0
    circular_dependencies: int = 0
    
    # 排名
    most_complex_files: List[FileRanking] = field(default_factory=list)
    most_issue_files: List[FileRanking] = field(default_factory=list)
    largest_files: List[FileRanking] = field(default_factory=list)


class SummaryGenerator:
    """项目摘要生成器"""

    def __init__(self):
        self.metrics = ProjectMetrics()

    def generate(
        self,
        file_analyses: List[Any],
        dependencies: Any = None,
        global_issues: List[Any] = None
    ) -> Dict[str, Any]:
        """
        生成项目摘要

        Args:
            file_analyses: 文件分析结果列表
            dependencies: 依赖信息
            global_issues: 全局问题列表

        Returns:
            Dict[str, Any]: 摘要字典
        """
        self.metrics = ProjectMetrics()

        # 收集各文件的数据
        complexity_data: List[Dict] = []
        issue_data: List[Dict] = []
        size_data: List[Dict] = []

        for analysis in file_analyses:
            summary = analysis.summary
            complexity = analysis.complexity

            # 基础统计
            self.metrics.total_files += 1
            self.metrics.total_lines += summary.line_count
            self.metrics.total_functions += summary.function_count
            self.metrics.total_classes += summary.class_count

            # 问题统计
            self.metrics.total_issues += summary.issue_count
            self.metrics.critical_issues += summary.critical_issues
            self.metrics.error_issues += summary.error_issues
            self.metrics.warning_issues += summary.warning_issues
            self.metrics.info_issues += summary.info_issues

            # 复杂度数据收集
            if complexity:
                cc = complexity.get('cyclomatic_complexity', 0)
                cogc = complexity.get('cognitive_complexity', 0)
                mi = complexity.get('maintainability_index', 0)

                self.metrics.max_cyclomatic_complexity = max(
                    self.metrics.max_cyclomatic_complexity, cc
                )
                self.metrics.max_cognitive_complexity = max(
                    self.metrics.max_cognitive_complexity, cogc
                )

                complexity_data.append({
                    'file_path': summary.path,
                    'cyclomatic_complexity': cc,
                    'cognitive_complexity': cogc,
                    'maintainability_index': mi,
                })

            # 问题数据收集
            issue_data.append({
                'file_path': summary.path,
                'issue_count': summary.issue_count,
                'critical': summary.critical_issues,
                'error': summary.error_issues,
                'warning': summary.warning_issues,
            })

            # 大小数据收集
            size_data.append({
                'file_path': summary.path,
                'line_count': summary.line_count,
            })

        # 计算平均值
        if self.metrics.total_files > 0:
            total_cc = sum(d['cyclomatic_complexity'] for d in complexity_data)
            total_cogc = sum(d['cognitive_complexity'] for d in complexity_data)
            total_mi = sum(d['maintainability_index'] for d in complexity_data)

            self.metrics.avg_cyclomatic_complexity = total_cc / self.metrics.total_files
            self.metrics.avg_cognitive_complexity = total_cogc / self.metrics.total_files
            self.metrics.avg_maintainability_index = total_mi / self.metrics.total_files

        # 依赖统计
        if dependencies:
            self.metrics.external_dependencies = len(dependencies.external)
            self.metrics.internal_dependencies = sum(
                len(deps) for deps in dependencies.dependency_graph.values()
            )

        # 全局问题统计
        if global_issues:
            self.metrics.circular_dependencies = sum(
                1 for issue in global_issues
                if issue.issue_type == 'circular_dependency'
            )
            self.metrics.security_issues = sum(
                1 for issue in global_issues
                if issue.issue_type == 'security'
            )

        # 计算排名
        self.metrics.most_complex_files = self._rank_by_complexity(complexity_data)
        self.metrics.most_issue_files = self._rank_by_issues(issue_data)
        self.metrics.largest_files = self._rank_by_size(size_data)

        return self._to_dict()

    def _rank_by_complexity(self, data: List[Dict]) -> List[Dict]:
        """按复杂度排名"""
        if not data:
            return []

        # 按圈复杂度排序
        sorted_data = sorted(
            data,
            key=lambda x: x['cyclomatic_complexity'],
            reverse=True
        )

        return [
            {
                'file_path': d['file_path'],
                'value': d['cyclomatic_complexity'],
                'rank': i + 1,
                'details': {
                    'cognitive_complexity': d['cognitive_complexity'],
                    'maintainability_index': d['maintainability_index'],
                }
            }
            for i, d in enumerate(sorted_data[:5])  # 取前5个
        ]

    def _rank_by_issues(self, data: List[Dict]) -> List[Dict]:
        """按问题数量排名"""
        if not data:
            return []

        # 按问题总数排序
        sorted_data = sorted(
            data,
            key=lambda x: x['issue_count'],
            reverse=True
        )

        return [
            {
                'file_path': d['file_path'],
                'value': d['issue_count'],
                'rank': i + 1,
                'details': {
                    'critical': d['critical'],
                    'error': d['error'],
                    'warning': d['warning'],
                }
            }
            for i, d in enumerate(sorted_data[:5])  # 取前5个
        ]

    def _rank_by_size(self, data: List[Dict]) -> List[Dict]:
        """按文件大小排名"""
        if not data:
            return []

        # 按行数排序
        sorted_data = sorted(
            data,
            key=lambda x: x['line_count'],
            reverse=True
        )

        return [
            {
                'file_path': d['file_path'],
                'value': d['line_count'],
                'rank': i + 1,
            }
            for i, d in enumerate(sorted_data[:5])  # 取前5个
        ]

    def _to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            # 基础统计
            'total_files': self.metrics.total_files,
            'total_lines': self.metrics.total_lines,
            'total_functions': self.metrics.total_functions,
            'total_classes': self.metrics.total_classes,
            
            # 复杂度统计
            'avg_cyclomatic_complexity': round(self.metrics.avg_cyclomatic_complexity, 2),
            'avg_cognitive_complexity': round(self.metrics.avg_cognitive_complexity, 2),
            'avg_maintainability_index': round(self.metrics.avg_maintainability_index, 2),
            'max_cyclomatic_complexity': self.metrics.max_cyclomatic_complexity,
            'max_cognitive_complexity': self.metrics.max_cognitive_complexity,
            
            # 问题统计
            'total_issues': self.metrics.total_issues,
            'critical_issues': self.metrics.critical_issues,
            'error_issues': self.metrics.error_issues,
            'warning_issues': self.metrics.warning_issues,
            'info_issues': self.metrics.info_issues,
            
            # 依赖统计
            'internal_dependencies': self.metrics.internal_dependencies,
            'external_dependencies': self.metrics.external_dependencies,
            'circular_dependencies': self.metrics.circular_dependencies,
            
            # 排名
            'most_complex_files': self.metrics.most_complex_files,
            'most_issue_files': self.metrics.most_issue_files,
            'largest_files': self.metrics.largest_files,
            
            # 健康评分
            'health_score': self._calculate_health_score(),
        }

    def _calculate_health_score(self) -> Dict[str, Any]:
        """计算项目健康评分"""
        score = 100.0
        factors = []

        # 复杂度扣分
        if self.metrics.avg_cyclomatic_complexity > 10:
            penalty = min(20, (self.metrics.avg_cyclomatic_complexity - 10) * 2)
            score -= penalty
            factors.append({
                'name': '复杂度过高',
                'impact': -penalty,
                'description': f'平均圈复杂度 {self.metrics.avg_cyclomatic_complexity:.1f} > 10'
            })

        # 问题扣分
        if self.metrics.total_issues > 0:
            issue_penalty = min(30, self.metrics.critical_issues * 10 + 
                                      self.metrics.error_issues * 5 + 
                                      self.metrics.warning_issues * 2)
            score -= issue_penalty
            factors.append({
                'name': '代码问题',
                'impact': -issue_penalty,
                'description': f'{self.metrics.total_issues} 个问题'
            })

        # 循环依赖扣分
        if self.metrics.circular_dependencies > 0:
            penalty = min(15, self.metrics.circular_dependencies * 5)
            score -= penalty
            factors.append({
                'name': '循环依赖',
                'impact': -penalty,
                'description': f'{self.metrics.circular_dependencies} 个循环依赖'
            })

        # 可维护性加分
        if self.metrics.avg_maintainability_index > 70:
            bonus = min(10, (self.metrics.avg_maintainability_index - 70) / 3)
            score += bonus
            factors.append({
                'name': '良好可维护性',
                'impact': bonus,
                'description': f'平均可维护性指数 {self.metrics.avg_maintainability_index:.1f}'
            })

        return {
            'score': max(0, min(100, round(score, 1))),
            'grade': self._score_to_grade(score),
            'factors': factors,
        }

    def _score_to_grade(self, score: float) -> str:
        """将分数转换为等级"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'


def generate_summary(
    file_analyses: List[Any],
    dependencies: Any = None,
    global_issues: List[Any] = None
) -> Dict[str, Any]:
    """
    便捷函数：生成项目摘要

    Args:
        file_analyses: 文件分析结果列表
        dependencies: 依赖信息
        global_issues: 全局问题列表

    Returns:
        Dict[str, Any]: 摘要字典
    """
    generator = SummaryGenerator()
    return generator.generate(file_analyses, dependencies, global_issues)
