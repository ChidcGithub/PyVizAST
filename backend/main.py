"""
PyVizAST - FastAPI Backend
AST-based Python Code Visualizer and Optimization Analyzer
"""
import ast
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from .models.schemas import (
    CodeInput, AnalysisResult, ASTGraph,
    ComplexityMetrics, CodeIssue, SeverityLevel,
    PerformanceHotspot, OptimizationSuggestion,
    LearningModeResult, ChallengeResult
)
from .ast_parser import ASTParser, NodeMapper
from .analyzers import ComplexityAnalyzer, PerformanceAnalyzer, CodeSmellDetector, SecurityScanner
from .optimizers import SuggestionEngine, PatchGenerator
from .utils.logger import get_logger, log_exception, init_logging
from .project_analyzer import (
    ProjectScanner,
    DependencyAnalyzer,
    CycleDetector,
    SymbolExtractor,
    UnusedExportDetector,
    ProjectMetricsAggregator,
    ProjectScanResult,
    ProjectAnalysisResult,
    FileAnalysisResult,
    FileSummary,
    FileInfo,
)


# Custom exception classes
class AnalysisError(Exception):
    """Error during analysis"""
    pass


class CodeParsingError(AnalysisError):
    """Code parsing error"""
    pass


class CodeTooLargeError(AnalysisError):
    """Code too large error"""
    pass


class ResourceNotFoundError(Exception):
    """Resource not found error"""
    pass


# Initialize logging system
logger = init_logging(level=logging.INFO)


# Create FastAPI application
app = FastAPI(
    title="PyVizAST API",
    description="Python AST Visualization and Static Analysis API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
import os
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Read allowed origins from environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Global exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Input validation failed: {exc}"}
    )


