"""
Pydantic models for PyVizAST API
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# 常量定义
MAX_CODE_LENGTH = 100000  # 最大代码长度（字符数）
MAX_FILENAME_LENGTH = 255  # 最大文件名长度


class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NodeType(str, Enum):
    """AST节点类型分类"""
    # 结构节点
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    
    # 控制流
    IF = "if"
    FOR = "for"
    WHILE = "while"
    TRY = "try"
    WITH = "with"
    
    # 表达式
    CALL = "call"
    BINARY_OP = "binary_op"
    COMPARE = "compare"
    LAMBDA = "lambda"
    
    # 数据结构
    LIST = "list"
    DICT = "dict"
    SET = "set"
    TUPLE = "tuple"
    
    # 变量
    ASSIGN = "assign"
    NAME = "name"
    
    # 其他
    IMPORT = "import"
    RETURN = "return"
    YIELD = "yield"
    OTHER = "other"


class ASTNode(BaseModel):
    """AST节点可视化模型"""
    id: str = Field(..., min_length=1, description="节点唯一标识")
    type: NodeType
    name: Optional[str] = Field(None, max_length=500, description="节点名称")
    lineno: Optional[int] = Field(None, ge=1, description="起始行号")
    col_offset: Optional[int] = Field(None, ge=0, description="起始列偏移")
    end_lineno: Optional[int] = Field(None, ge=1, description="结束行号")
    end_col_offset: Optional[int] = Field(None, ge=0, description="结束列偏移")
    
    # 可视化属性
    color: str = "#4A90D9"
    shape: str = "circle"
    size: int = Field(default=20, ge=1, le=100)
    
    # 图标和描述（用于学习模式）
    icon: str = "•"
    description: str = ""
    detailed_label: str = ""
    explanation: str = ""
    
    # 子节点和关系
    children: List[str] = Field(default_factory=list)
    parent: Optional[str] = None
    
    # 详细信息
    docstring: Optional[str] = None
    source_code: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('end_lineno')
    @classmethod
    def validate_end_lineno(cls, v: Optional[int], info) -> Optional[int]:
        """验证结束行号不小于起始行号"""
        if v is not None and info.data.get('lineno') is not None:
            if v < info.data['lineno']:
                raise ValueError('结束行号不能小于起始行号')
        return v


class ASTEdge(BaseModel):
    """AST节点之间的边"""
    id: str
    source: str
    target: str
    edge_type: str  # "parent-child", "call", "import", etc.
    label: Optional[str] = None


class ASTGraph(BaseModel):
    """完整的AST图结构"""
    nodes: List[ASTNode]
    edges: List[ASTEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeIssue(BaseModel):
    """代码问题"""
    id: str = Field(..., min_length=1, description="问题唯一标识")
    type: str = Field(..., min_length=1, description="问题类型")
    severity: SeverityLevel
    message: str = Field(..., min_length=1, max_length=2000, description="问题描述")
    lineno: Optional[int] = Field(None, ge=1, description="起始行号")
    col_offset: Optional[int] = Field(None, ge=0, description="起始列偏移")
    end_lineno: Optional[int] = Field(None, ge=1, description="结束行号")
    end_col_offset: Optional[int] = Field(None, ge=0, description="结束列偏移")
    node_id: Optional[str] = None
    source_snippet: Optional[str] = Field(None, max_length=5000, description="源代码片段")
    documentation_url: Optional[str] = Field(None, max_length=500, description="文档链接")
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证问题类型"""
        allowed_types = {'complexity', 'performance', 'code_smell', 'security'}
        if v not in allowed_types:
            raise ValueError(f'问题类型必须是: {allowed_types}')
        return v


