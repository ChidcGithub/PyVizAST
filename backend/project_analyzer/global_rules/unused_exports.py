"""
未使用导出检测器
检测定义但从未被其他文件使用的公共符号

增强功能：
- 白名单配置支持
- 测试文件智能识别
- 公共 API 检测
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

from .symbol_extractor import SymbolTable, Symbol, SymbolReference

logger = logging.getLogger(__name__)


@dataclass
class WhitelistConfig:
    """白名单配置"""
    # 符号白名单（永远不会报告为未使用）
    symbol_names: Set[str] = field(default_factory=set)
    
    # 文件模式白名单（这些文件中的符号不会被检查）
    file_patterns: List[str] = field(default_factory=list)
    
    # 装饰器白名单（带有这些装饰器的符号不会被报告）
    decorator_names: Set[str] = field(default_factory=set)
    
    # 模块入口点（通常是主入口函数）
    entry_points: Set[str] = field(default_factory=lambda: {'main', 'run', 'app', 'create_app', 'get_app'})
    
    # 插件/扩展点模式
    plugin_patterns: List[str] = field(default_factory=lambda: ['register_*', '*_handler', '*_plugin', '*_hook'])

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WhitelistConfig':
        """从字典创建配置"""
        return cls(
            symbol_names=set(data.get('symbol_names', [])),
            file_patterns=data.get('file_patterns', []),
            decorator_names=set(data.get('decorator_names', [])),
            entry_points=set(data.get('entry_points', ['main', 'run', 'app', 'create_app', 'get_app'])),
            plugin_patterns=data.get('plugin_patterns', ['register_*', '*_handler', '*_plugin', '*_hook'])
        )

    @classmethod
    def default(cls) -> 'WhitelistConfig':
        """获取默认配置"""
        return cls(
            symbol_names={
                '__init__', '__new__', '__call__', '__str__', '__repr__',
                '__len__', '__iter__', '__next__', '__getitem__', '__setitem__',
                '__delitem__', '__contains__', '__bool__', '__int__', '__float__',
                '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__',
                '__hash__', '__enter__', '__exit__', '__getattr__', '__setattr__',
                '__delattr__', '__get__', '__set__', '__delete__',
                '__all__', '__version__', '__author__', '__email__',
            },
            file_patterns=[
                'test_*.py', '*_test.py', 'tests/', 'testing/',
                'conftest.py',  # pytest 配置
                'setup.py', 'setup.cfg',  # 安装配置
                '__init__.py',  # 包初始化（通常只导出）
            ],
            decorator_names={
                'property', 'staticmethod', 'classmethod',
                'abstractmethod', 'abstractproperty',
                'route', 'get', 'post', 'put', 'delete', 'patch',  # web 框架路由
                'click.command', 'click.group', 'click.option', 'click.argument',  # click CLI
                'app.route', 'blueprint.route',  # Flask
                'router.get', 'router.post', 'api_view',  # FastAPI / Django REST
                'pytest.fixture', 'fixture',  # pytest fixtures
                'task', 'shared_task', 'celery.task',  # Celery
                'signal_handler', 'receiver',  # 信号处理
            },
            entry_points={'main', 'run', 'app', 'create_app', 'get_app', 'mainloop'},
            plugin_patterns=['register_*', '*_handler', '*_plugin', '*_hook', '*_callback', 'on_*']
        )


@dataclass
class UnusedExport:
    """未使用的导出信息"""
    name: str  # 符号名称
    file_path: str  # 定义所在文件
    kind: str  # function, class, variable
    lineno: Optional[int] = None
    severity: str = "info"
    description: str = ""
    confidence: str = "medium"  # low, medium, high


class UnusedExportsDetector:
    """
    未使用导出检测器
    检测定义但从未被其他文件使用的公共符号
    """

    # 可能是测试或示例的文件模式
    TEST_FILE_PATTERNS = {'test_', '_test', 'tests/', 'testing/', 'examples/', 'examples/', 'conftest'}

    def __init__(self, whitelist: Optional[WhitelistConfig] = None):
        """
        初始化检测器
        
        Args:
            whitelist: 白名单配置
        """
        self.whitelist = whitelist or WhitelistConfig.default()
        self.unused_exports: List[UnusedExport] = []

    def detect(
        self,
        symbol_table: SymbolTable,
        dependency_graph: Optional[Dict[str, List[str]]] = None
    ) -> List[UnusedExport]:
        """
        检测未使用的导出

        Args:
            symbol_table: 符号表
            dependency_graph: 依赖图（可选，用于更精确的检测）

        Returns:
            List[UnusedExport]: 未使用的导出列表
        """
        self.unused_exports = []

        # 遍历所有文件的定义
        for file_path, file_symbols in symbol_table.file_symbols.items():
            # 跳过测试文件和白名单文件
            if self._should_skip_file(file_path):
                continue

            # 获取该文件导入的符号
            imported_names = set(file_symbols.imports.keys())

            # 检查每个导出的符号
            for symbol in file_symbols.definitions:
                if not self._should_check(symbol, file_path):
                    continue

                # 检查是否被使用
                unused_info = self._check_unused(symbol, symbol_table, imported_names, file_path)
                if unused_info:
                    self.unused_exports.append(unused_info)

        return self.unused_exports

    def _should_skip_file(self, file_path: str) -> bool:
        """判断是否应该跳过文件"""
        # 检查测试文件
        if self._is_test_file(file_path):
            return True
        
        # 检查白名单文件模式
        file_name = Path(file_path).name
        file_path_str = file_path.replace('\\', '/')
        
        for pattern in self.whitelist.file_patterns:
            if pattern.endswith('/'):
                # 目录模式
                if pattern in file_path_str:
                    return True
            else:
                # 文件名模式
                if self._match_pattern(file_name, pattern):
                    return True
        
        return False

    def _should_check(self, symbol: Symbol, file_path: str) -> bool:
        """
        判断符号是否需要检查

        Args:
            symbol: 符号定义
            file_path: 文件路径

        Returns:
            bool: 是否需要检查
        """
        # 只检查导出的符号
        if not symbol.is_exported:
            return False

        # 检查符号白名单
        if symbol.name in self.whitelist.symbol_names:
            return False

        # 检查入口点
        if symbol.name in self.whitelist.entry_points:
            return False

        # 检查插件模式
        for pattern in self.whitelist.plugin_patterns:
            if self._match_pattern(symbol.name, pattern):
                return False

        # 检查装饰器白名单
        for decorator in symbol.decorators:
            if decorator in self.whitelist.decorator_names:
                return False
            # 检查装饰器名称模式
            dec_name = decorator.split('.')[-1]  # 取最后一部分
            if dec_name in self.whitelist.decorator_names:
                return False

        # 排除以 _ 开头的私有符号（不应该被导出）
        if symbol.name.startswith('_'):
            return False

        return True

    def _check_unused(
        self,
        symbol: Symbol,
        symbol_table: SymbolTable,
        local_imports: Set[str],
        file_path: str
    ) -> Optional[UnusedExport]:
        """
        检查符号是否未被使用

        Args:
            symbol: 符号定义
            symbol_table: 符号表
            local_imports: 本地导入的符号名
            file_path: 文件路径

        Returns:
            Optional[UnusedExport]: 如果未使用则返回信息，否则返回 None
        """
        # 获取所有引用
        refs = symbol_table.references.get(symbol.name, [])

        # 检查是否有外部引用
        external_refs = [r for r in refs if r.file_path != symbol.file_path]
        if external_refs:
            return None

        # 检查是否被其他文件导入
        for other_path, other_symbols in symbol_table.file_symbols.items():
            if other_path == symbol.file_path:
                continue

            # 检查是否有 from ... import symbol 或 import module.symbol
            if symbol.name in other_symbols.imports:
                return None

        # 检查是否有同名的导入（可能是 re-export）
        if symbol.name in local_imports:
            return None

        # 确定置信度
        confidence = self._calculate_confidence(symbol, symbol_table)

        return UnusedExport(
            name=symbol.name,
            file_path=symbol.file_path,
            kind=symbol.kind,
            lineno=symbol.lineno,
            severity="info",
            description=f"符号 '{symbol.name}' 在 {symbol.file_path} 中定义但可能未被其他文件使用",
            confidence=confidence
        )

    def _calculate_confidence(self, symbol: Symbol, symbol_table: SymbolTable) -> str:
        """
        计算检测置信度
        
        Args:
            symbol: 符号定义
            symbol_table: 符号表
            
        Returns:
            str: 置信度 (low, medium, high)
        """
        # 如果文件定义了 __all__ 且符号在其中，置信度高
        file_sym = symbol_table.file_symbols.get(symbol.file_path)
        if file_sym and file_sym.has_all_definition:
            if symbol.name in file_sym.exported_names:
                return "high"
            # 在 __all__ 定义但符号不在其中，可能是私有
            return "low"
        
        # 如果有装饰器，置信度低（可能是框架使用的钩子）
        if symbol.decorators:
            return "low"
        
        # 如果是测试文件的相邻文件，置信度低
        has_test_file = any(
            self._is_test_file(fp) 
            for fp in symbol_table.file_symbols.keys()
        )
        if has_test_file:
            return "medium"
        
        return "medium"

    def _is_test_file(self, file_path: str) -> bool:
        """判断是否是测试文件"""
        file_path_lower = file_path.lower()
        for pattern in self.TEST_FILE_PATTERNS:
            if pattern in file_path_lower:
                return True
        return False

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """
        简单的模式匹配
        
        支持 * 通配符
        """
        if '*' not in pattern:
            return name == pattern
        
        # 转换为正则表达式
        regex_pattern = pattern.replace('*', '.*')
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, name))


def detect_unused_exports(
    symbol_table: SymbolTable,
    dependency_graph: Optional[Dict[str, List[str]]] = None,
    whitelist: Optional[WhitelistConfig] = None
) -> List[Dict]:
    """
    便捷函数：检测未使用的导出

    Args:
        symbol_table: 符号表
        dependency_graph: 依赖图
        whitelist: 白名单配置

    Returns:
        List[Dict]: 未使用导出信息列表
    """
    detector = UnusedExportsDetector(whitelist=whitelist)
    unused = detector.detect(symbol_table, dependency_graph)

    return [
        {
            "name": u.name,
            "file_path": u.file_path,
            "kind": u.kind,
            "lineno": u.lineno,
            "severity": u.severity,
            "description": u.description,
            "confidence": u.confidence,
        }
        for u in unused
    ]
