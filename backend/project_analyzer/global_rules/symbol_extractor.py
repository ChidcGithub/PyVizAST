"""
符号提取器
从 Python 文件中提取定义和引用的符号

增强功能：
- 完整支持 __all__（静态列表、列表拼接、动态扩展）
- 条件导入检测（try/except 块中的导入）
- 动态导入检测（importlib.import_module, __import__）
"""

import ast
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Symbol:
    """符号信息"""
    name: str  # 符号名称
    kind: str  # function, class, variable, import
    file_path: str  # 定义所在文件
    lineno: Optional[int] = None  # 定义行号
    col_offset: Optional[int] = None
    is_exported: bool = False  # 是否公开（不以 _ 开头）
    is_in_all: bool = False  # 是否在 __all__ 中
    docstring: Optional[str] = None
    is_conditional: bool = False  # 是否在条件块中定义
    decorators: List[str] = field(default_factory=list)  # 装饰器列表


@dataclass
class SymbolReference:
    """符号引用信息"""
    name: str  # 符号名称
    file_path: str  # 引用所在文件
    lineno: Optional[int] = None
    col_offset: Optional[int] = None
    context: str = ""  # 引用上下文（load, store, del）


@dataclass
class DynamicImport:
    """动态导入信息"""
    module_expr: str  # 模块表达式（可能是变量）
    file_path: str
    lineno: Optional[int] = None
    import_type: str = "importlib"  # importlib, __import__, import_module
    assigned_to: Optional[str] = None  # 赋值目标


@dataclass
class ConditionalImport:
    """条件导入信息"""
    module: str
    file_path: str
    lineno: Optional[int] = None
    condition_type: str = "try_except"  # try_except, if, if_type_checking
    is_fallback: bool = False  # 是否是回退导入


@dataclass
class FileSymbols:
    """单个文件的符号信息"""
    file_path: str
    definitions: List[Symbol] = field(default_factory=list)
    references: List[SymbolReference] = field(default_factory=list)
    imports: Dict[str, str] = field(default_factory=dict)  # 导入名 -> 模块
    exported_names: Set[str] = field(default_factory=set)  # __all__ 中的名称
    dynamic_imports: List[DynamicImport] = field(default_factory=list)  # 动态导入
    conditional_imports: List[ConditionalImport] = field(default_factory=list)  # 条件导入
    has_all_definition: bool = False  # 是否有 __all__ 定义
    all_is_dynamic: bool = False  # __all__ 是否是动态生成的


class SymbolTable:
    """项目级符号表"""

    def __init__(self):
        self.file_symbols: Dict[str, FileSymbols] = {}
        # 全局索引：符号名 -> 定义列表
        self.definitions: Dict[str, List[Symbol]] = {}
        # 全局索引：符号名 -> 引用列表
        self.references: Dict[str, List[SymbolReference]] = {}
        # 动态导入
        self.dynamic_imports: List[DynamicImport] = []
        # 条件导入
        self.conditional_imports: List[ConditionalImport] = []

    def add_file_symbols(self, file_symbols: FileSymbols):
        """添加文件的符号信息"""
        self.file_symbols[file_symbols.file_path] = file_symbols

        # 更新全局索引
        for sym in file_symbols.definitions:
            if sym.name not in self.definitions:
                self.definitions[sym.name] = []
            self.definitions[sym.name].append(sym)

        for ref in file_symbols.references:
            if ref.name not in self.references:
                self.references[ref.name] = []
            self.references[ref.name].append(ref)
        
        # 收集动态导入和条件导入
        self.dynamic_imports.extend(file_symbols.dynamic_imports)
        self.conditional_imports.extend(file_symbols.conditional_imports)

    def get_definition(self, name: str) -> Optional[Symbol]:
        """获取符号的定义"""
        defs = self.definitions.get(name, [])
        return defs[0] if defs else None

    def get_references(self, name: str) -> List[SymbolReference]:
        """获取符号的所有引用"""
        return self.references.get(name, [])

    def is_used_externally(self, symbol: Symbol) -> bool:
        """
        判断符号是否在其他文件中被使用

        Args:
            symbol: 符号定义

        Returns:
            bool: 是否被外部使用
        """
        refs = self.references.get(symbol.name, [])
        for ref in refs:
            if ref.file_path != symbol.file_path:
                return True
        return False
    
    def get_all_exported_symbols(self, file_path: str) -> Set[str]:
        """
        获取文件的所有导出符号
        
        如果定义了 __all__，则返回 __all__ 中的符号
        否则返回所有不以 _ 开头的公共符号
        
        Args:
            file_path: 文件路径
            
        Returns:
            Set[str]: 导出符号集合
        """
        file_sym = self.file_symbols.get(file_path)
        if not file_sym:
            return set()
        
        # 如果有 __all__ 定义且不是动态的，使用 __all__
        if file_sym.has_all_definition and not file_sym.all_is_dynamic:
            return file_sym.exported_names
        
        # 否则返回所有公共符号
        exported = set()
        for sym in file_sym.definitions:
            if sym.is_exported:
                exported.add(sym.name)
        
        return exported


