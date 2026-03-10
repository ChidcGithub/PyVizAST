"""
PyVizAST - FastAPI Backend
AST-based Python Code Visualizer and Optimization Analyzer

@author: Chidc
@link: github.com/chidcGithub
"""
import ast
import json
import logging
import os
import tempfile
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from .models.schemas import (
    CodeInput, AnalysisResult,
    ComplexityMetrics, CodeIssue, SeverityLevel,
    LearningModeResult, ChallengeResult
)
from .ast_parser import ASTParser, NodeMapper
from .analyzers import ComplexityAnalyzer, PerformanceAnalyzer, CodeSmellDetector, SecurityScanner
from .optimizers import SuggestionEngine, PatchGenerator
from .utils.logger import log_exception, init_logging
from .utils.progress import progress_tracker, ProgressStage
from .project_analyzer import (
    ProjectScanner,
    DependencyAnalyzer,
    CycleDetector,
    UnusedExportDetector,
    ProjectMetricsAggregator,
    FileAnalysisResult,
    FileSummary,
    FileInfo,
)


# Custom exception classes
class AnalysisError(Exception):
    """Base exception for analysis errors
    
    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error code for frontend handling
        details: Additional context about the error
    """
    
    def __init__(self, message: str = "An error occurred during analysis", 
                 error_code: str = "ANALYSIS_ERROR", 
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        result = self.message
        if self.details:
            result += f" | Details: {self.details}"
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class CodeParsingError(AnalysisError):
    """Exception raised when Python code cannot be parsed
    
    Attributes:
        line_number: Line where parsing failed (if known)
        syntax_error: Original SyntaxError if available
    """
    
    def __init__(self, message: str = "Failed to parse Python code", 
                 error_code: str = "CODE_PARSING_ERROR",
                 line_number: Optional[int] = None,
                 syntax_error: Optional[SyntaxError] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.line_number = line_number
        self.syntax_error = syntax_error
        
        details = details or {}
        if line_number is not None:
            details["line_number"] = line_number
        if syntax_error is not None:
            details["syntax_message"] = str(syntax_error)
        
        super().__init__(message, error_code, details)
    
    def __str__(self) -> str:
        result = self.message
        if self.line_number is not None:
            result += f" at line {self.line_number}"
        if self.syntax_error:
            result += f": {self.syntax_error}"
        return result


class CodeTooLargeError(AnalysisError):
    """Exception raised when code exceeds size limits
    
    Attributes:
        size: Actual size of the code (characters or lines)
        max_size: Maximum allowed size
        size_type: Type of size measurement ('characters' or 'lines')
    """
    
    def __init__(self, message: str = "Code exceeds maximum allowed size", 
                 error_code: str = "CODE_TOO_LARGE",
                 size: Optional[int] = None,
                 max_size: Optional[int] = None,
                 size_type: str = "characters",
                 details: Optional[Dict[str, Any]] = None):
        self.size = size
        self.max_size = max_size
        self.size_type = size_type
        
        details = details or {}
        if size is not None:
            details["actual_size"] = size
        if max_size is not None:
            details["max_allowed_size"] = max_size
        details["size_type"] = size_type
        
        super().__init__(message, error_code, details)
    
    def __str__(self) -> str:
        result = self.message
        if self.size is not None and self.max_size is not None:
            result += f": {self.size} {self.size_type} (max: {self.max_size})"
        return result


class ResourceNotFoundError(Exception):
    """Exception raised when a requested resource is not found
    
    Attributes:
        resource_type: Type of the resource (e.g., 'file', 'challenge', 'task')
        resource_id: Identifier of the missing resource
    """
    
    def __init__(self, message: str = "Requested resource not found",
                 resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None):
        self.message = message
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(self.message)
    
    def __str__(self) -> str:
        result = self.message
        if self.resource_type:
            result = f"{self.resource_type.capitalize()} not found"
        if self.resource_id:
            result += f": {self.resource_id}"
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error_code": "RESOURCE_NOT_FOUND",
            "message": str(self),
            "resource_type": self.resource_type,
            "resource_id": self.resource_id
        }


# Initialize logging system
logger = init_logging(level=logging.INFO)


# Create FastAPI application
app = FastAPI(
    title="PyVizAST API",
    description="Python AST Visualization and Static Analysis API",
    version="0.6.2",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Read allowed origins from environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Cache-Control"],
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
    
    # Extract error type and message for better user feedback
    error_type = type(exc).__name__
    error_message = str(exc) if str(exc) else "Unknown error occurred"
    
    # Provide user-friendly messages based on error type
    if isinstance(exc, TypeError):
        detail = f"Type error during analysis: {error_message}. This may indicate a bug in the code being analyzed."
    elif isinstance(exc, AttributeError):
        detail = f"Attribute error during analysis: {error_message}. The code structure may be unexpected."
    elif isinstance(exc, ValueError):
        detail = f"Value error during analysis: {error_message}"
    elif isinstance(exc, KeyError):
        detail = f"Key error during analysis: {error_message}. Some expected data is missing."
    elif isinstance(exc, RecursionError):
        detail = "Code structure is too deeply nested to analyze. Consider simplifying the code."
    elif isinstance(exc, MemoryError):
        detail = "Not enough memory to analyze this code. Try with a smaller file."
    else:
        detail = f"Analysis error ({error_type}): {error_message}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail, "error_type": error_type}
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
        "version": "0.6.2",
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


# ============== Progress Tracking Endpoints ==============

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    """Get current progress state for a task"""
    state = progress_tracker.get_state(task_id)
    if not state:
        return {"error": "Task not found", "task_id": task_id}
    return state.to_dict()


@app.get("/api/progress/{task_id}/stream")
async def progress_stream(task_id: str):
    """
    SSE endpoint for real-time progress updates
    Returns Server-Sent Events stream
    """
    async def event_generator():
        # First, send current state if exists
        current_state = progress_tracker.get_state(task_id)
        if current_state:
            yield current_state.to_sse()
        
        # Then stream updates
        async for event in progress_tracker.progress_generator(task_id):
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


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
        code_size = len(code)
        
        # Pre-check: warn about extremely large files
        MAX_RECOMMENDED_LINES = 3000
        MAX_SAFE_LINES = 10000
        if code_lines > MAX_SAFE_LINES:
            logger.warning(f"Very large file ({code_lines} lines, {code_size} bytes)")
        
        auto_simplified = code_lines > 500
        logger.debug(f"Code lines: {code_lines}, simplified mode: {auto_simplified}")
        
        # Parse AST - use progressive strategy for large files
        tree = None
        truncation_warning = None
        simplification_level = 0  # 0=normal, 1=simplified, 2=aggressive simplification
        
        while tree is None and simplification_level <= 2:
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                # Syntax errors should be raised immediately, no retry needed
                raise CodeParsingError(f"Syntax error: {str(e)}")
            except MemoryError:
                simplification_level += 1
                import gc
                gc.collect()  # Force garbage collection
                
                if simplification_level == 1:
                    # First memory error: try simplified mode
                    logger.warning(f"Code too large ({code_lines} lines), trying simplified mode...")
                    auto_simplified = True
                elif simplification_level == 2:
                    # Second memory error: try aggressive truncation
                    logger.warning("Simplified mode insufficient, trying smart truncation...")
                    try:
                        lines = code.splitlines()
                        if len(lines) > MAX_RECOMMENDED_LINES:
                            # Smart truncation: find a good cut point
                            # Try to end at a complete statement (line ending with :, blank line, or return)
                            cut_line = MAX_RECOMMENDED_LINES
                            for i in range(MAX_RECOMMENDED_LINES - 1, max(0, MAX_RECOMMENDED_LINES - 100), -1):
                                line = lines[i].rstrip()
                                if not line or line.endswith(':') or line.startswith('return ') or line.startswith('break'):
                                    cut_line = i + 1
                                    break
                            
                            truncated_lines = len(lines) - cut_line
                            code = '\n'.join(lines[:cut_line])
                            code_lines = cut_line
                            truncation_warning = f"Large file truncated: analyzed first {cut_line} lines ({truncated_lines} lines omitted for performance)"
                            logger.info(f"Smart truncation: keeping {cut_line} lines, omitting {truncated_lines}")
                            tree = ast.parse(code)
                            break
                    except SyntaxError as e:
                        # Truncated code may have syntax errors, provide helpful message
                        raise CodeParsingError(
                            f"Syntax error after truncation: {str(e)}. "
                            f"The file is very large and was truncated for analysis. "
                            f"Consider splitting into smaller files."
                        )
                    except MemoryError as mem_err:
                        logger.error(f"Memory error during aggressive truncation: {mem_err}")
                        gc.collect()
                else:
                    # Final failure
                    raise CodeTooLargeError(
                        f"Code too large ({code_lines} lines, {code_size} bytes), cannot parse. "
                        f"Suggestions: 1) Split code into multiple files; "
                        f"2) Use a more powerful machine; "
                        f"3) Analyze only part of the code."
                    )
        
        parser = get_parser({'simplified': auto_simplified, **options})
        ast_graph = parser.parse(code, tree=tree)  # Pass pre-parsed tree to avoid double parsing
        
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
            "node_statistics": node_mapper.get_statistics(ast_graph),
            "truncation_warning": truncation_warning
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
    logger.debug("Getting AST graph structure")
    
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
        logger.error(f"Challenge data JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}")
        return []


def get_challenges_cache() -> List[Dict[str, Any]]:
    """Get challenge data (with cache, auto-reload on file change)"""
    challenges_path = Path(__file__).parent / "data" / "challenges.json"
    
    # Check if cache needs to be refreshed
    if not hasattr(get_challenges_cache, '_cache'):
        get_challenges_cache._cache = load_challenges()
        get_challenges_cache._mtime = challenges_path.stat().st_mtime if challenges_path.exists() else 0
    elif challenges_path.exists():
        current_mtime = challenges_path.stat().st_mtime
        if current_mtime != get_challenges_cache._mtime:
            get_challenges_cache._cache = load_challenges()
            get_challenges_cache._mtime = current_mtime
            logger.debug("Challenge data reloaded due to file change")
    
    return get_challenges_cache._cache


def clear_challenges_cache():
    """Clear challenge cache to force reload"""
    if hasattr(get_challenges_cache, '_cache'):
        delattr(get_challenges_cache, '_cache')
    if hasattr(get_challenges_cache, '_mtime'):
        delattr(get_challenges_cache, '_mtime')
    logger.debug("Challenge cache cleared")


@app.post("/api/challenges/reload")
async def reload_challenges():
    """Force reload challenge data from file"""
    clear_challenges_cache()
    challenges = get_challenges_cache()
    return {"status": "ok", "count": len(challenges), "message": "Challenges reloaded"}


def load_challenge_categories() -> List[Dict[str, Any]]:
    """Load challenge categories from JSON file"""
    challenges_path = Path(__file__).parent / "data" / "challenges.json"
    try:
        with open(challenges_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("categories", [])
    except FileNotFoundError:
        logger.warning(f"Challenge categories file not found: {challenges_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Challenge categories JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}")
        return []


@app.get("/api/challenges/categories")
async def get_challenge_categories():
    """Get challenge categories"""
    logger.debug("Getting challenge categories")
    categories = load_challenge_categories()
    challenges = get_challenges_cache()
    
    # Enrich categories with challenge details
    for category in categories:
        category_challenges = [c for c in challenges if c["id"] in category.get("challenges", [])]
        category["challenge_count"] = len(category_challenges)
        category["total_points"] = sum(c.get("points", 0) for c in category_challenges)
    
    return categories


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
            "category": c.get("category"),
            "estimated_time_minutes": c.get("estimated_time_minutes"),
            "points": c.get("points", 0)
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
                "category": challenge.get("category"),
                "difficulty": challenge["difficulty"],
                "hints": challenge.get("hints", []),
                "learning_objectives": challenge.get("learning_objectives", []),
                "solution_hint": challenge.get("solution_hint"),
                "points": challenge.get("points", 0),
                "estimated_time_minutes": challenge.get("estimated_time_minutes", 5)
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
            
            # Calculate score based on points
            base_points = challenge.get("points", 100)
            correct_ratio = len(correct) / len(expected) if expected else 0
            penalty = len(wrong) * 0.1  # 10% penalty per wrong answer
            score = max(0, int(base_points * correct_ratio * (1 - penalty)))
            
            # Determine if passed (at least 60% of issues found)
            passed = correct_ratio >= 0.6
            
            return ChallengeResult(
                challenge_id=submission.challenge_id,
                score=score,
                max_score=base_points,
                found_issues=list(correct),
                missed_issues=list(missed),
                feedback=_generate_challenge_feedback(correct, missed, wrong, challenge.get("solution_hint"), passed),
                passed=passed
            )
    
    raise ResourceNotFoundError(f"Challenge not found: {submission.challenge_id}")


def _generate_node_explanation(node) -> Dict[str, Any]:
    """Generate comprehensive node explanation for learning mode"""
    node_name = node.name or "unnamed"
    node_type = node.type.value if hasattr(node.type, 'value') else str(node.type)
    
    # Comprehensive explanations for all AST node types
    explanations = {
        # Structure nodes
        "module": {
            "explanation": "This is the module (file) root node, representing the entire Python file.",
            "doc": "A module is the top-level organizational unit in Python. Each Python file is a module that can contain "
                   "function definitions, class definitions, import statements, and executable code. Modules help organize "
                   "code and provide namespace isolation.",
            "examples": [
                "# my_module.py\nimport os\n\ndef helper():\n    pass",
                "# All code in a file belongs to the module"
            ],
            "related": ["import", "package", "__name__", "__file__"]
        },
        "function": {
            "explanation": f"This is a function definition node. Function name is '{node_name}', "
                          f"it contains {len(node.children)} child nodes.",
            "doc": "In Python, functions are code blocks defined using the def keyword. Functions encapsulate reusable logic, "
                   "can receive parameters (positional, keyword, *args, **kwargs), and return values. They support decorators, "
                   "type hints, and docstrings for documentation.",
            "examples": [
                "def greet(name: str) -> str:\n    \"\"\"Return a greeting message.\"\"\"\n    return f'Hello, {name}!'",
                "def calculate(*args, operation='sum'):\n    if operation == 'sum':\n        return sum(args)\n    return max(args)"
            ],
            "related": ["parameters", "return", "decorators", "lambda", "type hints", "docstring"]
        },
        "class": {
            "explanation": f"This is a class definition node. Class name is '{node_name}'.",
            "doc": "Classes are blueprints for creating objects. They encapsulate data (attributes) and behavior (methods). "
                   "Python supports single and multiple inheritance, property decorators, class methods, static methods, "
                   "and special (dunder) methods like __init__, __str__, __repr__.",
            "examples": [
                "class Person:\n    def __init__(self, name: str):\n        self.name = name\n    \n    def greet(self) -> str:\n        return f'Hello, I am {self.name}'",
                "class Student(Person):\n    def __init__(self, name, grade):\n        super().__init__(name)\n        self.grade = grade"
            ],
            "related": ["inheritance", "methods", "attributes", "property", "classmethod", "staticmethod", "__init__"]
        },
        
        # Control flow
        "if": {
            "explanation": "This is an if conditional node, used to execute different code based on conditions.",
            "doc": "If statements control program flow based on boolean conditions. Python supports if-elif-else chains, "
                   "and conditions can be any expression that evaluates to a truthy or falsy value. Avoid deeply nested "
                   "conditionals by using early returns or guard clauses.",
            "examples": [
                "if x > 0:\n    print('positive')\nelif x < 0:\n    print('negative')\nelse:\n    print('zero')",
                "# Guard clause pattern\nif not user:\n    return None\n# Process user..."
            ],
            "related": ["elif", "else", "boolean logic", "ternary operator", "guard clause"]
        },
        "for": {
            "explanation": "This is a for loop node, used to iterate over iterable objects.",
            "doc": "For loops iterate over any iterable object (list, tuple, dict, set, string, range, generator). "
                   "Use enumerate() for index-value pairs, zip() for parallel iteration, and dict.items() for key-value pairs. "
                   "Avoid modifying the iterable while looping.",
            "examples": [
                "for i, item in enumerate(items):\n    print(f'{i}: {item}')",
                "for name, score in students.items():\n    print(f'{name}: {score}')",
                "for x, y in zip(list1, list2):\n    result.append(x + y)"
            ],
            "related": ["while", "range()", "enumerate()", "zip()", "iterators", "list comprehension", "break", "continue"]
        },
        "while": {
            "explanation": "This is a while loop node, used to repeat code while a condition is true.",
            "doc": "While loops continue execution as long as the condition remains truthy. Be careful to ensure "
                   "the condition eventually becomes false to avoid infinite loops. Use break to exit early "
                   "and continue to skip to the next iteration.",
            "examples": [
                "count = 0\nwhile count < 10:\n    print(count)\n    count += 1",
                "while True:\n    response = get_input()\n    if response == 'quit':\n        break"
            ],
            "related": ["for", "break", "continue", "else clause", "infinite loop"]
        },
        "try": {
            "explanation": "This is a try-except node for exception handling.",
            "doc": "Try-except blocks handle exceptions gracefully. Always catch specific exceptions rather than bare 'except:'. "
                   "The 'finally' clause always executes regardless of exceptions. Use 'else' clause for code that should "
                   "run only if no exception occurred.",
            "examples": [
                "try:\n    result = risky_operation()\nexcept ValueError as e:\n    print(f'Invalid value: {e}')\nelse:\n    print(f'Success: {result}')\nfinally:\n    cleanup()",
                "# Context manager is preferred for resources\nwith open('file.txt') as f:\n    data = f.read()"
            ],
            "related": ["except", "finally", "raise", "else", "with", "context manager", "custom exceptions"]
        },
        "with": {
            "explanation": "This is a with statement node for context management.",
            "doc": "The 'with' statement provides context management for resources that need setup and cleanup. "
                   "It ensures proper resource release even if exceptions occur. Common uses include file handling, "
                   "database connections, locks, and custom context managers.",
            "examples": [
                "with open('file.txt', 'r') as f:\n    content = f.read()\n# File automatically closed here",
                "with threading.Lock():\n    shared_resource.modify()\n# Lock automatically released"
            ],
            "related": ["context manager", "__enter__", "__exit__", "contextlib", "try-finally"]
        },
        
        # Expressions
        "call": {
            "explanation": f"This is a function call node, calling '{node_name}' function.",
            "doc": "Function calls execute a function with provided arguments. Python supports positional arguments, "
                   "keyword arguments, unpacking with *args and **kwargs. Built-in functions like len(), print(), "
                   "range() are frequently used. Method calls on objects use dot notation.",
            "examples": [
                "result = calculate(1, 2, 3, operation='sum')",
                "print(*items, sep=', ')\nprocess(**config)"
            ],
            "related": ["arguments", "parameters", "return value", "built-in functions", "methods"]
        },
        "binary_op": {
            "explanation": "This is a binary operation node (e.g., +, -, *, /, ==, and, or).",
            "doc": "Binary operations combine two operands with an operator. Arithmetic operators (+, -, *, /, //, %, **) "
                   "perform math. Comparison operators (==, !=, <, >, <=, >=) return boolean values. "
                   "Logical operators (and, or) short-circuit evaluation.",
            "examples": [
                "result = a + b * c  # Multiplication first\nresult = (a + b) * c  # Addition first",
                "if x > 0 and y > 0:  # Short-circuit: y not evaluated if x <= 0\n    return 'both positive'"
            ],
            "related": ["operators", "precedence", "short-circuit", "comparison", "arithmetic"]
        },
        "compare": {
            "explanation": "This is a comparison operation node.",
            "doc": "Comparison operators compare values and return boolean results. Python supports chained comparisons "
                   "like 'a < b < c' which is equivalent to 'a < b and b < c' but more readable and efficient. "
                   "Use 'is' for identity comparison, '==' for equality.",
            "examples": [
                "if 0 < x < 100:  # Chained comparison\n    print('x is between 0 and 100')",
                "if x is None:  # Identity check\n    x = default_value"
            ],
            "related": ["boolean", "operators", "chaining", "identity", "equality"]
        },
        "lambda": {
            "explanation": "This is a lambda (anonymous function) node.",
            "doc": "Lambda expressions create small anonymous functions with a single expression. They are useful for "
                   "short callbacks, key functions in sorting, and simple transformations. For complex logic, "
                   "use regular def functions for readability.",
            "examples": [
                "square = lambda x: x ** 2\nsquares = list(map(lambda x: x**2, range(10)))",
                "students.sort(key=lambda s: s.grade)"
            ],
            "related": ["function", "def", "map", "filter", "sorted", "key function"]
        },
        
        # Data structures
        "list": {
            "explanation": "This is a list literal node.",
            "doc": "Lists are mutable ordered sequences that can contain heterogeneous elements. They support indexing, "
                   "slicing, and various methods like append(), extend(), insert(), remove(), pop(). "
                   "Use list comprehensions for concise list creation.",
            "examples": [
                "numbers = [1, 2, 3, 4, 5]\nfirst = numbers[0]\nslice = numbers[1:3]",
                "squares = [x**2 for x in range(10) if x % 2 == 0]  # List comprehension"
            ],
            "related": ["tuple", "list comprehension", "slicing", "append", "extend", "mutable"]
        },
        "dict": {
            "explanation": "This is a dictionary literal node.",
            "doc": "Dictionaries are mutable mappings of key-value pairs. Keys must be hashable (immutable). "
                   "Python 3.7+ preserves insertion order. Use dict.get() for safe access with defaults, "
                   "and dict comprehension for creating dictionaries from iterables.",
            "examples": [
                "person = {'name': 'Alice', 'age': 30}\nname = person.get('name', 'Unknown')",
                "squares = {x: x**2 for x in range(5)}  # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}"
            ],
            "related": ["keys", "values", "items", "get", "update", "setdefault", "defaultdict"]
        },
        "set": {
            "explanation": "This is a set literal node.",
            "doc": "Sets are unordered collections of unique elements. They support mathematical set operations "
                   "like union (|), intersection (&), difference (-), and symmetric difference (^). "
                   "Use sets for membership testing and removing duplicates.",
            "examples": [
                "unique = set([1, 2, 2, 3, 3, 3])  # {1, 2, 3}\nif item in my_set:  # O(1) lookup",
                "common = set_a & set_b  # Intersection\nall_items = set_a | set_b  # Union"
            ],
            "related": ["frozenset", "union", "intersection", "difference", "membership"]
        },
        "tuple": {
            "explanation": "This is a tuple literal node.",
            "doc": "Tuples are immutable ordered sequences. They are commonly used for fixed collections of items, "
                   "function return values, and dictionary keys (since they're hashable). "
                   "Named tuples provide field names for better readability.",
            "examples": [
                "point = (3, 4)\nx, y = point  # Unpacking",
                "from collections import namedtuple\nPoint = namedtuple('Point', ['x', 'y'])\np = Point(3, 4)"
            ],
            "related": ["list", "unpacking", "namedtuple", "immutable", "hashable"]
        },
        
        # Variables
        "assign": {
            "explanation": "This is an assignment node, binding a value to a variable name.",
            "doc": "Assignment binds a value to a name. Python supports multiple assignment (a, b = 1, 2), "
                   "chained assignment (x = y = 0), and augmented assignment (x += 1). "
                   "Variables are references to objects, not containers.",
            "examples": [
                "x = 10\na, b = 1, 2  # Tuple unpacking\nx = y = z = 0  # Chained",
                "x += 1  # Augmented assignment\ndata['key'] = value  # Subscript assignment"
            ],
            "related": ["variables", "names", "binding", "augmented assignment", "unpacking"]
        },
        "name": {
            "explanation": f"This is a name (identifier) node: '{node_name}'.",
            "doc": "Names are identifiers that reference objects in Python's namespace. They can refer to variables, "
                   "functions, classes, modules, or any object. Name resolution follows LEGB rule: "
                   "Local, Enclosing, Global, Built-in scopes.",
            "examples": [
                "x = 10  # 'x' is a name\nimport math  # 'math' is a name\nprint(math.pi)",
                "def outer():\n    x = 1  # Local scope\n    def inner():\n        nonlocal x  # Enclosing scope"
            ],
            "related": ["scope", "namespace", "LEGB", "global", "nonlocal"]
        },
        
        # Others
        "import": {
            "explanation": "This is an import statement node.",
            "doc": "Import statements load modules and make their contents available. Use 'import module' for "
                   "full module access, 'from module import name' for specific items, and 'as' for aliases. "
                   "Avoid 'from module import *' as it pollutes the namespace.",
            "examples": [
                "import os\nfrom datetime import datetime, timedelta\nimport numpy as np",
                "from collections import defaultdict, Counter"
            ],
            "related": ["module", "package", "from", "as", "__import__", "importlib"]
        },
        "return": {
            "explanation": "This is a return statement node.",
            "doc": "Return statements exit a function and optionally return a value. Functions without explicit "
                   "return statements return None. Multiple values can be returned as a tuple. "
                   "Early returns can improve code clarity by handling edge cases first.",
            "examples": [
                "def add(a, b):\n    return a + b",
                "def find_item(items, target):\n    for i, item in enumerate(items):\n        if item == target:\n            return i  # Early return\n    return -1"
            ],
            "related": ["function", "None", "yield", "early return"]
        },
        "yield": {
            "explanation": "This is a yield statement node, used in generators.",
            "doc": "Yield statements turn a function into a generator. Generators produce values lazily, "
                   "one at a time, which is memory efficient for large sequences. Use 'yield from' to delegate "
                   "to another generator. Generator expressions offer a concise syntax.",
            "examples": [
                "def countdown(n):\n    while n > 0:\n        yield n\n        n -= 1",
                "# Generator expression\nsquares = (x**2 for x in range(1000000))  # Lazy evaluation"
            ],
            "related": ["generator", "iterator", "next", "yield from", "generator expression"]
        }
    }
    
    return explanations.get(node_type, {
        "explanation": f"This is an AST node of type {node_type}.",
        "doc": f"The {node_type} node type represents a specific construct in Python's abstract syntax tree. "
               f"Click on different nodes in the visualization to learn more about each type.",
        "examples": [],
        "related": ["AST", "parsing", "Python syntax"]
    })


def _generate_challenge_feedback(correct, missed, wrong, solution_hint=None, passed=False):
    """Generate comprehensive challenge feedback"""
    feedback = []
    
    if passed:
        feedback.append("🎉 Congratulations! You passed this challenge!")
    else:
        feedback.append("Keep practicing! You're getting there.")
    
    if correct:
        feedback.append(f"✅ Correctly identified: {', '.join(sorted(correct))}")
    
    if missed:
        feedback.append(f"⚠️ Missed issues: {', '.join(sorted(missed))}")
    
    if wrong:
        feedback.append(f"❌ Incorrectly identified: {', '.join(sorted(wrong))}")
    
    if solution_hint and not passed:
        feedback.append(f"💡 Hint: {solution_hint}")
    
    return "\n\n".join(feedback) if feedback else "Keep trying!"


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
        
        # Use list() to create a copy for safe iteration during modification
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
    
    # Initialize progress tracking if task_id provided
    if task_id:
        progress_tracker.create_task(task_id, "Initializing project analysis...")
    
    try:
        # Write uploaded file
        if task_id:
            progress_tracker.update(task_id, ProgressStage.UPLOADING, 5, "Uploading project files...")
        
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        # Scan project
        if task_id:
            progress_tracker.update(task_id, ProgressStage.SCANNING, 10, "Scanning project structure...")
        
        scanner = ProjectScanner()
        scan_result, project_root = scanner.scan_zip(str(temp_file), Path(file.filename).stem)
        
        if task_id:
            progress_tracker.update(task_id, ProgressStage.PARSING, 20, f"Found {scan_result.total_files} Python files")
        
        # Analyze dependencies
        if task_id:
            progress_tracker.update(task_id, ProgressStage.DEPENDENCIES, 25, "Analyzing dependencies...")
        logger.debug("Analyzing dependencies...")
        dependency_analyzer = DependencyAnalyzer(project_root)
        module_files = {f.relative_path: f.path for f in scan_result.file_infos}
        dependency_graph = dependency_analyzer.analyze(list(module_files.values()))
        
        # Detect circular dependencies
        if task_id:
            progress_tracker.update(task_id, ProgressStage.DEPENDENCIES, 35, "Detecting circular dependencies...")
        logger.debug("Detecting circular dependencies...")
        cycle_detector = CycleDetector(dependency_graph.adjacency_list)
        circular_issues = cycle_detector.detect()
        
        # Detect unused exports
        if task_id:
            progress_tracker.update(task_id, ProgressStage.DEPENDENCIES, 40, "Detecting unused exports...")
        logger.debug("Detecting unused exports...")
        unused_detector = UnusedExportDetector(dependency_analyzer)
        unused_issues = unused_detector.detect(module_files) if not quick_mode else []
        
        # Merge global issues
        global_issues = circular_issues + unused_issues
        
        # Analyze each file
        file_results: List[FileAnalysisResult] = []
        total_files = len(scan_result.file_infos)
        
        for idx, file_info in enumerate(scan_result.file_infos):
            if quick_mode and file_info.is_test:
                # Skip test files in quick mode
                continue
            
            # Update progress
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
        if task_id:
            progress_tracker.update(task_id, ProgressStage.FINALIZING, 95, "Aggregating metrics...")
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
        
        # Mark complete
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
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


async def _analyze_single_file(file_info: FileInfo, project_root: str) -> FileAnalysisResult:
    """
    Analyze single file
    """
    from pathlib import Path as PathlibPath
    
    file_path = PathlibPath(file_info.path)
    code_content = ""  # Initialize upfront to avoid undefined variable
    tree = None
    
    # First, read file content
    try:
        code_content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Failed to read file {file_info.relative_path}: {e}")
        return FileAnalysisResult(
            file=file_info,
            content="",
            summary=FileSummary(lines_of_code=file_info.line_count),
            issues=[],
            complexity={},
            performance_hotspots=[],
            suggestions=[],
        )
    
    # Parse AST
    try:
        tree = ast.parse(code_content)
    except SyntaxError as e:
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
    except Exception as e:
        logger.warning(f"Failed to parse AST for {file_info.relative_path}: {e}")
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
    complexity = complexity_analyzer.analyze(code_content, tree)
    
    # Performance analysis
    performance_analyzer.analyze(code_content, tree)
    
    # Code smell detection
    code_smell_detector.analyze(code_content, tree)
    
    # Security scan
    security_scanner.scan(code_content, tree)
    
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
        content=code_content,  # Use the already defined variable
        summary=summary,
        issues=[issue.model_dump() for issue in all_issues],
        complexity=complexity.model_dump(),
        performance_hotspots=[hs.model_dump() for hs in performance_analyzer.hotspots],
        suggestions=[],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)