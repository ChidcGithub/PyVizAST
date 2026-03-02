"""
全局规则检测模块
检测跨文件的代码问题
"""

from .cycle_detector import CycleDetector, detect_cycles
from .symbol_extractor import (
    SymbolExtractor, 
    extract_symbols, 
    SymbolTable,
    Symbol,
    SymbolReference,
    FileSymbols,
    DynamicImport,
    ConditionalImport,
)
from .unused_exports import (
    UnusedExportsDetector, 
    detect_unused_exports,
    WhitelistConfig,
    UnusedExport,
)
from .duplicate_code import DuplicateCodeDetector, detect_duplicates
from .module_quality import (
    ModuleQualityDetector,
    detect_module_issues,
    DependencyAnalyzer,
    DependencyMetrics,
)

__all__ = [
    # 循环依赖检测
    'CycleDetector',
    'detect_cycles',
    
    # 符号提取
    'SymbolExtractor',
    'extract_symbols',
    'SymbolTable',
    'Symbol',
    'SymbolReference',
    'FileSymbols',
    'DynamicImport',
    'ConditionalImport',
    
    # 未使用导出检测
    'UnusedExportsDetector',
    'detect_unused_exports',
    'WhitelistConfig',
    'UnusedExport',
    
    # 重复代码检测
    'DuplicateCodeDetector',
    'detect_duplicates',
    
    # 模块质量检测
    'ModuleQualityDetector',
    'detect_module_issues',
    'DependencyAnalyzer',
    'DependencyMetrics',
]
