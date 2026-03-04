"""
Suggestion Engine - Optimization suggestion generation engine
Generates concrete refactoring suggestions based on analysis results
"""
import ast
import re
from typing import List, Dict, Any, Optional
from ..models.schemas import OptimizationSuggestion, CodeIssue, SeverityLevel


class SuggestionEngine:
    """Optimization Suggestion Generation Engine"""
    
    # Optimization rules library
    RULES = {
        # Performance optimization rules
        'list_comp_to_gen': {
            'category': 'performance',
            'title': 'Use generator expression instead of list comprehension',
            'description': 'Generator expressions are more memory efficient when only iterating over results without index access',
            'auto_fixable': True,
            'priority': 2,
        },
        'string_concat': {
            'category': 'performance',
            'title': 'Use join() instead of string concatenation in loops',
            'description': 'Strings are immutable, += operations in loops create many temporary objects',
            'auto_fixable': True,
            'priority': 2,
        },
        'use_local_variable': {
            'category': 'performance',
            'title': 'Cache global lookups as local variables',
            'description': 'Accessing global variables or methods in loops adds lookup overhead',
            'auto_fixable': False,
            'priority': 3,
        },
        'use_set_for_lookup': {
            'category': 'performance',
            'title': 'Use set instead of list for membership checks',
            'description': 'Set membership check is O(1), while list is O(n)',
            'auto_fixable': True,
            'priority': 2,
        },
        
        # Readability rules
        'use_enumerate': {
            'category': 'readability',
            'title': 'Use enumerate() instead of range(len())',
            'description': 'enumerate() is more Pythonic and readable',
            'auto_fixable': True,
            'priority': 3,
        },
        'use_fstring': {
            'category': 'readability',
            'title': 'Use f-string instead of % or .format()',
            'description': 'f-string is more concise, faster, and more readable',
            'auto_fixable': True,
            'priority': 3,
        },
        'use_context_manager': {
            'category': 'readability',
            'title': 'Use with statement to manage resources',
            'description': 'Ensures resources are properly released, avoiding resource leaks',
            'auto_fixable': False,
            'priority': 2,
        },
        'extract_method': {
            'category': 'readability',
            'title': 'Extract method to reduce complexity',
            'description': 'Split complex logic into smaller, well-named methods',
            'auto_fixable': False,
            'priority': 1,
        },
        
        # Security rules
        'parametrize_sql': {
            'category': 'security',
            'title': 'Use parameterized queries',
            'description': 'Prevent SQL injection attacks',
            'auto_fixable': False,
            'priority': 1,
        },
        'use_literal_eval': {
            'category': 'security',
            'title': 'Use ast.literal_eval() instead of eval()',
            'description': 'ast.literal_eval() only parses literals, safer',
            'auto_fixable': True,
            'priority': 1,
        },
        
        # Best practice rules
        'use_dataclass': {
            'category': 'best_practice',
            'title': 'Consider using @dataclass decorator',
            'description': 'Automatically generates __init__, __repr__, and other methods, reducing boilerplate',
            'auto_fixable': False,
            'priority': 4,
        },
        'add_type_hints': {
            'category': 'best_practice',
            'title': 'Add type annotations',
            'description': 'Improve code readability and IDE support',
            'auto_fixable': False,
            'priority': 4,
        },
        'use_walrus_operator': {
            'category': 'best_practice',
            'title': 'Consider using walrus operator (:=)',
            'description': 'Assign within expressions to simplify code',
            'auto_fixable': False,
            'priority': 5,
        },
    }
    
    def __init__(self):
        self.suggestions: List[OptimizationSuggestion] = []
        self.suggestion_counter = 0
        self._added_suggestion_keys: set = set()  # Deduplication key set
    
    def _generate_suggestion_id(self) -> str:
        self.suggestion_counter += 1
        return f"suggestion_{self.suggestion_counter}"
    
    def _get_suggestion_key(self, title: str, lineno: Optional[int] = None) -> str:
        """Generate unique key for suggestion, for deduplication"""
        return f"{title}:{lineno or 0}"
    
    def _is_duplicate(self, title: str, lineno: Optional[int] = None) -> bool:
        """Check if the same suggestion already exists"""
        key = self._get_suggestion_key(title, lineno)
        if key in self._added_suggestion_keys:
            return True
        self._added_suggestion_keys.add(key)
        return False
    
    def generate_suggestions(
        self, 
        code: str, 
        tree: Optional[ast.AST] = None,
        issues: Optional[List[CodeIssue]] = None
    ) -> List[OptimizationSuggestion]:
        """
        Generate optimization suggestions based on code and issue list
        
        Args:
            code: Source code string
            tree: Optional AST tree
            issues: Optional issue list
        
        Returns:
            List of optimization suggestions
        """
        if tree is None:
            tree = ast.parse(code)
        
        # Reset state
        self.suggestions = []
        self.suggestion_counter = 0
        self._added_suggestion_keys = set()
        
        source_lines = code.splitlines()
        
        # Generate suggestions based on AST structure
        self._detect_list_comp_opportunities(tree, source_lines)
        self._detect_string_concat_opportunities(tree, source_lines)
        self._detect_enumerate_opportunities(tree, source_lines)
        self._detect_fstring_opportunities(tree, source_lines)
        self._detect_set_lookup_opportunities(tree, source_lines)
        self._detect_dataclass_opportunities(tree, source_lines)
        self._detect_context_manager_opportunities(tree, source_lines)
        
        # Generate targeted suggestions based on issue list
        if issues:
            self._generate_issue_based_suggestions(issues)
        
        return self.suggestions
    
    def _detect_list_comp_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """
        Detect list comprehensions that can be replaced with generators
        
        Only suggest conversion to generator expression in these scenarios:
        1. Passed as function argument, and function only iterates once (e.g., sum, any, all, max, min, join, sorted)
        2. Used directly for iteration and won't be reused
        
        Scenarios NOT recommended for conversion:
        1. Assigned to variable (may be iterated multiple times or indexed)
        2. Used as return value
        3. In contexts requiring len()
        """
        
        # Single-pass functions (suitable for generators)
        SINGLE_PASS_FUNCTIONS = {
            'sum', 'any', 'all', 'max', 'min', 'sorted', 'reversed',
            'list', 'tuple', 'set', 'dict', 'frozenset',
            'join',  # string join
            'map', 'filter', 'enumerate', 'zip',
            'heapq.nlargest', 'heapq.nsmallest',
            'itertools.chain', 'itertools.islice',
        }
        
        # Multi-pass or multi-function functions (not suitable for generators)
        MULTI_PASS_FUNCTIONS = {'len', 'copy', 'deepcopy'}
        
        class ListCompContextVisitor(ast.NodeVisitor):
            def __init__(self, engine, lines):
                self.engine = engine
                self.lines = lines
                self.suggestions_added = set()  # Avoid duplicate suggestions
            
            def visit_Call(self, node):
                """Check list comprehension as function argument"""
                
                # Check function name
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                if func_name in SINGLE_PASS_FUNCTIONS:
                    # Check if arguments contain list comprehension
                    for arg in node.args:
                        if isinstance(arg, ast.ListComp):
                            self._add_suggestion(arg, node, 'function_arg', func_name)
                
                # Continue traversing child nodes
                self.generic_visit(node)
            
            def visit_For(self, node):
                """Check for loops directly using list comprehension for iteration"""
                
                # Check if iterator is a list comprehension
                if isinstance(node.iter, ast.ListComp):
                    # Check if this for loop is inside a function and result won't be saved
                    # This can usually be converted to a generator
                    self._add_suggestion(node.iter, node, 'for_iter')
                
                self.generic_visit(node)
            
            def _add_suggestion(self, listcomp_node, parent_node, context, func_name=None):
                """Add optimization suggestion"""
                
                # Avoid duplicate suggestions for the same node
                node_key = (listcomp_node.lineno, listcomp_node.col_offset)
                if node_key in self.suggestions_added:
                    return
                self.suggestions_added.add(node_key)
                
                before_code = self.engine._get_source_segment(listcomp_node, self.lines)
                after_code = self.engine._convert_listcomp_to_genexpr(listcomp_node, self.lines)
                
                # Generate different descriptions based on context
                if context == 'function_arg':
                    description = (
                        f"When used as argument to `{func_name}()`, generator expression is more memory efficient "
                        f"because the function only iterates once"
                    )
                    estimated = '50%+ memory reduction'
                elif context == 'for_iter':
                    description = (
                        "When used as for loop iterator, generator expression enables lazy evaluation, "
                        "saving memory. But be cautious if loop contains break or multiple iterations"
                    )
                    estimated = 'Memory reduction, lazy evaluation'
                else:
                    description = 'If only iterating over results without random access, generator expression saves memory'
                    estimated = '50%+ memory reduction'
                
                self.engine.suggestions.append(OptimizationSuggestion(
                    id=self.engine._generate_suggestion_id(),
                    node_id="",
                    category='performance',
                    title='Consider using generator expression',
                    description=description,
                    before_code=before_code,
                    after_code=after_code,
                    estimated_improvement=estimated,
                    auto_fixable=True,
                    priority=3
                ))
        
        visitor = ListCompContextVisitor(self, source_lines)
        visitor.visit(tree)
    
    def _detect_string_concat_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """Detect string concatenation in loops"""
        
        class StringConcatVisitor(ast.NodeVisitor):
            def __init__(self, engine, source_lines):
                self.engine = engine
                self.source_lines = source_lines
                self.in_loop = False
                self.concat_vars = {}
            
            def visit_For(self, node):
                old_in_loop = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old_in_loop
            
            def visit_While(self, node):
                old_in_loop = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old_in_loop
            
            def visit_AugAssign(self, node):
                if self.in_loop and isinstance(node.op, ast.Add):
                    if isinstance(node.target, ast.Name):
                        # Might be string concatenation
                        self.engine.suggestions.append(OptimizationSuggestion(
                            id=self.engine._generate_suggestion_id(),
                            category='performance',
                            title='Optimize string concatenation in loop',
                            description='Using list append + join is more efficient',
                            before_code=self.engine._get_source_segment(node, self.source_lines),
                            after_code=f"# {node.target.id}_parts = []\n# {node.target.id}_parts.append(...)\n# {node.target.id} = ''.join({node.target.id}_parts)",
                            estimated_improvement='5-10x performance improvement',
                            auto_fixable=True,
                            priority=2
                        ))
                self.generic_visit(node)
        
        visitor = StringConcatVisitor(self, source_lines)
        visitor.visit(tree)
    
    def _detect_enumerate_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """Detect range(len()) pattern"""
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                        if node.iter.args:
                            arg = node.iter.args[0]
                            if isinstance(arg, ast.Call):
                                if isinstance(arg.func, ast.Name) and arg.func.id == 'len':
                                    # Check if same suggestion already exists
                                    if self._is_duplicate('Use enumerate() instead of range(len())', node.lineno):
                                        continue
                                    # Found range(len(...)) pattern
                                    self.suggestions.append(OptimizationSuggestion(
                                        id=self._generate_suggestion_id(),
                                        node_id="",
                                        category='readability',
                                        title='Use enumerate() instead of range(len())',
                                        description='enumerate() is more Pythonic, getting both index and value',
                                        before_code=self._get_source_segment(node, source_lines),
                                        after_code="# for i, item in enumerate(sequence):\n#     ...",
                                        estimated_improvement='Improved readability',
                                        auto_fixable=True,
                                        priority=3
                                    ))
    
    def _detect_fstring_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """Detect cases where f-string can be used"""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Mod):
                    if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Tuple):
                        # Check if same suggestion already exists
                        if self._is_duplicate('Consider using f-string', node.lineno):
                            continue
                        # % formatting
                        self.suggestions.append(OptimizationSuggestion(
                            id=self._generate_suggestion_id(),
                            category='readability',
                            title='Consider using f-string',
                            description='f-string is the recommended string formatting method in Python 3.6+',
                            before_code=self._get_source_segment(node, source_lines),
                            after_code="# f\"...{variable}...\"",
                            estimated_improvement='More concise, faster',
                            auto_fixable=True,
                            priority=3
                        ))
            
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'format':
                    if isinstance(node.func.value, ast.Constant):
                        # Check if same suggestion already exists
                        if self._is_duplicate('Consider using f-string', node.lineno):
                            continue
                        # .format() method
                        self.suggestions.append(OptimizationSuggestion(
                            id=self._generate_suggestion_id(),
                            category='readability',
                            title='Consider using f-string',
                            description='f-string is more concise than .format()',
                            before_code=self._get_source_segment(node, source_lines),
                            after_code="# f\"...{variable}...\"",
                            estimated_improvement='More concise, faster',
                            auto_fixable=True,
                            priority=3
                        ))
    
    def _detect_set_lookup_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """Detect membership checks on lists"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for i, op in enumerate(node.ops):
                    if isinstance(op, (ast.In, ast.NotIn)):
                        comparator = node.comparators[i]
                        if isinstance(comparator, ast.List):
                            # Check if same suggestion already exists
                            if self._is_duplicate('Use set for membership check', node.lineno):
                                continue
                            self.suggestions.append(OptimizationSuggestion(
                                id=self._generate_suggestion_id(),
                                category='performance',
                                title='Use set for membership check',
                                description='Set "in" operation is O(1), list is O(n)',
                                before_code=self._get_source_segment(node, source_lines),
                                after_code="# Convert list to set first\n# my_set = set(my_list)\n# if x in my_set: ...",
                                estimated_improvement='O(n) -> O(1)',
                                auto_fixable=True,
                                priority=2
                            ))
    
    def _detect_dataclass_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """Detect classes that can use dataclass"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a simple data class
                has_init = False
                has_repr = False
                has_eq = False
                simple_attributes = []
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name == '__init__':
                            has_init = True
                        elif item.name == '__repr__':
                            has_repr = True
                        elif item.name == '__eq__':
                            has_eq = True
                    elif isinstance(item, ast.AnnAssign):
                        simple_attributes.append(item.target.id if isinstance(item.target, ast.Name) else None)
                
                # If class is mainly data attributes, suggest dataclass
                if len(simple_attributes) > 2 and (has_init or has_repr or has_eq):
                    # Check if same suggestion already exists
                    if self._is_duplicate('Consider using @dataclass', node.lineno):
                        continue
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        category='best_practice',
                        title='Consider using @dataclass',
                        description='Automatically generates __init__, __repr__, __eq__, and other methods',
                        before_code=self._get_source_segment(node, source_lines),
                        after_code="# @dataclass\n# class YourClass:\n#     attr1: type\n#     attr2: type",
                        estimated_improvement='Reduced boilerplate',
                        auto_fixable=False,
                        priority=4
                    ))
    
    def _detect_context_manager_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """Detect cases where context manager should be used"""
        file_methods = {'read', 'write', 'close'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'open':
                    # Check if same suggestion already exists
                    if self._is_duplicate('Use with statement to manage file', node.lineno):
                        continue
                    # Check if "with" is used
                    # Simplified: mark all open calls
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        category='readability',
                        title='Use with statement to manage file',
                        description='Ensures file is properly closed even if exception occurs',
                        before_code=self._get_source_segment(node, source_lines),
                        after_code="# with open(...) as f:\n#     ...",
                        estimated_improvement='Safer, more concise',
                        auto_fixable=False,
                        priority=2
                    ))
    
    def _generate_issue_based_suggestions(self, issues: List[CodeIssue]):
        """Generate targeted suggestions based on issue list"""
        for issue in issues:
            if issue.type == 'security':
                if 'eval' in issue.message:
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        issue_id=issue.id,
                        category='security',
                        title='Replace eval() with safer alternative',
                        description='ast.literal_eval() only parses Python literals, does not execute code',
                        estimated_improvement='Eliminates code injection risk',
                        auto_fixable=True,
                        priority=1
                    ))
                elif 'SQL' in issue.message:
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        issue_id=issue.id,
                        category='security',
                        title='Use parameterized queries',
                        description='Use placeholders and parameter tuples to prevent SQL injection',
                        estimated_improvement='Eliminates SQL injection risk',
                        auto_fixable=False,
                        priority=1
                    ))
            
            elif issue.type == 'complexity':
                if 'cyclomatic complexity' in issue.message or 'cognitive complexity' in issue.message:
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        issue_id=issue.id,
                        category='readability',
                        title='Reduce code complexity',
                        description='Extract methods, use early returns, split conditions',
                        auto_fixable=False,
                        priority=1
                    ))
    
    def _get_source_segment(self, node: ast.AST, source_lines: List[str]) -> str:
        """Get source code segment for node"""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            start = node.lineno - 1
            end = node.end_lineno
            return '\n'.join(source_lines[start:end])
        return ""
    
    def _convert_listcomp_to_genexpr(self, node: ast.ListComp, source_lines: List[str]) -> str:
        """Convert list comprehension to generator expression"""
        source = self._get_source_segment(node, source_lines)
        if source.startswith('[') and source.endswith(']'):
            return '(' + source[1:-1] + ')'
        return source
    
    def get_suggestions_by_category(self) -> Dict[str, List[OptimizationSuggestion]]:
        """Group suggestions by category"""
        grouped = {}
        for suggestion in self.suggestions:
            category = suggestion.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(suggestion)
        return grouped
    
    def get_high_priority_suggestions(self) -> List[OptimizationSuggestion]:
        """Get high priority suggestions"""
        return [s for s in self.suggestions if s.priority <= 2]