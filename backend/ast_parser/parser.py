"""
AST Parser - Parse Python source code into visualizable graph structure
Supports performance optimization mode for large codebases
Enhanced with code relationship analysis (inheritance, calls, decorators, variables)

@author: Chidc
@link: github.com/chidcGithub
"""
import ast
import logging
from typing import Dict, List, Optional, Any

from ..models.schemas import ASTNode, ASTEdge, ASTGraph, NodeType
from .node_styles import SKIP_TYPES_SIMPLIFIED, PRIORITY_NODE_TYPES
from .node_builder import NodeBuilder
from .relationships import RelationshipBuilder

logger = logging.getLogger(__name__)


class ASTParser:
    """Python AST Parser - Supports performance optimization mode and enhanced code analysis"""
    
    # Maximum depth for AST traversal
    MAX_DEPTH = 50
    
    def __init__(self, max_nodes: int = 2000, simplified: bool = False):
        """
        Initialize the parser
        
        Args:
            max_nodes: Maximum number of nodes allowed
            simplified: Whether to use simplified mode (skip secondary nodes)
        """
        self.nodes: Dict[str, ASTNode] = {}
        self.edges: List[ASTEdge] = []
        self.relationships = []
        self.max_nodes = max_nodes
        self.simplified = simplified
        self._node_count = 0
        self._skipped_count = 0
        self._lineno_index: Dict[int, List[str]] = {}
        
        # Helper classes
        self._node_builder = NodeBuilder()
        self._relationship_builder = RelationshipBuilder()
    
    def parse(self, code: str, source_lines: Optional[List[str]] = None, tree: Optional[ast.AST] = None) -> ASTGraph:
        """
        Parse Python code and generate AST graph with enhanced relationships
        
        Args:
            code: Python source code string
            source_lines: Source code line list (optional)
            tree: Pre-parsed AST tree (optional)
        
        Returns:
            ASTGraph: Visualizable graph structure with relationships
        """
        # Reset state
        self.nodes = {}
        self.edges = []
        self.relationships = []
        self._node_count = 0
        self._skipped_count = 0
        self._lineno_index = {}
        
        # Reset helpers
        self._node_builder.reset()
        self._relationship_builder.reset()
        
        if tree is not None:
            ast_tree = tree
        else:
            try:
                ast_tree = ast.parse(code)
            except SyntaxError as e:
                raise ValueError(f"Syntax error in code: {e}")
            except MemoryError:
                raise ValueError("Code too large to parse (out of memory). Try simplifying the code or use simplified mode.")
            except RecursionError:
                raise ValueError("Code structure too deeply nested to parse.")
            except (ValueError, TypeError) as e:
                # Handle encoding issues, invalid characters, or type errors
                raise ValueError(f"Invalid code format: {e}")
            except Exception as e:
                # Catch-all for any other unexpected errors during parsing
                raise ValueError(f"Failed to parse code: {type(e).__name__}: {e}")
        
        if source_lines is None:
            source_lines = code.splitlines()
        
        # Traverse AST and build graph
        self._traverse(ast_tree, None, source_lines)
        
        # Build enhanced relationships
        self._relationship_builder.build_inheritance_relationships(
            self.nodes, self.edges, self.relationships
        )
        self._relationship_builder.build_call_relationships(
            self.nodes, self.edges, self.relationships
        )
        self._relationship_builder.build_import_relationships(
            self.nodes, self.edges
        )
        self._relationship_builder.build_decorator_relationships(
            self.nodes, self.edges
        )
        self._relationship_builder.analyze_variable_scopes(self.nodes)
        
        # Post-process: calculate additional metrics
        self._relationship_builder.post_process_nodes(self.nodes)
        
        return ASTGraph(
            nodes=list(self.nodes.values()),
            edges=self.edges,
            metadata={
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "total_relationships": len(self.relationships),
                "node_types": self._count_node_types(),
                "skipped_nodes": self._skipped_count,
                "simplified": self.simplified
            },
            relationships=self.relationships
        )
    
    def _should_skip_node(self, ast_node: ast.AST) -> bool:
        """Determine if node should be skipped (for performance optimization)"""
        if not self.simplified:
            return False
        
        node_type_name = type(ast_node).__name__
        
        if node_type_name in PRIORITY_NODE_TYPES:
            return False
        
        if node_type_name.lower() in {t.lower() for t in SKIP_TYPES_SIMPLIFIED}:
            return True
        
        if self._node_count >= self.max_nodes:
            return True
        
        return False
    
    def _traverse(self, ast_node: ast.AST, parent_id: Optional[str], source_lines: List[str], depth: int = 0):
        """Recursively traverse AST"""
        if depth >= self.MAX_DEPTH:
            if depth == self.MAX_DEPTH:
                logger.warning(f"AST traversal reached max depth {self.MAX_DEPTH}")
            self._skipped_count += 1
            return
        
        if self._should_skip_node(ast_node):
            self._skipped_count += 1
            for child in ast.iter_child_nodes(ast_node):
                self._traverse(child, parent_id, source_lines, depth + 1)
            return
        
        if self._node_count >= self.max_nodes:
            self._skipped_count += 1
            return
        
        self._node_count += 1
        
        try:
            node = self._node_builder.create_ast_node(ast_node, parent_id)
        except Exception as e:
            node_type_name = type(ast_node).__name__
            logger.warning(f"Error creating node for {node_type_name}: {e}")
            node = ASTNode(
                id=f"fallback_{self._node_count}",
                type=NodeType.UNKNOWN,
                name=f"<error: {node_type_name}>",
            )
        
        # Extract source code snippet
        if node.lineno and node.end_lineno:
            start = node.lineno - 1
            end = min(node.end_lineno, len(source_lines))
            node.source_code = "\n".join(source_lines[start:end])
        
        self.nodes[node.id] = node
        
        # Track node for relationship building
        self._relationship_builder.track_node(node)
        
        # Build line number index
        if node.lineno:
            if node.lineno not in self._lineno_index:
                self._lineno_index[node.lineno] = []
            self._lineno_index[node.lineno].append(node.id)
        
        # Add parent-child edge
        if parent_id:
            edge_id = f"edge_{len(self.edges) + 1}"
            edge = ASTEdge(
                id=edge_id,
                source=parent_id,
                target=node.id,
                edge_type="parent-child"
            )
            self.edges.append(edge)
            if parent_id in self.nodes:
                self.nodes[parent_id].children.append(node.id)
        
        # Update scope info
        if node.type in (NodeType.FUNCTION, NodeType.CLASS):
            self._relationship_builder.push_scope(node.id)
            node.enclosing_scope_id = self._relationship_builder._scope_stack[-2] if len(self._relationship_builder._scope_stack) > 1 else None
            node.scope_level = len(self._relationship_builder._scope_stack) - 1
        
        # Traverse child nodes
        for child in ast.iter_child_nodes(ast_node):
            self._traverse(child, node.id, source_lines, depth + 1)
        
        # Pop scope
        if node.type in (NodeType.FUNCTION, NodeType.CLASS):
            self._relationship_builder.pop_scope()
    
    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type"""
        counts = {}
        for node in self.nodes.values():
            counts[node.type.value] = counts.get(node.type.value, 0) + 1
        return counts
    
    def get_node_by_lineno(self, lineno: int) -> Optional[ASTNode]:
        """Get node by line number"""
        if lineno in self._lineno_index:
            node_ids = self._lineno_index[lineno]
            if node_ids:
                return self.nodes.get(node_ids[0])
        for node in self.nodes.values():
            if node.lineno == lineno:
                return node
        return None
    
    def get_nodes_by_lineno(self, lineno: int) -> List[ASTNode]:
        """Get all nodes by line number"""
        if lineno in self._lineno_index:
            return [self.nodes[nid] for nid in self._lineno_index[lineno] if nid in self.nodes]
        return []
    
    def get_function_nodes(self) -> List[ASTNode]:
        """Get all function nodes"""
        return [n for n in self.nodes.values() if n.type == NodeType.FUNCTION]
    
    def get_class_nodes(self) -> List[ASTNode]:
        """Get all class nodes"""
        return [n for n in self.nodes.values() if n.type == NodeType.CLASS]
    
    def get_inheritance_tree(self) -> Dict[str, Any]:
        """Get class inheritance tree structure"""
        tree = {}
        processed = set()
        
        def build_tree(class_name: str) -> Dict[str, Any]:
            if class_name in processed:
                return {}
            processed.add(class_name)
            
            node = self._relationship_builder._class_nodes.get(class_name)
            children = []
            
            # Find derived classes
            for derived_name, bases in self._relationship_builder._class_hierarchy.items():
                if class_name in bases:
                    children.append(build_tree(derived_name))
            
            return {
                "name": class_name,
                "node_id": node.id if node else None,
                "methods": node.methods if node else [],
                "children": children
            }
        
        # Find root classes (no base class or base class not in current code)
        for class_name, bases in self._relationship_builder._class_hierarchy.items():
            if not bases or all(b not in self._relationship_builder._class_hierarchy for b in bases):
                tree[class_name] = build_tree(class_name)
        
        return tree
    
    def get_call_graph(self) -> Dict[str, Any]:
        """Get function call graph"""
        from ..models.schemas import NodeType
        
        nodes = []
        links = []
        
        for node in self.nodes.values():
            if node.type == NodeType.FUNCTION:
                nodes.append({
                    "id": node.id,
                    "name": node.name,
                    "called_count": node.is_called_count
                })
                
                for callee_id in node.calls_to:
                    links.append({
                        "source": node.id,
                        "target": callee_id
                    })
        
        return {"nodes": nodes, "links": links}