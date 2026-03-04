"""
Complexity Analyzer - Code complexity analysis
Calculates cyclomatic complexity, cognitive complexity, and other metrics
"""
import ast
from typing import Dict, List, Any, Optional
from collections import defaultdict
from ..models.schemas import ComplexityMetrics, CodeIssue, SeverityLevel


class ComplexityAnalyzer:
    """Code Complexity Analyzer"""
    
    # Node types that increase cyclomatic complexity
    BRANCHING_NODES = {
        ast.If: 1,
        ast.For: 1,
        ast.While: 1,
        ast.ExceptHandler: 1,
        ast.With: 1,
        ast.Assert: 1,
        ast.comprehension: 1,
    }
    
    # Boolean operators, each increases cyclomatic complexity
    BOOLEAN_OPS = {
        ast.And: 1,
        ast.Or: 1,
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
    
    def analyze(self, code: str, tree: Optional[ast.AST] = None) -> ComplexityMetrics:
        """
        Analyze code complexity
        
        Args:
            code: Source code string
            tree: Optional AST tree (avoid re-parsing)
        
        Returns:
            ComplexityMetrics: Complexity metrics
        """
        # Clear previous state to avoid accumulation
        self.issues = []
        
        if tree is None:
            tree = ast.parse(code)
        
        source_lines = code.splitlines()
        
        metrics = ComplexityMetrics(
            lines_of_code=len([l for l in source_lines if l.strip()]),
        )
        
        # Calculate various complexity metrics
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(tree)
        
        # Count functions and classes
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)
                metrics.function_count += 1
            elif isinstance(node, ast.ClassDef):
                classes.append(node)
                metrics.class_count += 1
        
        # Calculate maximum nesting depth
        metrics.max_nesting_depth = self._calculate_max_nesting_depth(tree)
        
        # Calculate average function length
        if functions:
            func_lengths = self._get_function_lengths(functions, source_lines)
            metrics.avg_function_length = sum(func_lengths) / len(func_lengths)
        
        # Calculate Halstead metrics
        halstead = self._calculate_halstead_metrics(tree)
        metrics.halstead_volume = halstead.get('volume', 0)
        metrics.halstead_difficulty = halstead.get('difficulty', 0)
        
        # Calculate maintainability index
        metrics.maintainability_index = self._calculate_maintainability_index(
            metrics, len(code)
        )
        
        # Generate issue reports
        self._generate_issues(metrics, tree)
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """
        Calculate cyclomatic complexity
        CC = E - N + 2P (simplified to branch count + 1)
        
        Note: elif is represented in AST as an If node in the orelse list of another If node,
        each elif is itself an independent If node and will be traversed by ast.walk.
        """
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            # Handle branching nodes
            node_type = type(node)
            if node_type in self.BRANCHING_NODES:
                complexity += self.BRANCHING_NODES[node_type]
            
            # Handle boolean operators (each and/or increases complexity)
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            
            # Handle conditional expressions (ternary operator)
            elif isinstance(node, ast.IfExp):
                complexity += 1
        
        return complexity
    
    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """
        Calculate cognitive complexity
        Considers nesting depth, logical operators, and recursion
        """
        total_complexity = 0
        
        # Use a visitor that tracks function context for recursion detection
        class CognitiveVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 0
                self.nesting = 0
                self.current_function = None  # Track current function name
            
            def _visit_with_nesting(self, node, visit_body=True):
                """Visit a node that increases nesting"""
                self.complexity += self.nesting + 1
                self.nesting += 1
                self.generic_visit(node)
                self.nesting -= 1
            
            def visit_FunctionDef(self, node):
                old_func = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = old_func
            
            def visit_AsyncFunctionDef(self, node):
                old_func = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = old_func
            
            def visit_If(self, node):
                self._visit_with_nesting(node)
            
            def visit_For(self, node):
                self._visit_with_nesting(node)
            
            def visit_While(self, node):
                self._visit_with_nesting(node)
            
            def visit_ExceptHandler(self, node):
                self._visit_with_nesting(node)
            
            def visit_With(self, node):
                self._visit_with_nesting(node)
            
            def visit_IfExp(self, node):  # Ternary operator
                self.complexity += self.nesting + 1
                self.generic_visit(node)
            
            def visit_BoolOp(self, node):
                # Each additional operand in and/or adds complexity
                self.complexity += len(node.values) - 1
                self.generic_visit(node)
            
            def visit_Call(self, node):
                # Check for recursive calls
                if self.current_function:
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        # Method call like self.func()
                        if node.func.attr == self.current_function:
                            self.complexity += 1  # Recursive call
                    if func_name == self.current_function:
                        self.complexity += 1  # Direct recursion
                self.generic_visit(node)
        
        visitor = CognitiveVisitor()
        visitor.visit(tree)
        return visitor.complexity
    
    def _cognitive_visitor(self, node: ast.AST, nesting: int) -> int:
        """Recursively calculate cognitive complexity (legacy method, kept for compatibility)"""
        complexity = 0
        
        # Structures that increase cognitive complexity
        cognitive_structures = (
            ast.If, ast.For, ast.While, ast.ExceptHandler,
            ast.With, ast.IfExp, ast.comprehension
        )
        
        if isinstance(node, cognitive_structures):
            complexity += nesting + 1
            new_nesting = nesting + 1
        else:
            new_nesting = nesting
        
        # Boolean operators increase complexity
        if isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        
        # Recursively process child nodes
        for child in ast.iter_child_nodes(node):
            complexity += self._cognitive_visitor(child, new_nesting)
        
        return complexity
    
    def _calculate_max_nesting_depth(self, tree: ast.AST) -> int:
        """Calculate maximum nesting depth"""
        max_depth = [0]
        
        def visit(node: ast.AST, depth: int):
            nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
            
            if isinstance(node, nesting_nodes):
                depth += 1
                max_depth[0] = max(max_depth[0], depth)
            
            for child in ast.iter_child_nodes(node):
                visit(child, depth)
        
        visit(tree, 0)
        return max_depth[0]
    
    def _get_function_lengths(self, functions: List[ast.AST], 
                              source_lines: List[str]) -> List[int]:
        """Get list of function lengths"""
        lengths = []
        for func in functions:
            if hasattr(func, 'end_lineno') and hasattr(func, 'lineno'):
                length = func.end_lineno - func.lineno + 1
                lengths.append(length)
            else:
                lengths.append(1)
        return lengths
    
    def _calculate_halstead_metrics(self, tree: ast.AST) -> Dict[str, float]:
        """
        Calculate Halstead complexity metrics
        Based on the number of operators and operands
        """
        operators = defaultdict(int)
        operands = defaultdict(int)
        
        operator_types = {
            ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/',
            ast.Mod: '%', ast.Pow: '**', ast.LShift: '<<', ast.RShift: '>>',
            ast.BitOr: '|', ast.BitXor: '^', ast.BitAnd: '&',
            ast.FloorDiv: '//', ast.MatMult: '@',
            ast.And: 'and', ast.Or: 'or', ast.Not: 'not',
            ast.Invert: '~', ast.UAdd: '+', ast.USub: '-',
            ast.Eq: '==', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=',
            ast.Gt: '>', ast.GtE: '>=', ast.Is: 'is', ast.IsNot: 'is not',
            ast.In: 'in', ast.NotIn: 'not in',
        }
        
        for node in ast.walk(tree):
            # Count operators
            node_type = type(node)
            if node_type in operator_types:
                operators[operator_types[node_type]] += 1
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                operators['='] += 1
            elif isinstance(node, ast.Call):
                operators['()'] += 1
            elif isinstance(node, ast.Subscript):
                operators['[]'] += 1
            elif isinstance(node, (ast.If, ast.While, ast.For)):
                operators['keyword'] += 1
            
            # Count operands
            if isinstance(node, ast.Name):
                operands[node.id] += 1
            elif isinstance(node, ast.Constant):
                operands[str(node.value)] += 1
        
        n1 = len(operators)  # Number of distinct operators
        n2 = len(operands)   # Number of distinct operands
        N1 = sum(operators.values())  # Total operators
        N2 = sum(operands.values())   # Total operands
        
        n = n1 + n2  # Vocabulary
        N = N1 + N2  # Program length
        
        if n == 0:
            return {'volume': 0, 'difficulty': 0}
        
        volume = N * (n.bit_length()) if n > 0 else 0  # Volume
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0  # Difficulty
        
        return {
            'volume': volume,
            'difficulty': difficulty,
            'vocabulary': n,
            'length': N,
            'effort': volume * difficulty,
        }
    
    def _calculate_maintainability_index(self, metrics: ComplexityMetrics, 
                                         code_length: int) -> float:
        """
        Calculate maintainability index (improved version)
        
        Improvements:
        1. Use multi-dimensional weighted average scoring
        2. Use progressive decay for very long code instead of going to zero
        3. Consider code density, comment ratio, etc.
        4. Use piecewise functions to avoid extreme values
        
        Reference:
        - Original formula: MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        - Improved: Use weighted scoring model
        """
        import math
        
        if code_length == 0:
            return 100.0
        
        # === 1. Complexity score (weight 35%) ===
        # Cyclomatic complexity score: ideal value 1-10, decreases one level for every 10 increase
        cc = metrics.cyclomatic_complexity or 1
        if cc <= 5:
            cc_score = 100
        elif cc <= 10:
            cc_score = 90 - (cc - 5) * 4  # 90 -> 70
        elif cc <= 20:
            cc_score = 70 - (cc - 10) * 4  # 70 -> 30
        elif cc <= 30:
            cc_score = 30 - (cc - 20) * 2  # 30 -> 10
        else:
            cc_score = max(0, 10 - (cc - 30) * 0.5)
        
        # Cognitive complexity score
        cognitive = metrics.cognitive_complexity or 0
        if cognitive <= 10:
            cog_score = 100
        elif cognitive <= 20:
            cog_score = 90 - (cognitive - 10) * 4
        elif cognitive <= 40:
            cog_score = 50 - (cognitive - 20) * 2
        else:
            cog_score = max(0, 10 - (cognitive - 40) * 0.3)
        
        complexity_score = cc_score * 0.6 + cog_score * 0.4
        
        # === 2. Code size score (weight 25%) ===
        # Use logarithmic decay instead of linear penalty
        loc = metrics.lines_of_code or 1
        
        # Piecewise evaluation: small code (<100), medium code (100-500), large code (500-2000), huge code (>2000)
        if loc <= 100:
            size_score = 100
        elif loc <= 500:
            # Medium code: slight decay
            size_score = 100 - 10 * math.log10(loc / 100)
        elif loc <= 2000:
            # Large code: moderate decay
            size_score = 90 - 15 * math.log10(loc / 500)
        else:
            # Huge code: progressive decay, won't go to zero
            size_score = max(20, 75 - 20 * math.log10(loc / 2000))
        
        # Nesting depth penalty
        nesting = metrics.max_nesting_depth or 0
        nesting_penalty = min(30, nesting * 5) if nesting > 3 else 0
        size_score = max(0, size_score - nesting_penalty)
        
        # === 3. Function quality score (weight 25%) ===
        func_score = 100
        
        if metrics.function_count > 0:
            # Average function length score
            avg_len = metrics.avg_function_length or 0
            if avg_len <= 20:
                func_len_score = 100
            elif avg_len <= 50:
                func_len_score = 100 - (avg_len - 20) * 1.5
            else:
                func_len_score = max(20, 55 - (avg_len - 50) * 0.5)
            
            func_score = func_len_score
        else:
            # Code without functions (possibly a script), evaluate by line count
            if loc <= 50:
                func_score = 100
            else:
                func_score = max(40, 100 - (loc - 50) * 0.3)
        
        # === 4. Halstead complexity score (weight 15%) ===
        volume = metrics.halstead_volume or 0
        difficulty = metrics.halstead_difficulty or 0
        
        if volume == 0:
            halstead_score = 100
        else:
            # Volume score (logarithmic decay)
            if volume <= 100:
                vol_score = 100
            elif volume <= 1000:
                vol_score = 100 - 15 * math.log10(volume / 100)
            else:
                vol_score = max(30, 85 - 20 * math.log10(volume / 1000))
            
            # Difficulty score
            if difficulty <= 5:
                diff_score = 100
            elif difficulty <= 15:
                diff_score = 100 - (difficulty - 5) * 5
            else:
                diff_score = max(20, 50 - (difficulty - 15) * 2)
            
            halstead_score = vol_score * 0.6 + diff_score * 0.4
        
        # === Final score ===
        final_score = (
            complexity_score * 0.35 +
            size_score * 0.25 +
            func_score * 0.25 +
            halstead_score * 0.15
        )
        
        # Ensure range is 0-100
        final_score = max(0, min(100, final_score))
        
        return round(final_score, 2)
    
    def _generate_issues(self, metrics: ComplexityMetrics, tree: ast.AST):
        """Generate issue reports based on complexity metrics"""
        
        # High cyclomatic complexity
        if metrics.cyclomatic_complexity > 15:
            self.issues.append(CodeIssue(
                id="complexity_cyclomatic_high",
                type="complexity",
                severity=SeverityLevel.ERROR if metrics.cyclomatic_complexity > 25 else SeverityLevel.WARNING,
                message=f"High cyclomatic complexity ({metrics.cyclomatic_complexity}), consider splitting functions or simplifying logic",
                documentation_url="https://en.wikipedia.org/wiki/Cyclomatic_complexity"
            ))
        
        # High cognitive complexity
        if metrics.cognitive_complexity > 15:
            self.issues.append(CodeIssue(
                id="complexity_cognitive_high",
                type="complexity",
                severity=SeverityLevel.WARNING,
                message=f"High cognitive complexity ({metrics.cognitive_complexity}), code may be hard to understand",
            ))
        
        # Deep nesting
        if metrics.max_nesting_depth > 4:
            self.issues.append(CodeIssue(
                id="complexity_nesting_deep",
                type="complexity",
                severity=SeverityLevel.ERROR if metrics.max_nesting_depth > 6 else SeverityLevel.WARNING,
                message=f"Deep nesting ({metrics.max_nesting_depth} levels), consider extracting methods or using early returns",
            ))
        
        # Long functions
        if metrics.avg_function_length > 50:
            self.issues.append(CodeIssue(
                id="complexity_function_long",
                type="complexity",
                severity=SeverityLevel.WARNING,
                message=f"Average function length is too long ({metrics.avg_function_length:.0f} lines), consider splitting large functions",
            ))
        
        # Low maintainability index
        if metrics.maintainability_index < 20:
            self.issues.append(CodeIssue(
                id="complexity_maintainability_low",
                type="complexity",
                severity=SeverityLevel.ERROR if metrics.maintainability_index < 10 else SeverityLevel.WARNING,
                message=f"Low maintainability index ({metrics.maintainability_index:.1f}), code needs refactoring",
            ))
    
    def get_issues(self) -> List[CodeIssue]:
        """Get issue list"""
        return self.issues
    
    def analyze_function(self, func_node: ast.AST, source_lines: List[str]) -> Dict[str, Any]:
        """
        Analyze complexity of a single function
        
        Args:
            func_node: Function AST node
            source_lines: Source code line list
        
        Returns:
            Function complexity analysis result
        """
        result = {
            "name": func_node.name,
            "lineno": func_node.lineno,
            "cyclomatic_complexity": 1,
            "cognitive_complexity": 0,
            "nesting_depth": 0,
            "lines": 0,
            "parameters": len(func_node.args.args),
            "has_docstring": bool(ast.get_docstring(func_node)),
        }
        
        # Calculate function-level cyclomatic complexity
        for node in ast.walk(func_node):
            node_type = type(node)
            if node_type in self.BRANCHING_NODES:
                result["cyclomatic_complexity"] += self.BRANCHING_NODES[node_type]
            elif isinstance(node, ast.BoolOp):
                result["cyclomatic_complexity"] += len(node.values) - 1
            elif isinstance(node, ast.IfExp):
                result["cyclomatic_complexity"] += 1
        
        # Calculate function nesting depth
        result["nesting_depth"] = self._calculate_max_nesting_depth(func_node)
        
        # Calculate cognitive complexity
        result["cognitive_complexity"] = self._cognitive_visitor(func_node, 0)
        
        # Function line count
        if hasattr(func_node, 'end_lineno'):
            result["lines"] = func_node.end_lineno - func_node.lineno + 1
        
        return result