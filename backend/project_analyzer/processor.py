"""
文件处理器
负责对扫描到的文件进行完整分析，支持并发处理
"""

import ast
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Set

from .models import (
    ProjectFile, ProjectFileAnalysis, FileSummary, ProjectSummary,
    ProcessResult, CrossFileIssue, ProjectDependencies, GlobalIssue
)
from .analyzers import FileAnalyzer
from .dependency import build_dependency_graph, DependencyGraphBuilder
from .global_rules import (
    detect_cycles,
    SymbolExtractor,
    detect_unused_exports,
    detect_duplicates,
)
from .summary import generate_summary

logger = logging.getLogger(__name__)

# 并发分析的最大线程数
MAX_WORKERS = 4


def process_files(
    files: List[ProjectFile],
    quick_mode: bool = False,
    max_workers: int = MAX_WORKERS
) -> ProcessResult:
    """
    处理扫描到的文件，执行完整分析（支持并发）

    Args:
        files: 扫描到的文件列表
        quick_mode: 快速模式（仅复杂度分析）
        max_workers: 并发分析的最大线程数

    Returns:
        ProcessResult: 处理结果
    """
    # 创建分析器实例
    analyzer = FileAnalyzer(quick_mode=quick_mode)

    # 使用线程池并发分析
    analysis_results: Dict[str, Dict[str, Any]] = {}

    if max_workers > 1 and len(files) > 1:
        # 并发分析
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(_analyze_file_safe, analyzer, f): f
                for f in files
            }

            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    result = future.result()
                    analysis_results[file.path] = result
                except Exception as e:
                    logger.error(f"分析文件 {file.path} 失败: {e}")
                    analysis_results[file.path] = {
                        "success": False,
                        "error": str(e),
                        "complexity": None,
                        "issues": [],
                    }
    else:
        # 单线程分析
        for file in files:
            analysis_results[file.path] = _analyze_file_safe(analyzer, file)

    # 构建依赖图（使用新的依赖模块）
    dependency_graph, project_dependencies = build_dependency_graph(files)

    # 处理分析结果
    file_analyses: List[ProjectFileAnalysis] = []
    total_complexity = 0
    total_maintainability = 0.0

    for file in files:
        result = analysis_results.get(file.path, {})

        # 更新文件的 analysis 字段
        file.analysis = result

        # 构建文件摘要
        complexity = result.get("complexity")
        issues = result.get("issues", [])

        file_summary = FileSummary(
            path=file.path,
            line_count=file.line_count,
            cyclomatic_complexity=complexity.get("cyclomatic_complexity", 0) if complexity else 0,
            cognitive_complexity=complexity.get("cognitive_complexity", 0) if complexity else 0,
            function_count=complexity.get("function_count", 0) if complexity else 0,
            class_count=complexity.get("class_count", 0) if complexity else 0,
            issue_count=len(issues),
            critical_issues=sum(1 for i in issues if i.get("severity") == "critical"),
            error_issues=sum(1 for i in issues if i.get("severity") == "error"),
            warning_issues=sum(1 for i in issues if i.get("severity") == "warning"),
            info_issues=sum(1 for i in issues if i.get("severity") == "info"),
        )

        # 创建文件分析结果
        file_analysis = ProjectFileAnalysis(
            file=file,
            summary=file_summary,
            issues=issues,
            complexity=complexity,
            performance_hotspots=(result.get("performance") or {}).get("hotspots", []),
            suggestions=result.get("suggestions") or [],
            error=result.get("error"),
        )

        file_analyses.append(file_analysis)

        if complexity:
            total_complexity += complexity.get("cyclomatic_complexity", 0)
            total_maintainability += complexity.get("maintainability_index", 0)

    # 执行全局检测（在构建摘要之前）
    global_issues = _run_global_detectors(files, dependency_graph, project_dependencies)

    # 构建项目摘要（传入依赖和全局问题信息）
    project_summary = _build_project_summary(
        file_analyses, 
        total_complexity, 
        total_maintainability,
        dependencies=project_dependencies,
        global_issues=global_issues
    )

    # 构建跨文件问题（从全局问题转换）
    cross_file_issues = _convert_to_cross_file_issues(global_issues)

    return ProcessResult(
        files=file_analyses,
        summary=project_summary,
        dependencies=project_dependencies,
        cross_file_issues=cross_file_issues,
        global_issues=global_issues
    )


def _analyze_file_safe(analyzer: FileAnalyzer, file: ProjectFile) -> Dict[str, Any]:
    """
    安全地分析单个文件（用于并发调用）

    Args:
        analyzer: 文件分析器实例
        file: 项目文件对象

    Returns:
        Dict[str, Any]: 分析结果
    """
    try:
        return analyzer.analyze_file(file)
    except Exception as e:
        logger.error(f"分析文件 {file.path} 时发生错误: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "complexity": None,
            "issues": [],
        }


