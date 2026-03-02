"""
项目级分析模块
支持上传项目 zip 包，扫描并分析所有 Python 文件

包含：
- 文件扫描器（支持 zip 和目录）
- 文件分析器（复用现有分析器）
- 依赖图构建器
- 全局问题检测器
- 缓存和持久化存储
- CLI 命令行工具
"""

from .scanner import ProjectScanner, ScanResult, scan_directory, extract_and_scan
from .models import (
    ProjectFile,
    ProjectAnalysisResult,
    ProjectFileAnalysis,
    FileSummary,
    ProjectSummary,
    ProcessResult,
    GlobalIssue,
    ImportInfo,
    ExportInfo,
    FileDependency,
    ProjectDependencies,
    CrossFileIssue,
)
from .processor import process_files
from .analyzers import FileAnalyzer, analyze_single_file
from .dependency import DependencyGraphBuilder, build_dependency_graph
from .summary import SummaryGenerator, generate_summary

# 缓存和存储
from .cache import (
    ASTCache,
    DependencyGraphCache,
    get_ast_cache,
    get_dependency_cache,
    clear_all_caches,
)
from .storage import (
    AnalysisStorage,
    IncrementalAnalyzer,
    get_storage,
)

__all__ = [
    # 扫描器
    'ProjectScanner',
    'ScanResult',
    'scan_directory',
    'extract_and_scan',
    
    # 模型
    'ProjectFile',
    'ProjectAnalysisResult',
    'ProjectFileAnalysis',
    'FileSummary',
    'ProjectSummary',
    'ProcessResult',
    'GlobalIssue',
    'ImportInfo',
    'ExportInfo',
    'FileDependency',
    'ProjectDependencies',
    'CrossFileIssue',
    
    # 处理器
    'process_files',
    'FileAnalyzer',
    'analyze_single_file',
    
    # 依赖分析
    'DependencyGraphBuilder',
    'build_dependency_graph',
    
    # 摘要生成
    'SummaryGenerator',
    'generate_summary',
    
    # 缓存
    'ASTCache',
    'DependencyGraphCache',
    'get_ast_cache',
    'get_dependency_cache',
    'clear_all_caches',
    
    # 存储
    'AnalysisStorage',
    'IncrementalAnalyzer',
    'get_storage',
]
