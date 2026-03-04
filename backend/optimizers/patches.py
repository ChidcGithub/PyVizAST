"""
Patch Generator - Code patch generator
Generates automatically applicable code fix patches
"""
import ast
import difflib
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from ..models.schemas import OptimizationSuggestion


logger = logging.getLogger(__name__)


class PatchGenerator:
    """Code Patch Generator - Improved Version"""
    
    def __init__(self):
        self.patches: List[Dict[str, Any]] = []
        self._errors: List[str] = []
    
    def generate_patch(
        self, 
        original_code: str, 
        suggestion: OptimizationSuggestion
    ) -> Optional[str]:
        """
        Generate unified diff format patch
        
        Args:
            original_code: Original code
            suggestion: Optimization suggestion
        
        Returns:
            Unified diff format patch string
        """
        if not suggestion.auto_fixable:
            return None
        
        # Validate original code syntax
        if not self._validate_syntax(original_code):
            logger.warning("Original code has syntax errors, cannot generate patch")
            return None
        
        try:
            # Attempt to apply fix
            fixed_code = self._apply_fix(original_code, suggestion)
            
            if fixed_code is None or fixed_code == original_code:
                return None
            
            # Validate fixed code syntax
            if not self._validate_syntax(fixed_code):
                logger.warning(f"Fixed code has syntax errors: {suggestion.title}")
                return None
            
            # Generate diff
            diff = self._generate_unified_diff(
                original_code, 
                fixed_code, 
                fromfile='original',
                tofile='fixed'
            )
            
            return diff
            
        except Exception as e:
            logger.error(f"Failed to generate patch: {e}")
            self._errors.append(f"Failed to generate patch ({suggestion.title}): {str(e)}")
            return None
    
    def _validate_syntax(self, code: str) -> bool:
        """Validate code syntax is correct"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _apply_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """Apply specific fix"""
        # Apply different fix strategies based on suggestion type
        if suggestion.category == 'performance':
            return self._apply_performance_fix(code, suggestion)
        elif suggestion.category == 'readability':
            return self._apply_readability_fix(code, suggestion)
        elif suggestion.category == 'security':
            return self._apply_security_fix(code, suggestion)
        
        return None
    
    def _apply_performance_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """Apply performance optimization fix"""
        
        # List comprehension to generator expression
        if 'generator' in suggestion.title.lower():
            return self._fix_listcomp_to_gen(code)
        
        # String concatenation optimization
        if 'string concatenation' in suggestion.title.lower() or 'join' in suggestion.title.lower():
            return self._fix_string_concat(code)
        
        # Set optimization
        if 'set' in suggestion.title.lower() and 'membership' in suggestion.title.lower():
            return self._fix_list_membership(code)
        
        return None
    
    def _apply_readability_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """Apply readability fix"""
        
        # range(len()) -> enumerate()
        if 'enumerate' in suggestion.title.lower():
            return self._fix_range_len(code)
        
        # Format string -> f-string
        if 'f-string' in suggestion.title.lower():
            return self._fix_format_string(code)
        
        return None
    
    def _apply_security_fix(self, code: str, suggestion: OptimizationSuggestion) -> Optional[str]:
        """Apply security fix"""
        
        # eval -> ast.literal_eval
        if 'eval' in suggestion.title.lower() or 'literal_eval' in suggestion.title.lower():
            return self._fix_eval_to_literal_eval(code)
        
        return None
    
    def _fix_listcomp_to_gen(self, code: str) -> Optional[str]:
        """Convert list comprehension in function arguments to generator expression"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        
        # Find positions that need conversion
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
                        # Record position for replacement
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
        
        # Use ast.unparse or manual replacement
        lines = code.splitlines(keepends=True)
        result = code
        
        for repl in replacements:
            node = repl['node']
            # Get original code segment
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                start_line = node.lineno - 1
                end_line = node.end_lineno - 1
                
                # Extract original list comprehension
                original_segment = self._extract_segment(lines, start_line, 
                                                         node.col_offset, 
                                                         end_line, 
                                                         node.end_col_offset)
                
                if original_segment and original_segment.startswith('[') and original_segment.endswith(']'):
                    # Convert to generator expression
                    gen_expr = '(' + original_segment[1:-1] + ')'
                    result = result.replace(original_segment, gen_expr, 1)
        
        return result if result != code else None
    
    def _extract_segment(self, lines: List[str], start_line: int, start_col: int,
                         end_line: int, end_col: int) -> str:
        """Extract segment from source code at specified position"""
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
        """Fix string concatenation in loops - Improved Version
        
        Handles:
        - Proper loop tracking with indent-based scope detection
        - Correct initialization placement before first use in correct scope
        - Join statement addition at end of loop or before return/print
        """
        lines = code.splitlines()
        
        # Track string concatenation variables per loop scope
        # Key: var_name, Value: dict with scope info
        string_vars_info: Dict[str, Dict[str, Any]] = {}
        
        def get_indent(line: str) -> int:
            return len(line) - len(line.lstrip())
        
        def is_string_value(value: str) -> bool:
            """Check if value is likely a string"""
            value = value.strip()
            return (
                value.startswith('"') or value.startswith("'") or
                value.startswith('f"') or value.startswith("f'") or
                'str(' in value or
                value.endswith('"') or value.endswith("'")
            )
        
        # First pass: detect all string concatenations in loops
        loop_indent_stack: List[int] = []  # Stack of loop indentation levels
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            current_indent = get_indent(line)
            
            # Track loop entry/exit based on indentation
            while loop_indent_stack and current_indent <= loop_indent_stack[-1]:
                if stripped and not stripped.startswith(('for ', 'while ', 'elif ', 'else:', 'except', 'finally:', '#')):
                    loop_indent_stack.pop()
                else:
                    break
            
            # Track new loops
            if stripped.startswith('for ') or stripped.startswith('while '):
                loop_indent_stack.append(current_indent)
            
            # Detect += string concatenation inside loops
            if '+=' in line and loop_indent_stack:
                match = re.match(r'^(\s*)(\w+)\s*\+=\s*(.+)$', line)
                if match:
                    indent, var_name, value = match.groups()
                    value = value.strip()
                    
                    # Check if it's string concatenation
                    if is_string_value(value) or var_name in string_vars_info:
                        if var_name not in string_vars_info:
                            string_vars_info[var_name] = {
                                'first_line': i,
                                'indent': current_indent,
                                'loop_indent': loop_indent_stack[-1],
                                'parts_name': f'{var_name}_parts',
                                'lines': [i],
                            }
                        else:
                            string_vars_info[var_name]['lines'].append(i)
        
        if not string_vars_info:
            return None
        
        # Second pass: apply transformations
        result_lines = lines.copy()
        added_inits: Set[str] = set()
        added_joins: Set[str] = set()
        
        # Process from back to front to preserve line numbers during insertion
        for var_name, info in sorted(string_vars_info.items(), 
                                     key=lambda x: x[1]['first_line'], 
                                     reverse=True):
            parts_name = info['parts_name']
            loop_indent = info['loop_indent']
            first_line = info['first_line']
            
            # Find the loop start line for initialization placement
            loop_start_line = first_line
            for j in range(first_line, -1, -1):
                stripped = lines[j].strip()
                if stripped.startswith('for ') or stripped.startswith('while '):
                    if get_indent(lines[j]) == loop_indent:
                        loop_start_line = j
                        break
            
            # Transform += lines to append
            for line_idx in sorted(info['lines'], reverse=True):
                line = result_lines[line_idx]
                match = re.match(r'^(\s*)(\w+)\s*\+=\s*(.+)$', line)
                if match:
                    indent, _, value = match.groups()
                    result_lines[line_idx] = f'{indent}{parts_name}.append({value.strip()})'
            
            # Add initialization after loop start
            if var_name not in added_inits:
                init_line = loop_start_line + 1
                init_indent = loop_indent + 4  # One level inside loop
                result_lines.insert(init_line, ' ' * init_indent + f'{parts_name} = []')
                added_inits.add(var_name)
                # Adjust line indices after insertion
                for other_name, other_info in string_vars_info.items():
                    if other_name != var_name:
                        other_info['first_line'] += 1
                        other_info['lines'] = [l + 1 for l in other_info['lines']]
            
            # Find where to add join statement
            # Look for return, print, or end of function
            join_added = False
            for j in range(info['lines'][-1] + 1, len(result_lines)):
                stripped = result_lines[j].strip()
                join_indent = loop_indent + 4
                
                # Add join before return/print that uses the variable
                if f'return {var_name}' in result_lines[j] or f'print({var_name}' in result_lines[j]:
                    result_lines.insert(j, ' ' * join_indent + f"{var_name} = ''.join({parts_name})")
                    join_added = True
                    added_joins.add(var_name)
                    break
                
                # Check for end of scope (dedent to loop level or less)
                if stripped and not stripped.startswith('#'):
                    if get_indent(result_lines[j]) <= loop_indent:
                        # End of loop scope, add join before this line
                        result_lines.insert(j, ' ' * join_indent + f"{var_name} = ''.join({parts_name})")
                        join_added = True
                        added_joins.add(var_name)
                        break
            
            # If no suitable location found, add at end of loop body
            if not join_added and var_name not in added_joins:
                # Find last line of the loop
                last_concat_line = max(info['lines'])
                for j in range(last_concat_line + 1, len(result_lines)):
                    if get_indent(result_lines[j]) <= loop_indent and result_lines[j].strip():
                        join_indent = loop_indent + 4
                        result_lines.insert(j, ' ' * join_indent + f"{var_name} = ''.join({parts_name})")
                        break
        
        result = '\n'.join(result_lines)
        return result if result != code else None
    
    def _fix_list_membership(self, code: str) -> Optional[str]:
        """Fix list membership check - Improved Version"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        
        # Collect lists that need conversion
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
        
        # Generate conversion names
        for lst in finder.lists_in_loops:
            lists_to_convert[lst] = f'{lst}_set'
        
        lines = code.splitlines()
        result_lines = []
        added_conversions: Set[str] = set()
        
        for line in lines:
            # Check if conversion is needed
            for list_name, set_name in lists_to_convert.items():
                # Match "in list_name" pattern (avoid false matches)
                patterns = [
                    (rf'\bin\s+{re.escape(list_name)}\b', f'in {set_name}'),
                    (rf'\bnot\s+in\s+{re.escape(list_name)}\b', f'not in {set_name}'),
                ]
                
                new_line = line
                for pattern, replacement in patterns:
                    if re.search(pattern, line) and list_name not in added_conversions:
                        # Find appropriate insertion position (outside loop)
                        if 'for ' in line or 'while ' in line:
                            # Get indent
                            indent = len(line) - len(line.lstrip())
                            # Add conversion before loop
                            if list_name not in added_conversions:
                                result_lines.append(' ' * indent + f'{set_name} = set({list_name})')
                                added_conversions.add(list_name)
                        new_line = re.sub(pattern, replacement, new_line)
            
            result_lines.append(new_line)
        
        result = '\n'.join(result_lines)
        return result if result != code else None
    
    def _fix_range_len(self, code: str) -> Optional[str]:
        """Fix range(len()) pattern - Improved Version"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        
        # Collect fix information
        fixes = []
        
        class RangeLenFinder(ast.NodeVisitor):
            def visit_For(self, node):
                # Check if it's range(len(...)) pattern
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
        
        # Process from back to front to avoid line number offset
        for fix in reversed(fixes):
            line_idx = fix['lineno'] - 1
            original_line = lines[line_idx]
            
            # Get indent
            indent = len(original_line) - len(original_line.lstrip())
            indent_str = ' ' * indent
            
            # Generate new for line
            index_var = fix['index_var']
            seq_name = fix['seq_name']
            new_for_line = f'{indent_str}for {index_var}, item in enumerate({seq_name}):'
            
            result_lines[line_idx] = new_for_line
            
            # Try to replace arr[i] with item in loop body
            # Need to find loop body range
            loop_node = fix['node']
            if loop_node.body:
                body_start = loop_node.body[0].lineno - 1
                body_end = (loop_node.body[-1].end_lineno - 1) if hasattr(loop_node.body[-1], 'end_lineno') else body_start + 1
                
                for i in range(body_start, min(body_end + 1, len(result_lines))):
                    # Replace seq_name[index_var] with item
                    pattern = rf'\b{re.escape(seq_name)}\s*\[\s*{re.escape(index_var)}\s*\]'
                    result_lines[i] = re.sub(pattern, 'item', result_lines[i])
        
        result = '\n'.join(result_lines)
        return result if result != code else None
    
    def _fix_format_string(self, code: str) -> Optional[str]:
        """Convert format strings to f-string - Improved Version"""
        result = code
        changes_made = False
        
        # Handle % formatting
        def convert_percent(match):
            nonlocal changes_made
            
            full_match = match.group(0)
            quote = match.group(1)
            template = match.group(2)
            args_str = match.group(3)
            
            try:
                # Parse arguments
                args = [a.strip() for a in args_str.split(',')]
                
                # Check for attribute access or method calls
                # Complex expressions need special handling - skip for safety
                if any('.' in a or '[' in a or '(' in a for a in args):
                    # Complex expressions like obj.attr, arr[i], func() 
                    # These need parentheses in f-strings, but for safety we skip
                    return full_match
                
                # Replace format specifiers
                fstring = template
                for arg in args:
                    # Handle different format specifiers
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
        
        # Match "template" % (args) or 'template' % (args)
        pattern = r'(["\'])([^"\']*%[sdfroxef])\1\s*%\s*\(([^)]+)\)'
        result = re.sub(pattern, convert_percent, result)
        
        # Handle .format() method
        def convert_format_method(match):
            nonlocal changes_made
            
            full_match = match.group(0)
            quote = match.group(1)
            template = match.group(2)
            args_str = match.group(3)
            
            try:
                args = [a.strip() for a in args_str.split(',')]
                
                # Replace {0}, {1} etc. positional arguments
                fstring = template
                for i, arg in enumerate(args):
                    # Replace {index} and {index:format}
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
        
        # Match "template".format(args)
        pattern = r'(["\'])([^"\']*\{[\d]+[^"\']*)\1\.format\s*\(([^)]+)\)'
        result = re.sub(pattern, convert_format_method, result)
        
        return result if changes_made else None
    
    def _fix_eval_to_literal_eval(self, code: str) -> Optional[str]:
        """Replace eval() with ast.literal_eval() - Improved Version"""
        lines = code.splitlines()
        result_lines = []
        needs_ast_import = False
        changes_made = False
        
        for line in lines:
            new_line = line
            
            # Check for eval() call
            if re.search(r'\beval\s*\(', line):
                # Replace eval with ast.literal_eval
                new_line = re.sub(r'\beval\s*\(', 'ast.literal_eval(', line)
                needs_ast_import = True
                changes_made = True
            
            result_lines.append(new_line)
        
        if not changes_made:
            return None
        
        # Check if ast import already exists
        has_ast_import = any(
            'import ast' in line or 'from ast import' in line 
            for line in lines
        )
        
        if needs_ast_import and not has_ast_import:
            # Find appropriate insertion position (file beginning or after first import)
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_pos = i + 1
                elif line.strip().startswith('"""') or line.strip().startswith("'''"):
                    # Skip docstring
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
        """Generate unified diff format"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        # Ensure each line has newline
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
        Apply patch to code - Improved Version
        
        Args:
            code: Original code
            patch: Unified diff format patch
        
        Returns:
            Fixed code, or None on failure
        """
        try:
            lines = code.splitlines()
            patch_lines = patch.splitlines()
            
            # Validate patch format
            if not any(line.startswith('@@') for line in patch_lines):
                logger.warning("Invalid patch format: missing hunk marker")
                return None
            
            # Parse patch
            hunks = self._parse_patch_hunks(patch_lines)
            
            if not hunks:
                logger.warning("Cannot parse hunks in patch")
                return None
            
            # Validate patch is applicable to current code
            if not self._validate_patch_applicable(lines, hunks):
                logger.warning("Patch not applicable to current code")
                return None
            
            # Apply each hunk (from back to front to avoid line number offset)
            hunks_sorted = sorted(hunks, key=lambda h: h['start_line'], reverse=True)
            
            for hunk in hunks_sorted:
                start_line = hunk['start_line'] - 1
                
                if start_line < 0 or start_line > len(lines):
                    logger.warning(f"Invalid line number: {start_line + 1}")
                    return None
                
                deleted_count = hunk['deleted']
                new_lines = hunk['lines']
                
                # Check if delete range is valid
                if start_line + deleted_count > len(lines):
                    logger.warning(f"Delete range exceeds code lines")
                    return None
                
                # Execute replacement
                lines[start_line:start_line + deleted_count] = new_lines
            
            result = '\n'.join(lines)
            
            # Validate result syntax
            if not self._validate_syntax(result):
                logger.warning("Code has syntax errors after applying patch")
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            return None
    
    def _validate_patch_applicable(self, lines: List[str], hunks: List[Dict[str, Any]]) -> bool:
        """
        Validate patch is applicable to current code
        
        Validates patch applicability by checking if context lines match,
        avoiding patch application to wrong positions.
        """
        for hunk in hunks:
            start_line = hunk['start_line'] - 1
            context_lines = hunk.get('context', [])
            deleted_lines = hunk.get('deleted_lines', [])
            
            # Validate start line is in valid range
            if start_line < 0 or start_line >= len(lines):
                logger.warning(f"Patch start line {start_line + 1} exceeds code range")
                return False
            
            # Validate context lines match
            for ctx_line_num, ctx_content in context_lines:
                actual_line_idx = ctx_line_num - 1
                if actual_line_idx < 0 or actual_line_idx >= len(lines):
                    logger.warning(f"Context line {ctx_line_num} exceeds range")
                    return False
                
                # Compare after stripping whitespace (allow whitespace differences)
                actual_content = lines[actual_line_idx].rstrip()
                expected_content = ctx_content.rstrip() if ctx_content else ''
                
                # Allow some whitespace difference
                if actual_content != expected_content:
                    # Try looser matching (ignore trailing whitespace)
                    if actual_content.strip() != expected_content.strip():
                        logger.warning(
                            f"Context mismatch (line {ctx_line_num}): "
                            f"expected '{expected_content[:50]}...', "
                            f"actual '{actual_content[:50]}...'"
                        )
                        return False
            
            # Validate lines to be deleted exist
            if deleted_lines:
                for line_num, deleted_content in deleted_lines:
                    line_idx = line_num - 1
                    if line_idx < 0 or line_idx >= len(lines):
                        logger.warning(f"Delete line {line_num} exceeds range")
                        return False
                    
                    actual = lines[line_idx].rstrip()
                    expected = deleted_content.rstrip() if deleted_content else ''
                    
                    # Allow whitespace differences but content should be similar
                    if actual.strip() != expected.strip():
                        logger.warning(
                            f"Delete line mismatch (line {line_num}): "
                            f"expected '{expected[:30]}...', "
                            f"actual '{actual[:30]}...'"
                        )
                        return False
        
        return True
    
    def _parse_patch_hunks(self, patch_lines: List[str]) -> List[Dict[str, Any]]:
        """Parse hunks in patch - Improved Version"""
        hunks = []
        current_hunk = None
        old_line_num = 0  # Original file line number
        new_line_num = 0  # New file line number
        
        for line in patch_lines:
            if line.startswith('@@'):
                # Save previous hunk
                if current_hunk is not None:
                    hunks.append(current_hunk)
                
                # Parse @@ -start,count +start,count @@ or @@ -start +start @@
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2) or 1)
                    new_start = int(match.group(3))
                    new_count = int(match.group(4) or 1)
                    
                    current_hunk = {
                        'start_line': new_start,
                        'old_start': old_start,
                        'deleted': 0,
                        'added': 0,
                        'lines': [],
                        'context': [],
                        'deleted_lines': []
                    }
                    old_line_num = old_start
                    new_line_num = new_start
                else:
                    current_hunk = None
                    
            elif current_hunk is not None:
                if line.startswith('+++') or line.startswith('---'):
                    continue
                elif line.startswith('+'):
                    # Added line
                    content = line[1:] if len(line) > 1 else ''
                    current_hunk['lines'].append(content)
                    current_hunk['added'] += 1
                    new_line_num += 1
                elif line.startswith('-'):
                    # Deleted line - record content for validation
                    deleted_content = line[1:] if len(line) > 1 else ''
                    current_hunk['deleted'] += 1
                    current_hunk['deleted_lines'].append((old_line_num, deleted_content))
                    old_line_num += 1  # Original file line number increases
                elif line.startswith('\\'):
                    # Continuation indicator (e.g., "\ No newline at end of file"), ignore
                    continue
                elif line.startswith(' '):
                    # Context line (starts with space)
                    context_content = line[1:] if len(line) > 1 else ''
                    current_hunk['lines'].append(context_content)
                    current_hunk['context'].append((new_line_num, context_content))
                    old_line_num += 1
                    new_line_num += 1
                else:
                    # Empty line or other case, treat as context
                    current_hunk['lines'].append('')
                    current_hunk['context'].append((new_line_num, ''))
                    old_line_num += 1
                    new_line_num += 1
        
        # Add last hunk
        if current_hunk is not None:
            hunks.append(current_hunk)
        
        return hunks
    
    def generate_all_patches(
        self, 
        code: str, 
        suggestions: List[OptimizationSuggestion]
    ) -> List[Dict[str, Any]]:
        """
        Generate patches for all auto-fixable suggestions
        
        Args:
            code: Original code
            suggestions: List of optimization suggestions
        
        Returns:
            List of patch information
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
                logger.error(f"Error processing suggestion {suggestion.id}: {e}")
                self._errors.append(f"{suggestion.title}: {str(e)}")
        
        return self.patches
    
    def get_errors(self) -> List[str]:
        """Get list of errors during generation"""
        return self._errors.copy()
