"""
Pydantic models for PyVizAST API
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# Constants
MAX_CODE_LENGTH = 5000000  # Maximum code length (characters) - supports large project files (5 million characters)
MAX_FILENAME_LENGTH = 255  # Maximum filename length


class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NodeType(str, Enum):
    """AST node type classification"""
    # Structure nodes
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    
    # Control flow
    IF = "if"
    FOR = "for"
    WHILE = "while"
    TRY = "try"
    WITH = "with"
    
    # Expressions
    CALL = "call"
    BINARY_OP = "binary_op"
    COMPARE = "compare"
    LAMBDA = "lambda"
    
    # Data structures
    LIST = "list"
    DICT = "dict"
    SET = "set"
    TUPLE = "tuple"
    
    # Variables
    ASSIGN = "assign"
    NAME = "name"
    
    # Others
    IMPORT = "import"
    RETURN = "return"
    YIELD = "yield"
    OTHER = "other"


class ASTNode(BaseModel):
    """AST node visualization model"""
    id: str = Field(..., min_length=1, description="Unique node identifier")
    type: NodeType
    name: Optional[str] = Field(None, max_length=500, description="Node name")
    lineno: Optional[int] = Field(None, ge=1, description="Starting line number")
    col_offset: Optional[int] = Field(None, ge=0, description="Starting column offset")
    end_lineno: Optional[int] = Field(None, ge=1, description="Ending line number")
    end_col_offset: Optional[int] = Field(None, ge=0, description="Ending column offset")
    
    # Visualization properties
    color: str = "#4A90D9"
    shape: str = "circle"
    size: int = Field(default=20, ge=1, le=100)
    
    # Icon and description (for learning mode)
    icon: str = "•"
    description: str = ""
    detailed_label: str = ""
    explanation: str = ""
    
    # Children and relationships
    children: List[str] = Field(default_factory=list)
    parent: Optional[str] = None
    
    # Detailed information
    docstring: Optional[str] = None
    source_code: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('end_lineno')
    @classmethod
    def validate_end_lineno(cls, v: Optional[int], info) -> Optional[int]:
        """Validate that end line number is not less than start line number"""
        if v is not None and info.data.get('lineno') is not None:
            if v < info.data['lineno']:
                raise ValueError('End line number cannot be less than start line number')
        return v


class ASTEdge(BaseModel):
    """Edge between AST nodes"""
    id: str
    source: str
    target: str
    edge_type: str  # "parent-child", "call", "import", etc.
    label: Optional[str] = None


class ASTGraph(BaseModel):
    """Complete AST graph structure"""
    nodes: List[ASTNode]
    edges: List[ASTEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeIssue(BaseModel):
    """Code issue"""
    id: str = Field(..., min_length=1, description="Unique issue identifier")
    type: str = Field(..., min_length=1, description="Issue type")
    severity: SeverityLevel
    message: str = Field(..., min_length=1, max_length=2000, description="Issue description")
    lineno: Optional[int] = Field(None, ge=1, description="Starting line number")
    col_offset: Optional[int] = Field(None, ge=0, description="Starting column offset")
    end_lineno: Optional[int] = Field(None, ge=1, description="Ending line number")
    end_col_offset: Optional[int] = Field(None, ge=0, description="Ending column offset")
    node_id: Optional[str] = None
    source_snippet: Optional[str] = Field(None, max_length=5000, description="Source code snippet")
    documentation_url: Optional[str] = Field(None, max_length=500, description="Documentation URL")
    suggestion: Optional[str] = Field(None, max_length=1000, description="Fix suggestion")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate issue type"""
        allowed_types = {'complexity', 'performance', 'code_smell', 'security'}
        if v not in allowed_types:
            raise ValueError(f'Issue type must be one of: {allowed_types}')
        return v


