"""
Node Mapper - AST节点到可视化元素的映射器
"""
from typing import Dict, List, Any, Optional
from ..models.schemas import ASTNode, ASTGraph, NodeType


class NodeMapper:
    """
    将AST节点映射为可视化图形元素
    支持不同的可视化布局和样式主题
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
    
    # 节点类型到类别的映射
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
        """设置颜色主题"""
        if theme_name in self.THEMES:
            self.theme = self.THEMES[theme_name]
            self.theme_name = theme_name
    
    def get_category_color(self, category: str) -> str:
        """获取类别对应的颜色"""
        return self.theme.get(category, self.theme["other"])
    
    def apply_theme_to_node(self, node: ASTNode) -> ASTNode:
        """将主题应用到节点"""
        category = self.TYPE_TO_CATEGORY.get(node.type, "other")
        node.color = self.get_category_color(category)
        return node
    
    def apply_theme_to_graph(self, graph: ASTGraph) -> ASTGraph:
        """将主题应用到整个图"""
        for node in graph.nodes:
            self.apply_theme_to_node(node)
        return graph
    
    def calculate_node_sizes(self, graph: ASTGraph, 
                             min_size: int = 10, 
                             max_size: int = 40) -> ASTGraph:
        """
        根据节点重要性计算节点大小
        重要性与子节点数量和深度相关
        """
        node_children_count = {}
        
        # 统计每个节点的直接子节点数
        for node in graph.nodes:
            node_children_count[node.id] = len(node.children)
        
        # 找到最大子节点数用于归一化
        max_children = max(node_children_count.values()) if node_children_count else 1
        max_children = max(max_children, 1)
        
        # 计算大小
        for node in graph.nodes:
            importance = node_children_count.get(node.id, 0) / max_children
            node.size = int(min_size + importance * (max_size - min_size))
        
        return graph
    
    def to_cytoscape_elements(self, graph: ASTGraph) -> Dict[str, List[Dict]]:
        """
        转换为Cytoscape.js格式
        用于前端可视化库
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
        转换为D3.js格式
        包含节点和链接数组
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
            # 检查边的源节点和目标节点是否存在
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
        转换为层级树结构
        适用于树形可视化
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
        
        # 找到根节点（没有parent的节点）
        root_nodes = [n for n in graph.nodes if n.parent is None]
        
        if not root_nodes:
            return {"name": "root", "children": []}
        
        # 通常只有一个根节点（Module）
        return build_tree(root_nodes[0].id)
    
    def filter_by_type(self, graph: ASTGraph, 
                       node_types: List[NodeType]) -> ASTGraph:
        """
        按节点类型过滤图
        只保留指定类型的节点及其连接
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
        按深度过滤节点
        只保留深度小于等于max_depth的节点
        """
        node_map = {node.id: node for node in graph.nodes}
        
        # 计算每个节点的深度
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
        
        # 计算所有节点深度
        for node in graph.nodes:
            get_depth(node.id)
        
        # 过滤节点
        filtered_nodes = [
            n for n in graph.nodes 
            if depths.get(n.id, 0) <= max_depth
        ]
        filtered_node_ids = {n.id for n in filtered_nodes}
        
        # 过滤边
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
        提取调用关系子图
        只包含函数节点和调用关系
        """
        call_edges = [e for e in graph.edges if e.edge_type == "call"]
        
        # 获取涉及的节点
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
        """获取图的统计信息"""
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
        
        # 节点类型统计
        for node in graph.nodes:
            node_type = node.type.value
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
            
            if node.type == NodeType.FUNCTION:
                stats["function_count"] += 1
            elif node.type == NodeType.CLASS:
                stats["class_count"] += 1
            elif node.type in [NodeType.IF, NodeType.FOR, NodeType.WHILE, NodeType.TRY]:
                stats["control_flow_count"] += 1
        
        # 计算平均子节点数
        total_children = sum(len(n.children) for n in graph.nodes)
        stats["avg_children"] = total_children / len(graph.nodes) if graph.nodes else 0
        
        # 计算最大深度
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
