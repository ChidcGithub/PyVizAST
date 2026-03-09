"""
Node Mapper - Maps AST nodes to visualization elements
Enhanced with support for code relationships
"""
from typing import Dict, List, Any
from ..models.schemas import ASTNode, ASTGraph, NodeType, VariableInfo


class NodeMapper:
    """
    Maps AST nodes to visualization graph elements.
    Supports different visualization layouts and style themes.
    """
    
    # Minimalist Monochrome Theme
    THEMES = {
        "default": {
            "function": "#ffffff",
            "class": "#e0e0e0",
            "control_flow": "#a0a0a0",
            "data_structures": "#c0c0c0",
            "variables": "#606060",
            "expressions": "#808080",
            "other": "#404040"
        },
        "dark": {
            "function": "#ffffff",
            "class": "#d0d0d0",
            "control_flow": "#909090",
            "data_structures": "#b0b0b0",
            "variables": "#505050",
            "expressions": "#707070",
            "other": "#303030"
        },
        "light": {
            "function": "#000000",
            "class": "#202020",
            "control_flow": "#606060",
            "data_structures": "#404040",
            "variables": "#909090",
            "expressions": "#707070",
            "other": "#b0b0b0"
        }
    }
    
    # Mapping from node types to categories
    TYPE_TO_CATEGORY = {
        NodeType.MODULE: "other",
        NodeType.FUNCTION: "function",
        NodeType.CLASS: "class",
        NodeType.IF: "control_flow",
        NodeType.FOR: "control_flow",
        NodeType.WHILE: "control_flow",
        NodeType.TRY: "control_flow",
        NodeType.WITH: "control_flow",
        NodeType.CALL: "expressions",
        NodeType.BINARY_OP: "expressions",
        NodeType.COMPARE: "expressions",
        NodeType.LAMBDA: "function",
        NodeType.LIST: "data_structures",
        NodeType.DICT: "data_structures",
        NodeType.SET: "data_structures",
        NodeType.TUPLE: "data_structures",
        NodeType.ASSIGN: "variables",
        NodeType.NAME: "variables",
        NodeType.IMPORT: "other",
        NodeType.RETURN: "control_flow",
        NodeType.YIELD: "control_flow",
        NodeType.OTHER: "other",
        NodeType.UNKNOWN: "other",
    }
    
    def __init__(self, theme: str = "default"):
        self.theme = self.THEMES.get(theme, self.THEMES["default"])
        self.theme_name = theme
    
    def set_theme(self, theme_name: str):
        """Set the color theme."""
        if theme_name in self.THEMES:
            self.theme = self.THEMES[theme_name]
            self.theme_name = theme_name
    
    def get_category_color(self, category: str) -> str:
        """Get the color for a given category."""
        return self.theme.get(category, self.theme["other"])
    
    def apply_theme_to_node(self, node: ASTNode) -> ASTNode:
        """Apply the theme to a node."""
        category = self.TYPE_TO_CATEGORY.get(node.type, "other")
        node.color = self.get_category_color(category)
        return node
    
    def apply_theme_to_graph(self, graph: ASTGraph) -> ASTGraph:
        """Apply the theme to the entire graph."""
        for node in graph.nodes:
            self.apply_theme_to_node(node)
        return graph
    
    def calculate_node_sizes(self, graph: ASTGraph, 
                             min_size: int = 10, 
                             max_size: int = 40) -> ASTGraph:
        """
        Calculate node sizes based on node importance.
        Importance is correlated with the number of child nodes and depth.
        """
        node_children_count = {}
        
        for node in graph.nodes:
            node_children_count[node.id] = len(node.children)
        
        max_children = max(node_children_count.values()) if node_children_count else 1
        max_children = max(max_children, 1)
        
        for node in graph.nodes:
            importance = node_children_count.get(node.id, 0) / max_children
            node.size = int(min_size + importance * (max_size - min_size))
        
        return graph
    
    def to_cytoscape_elements(self, graph: ASTGraph) -> Dict[str, List[Dict]]:
        """
        Convert to Cytoscape.js format with enhanced relationship data.
        """
        elements = {"nodes": [], "edges": []}
        
        for node in graph.nodes:
            node_data = {
                "id": node.id,
                "label": node.name or node.type.value,
                "type": node.type.value,
                "color": node.color,
                "shape": node.shape,
                "size": node.size,
                "lineno": node.lineno,
                "end_lineno": node.end_lineno,
                "docstring": node.docstring,
                "source_code": node.source_code,
                "attributes": node.attributes,
                # Extended information
                "icon": node.icon,
                "description": node.description,
                "detailed_label": node.detailed_label,
                "explanation": node.explanation,
                # Code metrics
                "line_count": node.line_count,
                "char_count": node.char_count,
                "indent_level": node.indent_level,
                # Structure info
                "child_count": node.child_count,
                "total_descendants": node.total_descendants,
                "depth": node.depth,
                "scope_name": node.scope_name,
                # Type annotations
                "return_type": node.return_type,
                "parameter_types": node.parameter_types,
                "default_values": node.default_values,
                # Function/Class specific
                "method_count": node.method_count,
                "attribute_count": node.attribute_count,
                "local_var_count": node.local_var_count,
                # Code patterns
                "has_try_except": node.has_try_except,
                "has_loop": node.has_loop,
                "has_recursion": node.has_recursion,
                "is_generator": node.is_generator,
                "is_async": node.is_async,
                # Dependencies
                "imports_used": node.imports_used,
                "functions_called": node.functions_called,
                "is_called_count": node.is_called_count,
                # ===== NEW: Enhanced relationship fields =====
                "base_classes": node.base_classes,
                "derived_classes": node.derived_classes,
                "inheritance_depth": node.inheritance_depth,
                "methods": node.methods,
                "inherited_methods": node.inherited_methods,
                "overridden_methods": node.overridden_methods,
                "decorators": node.decorators,
                "decorated_by": node.decorated_by,
                "decorates": node.decorates,
                "calls_to": node.calls_to,
                "called_by": node.called_by,
                "nested_scopes": node.nested_scopes,
                "enclosing_scope_id": node.enclosing_scope_id,
                "scope_level": node.scope_level,
                "branch_count": node.branch_count,
                "loop_count": node.loop_count,
                "exception_handlers": node.exception_handlers,
                # Variable tracking
                "variables_defined": [v.model_dump() for v in node.variables_defined] if node.variables_defined else [],
                "variables_used": [v.model_dump() for v in node.variables_used] if node.variables_used else [],
            }
            
            elements["nodes"].append({"data": node_data})
        
        for edge in graph.edges:
            elements["edges"].append({
                "data": {
                    "id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.edge_type,
                    "label": edge.label
                }
            })
        
        return elements
    
    def to_d3_format(self, graph: ASTGraph) -> Dict[str, Any]:
        """
        Convert to D3.js format with enhanced relationship data.
        """
        node_id_to_index = {node.id: i for i, node in enumerate(graph.nodes)}
        
        nodes = []
        for node in graph.nodes:
            nodes.append({
                "id": node.id,
                "name": node.name or node.type.value,
                "type": node.type.value,
                "color": node.color,
                "shape": node.shape,
                "size": node.size,
                "lineno": node.lineno,
                "end_lineno": node.end_lineno,
                "docstring": node.docstring,
                "source_code": node.source_code,
                "attributes": node.attributes,
                "icon": node.icon,
                "description": node.description,
                "detailed_label": node.detailed_label,
                "explanation": node.explanation,
                "line_count": node.line_count,
                "char_count": node.char_count,
                "indent_level": node.indent_level,
                "child_count": node.child_count,
                "total_descendants": node.total_descendants,
                "depth": node.depth,
                "scope_name": node.scope_name,
                "return_type": node.return_type,
                "parameter_types": node.parameter_types,
                "default_values": node.default_values,
                "method_count": node.method_count,
                "attribute_count": node.attribute_count,
                "local_var_count": node.local_var_count,
                "has_try_except": node.has_try_except,
                "has_loop": node.has_loop,
                "has_recursion": node.has_recursion,
                "is_generator": node.is_generator,
                "is_async": node.is_async,
                "imports_used": node.imports_used,
                "functions_called": node.functions_called,
                "is_called_count": node.is_called_count,
                # NEW fields
                "base_classes": node.base_classes,
                "derived_classes": node.derived_classes,
                "inheritance_depth": node.inheritance_depth,
                "methods": node.methods,
                "inherited_methods": node.inherited_methods,
                "overridden_methods": node.overridden_methods,
                "decorators": node.decorators,
                "decorated_by": node.decorated_by,
                "decorates": node.decorates,
                "calls_to": node.calls_to,
                "called_by": node.called_by,
                "nested_scopes": node.nested_scopes,
                "enclosing_scope_id": node.enclosing_scope_id,
                "scope_level": node.scope_level,
                "branch_count": node.branch_count,
                "loop_count": node.loop_count,
                "exception_handlers": node.exception_handlers,
            })
        
        links = []
        skipped_edges = 0
        for edge in graph.edges:
            if edge.source not in node_id_to_index or edge.target not in node_id_to_index:
                skipped_edges += 1
                continue
            
            links.append({
                "source": node_id_to_index[edge.source],
                "target": node_id_to_index[edge.target],
                "type": edge.edge_type,
                "label": edge.label
            })
        
        metadata = dict(graph.metadata) if graph.metadata else {}
        if skipped_edges > 0:
            metadata["skipped_edges"] = skipped_edges
        
        # Add relationships summary
        if graph.relationships:
            metadata["relationships"] = [r.model_dump() for r in graph.relationships]
        
        return {"nodes": nodes, "links": links, "metadata": metadata}
    
    def to_hierarchical_tree(self, graph: ASTGraph) -> Dict[str, Any]:
        """
        Convert to hierarchical tree structure.
        """
        node_map = {node.id: node for node in graph.nodes}
        
        def build_tree(node_id: str) -> Dict[str, Any]:
            node = node_map.get(node_id)
            if not node:
                return {}
            
            tree_node = {
                "id": node.id,
                "name": node.name or node.type.value,
                "type": node.type.value,
                "color": node.color,
                "lineno": node.lineno,
                "children": []
            }
            
            for child_id in node.children:
                child_tree = build_tree(child_id)
                if child_tree:
                    tree_node["children"].append(child_tree)
            
            return tree_node
        
        root_nodes = [n for n in graph.nodes if n.parent is None]
        
        if not root_nodes:
            return {"name": "root", "children": []}
        
        return build_tree(root_nodes[0].id)
    
    def filter_by_type(self, graph: ASTGraph, 
                       node_types: List[NodeType]) -> ASTGraph:
        """
        Filter graph by node types.
        """
        filtered_nodes = [n for n in graph.nodes if n.type in node_types]
        filtered_node_ids = {n.id for n in filtered_nodes}
        
        filtered_edges = [
            e for e in graph.edges 
            if e.source in filtered_node_ids and e.target in filtered_node_ids
        ]
        
        filtered_relationships = [
            r for r in graph.relationships
            if r.source_id in filtered_node_ids and r.target_id in filtered_node_ids
        ]
        
        return ASTGraph(
            nodes=filtered_nodes,
            edges=filtered_edges,
            metadata=graph.metadata,
            relationships=filtered_relationships
        )
    
    def filter_by_depth(self, graph: ASTGraph, 
                        max_depth: int) -> ASTGraph:
        """
        Filter nodes by depth.
        """
        node_map = {node.id: node for node in graph.nodes}
        
        depths = {}
        def get_depth(node_id: str) -> int:
            if node_id in depths:
                return depths[node_id]
            
            node = node_map.get(node_id)
            if not node or not node.parent:
                depths[node_id] = 0
                return 0
            
            depth = get_depth(node.parent) + 1
            depths[node_id] = depth
            return depth
        
        for node in graph.nodes:
            get_depth(node.id)
        
        filtered_nodes = [
            n for n in graph.nodes 
            if depths.get(n.id, 0) <= max_depth
        ]
        filtered_node_ids = {n.id for n in filtered_nodes}
        
        filtered_edges = [
            e for e in graph.edges 
            if e.source in filtered_node_ids and e.target in filtered_node_ids
        ]
        
        return ASTGraph(
            nodes=filtered_nodes,
            edges=filtered_edges,
            metadata={**graph.metadata, "max_depth": max_depth}
        )
    
    def get_call_graph(self, graph: ASTGraph) -> ASTGraph:
        """
        Extract call relationship subgraph.
        """
        call_edges = [e for e in graph.edges if e.edge_type == "call"]
        
        node_ids = set()
        for edge in call_edges:
            node_ids.add(edge.source)
            node_ids.add(edge.target)
        
        nodes = [n for n in graph.nodes if n.id in node_ids]
        
        return ASTGraph(
            nodes=nodes,
            edges=call_edges,
            metadata={"type": "call_graph"}
        )
    
    def get_inheritance_graph(self, graph: ASTGraph) -> ASTGraph:
        """
        Extract inheritance relationship subgraph.
        """
        inheritance_edges = [e for e in graph.edges if e.edge_type == "inheritance"]
        
        node_ids = set()
        for edge in inheritance_edges:
            node_ids.add(edge.source)
            node_ids.add(edge.target)
        
        nodes = [n for n in graph.nodes if n.id in node_ids]
        
        return ASTGraph(
            nodes=nodes,
            edges=inheritance_edges,
            metadata={"type": "inheritance_graph"}
        )
    
    def get_statistics(self, graph: ASTGraph) -> Dict[str, Any]:
        """Get statistics for the graph including relationship counts."""
        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "total_relationships": len(graph.relationships),
            "node_types": {},
            "max_depth": 0,
            "avg_children": 0,
            "function_count": 0,
            "class_count": 0,
            "control_flow_count": 0,
            # NEW statistics
            "inheritance_count": 0,
            "decorator_count": 0,
            "total_methods": 0,
            "total_base_classes": 0,
            "total_derived_classes": 0,
        }
        
        for node in graph.nodes:
            node_type = node.type.value
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
            
            if node.type == NodeType.FUNCTION:
                stats["function_count"] += 1
            elif node.type == NodeType.CLASS:
                stats["class_count"] += 1
                stats["total_methods"] += node.method_count
                stats["total_base_classes"] += len(node.base_classes)
                stats["total_derived_classes"] += len(node.derived_classes)
            elif node.type in [NodeType.IF, NodeType.FOR, NodeType.WHILE, NodeType.TRY]:
                stats["control_flow_count"] += 1
            
            stats["decorator_count"] += len(node.decorators)
        
        # Count edges by type
        edge_types = {}
        for edge in graph.edges:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
        stats["edge_types"] = edge_types
        stats["inheritance_count"] = edge_types.get("inheritance", 0)
        
        total_children = sum(len(n.children) for n in graph.nodes)
        stats["avg_children"] = total_children / len(graph.nodes) if graph.nodes else 0
        
        node_map = {n.id: n for n in graph.nodes}
        
        def get_depth(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            
            node = node_map.get(node_id)
            if not node or not node.children:
                return 0
            
            return 1 + max(get_depth(c, visited.copy()) for c in node.children)
        
        roots = [n for n in graph.nodes if not n.parent]
        if roots:
            stats["max_depth"] = max(get_depth(r.id, set()) for r in roots)
        
        return stats
