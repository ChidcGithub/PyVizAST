"""
Circular Dependency Detector - Detect circular dependencies
"""
from __future__ import annotations
from typing import List, Dict, Set, Optional, Tuple
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
    
    def _find_all_cycles(self) -> Tuple[List[List[str]], List[Set[str]]]:
        """
        Find all cycles using strongly connected components (SCC).
        
        This method leverages the Tarjan's algorithm from get_strongly_connected_components()
        to efficiently detect cycles. Each SCC with more than one node contains at least
        one cycle.
        
        Returns:
            Tuple of (cycles, complex_sccs) where:
            - cycles: List of extracted cycles (each cycle is a list of module names)
            - complex_sccs: List of SCCs where exact cycle couldn't be extracted
        """
        # Get strongly connected components using Tarjan's algorithm
        sccs = self.get_strongly_connected_components()
        
        cycles = []
        complex_sccs = []
        
        for scc in sccs:
            # Each SCC with more than one node contains cycles
            if len(scc) > 1:
                # Extract a representative cycle from each SCC
                cycle = self._extract_cycle_from_scc(scc)
                if cycle:
                    cycles.append(cycle)
                else:
                    # Store the SCC for separate reporting
                    complex_sccs.append(scc)
        
        # Also check for self-loops (module depends on itself)
        for module, deps in self.adjacency.items():
            if module in deps:
                cycles.append([module])
        
        return cycles, complex_sccs
    
    def detect(self) -> List[GlobalIssue]:
        """
        Detect all circular dependencies
        
        Returns:
            List of circular dependency issues
        """
        cycles, complex_sccs = self._find_all_cycles()
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
        
        # Handle complex SCCs that couldn't be reduced to simple cycles
        for scc in complex_sccs:
            issue = self._create_scc_issue(scc)
            issues.append(issue)
        
        if issues:
            logger.warning(f"Detected {len(issues)} circular dependencies")
        
        return issues
    
    def _extract_cycle_from_scc(self, scc: Set[str]) -> Optional[List[str]]:
        """
        Extract a representative cycle from a strongly connected component.
        
        Uses a simple path-following approach within the SCC to find a cycle.
        
        Args:
            scc: Set of nodes in the strongly connected component
            
        Returns:
            A cycle as a list of module names, or None if extraction fails
        """
        if len(scc) < 2:
            return None
        
        # Start from any node in the SCC
        start = next(iter(scc))
        path = [start]
        visited_in_path = {start}
        
        # Follow edges within SCC until we find a cycle
        current = start
        max_iterations = len(scc) * 2  # Prevent infinite loops
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            found_next = False
            
            for neighbor in self.adjacency.get(current, []):
                if neighbor in scc:
                    if neighbor in visited_in_path:
                        # Found a cycle back to a node in our path
                        cycle_start = path.index(neighbor)
                        return path[cycle_start:] + [neighbor]
                    else:
                        # Continue exploring
                        path.append(neighbor)
                        visited_in_path.add(neighbor)
                        current = neighbor
                        found_next = True
                        break
            
            if not found_next:
                # Dead end, backtrack
                if len(path) > 1:
                    path.pop()
                    visited_in_path.discard(current)
                    current = path[-1]
                else:
                    break
        
        # Could not extract a specific cycle
        # This indicates mutual dependencies exist but exact cycle is complex
        logger.warning(f"Could not extract specific cycle from SCC of size {len(scc)}, "
                      f"modules: {list(scc)[:5]}{'...' if len(scc) > 5 else ''}. "
                      f"This indicates complex mutual dependencies.")
        return None
    
    def _create_scc_issue(self, scc: Set[str]) -> GlobalIssue:
        """
        Create an issue for a complex SCC where exact cycle couldn't be extracted.
        
        Args:
            scc: Set of modules in the strongly connected component
            
        Returns:
            GlobalIssue representing the complex mutual dependency
        """
        modules = list(scc)
        normalized = sorted(modules)
        severity = self._get_severity(modules)
        
        return GlobalIssue(
            issue_type='circular_dependency',
            severity=severity,
            message=f"Complex mutual dependencies among {len(scc)} modules: {', '.join(normalized[:5])}{'...' if len(normalized) > 5 else ''}",
            locations=[
                {
                    'file_path': module,
                    'type': 'module',
                }
                for module in normalized
            ],
            suggestion=(
                "Suggestions to simplify module structure:\n"
                "1. Consider introducing an intermediate module for decoupling\n"
                "2. Use dependency injection instead of direct imports\n"
                "3. Review if all these inter-dependencies are necessary"
            ),
        )
    
    def _normalize_cycle(self, cycle: List[str]) -> List[str]:
        """
        Normalize cycle representation
        Start from smallest module name, maintain cycle direction
        """
        if len(cycle) <= 1:
            return list(cycle)  # Return a copy, don't modify original
        
        # Create a copy to avoid modifying the input
        cycle = list(cycle)
        
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