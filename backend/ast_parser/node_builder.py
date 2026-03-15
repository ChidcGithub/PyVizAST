"""
AST Node Builder - Create AST nodes from Python AST

@author: Chidc
@link: github.com/chidcGithub
"""
import ast
import logging
from typing import Dict, List, Optional, Any

from ..models.schemas import ASTNode, NodeType
from .node_styles import NODE_STYLES

logger = logging.getLogger(__name__)


class NodeBuilder:
    """Builder class for creating AST nodes"""
    
    def __init__(self):
        self.node_counter: Dict[str, int] = {}
    
    def reset(self):
        """Reset the builder state"""
        self.node_counter = {}
    
    def _generate_id(self, node_type: str) -> str:
        """Generate unique node ID"""
        self.node_counter[node_type] = self.node_counter.get(node_type, 0) + 1
        return f"{node_type}_{self.node_counter[node_type]}"
    
    def get_node_type(self, ast_node: ast.AST) -> NodeType:
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
    
    def get_node_name(self, ast_node: ast.AST) -> Optional[str]:
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
    
    def get_decorator_names(self, decorator_list: List[ast.AST]) -> List[str]:
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
    
    def get_base_class_names(self, bases: List[ast.AST]) -> List[str]:
        """Get list of base class names"""
        base_names = []
        for base in bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(self._get_attribute_name(base))
        return base_names
    
    def create_ast_node(self, ast_node: ast.AST, parent_id: Optional[str] = None) -> ASTNode:
        """Create ASTNode object with enhanced information"""
        node_type = self.get_node_type(ast_node)
        style = NODE_STYLES.get(node_type, NODE_STYLES[NodeType.OTHER])
        
        node_id = self._generate_id(node_type.value)
        name = self.get_node_name(ast_node)
        
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
        
        # Extract enhanced relationships
        decorators = []
        base_classes = []
        methods = []
        
        if isinstance(ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = self.get_decorator_names(ast_node.decorator_list)
        elif isinstance(ast_node, ast.ClassDef):
            decorators = self.get_decorator_names(ast_node.decorator_list)
            base_classes = self.get_base_class_names(ast_node.bases)
            # Extract method names
            for item in ast_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
        
        # Branch and loop counts - use single-pass counting
        structure_counts = self._count_structures(ast_node)
        branch_count = structure_counts['branches']
        loop_count = structure_counts['loops']
        exception_handlers = structure_counts['exception_handlers']
        
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
            decorators=decorators,
            base_classes=base_classes,
            methods=methods,
            branch_count=branch_count,
            loop_count=loop_count,
            exception_handlers=exception_handlers,
        )
    
    def _count_structures(self, node: ast.AST) -> Dict[str, int]:
        """Count branches, loops, and exception handlers in a single pass"""
        counts = {
            'branches': 0,
            'loops': 0,
            'exception_handlers': 0
        }
        
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                counts['branches'] += 1
            elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                counts['loops'] += 1
            elif isinstance(child, ast.Try):
                counts['exception_handlers'] += len(child.handlers)
        
        return counts
    
    def _count_branches(self, node: ast.AST) -> int:
        """Count number of if/elif/else branches - deprecated, use _count_structures"""
        return self._count_structures(node)['branches']
    
    def _count_loops(self, node: ast.AST) -> int:
        """Count number of loops - deprecated, use _count_structures"""
        return self._count_structures(node)['loops']
    
    def _count_exception_handlers(self, node: ast.AST) -> int:
        """Count number of except handlers - deprecated, use _count_structures"""
        return self._count_structures(node)['exception_handlers']
    
    def _generate_detailed_label(self, ast_node: ast.AST, node_type: NodeType, 
                                  name: Optional[str], attributes: Dict[str, Any]) -> str:
        """Generate detailed node label for better understanding"""
        type_desc = NODE_STYLES.get(node_type, {}).get("description", node_type.value)
        
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
            attrs['decorators'] = self.get_decorator_names(ast_node.decorator_list)
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
            attrs['bases'] = self.get_base_class_names(ast_node.bases)
            attrs['decorators'] = self.get_decorator_names(ast_node.decorator_list)
            
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
        except Exception as e:
            logger.debug(f"Failed to unparse default value: {e}")
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
    
    def _get_target_name(self, target: ast.AST) -> str:
        """Get loop target name"""
        if isinstance(target, ast.Name):
            return target.id
        return "unknown"