def _build_project_summary(
    file_analyses: List[ProjectFileAnalysis],
    total_complexity: int,
    total_maintainability: float,
    dependencies: ProjectDependencies = None,
    global_issues: List[GlobalIssue] = None
) -> ProjectSummary:
    """
    构建项目摘要

    Args:
        file_analyses: 文件分析结果列表
        total_complexity: 总复杂度
        total_maintainability: 总可维护性指数
        dependencies: 依赖信息
        global_issues: 全局问题列表

    Returns:
        ProjectSummary: 项目摘要
    """
    # 使用 generate_summary 生成扩展摘要
    extended_summary = generate_summary(file_analyses, dependencies, global_issues)
    
    file_count = len(file_analyses)
    total_lines = sum(f.summary.line_count for f in file_analyses)
    total_issues = sum(f.summary.issue_count for f in file_analyses)
    critical_issues = sum(f.summary.critical_issues for f in file_analyses)
    error_issues = sum(f.summary.error_issues for f in file_analyses)
    warning_issues = sum(f.summary.warning_issues for f in file_analyses)
    info_issues = sum(f.summary.info_issues for f in file_analyses)
    total_functions = sum(f.summary.function_count for f in file_analyses)
    total_classes = sum(f.summary.class_count for f in file_analyses)

    return ProjectSummary(
        total_files=file_count,
        total_lines=total_lines,
        total_issues=total_issues,
        critical_issues=critical_issues,
        error_issues=error_issues,
        warning_issues=warning_issues,
        info_issues=info_issues,
        avg_complexity=total_complexity / file_count if file_count > 0 else 0,
        avg_maintainability=total_maintainability / file_count if file_count > 0 else 0,
        total_functions=total_functions,
        total_classes=total_classes,
        file_summaries=[f.summary for f in file_analyses],
        # 扩展字段
        internal_dependencies=extended_summary.get("internal_dependencies", 0),
        external_dependencies=extended_summary.get("external_dependencies", 0),
        circular_dependencies=extended_summary.get("circular_dependencies", 0),
        max_cyclomatic_complexity=extended_summary.get("max_cyclomatic_complexity", 0),
        max_cognitive_complexity=extended_summary.get("max_cognitive_complexity", 0),
        most_complex_files=extended_summary.get("most_complex_files", []),
        most_issue_files=extended_summary.get("most_issue_files", []),
        largest_files=extended_summary.get("largest_files", []),
        health_score=extended_summary.get("health_score", {}),
    )


def _run_global_detectors(
    files: List[ProjectFile],
    dependency_graph: Dict[str, List[str]],
    project_dependencies: ProjectDependencies
) -> List[GlobalIssue]:
    """
    运行全局检测器

    Args:
        files: 文件列表
        dependency_graph: 文件级依赖图
        project_dependencies: 项目依赖信息

    Returns:
        List[GlobalIssue]: 全局问题列表
    """
    global_issues: List[GlobalIssue] = []
    issue_id = 0

    # 1. 循环依赖检测
    cycles = detect_cycles(dependency_graph)
    for cycle_info in cycles:
        issue_id += 1
        global_issues.append(GlobalIssue.from_cycle(
            cycle=cycle_info["cycle"],
            issue_id=issue_id
        ))

    # 2. 符号提取和未使用导出检测
    try:
        symbol_extractor = SymbolExtractor()
        symbol_table = symbol_extractor.extract_all(files)

        unused = detect_unused_exports(symbol_table, dependency_graph)
        for unused_info in unused:
            issue_id += 1
            global_issues.append(GlobalIssue.from_unused_export(
                name=unused_info["name"],
                file_path=unused_info["file_path"],
                kind=unused_info["kind"],
                lineno=unused_info.get("lineno"),
                issue_id=issue_id
            ))
    except Exception as e:
        logger.warning(f"符号分析失败: {e}")

    # 3. 重复代码检测
    try:
        duplicates = detect_duplicates(files, min_lines=5)
        for dup_info in duplicates:
            issue_id += 1
            global_issues.append(GlobalIssue.from_duplicate(
                blocks=dup_info["blocks"],
                issue_id=issue_id
            ))
    except Exception as e:
        logger.warning(f"重复代码检测失败: {e}")

    return global_issues


def _convert_to_cross_file_issues(global_issues: List[GlobalIssue]) -> List[CrossFileIssue]:
    """
    将全局问题转换为跨文件问题（兼容旧格式）

    Args:
        global_issues: 全局问题列表

    Returns:
        List[CrossFileIssue]: 跨文件问题列表
    """
    cross_file_issues: List[CrossFileIssue] = []

    for issue in global_issues:
        cross_file_issues.append(CrossFileIssue(
            id=issue.id,
            issue_type=issue.issue_type,
            severity=issue.severity,
            message=issue.message,
            involved_files=[loc.get("file_path", "") for loc in issue.locations if loc.get("file_path")],
            details=issue.details
        ))

    return cross_file_issues