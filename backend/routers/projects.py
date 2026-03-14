"""
Project analysis API routes

@author: Chidc
@link: github.com/chidcGithub
"""
import ast
import asyncio
import logging
import shutil
import tempfile
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from pydantic import BaseModel

from ..models.schemas import CodeIssue, SeverityLevel
from ..project_analyzer import (
    ProjectScanner,
    DependencyAnalyzer,
    CycleDetector,
    UnusedExportDetector,
    ProjectMetricsAggregator,
    FileAnalysisResult,
    FileInfo,
)
from ..project_analyzer.models import FileSummary
from ..analyzers import ComplexityAnalyzer, PerformanceAnalyzer, CodeSmellDetector, SecurityScanner
from ..utils.progress import progress_tracker, ProgressStage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/project", tags=["projects"])


@dataclass
class ProjectStorageEntry:
    """Project storage entry"""
    scan_result: Any
    project_root: str
    temp_dir: str
    zip_path: str
    file_name: str
    created_at: float
    last_accessed: float


class ProjectStorage:
    """
    Project storage manager
    - Supports maximum entry limit
    - Supports TTL expiration cleanup
    - Thread-safe
    """
    
    def __init__(self, max_entries: int = 50, ttl_seconds: float = 3600):
        self._storage: Dict[str, ProjectStorageEntry] = {}
        self._lock = threading.RLock()
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._cleanup_interval = 300
        self._last_cleanup = time.time()
    
    def _cleanup_expired(self) -> None:
        """Clean up expired entries"""
        now = time.time()
        expired_keys = []
        
        for key, entry in list(self._storage.items()):
            if now - entry.last_accessed > self._ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired project storage entries")
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry and clean up temporary directory"""
        entry = self._storage.pop(key, None)
        if entry:
            try:
                shutil.rmtree(entry.temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")
    
    def _evict_oldest_if_needed(self) -> None:
        """If exceeding max entries, remove oldest entry"""
        if len(self._storage) >= self._max_entries:
            oldest_key = min(
                self._storage.keys(),
                key=lambda k: self._storage[k].last_accessed
            )
            self._remove_entry(oldest_key)
            logger.debug(f"Removed oldest project storage entry: {oldest_key}")
    
    def _maybe_cleanup(self) -> None:
        """Periodic cleanup check"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now
    
    def set(self, project_id: str, entry: ProjectStorageEntry) -> None:
        """Store project entry"""
        with self._lock:
            self._maybe_cleanup()
            self._evict_oldest_if_needed()
            self._storage[project_id] = entry
    
    def get(self, project_id: str) -> Optional[ProjectStorageEntry]:
        """Get project entry and update access time"""
        with self._lock:
            entry = self._storage.get(project_id)
            if entry:
                entry.last_accessed = time.time()
            return entry
    
    def delete(self, project_id: str) -> bool:
        """Delete project entry"""
        with self._lock:
            if project_id in self._storage:
                self._remove_entry(project_id)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries"""
        with self._lock:
            for key in list(self._storage.keys()):
                self._remove_entry(key)
    
    def __len__(self) -> int:
        return len(self._storage)


# Project storage instance
_project_storage = ProjectStorage(max_entries=50, ttl_seconds=3600)


class ProjectUploadResponse(BaseModel):
    """Project upload response"""
    project_id: str
    project_name: str
    total_files: int
    file_paths: List[str]
    skipped_count: int
    message: str = "Project uploaded successfully"


class QuickModeOptions(BaseModel):
    """Quick mode options"""
    quick_mode: bool = False


async def _analyze_single_file(file_info: FileInfo, project_root: str) -> FileAnalysisResult:
    """Analyze single file - async version with non-blocking IO"""
    file_path = Path(file_info.path)
    code_content = ""
    tree = None
    
    # Read file content asynchronously
    def read_file_sync():
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Failed to read file {file_info.relative_path}: {e}")
            return None
    
    code_content = await asyncio.to_thread(read_file_sync)
    if code_content is None:
        return FileAnalysisResult(
            file=file_info,
            content="",
            summary=FileSummary(lines_of_code=file_info.line_count),
            issues=[],
            complexity={},
            performance_hotspots=[],
            suggestions=[],
        )
    
    # Parse AST asynchronously (CPU-bound, run in thread pool)
    def parse_ast_sync():
        try:
            return ast.parse(code_content), None
        except SyntaxError as e:
            return None, ('syntax', e)
        except Exception as e:
            return None, ('other', e)
    
    tree, error = await asyncio.to_thread(parse_ast_sync)
    
    if error:
        if error[0] == 'syntax':
            e = error[1]
            return FileAnalysisResult(
                file=file_info,
                content=code_content,
                summary=FileSummary(
                    lines_of_code=file_info.line_count,
                    issue_count=1,
                ),
                issues=[CodeIssue(
                    id=f'syntax_error_{file_info.relative_path}',
                    type='code_smell',
                    severity=SeverityLevel.ERROR,
                    message=f"Syntax error: {str(e)}",
                    lineno=e.lineno,
                )],
                complexity={},
                performance_hotspots=[],
                suggestions=[],
            )
        else:
            logger.warning(f"Failed to parse AST for {file_info.relative_path}: {error[1]}")
            return FileAnalysisResult(
                file=file_info,
                content=code_content,
                summary=FileSummary(lines_of_code=file_info.line_count),
                issues=[],
                complexity={},
                performance_hotspots=[],
                suggestions=[],
            )
    
    # Run analyzers
    complexity_analyzer = ComplexityAnalyzer()
    performance_analyzer = PerformanceAnalyzer()
    code_smell_detector = CodeSmellDetector()
    security_scanner = SecurityScanner()
    
    complexity = complexity_analyzer.analyze(code_content, tree)
    performance_analyzer.analyze(code_content, tree)
    code_smell_detector.analyze(code_content, tree)
    security_scanner.scan(code_content, tree)
    
    all_issues = (
        complexity_analyzer.get_issues() +
        performance_analyzer.get_issues() +
        code_smell_detector.issues +
        security_scanner.issues
    )
    
    summary = FileSummary(
        issue_count=len(all_issues),
        cyclomatic_complexity=complexity.cyclomatic_complexity,
        lines_of_code=complexity.lines_of_code,
        function_count=complexity.function_count,
        class_count=complexity.class_count,
        maintainability_index=complexity.maintainability_index,
    )
    
    return FileAnalysisResult(
        file=file_info,
        content=code_content,
        summary=summary,
        issues=[issue.model_dump() for issue in all_issues],
        complexity=complexity.model_dump(),
        performance_hotspots=[hs.model_dump() for hs in performance_analyzer.hotspots],
        suggestions=[],
    )


@router.post("/upload", response_model=ProjectUploadResponse)
async def upload_project(file: UploadFile = File(...)):
    """Upload project ZIP file"""
    logger.info(f"Uploading project: {file.filename}")
    
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a .zip format project archive"
        )
    
    temp_dir = tempfile.mkdtemp(prefix='pyvizast_upload_')
    temp_file = Path(temp_dir) / file.filename
    
    try:
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        scanner = ProjectScanner()
        scan_result, project_root = scanner.scan_zip(str(temp_file), Path(file.filename).stem)
        
        project_id = f"proj_{int(time.time() * 1000)}"
        
        now = time.time()
        entry = ProjectStorageEntry(
            scan_result=scan_result,
            project_root=project_root,
            temp_dir=temp_dir,
            zip_path=str(temp_file),
            file_name=file.filename,
            created_at=now,
            last_accessed=now,
        )
        _project_storage.set(project_id, entry)
        
        logger.info(f"Project uploaded successfully: {project_id}, {scan_result.total_files} files, current storage: {len(_project_storage)} projects")
        
        return ProjectUploadResponse(
            project_id=project_id,
            project_name=scan_result.project_name,
            total_files=scan_result.total_files,
            file_paths=scan_result.file_paths,
            skipped_count=scan_result.skipped_count,
        )
    
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error(f"Project upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project upload failed: {str(e)}"
        )


@router.post("/analyze")
async def analyze_project(
    file: UploadFile = File(...),
    quick_mode: bool = Form(False),
    task_id: Optional[str] = Form(None)
):
    """
    Analyze uploaded project
    Receive ZIP file directly and analyze, single step
    Supports optional task_id for progress tracking
    """
    logger.info(f"Analyzing project: {file.filename}, quick mode: {quick_mode}")
    
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a .zip format project archive"
        )
    
    start_time = time.time()
    temp_dir = tempfile.mkdtemp(prefix='pyvizast_analyze_')
    temp_file = Path(temp_dir) / file.filename
    
    if task_id:
        progress_tracker.create_task(task_id, "Initializing project analysis...")
    
    try:
        if task_id:
            progress_tracker.update(task_id, ProgressStage.UPLOADING, 5, "Uploading project files...")
        
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.SCANNING, 10, "Scanning project structure...")
        
        scanner = ProjectScanner()
        scan_result, project_root = scanner.scan_zip(str(temp_file), Path(file.filename).stem)
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.PARSING, 20, f"Found {scan_result.total_files} Python files")
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.DEPENDENCIES, 25, "Analyzing dependencies...")
        logger.debug("Analyzing dependencies...")
        dependency_analyzer = DependencyAnalyzer(project_root)
        module_files = {f.relative_path: f.path for f in scan_result.file_infos}
        dependency_graph = dependency_analyzer.analyze(list(module_files.values()))
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.DEPENDENCIES, 35, "Detecting circular dependencies...")
        logger.debug("Detecting circular dependencies...")
        cycle_detector = CycleDetector(dependency_graph.adjacency_list)
        circular_issues = cycle_detector.detect()
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.DEPENDENCIES, 40, "Detecting unused exports...")
        logger.debug("Detecting unused exports...")
        unused_detector = UnusedExportDetector(dependency_analyzer)
        unused_issues = unused_detector.detect(module_files) if not quick_mode else []
        
        global_issues = circular_issues + unused_issues
        
        file_results: List[FileAnalysisResult] = []
        total_files = len(scan_result.file_infos)
        
        for idx, file_info in enumerate(scan_result.file_infos):
            if quick_mode and file_info.is_test:
                continue
            
            if task_id and total_files > 0:
                file_progress = 40 + (idx + 1) / total_files * 50
                progress_tracker.update(
                    task_id, 
                    ProgressStage.ANALYZING, 
                    file_progress,
                    f"Analyzing {file_info.relative_path}...",
                    {"current_file": file_info.relative_path, "file_index": idx + 1, "total_files": total_files}
                )
            
            try:
                file_result = await _analyze_single_file(file_info, project_root)
                file_results.append(file_result)
            except Exception as e:
                logger.warning(f"Failed to analyze file {file_info.relative_path}: {e}")
                file_results.append(FileAnalysisResult(
                    file=file_info,
                    summary=FileSummary(),
                    issues=[],
                    complexity={},
                    performance_hotspots=[],
                    suggestions=[],
                ))
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.FINALIZING, 95, "Aggregating metrics...")
        metrics_aggregator = ProjectMetricsAggregator()
        metrics = metrics_aggregator.aggregate(file_results, scan_result, global_issues)
        
        analysis_time_ms = (time.time() - start_time) * 1000
        
        dependencies = {
            'dependency_graph': dependency_graph.adjacency_list,
            'nodes': dependency_graph.nodes,
            'edges': [
                {'source': e['source'], 'target': e['target']}
                for e in dependency_graph.edges
            ],
        }
        
        logger.info(f"Project analysis complete: {len(file_results)} files, "
                   f"{len(global_issues)} global issues, "
                   f"took {analysis_time_ms:.2f}ms")
        
        if task_id:
            progress_tracker.complete(task_id, f"Analysis complete! {len(file_results)} files analyzed.")
        
        return {
            'scan_result': scan_result.model_dump(),
            'files': [f.model_dump() for f in file_results],
            'dependencies': dependencies,
            'global_issues': [issue.model_dump() for issue in global_issues],
            'metrics': metrics.model_dump(),
            'analysis_time_ms': analysis_time_ms,
        }
    
    except Exception as e:
        logger.error(f"Project analysis failed: {e}")
        if task_id:
            progress_tracker.error(task_id, f"Analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project analysis failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary directory - always executed, even on exceptions
        try:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as cleanup_error:
            # Log cleanup failure but don't raise - the analysis result is more important
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {cleanup_error}")
