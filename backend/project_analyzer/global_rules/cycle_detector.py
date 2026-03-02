"""
循环依赖检测器
使用深度优先搜索（DFS）检测依赖图中的所有环
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CycleInfo:
    """循环依赖信息"""
    cycle: List[str]  # 循环中的文件路径列表
    severity: str = "warning"  # warning 或 error
    description: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = f"检测到循环依赖: {' -> '.join(self.cycle)}"


class CycleDetector:
    """
    循环依赖检测器
    使用 DFS 算法检测有向图中的所有环
    """

    def __init__(self):
        self.cycles: List[CycleInfo] = []
        self._visited: Set[str] = set()
        self._rec_stack: Set[str] = set()
        self._path: List[str] = []
        self._found_cycles: Set[Tuple[str, ...]] = set()

    def detect(self, dependency_graph: Dict[str, List[str]]) -> List[CycleInfo]:
        """
        检测依赖图中的所有循环依赖

        Args:
            dependency_graph: 依赖图 {文件路径: [依赖的文件路径列表]}

        Returns:
            List[CycleInfo]: 检测到的循环列表
        """
        self.cycles = []
        self._visited = set()
        self._rec_stack = set()
        self._path = []
        self._found_cycles = set()

        # 对每个节点进行 DFS
        for node in dependency_graph:
            if node not in self._visited:
                self._dfs(node, dependency_graph)

        return self.cycles

    def _dfs(self, node: str, graph: Dict[str, List[str]]):
        """
        深度优先搜索

        Args:
            node: 当前节点
            graph: 依赖图
        """
        self._visited.add(node)
        self._rec_stack.add(node)
        self._path.append(node)

        # 遍历所有邻居
        for neighbor in graph.get(node, []):
            if neighbor not in self._visited:
                self._dfs(neighbor, graph)
            elif neighbor in self._rec_stack:
                # 找到环
                self._record_cycle(neighbor)

        # 回溯
        self._path.pop()
        self._rec_stack.remove(node)

    def _record_cycle(self, cycle_start: str):
        """
        记录找到的环

        Args:
            cycle_start: 环的起始节点
        """
        # 找到环的起始位置
        start_idx = self._path.index(cycle_start)
        
        # 提取环（包含起点和终点）
        cycle = self._path[start_idx:] + [cycle_start]
        
        # 标准化环表示（从最小元素开始）
        normalized = self._normalize_cycle(cycle)
        
        # 避免重复记录
        cycle_key = tuple(normalized)
        if cycle_key not in self._found_cycles:
            self._found_cycles.add(cycle_key)
            
            # 根据环的长度确定严重程度
            severity = "error" if len(cycle) <= 3 else "warning"
            
            self.cycles.append(CycleInfo(
                cycle=normalized,
                severity=severity
            ))

    def _normalize_cycle(self, cycle: List[str]) -> List[str]:
        """
        标准化环表示（从最小元素开始）

        Args:
            cycle: 原始环

        Returns:
            List[str]: 标准化后的环
        """
        if len(cycle) <= 1:
            return cycle
        
        # 找到最小元素的位置
        min_val = min(cycle[:-1])  # 排除最后一个（重复的起点）
        min_idx = cycle.index(min_val)
        
        # 重新排列
        normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
        
        return normalized

    def get_cycle_count(self) -> int:
        """获取检测到的循环数量"""
        return len(self.cycles)

    def has_cycles(self) -> bool:
        """判断是否存在循环依赖"""
        return len(self.cycles) > 0


def detect_cycles(dependency_graph: Dict[str, List[str]]) -> List[Dict]:
    """
    便捷函数：检测循环依赖

    Args:
        dependency_graph: 依赖图

    Returns:
        List[Dict]: 循环信息列表
    """
    detector = CycleDetector()
    cycles = detector.detect(dependency_graph)
    
    return [
        {
            "cycle": c.cycle,
            "severity": c.severity,
            "description": c.description,
        }
        for c in cycles
    ]
