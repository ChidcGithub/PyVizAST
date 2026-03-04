"""
Project Scanner - Scan project directories and discover Python files
"""
import os
import zipfile
import tempfile
import shutil
import time
import ast
from pathlib import Path
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass

from .models import FileInfo, ProjectScanResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Directories ignored by default
DEFAULT_IGNORE_DIRS = {
    '__pycache__',
    '.git',
    '.svn',
    '.hg',
    'node_modules',
    'venv',
    '.venv',
    'env',
    '.env',
    'dist',
    'build',
    'egg-info',
    '.eggs',
    '.mypy_cache',
    '.pytest_cache',
    '.tox',
    'htmlcov',
    '.idea',
    '.vscode',
}

# File patterns ignored by default
# Note: setup.py is NOT ignored by default as it may contain important project configuration
DEFAULT_IGNORE_PATTERNS = {
    'conftest.py',  # pytest configuration files
}


class ProjectScanner:
    """Project Scanner"""
    
    def __init__(self, ignore_dirs: Optional[Set[str]] = None,
                 ignore_patterns: Optional[Set[str]] = None,
                 max_file_size: int = 5 * 1024 * 1024,  # 5MB
                 max_files: int = 1000):
        """
        Initialize the scanner
        
        Args:
            ignore_dirs: Directory names to ignore
            ignore_patterns: File patterns to ignore
            max_file_size: Maximum file size in bytes
            max_files: Maximum number of files
        """
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
        self.ignore_patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS
        self.max_file_size = max_file_size
        self.max_files = max_files
    
    def scan_zip(self, zip_path: str, project_name: Optional[str] = None) -> Tuple[ProjectScanResult, str]:
        """
        Scan a ZIP archive
        
        Args:
            zip_path: ZIP file path
            project_name: Project name (optional)
        
        Returns:
            (scan result, temporary directory path)
        """
        start_time = time.time()
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='pyvizast_')
        
        try:
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find project root directory
            project_root = self._find_project_root(temp_dir)
            
            if project_name is None:
                project_name = Path(zip_path).stem
            
            # Scan directory
            result = self.scan_directory(project_root, project_name)
            result.scan_time_ms = (time.time() - start_time) * 1000
            
            return result, project_root
            
        except Exception as e:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to extract ZIP file: {str(e)}")
    
    def scan_directory(self, directory: str, project_name: str) -> ProjectScanResult:
        """
        Scan a directory
        
        Args:
            directory: Directory path
            project_name: Project name
        
        Returns:
            Scan result
        """
        start_time = time.time()
        
        directory = Path(directory).resolve()
        file_infos: List[FileInfo] = []
        skipped_files: List[str] = []
        
        for root, dirs, files in os.walk(directory):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith('.')]
            
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(directory)
                
                # Check if file should be ignored
                if self._should_ignore_file(relative_path):
                    skipped_files.append(str(relative_path))
                    continue
                
                # Check file size
                try:
                    file_size = file_path.stat().st_size
                except OSError:
                    continue
                
                if file_size > self.max_file_size:
                    skipped_files.append(str(relative_path))
                    logger.warning(f"File too large, skipping: {relative_path} ({file_size} bytes)")
                    continue
                
                # Check file count limit
                if len(file_infos) >= self.max_files:
                    logger.warning(f"Reached maximum file limit ({self.max_files})")
                    break
                
                # Get file info
                file_info = self._get_file_info(file_path, relative_path)
                file_infos.append(file_info)
        
        # Build result
        result = ProjectScanResult(
            project_name=project_name,
            total_files=len(file_infos),
            total_size=sum(f.size for f in file_infos),
            file_paths=[f.relative_path for f in file_infos],
            file_infos=file_infos,
            skipped_count=len(skipped_files),
            skipped_files=skipped_files,
            scan_time_ms=(time.time() - start_time) * 1000,
        )
        
        logger.info(f"Scan complete: {result.total_files} Python files, "
                   f"{result.skipped_count} skipped")
        
        return result
    
    def _find_project_root(self, directory: str) -> str:
        """
        Find project root directory (containing pyproject.toml, setup.py, requirements.txt, etc.)
        """
        directory = Path(directory)
        
        # Project root marker files
        root_markers = {
            'pyproject.toml',
            'setup.py',
            'setup.cfg',
            'requirements.txt',
            'Pipfile',
            'poetry.lock',
        }
        
        # First check if root directory contains these markers
        for marker in root_markers:
            if (directory / marker).exists():
                return str(directory)
        
        # Check subdirectories
        for item in directory.iterdir():
            if item.is_dir():
                for marker in root_markers:
                    if (item / marker).exists():
                        return str(item)
        
        # If not found, check for src directory
        src_dir = directory / 'src'
        if src_dir.exists() and src_dir.is_dir():
            return str(src_dir)
        
        # Return original directory
        return str(directory)
    
    def _should_ignore_file(self, relative_path: Path) -> bool:
        """Check if file should be ignored"""
        # Check file name patterns
        if relative_path.name in self.ignore_patterns:
            return True
        
        # Check if path contains ignored directories
        for part in relative_path.parts[:-1]:
            if part in self.ignore_dirs:
                return True
        
        return False
    
    def _get_file_info(self, file_path: Path, relative_path: Path) -> FileInfo:
        """Get file information"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            line_count = content.count('\n') + 1
        except Exception:
            line_count = 0
        
        # Check if it's a special file
        name = file_path.name
        is_test = name.startswith('test_') or name.endswith('_test.py')
        is_init = name == '__init__.py'
        is_main = name == '__main__.py'
        
        return FileInfo(
            path=str(file_path),
            relative_path=str(relative_path).replace('\\', '/'),
            size=file_path.stat().st_size,
            line_count=line_count,
            is_test=is_test,
            is_init=is_init,
            is_main=is_main,
        )
    
    @staticmethod
    def count_lines(content: str) -> int:
        """Count code lines (excluding empty lines and comments)"""
        try:
            tree = ast.parse(content)
            # Simple count: total lines - empty lines - pure comment lines
            lines = content.split('\n')
            code_lines = 0
            in_multiline_string = False
            
            for line in lines:
                stripped = line.strip()
                
                # Skip empty lines
                if not stripped:
                    continue
                
                # Skip single-line comments
                if stripped.startswith('#'):
                    continue
                
                code_lines += 1
            
            return code_lines
        except SyntaxError:
            # If parsing fails, return simple line count
            return len([l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')])