"""
Complexity Analyzer - 代码复杂度分析
计算圈复杂度、认知复杂度等指标
"""
import ast
from typing import Dict, List, Any, Optional
from collections import defaultdict
from ..models.schemas import ComplexityMetrics, CodeIssue, SeverityLevel


class ComplexityAnalyzer:
    """代码复杂度分析器"""
    
    # 增加圈复杂度的节点类型
    BRANCHING_NODES = {
        ast.If: 1,
        ast.For: 1,
        ast.While: 1,
        ast.ExceptHandler: 1,
        ast.With: 1,
        ast.Assert: 1,
        ast.comprehension: 1,
    }
    
    # 布尔运算符，每个增加圈复杂度
    BOOLEAN_OPS = {
        ast.And: 1,
        ast.Or: 1,
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
    
    def analyze(self, code: str, tree: Optional[ast.AST] = None) -> ComplexityMetrics:
        """
        分析代码复杂度
        
        Args:
            code: 源代码字符串
            tree: 可选的AST树（避免重复解析）
        
        Returns:
            ComplexityMetrics: 复杂度指标
        """
        # 清空之前的状态，避免累积
        self.issues = []
        
        if tree is None:
            tree = ast.parse(code)
        
        source_lines = code.splitlines()
        
        metrics = ComplexityMetrics(
            lines_of_code=len([l for l in source_lines if l.strip()]),
        )
        
        # 计算各类复杂度
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(tree)
        
        # 统计函数和类
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)
                metrics.function_count += 1
            elif isinstance(node, ast.ClassDef):
                classes.append(node)
                metrics.class_count += 1
        
        # 计算最大嵌套深度
        metrics.max_nesting_depth = self._calculate_max_nesting_depth(tree)
        
        # 计算平均函数长度
        if functions:
            func_lengths = self._get_function_lengths(functions, source_lines)
            metrics.avg_function_length = sum(func_lengths) / len(func_lengths)
        
        # 计算Halstead指标
        halstead = self._calculate_halstead_metrics(tree)
        metrics.halstead_volume = halstead.get('volume', 0)
        metrics.halstead_difficulty = halstead.get('difficulty', 0)
        
        # 计算可维护性指数
        metrics.maintainability_index = self._calculate_maintainability_index(
            metrics, len(code)
        )
        
        # 生成问题报告
        self._generate_issues(metrics, tree)
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """
        计算圈复杂度
        CC = E - N + 2P (简化为分支计数 + 1)
        """
        complexity = 1  # 基础复杂度
        
        for node in ast.walk(tree):
            # 处理分支节点
            node_type = type(node)
            if node_type in self.BRANCHING_NODES:
                complexity += self.BRANCHING_NODES[node_type]
            
            # 处理布尔运算符
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            
            # 处理条件表达式 (三元运算符)
            elif isinstance(node, ast.IfExp):
                complexity += 1
            
            # 处理elif
            elif isinstance(node, ast.If):
                # 统计elif数量
                for child in ast.walk(node):
                    if isinstance(child, ast.If) and child is not node:
                        complexity += 1
        
        return complexity
    
    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """
        计算认知复杂度
        考虑嵌套深度和逻辑运算符
        """
        return self._cognitive_visitor(tree, nesting=0)
    
    def _cognitive_visitor(self, node: ast.AST, nesting: int) -> int:
        """递归计算认知复杂度"""
        complexity = 0
        
        # 增加认知复杂度的结构
        cognitive_structures = (
            ast.If, ast.For, ast.While, ast.ExceptHandler,
            ast.With, ast.IfExp, ast.comprehension
        )
        
        if isinstance(node, cognitive_structures):
            complexity += nesting + 1
            new_nesting = nesting + 1
        else:
            new_nesting = nesting
        
        # 布尔运算符增加复杂度
        if isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        
        # 递归调用增加复杂度
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # 检查是否是递归（简化判断）
                pass
        
        # 递归处理子节点
        for child in ast.iter_child_nodes(node):
            complexity += self._cognitive_visitor(child, new_nesting)
        
        return complexity
    
    def _calculate_max_nesting_depth(self, tree: ast.AST) -> int:
        """计算最大嵌套深度"""
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
        """获取函数长度列表"""
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
        计算Halstead复杂度指标
        基于操作符和操作数的数量
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
            # 统计操作符
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
            
            # 统计操作数
            if isinstance(node, ast.Name):
                operands[node.id] += 1
            elif isinstance(node, ast.Constant):
                operands[str(node.value)] += 1
        
        n1 = len(operators)  # 不同操作符数
        n2 = len(operands)   # 不同操作数数
        N1 = sum(operators.values())  # 操作符总数
        N2 = sum(operands.values())   # 操作数总数
        
        n = n1 + n2  # 词汇量
        N = N1 + N2  # 程序长度
        
        if n == 0:
            return {'volume': 0, 'difficulty': 0}
        
        volume = N * (n.bit_length()) if n > 0 else 0  # 容量
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0  # 难度
        
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
        计算可维护性指数（改进版）
        
        改进点：
        1. 使用多维度评分加权平均
        2. 对特长代码使用渐进式衰减而非直接归零
        3. 考虑代码密度、注释率等因素
        4. 使用分段函数避免极端值
        
        参考：
        - 原始公式: MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        - 改进: 使用加权评分模型
        """
        import math
        
        if code_length == 0:
            return 100.0
        
        # === 1. 复杂度评分 (权重 35%) ===
        # 圈复杂度评分：理想值 1-10，每增加10降低一个等级
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
        
        # 认知复杂度评分
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
        
        # === 2. 代码规模评分 (权重 25%) ===
        # 使用对数衰减，而非线性惩罚
        loc = metrics.lines_of_code or 1
        
        # 分段评估：小代码(<100)、中等代码(100-500)、大代码(500-2000)、超大代码(>2000)
        if loc <= 100:
            size_score = 100
        elif loc <= 500:
            # 中等代码：轻微衰减
            size_score = 100 - 10 * math.log10(loc / 100)
        elif loc <= 2000:
            # 大代码：中等衰减
            size_score = 90 - 15 * math.log10(loc / 500)
        else:
            # 超大代码：渐进衰减，不会直接归零
            size_score = max(20, 75 - 20 * math.log10(loc / 2000))
        
        # 嵌套深度惩罚
        nesting = metrics.max_nesting_depth or 0
        nesting_penalty = min(30, nesting * 5) if nesting > 3 else 0
        size_score = max(0, size_score - nesting_penalty)
        
        # === 3. 函数质量评分 (权重 25%) ===
        func_score = 100
        
        if metrics.function_count > 0:
            # 平均函数长度评分
            avg_len = metrics.avg_function_length or 0
            if avg_len <= 20:
                func_len_score = 100
            elif avg_len <= 50:
                func_len_score = 100 - (avg_len - 20) * 1.5
            else:
                func_len_score = max(20, 55 - (avg_len - 50) * 0.5)
            
            func_score = func_len_score
        else:
            # 没有函数的代码（可能是脚本），使用行数评估
            if loc <= 50:
                func_score = 100
            else:
                func_score = max(40, 100 - (loc - 50) * 0.3)
        
        # === 4. Halstead 复杂度评分 (权重 15%) ===
        volume = metrics.halstead_volume or 0
        difficulty = metrics.halstead_difficulty or 0
        
        if volume == 0:
            halstead_score = 100
        else:
            # Volume 评分（对数衰减）
            if volume <= 100:
                vol_score = 100
            elif volume <= 1000:
                vol_score = 100 - 15 * math.log10(volume / 100)
            else:
                vol_score = max(30, 85 - 20 * math.log10(volume / 1000))
            
            # Difficulty 评分
            if difficulty <= 5:
                diff_score = 100
            elif difficulty <= 15:
                diff_score = 100 - (difficulty - 5) * 5
            else:
                diff_score = max(20, 50 - (difficulty - 15) * 2)
            
            halstead_score = vol_score * 0.6 + diff_score * 0.4
        
        # === 综合评分 ===
        final_score = (
            complexity_score * 0.35 +
            size_score * 0.25 +
            func_score * 0.25 +
            halstead_score * 0.15
        )
        
        # 确保范围在 0-100
        final_score = max(0, min(100, final_score))
        
        return round(final_score, 2)
    
    def _generate_issues(self, metrics: ComplexityMetrics, tree: ast.AST):
        """根据复杂度指标生成问题报告"""
        
        # 圈复杂度过高
        if metrics.cyclomatic_complexity > 15:
            self.issues.append(CodeIssue(
                id="complexity_cyclomatic_high",
                type="complexity",
                severity=SeverityLevel.ERROR if metrics.cyclomatic_complexity > 25 else SeverityLevel.WARNING,
                message=f"圈复杂度过高 ({metrics.cyclomatic_complexity})，建议拆分函数或简化逻辑",
                documentation_url="https://en.wikipedia.org/wiki/Cyclomatic_complexity"
            ))
        
        # 认知复杂度过高
        if metrics.cognitive_complexity > 15:
            self.issues.append(CodeIssue(
                id="complexity_cognitive_high",
                type="complexity",
                severity=SeverityLevel.WARNING,
                message=f"认知复杂度过高 ({metrics.cognitive_complexity})，代码可能难以理解",
            ))
        
        # 嵌套过深
        if metrics.max_nesting_depth > 4:
            self.issues.append(CodeIssue(
                id="complexity_nesting_deep",
                type="complexity",
                severity=SeverityLevel.ERROR if metrics.max_nesting_depth > 6 else SeverityLevel.WARNING,
                message=f"嵌套层级过深 ({metrics.max_nesting_depth}层)，建议提取方法或使用早返回",
            ))
        
        # 函数过长
        if metrics.avg_function_length > 50:
            self.issues.append(CodeIssue(
                id="complexity_function_long",
                type="complexity",
                severity=SeverityLevel.WARNING,
                message=f"平均函数长度过长 ({metrics.avg_function_length:.0f}行)，建议拆分大函数",
            ))
        
        # 可维护性指数过低
        if metrics.maintainability_index < 20:
            self.issues.append(CodeIssue(
                id="complexity_maintainability_low",
                type="complexity",
                severity=SeverityLevel.ERROR if metrics.maintainability_index < 10 else SeverityLevel.WARNING,
                message=f"可维护性指数过低 ({metrics.maintainability_index:.1f})，代码需要重构",
            ))
    
    def get_issues(self) -> List[CodeIssue]:
        """获取问题列表"""
        return self.issues
    
    def analyze_function(self, func_node: ast.AST, source_lines: List[str]) -> Dict[str, Any]:
        """
        分析单个函数的复杂度
        
        Args:
            func_node: 函数AST节点
            source_lines: 源代码行列表
        
        Returns:
            函数复杂度分析结果
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
        
        # 计算函数级别的圈复杂度
        for node in ast.walk(func_node):
            node_type = type(node)
            if node_type in self.BRANCHING_NODES:
                result["cyclomatic_complexity"] += self.BRANCHING_NODES[node_type]
            elif isinstance(node, ast.BoolOp):
                result["cyclomatic_complexity"] += len(node.values) - 1
            elif isinstance(node, ast.IfExp):
                result["cyclomatic_complexity"] += 1
        
        # 计算函数嵌套深度
        result["nesting_depth"] = self._calculate_max_nesting_depth(func_node)
        
        # 计算认知复杂度
        result["cognitive_complexity"] = self._cognitive_visitor(func_node, 0)
        
        # 函数行数
        if hasattr(func_node, 'end_lineno'):
            result["lines"] = func_node.end_lineno - func_node.lineno + 1
        
        return result