@app.exception_handler(CodeParsingError)
async def code_parsing_exception_handler(request: Request, exc: CodeParsingError):
    """Handle code parsing errors"""
    logger.warning(f"Code parsing error: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(CodeTooLargeError)
async def code_too_large_exception_handler(request: Request, exc: CodeTooLargeError):
    """Handle code too large errors"""
    logger.warning(f"Code too large: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"detail": str(exc)}
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
    """Handle resource not found errors"""
    logger.warning(f"Resource not found: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@app.exception_handler(AnalysisError)
async def analysis_exception_handler(request: Request, exc: AnalysisError):
    """Handle errors during analysis"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Error during analysis: {str(exc)}"}
    )


@app.exception_handler(OSError)
async def os_exception_handler(request: Request, exc: OSError):
    """Handle OS errors (e.g., file operations)"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error, please try again later"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    log_exception(logger, exc, f"Request path: {request.url.path}")
    # Don't return detailed error info in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Local model definitions
class PatchApplyRequest(BaseModel):
    """Patch apply request model"""
    code: str
    patch: str


class AnalyzerFactory:
    """Analyzer factory - creates new instances per request to avoid state pollution"""
    
    @staticmethod
    def create_complexity_analyzer() -> ComplexityAnalyzer:
        return ComplexityAnalyzer()
    
    @staticmethod
    def create_performance_analyzer() -> PerformanceAnalyzer:
        return PerformanceAnalyzer()
    
    @staticmethod
    def create_code_smell_detector() -> CodeSmellDetector:
        return CodeSmellDetector()
    
    @staticmethod
    def create_security_scanner() -> SecurityScanner:
        return SecurityScanner()
    
    @staticmethod
    def create_suggestion_engine() -> SuggestionEngine:
        return SuggestionEngine()
    
    @staticmethod
    def create_patch_generator() -> PatchGenerator:
        return PatchGenerator()
    
    @staticmethod
    def create_node_mapper(theme: str = "default") -> NodeMapper:
        return NodeMapper(theme=theme)


def get_parser(options: dict = None) -> ASTParser:
    """Get configured parser instance"""
    options = options or {}
    max_nodes = options.get('max_nodes', 2000)
    simplified = options.get('simplified', False)
    
    return ASTParser(max_nodes=max_nodes, simplified=simplified)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "PyVizAST API",
        "version": "0.1.0",
        "description": "Python AST Visualizer and Static Analyzer",
        "status": "running",
        "endpoints": {
            "analyze": "/api/analyze",
            "ast": "/api/ast",
            "complexity": "/api/complexity",
            "performance": "/api/performance",
            "security": "/api/security",
            "suggestions": "/api/suggestions",
            "docs": "/docs"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "PyVizAST API"}


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_code(input_data: CodeInput):
    """
    Complete code analysis
    Parse AST, analyze complexity, detect issues, generate optimization suggestions
    """
    logger.info(f"Starting code analysis, filename: {input_data.filename or 'unspecified'}")
    
    try:
        code = input_data.code
        filename = input_data.filename
        options = input_data.options or {}
        
        # Detect code size, automatically enable simplified mode
        code_lines = len(code.splitlines())
        auto_simplified = code_lines > 500
        logger.debug(f"Code lines: {code_lines}, simplified mode: {auto_simplified}")
        
        # Parse AST - use progressive strategy for large files
        tree = None
        simplification_level = 0  # 0=normal, 1=simplified, 2=aggressive simplification
        
        while tree is None and simplification_level <= 2:
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                # Syntax errors should be raised immediately, no retry needed
                raise CodeParsingError(f"Syntax error: {str(e)}")
            except MemoryError:
                simplification_level += 1
                if simplification_level == 1:
                    # First memory error: try simplified mode
                    logger.warning(f"Code too large ({code_lines} lines), trying simplified mode...")
                    auto_simplified = True
                    import gc
                    gc.collect()  # Force garbage collection
                elif simplification_level == 2:
                    # Second memory error: try aggressive simplification
                    logger.warning("Simplified mode insufficient, trying aggressive simplification...")
                    # Try to parse only code structure (remove function body content)
                    try:
                        # Keep only code structure framework
                        lines = code.splitlines()
                        if len(lines) > 2000:
                            # For very large files, only analyze first 2000 lines
                            code = '\n'.join(lines[:2000])
                            code_lines = 2000
                            tree = ast.parse(code)
                            logger.info(f"Truncated to first 2000 lines for analysis")
                            break
                    except SyntaxError as e:
                        # Truncated code may have syntax errors, raise directly
                        raise CodeParsingError(f"Syntax error: {str(e)}")
                    except MemoryError:
                        pass
                    import gc
                    gc.collect()
                else:
                    # Final failure
                    raise CodeTooLargeError(
                        f"Code too large ({code_lines} lines), cannot parse. "
                        f"Suggestions: 1) Split code into multiple files; "
                        f"2) Use a more powerful machine; "
                        f"3) Analyze only part of the code."
                    )
        
        parser = get_parser({'simplified': auto_simplified, **options})
        ast_graph = parser.parse(code)
        
        # Create new analyzer instances
        theme = options.get('theme', 'default')
        node_mapper = AnalyzerFactory.create_node_mapper(theme)
        complexity_analyzer = AnalyzerFactory.create_complexity_analyzer()
        performance_analyzer = AnalyzerFactory.create_performance_analyzer()
        code_smell_detector = AnalyzerFactory.create_code_smell_detector()
        security_scanner = AnalyzerFactory.create_security_scanner()
        suggestion_engine = AnalyzerFactory.create_suggestion_engine()
        
        # Apply theme
        ast_graph = node_mapper.apply_theme_to_graph(ast_graph)
        ast_graph = node_mapper.calculate_node_sizes(ast_graph)
        
        # Complexity analysis
        complexity = complexity_analyzer.analyze(code, tree)
        
        # Performance analysis
        performance_analyzer.analyze(code, tree)
        performance_hotspots = performance_analyzer.hotspots
        
        # Code smell detection
        code_smell_detector.analyze(code, tree)
        
        # Security scan
        security_scanner.scan(code, tree)
        
        # Merge all issues
        all_issues = (
            complexity_analyzer.get_issues() +
            performance_analyzer.get_issues() +
            code_smell_detector.issues +
            security_scanner.issues
        )
        
        # Generate optimization suggestions
        suggestions = suggestion_engine.generate_suggestions(code, tree, all_issues)
        
        # Generate statistics summary
        summary = {
            "total_issues": len(all_issues),
            "critical_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.CRITICAL),
            "error_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.ERROR),
            "warning_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.WARNING),
            "info_issues": sum(1 for i in all_issues if i.severity == SeverityLevel.INFO),
            "performance_hotspots": len(performance_hotspots),
            "suggestions_count": len(suggestions),
            "security_summary": security_scanner.get_security_summary(),
            "node_statistics": node_mapper.get_statistics(ast_graph)
        }
        
        logger.info(f"Analysis complete, found {len(all_issues)} issues")
        
        return AnalysisResult(
            filename=filename,
            total_lines=len(code.splitlines()),
            ast_graph=ast_graph,
            complexity=complexity,
            issues=all_issues,
            performance_hotspots=performance_hotspots,
            suggestions=suggestions,
            summary=summary
        )
    
    except (CodeParsingError, CodeTooLargeError):
        # Re-raise known exceptions, let global handler process
        raise
    except RecursionError:
        logger.error("Recursion depth exceeded")
        raise AnalysisError("Code structure too complex to analyze")
    except MemoryError:
        logger.error("Out of memory")
        raise CodeTooLargeError("Code too large, out of memory")


@app.post("/api/ast")
async def get_ast(input_data: CodeInput):
    """
    Get AST graph structure
    For visualization
    """
    logger.debug(f"Getting AST graph structure")
    
    try:
        code = input_data.code
        options = input_data.options or {}
        
        # Auto-simplify large files
        code_lines = len(code.splitlines())
        auto_simplified = code_lines > 500 or options.get('simplified', False)
        
        # Parse AST
        try:
            parser = get_parser({'simplified': auto_simplified, **options})
            ast_graph = parser.parse(code)
        except SyntaxError as e:
            raise CodeParsingError(f"Syntax error: {str(e)}")
        except MemoryError:
            raise CodeTooLargeError("Code too large to parse")
        
        # Apply theme and layout
        theme = options.get('theme', 'default')
        format_type = options.get('format', 'cytoscape')
        
        node_mapper = AnalyzerFactory.create_node_mapper(theme)
        ast_graph = node_mapper.apply_theme_to_graph(ast_graph)
        ast_graph = node_mapper.calculate_node_sizes(ast_graph)
        
        # Convert format
        if format_type == 'cytoscape':
            return node_mapper.to_cytoscape_elements(ast_graph)
        elif format_type == 'd3':
            return node_mapper.to_d3_format(ast_graph)
        elif format_type == 'tree':
            return node_mapper.to_hierarchical_tree(ast_graph)
        else:
            return ast_graph
    
    except (CodeParsingError, CodeTooLargeError):
        raise


@app.post("/api/ast/filter")
async def filter_ast(input_data: CodeInput, node_types: Optional[str] = None, max_depth: Optional[int] = None):
    """
    Filter AST nodes
    """
    logger.debug(f"Filtering AST nodes, types: {node_types}, max depth: {max_depth}")
    
    try:
        from .models.schemas import NodeType
        
        code = input_data.code
        options = input_data.options or {}
        
        parser = get_parser(options)
        ast_graph = parser.parse(code)
        
        node_mapper = AnalyzerFactory.create_node_mapper()
        
        # Filter by type
        if node_types:
            try:
                types = [NodeType[t.strip().upper()] for t in node_types.split(',')]
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid node type: {e}"
                )
            ast_graph = node_mapper.filter_by_type(ast_graph, types)
        
        # Filter by depth
        if max_depth:
            if max_depth < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Max depth must be greater than 0"
                )
            ast_graph = node_mapper.filter_by_depth(ast_graph, max_depth)
        
        return node_mapper.to_cytoscape_elements(ast_graph)
    
    except HTTPException:
        raise
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@app.post("/api/complexity", response_model=ComplexityMetrics)
async def get_complexity(input_data: CodeInput):
    """
    Get complexity analysis results
    """
    logger.debug("Getting complexity analysis")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        analyzer = AnalyzerFactory.create_complexity_analyzer()
        return analyzer.analyze(code, tree)
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@app.post("/api/performance")
async def get_performance_issues(input_data: CodeInput):
    """
    Get performance hotspot analysis
    """
    logger.debug("Getting performance hotspot analysis")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        analyzer = AnalyzerFactory.create_performance_analyzer()
        hotspots = analyzer.analyze(code, tree)
        issues = analyzer.get_issues()
        
        return {
            "hotspots": hotspots,
            "issues": issues
        }
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@app.post("/api/security")
async def get_security_issues(input_data: CodeInput):
    """
    Get security scan results
    """
    logger.debug("Getting security scan results")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        scanner = AnalyzerFactory.create_security_scanner()
        scanner.scan(code, tree)
        summary = scanner.get_security_summary()
        
        return {
            "issues": scanner.issues,
            "summary": summary
        }
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@app.post("/api/suggestions")
async def get_suggestions(input_data: CodeInput):
    """
    Get optimization suggestions
    """
    logger.debug("Getting optimization suggestions")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        
        # Create new analyzer instances
        complexity_analyzer = AnalyzerFactory.create_complexity_analyzer()
        performance_analyzer = AnalyzerFactory.create_performance_analyzer()
        code_smell_detector = AnalyzerFactory.create_code_smell_detector()
        security_scanner = AnalyzerFactory.create_security_scanner()
        suggestion_engine = AnalyzerFactory.create_suggestion_engine()
        
        # Run complete analysis to get issues
        complexity_analyzer.analyze(code, tree)
        performance_analyzer.analyze(code, tree)
        code_smell_detector.analyze(code, tree)
        security_scanner.scan(code, tree)
        
        all_issues = (
            complexity_analyzer.get_issues() +
            performance_analyzer.get_issues() +
            code_smell_detector.issues +
            security_scanner.issues
        )
        
        suggestions = suggestion_engine.generate_suggestions(code, tree, all_issues)
        by_category = suggestion_engine.get_suggestions_by_category()
        
        return {
            "suggestions": suggestions,
            "by_category": by_category,
            "high_priority": suggestion_engine.get_high_priority_suggestions()
        }
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@app.post("/api/patches")
async def generate_patches(input_data: CodeInput):
    """
    Generate auto-fix patches
    """
    logger.debug("Generating auto-fix patches")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        
        # Create new instances
        suggestion_engine = AnalyzerFactory.create_suggestion_engine()
        patch_generator = AnalyzerFactory.create_patch_generator()
        
        # Get suggestions
        suggestions = suggestion_engine.generate_suggestions(code, tree)
        patches = patch_generator.generate_all_patches(code, suggestions)
        
        return {
            "patches": patches,
            "total": len(patches)
        }
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@app.post("/api/apply-patch")
async def apply_patch(request: PatchApplyRequest):
    """
    Apply patch to code
    """
    logger.debug("Applying patch to code")
    
    try:
        patch_generator = AnalyzerFactory.create_patch_generator()
        result = patch_generator.apply_patch(request.code, request.patch)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patch application failed, invalid format or doesn't match code"
            )
        return {"fixed_code": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patch format error: {str(e)}"
        )


