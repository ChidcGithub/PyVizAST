"""
Suggestion Engine - 优化建议生成引擎
基于分析结果生成具体的重构建议
"""
import ast
import re
from typing import List, Dict, Any, Optional
from ..models.schemas import OptimizationSuggestion, CodeIssue, SeverityLevel


class SuggestionEngine:
    """优化建议生成引擎"""
    
    # 优化规则库
    RULES = {
        # 性能优化规则
        'list_comp_to_gen': {
            'category': 'performance',
            'title': '使用生成器表达式替代列表推导式',
            'description': '当只需要遍历结果而不需要索引访问时，生成器表达式更节省内存',
            'auto_fixable': True,
            'priority': 2,
        },
        'string_concat': {
            'category': 'performance',
            'title': '使用join()替代循环中的字符串拼接',
            'description': '字符串是不可变的，循环中的+=操作会创建大量临时对象',
            'auto_fixable': True,
            'priority': 2,
        },
        'use_local_variable': {
            'category': 'performance',
            'title': '将全局查找缓存为局部变量',
            'description': '在循环中访问全局变量或方法会增加查找开销',
            'auto_fixable': False,
            'priority': 3,
        },
        'use_set_for_lookup': {
            'category': 'performance',
            'title': '使用集合替代列表进行成员检查',
            'description': '集合的成员检查是O(1)，而列表是O(n)',
            'auto_fixable': True,
            'priority': 2,
        },
        
        # 可读性规则
        'use_enumerate': {
            'category': 'readability',
            'title': '使用enumerate()替代range(len())',
            'description': 'enumerate()更Pythonic且更易读',
            'auto_fixable': True,
            'priority': 3,
        },
        'use_fstring': {
            'category': 'readability',
            'title': '使用f-string替代%或.format()',
            'description': 'f-string更简洁、更快、更易读',
            'auto_fixable': True,
            'priority': 3,
        },
        'use_context_manager': {
            'category': 'readability',
            'title': '使用with语句管理资源',
            'description': '确保资源正确释放，避免资源泄漏',
            'auto_fixable': False,
            'priority': 2,
        },
        'extract_method': {
            'category': 'readability',
            'title': '提取方法以降低复杂度',
            'description': '将复杂逻辑拆分为更小的、有命名的方法',
            'auto_fixable': False,
            'priority': 1,
        },
        
        # 安全规则
        'parametrize_sql': {
            'category': 'security',
            'title': '使用参数化查询',
            'description': '防止SQL注入攻击',
            'auto_fixable': False,
            'priority': 1,
        },
        'use_literal_eval': {
            'category': 'security',
            'title': '使用ast.literal_eval()替代eval()',
            'description': 'ast.literal_eval()只解析字面量，更安全',
            'auto_fixable': True,
            'priority': 1,
        },
        
        # 最佳实践规则
        'use_dataclass': {
            'category': 'best_practice',
            'title': '考虑使用@dataclass装饰器',
            'description': '自动生成__init__、__repr__等方法，减少样板代码',
            'auto_fixable': False,
            'priority': 4,
        },
        'add_type_hints': {
            'category': 'best_practice',
            'title': '添加类型注解',
            'description': '提高代码可读性和IDE支持',
            'auto_fixable': False,
            'priority': 4,
        },
        'use_walrus_operator': {
            'category': 'best_practice',
            'title': '考虑使用海象运算符(:=)',
            'description': '在表达式内部赋值，简化代码',
            'auto_fixable': False,
            'priority': 5,
        },
    }
    
    def __init__(self):
        self.suggestions: List[OptimizationSuggestion] = []
        self.suggestion_counter = 0
    
    def _generate_suggestion_id(self) -> str:
        self.suggestion_counter += 1
        return f"suggestion_{self.suggestion_counter}"
    
    def generate_suggestions(
        self, 
        code: str, 
        tree: Optional[ast.AST] = None,
        issues: Optional[List[CodeIssue]] = None
    ) -> List[OptimizationSuggestion]:
        """
        根据代码和问题列表生成优化建议
        
        Args:
            code: 源代码字符串
            tree: 可选的AST树
            issues: 可选的问题列表
        
        Returns:
            优化建议列表
        """
        if tree is None:
            tree = ast.parse(code)
        
        self.suggestions = []
        self.suggestion_counter = 0
        
        source_lines = code.splitlines()
        
        # 根据AST结构生成建议
        self._detect_list_comp_opportunities(tree, source_lines)
        self._detect_string_concat_opportunities(tree, source_lines)
        self._detect_enumerate_opportunities(tree, source_lines)
        self._detect_fstring_opportunities(tree, source_lines)
        self._detect_set_lookup_opportunities(tree, source_lines)
        self._detect_dataclass_opportunities(tree, source_lines)
        self._detect_context_manager_opportunities(tree, source_lines)
        
        # 根据问题列表生成针对性建议
        if issues:
            self._generate_issue_based_suggestions(issues)
        
        return self.suggestions
    
    def _detect_list_comp_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """
        检测可以用生成器替代的列表推导式
        
        只有在以下场景才建议转换为生成器表达式：
        1. 作为函数参数传递，且该函数只遍历一次（如 sum, any, all, max, min, join, sorted）
        2. 直接用于迭代且不会被多次使用
        
        不建议转换的场景：
        1. 赋值给变量（可能多次遍历或索引访问）
        2. 作为返回值
        3. 在需要 len() 的上下文中
        """
        
        # 只遍历一次的函数（适合生成器）
        SINGLE_PASS_FUNCTIONS = {
            'sum', 'any', 'all', 'max', 'min', 'sorted', 'reversed',
            'list', 'tuple', 'set', 'dict', 'frozenset',
            ''.join.__name__: 'join',  # 字符串 join
            'map', 'filter', 'enumerate', 'zip',
            'heapq.nlargest', 'heapq.nsmallest',
            'itertools.chain', 'itertools.islice',
        }
        
        # 需要多次访问或多功能的函数（不适合生成器）
        MULTI_PASS_FUNCTIONS = {'len', 'copy', 'deepcopy'}
        
        class ListCompContextVisitor(ast.NodeVisitor):
            def __init__(self, engine, lines):
                self.engine = engine
                self.lines = lines
                self.suggestions_added = set()  # 避免重复建议
            
            def visit_Call(self, node):
                """检查列表推导式作为函数参数的情况"""
                
                # 检查函数名
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                if func_name in SINGLE_PASS_FUNCTIONS:
                    # 检查参数中是否有列表推导式
                    for arg in node.args:
                        if isinstance(arg, ast.ListComp):
                            self._add_suggestion(arg, node, 'function_arg', func_name)
                
                # 继续遍历子节点
                self.generic_visit(node)
            
            def visit_For(self, node):
                """检查 for 循环中直接使用列表推导式迭代的情况"""
                
                # 检查迭代器是否是列表推导式
                if isinstance(node.iter, ast.ListComp):
                    # 检查这个 for 循环是否在函数内且结果不会被保存
                    # 这通常可以转换为生成器
                    self._add_suggestion(node.iter, node, 'for_iter')
                
                self.generic_visit(node)
            
            def _add_suggestion(self, listcomp_node, parent_node, context, func_name=None):
                """添加优化建议"""
                
                # 避免重复建议同一个节点
                node_key = (listcomp_node.lineno, listcomp_node.col_offset)
                if node_key in self.suggestions_added:
                    return
                self.suggestions_added.add(node_key)
                
                before_code = self.engine._get_source_segment(listcomp_node, self.lines)
                after_code = self.engine._convert_listcomp_to_genexpr(listcomp_node, self.lines)
                
                # 根据上下文生成不同的描述
                if context == 'function_arg':
                    description = (
                        f"作为 `{func_name}()` 的参数时，生成器表达式更节省内存，"
                        f"因为函数只会遍历一次"
                    )
                    estimated = '内存使用减少50%+'
                elif context == 'for_iter':
                    description = (
                        "作为 for 循环的迭代器时，生成器表达式可以延迟计算，"
                        "节省内存。但如果循环内有 break 或多次迭代，需谨慎"
                    )
                    estimated = '内存使用减少，惰性计算'
                else:
                    description = '如果只需要遍历结果而不需要随机访问，生成器表达式更节省内存'
                    estimated = '内存使用减少50%+'
                
                self.engine.suggestions.append(OptimizationSuggestion(
                    id=self.engine._generate_suggestion_id(),
                    node_id="",
                    category='performance',
                    title='考虑使用生成器表达式',
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
        """检测循环中的字符串拼接"""
        
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
                        # 可能是字符串拼接
                        self.engine.suggestions.append(OptimizationSuggestion(
                            id=self.engine._generate_suggestion_id(),
                            category='performance',
                            title='优化循环中的字符串拼接',
                            description='使用列表append + join更高效',
                            before_code=self.engine._get_source_segment(node, self.source_lines),
                            after_code=f"# {node.target.id}_parts = []\n# {node.target.id}_parts.append(...)\n# {node.target.id} = ''.join({node.target.id}_parts)",
                            estimated_improvement='性能提升5-10倍',
                            auto_fixable=True,
                            priority=2
                        ))
                self.generic_visit(node)
        
        visitor = StringConcatVisitor(self, source_lines)
        visitor.visit(tree)
    
    def _detect_enumerate_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """检测range(len())模式"""
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                        if node.iter.args:
                            arg = node.iter.args[0]
                            if isinstance(arg, ast.Call):
                                if isinstance(arg.func, ast.Name) and arg.func.id == 'len':
                                    # 找到range(len(...))模式
                                    self.suggestions.append(OptimizationSuggestion(
                                        id=self._generate_suggestion_id(),
                                        node_id="",
                                        category='readability',
                                        title='使用enumerate()替代range(len())',
                                        description='enumerate()更Pythonic，同时获取索引和值',
                                        before_code=self._get_source_segment(node, source_lines),
                                        after_code="# for i, item in enumerate(sequence):\n#     ...",
                                        estimated_improvement='可读性提升',
                                        auto_fixable=True,
                                        priority=3
                                    ))
    
    def _detect_fstring_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """检测可以使用f-string的情况"""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Mod):
                    if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Tuple):
                        # % 格式化
                        self.suggestions.append(OptimizationSuggestion(
                            id=self._generate_suggestion_id(),
                            category='readability',
                            title='考虑使用f-string',
                            description='f-string是Python 3.6+推荐的字串格式化方式',
                            before_code=self._get_source_segment(node, source_lines),
                            after_code="# f\"...{variable}...\"",
                            estimated_improvement='更简洁、更快',
                            auto_fixable=True,
                            priority=3
                        ))
            
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'format':
                    if isinstance(node.func.value, ast.Constant):
                        # .format() 方法
                        self.suggestions.append(OptimizationSuggestion(
                            id=self._generate_suggestion_id(),
                            category='readability',
                            title='考虑使用f-string',
                            description='f-string比.format()更简洁',
                            before_code=self._get_source_segment(node, source_lines),
                            after_code="# f\"...{variable}...\"",
                            estimated_improvement='更简洁、更快',
                            auto_fixable=True,
                            priority=3
                        ))
    
    def _detect_set_lookup_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """检测对列表的成员检查"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for i, op in enumerate(node.ops):
                    if isinstance(op, (ast.In, ast.NotIn)):
                        comparator = node.comparators[i]
                        if isinstance(comparator, ast.List):
                            self.suggestions.append(OptimizationSuggestion(
                                id=self._generate_suggestion_id(),
                                category='performance',
                                title='使用集合进行成员检查',
                                description='集合的in操作是O(1)，列表是O(n)',
                                before_code=self._get_source_segment(node, source_lines),
                                after_code="# 先将列表转换为集合\n# my_set = set(my_list)\n# if x in my_set: ...",
                                estimated_improvement='O(n) -> O(1)',
                                auto_fixable=True,
                                priority=2
                            ))
    
    def _detect_dataclass_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """检测可以使用dataclass的类"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查是否是简单的数据类
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
                
                # 如果类主要是数据属性，建议使用dataclass
                if len(simple_attributes) > 2 and (has_init or has_repr or has_eq):
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        category='best_practice',
                        title='考虑使用@dataclass',
                        description='自动生成__init__、__repr__、__eq__等方法',
                        before_code=self._get_source_segment(node, source_lines),
                        after_code="# @dataclass\n# class YourClass:\n#     attr1: type\n#     attr2: type",
                        estimated_improvement='减少样板代码',
                        auto_fixable=False,
                        priority=4
                    ))
    
    def _detect_context_manager_opportunities(self, tree: ast.AST, source_lines: List[str]):
        """检测应该使用上下文管理器的情况"""
        file_methods = {'read', 'write', 'close'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'open':
                    # 检查是否使用了with
                    # 简化：标记所有open调用
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        category='readability',
                        title='使用with语句管理文件',
                        description='确保文件正确关闭，即使发生异常',
                        before_code=self._get_source_segment(node, source_lines),
                        after_code="# with open(...) as f:\n#     ...",
                        estimated_improvement='更安全、更简洁',
                        auto_fixable=False,
                        priority=2
                    ))
    
    def _generate_issue_based_suggestions(self, issues: List[CodeIssue]):
        """根据问题列表生成针对性建议"""
        for issue in issues:
            if issue.type == 'security':
                if 'eval' in issue.message:
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        issue_id=issue.id,
                        category='security',
                        title='替换eval()为更安全的替代方案',
                        description='ast.literal_eval()只解析Python字面量，不会执行代码',
                        estimated_improvement='消除代码注入风险',
                        auto_fixable=True,
                        priority=1
                    ))
                elif 'SQL' in issue.message:
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        issue_id=issue.id,
                        category='security',
                        title='使用参数化查询',
                        description='使用占位符和参数元组防止SQL注入',
                        estimated_improvement='消除SQL注入风险',
                        auto_fixable=False,
                        priority=1
                    ))
            
            elif issue.type == 'complexity':
                if '圈复杂度' in issue.message or '认知复杂度' in issue.message:
                    self.suggestions.append(OptimizationSuggestion(
                        id=self._generate_suggestion_id(),
                        issue_id=issue.id,
                        category='readability',
                        title='降低代码复杂度',
                        description='提取方法、使用早返回、拆分条件',
                        auto_fixable=False,
                        priority=1
                    ))
    
    def _get_source_segment(self, node: ast.AST, source_lines: List[str]) -> str:
        """获取节点的源代码片段"""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            start = node.lineno - 1
            end = node.end_lineno
            return '\n'.join(source_lines[start:end])
        return ""
    
    def _convert_listcomp_to_genexpr(self, node: ast.ListComp, source_lines: List[str]) -> str:
        """将列表推导式转换为生成器表达式"""
        source = self._get_source_segment(node, source_lines)
        if source.startswith('[') and source.endswith(']'):
            return '(' + source[1:-1] + ')'
        return source
    
    def get_suggestions_by_category(self) -> Dict[str, List[OptimizationSuggestion]]:
        """按类别分组建议"""
        grouped = {}
        for suggestion in self.suggestions:
            category = suggestion.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(suggestion)
        return grouped
    
    def get_high_priority_suggestions(self) -> List[OptimizationSuggestion]:
        """获取高优先级建议"""
        return [s for s in self.suggestions if s.priority <= 2]
