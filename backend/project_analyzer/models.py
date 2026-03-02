"""
项目级分析数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ProjectFile(BaseModel):
    """项目文件模型"""
    path: str = Field(..., min_length=1, description="文件相对路径")
    content: str = Field(default="", description="文件内容")
    ast: Optional[Dict[str, Any]] = Field(default=None, description="AST 结构（可选，后续填充）")
    size_bytes: int = Field(default=0, ge=0, description="文件大小（字节）")
    line_count: int = Field(default=0, ge=0, description="代码行数")
    analysis: Optional[Dict[str, Any]] = Field(default=None, description="完整分析结果（后续填充）")

    model_config = ConfigDict(str_strip_whitespace=True)


class ScanResult(BaseModel):
    """扫描结果模型"""
    success: bool = Field(default=True, description="是否成功")
    files: List[ProjectFile] = Field(default_factory=list, description="扫描到的文件列表")
    skipped_files: List[str] = Field(default_factory=list, description="被跳过的文件列表")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    total_size_bytes: int = Field(default=0, ge=0, description="总文件大小")


class FileSummary(BaseModel):
    """单个文件的分析摘要"""
    path: str
    line_count: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    function_count: int = 0
    class_count: int = 0
    issue_count: int = 0
    critical_issues: int = 0
    error_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0


class ProjectSummary(BaseModel):
    """项目级摘要"""
    total_files: int = Field(default=0, ge=0, description="总文件数")
    total_lines: int = Field(default=0, ge=0, description="总代码行数")
    total_issues: int = Field(default=0, ge=0, description="总问题数")
    critical_issues: int = Field(default=0, ge=0, description="严重问题数")
    error_issues: int = Field(default=0, ge=0, description="错误数")
    warning_issues: int = Field(default=0, ge=0, description="警告数")
    info_issues: int = Field(default=0, ge=0, description="信息数")
    avg_complexity: float = Field(default=0.0, ge=0, description="平均复杂度")
    avg_maintainability: float = Field(default=0.0, ge=0, le=100, description="平均可维护性指数")
    total_functions: int = Field(default=0, ge=0, description="总函数数")
    total_classes: int = Field(default=0, ge=0, description="总类数")
    file_summaries: List[FileSummary] = Field(default_factory=list, description="各文件摘要")
    
    # 扩展字段
    internal_dependencies: int = Field(default=0, ge=0, description="内部依赖数")
    external_dependencies: int = Field(default=0, ge=0, description="外部依赖数")
    circular_dependencies: int = Field(default=0, ge=0, description="循环依赖数")
    max_cyclomatic_complexity: int = Field(default=0, ge=0, description="最大圈复杂度")
    max_cognitive_complexity: int = Field(default=0, ge=0, description="最大认知复杂度")
    most_complex_files: List[Dict[str, Any]] = Field(default_factory=list, description="最复杂的文件")
    most_issue_files: List[Dict[str, Any]] = Field(default_factory=list, description="问题最多的文件")
    largest_files: List[Dict[str, Any]] = Field(default_factory=list, description="最大的文件")
    health_score: Dict[str, Any] = Field(default_factory=dict, description="健康评分")


class ImportInfo(BaseModel):
    """导入信息"""
    module: str = Field(..., description="导入的模块名")
    alias: Optional[str] = Field(default=None, description="别名")
    items: List[str] = Field(default_factory=list, description="导入的项目（from ... import ...）")
    is_relative: bool = Field(default=False, description="是否相对导入")
    level: int = Field(default=0, ge=0, description="相对导入层级")
    lineno: Optional[int] = Field(default=None, description="行号")


class ExportInfo(BaseModel):
    """导出信息（通过 __all__ 或公开函数/类）"""
    name: str = Field(..., description="导出的名称")
    type: str = Field(..., description="类型：function, class, variable")
    lineno: Optional[int] = Field(default=None, description="行号")


class FileDependency(BaseModel):
    """单个文件的依赖信息"""
    file_path: str = Field(..., description="文件路径")
    imports: List[ImportInfo] = Field(default_factory=list, description="导入列表")
    exports: List[ExportInfo] = Field(default_factory=list, description="导出列表")
    internal_imports: List[str] = Field(default_factory=list, description="内部模块导入（指向项目内其他文件）")
    external_imports: List[str] = Field(default_factory=list, description="外部模块导入")


class ProjectDependencies(BaseModel):
    """项目级依赖信息"""
    internal: List[FileDependency] = Field(default_factory=list, description="内部依赖列表")
    external: List[str] = Field(default_factory=list, description="外部依赖模块列表")
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict, description="依赖图（文件 -> 它依赖的文件）")
    reverse_dependency_graph: Dict[str, List[str]] = Field(default_factory=dict, description="反向依赖图（文件 -> 依赖它的文件）")


class CrossFileIssue(BaseModel):
    """跨文件问题"""
    id: str = Field(..., description="问题唯一标识")
    issue_type: str = Field(..., description="问题类型")
    severity: str = Field(..., description="严重程度")
    message: str = Field(..., description="问题描述")
    involved_files: List[str] = Field(default_factory=list, description="涉及的文件")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")


class GlobalIssue(BaseModel):
    """全局问题（跨文件）"""
    id: str = Field(..., description="问题唯一标识")
    issue_type: str = Field(..., description="问题类型：circular_dependency, unused_export, duplicate_code")
    severity: str = Field(..., description="严重程度：critical, error, warning, info")
    message: str = Field(..., description="问题描述")
    locations: List[Dict[str, Any]] = Field(default_factory=list, description="涉及的位置列表")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")

    @classmethod
    def from_cycle(cls, cycle: List[str], issue_id: int) -> 'GlobalIssue':
        """从循环依赖创建问题"""
        return cls(
            id=f"cycle-{issue_id}",
            issue_type="circular_dependency",
            severity="warning",
            message=f"检测到循环依赖: {' -> '.join(cycle)}",
            locations=[{"file_path": f} for f in cycle],
            details={"cycle": cycle}
        )

    @classmethod
    def from_unused_export(cls, name: str, file_path: str, kind: str, lineno: Optional[int], issue_id: int) -> 'GlobalIssue':
        """从未使用导出创建问题"""
        return cls(
            id=f"unused-export-{issue_id}",
            issue_type="unused_export",
            severity="info",
            message=f"符号 '{name}' 在 {file_path} 中定义但可能未被其他文件使用",
            locations=[{"file_path": file_path, "lineno": lineno, "name": name, "kind": kind}],
            details={"name": name, "kind": kind}
        )

    @classmethod
    def from_duplicate(cls, blocks: List[Dict[str, Any]], issue_id: int) -> 'GlobalIssue':
        """从重复代码创建问题"""
        return cls(
            id=f"duplicate-{issue_id}",
            issue_type="duplicate_code",
            severity="info",
            message=f"发现 {len(blocks)} 个相似的代码块",
            locations=blocks,
            details={"block_count": len(blocks)}
        )


class ProjectFileAnalysis(BaseModel):
    """单个文件的完整分析结果"""
    file: ProjectFile
    summary: FileSummary
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    complexity: Optional[Dict[str, Any]] = Field(default=None)
    performance_hotspots: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = Field(default=None, description="分析错误（如果有）")


class ProjectAnalysisResult(BaseModel):
    """项目级分析结果"""
    project_name: str = Field(default="unknown", description="项目名称")
    files: List[ProjectFileAnalysis] = Field(default_factory=list, description="各文件分析结果")
    summary: ProjectSummary = Field(default_factory=ProjectSummary, description="项目摘要")
    dependencies: Optional[ProjectDependencies] = Field(default=None, description="依赖信息")
    cross_file_issues: List[CrossFileIssue] = Field(default_factory=list, description="跨文件问题")
    global_issues: List[GlobalIssue] = Field(default_factory=list, description="全局问题（循环依赖、未使用导出等）")


class ProcessResult(BaseModel):
    """文件处理结果"""
    files: List[ProjectFileAnalysis] = Field(default_factory=list)
    summary: ProjectSummary = Field(default_factory=ProjectSummary)
    dependencies: Optional[ProjectDependencies] = Field(default=None)
    cross_file_issues: List[CrossFileIssue] = Field(default_factory=list)
    global_issues: List[GlobalIssue] = Field(default_factory=list)