# Interactive learning mode endpoints
@app.post("/api/learn/node/{node_id}")
async def explain_node(node_id: str, input_data: CodeInput):
    """
    Explain AST node (learning mode)
    """
    logger.debug(f"Explaining AST node: {node_id}")
    
    try:
        code = input_data.code
        options = input_data.options or {}
        
        parser = get_parser(options)
        ast_graph = parser.parse(code)
        
        # Find node
        node = None
        for n in ast_graph.nodes:
            if n.id == node_id:
                node = n
                break
        
        if not node:
            raise ResourceNotFoundError(f"Node not found: {node_id}")
        
        # Generate explanation
        explanation = _generate_node_explanation(node)
        
        return LearningModeResult(
            node_id=node_id,
            explanation=explanation['explanation'],
            python_doc=explanation.get('doc'),
            examples=explanation.get('examples', []),
            related_concepts=explanation.get('related', [])
        )
    
    except (ResourceNotFoundError, CodeParsingError):
        raise
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


# Challenge data loader
def load_challenges() -> List[Dict[str, Any]]:
    """Load challenge data from JSON file"""
    challenges_path = Path(__file__).parent / "data" / "challenges.json"
    try:
        with open(challenges_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("challenges", [])
    except FileNotFoundError:
        logger.warning(f"Challenge data file not found: {challenges_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Challenge data JSON parse error: {e}")
        return []


def get_challenges_cache() -> List[Dict[str, Any]]:
    """Get challenge data (with cache)"""
    if not hasattr(get_challenges_cache, '_cache'):
        get_challenges_cache._cache = load_challenges()
    return get_challenges_cache._cache


@app.get("/api/challenges")
async def get_challenges():
    """Get challenge list"""
    logger.debug("Getting challenge list")
    challenges = get_challenges_cache()
    return [
        {
            "id": c["id"], 
            "title": c["title"], 
            "difficulty": c["difficulty"],
            "estimated_time_minutes": c.get("estimated_time_minutes")
        } 
        for c in challenges
    ]


@app.get("/api/challenges/{challenge_id}")
async def get_challenge(challenge_id: str):
    """Get challenge details"""
    logger.debug(f"Getting challenge details: {challenge_id}")
    challenges = get_challenges_cache()
    for challenge in challenges:
        if challenge["id"] == challenge_id:
            return {
                "id": challenge["id"],
                "title": challenge["title"],
                "description": challenge["description"],
                "code": challenge["code"],
                "difficulty": challenge["difficulty"],
                "hints": challenge.get("hints", [])
            }
    raise ResourceNotFoundError(f"Challenge not found: {challenge_id}")


class ChallengeSubmission(BaseModel):
    challenge_id: str
    found_issues: List[str]


@app.post("/api/challenges/submit")
async def submit_challenge(submission: ChallengeSubmission):
    """Submit challenge answer"""
    logger.debug(f"Submitting challenge answer: {submission.challenge_id}")
    challenges = get_challenges_cache()
    for challenge in challenges:
        if challenge["id"] == submission.challenge_id:
            expected = set(challenge["issues"])
            found = set(submission.found_issues)
            
            correct = found & expected
            missed = expected - found
            wrong = found - expected
            
            score = len(correct) * 10 - len(wrong) * 5
            max_score = len(expected) * 10
            
            return ChallengeResult(
                challenge_id=submission.challenge_id,
                score=max(0, score),
                max_score=max_score,
                found_issues=list(correct),
                missed_issues=list(missed),
                feedback=_generate_challenge_feedback(correct, missed, wrong)
            )
    
    raise ResourceNotFoundError(f"Challenge not found: {submission.challenge_id}")


def _generate_node_explanation(node) -> Dict[str, Any]:
    """Generate node explanation"""
    node_name = node.name or "unnamed"
    
    explanations = {
        "function": {
            "explanation": f"This is a function definition node. Function name is '{node_name}', "
                          f"it contains {len(node.children)} child nodes.",
            "doc": "In Python, functions are code blocks defined using the def keyword, "
                   "which can receive parameters and return values. Functions help with code reuse and modularization.",
            "examples": [
                "def greet(name):\n    return f'Hello, {name}!'",
                "def add(a, b=0):\n    return a + b"
            ],
            "related": ["parameters", "return statement", "decorators"]
        },
        "class": {
            "explanation": f"This is a class definition node. Class name is '{node_name}'.",
            "doc": "Classes are blueprints for objects, containing attributes and methods. "
                   "Python supports object-oriented programming, including inheritance, encapsulation, and polymorphism.",
            "examples": [
                "class Dog:\n    def __init__(self, name):\n        self.name = name",
                "class Cat(Animal):\n    def speak(self):\n        print('Meow')"
            ],
            "related": ["inheritance", "methods", "attributes", "__init__"]
        },
        "for": {
            "explanation": "This is a for loop node, used to iterate over iterable objects.",
            "doc": "For loops are the most common iteration structure in Python, "
                   "can iterate over lists, tuples, dictionaries, strings, and other iterable objects.",
            "examples": [
                "for i in range(10):\n    print(i)",
                "for item in my_list:\n    process(item)"
            ],
            "related": ["while loop", "range()", "iterators", "enumerate()"]
        },
        "if": {
            "explanation": "This is an if conditional node, used to execute different code based on conditions.",
            "doc": "If statements decide which branch to execute based on the truth value of the condition expression. "
                   "Can be used with elif and else.",
            "examples": [
                "if x > 0:\n    print('positive')\nelse:\n    print('non-positive')",
                "if x > 10 and y > 10:\n    return 'large'"
            ],
            "related": ["elif", "else", "conditional expressions", "boolean logic"]
        },
        "call": {
            "explanation": f"This is a function call node, calling '{node_name}' function.",
            "doc": "Function calls execute the code in the function definition, can pass arguments and receive return values.",
            "examples": [
                "result = len(my_list)",
                "greeting = greet('World')"
            ],
            "related": ["arguments", "parameters", "return value", "built-in functions"]
        },
        "assign": {
            "explanation": "This is an assignment node, binding a value to a variable name.",
            "doc": "Assignment operations bind the right-hand value to the left-hand variable name. "
                   "Python supports multiple assignment and unpacking assignment.",
            "examples": [
                "x = 10",
                "a, b = 1, 2",
                "x = y = z = 0"
            ],
            "related": ["variables", "names", "binding", "augmented assignment"]
        }
    }
    
    return explanations.get(node.type.value, {
        "explanation": f"This is an AST node of type {node.type.value}.",
        "doc": None,
        "examples": [],
        "related": []
    })


def _generate_challenge_feedback(correct, missed, wrong):
    """Generate challenge feedback"""
    feedback = []
    
    if correct:
        feedback.append(f"Great job! You correctly identified: {', '.join(correct)}")
    
    if missed:
        feedback.append(f"You missed: {', '.join(missed)}")
    
    if wrong:
        feedback.append(f"Incorrectly identified: {', '.join(wrong)}")
    
    return " ".join(feedback) if feedback else "Keep trying!"


# Frontend log receiving endpoint

class FrontendLogEntry(BaseModel):
    """Frontend log entry model"""
    timestamp: str
    level: str
    message: str
    userAgent: Optional[str] = None
    url: Optional[str] = None
    reason: Optional[str] = None
    stack: Optional[str] = None
    componentStack: Optional[str] = None
    filename: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None


class FrontendLogsRequest(BaseModel):
    """Frontend logs request model"""
    logs: List[FrontendLogEntry]


# Ensure log directory exists
LOGS_DIR = Path(__file__).parent.parent / "logs"


def ensure_logs_dir():
    """Ensure log directory exists"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/logs/frontend")
async def receive_frontend_logs(request: FrontendLogsRequest):
    """
    Receive frontend logs and save to file
    """
    ensure_logs_dir()
    
    # Generate log filename (by date)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"frontend-{today}.log"
    
    # Append logs
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            for log_entry in request.logs:
                # Format log entry
                log_line = (
                    f"[{log_entry.timestamp}] "
                    f"[{log_entry.level.upper()}] "
                    f"{log_entry.message}"
                )
                
                # Add extra info
                extras = []
                if log_entry.url:
                    extras.append(f"url={log_entry.url}")
                if log_entry.filename:
                    extras.append(f"file={log_entry.filename}:{log_entry.lineno}:{log_entry.colno}")
                if log_entry.stack:
                    extras.append(f"stack={log_entry.stack[:500]}")  # Limit stack length
                if log_entry.componentStack:
                    extras.append(f"componentStack={log_entry.componentStack[:500]}")
                
                if extras:
                    log_line += f" | {' | '.join(extras)}"
                
                f.write(log_line + "\n")
        
        logger.debug(f"Saved {len(request.logs)} frontend log entries")
        return {"status": "ok", "count": len(request.logs)}
    
    except Exception as e:
        logger.error(f"Failed to save frontend logs: {e}")
        return {"status": "error", "message": str(e)}


# ============== Project-level Analysis Endpoints ==============

import tempfile
import shutil
import time
import threading
from fastapi import UploadFile, File, Form
from dataclasses import dataclass
from typing import Optional


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
        """
        Initialize project storage
        
        Args:
            max_entries: Maximum number of entries to store
            ttl_seconds: Entry expiration time (seconds)
        """
        self._storage: Dict[str, ProjectStorageEntry] = {}
        self._lock = threading.RLock()
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._cleanup_interval = 300  # Cleanup interval (seconds)
        self._last_cleanup = time.time()
    
    def _cleanup_expired(self) -> None:
        """Clean up expired entries"""
        now = time.time()
        expired_keys = []
        
        for key, entry in self._storage.items():
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
            # Find oldest entry
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


@app.post("/api/project/upload", response_model=ProjectUploadResponse)
async def upload_project(file: UploadFile = File(...)):
    """
    Upload project ZIP file
    """
    logger.info(f"Uploading project: {file.filename}")
    
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a .zip format project archive"
        )
    
    # Save uploaded file to temporary directory
    temp_dir = tempfile.mkdtemp(prefix='pyvizast_upload_')
    temp_file = Path(temp_dir) / file.filename
    
    try:
        # Write uploaded file
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        # Scan project
        scanner = ProjectScanner()
        scan_result, project_root = scanner.scan_zip(str(temp_file), Path(file.filename).stem)
        
        # Generate project ID
        project_id = f"proj_{int(time.time() * 1000)}"
        
        # Store project info (using new ProjectStorage class)
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
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error(f"Project upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project upload failed: {str(e)}"
        )


@app.post("/api/project/analyze")
async def analyze_project(
    file: UploadFile = File(...),
    quick_mode: bool = Form(False)
):
    """
    Analyze uploaded project
    Receive ZIP file directly and analyze, single step
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
    
    try:
        # Write uploaded file
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        # Scan project
        scanner = ProjectScanner()
        scan_result, project_root = scanner.scan_zip(str(temp_file), Path(file.filename).stem)
        
        # Analyze dependencies
        logger.debug("Analyzing dependencies...")
        dependency_analyzer = DependencyAnalyzer(project_root)
        module_files = {f.relative_path: f.path for f in scan_result.file_infos}
        dependency_graph = dependency_analyzer.analyze(list(module_files.values()))
        
        # Detect circular dependencies
        logger.debug("Detecting circular dependencies...")
        cycle_detector = CycleDetector(dependency_graph.adjacency_list)
        circular_issues = cycle_detector.detect()
        
        # Detect unused exports
        logger.debug("Detecting unused exports...")
        unused_detector = UnusedExportDetector(dependency_analyzer)
        unused_issues = unused_detector.detect(module_files) if not quick_mode else []
        
        # Merge global issues
        global_issues = circular_issues + unused_issues
        
        # Analyze each file
        file_results: List[FileAnalysisResult] = []
        
        for file_info in scan_result.file_infos:
            if quick_mode and file_info.is_test:
                # Skip test files in quick mode
                continue
            
            try:
                file_result = await _analyze_single_file(file_info, project_root)
                file_results.append(file_result)
            except Exception as e:
                logger.warning(f"Failed to analyze file {file_info.relative_path}: {e}")
                # Add an empty result
                file_results.append(FileAnalysisResult(
                    file=file_info,
                    summary=FileSummary(),
                    issues=[],
                    complexity={},
                    performance_hotspots=[],
                    suggestions=[],
                ))
        
        # Aggregate project metrics
        metrics_aggregator = ProjectMetricsAggregator()
        metrics = metrics_aggregator.aggregate(file_results, scan_result, global_issues)
        
        # Calculate analysis time
        analysis_time_ms = (time.time() - start_time) * 1000
        
        # Build dependency data
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project analysis failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


async def _analyze_single_file(file_info: FileInfo, project_root: str) -> FileAnalysisResult:
    """
    Analyze single file
    """
    from pathlib import Path as PathlibPath
    
    file_path = PathlibPath(file_info.path)
    
    try:
        code = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(code)
    except SyntaxError as e:
        # Read file content for editing
        try:
            code_content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            code_content = ""
        return FileAnalysisResult(
            file=file_info,
            content=code_content,
            summary=FileSummary(
                lines_of_code=file_info.line_count,
                issue_count=1,
            ),
            issues=[{
                'id': f'syntax_error_{file_info.relative_path}',
                'type': 'code_smell',
                'severity': 'error',
                'message': f"Syntax error: {str(e)}",
                'lineno': e.lineno,
            }],
            complexity={},
            performance_hotspots=[],
            suggestions=[],
        )
    except Exception as e:
        # Read file content for editing
        try:
            code_content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            code_content = ""
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
    
    # Complexity analysis
    complexity = complexity_analyzer.analyze(code, tree)
    
    # Performance analysis
    performance_analyzer.analyze(code, tree)
    
    # Code smell detection
    code_smell_detector.analyze(code, tree)
    
    # Security scan
    security_scanner.scan(code, tree)
    
    # Merge issues
    all_issues = (
        complexity_analyzer.get_issues() +
        performance_analyzer.get_issues() +
        code_smell_detector.issues +
        security_scanner.issues
    )
    
    # Build summary
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
        content=code,  # Include file content
        summary=summary,
        issues=[issue.model_dump() for issue in all_issues],
        complexity=complexity.model_dump(),
        performance_hotspots=[hs.model_dump() for hs in performance_analyzer.hotspots],
        suggestions=[],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)