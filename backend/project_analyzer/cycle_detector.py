"""
Circular Dependency Detector - Detect circular dependencies
"""
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from .models import GlobalIssue
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CycleInfo:
    """Circular dependency information"""
    modules: List[str]
    length: int
    severity: str  # 'critical', 'warning', 'info'


class CycleDetector:
    """Circular Dependency Detector"""
    
    def __init__(self, dependency_graph: Dict[str, List[str]]):
        """
        Initialize the detector
        
        Args:
            dependency_graph: Dependency graph {module: [dependencies]}
        """
        self.graph = dependency_graph
        self.adjacency = defaultdict(set)
        
        # Build adjacency list
        for module, deps in dependency_graph.items():
            for dep in deps:
                self.adjacency[module].add(dep)
    
    def detect(self) -> List[GlobalIssue]:
        """
        Detect all circular dependencies
        
        Returns:
            List of circular dependency issues
        """
        cycles = self._find_all_cycles()
        issues = []
        
        seen_cycles = set()  # For deduplication
        
        for cycle in cycles:
            # Normalize cycle (start from smallest element)
            normalized = self._normalize_cycle(cycle)
            cycle_key = tuple(normalized)
            
            if cycle_key in seen_cycles:
                continue
            seen_cycles.add(cycle_key)
            
            # Determine severity
            severity = self._get_severity(normalized)
            
            issue = GlobalIssue(
                issue_type='circular_dependency',
                severity=severity,
                message=self._generate_message(normalized),
                locations=[
                    {
                        'file_path': module,
                        'type': 'module',
                    }
                    for module in normalized
                ],
                suggestion=self._generate_suggestion(normalized),
            )
            issues.append(issue)
        
        if issues:
            logger.warning(f"Detected {len(issues)} circular dependencies")
        
        return issues
    
    def _find_all_cycles(self) -> List[List[str]]:
        """Find all cycles using iterative DFS (avoid recursion stack overflow)"""
        cycles = []
        visited = set()
        
        # Use explicit stack for iterative DFS
        # Stack element: (node, path, rec_stack_set)
        for start_node in list(self.adjacency.keys()):
            if start_node in visited:
                continue
            
            # Independent DFS for each starting node
            stack = [(start_node, [], set())]
            
            while stack:
                node, path, rec_stack = stack.pop()
                
                if node in rec_stack:
                    # Found a cycle: from cycle start to current node
                    cycle_start = path.index(node) if node in path else -1
                    if cycle_start >= 0:
                        cycle = path[cycle_start:] + [node]
                        cycles.append(cycle)
                    continue
                
                if node in visited and node not in rec_stack:
                    # Already visited and not in current recursion stack, skip
                    continue
                
                # Mark as visited
                new_path = path + [node]
                new_rec_stack = rec_stack | {node}
                visited.add(node)
                
                # Traverse neighbors (reverse order to maintain original order)
                neighbors = list(self.adjacency.get(node, []))
                for neighbor in reversed(neighbors):
                    if neighbor in new_rec_stack:
                        # Found a cycle
                        cycle_start = new_path.index(neighbor) if neighbor in new_path else -1
                        if cycle_start >= 0:
                            cycle = new_path[cycle_start:] + [neighbor]
                            cycles.append(cycle)
                    else:
                        stack.append((neighbor, new_path, new_rec_stack))
        
        return cycles
    
    def _normalize_cycle(self, cycle: List[str]) -> List[str]:
        """
        Normalize cycle representation
        Start from smallest module name, maintain cycle direction
        """
        if len(cycle) <= 1:
            return cycle
        
        # Remove duplicate trailing element
        if cycle[0] == cycle[-1]:
            cycle = cycle[:-1]
        
        if not cycle:
            return cycle
        
        # Find position of smallest element
        min_idx = cycle.index(min(cycle))
        
        # Rotate to put smallest element first
        normalized = cycle[min_idx:] + cycle[:min_idx]
        
        return normalized
    
    def _get_severity(self, cycle: List[str]) -> str:
        """
        Determine severity of circular dependency
        
        Rules:
        - 2-module direct cycle: critical
        - 3-4 modules: warning
        - 5+ modules: info
        """
        length = len(cycle)
        
        if length <= 2:
            return 'critical'
        elif length <= 4:
            return 'warning'
        else:
            return 'info'
    
    def _generate_message(self, cycle: List[str]) -> str:
        """Generate issue description"""
        if len(cycle) <= 2:
            return f"Direct circular dependency: {' <-> '.join(cycle)}"
        else:
            return f"Circular dependency chain ({len(cycle)} modules): {' -> '.join(cycle)} -> {cycle[0]}"
    
    def _generate_suggestion(self, cycle: List[str]) -> str:
        """Generate fix suggestion"""
        if len(cycle) <= 2:
            return (
                "Suggestions to break the cycle:\n"
                "1. Extract shared logic into a separate common module\n"
                "2. Use dependency injection instead of direct imports\n"
                "3. Consider using interfaces/abstract base classes"
            )
        else:
            return (
                "Suggestions to simplify module structure:\n"
                "1. Check if each link in the dependency chain is necessary\n"
                "2. Consider introducing an intermediate module for decoupling\n"
                "3. Use lazy imports"
            )
    
    def get_strongly_connected_components(self) -> List[Set[str]]:
        """
        Find strongly connected components using iterative Tarjan's algorithm
        
        Returns:
            List of strongly connected components
        """
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []
        
        # Use explicit stack for iterative processing
        # Stack element: (node, 'enter'|'exit', neighbors_iterator)
        for node in list(self.adjacency.keys()):
            if node in index:
                continue
            
            process_stack = [(node, 'enter', None)]
            
            while process_stack:
                current, state, neighbors_iter = process_stack.pop()
                
                if state == 'enter':
                    # First visit to node
                    index[current] = index_counter[0]
                    lowlinks[current] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(current)
                    on_stack[current] = True
                    
                    # Create neighbor iterator
                    neighbor_list = list(self.adjacency.get(current, []))
                    process_stack.append((current, 'exit', iter(neighbor_list)))
                    
                elif state == 'exit':
                    # Process neighbors
                    try:
                        successor = next(neighbors_iter)
                        if successor not in index:
                            # Successor not visited, visit it first
                            process_stack.append((current, 'exit', neighbors_iter))
                            process_stack.append((successor, 'enter', None))
                        elif on_stack.get(successor, False):
                            lowlinks[current] = min(lowlinks[current], index[successor])
                        else:
                            # Continue to next neighbor
                            process_stack.append((current, 'exit', neighbors_iter))
                    except StopIteration:
                        # All neighbors processed, check if SCC root
                        if lowlinks[current] == index[current]:
                            scc = set()
                            while True:
                                successor = stack.pop()
                                on_stack[successor] = False
                                scc.add(successor)
                                if successor == current:
                                    break
                            if len(scc) > 1:
                                sccs.append(scc)
        
        return sccs