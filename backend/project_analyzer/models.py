"""
Data models for project-level analysis
Using Pydantic BaseModel consistently for type system consistency
"""
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field, ConfigDict


class FileInfo(BaseModel):
    """File information"""
    model_config = ConfigDict(frozen=False)
    
    path: str
    relative_path: str
    size: int = 0
    line_count: int = 0
    is_test: bool = False
    is_init: bool = False
    is_main: bool = False


class ImportInfo(BaseModel):
    """Import information"""
    model_config = ConfigDict(frozen=False)
    
    module: str
    names: List[str] = Field(default_factory=list)
    alias: Optional[str] = None
    is_relative: bool = False
    level: int = 0  # Relative import level
    lineno: int = 0


class ExportInfo(BaseModel):
    """Export information (function, class, variable)"""
    model_config = ConfigDict(frozen=False)
    
    name: str
    type: str  # 'function', 'class', 'variable', 'constant'
    lineno: int = 0
    is_public: bool = True
    is_used: bool = False
    used_in: List[str] = Field(default_factory=list)  # Use List instead of Set for JSON serialization


class DependencyEdge(BaseModel):
    """Dependency edge"""
    model_config = ConfigDict(frozen=False)
    
    source: str
    target: str
    import_type: str  # 'import', 'from_import', 'relative'
    imported_names: List[str] = Field(default_factory=list)
    lineno: int = 0


class DependencyGraph(BaseModel):
    """Dependency graph model"""
    nodes: List[str] = Field(default_factory=list, description="All module nodes")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Dependency edges")
    adjacency_list: Dict[str, List[str]] = Field(default_factory=dict, description="Adjacency list")


class GlobalIssue(BaseModel):
    """Global issue (cross-file)"""
    issue_type: str = Field(..., description="Issue type")
    severity: str = Field(default="warning", description="Severity level")
    message: str = Field(..., description="Issue description")
    locations: List[Dict[str, Any]] = Field(default_factory=list, description="Related locations")
    suggestion: Optional[str] = Field(None, description="Fix suggestion")


class FileSummary(BaseModel):
    """File analysis summary"""
    issue_count: int = 0
    cyclomatic_complexity: int = 0
    lines_of_code: int = 0
    function_count: int = 0
    class_count: int = 0
    maintainability_index: float = 0.0


class FileAnalysisResult(BaseModel):
    """Single file analysis result"""
    file: FileInfo
    content: str = ""  # File content
    summary: FileSummary = Field(default_factory=FileSummary)
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    complexity: Dict[str, Any] = Field(default_factory=dict)
    performance_hotspots: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)


class ProjectMetrics(BaseModel):
    """Project-level metrics"""
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    avg_complexity: float = 0.0
    avg_maintainability: float = 0.0
    max_complexity_file: Optional[str] = None
    max_complexity_value: int = 0
    dependency_count: int = 0
    circular_dependency_count: int = 0
    unused_export_count: int = 0
    test_coverage_estimate: float = 0.0


class ProjectScanResult(BaseModel):
    """Project scan result"""
    project_name: str
    total_files: int = 0
    total_size: int = 0
    file_paths: List[str] = Field(default_factory=list)
    file_infos: List[FileInfo] = Field(default_factory=list)
    skipped_count: int = 0
    skipped_files: List[str] = Field(default_factory=list)
    scan_time_ms: float = 0.0


class ProjectAnalysisResult(BaseModel):
    """Complete project analysis result"""
    scan_result: ProjectScanResult
    files: List[FileAnalysisResult] = Field(default_factory=list)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    global_issues: List[GlobalIssue] = Field(default_factory=list)
    metrics: ProjectMetrics = Field(default_factory=ProjectMetrics)
    analysis_time_ms: float = 0.0