"""
模块质量检测规则
检测过大模块、过多公共 API、循环依赖层级等问题
"""

import ast
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ModuleIssue:
    """模块问题"""
    file_path: str
    issue_type: str  # large_module, too_many_exports, circular_dependency_depth
    severity: str  # warning, info
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class ModuleQualityDetector:
    """
    模块质量检测器
    
    检测：
    - 过大的模块（行数过多）
    - 过多的公共 API（函数/类数量过多）
    - 循环依赖的层级深度
    """
    
    # 默认阈值
    DEFAULT_THRESHOLDS = {
        'large_module_lines': 500,  # 超过此行数为大模块
        'large_module_warning_lines': 1000,  # 超过此行数为警告级别
        'too_many_exports': 20,  # 公共 API 数量阈值
        'too_many_exports_warning': 40,  # 警告级别阈值
        'circular_dependency_depth': 3,  # 循环依赖层级阈值
    }
    
    def __init__(self, thresholds: Optional[Dict[str, int]] = None):
        """
        初始化检测器
        
        Args:
            thresholds: 自定义阈值
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.issues: List[ModuleIssue] = []
    
    def detect(
        self,
        files: List[Any],
        dependency_graph: Dict[str, List[str]],
        file_analyses: Optional[Dict[str, Any]] = None
    ) -> List[ModuleIssue]:
        """
        执行检测
        
        Args:
            files: 文件列表
            dependency_graph: 依赖图
            file_analyses: 文件分析结果（可选）
            
        Returns:
            List[ModuleIssue]: 问题列表
        """
        self.issues = []
        
        # 检测过大模块
        self._detect_large_modules(files)
        
        # 检测过多公共 API
        self._detect_too_many_exports(files)
        
        # 检测循环依赖层级
        self._detect_circular_dependency_depth(dependency_graph)
        
        return self.issues
    
    def _detect_large_modules(self, files: List[Any]):
        """检测过大的模块"""
        for file in files:
            line_count = file.line_count if hasattr(file, 'line_count') else len(file.content.splitlines())
            
            if line_count >= self.thresholds['large_module_warning_lines']:
                self.issues.append(ModuleIssue(
                    file_path=file.path,
                    issue_type="large_module",
                    severity="warning",
                    message=f"模块过大: {line_count} 行（建议不超过 {self.thresholds['large_module_warning_lines']} 行）",
                    details={
                        "line_count": line_count,
                        "threshold": self.thresholds['large_module_warning_lines']
                    }
                ))
            elif line_count >= self.thresholds['large_module_lines']:
                self.issues.append(ModuleIssue(
                    file_path=file.path,
                    issue_type="large_module",
                    severity="info",
                    message=f"模块较大: {line_count} 行（建议拆分）",
                    details={
                        "line_count": line_count,
                        "threshold": self.thresholds['large_module_lines']
                    }
                ))
    
    def _detect_too_many_exports(self, files: List[Any]):
        """检测过多的公共 API"""
        for file in files:
            try:
                tree = ast.parse(file.content)
            except SyntaxError:
                continue
            
            # 收集公共符号
            public_functions = []
            public_classes = []
            public_variables = []
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith('_'):
                        public_functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):
                        public_classes.append(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and not target.id.startswith('_'):
                            if not (target.id.startswith('__') and target.id.endswith('__')):
                                public_variables.append(target.id)
            
            total_exports = len(public_functions) + len(public_classes) + len(public_variables)
            
            if total_exports >= self.thresholds['too_many_exports_warning']:
                self.issues.append(ModuleIssue(
                    file_path=file.path,
                    issue_type="too_many_exports",
                    severity="warning",
                    message=f"公共 API 过多: {total_exports} 个（函数: {len(public_functions)}, 类: {len(public_classes)}, 变量: {len(public_variables)}）",
                    details={
                        "total_exports": total_exports,
                        "functions": len(public_functions),
                        "classes": len(public_classes),
                        "variables": len(public_variables),
                        "function_names": public_functions[:10],  # 只显示前10个
                        "class_names": public_classes[:10],
                        "threshold": self.thresholds['too_many_exports_warning']
                    }
                ))
            elif total_exports >= self.thresholds['too_many_exports']:
                self.issues.append(ModuleIssue(
                    file_path=file.path,
                    issue_type="too_many_exports",
                    severity="info",
                    message=f"公共 API 较多: {total_exports} 个，考虑拆分模块",
                    details={
                        "total_exports": total_exports,
                        "functions": len(public_functions),
                        "classes": len(public_classes),
                        "variables": len(public_variables),
                        "threshold": self.thresholds['too_many_exports']
                    }
                ))
    
    def _detect_circular_dependency_depth(self, dependency_graph: Dict[str, List[str]]):
        """检测循环依赖的层级深度"""
        # 找出所有循环
        cycles = self._find_all_cycles(dependency_graph)
        
        for cycle in cycles:
            depth = len(cycle)
            
            if depth >= self.thresholds['circular_dependency_depth']:
                self.issues.append(ModuleIssue(
                    file_path=cycle[0],
                    issue_type="circular_dependency_depth",
                    severity="warning",
                    message=f"深层循环依赖: {depth} 层 ({' → '.join(cycle[:5])}{'...' if depth > 5 else ''})",
                    details={
                        "depth": depth,
                        "cycle": cycle
                    }
                ))
    
    def _find_all_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        查找所有循环依赖
        
        使用 Johnson 算法的简化版本
        """
        cycles = []
        visited = set()
        
        def dfs(node: str, path: List[str], path_set: Set[str]):
            if node in path_set:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                
                # 标准化循环（从最小的节点开始）
                min_idx = cycle[:-1].index(min(cycle[:-1]))
                normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                
                if normalized not in cycles:
                    cycles.append(normalized)
                return
            
            if node in visited:
                return
            
            path.append(node)
            path_set.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path, path_set)
            
            path.pop()
            path_set.remove(node)
            visited.add(node)
        
        for node in graph:
            visited.clear()
            dfs(node, [], set())
        
        return cycles


