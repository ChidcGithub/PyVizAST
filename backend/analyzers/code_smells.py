"""
Code Smell Detector - 代码异味检测
检测过长函数、上帝类、重复代码等
"""
import ast
from typing import List, Dict, Any, Optional
from collections import Counter
from ..models.schemas import CodeIssue, SeverityLevel


class CodeSmellDetector:
    """代码异味检测器"""
    
    # 配置阈值
    CONFIG = {
        'max_function_lines': 50,
        'max_function_params': 5,
        'max_class_methods': 15,
        'max_class_lines': 300,
        'max_line_length': 100,
        'max_nesting_depth': 4,
        'min_variable_name_length': 2,
        'duplicate_code_threshold': 6,  # 相似代码块的最小行数
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.issue_counter = 0
    
    def _generate_issue_id(self, issue_type: str) -> str:
        self.issue_counter += 1
        return f"smell_{issue_type}_{self.issue_counter}"
    
    def analyze(self, code: str, tree: Optional[ast.AST] = None) -> List[CodeIssue]:
        """
        检测代码异味
        
        Args:
            code: 源代码字符串
            tree: 可选的AST树
        
        Returns:
            代码问题列表
        """
        # 清空之前的状态，避免累积
        self.issues = []
        self.issue_counter = 0
        
        if tree is None:
            tree = ast.parse(code)
        
        source_lines = code.splitlines()
        
        # 执行各项检测
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
        """检测过长函数"""
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
                            message=f"函数 '{node.name}' 过长 ({lines}行)，建议拆分为更小的函数",
                            lineno=node.lineno,
                            end_lineno=node.end_lineno,
                            source_snippet=ast.get_docstring(node)
                        ))
    
    def _detect_god_classes(self, tree: ast.AST, source_lines: List[str]):
        """检测上帝类（过大过复杂的类）"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                attributes = set()
                
                # 统计属性
                for item in ast.walk(node):
                    if isinstance(item, ast.Attribute):
                        if isinstance(item.value, ast.Name) and item.value.id == 'self':
                            attributes.add(item.attr)
                
                method_count = len(methods)
                attribute_count = len(attributes)
                
                # 检查行数
                lines = 0
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    lines = node.end_lineno - node.lineno + 1
                
                # 判断是否为上帝类
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
                        message=f"类 '{node.name}' 可能是上帝类 ({method_count}个方法, {attribute_count}个属性, {lines}行)，建议拆分职责",
                        lineno=node.lineno
                    ))
    
    def _detect_long_parameter_list(self, tree: ast.AST):
        """检测过长参数列表"""
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
                        message=f"函数 '{node.name}' 参数过多 ({param_count}个)，考虑使用配置对象或重构",
                        lineno=node.lineno
                    ))
    
    def _detect_deep_nesting(self, tree: ast.AST):
        """检测深层嵌套"""
        
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
                        message=f"{node_type}嵌套过深 ({self.current_depth}层)，建议提取方法或使用早返回",
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
        """检测魔法数字"""
        excluded_values = {0, 1, -1, 2, 10, 100, 1000, 255, 256, 360, 1024}
        
        class MagicNumberVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.in_assign_value = False
                self.in_constant_def = False
            
            def visit_Assign(self, node):
                # 检查是否是常量定义（大写变量名）
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
                # 类型注解赋值
                is_constant = isinstance(node.target, ast.Name) and node.target.id.isupper()
                
                old_in_constant = self.in_constant_def
                self.in_constant_def = is_constant
                
                self.generic_visit(node)
                
                self.in_constant_def = old_in_constant
            
            def visit_Constant(self, node):
                if isinstance(node.value, (int, float)):
                    if node.value not in excluded_values:
                        # 如果在常量定义中，不报告
                        if not self.in_constant_def:
                            self.detector.issues.append(CodeIssue(
                                id=self.detector._generate_issue_id("magic_number"),
                                type="code_smell",
                                severity=SeverityLevel.INFO,
                                message=f"魔法数字 '{node.value}'，建议定义为常量",
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            ))
        
        visitor = MagicNumberVisitor(self)
        visitor.visit(tree)
    
    def _detect_unused_variables(self, tree: ast.AST):
        """检测未使用的变量"""
        assigned_vars = set()
        used_vars = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    assigned_vars.add((node.id, node.lineno))
                elif isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
        
        # 查找定义但未使用的变量
        for var_name, lineno in assigned_vars:
            if var_name not in used_vars and not var_name.startswith('_'):
                # 排除一些特殊情况
                if var_name not in ('_', 'self', 'cls'):
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("unused_var"),
                        type="code_smell",
                        severity=SeverityLevel.INFO,
                        message=f"变量 '{var_name}' 可能未被使用",
                        lineno=lineno
                    ))
    
    def _detect_poor_names(self, tree: ast.AST):
        """检测不良命名"""
        poor_names = {'x', 'y', 'z', 'temp', 'tmp', 'data', 'result', 'val', 'var', 'foo', 'bar', 'baz'}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in poor_names:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("poor_name"),
                        type="code_smell",
                        severity=SeverityLevel.INFO,
                        message=f"函数名 '{node.name}' 不够描述性，建议使用更具意义的名称",
                        lineno=node.lineno
                    ))
                
                # 检查参数名
                for arg in node.args.args:
                    if arg.arg in poor_names:
                        self.issues.append(CodeIssue(
                            id=self._generate_issue_id("poor_param_name"),
                            type="code_smell",
                            severity=SeverityLevel.INFO,
                            message=f"参数名 '{arg.arg}' 不够描述性",
                            lineno=node.lineno
                        ))
            
            elif isinstance(node, ast.ClassDef):
                if node.name in poor_names:
                    self.issues.append(CodeIssue(
                        id=self._generate_issue_id("poor_class_name"),
                        type="code_smell",
                        severity=SeverityLevel.INFO,
                        message=f"类名 '{node.name}' 不够描述性",
                        lineno=node.lineno
                    ))
    
    def _detect_duplicate_code(self, source_lines: List[str]):
        """检测重复代码（简化版）"""
        # 简化实现：检测相同的行
        line_count = Counter(line.strip() for line in source_lines if line.strip())
        
        for line, count in line_count.items():
            if count > 3 and len(line) > 20:  # 排除短行和注释
                # 找到这些行的位置
                positions = [i + 1 for i, l in enumerate(source_lines) if l.strip() == line.strip()]
                
                self.issues.append(CodeIssue(
                    id=self._generate_issue_id("duplicate"),
                    type="code_smell",
                    severity=SeverityLevel.INFO,
                    message=f"检测到重复代码行，出现 {count} 次",
                    lineno=positions[0]
                ))
    
    def _detect_dead_code(self, tree: ast.AST):
        """检测死代码"""
        
        class DeadCodeVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.after_return = False
                self.after_break = False
                self.after_continue = False
            
            def visit_FunctionDef(self, node):
                self.after_return = False
                for i, stmt in enumerate(node.body):
                    if self.after_return:
                        self.detector.issues.append(CodeIssue(
                            id=self.detector._generate_issue_id("dead_code"),
                            type="code_smell",
                            severity=SeverityLevel.WARNING,
                            message="return语句后的代码永远不会执行",
                            lineno=getattr(stmt, 'lineno', node.lineno)
                        ))
                        break
                    
                    if isinstance(stmt, ast.Return):
                        self.after_return = True
                    
                    self.visit(stmt)
                
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
        """检测过长的属性/方法链"""
        
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
                        message=f"属性链过长 ({chain_length}层)，考虑使用中间变量提高可读性",
                        lineno=node.lineno
                    ))
    
    def get_summary(self) -> Dict[str, int]:
        """获取检测摘要"""
        summary = {}
        for issue in self.issues:
            key = issue.message.split('，')[0]  # 提取主要信息
            summary[key] = summary.get(key, 0) + 1
        return summary
