"""
Node Mapper - Maps AST nodes to visualization elements
"""
from typing import Dict, List, Any, Optional
from ..models.schemas import ASTNode, ASTGraph, NodeType


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
        
        # Count direct children for each node
        for node in graph.nodes:
            node_children_count[node.id] = len(node.children)
        
        # Find the maximum children count for normalization
        max_children = max(node_children_count.values()) if node_children_count else 1
        max_children = max(max_children, 1)
        
        # Calculate sizes
        for node in graph.nodes:
            importance = node_children_count.get(node.id, 0) / max_children
            node.size = int(min_size + importance * (max_size - min_size))
        
        return graph
    
    def to_cytoscape_elements(self, graph: ASTGraph) -> Dict[str, List[Dict]]:
        """
        Convert to Cytoscape.js format.
        Used for frontend visualization library.
        """
        elements = {"nodes": [], "edges": []}
        
        for node in graph.nodes:
            elements["nodes"].append({
                "data": {
                    "id": node.id,
                    "label": node.name or node.type.value,
                    "type": node.type.value,
                    "color": node.color,
                    "shape": node.shape,
                    "size": node.size,
                    "lineno": node.lineno,
                    "docstring": node.docstring,
                    "source_code": node.source_code,
                    "attributes": node.attributes
                }
            })
        
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
        Convert to D3.js format.
        Contains nodes and links arrays.
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
                "docstring": node.docstring,
                "source_code": node.source_code,
                "attributes": node.attributes
            })
        
        links = []
        skipped_edges = 0
        for edge in graph.edges:
            # Check if source and target nodes exist
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
        
        return {"nodes": nodes, "links": links, "metadata": metadata}
    
    def to_hierarchical_tree(self, graph: ASTGraph) -> Dict[str, Any]:
        """
        Convert to hierarchical tree structure.
        Suitable for tree visualization.
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
        
        # Find root nodes (nodes without a parent)
        root_nodes = [n for n in graph.nodes if n.parent is None]
        
        if not root_nodes:
            return {"name": "root", "children": []}
        
        # Typically there is only one root node (Module)
        return build_tree(root_nodes[0].id)
    
    def filter_by_type(self, graph: ASTGraph, 
                       node_types: List[NodeType]) -> ASTGraph:
        """
        Filter graph by node types.
        Only keeps nodes of specified types and their connections.
        """
        filtered_nodes = [n for n in graph.nodes if n.type in node_types]
        filtered_node_ids = {n.id for n in filtered_nodes}
        
        filtered_edges = [
            e for e in graph.edges 
            if e.source in filtered_node_ids and e.target in filtered_node_ids
        ]
        
        return ASTGraph(
            nodes=filtered_nodes,
            edges=filtered_edges,
            metadata=graph.metadata
        )
    
    def filter_by_depth(self, graph: ASTGraph, 
                        max_depth: int) -> ASTGraph:
        """
        Filter nodes by depth.
        Only keeps nodes with depth less than or equal to max_depth.
        """
        node_map = {node.id: node for node in graph.nodes}
        
        # Calculate depth for each node
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
        
        # Calculate depth for all nodes
        for node in graph.nodes:
            get_depth(node.id)
        
        # Filter nodes
        filtered_nodes = [
            n for n in graph.nodes 
            if depths.get(n.id, 0) <= max_depth
        ]
        filtered_node_ids = {n.id for n in filtered_nodes}
        
        # Filter edges
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
        Only includes function nodes and call relationships.
        """
        call_edges = [e for e in graph.edges if e.edge_type == "call"]
        
        # Get involved nodes
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
    
    def get_statistics(self, graph: ASTGraph) -> Dict[str, Any]:
        """Get statistics for the graph."""
        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "node_types": {},
            "max_depth": 0,
            "avg_children": 0,
            "function_count": 0,
            "class_count": 0,
            "control_flow_count": 0
        }
        
        # Node type statistics
        for node in graph.nodes:
            node_type = node.type.value
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
            
            if node.type == NodeType.FUNCTION:
                stats["function_count"] += 1
            elif node.type == NodeType.CLASS:
                stats["class_count"] += 1
            elif node.type in [NodeType.IF, NodeType.FOR, NodeType.WHILE, NodeType.TRY]:
                stats["control_flow_count"] += 1
        
        # Calculate average children count
        total_children = sum(len(n.children) for n in graph.nodes)
        stats["avg_children"] = total_children / len(graph.nodes) if graph.nodes else 0
        
        # Calculate maximum depth
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