def detect_module_issues(
    files: List[Any],
    dependency_graph: Dict[str, List[str]],
    file_analyses: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, int]] = None
) -> List[Dict]:
    """
    便捷函数：检测模块问题
    
    Args:
        files: 文件列表
        dependency_graph: 依赖图
        file_analyses: 文件分析结果
        thresholds: 自定义阈值
        
    Returns:
        List[Dict]: 问题列表
    """
    detector = ModuleQualityDetector(thresholds=thresholds)
    issues = detector.detect(files, dependency_graph, file_analyses)
    
    return [
        {
            "file_path": issue.file_path,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "message": issue.message,
            "details": issue.details
        }
        for issue in issues
    ]


@dataclass
class DependencyMetrics:
    """依赖指标"""
    file_path: str
    fan_in: int  # 入度（被多少文件依赖）
    fan_out: int  # 出度（依赖多少文件）
    instability: float  # 不稳定性 (fan_out / (fan_in + fan_out))
    abstractness: float  # 抽象度（抽象元素比例）
    distance: float  # 距离主序列的距离


class DependencyAnalyzer:
    """
    依赖分析器
    
    计算依赖指标：
    - Fan-in / Fan-out
    - 不稳定性
    - 抽象度
    - 距离主序列
    """
    
    def analyze(
        self,
        dependency_graph: Dict[str, List[str]],
        reverse_graph: Dict[str, List[str]],
        file_analyses: Optional[Dict[str, Any]] = None
    ) -> List[DependencyMetrics]:
        """
        分析依赖指标
        
        Args:
            dependency_graph: 依赖图
            reverse_graph: 反向依赖图
            file_analyses: 文件分析结果
            
        Returns:
            List[DependencyMetrics]: 每个文件的依赖指标
        """
        metrics = []
        
        for file_path in dependency_graph:
            fan_out = len(dependency_graph.get(file_path, []))
            fan_in = len(reverse_graph.get(file_path, []))
            
            total = fan_in + fan_out
            instability = fan_out / total if total > 0 else 0
            
            # 计算抽象度
            abstractness = 0.0
            if file_analyses and file_path in file_analyses:
                analysis = file_analyses[file_path]
                complexity = analysis.get('complexity', {})
                abstract_count = complexity.get('class_count', 0)
                concrete_count = complexity.get('function_count', 0)
                total_elements = abstract_count + concrete_count
                abstractness = abstract_count / total_elements if total_elements > 0 else 0
            
            # 距离主序列 = |抽象度 + 不稳定性 - 1|
            distance = abs(abstractness + instability - 1)
            
            metrics.append(DependencyMetrics(
                file_path=file_path,
                fan_in=fan_in,
                fan_out=fan_out,
                instability=instability,
                abstractness=abstractness,
                distance=distance
            ))
        
        return metrics
    
    def get_problematic_files(
        self,
        metrics: List[DependencyMetrics],
        max_instability: float = 0.8,
        max_distance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        获取有问题的文件
        
        Args:
            metrics: 依赖指标列表
            max_instability: 最大不稳定性阈值
            max_distance: 最大距离阈值
            
        Returns:
            List[Dict]: 问题文件列表
        """
        problematic = []
        
        for m in metrics:
            issues = []
            
            if m.fan_out > 10:
                issues.append(f"高耦合: 依赖 {m.fan_out} 个文件")
            
            if m.fan_in > 10:
                issues.append(f"高内聚风险: 被 {m.fan_in} 个文件依赖")
            
            if m.instability > max_instability and m.fan_in > 0:
                issues.append(f"高度不稳定: {m.instability:.2f}")
            
            if m.distance > max_distance:
                issues.append(f"偏离主序列: {m.distance:.2f}")
            
            if issues:
                problematic.append({
                    "file_path": m.file_path,
                    "issues": issues,
                    "metrics": {
                        "fan_in": m.fan_in,
                        "fan_out": m.fan_out,
                        "instability": m.instability,
                        "abstractness": m.abstractness,
                        "distance": m.distance
                    }
                })
        
        return problematic
