"""
AST Parser - 将Python源代码解析为可视化图结构
支持性能优化模式处理大型代码库
"""
import ast
import uuid
from typing import Dict, List, Optional, Any, Set
from ..models.schemas import (
    ASTNode, ASTEdge, ASTGraph, NodeType
)


# Performance optimization: Skip these node types in simplified mode
SKIP_TYPES_SIMPLIFIED = {
    'expr', 'expr_context', 'slice', 'boolop', 'operator', 
    'unaryop', 'cmpop', 'comprehension', 'excepthandler',
    'arguments', 'arg', 'keyword', 'alias', 'withitem',
    'type_ignore', 'type_param', 'pattern'
}

# Priority node types that are always kept
PRIORITY_NODE_TYPES = {
    'Module', 'FunctionDef', 'AsyncFunctionDef', 'ClassDef',
    'If', 'For', 'AsyncFor', 'While', 'Try', 'With', 'AsyncWith',
    'Import', 'ImportFrom', 'Return', 'Yield', 'YieldFrom'
}


class ASTParser:
    """Python AST解析器 - 支持性能优化模式"""
    
    # 节点类型到颜色和形状的映射
    NODE_STYLES = {
        # 结构节点
        NodeType.MODULE: {"color": "#ffffff", "shape": "hexagon", "size": 30},
        NodeType.FUNCTION: {"color": "#ffffff", "shape": "roundrectangle", "size": 25},
        NodeType.CLASS: {"color": "#e0e0e0", "shape": "roundrectangle", "size": 28},
        
        # 控制流
        NodeType.IF: {"color": "#a0a0a0", "shape": "diamond", "size": 20},
        NodeType.FOR: {"color": "#a0a0a0", "shape": "diamond", "size": 20},
        NodeType.WHILE: {"color": "#a0a0a0", "shape": "diamond", "size": 20},
        NodeType.TRY: {"color": "#909090", "shape": "diamond", "size": 22},
        NodeType.WITH: {"color": "#909090", "shape": "diamond", "size": 20},
        
        # 表达式
        NodeType.CALL: {"color": "#707070", "shape": "circle", "size": 15},
        NodeType.BINARY_OP: {"color": "#606060", "shape": "circle", "size": 12},
        NodeType.COMPARE: {"color": "#606060", "shape": "circle", "size": 12},
        NodeType.LAMBDA: {"color": "#d0d0d0", "shape": "ellipse", "size": 18},
        
        # 数据结构
        NodeType.LIST: {"color": "#808080", "shape": "rectangle", "size": 15},
        NodeType.DICT: {"color": "#808080", "shape": "rectangle", "size": 15},
        NodeType.SET: {"color": "#808080", "shape": "rectangle", "size": 15},
        NodeType.TUPLE: {"color": "#808080", "shape": "rectangle", "size": 15},
        
        # 变量
        NodeType.ASSIGN: {"color": "#505050", "shape": "circle", "size": 14},
        NodeType.NAME: {"color": "#404040", "shape": "circle", "size": 10},
        
        # 其他
        NodeType.IMPORT: {"color": "#909090", "shape": "parallelogram", "size": 16},
        NodeType.RETURN: {"color": "#707070", "shape": "triangle", "size": 14},
        NodeType.YIELD: {"color": "#707070", "shape": "triangle", "size": 14},
        NodeType.OTHER: {"color": "#404040", "shape": "circle", "size": 10},
    }
    
    def __init__(self, max_nodes: int = 2000, simplified: bool = False):
        """
        初始化解析器
        
        Args:
            max_nodes: 最大节点数量限制
            simplified: 是否使用简化模式（跳过次要节点）
        """
        self.nodes: Dict[str, ASTNode] = {}
        self.edges: List[ASTEdge] = []
        self.node_counter: Dict[str, int] = {}
        self.max_nodes = max_nodes
        self.simplified = simplified
        self._node_count = 0
        self._skipped_count = 0
    
    def _generate_id(self, node_type: str) -> str:
        """生成唯一节点ID"""
        self.node_counter[node_type] = self.node_counter.get(node_type, 0) + 1
        return f"{node_type}_{self.node_counter[node_type]}"
    
    def _get_node_type(self, ast_node: ast.AST) -> NodeType:
        """将ast节点类型映射到NodeType枚举"""
        type_mapping = {
            ast.Module: NodeType.MODULE,
            ast.FunctionDef: NodeType.FUNCTION,
            ast.AsyncFunctionDef: NodeType.FUNCTION,
            ast.ClassDef: NodeType.CLASS,
            ast.If: NodeType.IF,
            ast.For: NodeType.FOR,
            ast.AsyncFor: NodeType.FOR,
            ast.While: NodeType.WHILE,
            ast.Try: NodeType.TRY,
            ast.With: NodeType.WITH,
            ast.AsyncWith: NodeType.WITH,
            ast.Call: NodeType.CALL,
            ast.BinOp: NodeType.BINARY_OP,
            ast.Compare: NodeType.COMPARE,
            ast.Lambda: NodeType.LAMBDA,
            ast.List: NodeType.LIST,
            ast.Dict: NodeType.DICT,
            ast.Set: NodeType.SET,
            ast.Tuple: NodeType.TUPLE,
            ast.Assign: NodeType.ASSIGN,
            ast.AugAssign: NodeType.ASSIGN,
            ast.Name: NodeType.NAME,
            ast.Import: NodeType.IMPORT,
            ast.ImportFrom: NodeType.IMPORT,
            ast.Return: NodeType.RETURN,
            ast.Yield: NodeType.YIELD,
            ast.YieldFrom: NodeType.YIELD,
        }
        return type_mapping.get(type(ast_node), NodeType.OTHER)
    
    def _get_node_name(self, ast_node: ast.AST) -> Optional[str]:
        """获取节点名称"""
        if isinstance(ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return ast_node.name
        elif isinstance(ast_node, ast.ClassDef):
            return ast_node.name
        elif isinstance(ast_node, ast.Name):
            return ast_node.id
        elif isinstance(ast_node, ast.Call):
            if isinstance(ast_node.func, ast.Name):
                return ast_node.func.id
            elif isinstance(ast_node.func, ast.Attribute):
                return f"{self._get_attribute_name(ast_node.func)}"
        elif isinstance(ast_node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in ast_node.names]
            return ", ".join(names)
        elif isinstance(ast_node, ast.Assign):
            targets = []
            for t in ast_node.targets:
                if isinstance(t, ast.Name):
                    targets.append(t.id)
            return " = ".join(targets) if targets else None
        return None
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """获取属性访问的完整名称"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr
    
    def _create_ast_node(self, ast_node: ast.AST, parent_id: Optional[str] = None) -> ASTNode:
        """创建ASTNode对象"""
        node_type = self._get_node_type(ast_node)
        style = self.NODE_STYLES.get(node_type, self.NODE_STYLES[NodeType.OTHER])
        
        node_id = self._generate_id(node_type.value)
        name = self._get_node_name(ast_node)
        
        # 获取源代码位置
        lineno = getattr(ast_node, 'lineno', None)
        col_offset = getattr(ast_node, 'col_offset', None)
        end_lineno = getattr(ast_node, 'end_lineno', None)
        end_col_offset = getattr(ast_node, 'end_col_offset', None)
        
        # 获取文档字符串
        docstring = ast.get_docstring(ast_node) if isinstance(
            ast_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ) else None
        
        # 提取额外属性
        attributes = self._extract_attributes(ast_node)
        
        return ASTNode(
            id=node_id,
            type=node_type,
            name=name,
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            color=style["color"],
            shape=style["shape"],
            size=style["size"],
            children=[],
            parent=parent_id,
            docstring=docstring,
            attributes=attributes
        )
    
    def _extract_attributes(self, ast_node: ast.AST) -> Dict[str, Any]:
        """提取节点的额外属性"""
        attrs = {}
        
        if isinstance(ast_node, ast.FunctionDef):
            attrs['args'] = [arg.arg for arg in ast_node.args.args]
            attrs['decorators'] = [self._get_decorator_name(d) for d in ast_node.decorator_list]
            attrs['is_async'] = isinstance(ast_node, ast.AsyncFunctionDef)
        
        elif isinstance(ast_node, ast.ClassDef):
            attrs['bases'] = [self._get_base_name(b) for b in ast_node.bases]
            attrs['decorators'] = [self._get_decorator_name(d) for d in ast_node.decorator_list]
        
        elif isinstance(ast_node, ast.For):
            attrs['target'] = self._get_target_name(ast_node.target)
            attrs['is_async'] = isinstance(ast_node, ast.AsyncFor)
        
        elif isinstance(ast_node, ast.While):
            attrs['has_else'] = bool(ast_node.orelse)
        
        elif isinstance(ast_node, ast.If):
            attrs['has_else'] = bool(ast_node.orelse)
        
        elif isinstance(ast_node, ast.Call):
            attrs['args_count'] = len(ast_node.args)
            attrs['kwargs'] = [kw.arg for kw in ast_node.keywords]
        
        elif isinstance(ast_node, ast.BinOp):
            attrs['operator'] = type(ast_node.op).__name__
        
        elif isinstance(ast_node, ast.Compare):
            attrs['operators'] = [type(op).__name__ for op in ast_node.ops]
        
        elif isinstance(ast_node, (ast.Import, ast.ImportFrom)):
            attrs['names'] = [(n.name, n.asname) for n in ast_node.names]
            if isinstance(ast_node, ast.ImportFrom):
                attrs['module'] = ast_node.module
        
        return attrs
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """获取装饰器名称"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_node_name(decorator) or "unknown"
        elif isinstance(decorator, ast.Attribute):
            return self._get_attribute_name(decorator)
        return "unknown"
    
    def _get_base_name(self, base: ast.AST) -> str:
        """获取基类名称"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return self._get_attribute_name(base)
        return "unknown"
    
    def _get_target_name(self, target: ast.AST) -> str:
        """获取循环目标名称"""
        if isinstance(target, ast.Name):
            return target.id
        return "unknown"
    
    def _create_edge(self, source_id: str, target_id: str, edge_type: str, label: Optional[str] = None) -> ASTEdge:
        """创建边"""
        edge_id = f"edge_{len(self.edges) + 1}"
        return ASTEdge(
            id=edge_id,
            source=source_id,
            target=target_id,
            edge_type=edge_type,
            label=label
        )
    
    def parse(self, code: str, source_lines: Optional[List[str]] = None) -> ASTGraph:
        """
        解析Python代码并生成AST图
        
        Args:
            code: Python源代码字符串
            source_lines: 源代码行列表（可选，用于提取代码片段）
        
        Returns:
            ASTGraph: 可视化图结构
        """
        # 重置状态
        self.nodes = {}
        self.edges = []
        self.node_counter = {}
        self._node_count = 0
        self._skipped_count = 0
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in code: {e}")
        
        if source_lines is None:
            source_lines = code.splitlines()
        
        # 遍历AST并构建图
        self._traverse(tree, None, source_lines)
        
        # 构建调用关系图
        self._build_call_relationships()
        
        # 构建导入关系
        self._build_import_relationships()
        
        return ASTGraph(
            nodes=list(self.nodes.values()),
            edges=self.edges,
            metadata={
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": self._count_node_types(),
                "skipped_nodes": self._skipped_count,
                "simplified": self.simplified
            }
        )
    
    def _should_skip_node(self, ast_node: ast.AST) -> bool:
        """判断是否应该跳过该节点（用于性能优化）"""
        if not self.simplified:
            return False
        
        node_type_name = type(ast_node).__name__
        
        # Always keep priority nodes
        if node_type_name in PRIORITY_NODE_TYPES:
            return False
        
        # Skip certain node types in simplified mode
        if node_type_name.lower() in {t.lower() for t in SKIP_TYPES_SIMPLIFIED}:
            return True
        
        # Skip if we've reached max nodes
        if self._node_count >= self.max_nodes:
            return True
        
        return False
    
    def _traverse(self, ast_node: ast.AST, parent_id: Optional[str], source_lines: List[str], depth: int = 0):
        """递归遍历AST"""
        # Check if we should skip this node
        if self._should_skip_node(ast_node):
            self._skipped_count += 1
            # Still traverse children if not at max depth
            if depth < 50:  # Max depth limit
                for child in ast.iter_child_nodes(ast_node):
                    self._traverse(child, parent_id, source_lines, depth + 1)
            return
        
        # Check node limit
        if self._node_count >= self.max_nodes:
            self._skipped_count += 1
            return
        
        self._node_count += 1
        
        # 创建当前节点
        node = self._create_ast_node(ast_node, parent_id)
        
        # 提取源代码片段
        if node.lineno and node.end_lineno:
            start = node.lineno - 1
            end = min(node.end_lineno, len(source_lines))
            node.source_code = "\n".join(source_lines[start:end])
        
        self.nodes[node.id] = node
        
        # 添加父子边
        if parent_id:
            edge = self._create_edge(parent_id, node.id, "parent-child")
            self.edges.append(edge)
            # 更新父节点的children列表
            if parent_id in self.nodes:
                self.nodes[parent_id].children.append(node.id)
        
        # 遍历子节点
        for child in ast.iter_child_nodes(ast_node):
            self._traverse(child, node.id, source_lines, depth + 1)
    
    def _build_call_relationships(self):
        """构建函数调用关系"""
        # 找到所有函数定义和函数调用
        function_nodes = {n.name: n for n in self.nodes.values() 
                         if n.type == NodeType.FUNCTION and n.name}
        
        for node in self.nodes.values():
            if node.type == NodeType.CALL and node.name:
                # 检查是否调用已定义的函数
                if node.name in function_nodes:
                    target_node = function_nodes[node.name]
                    edge = self._create_edge(
                        node.id, target_node.id, "call", node.name
                    )
                    self.edges.append(edge)
    
    def _build_import_relationships(self):
        """构建导入关系"""
        # 找到所有导入和使用
        import_nodes = {}  # module_name -> node_id
        
        for node in self.nodes.values():
            if node.type == NodeType.IMPORT:
                if node.attributes.get('names'):
                    for name, alias in node.attributes['names']:
                        import_nodes[alias or name] = node.id
        
        # 检查名称节点是否使用了导入
        for node in self.nodes.values():
            if node.type == NodeType.NAME and node.name in import_nodes:
                edge = self._create_edge(
                    node.id, import_nodes[node.name], "import-usage", node.name
                )
                self.edges.append(edge)
    
    def _count_node_types(self) -> Dict[str, int]:
        """统计各类型节点数量"""
        counts = {}
        for node in self.nodes.values():
            counts[node.type.value] = counts.get(node.type.value, 0) + 1
        return counts
    
    def get_node_by_lineno(self, lineno: int) -> Optional[ASTNode]:
        """根据行号获取节点"""
        for node in self.nodes.values():
            if node.lineno == lineno:
                return node
        return None
    
    def get_function_nodes(self) -> List[ASTNode]:
        """获取所有函数节点"""
        return [n for n in self.nodes.values() if n.type == NodeType.FUNCTION]
    
    def get_class_nodes(self) -> List[ASTNode]:
        """获取所有类节点"""
        return [n for n in self.nodes.values() if n.type == NodeType.CLASS]