class ComplexityMetrics(BaseModel):
    """复杂度指标"""
    cyclomatic_complexity: int = Field(default=0, ge=0, description="圈复杂度")
    cognitive_complexity: int = Field(default=0, ge=0, description="认知复杂度")
    lines_of_code: int = Field(default=0, ge=0, description="代码行数")
    maintainability_index: float = Field(default=0.0, ge=0, le=100, description="可维护性指数")
    halstead_volume: float = Field(default=0.0, ge=0, description="Halstead 容量")
    halstead_difficulty: float = Field(default=0.0, ge=0, description="Halstead 难度")
    
    # 函数级别
    function_count: int = Field(default=0, ge=0, description="函数数量")
    class_count: int = Field(default=0, ge=0, description="类数量")
    max_nesting_depth: int = Field(default=0, ge=0, description="最大嵌套深度")
    avg_function_length: float = Field(default=0.0, ge=0, description="平均函数长度")


class PerformanceHotspot(BaseModel):
    """性能热点"""
    id: str
    node_id: str
    hotspot_type: str  # "nested_loop", "recursion", "inefficient_operation"
    description: str
    estimated_complexity: str  # Big O notation
    lineno: Optional[int] = None
    suggestion: Optional[str] = None


class OptimizationSuggestion(BaseModel):
    """优化建议"""
    id: str = Field(..., min_length=1, description="建议唯一标识")
    issue_id: Optional[str] = None
    node_id: Optional[str] = None
    category: str = Field(..., min_length=1, description="建议类别")
    title: str = Field(..., min_length=1, max_length=200, description="建议标题")
    description: str = Field(..., min_length=1, max_length=5000, description="建议描述")
    before_code: Optional[str] = Field(None, max_length=MAX_CODE_LENGTH, description="修改前代码")
    after_code: Optional[str] = Field(None, max_length=MAX_CODE_LENGTH, description="修改后代码")
    estimated_improvement: Optional[str] = Field(None, max_length=100, description="预估改进")
    patch_diff: Optional[str] = Field(None, max_length=MAX_CODE_LENGTH, description="补丁差异")
    auto_fixable: bool = False
    priority: int = Field(default=1, ge=1, le=5, description="优先级（1-5）")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """验证建议类别"""
        allowed_categories = {'performance', 'readability', 'security', 'best_practice'}
        if v not in allowed_categories:
            raise ValueError(f'建议类别必须是: {allowed_categories}')
        return v


class AnalysisResult(BaseModel):
    """完整分析结果"""
    # 基本信息
    filename: Optional[str] = None
    total_lines: int = 0
    
    # AST图
    ast_graph: ASTGraph
    
    # 复杂度分析
    complexity: ComplexityMetrics
    
    # 问题列表
    issues: List[CodeIssue] = Field(default_factory=list)
    
    # 性能热点
    performance_hotspots: List[PerformanceHotspot] = Field(default_factory=list)
    
    # 优化建议
    suggestions: List[OptimizationSuggestion] = Field(default_factory=list)
    
    # 统计信息
    summary: Dict[str, Any] = Field(default_factory=dict)


class CodeInput(BaseModel):
    """代码输入模型"""
    code: str = Field(..., min_length=1, max_length=MAX_CODE_LENGTH, description="Python代码")
    filename: Optional[str] = Field(None, max_length=MAX_FILENAME_LENGTH, description="文件名")
    options: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证代码不为空且长度合理"""
        if not v or not v.strip():
            raise ValueError('代码不能为空')
        if len(v) > MAX_CODE_LENGTH:
            raise ValueError(f'代码长度超过限制（最大 {MAX_CODE_LENGTH} 字符）')
        return v
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: Optional[str]) -> Optional[str]:
        """验证文件名格式"""
        if v is None:
            return v
        # 移除前后空白
        v = v.strip()
        if not v:
            return None
        # 检查危险字符
        dangerous_chars = ['..', '/', '\\', '\x00']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'文件名包含不允许的字符: {char}')
        return v


class LearningModeResult(BaseModel):
    """学习模式结果"""
    node_id: str
    explanation: str
    python_doc: Optional[str] = None
    examples: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)


class ChallengeResult(BaseModel):
    """挑战模式结果"""
    challenge_id: str
    score: int
    max_score: int
    found_issues: List[str]
    missed_issues: List[str]
    feedback: str
