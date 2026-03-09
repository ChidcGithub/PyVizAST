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
    MATCH = "match"  # Python 3.10+ match-case statement
    
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
    UNKNOWN = "unknown"


class VariableInfo(BaseModel):
    """Variable definition/usage information"""
    name: str
    lineno: Optional[int] = None
    col_offset: Optional[int] = None
    is_definition: bool = False
    is_usage: bool = False
    scope: Optional[str] = None  # Function/class where defined


class CodeRelationship(BaseModel):
    """Code relationship between nodes"""
    source_id: str
    target_id: str
    relationship_type: str  # "inheritance", "call", "decorator", "variable_use", "import"
    details: Optional[str] = None


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
    
    # Extended information for detailed view
    # Code metrics
    line_count: int = Field(default=0, ge=0, description="Number of lines in this node")
    char_count: int = Field(default=0, ge=0, description="Number of characters")
    indent_level: int = Field(default=0, ge=0, description="Indentation level")
    
    # Structure info
    child_count: int = Field(default=0, ge=0, description="Number of direct children")
    total_descendants: int = Field(default=0, ge=0, description="Total number of descendants")
    depth: int = Field(default=0, ge=0, description="Depth in the tree")
    scope_name: Optional[str] = Field(None, description="Name of enclosing scope")
    
    # Type annotations (for functions)
    return_type: Optional[str] = Field(None, description="Return type annotation")
    parameter_types: Dict[str, str] = Field(default_factory=dict, description="Parameter type annotations")
    default_values: Dict[str, str] = Field(default_factory=dict, description="Default parameter values")
    
    # Function/Class specific
    method_count: int = Field(default=0, ge=0, description="Number of methods (for classes)")
    attribute_count: int = Field(default=0, ge=0, description="Number of attributes (for classes)")
    local_var_count: int = Field(default=0, ge=0, description="Number of local variables (for functions)")
    
    # Code patterns
    has_try_except: bool = Field(default=False, description="Contains try-except block")
    has_loop: bool = Field(default=False, description="Contains loop")
    has_recursion: bool = Field(default=False, description="May have recursion")
    is_generator: bool = Field(default=False, description="Is a generator function")
    is_async: bool = Field(default=False, description="Is async function/method")
    
    # Dependencies
    imports_used: List[str] = Field(default_factory=list, description="Imports used in this scope")
    functions_called: List[str] = Field(default_factory=list, description="Functions called in this scope")
    is_called_count: int = Field(default=0, ge=0, description="Number of times this function is called")
    
    # ===== NEW: Enhanced Code Relationship Fields =====
    
    # Class inheritance relationships
    base_classes: List[str] = Field(default_factory=list, description="Base class names (for classes)")
    derived_classes: List[str] = Field(default_factory=list, description="Derived class names")
    inheritance_depth: int = Field(default=0, ge=0, description="Depth in inheritance hierarchy")
    
    # Method relationships (for classes)
    methods: List[str] = Field(default_factory=list, description="Method names defined in this class")
    inherited_methods: List[str] = Field(default_factory=list, description="Methods inherited from base classes")
    overridden_methods: List[str] = Field(default_factory=list, description="Methods that override base class methods")
    
    # Variable tracking
    variables_defined: List[VariableInfo] = Field(default_factory=list, description="Variables defined in this scope")
    variables_used: List[VariableInfo] = Field(default_factory=list, description="Variables used from outer scopes")
    global_variables: List[str] = Field(default_factory=list, description="Global variables used")
    nonlocal_variables: List[str] = Field(default_factory=list, description="Nonlocal variables used")
    
    # Decorator relationships
    decorators: List[str] = Field(default_factory=list, description="Decorator names applied to this node")
    decorated_by: List[str] = Field(default_factory=list, description="Node IDs of decorators")
    decorates: List[str] = Field(default_factory=list, description="Functions/classes this decorator decorates")
    
    # Call graph enhancement
    calls_to: List[str] = Field(default_factory=list, description="Node IDs of functions this calls")
    called_by: List[str] = Field(default_factory=list, description="Node IDs of functions that call this")
    method_calls: List[str] = Field(default_factory=list, description="Method calls (obj.method format)")
    
    # Scope nesting
    nested_scopes: List[str] = Field(default_factory=list, description="IDs of nested functions/classes")
    enclosing_scope_id: Optional[str] = Field(None, description="ID of enclosing function/class")
    scope_level: int = Field(default=0, ge=0, description="Nesting level of scope")
    
    # Import details
    imported_symbols: Dict[str, str] = Field(default_factory=dict, description="Symbol -> module mapping")
    import_aliases: Dict[str, str] = Field(default_factory=dict, description="Alias -> original name")
    
    # Data flow hints
    assigned_from: List[str] = Field(default_factory=list, description="Node IDs this variable is assigned from")
    used_in: List[str] = Field(default_factory=list, description="Node IDs where this variable is used")
    
    # Complexity details
    branch_count: int = Field(default=0, ge=0, description="Number of branches (if/elif/else)")
    loop_count: int = Field(default=0, ge=0, description="Number of loops")
    exception_handlers: int = Field(default=0, ge=0, description="Number of except blocks")
    
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
    edge_type: str  # "parent-child", "call", "import", "inheritance", "decorator", etc.
    label: Optional[str] = None


class ASTGraph(BaseModel):
    """Complete AST graph structure"""
    nodes: List[ASTNode]
    edges: List[ASTEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # NEW: Code relationships summary
    relationships: List[CodeRelationship] = Field(default_factory=list, description="Code relationships")


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
        """Validate issue type - allows known types and logs warnings for unknown types"""
        known_types = {'complexity', 'performance', 'code_smell', 'security', 'style', 'formatting', 'type_check', 'lint'}
        if v not in known_types:
            # Allow unknown types but could log a warning in production
            # For now, just normalize the type
            import logging
            logging.getLogger(__name__).debug(f"Unknown issue type: {v}, consider adding to known_types")
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
    
    # NEW: Enhanced metrics
    inheritance_depth: int = Field(default=0, ge=0, description="Maximum inheritance depth")
    total_inheritance_chains: int = Field(default=0, ge=0, description="Total inheritance chains")
    total_function_calls: int = Field(default=0, ge=0, description="Total function calls")
    total_method_calls: int = Field(default=0, ge=0, description="Total method calls")
    decorator_count: int = Field(default=0, ge=0, description="Total decorators used")
    global_variable_count: int = Field(default=0, ge=0, description="Global variables used")


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
    passed: bool = False
