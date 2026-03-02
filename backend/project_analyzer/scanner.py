"""
项目扫描器
负责解压和扫描项目文件
"""

import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

from .models import ProjectFile, ScanResult

logger = logging.getLogger(__name__)


# 配置常量
MAX_FILE_SIZE = 5 * 1024 * 1024  # 单个文件最大 5MB
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 总解压大小最大 100MB
MAX_FILES = 1000  # 最大文件数量
MAX_PATH_LENGTH = 500  # 最大路径长度
SKIP_DIRS = {
    '__pycache__', '.git', '.svn', '.hg',
    'node_modules', 'venv', '.venv', 'env', '.env',
    'dist', 'build', 'egg-info', '.tox', '.pytest_cache',
    '.mypy_cache', '.idea', '.vscode'
}
SKIP_FILE_PATTERNS = {
    '.pyc', '.pyo', '.pyd',  # Python 编译文件
}


class ProjectScanner:
    """项目扫描器类"""

    def __init__(
        self,
        max_file_size: int = MAX_FILE_SIZE,
        max_total_size: int = MAX_TOTAL_SIZE,
        max_files: int = MAX_FILES,
        skip_dirs: Optional[set] = None,
    ):
        """
        初始化扫描器

        Args:
            max_file_size: 单个文件最大字节数
            max_total_size: 总解压大小最大字节数
            max_files: 最大文件数量
            skip_dirs: 要跳过的目录名集合
        """
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self.max_files = max_files
        self.skip_dirs = skip_dirs or SKIP_DIRS

    def extract_and_scan(self, zip_bytes: bytes) -> ScanResult:
        """
        解压并扫描 zip 数据中的 Python 文件

        Args:
            zip_bytes: zip 文件的字节数据

        Returns:
            ScanResult: 扫描结果
        """
        files: List[ProjectFile] = []
        skipped_files: List[str] = []
        total_size = 0

        try:
            # 使用内存中的 zip 文件
            zip_buffer = io.BytesIO(zip_bytes)

            # 验证是否为有效 zip 文件
            if not zipfile.is_zipfile(zip_buffer):
                return ScanResult(
                    success=False,
                    files=[],
                    skipped_files=[],
                    error_message="无效的 ZIP 文件格式"
                )

            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # 安全检查：检测 Zip Slip 漏洞
                for info in zf.infolist():
                    if self._is_unsafe_path(info.filename):
                        return ScanResult(
                            success=False,
                            files=[],
                            skipped_files=[],
                            error_message=f"检测到不安全的文件路径: {info.filename}"
                        )

                # 先检查文件数量
                file_count = sum(
                    1 for info in zf.infolist()
                    if not info.is_dir() and info.filename.lower().endswith('.py')
                )
                if file_count > self.max_files:
                    return ScanResult(
                        success=False,
                        files=[],
                        skipped_files=[],
                        error_message=f"文件数量超出限制 ({file_count} > {self.max_files})"
                    )

                # 遍历 zip 中的文件
                for info in zf.infolist():
                    # 跳过目录
                    if info.is_dir():
                        continue

                    filename = info.filename

                    # 跳过非 Python 文件
                    if not filename.lower().endswith('.py'):
                        continue

                    # 跳过特定目录
                    if self._should_skip_path(filename):
                        skipped_files.append(filename)
                        continue

                    # 检查文件大小
                    file_size = info.file_size
                    if file_size > self.max_file_size:
                        skipped_files.append(f"{filename} (文件过大: {file_size} 字节)")
                        continue

                    # 检查总大小
                    if total_size + file_size > self.max_total_size:
                        logger.warning(f"总解压大小超限，停止扫描")
                        break

                    try:
                        # 读取文件内容
                        content_bytes = zf.read(info.filename)
                        content = content_bytes.decode('utf-8', errors='ignore')

                        # 计算行数
                        line_count = content.count('\n') + 1 if content else 0

                        # 创建 ProjectFile
                        project_file = ProjectFile(
                            path=self._normalize_path(filename),
                            content=content,
                            size_bytes=file_size,
                            line_count=line_count
                        )

                        files.append(project_file)
                        total_size += file_size

                    except Exception as e:
                        logger.warning(f"读取文件失败 {filename}: {e}")
                        skipped_files.append(f"{filename} (读取失败)")

            logger.info(f"扫描完成: {len(files)} 个 Python 文件, {len(skipped_files)} 个被跳过")

            return ScanResult(
                success=True,
                files=files,
                skipped_files=skipped_files,
                total_size_bytes=total_size
            )

        except zipfile.BadZipFile as e:
            logger.error(f"ZIP 文件损坏: {e}")
            return ScanResult(
                success=False,
                files=[],
                skipped_files=[],
                error_message=f"ZIP 文件损坏或格式不正确: {str(e)}"
            )
        except Exception as e:
            logger.error(f"扫描过程中发生错误: {e}", exc_info=True)
            return ScanResult(
                success=False,
                files=[],
                skipped_files=[],
                error_message=f"扫描过程中发生错误: {str(e)}"
            )

    def _is_unsafe_path(self, path: str) -> bool:
        """
        检查路径是否安全（防止 Zip Slip 攻击）

        Args:
            path: 文件路径

        Returns:
            bool: 如果路径不安全返回 True
        """
        # 检查绝对路径
        if os.path.isabs(path):
            return True

        # 检查路径遍历
        normalized = os.path.normpath(path)
        if normalized.startswith('..') or normalized.startswith('/'):
            return True

        # 检查路径长度
        if len(path) > MAX_PATH_LENGTH:
            return True

        return False

    def _should_skip_path(self, path: str) -> bool:
        """
        判断是否应该跳过该路径

        Args:
            path: 文件路径

        Returns:
            bool: 如果应该跳过返回 True
        """
        # 统一路径分隔符
        normalized_path = path.replace('\\', '/')

        # 检查是否在跳过目录中
        parts = normalized_path.split('/')
        for part in parts[:-1]:  # 排除文件名本身
            if part in self.skip_dirs:
                return True

        # 检查文件扩展名
        filename = parts[-1] if parts else ''
        for pattern in SKIP_FILE_PATTERNS:
            if filename.endswith(pattern):
                return True

        return False

    def _normalize_path(self, path: str) -> str:
        """
        标准化文件路径

        Args:
            path: 原始路径

        Returns:
            str: 标准化后的路径
        """
        # 统一使用正斜杠
        normalized = path.replace('\\', '/')

        # 移除开头的 ./ 或 /
        while normalized.startswith('./') or normalized.startswith('/'):
            if normalized.startswith('./'):
                normalized = normalized[2:]
            elif normalized.startswith('/'):
                normalized = normalized[1:]

        return normalized

    def scan_directory(self, directory: str) -> ScanResult:
        """
        扫描目录中的 Python 文件

        Args:
            directory: 目录路径

        Returns:
            ScanResult: 扫描结果
        """
        files: List[ProjectFile] = []
        skipped_files: List[str] = []
        total_size = 0

        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                return ScanResult(
                    success=False,
                    files=[],
                    skipped_files=[],
                    error_message=f"目录不存在: {directory}"
                )
            
            if not dir_path.is_dir():
                return ScanResult(
                    success=False,
                    files=[],
                    skipped_files=[],
                    error_message=f"不是目录: {directory}"
                )

            # 遍历目录
            py_files = list(dir_path.rglob('*.py'))
            
            # 检查文件数量
            if len(py_files) > self.max_files:
                return ScanResult(
                    success=False,
                    files=[],
                    skipped_files=[],
                    error_message=f"文件数量超出限制 ({len(py_files)} > {self.max_files})"
                )

            for file_path in py_files:
                # 转换为相对路径
                try:
                    rel_path = file_path.relative_to(dir_path)
                except ValueError:
                    rel_path = file_path
                
                path_str = str(rel_path)
                
                # 跳过特定目录
                if self._should_skip_path(path_str):
                    skipped_files.append(path_str)
                    continue

                # 检查文件大小
                file_size = file_path.stat().st_size
                if file_size > self.max_file_size:
                    skipped_files.append(f"{path_str} (文件过大: {file_size} 字节)")
                    continue

                # 检查总大小
                if total_size + file_size > self.max_total_size:
                    logger.warning(f"总大小超限，停止扫描")
                    break

                try:
                    # 读取文件内容
                    content = file_path.read_text(encoding='utf-8', errors='ignore')

                    # 计算行数
                    line_count = content.count('\n') + 1 if content else 0

                    # 创建 ProjectFile
                    project_file = ProjectFile(
                        path=self._normalize_path(path_str),
                        content=content,
                        size_bytes=file_size,
                        line_count=line_count
                    )

                    files.append(project_file)
                    total_size += file_size

                except Exception as e:
                    logger.warning(f"读取文件失败 {path_str}: {e}")
                    skipped_files.append(f"{path_str} (读取失败)")

            logger.info(f"扫描完成: {len(files)} 个 Python 文件, {len(skipped_files)} 个被跳过")

            return ScanResult(
                success=True,
                files=files,
                skipped_files=skipped_files,
                total_size_bytes=total_size
            )

        except Exception as e:
            logger.error(f"扫描过程中发生错误: {e}", exc_info=True)
            return ScanResult(
                success=False,
                files=[],
                skipped_files=[],
                error_message=f"扫描过程中发生错误: {str(e)}"
            )


def extract_and_scan(zip_bytes: bytes) -> ScanResult:
    """
    便捷函数：解压并扫描 zip 数据中的 Python 文件

    Args:
        zip_bytes: zip 文件的字节数据

    Returns:
        ScanResult: 扫描结果
    """
    scanner = ProjectScanner()
    return scanner.extract_and_scan(zip_bytes)


def scan_directory(directory: str, **kwargs) -> ScanResult:
    """
    便捷函数：扫描目录中的 Python 文件

    Args:
        directory: 目录路径
        **kwargs: 传递给 ProjectScanner 的参数

    Returns:
        ScanResult: 扫描结果
    """
    scanner = ProjectScanner(**kwargs)
    return scanner.scan_directory(directory)
