"""
重复代码检测器
检测跨文件的相似代码块
"""

import ast
import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CodeBlock:
    """代码块信息"""
    file_path: str
    start_lineno: int
    end_lineno: int
    content: str
    node_type: str  # function, class, method
    name: Optional[str] = None
    hash: str = ""


@dataclass
class DuplicateGroup:
    """重复代码组"""
    blocks: List[CodeBlock]
    similarity: float = 1.0
    description: str = ""


class DuplicateCodeDetector:
    """
    重复代码检测器
    使用多种方法检测跨文件的重复代码
    """

    # 最小代码块行数
    MIN_LINES = 5
    
    # 最小相似度阈值
    MIN_SIMILARITY = 0.8

    def __init__(self, min_lines: int = MIN_LINES, min_similarity: float = MIN_SIMILARITY):
        self.min_lines = min_lines
        self.min_similarity = min_similarity
        self.duplicates: List[DuplicateGroup] = []
        self._code_blocks: List[CodeBlock] = []

    def detect(self, files: List[Any]) -> List[DuplicateGroup]:
        """
        检测重复代码

        Args:
            files: 文件列表

        Returns:
            List[DuplicateGroup]: 重复代码组列表
        """
        self.duplicates = []
        self._code_blocks = []

        # 1. 提取所有代码块
        for file in files:
            try:
                blocks = self._extract_code_blocks(file)
                self._code_blocks.extend(blocks)
            except Exception as e:
                logger.warning(f"提取文件 {file.path} 的代码块失败: {e}")

        # 2. 使用精确匹配检测（完全相同的代码）
        exact_duplicates = self._find_exact_duplicates()
        self.duplicates.extend(exact_duplicates)

        # 3. 使用结构相似性检测（可选，更高级）
        # structural_duplicates = self._find_structural_duplicates()
        # self.duplicates.extend(structural_duplicates)

        return self.duplicates

    def _extract_code_blocks(self, file) -> List[CodeBlock]:
        """
        从文件提取代码块

        Args:
            file: 文件对象

        Returns:
            List[CodeBlock]: 代码块列表
        """
        blocks: List[CodeBlock] = []

        try:
            tree = ast.parse(file.content)
        except SyntaxError:
            return blocks

        source_lines = file.content.splitlines()

        for node in ast.walk(tree):
            # 函数定义
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                block = self._create_block(node, source_lines, file.path, 'function')
                if block:
                    blocks.append(block)

            # 类定义
            elif isinstance(node, ast.ClassDef):
                block = self._create_block(node, source_lines, file.path, 'class')
                if block:
                    blocks.append(block)

        return blocks

    def _create_block(
        self,
        node: ast.AST,
        source_lines: List[str],
        file_path: str,
        node_type: str
    ) -> Optional[CodeBlock]:
        """
        创建代码块

        Args:
            node: AST 节点
            source_lines: 源代码行列表
            file_path: 文件路径
            node_type: 节点类型

        Returns:
            Optional[CodeBlock]: 代码块，如果太小则返回 None
        """
        if not hasattr(node, 'lineno') or not hasattr(node, 'end_lineno'):
            return None

        start = node.lineno
        end = node.end_lineno

        # 检查最小行数
        if end - start + 1 < self.min_lines:
            return None

        # 提取代码内容
        content = '\n'.join(source_lines[start - 1:end])

        # 计算哈希（标准化后）
        normalized = self._normalize_code(content)
        code_hash = hashlib.md5(normalized.encode()).hexdigest()

        name = getattr(node, 'name', None)

        return CodeBlock(
            file_path=file_path,
            start_lineno=start,
            end_lineno=end,
            content=content,
            node_type=node_type,
            name=name,
            hash=code_hash
        )

    def _normalize_code(self, code: str) -> str:
        """
        标准化代码（移除空白和注释）

        Args:
            code: 原始代码

        Returns:
            str: 标准化后的代码
        """
        lines = []
        for line in code.splitlines():
            # 移除注释
            if '#' in line:
                line = line[:line.index('#')]
            # 移除首尾空白
            line = line.strip()
            if line:
                lines.append(line)
        return '\n'.join(lines)

    def _find_exact_duplicates(self) -> List[DuplicateGroup]:
        """
        查找完全相同的代码块

        Returns:
            List[DuplicateGroup]: 重复代码组列表
        """
        # 按哈希分组
        hash_groups: Dict[str, List[CodeBlock]] = defaultdict(list)

        for block in self._code_blocks:
            hash_groups[block.hash].append(block)

        # 提取重复组
        duplicates: List[DuplicateGroup] = []

        for code_hash, blocks in hash_groups.items():
            if len(blocks) > 1:
                # 过滤同一文件内的重复
                unique_files = set(b.file_path for b in blocks)
                if len(unique_files) > 1:  # 只报告跨文件的重复
                    duplicates.append(DuplicateGroup(
                        blocks=blocks,
                        similarity=1.0,
                        description=f"发现 {len(blocks)} 个完全相同的代码块"
                    ))

        return duplicates

    def _find_structural_duplicates(self) -> List[DuplicateGroup]:
        """
        查找结构相似的代码块（简化实现）

        Returns:
            List[DuplicateGroup]: 重复代码组列表
        """
        # TODO: 实现 AST 结构比较
        # 可以使用 tree edit distance 或 AST fingerprinting
        return []


def detect_duplicates(files: List[Any], min_lines: int = 5) -> List[Dict]:
    """
    便捷函数：检测重复代码

    Args:
        files: 文件列表
        min_lines: 最小代码行数

    Returns:
        List[Dict]: 重复代码信息列表
    """
    detector = DuplicateCodeDetector(min_lines=min_lines)
    duplicates = detector.detect(files)

    result = []
    for dup in duplicates:
        result.append({
            "similarity": dup.similarity,
            "description": dup.description,
            "blocks": [
                {
                    "file_path": b.file_path,
                    "start_lineno": b.start_lineno,
                    "end_lineno": b.end_lineno,
                    "node_type": b.node_type,
                    "name": b.name,
                    "line_count": b.end_lineno - b.start_lineno + 1,
                }
                for b in dup.blocks
            ]
        })

    return result
