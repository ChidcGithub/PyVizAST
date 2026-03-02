#!/usr/bin/env python3
"""
PyVizAST CLI - 命令行项目分析工具

允许在本地运行项目分析并输出 JSON 报告，便于集成到 CI/CD。

使用方法:
    python -m backend.project_analyzer.cli analyze ./myproject.zip
    python -m backend.project_analyzer.cli analyze ./src --format json --output report.json
    python -m backend.project_analyzer.cli check ./src --fail-on error
"""

import argparse
import json
import logging
import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional

# 设置路径以导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.project_analyzer.scanner import ProjectScanner
from backend.project_analyzer.processor import process_files
from backend.project_analyzer.models import ProjectAnalysisResult

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_project(
    source: Path,
    quick_mode: bool = False,
    incremental: bool = False,
    thresholds: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    分析项目
    
    Args:
        source: 源路径（zip 文件或目录）
        quick_mode: 快速模式
        incremental: 是否增量分析
        thresholds: 自定义阈值
        
    Returns:
        Dict: 分析结果
    """
    scanner = ProjectScanner()
    
    if source.is_file() and source.suffix == '.zip':
        # 处理 zip 文件
        with open(source, 'rb') as f:
            zip_bytes = f.read()
        scan_result = scanner.extract_and_scan(zip_bytes)
    elif source.is_dir():
        # 处理目录
        scan_result = scanner.scan_directory(str(source))
    else:
        raise ValueError(f"不支持的源类型: {source}")
    
    if not scan_result.success:
        raise RuntimeError(f"扫描失败: {scan_result.error_message}")
    
    # 执行分析
    process_result = process_files(
        scan_result.files,
        quick_mode=quick_mode
    )
    
    # 构建结果
    result = ProjectAnalysisResult(
        project_name=source.stem if source.is_file() else source.name,
        files=process_result.files,
        summary=process_result.summary,
        dependencies=process_result.dependencies,
        cross_file_issues=process_result.cross_file_issues,
        global_issues=process_result.global_issues
    )
    
    return result.model_dump()


def check_quality(
    result: Dict[str, Any],
    fail_on: str = "error",
    thresholds: Optional[Dict[str, int]] = None
) -> int:
    """
    检查项目质量
    
    Args:
        result: 分析结果
        fail_on: 失败级别
        thresholds: 自定义阈值
        
    Returns:
        int: 退出码 (0=成功, 1=失败)
    """
    severity_order = {'critical': 0, 'error': 1, 'warning': 2, 'info': 3}
    fail_level = severity_order.get(fail_on, 1)
    
    summary = result.get('summary', {})
    
    # 检查问题数量
    issues = {
        'critical': summary.get('critical_issues', 0),
        'error': summary.get('error_issues', 0),
        'warning': summary.get('warning_issues', 0),
        'info': summary.get('info_issues', 0)
    }
    
    # 检查是否超过阈值
    for severity, count in issues.items():
        if severity_order.get(severity, 3) <= fail_level and count > 0:
            return 1
    
    # 检查健康评分
    health_score = summary.get('health_score', {})
    if health_score:
        score = health_score.get('score', 100)
        grade = health_score.get('grade', 'A')
        
        if score < 60 or grade == 'F':
            if fail_level <= severity_order.get('error', 1):
                return 1
    
    return 0


def print_summary(result: Dict[str, Any]):
    """打印分析摘要"""
    summary = result.get('summary', {})
    health = summary.get('health_score', {})
    
    print("\n" + "=" * 60)
    print("PyVizAST 项目分析报告")
    print("=" * 60)
    
    # 基本信息
    print(f"\n项目: {result.get('project_name', 'unknown')}")
    print(f"文件数: {summary.get('total_files', 0)}")
    print(f"代码行数: {summary.get('total_lines', 0):,}")
    print(f"函数数: {summary.get('total_functions', 0)}")
    print(f"类数: {summary.get('total_classes', 0)}")
    
    # 健康评分
    if health:
        print(f"\n健康评分: {health.get('score', 0)} ({health.get('grade', 'F')})")
    
    # 问题统计
    print(f"\n问题统计:")
    print(f"  严重: {summary.get('critical_issues', 0)}")
    print(f"  错误: {summary.get('error_issues', 0)}")
    print(f"  警告: {summary.get('warning_issues', 0)}")
    print(f"  提示: {summary.get('info_issues', 0)}")
    
    # 复杂度
    print(f"\n复杂度:")
    print(f"  平均圈复杂度: {summary.get('avg_complexity', 0):.1f}")
    print(f"  最大圈复杂度: {summary.get('max_cyclomatic_complexity', 0)}")
    
    # 依赖
    deps = result.get('dependencies', {})
    if deps:
        print(f"\n依赖:")
        print(f"  内部依赖: {summary.get('internal_dependencies', 0)}")
        print(f"  外部依赖: {len(deps.get('external', []))}")
        print(f"  循环依赖: {summary.get('circular_dependencies', 0)}")
    
    # 全局问题
    global_issues = result.get('global_issues', [])
    if global_issues:
        print(f"\n全局问题:")
        for issue in global_issues[:5]:
            print(f"  - [{issue.get('severity', 'info')}] {issue.get('message', '')}")
        if len(global_issues) > 5:
            print(f"  ... 还有 {len(global_issues) - 5} 个问题")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='PyVizAST 命令行项目分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析 zip 文件
  python -m backend.project_analyzer.cli analyze myproject.zip

  # 分析目录
  python -m backend.project_analyzer.cli analyze ./src

  # 输出 JSON 报告
  python -m backend.project_analyzer.cli analyze ./src --format json --output report.json

  # CI 检查（有错误时退出码非零）
  python -m backend.project_analyzer.cli check ./src --fail-on error

  # 快速模式（仅复杂度分析）
  python -m backend.project_analyzer.cli analyze ./src --quick
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='分析项目')
    analyze_parser.add_argument(
        'source',
        type=str,
        help='源路径（zip 文件或目录）'
    )
    analyze_parser.add_argument(
        '--format', '-f',
        choices=['text', 'json', 'summary'],
        default='text',
        help='输出格式 (默认: text)'
    )
    analyze_parser.add_argument(
        '--output', '-o',
        type=str,
        help='输出文件路径（默认输出到标准输出）'
    )
    analyze_parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='快速模式（仅复杂度分析）'
    )
    analyze_parser.add_argument(
        '--incremental', '-i',
        action='store_true',
        help='增量分析（使用缓存）'
    )
    analyze_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    # check 命令
    check_parser = subparsers.add_parser('check', help='检查项目质量（用于 CI）')
    check_parser.add_argument(
        'source',
        type=str,
        help='源路径（zip 文件或目录）'
    )
    check_parser.add_argument(
        '--fail-on',
        choices=['critical', 'error', 'warning', 'info'],
        default='error',
        help='失败级别 (默认: error)'
    )
    check_parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='快速模式'
    )
    check_parser.add_argument(
        '--output', '-o',
        type=str,
        help='输出报告文件路径'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # 设置日志级别
    if getattr(args, 'verbose', False):
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        source = Path(args.source)
        
        if not source.exists():
            print(f"错误: 源路径不存在: {source}", file=sys.stderr)
            return 1
        
        # 执行分析
        result = analyze_project(
            source,
            quick_mode=getattr(args, 'quick', False),
            incremental=getattr(args, 'incremental', False)
        )
        
        if args.command == 'analyze':
            format_type = args.format
            
            if format_type == 'text' or format_type == 'summary':
                print_summary(result)
            elif format_type == 'json':
                output = json.dumps(result, indent=2, ensure_ascii=False)
                
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(output)
                    print(f"报告已保存到: {args.output}")
                else:
                    print(output)
        
        elif args.command == 'check':
            exit_code = check_quality(result, fail_on=args.fail_on)
            
            # 打印摘要
            print_summary(result)
            
            # 保存报告（如果指定）
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"报告已保存到: {args.output}")
            
            if exit_code != 0:
                print(f"\n质量检查失败 (级别: {args.fail_on})", file=sys.stderr)
            
            return exit_code
        
        return 0
        
    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=getattr(args, 'verbose', False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
