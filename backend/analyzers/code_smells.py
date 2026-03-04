"""
Code Smell Detector - Code smell detection
Detects long functions, god classes, duplicate code, etc.
"""
import ast
from typing import List, Dict, Any, Optional
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
        """Detect unused variables"""
        assigned_vars = set()
        used_vars = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    assigned_vars.add((node.id, node.lineno))
                elif isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
        
        # Find defined but unused variables
        for var_name, lineno in assigned_vars:
            if var_name not in used_vars and not var_name.startswith('_'):
                # Exclude some special cases
                if var_name not in ('_', 'self', 'cls'):
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
                positions = [i + 1 for i, l in enumerate(source_lines) if l.strip() == line.strip()]
                
                self.issues.append(CodeIssue(
                    id=self._generate_issue_id("duplicate"),
                    type="code_smell",
                    severity=SeverityLevel.INFO,
                    message=f"Detected duplicate code line, appears {count} times",
                    lineno=positions[0]
                ))
    
    def _detect_dead_code(self, tree: ast.AST):
        """Detect dead code"""
        
        class DeadCodeVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.after_return = False
                self.after_break = False
                self.after_continue = False
            
            def visit_FunctionDef(self, node):
                self.after_return = False
                dead_code_start = None
                
                for i, stmt in enumerate(node.body):
                    if self.after_return:
                        # Record start of dead code block
                        if dead_code_start is None:
                            dead_code_start = i
                    else:
                        # If there was a dead code block before and now encountered non-dead code, report the previous dead code block
                        if dead_code_start is not None:
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("dead_code"),
                                type="code_smell",
                                severity=SeverityLevel.WARNING,
                                message=f"{i - dead_code_start} lines of code after return statement will never execute",
                                lineno=getattr(node.body[dead_code_start], 'lineno', node.lineno)
                            ))
                            dead_code_start = None
                    
                    if isinstance(stmt, ast.Return):
                        self.after_return = True
                    
                    self.visit(stmt)
                
                # Handle dead code block at end of function
                if dead_code_start is not None:
                    self.detector.issues.append(CodeIssue(
                        id=self.detector._generate_issue_id("dead_code"),
                        type="code_smell",
                        severity=SeverityLevel.WARNING,
                        message=f"{len(node.body) - dead_code_start} lines of code after return statement will never execute",
                        lineno=getattr(node.body[dead_code_start], 'lineno', node.lineno)
                    ))
                
                self.after_return = False
            
            def visit_Return(self, node):
                self.after_return = True
                self.generic_visit(node)
            
            def visit_Break(self, node):
                self.after_break = True
            
            def visit_Continue(self, node):
                self.after_continue = True
        
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