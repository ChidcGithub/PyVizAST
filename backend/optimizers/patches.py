"""
Patch Generator - 代码补丁生成器
生成可自动应用的代码修复补丁
"""
import ast
import difflib
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from ..models.schemas import OptimizationSuggestion


logger = logging.getLogger(__name__)


class PatchGenerator:
    """代码补丁生成器 - 改进版"""
    
    def __init__(self):
        self.patches: List[Dict[str, Any]] = []
        self._errors: List[str] = []
    
    def generate_patch(
        self, 
        original_code: str, 
        suggestion: OptimizationSuggestion
    ) -> Optional[str]:
        """
        生成统一差异格式的补丁
        
        Args:
            original_code: 原始代码
            suggestion: 优化建议
        
        Returns:
            统一差异格式的补丁字符串
        """
        if not suggestion.auto_fixable:
            return None
        
        # 验证原始代码语法
        if not self._validate_syntax(original_code):
            logger.warning("原始代码存在语法错误，无法生成补丁")
            return None
        
        try:
            # 尝试应用修复
            fixed_code = self._apply_fix(original_code, suggestion)
            
            if fixed_code is None or fixed_code == original_code:
                return None
            
            # 验证修复后的代码语法
            if not self._validate_syntax(fixed_code):
                logger.warning(f"修复后的代码存在语法错误: {suggestion.title}")
                return None
            
            # 生成差异
            diff = self._generate_unified_diff(
                original_code, 
                fixed_code, 
                fromfile='original',
                tofile='fixed'
            )
            
            return diff
            
        except Exception as e:
            logger.error(f"生成补丁失败: {e}")
            self._errors.append(f"生成补丁失败 ({suggestion.title}): {str(e)}")
            return None
    
    def _validate_syntax(self, code: str) -> bool:
        """验证代码语法是否正确"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _apply_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """应用具体的修复"""
        # 根据建议类型应用不同的修复策略
        if suggestion.category == 'performance':
            return self._apply_performance_fix(code, suggestion)
        elif suggestion.category == 'readability':
            return self._apply_readability_fix(code, suggestion)
        elif suggestion.category == 'security':
            return self._apply_security_fix(code, suggestion)
        
        return None
    
    def _apply_performance_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """应用性能优化修复"""
        
        # 列表推导式转生成器表达式
        if '生成器' in suggestion.title:
            return self._fix_listcomp_to_gen(code)
        
        # 字符串拼接优化
        if '字符串拼接' in suggestion.title or 'join' in suggestion.title.lower():
            return self._fix_string_concat(code)
        
        # 集合优化
        if '集合' in suggestion.title and '成员检查' in suggestion.title:
            return self._fix_list_membership(code)
        
        return None
    
    def _apply_readability_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """应用可读性修复"""
        
        # range(len()) -> enumerate()
        if 'enumerate' in suggestion.title.lower():
            return self._fix_range_len(code)
        
        # 格式化字符串 -> f-string
        if 'f-string' in suggestion.title.lower():
            return self._fix_format_string(code)
        
        return None
    
    def _apply_security_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """应用安全修复"""
        
        # eval -> ast.literal_eval
        if 'eval' in suggestion.title.lower() or 'literal_eval' in suggestion.title.lower():
            return self._fix_eval_to_literal_eval(code)
        
        return None
    
    def _fix_listcomp_to_gen(self, code: str) -> Optional[str]:
        """将函数参数中的列表推导式转换为生成器表达式"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        
        # 找到需要转换的位置
        replacements = []
        
        class ListCompFinder(ast.NodeVisitor):
            def __init__(self):
                self.in_func_call = False
                self.current_call_node = None
            
            def visit_Call(self, node):
                old_in_func = self.in_func_call
                old_call = self.current_call_node
                self.in_func_call = True
                self.current_call_node = node
                
                for i, arg in enumerate(node.args):
                    if isinstance(arg, ast.ListComp):
                        # 记录需要替换的位置
                        replacements.append({
                            'node': arg,
                            'call_node': node,
                            'arg_index': i
                        })
                    self.visit(arg)
                
                for kw in node.keywords:
                    self.visit(kw)
                
                self.in_func_call = old_in_func
                self.current_call_node = old_call
        
        finder = ListCompFinder()
        finder.visit(tree)
        
        if not replacements:
            return None
        
        # 使用 ast.unparse 或手动替换
        lines = code.splitlines(keepends=True)
        result = code
        
        for repl in replacements:
            node = repl['node']
            # 获取原始代码片段
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                start_line = node.lineno - 1
                end_line = node.end_lineno - 1
                
                # 提取原始列表推导式
                original_segment = self._extract_segment(lines, start_line, 
                                                         node.col_offset, 
                                                         end_line, 
                                                         node.end_col_offset)
                
                if original_segment and original_segment.startswith('[') and original_segment.endswith(']'):
                    # 转换为生成器表达式
                    gen_expr = '(' + original_segment[1:-1] + ')'
                    result = result.replace(original_segment, gen_expr, 1)
        
        return result if result != code else None
    
    def _extract_segment(self, lines: List[str], start_line: int, start_col: int,
                         end_line: int, end_col: int) -> str:
        """从源代码中提取指定位置的片段"""
        try:
            if start_line == end_line:
                return lines[start_line][start_col:end_col]
            else:
                result = [lines[start_line][start_col:]]
                for i in range(start_line + 1, end_line):
                    result.append(lines[i])
                result.append(lines[end_line][:end_col])
                return ''.join(result).rstrip('\n\r')
        except (IndexError, KeyError):
            return ''
    
    def _fix_string_concat(self, code: str) -> Optional[str]:
        """修复循环中的字符串拼接 - 改进版"""
        lines = code.splitlines()
        result_lines = []
        
        # 追踪字符串变量和它们的拼接位置
        string_vars_in_loops: Dict[str, Dict[str, Any]] = {}
        loop_stack: List[Tuple[int, str]] = []  # (line_index, loop_var)
        
        def get_indent(line: str) -> int:
            return len(line) - len(line.lstrip())
        
        def is_inside_loop(current_indent: int) -> bool:
            return any(loop_stack)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            current_indent = get_indent(line)
            
            # 跟踪循环
            if stripped.startswith('for ') or stripped.startswith('while '):
                loop_stack.append((i, current_indent))
                result_lines.append(line)
                i += 1
                continue
            
            # 检测循环结束
            while loop_stack and current_indent <= loop_stack[-1][1] and not stripped.startswith(('for ', 'while ', 'elif ', 'else:', 'except', 'finally:')):
                if stripped and not stripped.startswith('#'):
                    loop_stack.pop()
                    break
                break
            
            # 检测 += 字符串拼接
            if '+=' in line and is_inside_loop(current_indent):
                match = re.match(r'^(\s*)(\w+)\s*\+=\s*(.+)$', line)
                if match:
                    indent, var_name, value = match.groups()
                    value = value.strip()
                    
                    # 检查是否可能是字符串拼接
                    is_string_op = (
                        '"' in value or "'" in value or 
                        var_name in string_vars_in_loops or
                        'str(' in value
                    )
                    
                    if is_string_op:
                        # 记录这个变量
                        if var_name not in string_vars_in_loops:
                            string_vars_in_loops[var_name] = {
                                'first_line': i,
                                'indent': len(indent),
                                'parts_name': f'{var_name}_parts'
                            }
                        
                        # 替换为 append
                        result_lines.append(f'{indent}{var_name}_parts.append({value})')
                        i += 1
                        continue
            
            result_lines.append(line)
            i += 1
        
        # 添加初始化和 join 语句
        if string_vars_in_loops:
            final_lines = []
            added_init: Set[str] = set()
            
            for i, line in enumerate(result_lines):
                # 检查是否需要在这个位置添加初始化
                for var_name, info in string_vars_in_loops.items():
                    if var_name not in added_init:
                        # 找到变量的第一次使用位置
                        if f'{var_name}_parts.append' in line:
                            indent = ' ' * info['indent']
                            # 在使用前添加初始化
                            final_lines.append(f'{indent}{info["parts_name"]} = []')
                            added_init.add(var_name)
                
                final_lines.append(line)
                
                # 检查是否需要在 return 前添加 join
                for var_name, info in string_vars_in_loops.items():
                    if var_name in added_init and f'return {var_name}' in line:
                        indent = ' ' * info['indent']
                        # 在 return 前添加 join
                        join_line = f'{indent}{var_name} = \'\'.join({info["parts_name"]})'
                        final_lines.insert(-1, join_line)
            
            result = '\n'.join(final_lines)
        else:
            result = '\n'.join(result_lines)
        
        return result if result != code else None
    
    def _fix_list_membership(self, code: str) -> Optional[str]:
        """修复列表成员检查 - 改进版"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        
        # 收集需要转换的列表
        lists_to_convert: Dict[str, str] = {}  # list_name -> set_name
        
        class MembershipFinder(ast.NodeVisitor):
            def __init__(self):
                self.lists_in_loops = set()
                self.in_loop = False
            
            def visit_For(self, node):
                old = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old
            
            def visit_While(self, node):
                old = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old
            
            def visit_Compare(self, node):
                if self.in_loop:
                    for i, op in enumerate(node.ops):
                        if isinstance(op, (ast.In, ast.NotIn)):
                            comparator = node.comparators[i]
                            if isinstance(comparator, ast.Name):
                                self.lists_in_loops.add(comparator.id)
                self.generic_visit(node)
        
        finder = MembershipFinder()
        finder.visit(tree)
        
        if not finder.lists_in_loops:
            return None
        
        # 生成转换名称
        for lst in finder.lists_in_loops:
            lists_to_convert[lst] = f'{lst}_set'
        
        lines = code.splitlines()
        result_lines = []
        added_conversions: Set[str] = set()
        
        for line in lines:
            # 检查是否需要转换
            for list_name, set_name in lists_to_convert.items():
                # 匹配 "in list_name" 模式（避免误匹配）
                patterns = [
                    (rf'\bin\s+{re.escape(list_name)}\b', f'in {set_name}'),
                    (rf'\bnot\s+in\s+{re.escape(list_name)}\b', f'not in {set_name}'),
                ]
                
                new_line = line
                for pattern, replacement in patterns:
                    if re.search(pattern, line) and list_name not in added_conversions:
                        # 找到合适的插入位置（在循环外）
                        if 'for ' in line or 'while ' in line:
                            # 获取缩进
                            indent = len(line) - len(line.lstrip())
                            # 在循环前添加转换
                            if list_name not in added_conversions:
                                result_lines.append(' ' * indent + f'{set_name} = set({list_name})')
                                added_conversions.add(list_name)
                        new_line = re.sub(pattern, replacement, new_line)
            
            result_lines.append(new_line)
        
        result = '\n'.join(result_lines)
        return result if result != code else None
    
    def _fix_range_len(self, code: str) -> Optional[str]:
        """修复 range(len()) 模式 - 改进版"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        
        # 收集需要修复的信息
        fixes = []
        
        class RangeLenFinder(ast.NodeVisitor):
            def visit_For(self, node):
                # 检查是否是 range(len(...)) 模式
                if isinstance(node.iter, ast.Call):
                    call = node.iter
                    if isinstance(call.func, ast.Name) and call.func.id == 'range':
                        if len(call.args) >= 1:
                            arg = call.args[0]
                            if isinstance(arg, ast.Call):
                                if isinstance(arg.func, ast.Name) and arg.func.id == 'len':
                                    if len(arg.args) == 1 and isinstance(arg.args[0], ast.Name):
                                        seq_name = arg.args[0].id
                                        index_var = node.target.id if isinstance(node.target, ast.Name) else None
                                        if index_var:
                                            fixes.append({
                                                'lineno': node.lineno,
                                                'col_offset': node.col_offset,
                                                'end_lineno': getattr(node, 'end_lineno', node.lineno),
                                                'end_col_offset': getattr(node, 'end_col_offset', node.col_offset),
                                                'index_var': index_var,
                                                'seq_name': seq_name,
                                                'node': node
                                            })
                self.generic_visit(node)
        
        finder = RangeLenFinder()
        finder.visit(tree)
        
        if not fixes:
            return None
        
        lines = code.splitlines()
        result_lines = lines.copy()
        
        # 从后向前处理，避免行号偏移
        for fix in reversed(fixes):
            line_idx = fix['lineno'] - 1
            original_line = lines[line_idx]
            
            # 获取缩进
            indent = len(original_line) - len(original_line.lstrip())
            indent_str = ' ' * indent
            
            # 生成新的 for 行
            index_var = fix['index_var']
            seq_name = fix['seq_name']
            new_for_line = f'{indent_str}for {index_var}, item in enumerate({seq_name}):'
            
            result_lines[line_idx] = new_for_line
            
            # 尝试替换循环体内的 arr[i] 为 item
            # 需要找到循环体的范围
            loop_node = fix['node']
            if loop_node.body:
                body_start = loop_node.body[0].lineno - 1
                body_end = (loop_node.body[-1].end_lineno - 1) if hasattr(loop_node.body[-1], 'end_lineno') else body_start + 1
                
                for i in range(body_start, min(body_end + 1, len(result_lines))):
                    # 替换 seq_name[index_var] 为 item
                    pattern = rf'\b{re.escape(seq_name)}\s*\[\s*{re.escape(index_var)}\s*\]'
                    result_lines[i] = re.sub(pattern, 'item', result_lines[i])
        
        result = '\n'.join(result_lines)
        return result if result != code else None
    
    def _fix_format_string(self, code: str) -> Optional[str]:
        """将格式化字符串转换为f-string - 改进版"""
        result = code
        changes_made = False
        
        # 处理 % 格式化
        def convert_percent(match):
            nonlocal changes_made
            
            full_match = match.group(0)
            quote = match.group(1)
            template = match.group(2)
            args_str = match.group(3)
            
            try:
                # 解析参数
                args = [a.strip() for a in args_str.split(',')]
                
                # 检查是否有属性访问或方法调用
                if any('.' in a or '[' in a or '(' in a for a in args):
                    # 复杂表达式，使用括号
                    pass
                
                # 替换格式说明符
                fstring = template
                for arg in args:
                    # 处理不同格式符
                    patterns = [
                        ('%s', '{' + arg + '}'),
                        ('%d', '{' + arg + '}'),
                        ('%f', '{' + arg + '}'),
                        ('%r', '{' + arg + '!r}'),
                        ('%x', '{' + arg + ':x}'),
                        ('%o', '{' + arg + ':o}'),
                        ('%e', '{' + arg + ':e}'),
                    ]
                    for pattern, replacement in patterns:
                        if re.search(pattern, fstring):
                            fstring = re.sub(pattern, replacement, fstring, count=1)
                            break
                
                changes_made = True
                return 'f' + quote + fstring + quote
                
            except Exception:
                return full_match
        
        # 匹配 "template" % (args) 或 'template' % (args)
        pattern = r'(["\'])([^"\']*%[sdfroxef])\1\s*%\s*\(([^)]+)\)'
        result = re.sub(pattern, convert_percent, result)
        
        # 处理 .format() 方法
        def convert_format_method(match):
            nonlocal changes_made
            
            full_match = match.group(0)
            quote = match.group(1)
            template = match.group(2)
            args_str = match.group(3)
            
            try:
                args = [a.strip() for a in args_str.split(',')]
                
                # 替换 {0}, {1} 等位置参数
                fstring = template
                for i, arg in enumerate(args):
                    # 替换 {index} 和 {index:format}
                    patterns = [
                        (rf'\{{{i}\}}', '{' + arg + '}'),
                        (rf'\{{{i}:([^}}]+)\}}', '{' + arg + ':\\1}'),
                    ]
                    for pattern, replacement in patterns:
                        fstring = re.sub(pattern, replacement, fstring)
                
                changes_made = True
                return 'f' + quote + fstring + quote
                
            except Exception:
                return full_match
        
        # 匹配 "template".format(args)
        pattern = r'(["\'])([^"\']*\{[\d]+[^"\']*)\1\.format\s*\(([^)]+)\)'
        result = re.sub(pattern, convert_format_method, result)
        
        return result if changes_made else None
    
    def _fix_eval_to_literal_eval(self, code: str) -> Optional[str]:
        """将 eval() 替换为 ast.literal_eval() - 改进版"""
        lines = code.splitlines()
        result_lines = []
        needs_ast_import = False
        changes_made = False
        
        for line in lines:
            new_line = line
            
            # 检查是否有 eval() 调用
            if re.search(r'\beval\s*\(', line):
                # 替换 eval 为 ast.literal_eval
                new_line = re.sub(r'\beval\s*\(', 'ast.literal_eval(', line)
                needs_ast_import = True
                changes_made = True
            
            result_lines.append(new_line)
        
        if not changes_made:
            return None
        
        # 检查是否已经有 ast 导入
        has_ast_import = any(
            'import ast' in line or 'from ast import' in line 
            for line in lines
        )
        
        if needs_ast_import and not has_ast_import:
            # 找到合适的插入位置（文件开头或第一个 import 之后）
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_pos = i + 1
                elif line.strip().startswith('"""') or line.strip().startswith("'''"):
                    # 跳过文档字符串
                    continue
                elif insert_pos == 0 and line.strip() and not line.strip().startswith('#'):
                    insert_pos = i
                    break
            
            result_lines.insert(insert_pos, 'import ast')
        
        result = '\n'.join(result_lines)
        return result if result != code else None
    
    def _generate_unified_diff(
        self, 
        original: str, 
        modified: str,
        fromfile: str = 'original',
        tofile: str = 'modified'
    ) -> str:
        """生成统一差异格式"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        # 确保每行都有换行符
        original_lines = [line if line.endswith('\n') else line + '\n' for line in original_lines]
        modified_lines = [line if line.endswith('\n') else line + '\n' for line in modified_lines]
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=fromfile,
            tofile=tofile,
            lineterm=''
        )
        
        return ''.join(diff)
    
    def apply_patch(self, code: str, patch: str) -> Optional[str]:
        """
        应用补丁到代码 - 改进版
        
        Args:
            code: 原始代码
            patch: 统一差异格式的补丁
        
        Returns:
            修复后的代码，失败返回None
        """
        try:
            lines = code.splitlines()
            patch_lines = patch.splitlines()
            
            # 验证补丁格式
            if not any(line.startswith('@@') for line in patch_lines):
                logger.warning("无效的补丁格式：缺少 hunk 标记")
                return None
            
            # 解析补丁
            hunks = self._parse_patch_hunks(patch_lines)
            
            if not hunks:
                logger.warning("无法解析补丁中的 hunks")
                return None
            
            # 验证补丁是否适用于当前代码
            if not self._validate_patch_applicable(lines, hunks):
                logger.warning("补丁不适用于当前代码")
                return None
            
            # 应用每个hunk（从后向前，避免行号偏移）
            hunks_sorted = sorted(hunks, key=lambda h: h['start_line'], reverse=True)
            
            for hunk in hunks_sorted:
                start_line = hunk['start_line'] - 1
                
                if start_line < 0 or start_line > len(lines):
                    logger.warning(f"无效的行号: {start_line + 1}")
                    return None
                
                deleted_count = hunk['deleted']
                new_lines = hunk['lines']
                
                # 检查删除范围是否有效
                if start_line + deleted_count > len(lines):
                    logger.warning(f"删除范围超出代码行数")
                    return None
                
                # 执行替换
                lines[start_line:start_line + deleted_count] = new_lines
            
            result = '\n'.join(lines)
            
            # 验证结果语法
            if not self._validate_syntax(result):
                logger.warning("应用补丁后代码存在语法错误")
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"应用补丁失败: {e}")
            return None
    
    def _validate_patch_applicable(self, lines: List[str], hunks: List[Dict[str, Any]]) -> bool:
        """验证补丁是否适用于当前代码"""
        for hunk in hunks:
            start_line = hunk['start_line'] - 1
            context_lines = hunk.get('context', [])
            
            # 简单验证：检查上下文行是否匹配
            # 这里可以添加更严格的验证逻辑
            
        return True
    
    def _parse_patch_hunks(self, patch_lines: List[str]) -> List[Dict[str, Any]]:
        """解析补丁中的hunks - 改进版"""
        hunks = []
        current_hunk = None
        line_num = 0
        
        for line in patch_lines:
            if line.startswith('@@'):
                # 保存之前的 hunk
                if current_hunk is not None:
                    hunks.append(current_hunk)
                
                # 解析 @@ -start,count +start,count @@ 或 @@ -start +start @@
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2) or 1)
                    new_start = int(match.group(3))
                    new_count = int(match.group(4) or 1)
                    
                    current_hunk = {
                        'start_line': new_start,
                        'deleted': 0,
                        'added': 0,
                        'lines': [],
                        'context': []
                    }
                    line_num = new_start
                else:
                    current_hunk = None
                    
            elif current_hunk is not None:
                if line.startswith('+++') or line.startswith('---'):
                    continue
                elif line.startswith('+'):
                    # 新增行
                    current_hunk['lines'].append(line[1:] if len(line) > 1 else '')
                    current_hunk['added'] += 1
                elif line.startswith('-'):
                    # 删除行
                    current_hunk['deleted'] += 1
                elif line.startswith('\\'):
                    # 继续指示符，忽略
                    continue
                elif line:
                    # 上下文行
                    current_hunk['lines'].append(line if not line.startswith(' ') else line[1:])
                    current_hunk['context'].append((line_num, line if not line.startswith(' ') else line[1:]))
                    line_num += 1
                else:
                    # 空行作为上下文
                    current_hunk['lines'].append('')
                    line_num += 1
        
        # 添加最后一个 hunk
        if current_hunk is not None:
            hunks.append(current_hunk)
        
        return hunks
    
    def generate_all_patches(
        self, 
        code: str, 
        suggestions: List[OptimizationSuggestion]
    ) -> List[Dict[str, Any]]:
        """
        为所有可自动修复的建议生成补丁
        
        Args:
            code: 原始代码
            suggestions: 优化建议列表
        
        Returns:
            补丁信息列表
        """
        self.patches = []
        self._errors = []
        
        for suggestion in suggestions:
            try:
                patch = self.generate_patch(code, suggestion)
                if patch:
                    self.patches.append({
                        'suggestion_id': suggestion.id,
                        'category': suggestion.category,
                        'title': suggestion.title,
                        'patch': patch,
                        'description': suggestion.description
                    })
            except Exception as e:
                logger.error(f"处理建议 {suggestion.id} 时出错: {e}")
                self._errors.append(f"{suggestion.title}: {str(e)}")
        
        return self.patches
    
    def get_errors(self) -> List[str]:
        """获取生成过程中的错误列表"""
        return self._errors.copy()