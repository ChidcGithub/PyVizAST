"""
AST Parser - Parse Python source code into visualizable graph structure
Supports performance optimization mode for large codebases
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
    """Python AST Parser - Supports performance optimization mode"""
    
    # Mapping of node types to colors, shapes, and icons/descriptions
    NODE_STYLES = {
        # Structural nodes
        NodeType.MODULE: {"color": "#ffffff", "shape": "hexagon", "size": 30, "icon": "📦", "description": "Module"},
        NodeType.FUNCTION: {"color": "#ffffff", "shape": "roundrectangle", "size": 25, "icon": "ƒ", "description": "Function"},
        NodeType.CLASS: {"color": "#e0e0e0", "shape": "roundrectangle", "size": 28, "icon": "C", "description": "Class"},
        
        # Control flow
        NodeType.IF: {"color": "#a0a0a0", "shape": "diamond", "size": 20, "icon": "?", "description": "Conditional"},
        NodeType.FOR: {"color": "#a0a0a0", "shape": "diamond", "size": 20, "icon": "⟳", "description": "For Loop"},
        NodeType.WHILE: {"color": "#a0a0a0", "shape": "diamond", "size": 20, "icon": "↻", "description": "While Loop"},
        NodeType.TRY: {"color": "#909090", "shape": "diamond", "size": 22, "icon": "⚠", "description": "Exception Handler"},
        NodeType.WITH: {"color": "#909090", "shape": "diamond", "size": 20, "icon": "▶", "description": "Context Manager"},
        
        # Expressions
        NodeType.CALL: {"color": "#707070", "shape": "circle", "size": 15, "icon": "()", "description": "Function Call"},
        NodeType.BINARY_OP: {"color": "#606060", "shape": "circle", "size": 12, "icon": "+", "description": "Binary Operation"},
        NodeType.COMPARE: {"color": "#606060", "shape": "circle", "size": 12, "icon": "≡", "description": "Comparison"},
        NodeType.LAMBDA: {"color": "#d0d0d0", "shape": "ellipse", "size": 18, "icon": "λ", "description": "Lambda Expression"},
        
        # Data structures
        NodeType.LIST: {"color": "#808080", "shape": "rectangle", "size": 15, "icon": "[]", "description": "List"},
        NodeType.DICT: {"color": "#808080", "shape": "rectangle", "size": 15, "icon": "{}", "description": "Dictionary"},
        NodeType.SET: {"color": "#808080", "shape": "rectangle", "size": 15, "icon": "∅", "description": "Set"},
        NodeType.TUPLE: {"color": "#808080", "shape": "rectangle", "size": 15, "icon": "()", "description": "Tuple"},
        
        # Variables
        NodeType.ASSIGN: {"color": "#505050", "shape": "circle", "size": 14, "icon": "=", "description": "Assignment"},
        NodeType.NAME: {"color": "#404040", "shape": "circle", "size": 10, "icon": "x", "description": "Variable Name"},
        
        # Other
        NodeType.IMPORT: {"color": "#909090", "shape": "parallelogram", "size": 16, "icon": "↓", "description": "Import"},
        NodeType.RETURN: {"color": "#707070", "shape": "triangle", "size": 14, "icon": "←", "description": "Return"},
        NodeType.YIELD: {"color": "#707070", "shape": "triangle", "size": 14, "icon": "→", "description": "Yield"},
        NodeType.OTHER: {"color": "#404040", "shape": "circle", "size": 10, "icon": "•", "description": "Other"},
    }
    
    def __init__(self, max_nodes: int = 2000, simplified: bool = False):
        """
        Initialize the parser
        
        Args:
            max_nodes: Maximum number of nodes allowed
            simplified: Whether to use simplified mode (skip secondary nodes)
        """
        self.nodes: Dict[str, ASTNode] = {}
        self.edges: List[ASTEdge] = []
        self.node_counter: Dict[str, int] = {}
        self.max_nodes = max_nodes
        self.simplified = simplified
        self._node_count = 0
        self._skipped_count = 0
    
    def _generate_id(self, node_type: str) -> str:
        """Generate unique node ID"""
        self.node_counter[node_type] = self.node_counter.get(node_type, 0) + 1
        return f"{node_type}_{self.node_counter[node_type]}"
    
    def _get_node_type(self, ast_node: ast.AST) -> NodeType:
        """Map AST node type to NodeType enum"""
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
        """Get node name"""
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
        """Get full name of attribute access"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr
    
    def _create_ast_node(self, ast_node: ast.AST, parent_id: Optional[str] = None) -> ASTNode:
        """Create ASTNode object"""
        node_type = self._get_node_type(ast_node)
        style = self.NODE_STYLES.get(node_type, self.NODE_STYLES[NodeType.OTHER])
        
        node_id = self._generate_id(node_type.value)
        name = self._get_node_name(ast_node)
        
        # Get source code position
        lineno = getattr(ast_node, 'lineno', None)
        col_offset = getattr(ast_node, 'col_offset', None)
        end_lineno = getattr(ast_node, 'end_lineno', None)
        end_col_offset = getattr(ast_node, 'end_col_offset', None)
        
        # Get docstring
        docstring = ast.get_docstring(ast_node) if isinstance(
            ast_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ) else None
        
        # Extract additional attributes
        attributes = self._extract_attributes(ast_node)
        
        # Generate detailed label (for learning mode)
        detailed_label = self._generate_detailed_label(ast_node, node_type, name, attributes)
        
        # Generate node explanation (for learning mode)
        explanation = self._generate_node_explanation(ast_node, node_type, name, attributes)
        
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
            attributes=attributes,
            # Additional fields
            icon=style.get("icon", "•"),
            description=style.get("description", ""),
            detailed_label=detailed_label,
            explanation=explanation
        )
    
    def _generate_detailed_label(self, ast_node: ast.AST, node_type: NodeType, 
                                  name: Optional[str], attributes: Dict[str, Any]) -> str:
        """Generate detailed node label for better understanding"""
        type_desc = self.NODE_STYLES.get(node_type, {}).get("description", node_type.value)
        
        if node_type == NodeType.FUNCTION:
            args = attributes.get('args', [])
            args_str = ', '.join(args[:3]) + ('...' if len(args) > 3 else '')
            decorators = attributes.get('decorators', [])
            dec_str = '@' + ' @'.join(decorators) + ' ' if decorators else ''
            return f"{dec_str}def {name}({args_str})"
        
        elif node_type == NodeType.CLASS:
            bases = attributes.get('bases', [])
            bases_str = '(' + ', '.join(bases) + ')' if bases else ''
            decorators = attributes.get('decorators', [])
            dec_str = '@' + ' @'.join(decorators) + ' ' if decorators else ''
            return f"{dec_str}class {name}{bases_str}"
        
        elif node_type == NodeType.FOR:
            target = attributes.get('target', 'item')
            return f"for {target} in ..."
        
        elif node_type == NodeType.WHILE:
            return "while ..."
        
        elif node_type == NodeType.IF:
            return "if ..."
        
        elif node_type == NodeType.CALL:
            args_count = attributes.get('args_count', 0)
            kwargs = attributes.get('kwargs', [])
            params = []
            if args_count > 0:
                params.append(f"{args_count} args")
            if kwargs:
                params.append(', '.join(kwargs[:2]) + ('...' if len(kwargs) > 2 else ''))
            params_str = ', '.join(params) if params else ''
            return f"{name}({params_str})" if name else "call()"
        
        elif node_type == NodeType.ASSIGN:
            return f"{name} = ..." if name else "= assignment"
        
        elif node_type == NodeType.IMPORT:
            names = attributes.get('names', [])
            if names:
                import_names = [n[0] if n[1] is None else f"{n[0]} as {n[1]}" for n in names[:3]]
                return f"import {', '.join(import_names)}" + ('...' if len(names) > 3 else '')
            return "import ..."
        
        elif node_type == NodeType.RETURN:
            return "return ..."
        
        elif node_type == NodeType.LAMBDA:
            return "λ: ..."
        
        elif node_type == NodeType.BINARY_OP:
            op = attributes.get('operator', '?')
            return f"... {op} ..."
        
        elif node_type == NodeType.COMPARE:
            ops = attributes.get('operators', [])
            if ops:
                return f"... {ops[0]} ..."
            return "... ? ..."
        
        elif node_type == NodeType.LIST:
            return "[...]"
        
        elif node_type == NodeType.DICT:
            return "{...}"
        
        elif node_type == NodeType.SET:
            return "{...}"
        
        elif node_type == NodeType.TUPLE:
            return "(...)"
        
        elif node_type == NodeType.NAME:
            return f"variable: {name}" if name else "variable"
        
        elif node_type == NodeType.MODULE:
            return "📦 Module"
        
        elif node_type == NodeType.TRY:
            return "try/except"
        
        elif node_type == NodeType.WITH:
            return "with ..."
        
        elif node_type == NodeType.YIELD:
            return "yield ..."
        
        return f"{type_desc}: {name}" if name else type_desc
    
    def _generate_node_explanation(self, ast_node: ast.AST, node_type: NodeType,
                                    name: Optional[str], attributes: Dict[str, Any]) -> str:
        """Generate node explanation for learning mode"""
        explanations = {
            NodeType.FUNCTION: lambda: (
                f"Function Definition: Defines a function named '{name}'.\n"
                f"Parameters: {', '.join(attributes.get('args', [])) or 'none'}\n"
                f"Decorators: {', '.join(attributes.get('decorators', [])) or 'none'}\n"
                f"Tip: Functions are the basic units of code organization and can be called to perform specific tasks."
            ),
            NodeType.CLASS: lambda: (
                f"Class Definition: Defines a class named '{name}'.\n"
                f"Inherits from: {', '.join(attributes.get('bases', [])) or 'no base class'}\n"
                f"Tip: Classes are the core of object-oriented programming, encapsulating data and methods."
            ),
            NodeType.FOR: lambda: (
                f"For Loop: Iterates over an iterable object.\n"
                f"Loop Variable: {attributes.get('target', 'item')}\n"
                f"Tip: for loops are used to iterate over sequences (lists, tuples, strings) or other iterable objects."
            ),
            NodeType.WHILE: lambda: (
                f"While Loop: Repeatedly executes while condition is true.\n"
                f"Tip: while loops continue until the condition becomes false. Be careful to avoid infinite loops!"
            ),
            NodeType.IF: lambda: (
                f"Conditional: Executes different code branches based on condition.\n"
                f"{'Has else branch' if attributes.get('has_else') else 'No else branch'}\n"
                f"Tip: if statements control the program's execution flow."
            ),
            NodeType.CALL: lambda: (
                f"Function Call: Calls the '{name}' function.\n"
                f"Argument Count: {attributes.get('args_count', 0)}\n"
                f"Keyword Arguments: {', '.join(attributes.get('kwargs', [])) or 'none'}\n"
                f"Tip: Function calls execute the code in the function body."
            ),
            NodeType.ASSIGN: lambda: (
                f"Assignment: Binds a value to a variable name.\n"
                f"Variable: {name}\n"
                f"Tip: Assignment creates a reference between a variable name and a value."
            ),
            NodeType.IMPORT: lambda: (
                f"Import Statement: Imports an external module.\n"
                f"Module: {name}\n"
                f"Tip: import statements allow using functions and classes defined in other modules."
            ),
            NodeType.RETURN: lambda: (
                f"Return Statement: Returns a value from a function.\n"
                f"Tip: return statements end function execution and return a result to the caller."
            ),
            NodeType.LAMBDA: lambda: (
                f"Lambda Expression: Anonymous function.\n"
                f"Tip: lambda creates simple single-line functions, often used for callbacks and higher-order functions."
            ),
            NodeType.LIST: lambda: (
                f"List: Python's ordered mutable sequence.\n"
                f"Tip: Lists use square brackets [] and can contain elements of any type."
            ),
            NodeType.DICT: lambda: (
                f"Dictionary: Python's key-value mapping.\n"
                f"Tip: Dictionaries use curly braces {{}} and allow fast lookup by key."
            ),
            NodeType.SET: lambda: (
                f"Set: Unordered collection of unique elements.\n"
                f"Tip: Sets are used for deduplication and set operations (union, intersection, difference)."
            ),
            NodeType.TUPLE: lambda: (
                f"Tuple: Immutable ordered sequence.\n"
                f"Tip: Tuples use parentheses () and cannot be modified after creation."
            ),
            NodeType.TRY: lambda: (
                f"Exception Handler: Catches and handles runtime errors.\n"
                f"Tip: try/except is used to gracefully handle potential errors."
            ),
            NodeType.WITH: lambda: (
                f"Context Manager: Automatically manages resources.\n"
                f"Tip: with statements ensure resources (like files) are properly closed, even if exceptions occur."
            ),
            NodeType.YIELD: lambda: (
                f"Generator: Yields values from a generator function.\n"
                f"Tip: yield makes a function a generator, producing values one at a time to save memory."
            ),
            NodeType.BINARY_OP: lambda: (
                f"Binary Operation: Performs arithmetic or bitwise operations.\n"
                f"Operator: {attributes.get('operator', '?')}\n"
                f"Tip: Binary operators include +, -, *, /, //, %, **, etc."
            ),
            NodeType.COMPARE: lambda: (
                f"Comparison: Compares two values.\n"
                f"Operators: {', '.join(attributes.get('operators', ['?']))}\n"
                f"Tip: Comparison operators include ==, !=, <, >, <=, >=, in, is, etc."
            ),
            NodeType.NAME: lambda: (
                f"Variable Name: References or defines a variable.\n"
                f"Name: {name}\n"
                f"Tip: Variable names should be descriptive and follow naming conventions."
            ),
            NodeType.MODULE: lambda: (
                f"Module: Python code file.\n"
                f"Tip: Modules are the basic unit of code organization and can contain functions, classes, and variables."
            ),
        }
        
        generator = explanations.get(node_type)
        return generator() if generator else f"{node_type.value}: {name or 'unnamed'}"
    
    def _extract_attributes(self, ast_node: ast.AST) -> Dict[str, Any]:
        """Extract additional node attributes"""
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
        """Get decorator name"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_node_name(decorator) or "unknown"
        elif isinstance(decorator, ast.Attribute):
            return self._get_attribute_name(decorator)
        return "unknown"
    
    def _get_base_name(self, base: ast.AST) -> str:
        """Get base class name"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return self._get_attribute_name(base)
        return "unknown"
    
    def _get_target_name(self, target: ast.AST) -> str:
        """Get loop target name"""
        if isinstance(target, ast.Name):
            return target.id
        return "unknown"
    
    def _create_edge(self, source_id: str, target_id: str, edge_type: str, label: Optional[str] = None) -> ASTEdge:
        """Create an edge"""
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
        Parse Python code and generate AST graph
        
        Args:
            code: Python source code string
            source_lines: Source code line list (optional, for extracting code snippets)
        
        Returns:
            ASTGraph: Visualizable graph structure
        """
        # Reset state
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
        
        # Traverse AST and build graph
        self._traverse(tree, None, source_lines)
        
        # Build call relationships
        self._build_call_relationships()
        
        # Build import relationships
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
        """Determine if node should be skipped (for performance optimization)"""
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
        """Recursively traverse AST"""
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
        
        # Create current node
        node = self._create_ast_node(ast_node, parent_id)
        
        # Extract source code snippet
        if node.lineno and node.end_lineno:
            start = node.lineno - 1
            end = min(node.end_lineno, len(source_lines))
            node.source_code = "\n".join(source_lines[start:end])
        
        self.nodes[node.id] = node
        
        # Add parent-child edge
        if parent_id:
            edge = self._create_edge(parent_id, node.id, "parent-child")
            self.edges.append(edge)
            # Update parent's children list
            if parent_id in self.nodes:
                self.nodes[parent_id].children.append(node.id)
        
        # Traverse child nodes
        for child in ast.iter_child_nodes(ast_node):
            self._traverse(child, node.id, source_lines, depth + 1)
    
    def _build_call_relationships(self):
        """Build function call relationships"""
        # Find all function definitions and calls
        function_nodes = {n.name: n for n in self.nodes.values() 
                         if n.type == NodeType.FUNCTION and n.name}
        
        for node in self.nodes.values():
            if node.type == NodeType.CALL and node.name:
                # Check if calling a defined function
                if node.name in function_nodes:
                    target_node = function_nodes[node.name]
                    edge = self._create_edge(
                        node.id, target_node.id, "call", node.name
                    )
                    self.edges.append(edge)
    
    def _build_import_relationships(self):
        """Build import relationships"""
        # Find all imports and usages
        import_nodes = {}  # module_name -> node_id
        
        for node in self.nodes.values():
            if node.type == NodeType.IMPORT:
                if node.attributes.get('names'):
                    for name, alias in node.attributes['names']:
                        import_nodes[alias or name] = node.id
        
        # Check if name nodes use imports
        for node in self.nodes.values():
            if node.type == NodeType.NAME and node.name in import_nodes:
                edge = self._create_edge(
                    node.id, import_nodes[node.name], "import-usage", node.name
                )
                self.edges.append(edge)
    
    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type"""
        counts = {}
        for node in self.nodes.values():
            counts[node.type.value] = counts.get(node.type.value, 0) + 1
        return counts
    
    def get_node_by_lineno(self, lineno: int) -> Optional[ASTNode]:
        """Get node by line number"""
        for node in self.nodes.values():
            if node.lineno == lineno:
                return node
        return None
    
    def get_function_nodes(self) -> List[ASTNode]:
        """Get all function nodes"""
        return [n for n in self.nodes.values() if n.type == NodeType.FUNCTION]
    
    def get_class_nodes(self) -> List[ASTNode]:
        """Get all class nodes"""
        return [n for n in self.nodes.values() if n.type == NodeType.CLASS]