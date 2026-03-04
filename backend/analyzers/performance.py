"""
Performance Analyzer - Performance hotspot detection
Analyzes potential performance issues in code
"""
import ast
from typing import List, Dict, Any, Optional, Tuple
from ..models.schemas import CodeIssue, SeverityLevel, PerformanceHotspot


class PerformanceAnalyzer:
    """Performance Analyzer"""
    
    # Inefficient operation patterns
    INEFFICIENT_PATTERNS = {
        'list_append_in_loop': {
            'message': 'Using list append in loop may be inefficient, consider list comprehension',
            'severity': SeverityLevel.INFO,
        },
        'string_concat_in_loop': {
            'message': 'String concatenation in loop has performance issues, recommend using join()',
            'severity': SeverityLevel.WARNING,
        },
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.hotspots: List[PerformanceHotspot] = []
        self.issue_counter = 0
        self.hotspot_counter = 0
    
    def _generate_issue_id(self, issue_type: str) -> str:
        self.issue_counter += 1
        return f"performance_{issue_type}_{self.issue_counter}"
    
    def _generate_hotspot_id(self) -> str:
        self.hotspot_counter += 1
        return f"hotspot_{self.hotspot_counter}"
    
    def _add_hotspot(self, hotspot_type: str, description: str, lineno: int = None, 
                     estimated_complexity: str = "O(n)", suggestion: str = None):
        """Add a performance hotspot"""
        self.hotspots.append(PerformanceHotspot(
            id=self._generate_hotspot_id(),
            node_id="",
            hotspot_type=hotspot_type,
            description=description,
            estimated_complexity=estimated_complexity,
            lineno=lineno,
            suggestion=suggestion
        ))
    
    def analyze(self, code: str, tree: Optional[ast.AST] = None) -> List[CodeIssue]:
        """
        Analyze code performance
        
        Args:
            code: Source code string
            tree: Optional AST tree
        
        Returns:
            List of performance issues
        """
        # Clear previous state to avoid accumulation
        self.issues = []
        self.hotspots = []
        self.issue_counter = 0
        self.hotspot_counter = 0
        
        if tree is None:
            tree = ast.parse(code)
        
        source_lines = code.splitlines()
        
        # Execute various performance checks
        self._detect_inefficient_loops(tree)
        self._detect_string_concatenation(tree)
        self._detect_inefficient_data_structures(tree)
        self._detect_expensive_operations_in_loops(tree)
        self._detect_global_variable_usage(tree)
        self._detect_redundant_calculations(tree)
        self._detect_memory_issues(tree)
        self._detect_unoptimized_comprehensions(tree)
        
        return self.issues
    
    def _detect_inefficient_loops(self, tree: ast.AST):
        """Detect inefficient loop patterns including nested loops"""
        
        # Detect nested loops (O(n^2) or worse complexity)
        class NestedLoopVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.loop_depth = 0
                self.loop_stack = []  # Track loop line numbers
            
            def visit_For(self, node):
                self._visit_loop(node)
            
            def visit_While(self, node):
                self._visit_loop(node)
            
            def _visit_loop(self, node):
                old_depth = self.loop_depth
                self.loop_depth += 1
                self.loop_stack.append(getattr(node, 'lineno', 0))
                
                # If we're in a nested loop (depth >= 2), report it
                if self.loop_depth >= 2:
                    estimated_complexity = f"O(n^{self.loop_depth})" if self.loop_depth <= 4 else "O(n^k)"
                    self.detector.issues.append(CodeIssue(
                        id=self.detector._generate_issue_id("nested_loop"),
                        type="performance",
                        severity=SeverityLevel.WARNING if self.loop_depth == 2 else SeverityLevel.ERROR,
                        message=f"Nested loop detected ({self.loop_depth} levels deep), complexity is {estimated_complexity}",
                        lineno=getattr(node, 'lineno', None),
                        suggestion="Consider refactoring to reduce nesting or use more efficient data structures"
                    ))
                    # Also add a hotspot
                    self.detector._add_hotspot(
                        hotspot_type="nested_loop",
                        description=f"Nested loop with {self.loop_depth} levels of nesting",
                        lineno=self.loop_stack[0] if self.loop_stack else getattr(node, 'lineno', None),
                        estimated_complexity=estimated_complexity,
                        suggestion="Consider using a more efficient algorithm or data structure"
                    )
                
                self.generic_visit(node)
                self.loop_depth = old_depth
                self.loop_stack.pop()
        
        visitor = NestedLoopVisitor(self)
        visitor.visit(tree)
        
        # Also check for inefficient operations inside loops
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check for operations inside loops that should be outside
                self._check_loop_contents(node)
    
    def _check_loop_contents(self, loop_node: ast.AST):
        """Check if there are inefficient operations inside loops"""
        
        for child in ast.walk(loop_node):
            # len() call in for loop condition - detect repeated len() calls
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == 'len':
                    # len() is called inside loop - could be cached outside
                    if child.args and isinstance(child.args[0], ast.Name):
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("len_in_loop"),
                            type="performance",
                            severity=SeverityLevel.INFO,
                            message="len() called inside loop, consider caching the result outside the loop",
                            lineno=getattr(child, 'lineno', None),
                            suggestion="Cache: n = len(sequence) before the loop"
                        ))
            
            # Check for repeated function calls - detect same function called multiple times
            if isinstance(child, ast.Call):
                # Detect range(len()) pattern which is inefficient
                if isinstance(child.func, ast.Name) and child.func.id == 'range':
                    if child.args and isinstance(child.args[0], ast.Call):
                        if isinstance(child.args[0].func, ast.Name) and child.args[0].func.id == 'len':
                            self.issues.append(CodeIssue(
                                id=self._generate_issue_id("range_len"),
                                type="performance",
                                severity=SeverityLevel.INFO,
                                message="range(len(...)) pattern detected, consider using enumerate() for better readability",
                                lineno=getattr(child, 'lineno', None),
                                suggestion="Use: for i, item in enumerate(sequence):"
                            ))
    
    def _detect_string_concatenation(self, tree: ast.AST):
        """Detect string concatenation in loops"""
        
        class StringConcatVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.in_loop = False
                self.loop_lineno = 0
            
            def visit_For(self, node):
                old_in_loop = self.in_loop
                old_lineno = self.loop_lineno
                self.in_loop = True
                self.loop_lineno = node.lineno
                self.generic_visit(node)
                self.in_loop = old_in_loop
                self.loop_lineno = old_lineno
            
            def visit_While(self, node):
                old_in_loop = self.in_loop
                old_lineno = self.loop_lineno
                self.in_loop = True
                self.loop_lineno = node.lineno
                self.generic_visit(node)
                self.in_loop = old_in_loop
                self.loop_lineno = old_lineno
            
            def visit_AugAssign(self, node):
                if self.in_loop and isinstance(node.op, ast.Add):
                    # Check if it's string concatenation
                    if isinstance(node.target, ast.Name):
                        self.detector.issues.append(CodeIssue(
                            id=self.detector._generate_issue_id("string_concat"),
                            type="performance",
                            severity=SeverityLevel.WARNING,
                            message="String concatenation in loop has performance issues, recommend using list and join()",
                            lineno=self.loop_lineno,
                            suggestion="Use: result = ''.join(items)"
                        ))
                        # Also add a hotspot
                        self.detector._add_hotspot(
                            hotspot_type="inefficient_operation",
                            description=f"String concatenation using += in loop on variable '{node.target.id}'",
                            lineno=self.loop_lineno,
                            estimated_complexity="O(n^2)",
                            suggestion="Use list.append() and ''.join() for O(n) complexity"
                        )
                
                self.generic_visit(node)
        
        visitor = StringConcatVisitor(self)
        visitor.visit(tree)
    
    def _detect_inefficient_data_structures(self, tree: ast.AST):
        """Detect inefficient data structure usage"""
        
        # Track if we're inside a loop for context-aware detection
        class InefficientDSVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.in_loop = False
                self.loop_lineno = 0
            
            def _enter_loop(self, node):
                old_in_loop = self.in_loop
                old_lineno = self.loop_lineno
                self.in_loop = True
                self.loop_lineno = getattr(node, 'lineno', 0)
                self.generic_visit(node)
                self.in_loop = old_in_loop
                self.loop_lineno = old_lineno
            
            def visit_For(self, node):
                self._enter_loop(node)
            
            def visit_While(self, node):
                self._enter_loop(node)
            
            def visit_Compare(self, node):
                # Check for 'x in list' operations inside loops - O(n) complexity
                for i, op in enumerate(node.ops):
                    if isinstance(op, (ast.In, ast.NotIn)):
                        comparator = node.comparators[i]
                        # Detect list literal membership test
                        if isinstance(comparator, ast.List):
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("list_membership"),
                                type="performance",
                                severity=SeverityLevel.WARNING,
                                message="Membership check on list is O(n), consider using a set for O(1) lookup",
                                lineno=getattr(node, 'lineno', None),
                                suggestion="Convert to set: my_set = set(my_list)"
                            ))
                self.generic_visit(node)
            
            def visit_Call(self, node):
                if self.in_loop:
                    # list.count() in loop - O(n^2) potential
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == 'count':
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("count_in_loop"),
                                type="performance",
                                severity=SeverityLevel.WARNING,
                                message="list.count() inside loop has O(n) complexity per call, consider using Counter or set",
                                lineno=getattr(node, 'lineno', None),
                                suggestion="Use: from collections import Counter"
                            ))
                        # list.index() in loop - also O(n)
                        elif node.func.attr == 'index':
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("index_in_loop"),
                                type="performance",
                                severity=SeverityLevel.INFO,
                                message="list.index() inside loop has O(n) complexity, consider using a dictionary for O(1) lookup",
                                lineno=getattr(node, 'lineno', None),
                                suggestion="Build a dict: index_map = {val: i for i, val in enumerate(lst)}"
                            ))
                self.generic_visit(node)
        
        visitor = InefficientDSVisitor(self)
        visitor.visit(tree)
    
    def _detect_expensive_operations_in_loops(self, tree: ast.AST):
        """Detect expensive operations inside loops"""
        
        expensive_calls = {
            'open', 'read', 'write', 'connect', 'request',
            'query', 'execute', 'fetch', 'commit'
        }
        
        class ExpensiveOpVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.loop_depth = 0
                self.loop_lineno = 0
            
            def _visit_loop(self, node):
                old_depth = self.loop_depth
                old_lineno = self.loop_lineno
                self.loop_depth += 1
                self.loop_lineno = node.lineno
                self.generic_visit(node)
                self.loop_depth = old_depth
                self.loop_lineno = old_lineno
            
            def visit_For(self, node):
                self._visit_loop(node)
            
            def visit_While(self, node):
                self._visit_loop(node)
            
            def visit_Call(self, node):
                if self.loop_depth > 0:
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    
                    if func_name in expensive_calls:
                        self.detector.issues.append(CodeIssue(
                            id=self.detector._generate_issue_id("expensive_in_loop"),
                            type="performance",
                            severity=SeverityLevel.WARNING,
                            message=f"Expensive operation '{func_name}()' inside loop may affect performance, consider moving outside",
                            lineno=node.lineno
                        ))
                
                self.generic_visit(node)
        
        visitor = ExpensiveOpVisitor(self)
        visitor.visit(tree)
    
    def _detect_global_variable_usage(self, tree: ast.AST):
        """Detect global variable usage in performance-critical code"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                self.issues.append(CodeIssue(
                    id=self._generate_issue_id("global_usage"),
                    type="performance",
                    severity=SeverityLevel.INFO,
                    message="Using global variables may affect performance, consider passing as parameters",
                    lineno=node.lineno
                ))
    
    def _detect_redundant_calculations(self, tree: ast.AST):
        """Detect redundant calculations"""
        
        # Detect duplicate expression calculations in loops
        class RedundantCalcVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.in_loop = False
                self.loop_lineno = 0
                # Track expressions by their source representation
                self.expressions: Dict[str, Tuple[ast.AST, int]] = {}
            
            def _enter_loop(self, node):
                old_in_loop = self.in_loop
                old_lineno = self.loop_lineno
                old_expressions = self.expressions.copy()
                self.in_loop = True
                self.loop_lineno = getattr(node, 'lineno', 0)
                self.expressions = {}
                self.generic_visit(node)
                self.in_loop = old_in_loop
                self.loop_lineno = old_lineno
                self.expressions = old_expressions
            
            def visit_For(self, node):
                self._enter_loop(node)
            
            def visit_While(self, node):
                self._enter_loop(node)
            
            def visit_Call(self, node):
                if self.in_loop:
                    # Get a string representation of the call for comparison
                    try:
                        import ast as ast_module
                        call_repr = ast_module.unparse(node) if hasattr(ast_module, 'unparse') else str(node)
                    except:
                        call_repr = str(getattr(node, 'lineno', ''))
                    
                    # Check if we've seen this expression before
                    if call_repr in self.expressions:
                        first_node, first_lineno = self.expressions[call_repr]
                        # Only report once per unique expression
                        if first_lineno != getattr(node, 'lineno', 0):
                            # Skip built-in functions that are typically cheap
                            func_name = None
                            if isinstance(node.func, ast.Name):
                                func_name = node.func.id
                            elif isinstance(node.func, ast.Attribute):
                                func_name = node.func.attr
                            
                            cheap_functions = {'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set'}
                            if func_name not in cheap_functions:
                                self.detector.issues.append(CodeIssue(
                                    id=self.detector._generate_issue_id("redundant_calc"),
                                    type="performance",
                                    severity=SeverityLevel.INFO,
                                    message=f"Potentially redundant calculation detected, same expression called multiple times in loop",
                                    lineno=getattr(node, 'lineno', None),
                                    suggestion="Consider caching the result in a variable outside or at the start of the loop"
                                ))
                    else:
                        self.expressions[call_repr] = (node, getattr(node, 'lineno', 0))
                
                self.generic_visit(node)
            
            def visit_BinOp(self, node):
                if self.in_loop:
                    # Detect repeated binary operations (e.g., calculations with constants)
                    try:
                        import ast as ast_module
                        expr_repr = ast_module.unparse(node) if hasattr(ast_module, 'unparse') else None
                        if expr_repr and expr_repr in self.expressions:
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("redundant_binop"),
                                type="performance",
                                severity=SeverityLevel.INFO,
                                message="Repeated calculation detected in loop, consider caching the result",
                                lineno=getattr(node, 'lineno', None),
                                suggestion="Cache: result = calculation  # outside loop"
                            ))
                        elif expr_repr:
                            self.expressions[expr_repr] = (node, getattr(node, 'lineno', 0))
                    except:
                        pass
                self.generic_visit(node)
        
        visitor = RedundantCalcVisitor(self)
        visitor.visit(tree)
    
    def _detect_memory_issues(self, tree: ast.AST):
        """Detect potential memory issues"""
        
        for node in ast.walk(tree):
            # Large list comprehension - detect potentially memory-heavy patterns
            if isinstance(node, ast.ListComp):
                # Check if there's filter condition (without filter, generates all items)
                if not node.generators[0].ifs:
                    # Check for nested loops in comprehension (multiplicative size)
                    if len(node.generators) > 1:
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("large_listcomp_nested"),
                            type="performance",
                            severity=SeverityLevel.INFO,
                            message="Nested list comprehension without filter may generate large result, consider generator expression",
                            lineno=getattr(node, 'lineno', None),
                            suggestion="Use generator: (... for ... for ...) instead of [... for ... for ...]"
                        ))
            
            # Range in Python 2 style (if using xrange)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    # Large range
                    if node.func.id == 'range':
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                                if arg.value > 10000:
                                    self.issues.append(CodeIssue(
                                        id=self._generate_issue_id("large_range"),
                                        type="performance",
                                        severity=SeverityLevel.INFO,
                                        message=f"Large range({arg.value}) may consume a lot of memory, consider using generator",
                                        lineno=node.lineno
                                    ))
    
    def _detect_unoptimized_comprehensions(self, tree: ast.AST):
        """Detect unoptimized comprehension patterns"""
        
        # Functions that only iterate once over their argument (suitable for generators)
        single_pass_functions = {
            'sum', 'any', 'all', 'max', 'min', 'sorted', 'reversed',
            'list', 'tuple', 'set', 'dict', 'frozenset',
            'join', 'map', 'filter', 'enumerate', 'zip'
        }
        
        class CompOptVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
            
            def visit_Call(self, node):
                # Check if list comprehension is passed to a single-pass function
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                if func_name in single_pass_functions:
                    for arg in node.args:
                        if isinstance(arg, ast.ListComp):
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("listcomp_to_gen"),
                                type="performance",
                                severity=SeverityLevel.INFO,
                                message=f"List comprehension passed to {func_name}() can be replaced with generator expression for memory efficiency",
                                lineno=getattr(node, 'lineno', None),
                                suggestion=f"Replace [...] with (...) inside {func_name}()"
                            ))
                
                self.generic_visit(node)
        
        for node in ast.walk(tree):
            # Nested comprehensions
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                if len(node.generators) > 2:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("nested_comp"),
                        type="performance",
                        severity=SeverityLevel.INFO,
                        message="Deeply nested comprehensions may affect readability and performance, consider using explicit loops",
                        lineno=node.lineno
                    ))
        
        visitor = CompOptVisitor(self)
        visitor.visit(tree)
    
    def _analyze_function_complexity(self, func_node: ast.AST) -> Dict[str, Any]:
        """Analyze function complexity"""
        result = {
            'has_nested_loops': False,
            'max_loop_depth': 0,
            'call_count': 0,
        }
        
        class LoopDepthVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0
            
            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
            
            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
        
        visitor = LoopDepthVisitor()
        visitor.visit(func_node)
        
        result['max_loop_depth'] = visitor.max_depth
        result['has_nested_loops'] = visitor.max_depth > 1
        
        # Count function calls
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                result['call_count'] += 1
        
        return result
    
    def get_performance_hotspots(self) -> List[PerformanceHotspot]:
        """Get list of performance hotspots"""
        return self.hotspots
    
    def get_issues(self) -> List[CodeIssue]:
        """Get issue list"""
        return self.issues
