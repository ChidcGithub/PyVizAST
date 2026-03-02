"""
文件分析器
复用现有分析器对单个文件进行完整分析
"""

import ast
import logging
from typing import Dict, Any, Optional

from ..analyzers import (
    ComplexityAnalyzer,
    PerformanceAnalyzer,
    CodeSmellDetector,
    SecurityScanner
)
from ..optimizers import SuggestionEngine
from .models import ProjectFile

logger = logging.getLogger(__name__)


class FileAnalyzer:
    """
    文件分析器类
    复用现有的单文件分析器，对项目中的单个文件进行完整分析
    """

    def __init__(self, quick_mode: bool = False):
        """
        初始化文件分析器

        Args:
            quick_mode: 快速模式，仅执行复杂度分析
        """
        self.quick_mode = quick_mode

    def analyze_file(self, file: ProjectFile) -> Dict[str, Any]:
        """
        分析单个文件

        Args:
            file: 项目文件对象

        Returns:
            Dict[str, Any]: 包含各维度分析结果的字典
        """
        result = {
            "success": False,
            "error": None,
            "complexity": None,
            "performance": None,
            "security": None,
            "code_smells": None,
            "issues": [],
            "suggestions": [],
        }

        try:
            # 解析 AST
            tree = ast.parse(file.content)
            code = file.content

            # 复杂度分析（总是执行）
            complexity_analyzer = ComplexityAnalyzer()
            complexity = complexity_analyzer.analyze(code, tree)
            result["complexity"] = complexity.model_dump()
            result["issues"].extend([issue.model_dump() for issue in complexity_analyzer.get_issues()])

            if not self.quick_mode:
                # 性能分析
                performance_analyzer = PerformanceAnalyzer()
                hotspots = performance_analyzer.analyze(code, tree)
                result["performance"] = {
                    "hotspots": [h.model_dump() for h in hotspots],
                }
                result["issues"].extend([issue.model_dump() for issue in performance_analyzer.get_issues()])

                # 代码异味检测
                code_smell_detector = CodeSmellDetector()
                code_smell_detector.analyze(code, tree)
                result["code_smells"] = {
                    "summary": code_smell_detector.get_summary(),
                }
                result["issues"].extend([issue.model_dump() for issue in code_smell_detector.issues])

                # 安全扫描
                security_scanner = SecurityScanner()
                security_scanner.scan(code, tree)
                result["security"] = {
                    "summary": security_scanner.get_security_summary(),
                }
                result["issues"].extend([issue.model_dump() for issue in security_scanner.issues])

                # 生成优化建议
                suggestion_engine = SuggestionEngine()
                # 收集所有问题用于生成建议
                all_issues = result["issues"]
                suggestions = suggestion_engine.generate_suggestions(code, tree, [])
                result["suggestions"] = [s.model_dump() for s in suggestions]

            result["success"] = True

        except SyntaxError as e:
            result["error"] = f"语法错误: {str(e)}"
            result["issues"].append({
                "id": f"syntax-error-{file.path}",
                "type": "syntax",
                "severity": "error",
                "message": f"语法错误: {str(e)}",
                "lineno": e.lineno,
            })
            logger.warning(f"文件 {file.path} 语法错误: {e}")

        except Exception as e:
            result["error"] = f"分析失败: {str(e)}"
            result["issues"].append({
                "id": f"analysis-error-{file.path}",
                "type": "analysis",
                "severity": "warning",
                "message": f"分析失败: {str(e)}",
            })
            logger.error(f"分析文件 {file.path} 失败: {e}", exc_info=True)

        return result

    def analyze_file_quick(self, file: ProjectFile) -> Dict[str, Any]:
        """
        快速分析单个文件（仅复杂度分析）

        Args:
            file: 项目文件对象

        Returns:
            Dict[str, Any]: 包含复杂度分析结果的字典
        """
        old_mode = self.quick_mode
        self.quick_mode = True
        result = self.analyze_file(file)
        self.quick_mode = old_mode
        return result


def analyze_single_file(file: ProjectFile, quick_mode: bool = False) -> Dict[str, Any]:
    """
    便捷函数：分析单个文件

    Args:
        file: 项目文件对象
        quick_mode: 是否使用快速模式

    Returns:
        Dict[str, Any]: 分析结果
    """
    analyzer = FileAnalyzer(quick_mode=quick_mode)
    return analyzer.analyze_file(file)