class SymbolExtractor:
    """符号提取器"""

    def __init__(self):
        self.table = SymbolTable()

    def extract_all(self, files: List[Any]) -> SymbolTable:
        """
        从所有文件提取符号

        Args:
            files: 文件列表（每个文件需要有 path 和 content 属性）

        Returns:
            SymbolTable: 符号表
        """
        self.table = SymbolTable()

        for file in files:
            try:
                file_symbols = self.extract_symbols(file)
                self.table.add_file_symbols(file_symbols)
            except Exception as e:
                logger.warning(f"提取文件 {file.path} 的符号失败: {e}")

        return self.table

    def extract_symbols(self, file) -> FileSymbols:
        """
        从单个文件提取符号

        Args:
            file: 文件对象（需要有 path 和 content 属性）

        Returns:
            FileSymbols: 文件符号信息
        """
        file_symbols = FileSymbols(file_path=file.path)

        try:
            tree = ast.parse(file.content)
        except SyntaxError as e:
            logger.warning(f"文件 {file.path} 语法错误: {e}")
            return file_symbols

        # 收集 __all__ 定义（增强版）
        all_names, all_is_dynamic = self._extract_all_names_enhanced(tree)
        file_symbols.exported_names = all_names
        file_symbols.has_all_definition = len(all_names) > 0 or all_is_dynamic
        file_symbols.all_is_dynamic = all_is_dynamic

        # 收集条件导入和动态导入
        self._extract_special_imports(tree, file_symbols)
        
        # 遍历 AST
        for node in ast.walk(tree):
            self._process_node(node, file_symbols, all_names, file.path)

        # 处理普通导入
        for node in ast.walk(tree):
            self._process_import(node, file_symbols)

        return file_symbols

    def _extract_all_names_enhanced(self, tree: ast.AST) -> Tuple[Set[str], bool]:
        """
        增强版 __all__ 提取
        
        支持：
        - 静态列表: __all__ = ['a', 'b']
        - 列表拼接: __all__ = ['a'] + ['b']
        - 列表扩展: __all__ = []; __all__.extend(['a'])
        - 动态生成: __all__ = dir()  # 标记为动态
        
        Args:
            tree: AST 树
            
        Returns:
            Tuple[Set[str], bool]: (名称集合, 是否动态)
        """
        all_names: Set[str] = set()
        is_dynamic = False

        for node in ast.iter_child_nodes(tree):
            # 处理 __all__ = [...]
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        names, dynamic = self._extract_all_value(node.value)
                        all_names.update(names)
                        if dynamic:
                            is_dynamic = True
            
            # 处理 __all__ += [...]
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name) and node.target.id == '__all__':
                    if isinstance(node.op, ast.Add):
                        names, dynamic = self._extract_all_value(node.value)
                        all_names.update(names)
                        if dynamic:
                            is_dynamic = True
            
            # 处理 __all__.extend(...) 或 __all__.append(...)
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    call = node.value
                    if isinstance(call.func, ast.Attribute):
                        if isinstance(call.func.value, ast.Name) and call.func.value.id == '__all__':
                            if call.func.attr in ('extend', 'append'):
                                if call.args:
                                    names, dynamic = self._extract_all_value(call.args[0])
                                    all_names.update(names)
                                    if dynamic:
                                        is_dynamic = True

        return all_names, is_dynamic

    def _extract_all_value(self, value: ast.AST) -> Tuple[Set[str], bool]:
        """
        从 __all__ 的值中提取名称
        
        Args:
            value: __all__ 的值节点
            
        Returns:
            Tuple[Set[str], bool]: (名称集合, 是否动态)
        """
        names: Set[str] = set()
        is_dynamic = False
        
        if isinstance(value, ast.List):
            # 静态列表
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    names.add(elt.value)
                elif isinstance(elt, ast.Str):  # Python 3.7 兼容
                    names.add(elt.s)
        
        elif isinstance(value, ast.BinOp):
            # 列表拼接: ['a'] + ['b']
            if isinstance(value.op, ast.Add):
                left_names, left_dynamic = self._extract_all_value(value.left)
                right_names, right_dynamic = self._extract_all_value(value.right)
                names.update(left_names)
                names.update(right_names)
                is_dynamic = left_dynamic or right_dynamic
        
        elif isinstance(value, ast.Call):
            # 动态调用: list(dir()), [... for ...], etc.
            is_dynamic = True
            if isinstance(value.func, ast.Name):
                # dir(), globals(), etc.
                if value.func.id in ('dir', 'globals', 'vars'):
                    is_dynamic = True
        
        elif isinstance(value, ast.Name):
            # 变量引用: __all__ = SOME_LIST
            is_dynamic = True
        
        return names, is_dynamic

    def _extract_special_imports(self, tree: ast.AST, file_symbols: FileSymbols):
        """
        提取条件导入和动态导入
        
        Args:
            tree: AST 树
            file_symbols: 文件符号信息
        """
        for node in ast.walk(tree):
            # 检测 try/except 块中的条件导入
            if isinstance(node, ast.Try):
                self._process_try_import(node, file_symbols)
            
            # 检测 TYPE_CHECKING 条件导入
            elif isinstance(node, ast.If):
                self._process_if_import(node, file_symbols)
            
            # 检测动态导入: importlib.import_module(), __import__()
            elif isinstance(node, ast.Call):
                self._process_dynamic_import(node, file_symbols)

    def _process_try_import(self, node: ast.Try, file_symbols: FileSymbols):
        """处理 try/except 中的条件导入"""
        for stmt in node.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                # try 块中的导入
                module = self._get_import_module(stmt)
                if module:
                    file_symbols.conditional_imports.append(ConditionalImport(
                        module=module,
                        file_path=file_symbols.file_path,
                        lineno=stmt.lineno,
                        condition_type="try_except",
                        is_fallback=False
                    ))
        
        for handler in node.handlers:
            for stmt in handler.body:
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    # except 块中的回退导入
                    module = self._get_import_module(stmt)
                    if module:
                        file_symbols.conditional_imports.append(ConditionalImport(
                            module=module,
                            file_path=file_symbols.file_path,
                            lineno=stmt.lineno,
                            condition_type="try_except",
                            is_fallback=True
                        ))

    def _process_if_import(self, node: ast.If, file_symbols: FileSymbols):
        """处理 if 块中的条件导入（如 TYPE_CHECKING）"""
        # 检查是否是 TYPE_CHECKING 条件
        is_type_checking = False
        if isinstance(node.test, ast.Name):
            if node.test.id == 'TYPE_CHECKING':
                is_type_checking = True
        elif isinstance(node.test, ast.Attribute):
            if isinstance(node.test.value, ast.Name):
                if node.test.value.id == 'typing' and node.test.attr == 'TYPE_CHECKING':
                    is_type_checking = True
        
        for stmt in node.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                module = self._get_import_module(stmt)
                if module:
                    file_symbols.conditional_imports.append(ConditionalImport(
                        module=module,
                        file_path=file_symbols.file_path,
                        lineno=stmt.lineno,
                        condition_type="if_type_checking" if is_type_checking else "if",
                        is_fallback=False
                    ))

    def _process_dynamic_import(self, node: ast.Call, file_symbols: FileSymbols):
        """处理动态导入调用"""
        func = node.func
        
        # importlib.import_module(...)
        if isinstance(func, ast.Attribute):
            if func.attr == 'import_module':
                if isinstance(func.value, ast.Name) and func.value.id == 'importlib':
                    module_expr = self._get_string_arg(node)
                    assigned_to = self._get_assignment_target(node)
                    file_symbols.dynamic_imports.append(DynamicImport(
                        module_expr=module_expr,
                        file_path=file_symbols.file_path,
                        lineno=node.lineno,
                        import_type="importlib",
                        assigned_to=assigned_to
                    ))
        
        # __import__(...)
        elif isinstance(func, ast.Name):
            if func.id == '__import__':
                module_expr = self._get_string_arg(node)
                assigned_to = self._get_assignment_target(node)
                file_symbols.dynamic_imports.append(DynamicImport(
                    module_expr=module_expr,
                    file_path=file_symbols.file_path,
                    lineno=node.lineno,
                    import_type="__import__",
                    assigned_to=assigned_to
                ))

    def _get_import_module(self, node: ast.AST) -> str:
        """从导入语句获取模块名"""
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else ""
        elif isinstance(node, ast.ImportFrom):
            return node.module or ""
        return ""

    def _get_string_arg(self, call_node: ast.Call) -> str:
        """获取调用的第一个字符串参数"""
        if call_node.args:
            arg = call_node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
            elif isinstance(arg, ast.Str):  # Python 3.7 兼容
                return arg.s
            elif isinstance(arg, ast.Name):
                return f"<variable: {arg.id}>"
        return "<dynamic>"

    def _get_assignment_target(self, node: ast.Call) -> Optional[str]:
        """获取动态导入的赋值目标（如果有）"""
        # 这需要查看父节点，在当前简化实现中返回 None
        return None

    def _process_node(
        self,
        node: ast.AST,
        file_symbols: FileSymbols,
        all_names: Set[str],
        file_path: str
    ):
        """处理 AST 节点"""
        # 函数定义
        if isinstance(node, ast.FunctionDef):
            is_exported = not node.name.startswith('_') or node.name in all_names
            decorators = [self._get_decorator_name(d) for d in node.decorator_list]
            file_symbols.definitions.append(Symbol(
                name=node.name,
                kind='function',
                file_path=file_path,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_exported=is_exported,
                is_in_all=node.name in all_names,
                docstring=ast.get_docstring(node),
                decorators=decorators
            ))

        # 异步函数定义
        elif isinstance(node, ast.AsyncFunctionDef):
            is_exported = not node.name.startswith('_') or node.name in all_names
            decorators = [self._get_decorator_name(d) for d in node.decorator_list]
            file_symbols.definitions.append(Symbol(
                name=node.name,
                kind='function',
                file_path=file_path,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_exported=is_exported,
                is_in_all=node.name in all_names,
                docstring=ast.get_docstring(node),
                decorators=decorators
            ))

        # 类定义
        elif isinstance(node, ast.ClassDef):
            is_exported = not node.name.startswith('_') or node.name in all_names
            decorators = [self._get_decorator_name(d) for d in node.decorator_list]
            file_symbols.definitions.append(Symbol(
                name=node.name,
                kind='class',
                file_path=file_path,
                lineno=node.lineno,
                col_offset=node.col_offset,
                is_exported=is_exported,
                is_in_all=node.name in all_names,
                docstring=ast.get_docstring(node),
                decorators=decorators
            ))

        # 模块级变量赋值
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # 跳过 __all__ 等特殊变量
                    if target.id.startswith('__') and target.id.endswith('__'):
                        continue
                    
                    is_exported = not target.id.startswith('_') or target.id in all_names
                    file_symbols.definitions.append(Symbol(
                        name=target.id,
                        kind='variable',
                        file_path=file_path,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        is_exported=is_exported,
                        is_in_all=target.id in all_names
                    ))

        # 名称引用
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                file_symbols.references.append(SymbolReference(
                    name=node.id,
                    file_path=file_path,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    context='load'
                ))

    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """获取装饰器名称"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}" if isinstance(decorator.value, ast.Name) else decorator.attr
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""

    def _process_import(self, node: ast.AST, file_symbols: FileSymbols):
        """处理导入语句"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if '.' in name:
                    name = name.split('.')[0]
                file_symbols.imports[name] = alias.name

        elif isinstance(node, ast.ImportFrom):
            if node.names:
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    file_symbols.imports[name] = node.module or ''


def extract_symbols(file) -> FileSymbols:
    """
    便捷函数：从单个文件提取符号

    Args:
        file: 文件对象

    Returns:
        FileSymbols: 文件符号信息
    """
    extractor = SymbolExtractor()
    return extractor.extract_symbols(file)