class ComplexityMetrics(BaseModel):
    """Complexity metrics"""
    cyclomatic_complexity: int = Field(default=0, ge=0, description="Cyclomatic complexity")
    cognitive_complexity: int = Field(default=0, ge=0, description="Cognitive complexity")
    lines_of_code: int = Field(default=0, ge=0, description="Lines of code")
    maintainability_index: float = Field(default=0.0, ge=0, le=100, description="Maintainability index")
    halstead_volume: float = Field(default=0.0, ge=0, description="Halstead volume")
    halstead_difficulty: float = Field(default=0.0, ge=0, description="Halstead difficulty")
    
    # Function level
    function_count: int = Field(default=0, ge=0, description="Number of functions")
    class_count: int = Field(default=0, ge=0, description="Number of classes")
    max_nesting_depth: int = Field(default=0, ge=0, description="Maximum nesting depth")
    avg_function_length: float = Field(default=0.0, ge=0, description="Average function length")


class PerformanceHotspot(BaseModel):
    """Performance hotspot"""
    id: str
    node_id: str
    hotspot_type: str  # "nested_loop", "recursion", "inefficient_operation"
    description: str
    estimated_complexity: str  # Big O notation
    lineno: Optional[int] = None
    suggestion: Optional[str] = None


class OptimizationSuggestion(BaseModel):
    """Optimization suggestion"""
    id: str = Field(..., min_length=1, description="Unique suggestion identifier")
    issue_id: Optional[str] = None
    node_id: Optional[str] = None
    category: str = Field(..., min_length=1, description="Suggestion category")
    title: str = Field(..., min_length=1, max_length=200, description="Suggestion title")
    description: str = Field(..., min_length=1, max_length=5000, description="Suggestion description")
    before_code: Optional[str] = Field(None, max_length=MAX_CODE_LENGTH, description="Code before change")
    after_code: Optional[str] = Field(None, max_length=MAX_CODE_LENGTH, description="Code after change")
    estimated_improvement: Optional[str] = Field(None, max_length=100, description="Estimated improvement")
    patch_diff: Optional[str] = Field(None, max_length=MAX_CODE_LENGTH, description="Patch diff")
    auto_fixable: bool = False
    priority: int = Field(default=1, ge=1, le=5, description="Priority (1-5)")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate suggestion category"""
        allowed_categories = {'performance', 'readability', 'security', 'best_practice'}
        if v not in allowed_categories:
            raise ValueError(f'Suggestion category must be one of: {allowed_categories}')
        return v


class AnalysisResult(BaseModel):
    """Complete analysis result"""
    # Basic information
    filename: Optional[str] = None
    total_lines: int = 0
    
    # AST graph
    ast_graph: ASTGraph
    
    # Complexity analysis
    complexity: ComplexityMetrics
    
    # Issue list
    issues: List[CodeIssue] = Field(default_factory=list)
    
    # Performance hotspots
    performance_hotspots: List[PerformanceHotspot] = Field(default_factory=list)
    
    # Optimization suggestions
    suggestions: List[OptimizationSuggestion] = Field(default_factory=list)
    
    # Statistics
    summary: Dict[str, Any] = Field(default_factory=dict)


class CodeInput(BaseModel):
    """Code input model"""
    code: str = Field(..., min_length=1, max_length=MAX_CODE_LENGTH, description="Python code")
    filename: Optional[str] = Field(None, max_length=MAX_FILENAME_LENGTH, description="Filename")
    options: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate code is not empty and has reasonable length"""
        if not v or not v.strip():
            raise ValueError('Code cannot be empty')
        if len(v) > MAX_CODE_LENGTH:
            raise ValueError(f'Code length exceeds limit (max {MAX_CODE_LENGTH} characters)')
        return v
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: Optional[str]) -> Optional[str]:
        """Validate filename format"""
        if v is None:
            return v
        # Strip whitespace
        v = v.strip()
        if not v:
            return None
        # Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', '\x00']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'Filename contains disallowed character: {char}')
        return v


class LearningModeResult(BaseModel):
    """Learning mode result"""
    node_id: str
    explanation: str
    python_doc: Optional[str] = None
    examples: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)


class ChallengeResult(BaseModel):
    """Challenge mode result"""
    challenge_id: str
    score: int
    max_score: int
    found_issues: List[str]
    missed_issues: List[str]
    feedback: str