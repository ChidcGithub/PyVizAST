"""
Code Smell Detector - Code smell detection
Detects long functions, god classes, duplicate code, etc.
"""
import ast
from typing import List, Dict, Optional
from collections import Counter
from ..models.schemas import CodeIssue, SeverityLevel


class CodeSmellDetector:
    """Code Smell Detector"""
    
    # Configuration thresholds
    CONFIG = {
        'max_function_lines': 50,
        'max_function_params': 5,
        'max_class_methods': 15,
        'max_class_lines': 300,
        'max_line_length': 100,
        'max_nesting_depth': 4,
        'min_variable_name_length': 2,
        'duplicate_code_threshold': 6,  # Minimum lines for similar code blocks
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.issue_counter = 0
    
    def _generate_issue_id(self, issue_type: str) -> str:
        self.issue_counter += 1
        return f"smell_{issue_type}_{self.issue_counter}"
    
    def analyze(self, code: str, tree: Optional[ast.AST] = None) -> List[CodeIssue]:
        """
        Detect code smells
        
        Args:
            code: Source code string
            tree: Optional AST tree
        
        Returns:
            List of code issues
        """
        # Clear previous state to avoid accumulation
        self.issues = []
        self.issue_counter = 0
        
        if tree is None:
            tree = ast.parse(code)
        
        source_lines = code.splitlines()
        
        # Execute various detections
        self._detect_long_functions(tree, source_lines)
        self._detect_god_classes(tree, source_lines)
        self._detect_long_parameter_list(tree)
        self._detect_deep_nesting(tree)
        self._detect_magic_numbers(tree)
        self._detect_unused_variables(tree)
        self._detect_poor_names(tree)
        self._detect_duplicate_code(source_lines)
        self._detect_dead_code(tree)
        self._detect_long_chains(tree)
        
        return self.issues
    
    def _detect_long_functions(self, tree: ast.AST, source_lines: List[str]):
        """Detect long functions"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    lines = node.end_lineno - node.lineno + 1
                    
                    if lines > self.CONFIG['max_function_lines']:
                        severity = SeverityLevel.ERROR if lines > 100 else SeverityLevel.WARNING
                        
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("long_function"),
                            type="code_smell",
                            severity=severity,
                            message=f"Function '{node.name}' is too long ({lines} lines), consider splitting into smaller functions",
                            lineno=node.lineno,
                            end_lineno=node.end_lineno,
                            source_snippet=ast.get_docstring(node)
                        ))
    
    def _detect_god_classes(self, tree: ast.AST, source_lines: List[str]):
        """Detect god classes (overly large and complex classes)"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                attributes = set()
                
                # Count attributes
                for item in ast.walk(node):
                    if isinstance(item, ast.Attribute):
                        if isinstance(item.value, ast.Name) and item.value.id == 'self':
                            attributes.add(item.attr)
                
                method_count = len(methods)
                attribute_count = len(attributes)
                
                # Check line count
                lines = 0
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    lines = node.end_lineno - node.lineno + 1
                
                # Determine if it's a god class
                is_god_class = (
                    method_count > self.CONFIG['max_class_methods'] or
                    lines > self.CONFIG['max_class_lines'] or
                    (method_count > 10 and attribute_count > 10)
                )
                
                if is_god_class:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("god_class"),
                        type="code_smell",
                        severity=SeverityLevel.WARNING,
                        message=f"Class '{node.name}' may be a god class ({method_count} methods, {attribute_count} attributes, {lines} lines), consider splitting responsibilities",
                        lineno=node.lineno
                    ))
    
    def _detect_long_parameter_list(self, tree: ast.AST):
        """Detect long parameter lists"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                param_count = len(node.args.args)
                param_count += len(node.args.posonlyargs) if hasattr(node.args, 'posonlyargs') else 0
                param_count += len(node.args.kwonlyargs)
                if node.args.vararg:
                    param_count += 1
                if node.args.kwarg:
                    param_count += 1
                
                if param_count > self.CONFIG['max_function_params']:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("long_params"),
                        type="code_smell",
                        severity=SeverityLevel.WARNING,
                        message=f"Function '{node.name}' has too many parameters ({param_count}), consider using a configuration object or refactoring",
                        lineno=node.lineno
                    ))
    
    def _detect_deep_nesting(self, tree: ast.AST):
        """Detect deep nesting"""
        
        class NestingVisitor(ast.NodeVisitor):
            def __init__(self, detector, max_depth):
                self.detector = detector
                self.max_depth = max_depth
                self.current_depth = 0
                self.depth_stack = []
            
            def _visit_nested(self, node, node_type):
                self.current_depth += 1
                self.depth_stack.append((node, node_type))
                
                if self.current_depth > self.max_depth:
                    self.detector.issues.append(CodeIssue(
                        id=self.detector._generate_issue_id("deep_nesting"),
                        type="code_smell",
                        severity=SeverityLevel.WARNING,
                        message=f"{node_type} nesting too deep ({self.current_depth} levels), consider extracting methods or using early returns",
                        lineno=node.lineno
                    ))
                
                self.generic_visit(node)
                self.current_depth -= 1
                self.depth_stack.pop()
            
            def visit_If(self, node):
                self._visit_nested(node, "if")
            
            def visit_For(self, node):
                self._visit_nested(node, "for")
            
            def visit_While(self, node):
                self._visit_nested(node, "while")
            
            def visit_Try(self, node):
                self._visit_nested(node, "try")
            
            def visit_With(self, node):
                self._visit_nested(node, "with")
        
        visitor = NestingVisitor(self, self.CONFIG['max_nesting_depth'])
        visitor.visit(tree)
    
    def _detect_magic_numbers(self, tree: ast.AST):
        """Detect magic numbers"""
        excluded_values = {0, 1, -1, 2, 10, 100, 1000, 255, 256, 360, 1024}
        
        class MagicNumberVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.in_assign_value = False
                self.in_constant_def = False
            
            def visit_Assign(self, node):
                # Check if it's a constant definition (uppercase variable name)
                is_constant = all(
                    isinstance(t, ast.Name) and t.id.isupper()
                    for t in node.targets
                )
                
                old_in_assign = self.in_assign_value
                old_in_constant = self.in_constant_def
                
                self.in_assign_value = True
                self.in_constant_def = is_constant
                
                self.generic_visit(node)
                
                self.in_assign_value = old_in_assign
                self.in_constant_def = old_in_constant
            
            def visit_AnnAssign(self, node):
                # Type-annotated assignment
                is_constant = isinstance(node.target, ast.Name) and node.target.id.isupper()
                
                old_in_constant = self.in_constant_def
                self.in_constant_def = is_constant
                
                self.generic_visit(node)
                
                self.in_constant_def = old_in_constant
            
            def visit_Constant(self, node):
                if isinstance(node.value, (int, float)):
                    if node.value not in excluded_values:
                        # Don't report if in constant definition
                        if not self.in_constant_def:
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("magic_number"),
                                type="code_smell",
                                severity=SeverityLevel.INFO,
                                message=f"Magic number '{node.value}', consider defining as a constant",
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            ))
        
        visitor = MagicNumberVisitor(self)
        visitor.visit(tree)
    
    def _detect_unused_variables(self, tree: ast.AST):
        """Detect unused variables - Enhanced version with unpacking support"""
        assigned_vars = set()  # (var_name, lineno)
        used_vars = set()      # var_name
        
        # Helper function to extract variable names from assignment targets
        def extract_var_names(target, lineno):
            """Extract variable names from assignment target, handling unpacking"""
            names = []
            if isinstance(target, ast.Name):
                names.append((target.id, lineno))
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                # Handle tuple/list unpacking: a, b = func() or [a, b] = func()
                for elt in target.elts:
                    names.extend(extract_var_names(elt, lineno))
            elif isinstance(target, ast.Starred):
                # Handle starred unpacking: a, *rest = func()
                names.extend(extract_var_names(target.value, lineno))
            return names
        
        for node in ast.walk(tree):
            # Handle regular assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    assigned_vars.update(extract_var_names(target, node.lineno))
            
            # Handle annotated assignments: x: int = 5
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    assigned_vars.add((node.target.id, node.lineno))
            
            # Handle augmented assignments: x += 1 (counts as both assign and use)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    used_vars.add(node.target.id)
            
            # Handle for loop variables: for i in range(10):
            elif isinstance(node, ast.For):
                assigned_vars.update(extract_var_names(node.target, node.lineno))
            
            # Handle with statement variables: with open() as f:
            elif isinstance(node, ast.withitem):
                if node.optional_vars:
                    assigned_vars.update(extract_var_names(node.optional_vars, node.lineno if hasattr(node, 'lineno') else 0))
            
            # Handle variable usage
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
        
        # Find defined but unused variables
        for var_name, lineno in assigned_vars:
            # Skip special cases
            if var_name.startswith('_'):  # Convention for intentionally unused
                continue
            if var_name in ('self', 'cls', 'args', 'kwargs'):  # Special parameters
                continue
            
            if var_name not in used_vars:
                self.issues.append(CodeIssue(
                    id=self._generate_issue_id("unused_var"),
                    type="code_smell",
                    severity=SeverityLevel.INFO,
                    message=f"Variable '{var_name}' may be unused",
                    lineno=lineno
                ))
    
    def _detect_poor_names(self, tree: ast.AST):
        """Detect poor naming"""
        poor_names = {'x', 'y', 'z', 'temp', 'tmp', 'data', 'result', 'val', 'var', 'foo', 'bar', 'baz'}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in poor_names:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("poor_name"),
                        type="code_smell",
                        severity=SeverityLevel.INFO,
                        message=f"Function name '{node.name}' is not descriptive enough, consider using a more meaningful name",
                        lineno=node.lineno
                    ))
                
                # Check parameter names
                for arg in node.args.args:
                    if arg.arg in poor_names:
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("poor_param_name"),
                            type="code_smell",
                            severity=SeverityLevel.INFO,
                            message=f"Parameter name '{arg.arg}' is not descriptive enough",
                            lineno=node.lineno
                        ))
            
            elif isinstance(node, ast.ClassDef):
                if node.name in poor_names:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("poor_class_name"),
                        type="code_smell",
                        severity=SeverityLevel.INFO,
                        message=f"Class name '{node.name}' is not descriptive enough",
                        lineno=node.lineno
                    ))
    
    def _detect_duplicate_code(self, source_lines: List[str]):
        """Detect duplicate code (simplified version)"""
        # Simplified implementation: detect identical lines
        line_count = Counter(line.strip() for line in source_lines if line.strip())
        
        for line, count in line_count.items():
            if count > 3 and len(line) > 20:  # Exclude short lines and comments
                # Find positions of these lines
                positions = [i + 1 for i, line_item in enumerate(source_lines) if line_item.strip() == line.strip()]
                
                self.issues.append(CodeIssue(
                    id=self._generate_issue_id("duplicate"),
                    type="code_smell",
                    severity=SeverityLevel.INFO,
                    message=f"Detected duplicate code line, appears {count} times",
                    lineno=positions[0]
                ))
    
    def _detect_dead_code(self, tree: ast.AST):
        """Detect dead code"""
        
        # Terminating statements that make following code unreachable
        TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)
        
        class DeadCodeVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
            
            def visit_FunctionDef(self, node):
                self._check_body_for_dead_code(node.body, node.lineno)
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                self._check_body_for_dead_code(node.body, node.lineno)
                self.generic_visit(node)
            
            def _check_body_for_dead_code(self, body: List[ast.stmt], func_lineno: int):
                """Check a body of statements for dead code"""
                dead_code_start = None
                dead_code_end = None
                
                for i, stmt in enumerate(body):
                    if dead_code_start is not None:
                        # We're in a dead code section
                        dead_code_end = i
                    
                    # Check for terminating statements
                    if isinstance(stmt, TERMINATORS):
                        if dead_code_start is None:
                            # Mark start of potential dead code (next statement)
                            if i + 1 < len(body):
                                dead_code_start = i + 1
                                dead_code_end = i + 1
                    
                    # Recursively check nested structures (but don't propagate terminator state)
                    if isinstance(stmt, ast.If):
                        self._check_body_for_dead_code(stmt.body, stmt.lineno)
                        if stmt.orelse:
                            self._check_body_for_dead_code(stmt.orelse, stmt.lineno)
                    elif isinstance(stmt, (ast.For, ast.While)):
                        self._check_body_for_dead_code(stmt.body, stmt.lineno)
                        if stmt.orelse:
                            self._check_body_for_dead_code(stmt.orelse, stmt.lineno)
                    elif isinstance(stmt, ast.Try):
                        self._check_body_for_dead_code(stmt.body, stmt.lineno)
                        for handler in stmt.handlers:
                            self._check_body_for_dead_code(handler.body, handler.lineno)
                        if stmt.orelse:
                            self._check_body_for_dead_code(stmt.orelse, stmt.lineno)
                        if stmt.finalbody:
                            self._check_body_for_dead_code(stmt.finalbody, stmt.lineno)
                    elif isinstance(stmt, ast.With):
                        self._check_body_for_dead_code(stmt.body, stmt.lineno)
                
                # Report dead code if found
                if dead_code_start is not None and dead_code_end is not None:
                    dead_code_count = dead_code_end - dead_code_start + 1
                    first_dead_stmt = body[dead_code_start]
                    self.detector.issues.append(CodeIssue(
                        id=self.detector._generate_issue_id("dead_code"),
                        type="code_smell",
                        severity=SeverityLevel.WARNING,
                        message=f"{dead_code_count} lines of unreachable code after return/raise/break/continue statement",
                        lineno=getattr(first_dead_stmt, 'lineno', func_lineno)
                    ))
        
        visitor = DeadCodeVisitor(self)
        visitor.visit(tree)
    
    def _detect_long_chains(self, tree: ast.AST):
        """Detect overly long attribute/method chains"""
        
        def get_chain_length(node, depth=0):
            if isinstance(node, ast.Attribute):
                return get_chain_length(node.value, depth + 1)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    return get_chain_length(node.func.value, depth + 1)
            return depth
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                chain_length = get_chain_length(node)
                if chain_length > 4:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("long_chain"),
                        type="code_smell",
                        severity=SeverityLevel.INFO,
                        message=f"Attribute chain too long ({chain_length} levels), consider using intermediate variables for readability",
                        lineno=node.lineno
                    ))
    
    def get_summary(self) -> Dict[str, int]:
        """Get detection summary"""
        summary = {}
        for issue in self.issues:
            key = issue.message.split(',')[0]  # Extract main information
            summary[key] = summary.get(key, 0) + 1
        return summary