"""
AST Parser - Parse Python source code into visualizable graph structure
Supports performance optimization mode for large codebases
Enhanced with code relationship analysis (inheritance, calls, decorators, variables)

@author: Chidc
@link: github.com/chidcGithub
"""
import ast
from typing import Dict, List, Optional, Any, Set, Tuple
from ..models.schemas import (
    ASTNode, ASTEdge, ASTGraph, NodeType, VariableInfo, CodeRelationship
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
    """Python AST Parser - Supports performance optimization mode and enhanced code analysis"""
    
    # Maximum depth for AST traversal
    MAX_DEPTH = 50
    
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
        NodeType.MATCH: {"color": "#a0a0a0", "shape": "diamond", "size": 22, "icon": "⬡", "description": "Match Statement"},
        
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
        self.relationships: List[CodeRelationship] = []
        self.node_counter: Dict[str, int] = {}
        self.max_nodes = max_nodes
        self.simplified = simplified
        self._node_count = 0
        self._skipped_count = 0
        self._lineno_index: Dict[int, List[str]] = {}
        
        # NEW: Enhanced tracking structures
        self._class_hierarchy: Dict[str, List[str]] = {}  # class_name -> [base_class_names]
        self._class_nodes: Dict[str, ASTNode] = {}  # class_name -> node
        self._function_nodes: Dict[str, ASTNode] = {}  # function_name -> node (per scope)
        self._import_map: Dict[str, str] = {}  # imported_name -> module
        self._scope_stack: List[str] = []  # stack of scope node IDs
        self._variable_scopes: Dict[str, Set[str]] = {}  # scope_id -> defined variables
        self._global_vars: Set[str] = set()
        self._nonlocal_vars: Dict[str, Set[str]] = {}  # scope_id -> nonlocal vars
    
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
        
        # Python 3.10+ match-case support
        if hasattr(ast, 'Match'):
            type_mapping[ast.Match] = NodeType.MATCH
        
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
            names = [n.name for n in ast_node.names if n.name]
            return ", ".join(names) if names else None
        elif isinstance(ast_node, ast.Assign):
            targets = []
            for t in ast_node.targets:
                if isinstance(t, ast.Name) and t.id:
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
    
    def _get_decorator_names(self, decorator_list: List[ast.AST]) -> List[str]:
        """Get list of decorator names"""
        decorators = []
        for dec in decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(self._get_attribute_name(dec))
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(self._get_attribute_name(dec.func))
        return decorators
    
    def _get_base_class_names(self, bases: List[ast.AST]) -> List[str]:
        """Get list of base class names"""
        base_names = []
        for base in bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(self._get_attribute_name(base))
        return base_names
    
    def _create_ast_node(self, ast_node: ast.AST, parent_id: Optional[str] = None) -> ASTNode:
        """Create ASTNode object with enhanced information"""
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
        
        # Generate detailed label and explanation
        detailed_label = self._generate_detailed_label(ast_node, node_type, name, attributes)
        explanation = self._generate_node_explanation(ast_node, node_type, name, attributes)
        
        # Calculate code metrics
        line_count = 0
        indent_level = col_offset // 4 if col_offset else 0
        
        if lineno and end_lineno:
            line_count = end_lineno - lineno + 1
        
        # Extract extended information
        return_type = attributes.get('return_type')
        parameter_types = attributes.get('parameter_types', {})
        default_values = attributes.get('default_values', {})
        is_generator = attributes.get('is_generator', False)
        is_async = attributes.get('is_async', False)
        
        # Class specific
        method_count = attributes.get('method_count', 0)
        attribute_count = attributes.get('attribute_count', 0)
        
        # Function specific - count local variables
        local_var_count = 0
        if isinstance(ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_var_count = self._count_local_variables(ast_node)
        
        # Detect patterns
        patterns = self._detect_patterns(ast_node)
        
        # Extract dependencies
        deps = self._extract_dependencies(ast_node)
        imports_used = deps['imports_used']
        functions_called = deps['functions_called']
        
        # ===== NEW: Extract enhanced relationships =====
        decorators = []
        base_classes = []
        methods = []
        
        if isinstance(ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = self._get_decorator_names(ast_node.decorator_list)
        elif isinstance(ast_node, ast.ClassDef):
            decorators = self._get_decorator_names(ast_node.decorator_list)
            base_classes = self._get_base_class_names(ast_node.bases)
            # Extract method names
            for item in ast_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
        
        # Branch and loop counts
        branch_count = self._count_branches(ast_node)
        loop_count = self._count_loops(ast_node)
        exception_handlers = self._count_exception_handlers(ast_node)
        
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
            icon=style.get("icon", "•"),
            description=style.get("description", ""),
            detailed_label=detailed_label,
            explanation=explanation,
            line_count=line_count,
            indent_level=indent_level,
            return_type=return_type,
            parameter_types=parameter_types,
            default_values=default_values,
            method_count=method_count,
            attribute_count=attribute_count,
            local_var_count=local_var_count,
            has_try_except=patterns['has_try_except'],
            has_loop=patterns['has_loop'],
            has_recursion=patterns['has_recursion'],
            is_generator=is_generator,
            is_async=is_async,
            imports_used=imports_used,
            functions_called=functions_called,
            # NEW fields
            decorators=decorators,
            base_classes=base_classes,
            methods=methods,
            branch_count=branch_count,
            loop_count=loop_count,
            exception_handlers=exception_handlers,
        )
    
    def _count_branches(self, node: ast.AST) -> int:
        """Count number of if/elif/else branches"""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                count += 1
                # Count elif branches
                if child.orelse and len(child.orelse) == 1 and isinstance(child.orelse[0], ast.If):
                    count += self._count_branches(child.orelse[0])
        return count
    
    def _count_loops(self, node: ast.AST) -> int:
        """Count number of loops"""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                count += 1
        return count
    
    def _count_exception_handlers(self, node: ast.AST) -> int:
        """Count number of except handlers"""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                count += len(child.handlers)
        return count
    
    def _generate_detailed_label(self, ast_node: ast.AST, node_type: NodeType, 
                                  name: Optional[str], attributes: Dict[str, Any]) -> str:
        """Generate detailed node label for better understanding"""
        type_desc = self.NODE_STYLES.get(node_type, {}).get("description", node_type.value)
        
        if node_type == NodeType.FUNCTION:
            args = [a for a in attributes.get('args', []) if a]
            args_str = ', '.join(args[:3]) + ('...' if len(args) > 3 else '')
            decorators = [d for d in attributes.get('decorators', []) if d]
            dec_str = '@' + ' @'.join(decorators) + ' ' if decorators else ''
            return f"{dec_str}def {name}({args_str})"
        
        elif node_type == NodeType.CLASS:
            bases = [b for b in attributes.get('bases', []) if b]
            bases_str = '(' + ', '.join(bases) + ')' if bases else ''
            decorators = [d for d in attributes.get('decorators', []) if d]
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
            kwargs = [k for k in kwargs if k is not None]
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
                import_names = []
                for n in names[:3]:
                    if n[0]:
                        import_names.append(n[0] if n[1] is None else f"{n[0]} as {n[1]}")
                return f"import {', '.join(import_names)}" + ('...' if len(names) > 3 else '') if import_names else "import ..."
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
                f"Parameters: {', '.join([a for a in attributes.get('args', []) if a]) or 'none'}\n"
                f"Decorators: {', '.join([d for d in attributes.get('decorators', []) if d]) or 'none'}\n"
                f"Tip: Functions are the basic units of code organization and can be called to perform specific tasks."
            ),
            NodeType.CLASS: lambda: (
                f"Class Definition: Defines a class named '{name}'.\n"
                f"Inherits from: {', '.join([b for b in attributes.get('bases', []) if b]) or 'no base class'}\n"
                f"Tip: Classes are the core of object-oriented programming, encapsulating data and methods."
            ),
            NodeType.FOR: lambda: (
                "For Loop: Iterates over an iterable object.\n"
                f"Loop Variable: {attributes.get('target', 'item')}\n"
                "Tip: for loops are used to iterate over sequences (lists, tuples, strings) or other iterable objects."
            ),
            NodeType.WHILE: lambda: (
                "While Loop: Repeatedly executes while condition is true.\n"
                "Tip: while loops continue until the condition becomes false. Be careful to avoid infinite loops!"
            ),
            NodeType.IF: lambda: (
                "Conditional: Executes different code branches based on condition.\n"
                f"{'Has else branch' if attributes.get('has_else') else 'No else branch'}\n"
                "Tip: if statements control the program's execution flow."
            ),
            NodeType.CALL: lambda: (
                f"Function Call: Calls the '{name}' function.\n"
                f"Argument Count: {attributes.get('args_count', 0)}\n"
                f"Keyword Arguments: {', '.join([k for k in attributes.get('kwargs', []) if k]) or 'none'}\n"
                "Tip: Function calls execute the code in the function body."
            ),
            NodeType.ASSIGN: lambda: (
                f"Assignment: Binds a value to a variable name.\n"
                f"Variable: {name}\n"
                "Tip: Assignment creates a reference between a variable name and a value."
            ),
            NodeType.IMPORT: lambda: (
                f"Import Statement: Imports an external module.\n"
                f"Module: {name}\n"
                "Tip: import statements allow using functions and classes defined in other modules."
            ),
            NodeType.RETURN: lambda: (
                "Return Statement: Returns a value from a function.\n"
                "Tip: return statements end function execution and return a result to the caller."
            ),
            NodeType.LAMBDA: lambda: (
                "Lambda Expression: Anonymous function.\n"
                "Tip: lambda creates simple single-line functions, often used for callbacks and higher-order functions."
            ),
            NodeType.LIST: lambda: (
                "List: Python's ordered mutable sequence.\n"
                "Tip: Lists use square brackets [] and can contain elements of any type."
            ),
            NodeType.DICT: lambda: (
                "Dictionary: Python's key-value mapping.\n"
                "Tip: Dictionaries use curly braces {} and allow fast lookup by key."
            ),
            NodeType.SET: lambda: (
                "Set: Unordered collection of unique elements.\n"
                "Tip: Sets are used for deduplication and set operations (union, intersection, difference)."
            ),
            NodeType.TUPLE: lambda: (
                "Tuple: Immutable ordered sequence.\n"
                "Tip: Tuples use parentheses () and cannot be modified after creation."
            ),
            NodeType.TRY: lambda: (
                "Exception Handler: Catches and handles runtime errors.\n"
                "Tip: try/except is used to gracefully handle potential errors."
            ),
            NodeType.WITH: lambda: (
                "Context Manager: Automatically manages resources.\n"
                "Tip: with statements ensure resources (like files) are properly closed, even if exceptions occur."
            ),
            NodeType.YIELD: lambda: (
                "Generator: Yields values from a generator function.\n"
                "Tip: yield makes a function a generator, producing values one at a time to save memory."
            ),
            NodeType.BINARY_OP: lambda: (
                "Binary Operation: Performs arithmetic or bitwise operations.\n"
                f"Operator: {attributes.get('operator', '?')}\n"
                "Tip: Binary operators include +, -, *, /, //, %, **, etc."
            ),
            NodeType.COMPARE: lambda: (
                "Comparison: Compares two values.\n"
                f"Operators: {', '.join([o for o in attributes.get('operators', ['?']) if o])}\n"
                "Tip: Comparison operators include ==, !=, <, >, <=, >=, in, is, etc."
            ),
            NodeType.NAME: lambda: (
                f"Variable Name: References or defines a variable.\n"
                f"Name: {name}\n"
                "Tip: Variable names should be descriptive and follow naming conventions."
            ),
            NodeType.MODULE: lambda: (
                "Module: Python code file.\n"
                "Tip: Modules are the basic unit of code organization and can contain functions, classes, and variables."
            ),
        }
        
        generator = explanations.get(node_type)
        return generator() if generator else f"{node_type.value}: {name or 'unnamed'}"
    
    def _extract_attributes(self, ast_node: ast.AST) -> Dict[str, Any]:
        """Extract additional node attributes"""
        attrs = {}
        
        if isinstance(ast_node, ast.FunctionDef):
            attrs['args'] = [arg.arg for arg in ast_node.args.args]
            attrs['decorators'] = self._get_decorator_names(ast_node.decorator_list)
            attrs['is_async'] = isinstance(ast_node, ast.AsyncFunctionDef)
            
            if ast_node.returns:
                attrs['return_type'] = self._get_annotation_string(ast_node.returns)
            
            param_types = {}
            for arg in ast_node.args.args:
                if arg.annotation:
                    param_types[arg.arg] = self._get_annotation_string(arg.annotation)
            if param_types:
                attrs['parameter_types'] = param_types
            
            defaults = {}
            num_defaults = len(ast_node.args.defaults)
            num_args = len(ast_node.args.args)
            for i, default in enumerate(ast_node.args.defaults):
                arg_idx = num_args - num_defaults + i
                arg_name = ast_node.args.args[arg_idx].arg
                defaults[arg_name] = self._get_default_value_string(default)
            if defaults:
                attrs['default_values'] = defaults
            
            attrs['is_generator'] = self._contains_yield(ast_node)
        
        elif isinstance(ast_node, ast.ClassDef):
            attrs['bases'] = self._get_base_class_names(ast_node.bases)
            attrs['decorators'] = self._get_decorator_names(ast_node.decorator_list)
            
            method_count = 0
            attribute_count = 0
            for item in ast_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_count += 1
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attribute_count += 1
            attrs['method_count'] = method_count
            attrs['attribute_count'] = attribute_count
        
        elif isinstance(ast_node, ast.For):
            attrs['target'] = self._get_target_name(ast_node.target)
            attrs['is_async'] = isinstance(ast_node, ast.AsyncFor)
        
        elif isinstance(ast_node, ast.While):
            attrs['has_else'] = bool(ast_node.orelse)
        
        elif isinstance(ast_node, ast.If):
            attrs['has_else'] = bool(ast_node.orelse)
        
        elif isinstance(ast_node, ast.Call):
            attrs['args_count'] = len(ast_node.args)
            attrs['kwargs'] = [kw.arg if kw.arg is not None else "**kw.arg" for kw in ast_node.keywords]
        
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
    
    def _get_annotation_string(self, annotation: ast.AST) -> str:
        """Get type annotation as string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return repr(annotation.value)
        elif isinstance(annotation, ast.Attribute):
            return self._get_attribute_name(annotation)
        elif isinstance(annotation, ast.Subscript):
            value = self._get_annotation_string(annotation.value)
            slice_str = self._get_annotation_string(annotation.slice)
            return f"{value}[{slice_str}]"
        elif isinstance(annotation, ast.Tuple):
            elements = [self._get_annotation_string(el) for el in annotation.elts]
            return ', '.join([e for e in elements if e])
        return "Any"
    
    def _get_default_value_string(self, default: ast.AST) -> str:
        """Get default value as string representation"""
        try:
            return ast.unparse(default) if hasattr(ast, 'unparse') else repr(default)
        except Exception:
            return "..."
    
    def _contains_yield(self, node: ast.AST) -> bool:
        """Check if function contains yield statement (is a generator)"""
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
        return False
    
    def _count_local_variables(self, func_node: ast.FunctionDef) -> int:
        """Count local variables in a function"""
        local_vars = set()
        params = {arg.arg for arg in func_node.args.args}
        
        for child in ast.walk(func_node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                if child.id not in params and not child.id.startswith('_'):
                    local_vars.add(child.id)
        
        return len(local_vars)
    
    def _detect_patterns(self, node: ast.AST) -> Dict[str, bool]:
        """Detect code patterns in a node"""
        patterns = {
            'has_try_except': False,
            'has_loop': False,
            'has_recursion': False
        }
        
        func_name = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = node.name
        
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                patterns['has_try_except'] = True
            elif isinstance(child, (ast.For, ast.While)):
                patterns['has_loop'] = True
            elif isinstance(child, ast.Call) and func_name:
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    patterns['has_recursion'] = True
        
        return patterns
    
    def _extract_dependencies(self, node: ast.AST) -> Dict[str, List[str]]:
        """Extract imports used and functions called in a scope"""
        imports_used = set()
        functions_called = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                imports_used.add(child.id)
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    functions_called.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    functions_called.add(child.func.attr)
        
        return {
            'imports_used': list(imports_used),
            'functions_called': list(functions_called)
        }
    
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
    
    def _add_relationship(self, source_id: str, target_id: str, rel_type: str, details: Optional[str] = None):
        """Add a code relationship"""
        self.relationships.append(CodeRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            details=details
        ))
    
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
        self.node_counter = {}
        self._node_count = 0
        self._skipped_count = 0
        self._lineno_index = {}
        self._class_hierarchy = {}
        self._class_nodes = {}
        self._function_nodes = {}
        self._import_map = {}
        self._scope_stack = []
        self._variable_scopes = {}
        self._global_vars = set()
        self._nonlocal_vars = {}
        
        if tree is not None:
            ast_tree = tree
        else:
            try:
                ast_tree = ast.parse(code)
            except SyntaxError as e:
                raise ValueError(f"Syntax error in code: {e}")
        
        if source_lines is None:
            source_lines = code.splitlines()
        
        # Traverse AST and build graph
        self._traverse(ast_tree, None, source_lines)
        
        # Build enhanced relationships
        self._build_inheritance_relationships()
        self._build_call_relationships()
        self._build_import_relationships()
        self._build_decorator_relationships()
        self._analyze_variable_scopes()
        
        # Post-process: calculate additional metrics
        self._post_process_nodes()
        
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
        import logging
        logger = logging.getLogger(__name__)
        
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
            node = self._create_ast_node(ast_node, parent_id)
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
        
        # Track class and function nodes for relationship building
        if node.type == NodeType.CLASS and node.name:
            self._class_nodes[node.name] = node
            self._class_hierarchy[node.name] = node.base_classes
        elif node.type == NodeType.FUNCTION and node.name:
            # Store with scope context
            scope_key = f"{self._scope_stack[-1]}.{node.name}" if self._scope_stack else node.name
            self._function_nodes[scope_key] = node
        
        # Track imports
        if node.type == NodeType.IMPORT and node.attributes.get('names'):
            for name, alias in node.attributes['names']:
                self._import_map[alias or name] = node.attributes.get('module', name) or name
        
        # Build line number index
        if node.lineno:
            if node.lineno not in self._lineno_index:
                self._lineno_index[node.lineno] = []
            self._lineno_index[node.lineno].append(node.id)
        
        # Add parent-child edge
        if parent_id:
            edge = self._create_edge(parent_id, node.id, "parent-child")
            self.edges.append(edge)
            if parent_id in self.nodes:
                self.nodes[parent_id].children.append(node.id)
        
        # Update scope info
        if node.type in (NodeType.FUNCTION, NodeType.CLASS):
            self._scope_stack.append(node.id)
            node.enclosing_scope_id = self._scope_stack[-2] if len(self._scope_stack) > 1 else None
            node.scope_level = len(self._scope_stack) - 1
        
        # Traverse child nodes
        for child in ast.iter_child_nodes(ast_node):
            self._traverse(child, node.id, source_lines, depth + 1)
        
        # Pop scope
        if node.type in (NodeType.FUNCTION, NodeType.CLASS):
            if self._scope_stack and self._scope_stack[-1] == node.id:
                self._scope_stack.pop()
    
    def _build_inheritance_relationships(self):
        """Build class inheritance relationships"""
        for class_name, base_names in self._class_hierarchy.items():
            class_node = self._class_nodes.get(class_name)
            if not class_node:
                continue
            
            for base_name in base_names:
                base_node = self._class_nodes.get(base_name)
                if base_node:
                    # Add edge for inheritance
                    edge = self._create_edge(class_node.id, base_node.id, "inheritance", f"extends {base_name}")
                    self.edges.append(edge)
                    
                    # Add relationship
                    self._add_relationship(class_node.id, base_node.id, "inheritance", f"{class_name} extends {base_name}")
                    
                    # Track derived classes
                    if base_name not in base_node.derived_classes:
                        base_node.derived_classes.append(class_name)
                    
                    # Track inherited methods
                    for method in base_node.methods:
                        if method not in class_node.inherited_methods:
                            class_node.inherited_methods.append(method)
                    
                    # Check for overridden methods
                    for method in class_node.methods:
                        if method in base_node.methods and method not in class_node.overridden_methods:
                            class_node.overridden_methods.append(method)
            
            # Calculate inheritance depth
            class_node.inheritance_depth = self._calculate_inheritance_depth(class_name)
    
    def _calculate_inheritance_depth(self, class_name: str, visited: Optional[Set[str]] = None) -> int:
        """Calculate inheritance depth for a class"""
        if visited is None:
            visited = set()
        
        if class_name in visited:
            return 0
        visited.add(class_name)
        
        base_names = self._class_hierarchy.get(class_name, [])
        if not base_names:
            return 0
        
        max_depth = 0
        for base_name in base_names:
            if base_name in self._class_hierarchy:
                depth = self._calculate_inheritance_depth(base_name, visited)
                max_depth = max(max_depth, depth + 1)
            else:
                max_depth = max(max_depth, 1)
        
        return max_depth
    
    def _build_call_relationships(self):
        """Build function call relationships"""
        # Map function names to nodes (considering scope)
        function_map: Dict[str, ASTNode] = {}
        for node in self.nodes.values():
            if node.type == NodeType.FUNCTION and node.name:
                function_map[node.name] = node
        
        # Track call counts
        call_counts: Dict[str, int] = {}
        
        for node in self.nodes.values():
            if node.type == NodeType.CALL and node.name:
                # Check if calling a defined function
                if node.name in function_map:
                    target_node = function_map[node.name]
                    edge = self._create_edge(node.id, target_node.id, "call", node.name)
                    self.edges.append(edge)
                    
                    # Track caller/callee relationships
                    if target_node.id not in node.calls_to:
                        node.calls_to.append(target_node.id)
                    if node.id not in target_node.called_by:
                        target_node.called_by.append(node.id)
                    
                    # Count calls
                    call_counts[node.name] = call_counts.get(node.name, 0) + 1
        
        # Update is_called_count for functions
        for func_name, count in call_counts.items():
            if func_name in function_map:
                function_map[func_name].is_called_count = count
    
    def _build_import_relationships(self):
        """Build import relationships"""
        import_nodes: Dict[str, ASTNode] = {}
        
        for node in self.nodes.values():
            if node.type == NodeType.IMPORT:
                if node.attributes.get('names'):
                    for name, alias in node.attributes['names']:
                        key = alias or name
                        if key:
                            import_nodes[key] = node
                            node.imported_symbols[key] = node.attributes.get('module', name) or name
                            if alias:
                                node.import_aliases[alias] = name
        
        # Check if name nodes use imports
        for node in self.nodes.values():
            if node.type == NodeType.NAME and node.name in import_nodes:
                import_node = import_nodes[node.name]
                edge = self._create_edge(node.id, import_node.id, "import-usage", node.name)
                self.edges.append(edge)
    
    def _build_decorator_relationships(self):
        """Build decorator relationships"""
        decorator_functions: Dict[str, ASTNode] = {}
        for node in self.nodes.values():
            if node.type == NodeType.FUNCTION and node.name:
                decorator_functions[node.name] = node
        
        for node in self.nodes.values():
            if node.decorators:
                for dec_name in node.decorators:
                    if dec_name in decorator_functions:
                        dec_node = decorator_functions[dec_name]
                        edge = self._create_edge(node.id, dec_node.id, "decorator", f"@{dec_name}")
                        self.edges.append(edge)
                        
                        # Track decorated_by
                        if dec_node.id not in node.decorated_by:
                            node.decorated_by.append(dec_node.id)
                        
                        # Track decorates
                        if node.id not in dec_node.decorates:
                            dec_node.decorates.append(node.id)
    
    def _analyze_variable_scopes(self):
        """Analyze variable definitions and usages across scopes"""
        # Find all variable definitions
        var_definitions: Dict[str, List[Tuple[str, int, Optional[str]]]] = {}  # var_name -> [(node_id, lineno, scope)]
        
        for node in self.nodes.values():
            if node.type == NodeType.ASSIGN and node.name:
                scope = node.scope_name or "global"
                for var_name in node.name.split(" = "):
                    var_name = var_name.strip()
                    if var_name:
                        if var_name not in var_definitions:
                            var_definitions[var_name] = []
                        var_definitions[var_name].append((node.id, node.lineno or 0, scope))
                        
                        # Add to variables_defined
                        node.variables_defined.append(VariableInfo(
                            name=var_name,
                            lineno=node.lineno,
                            is_definition=True,
                            scope=scope
                        ))
        
        # Find variable usages
        for node in self.nodes.values():
            if node.type == NodeType.NAME and node.name:
                if node.name in var_definitions:
                    # Find the definition in the closest scope
                    definitions = var_definitions[node.name]
                    for def_node_id, def_lineno, def_scope in definitions:
                        # Add usage info
                        node.variables_used.append(VariableInfo(
                            name=node.name,
                            lineno=node.lineno,
                            is_usage=True,
                            scope=def_scope
                        ))
                        node.used_in.append(def_node_id)
    
    def _post_process_nodes(self):
        """Post-process nodes to calculate additional metrics"""
        node_map = self.nodes
        
        # Count function calls for each function
        call_counts = {}
        for node in node_map.values():
            if node.type == NodeType.CALL and node.name:
                call_counts[node.name] = call_counts.get(node.name, 0) + 1
        
        # Calculate depth and total descendants
        def get_depth(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            node = node_map.get(node_id)
            if not node or not node.parent:
                return 0
            return 1 + get_depth(node.parent, visited)
        
        def count_descendants(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            node = node_map.get(node_id)
            if not node or not node.children:
                return 0
            count = len(node.children)
            for child_id in node.children:
                count += count_descendants(child_id, visited.copy())
            return count
        
        def get_scope_name(node_id: str) -> Optional[str]:
            node = node_map.get(node_id)
            if not node or not node.parent:
                return None
            
            parent = node_map.get(node.parent)
            if not parent:
                return None
            
            if parent.type in (NodeType.FUNCTION, NodeType.CLASS) and parent.name:
                return parent.name
            
            return get_scope_name(node.parent)
        
        def get_nested_scopes(node_id: str) -> List[str]:
            """Get IDs of nested functions/classes"""
            nested = []
            node = node_map.get(node_id)
            if not node:
                return nested
            
            def collect_nested(nid: str, depth: int):
                if depth > 5:  # Limit recursion
                    return
                n = node_map.get(nid)
                if not n:
                    return
                for child_id in n.children:
                    child = node_map.get(child_id)
                    if child and child.type in (NodeType.FUNCTION, NodeType.CLASS):
                        nested.append(child_id)
                    collect_nested(child_id, depth + 1)
            
            collect_nested(node_id, 0)
            return nested
        
        # Update each node
        for node_id, node in node_map.items():
            node.child_count = len(node.children)
            node.total_descendants = count_descendants(node_id, set())
            node.depth = get_depth(node_id, set())
            node.scope_name = get_scope_name(node_id)
            
            if node.type == NodeType.FUNCTION and node.name:
                node.is_called_count = call_counts.get(node.name, 0)
            
            if node.source_code:
                node.char_count = len(node.source_code)
            
            # Get nested scopes
            node.nested_scopes = get_nested_scopes(node_id)
    
    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type"""
        counts = {}
        for node in self.nodes.values():
            counts[node.type.value] = counts.get(node.type.value, 0) + 1
        return counts
    
    def get_node_by_lineno(self, lineno: int) -> Optional[ASTNode]:
        """Get node by line number"""
        if hasattr(self, '_lineno_index') and lineno in self._lineno_index:
            node_ids = self._lineno_index[lineno]
            if node_ids:
                return self.nodes.get(node_ids[0])
        for node in self.nodes.values():
            if node.lineno == lineno:
                return node
        return None
    
    def get_nodes_by_lineno(self, lineno: int) -> List[ASTNode]:
        """Get all nodes by line number"""
        if hasattr(self, '_lineno_index') and lineno in self._lineno_index:
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
            
            node = self._class_nodes.get(class_name)
            children = []
            
            # Find derived classes
            for derived_name, bases in self._class_hierarchy.items():
                if class_name in bases:
                    children.append(build_tree(derived_name))
            
            return {
                "name": class_name,
                "node_id": node.id if node else None,
                "methods": node.methods if node else [],
                "children": children
            }
        
        # Find root classes (no base class or base class not in current code)
        for class_name, bases in self._class_hierarchy.items():
            if not bases or all(b not in self._class_hierarchy for b in bases):
                tree[class_name] = build_tree(class_name)
        
        return tree
    
    def get_call_graph(self) -> Dict[str, Any]:
        """Get function call graph"""
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
