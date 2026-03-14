"""
Code analysis API routes

@author: Chidc
@link: github.com/chidcGithub
"""
import ast
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..models.schemas import (
    CodeInput, AnalysisResult, ComplexityMetrics, SeverityLevel
)
from ..exceptions import CodeParsingError, CodeTooLargeError, AnalysisError
from ..utils import AnalyzerFactory, get_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


class PatchApplyRequest(BaseModel):
    """Patch apply request model"""
    code: str
    patch: str


@router.post("/analyze", response_model=AnalysisResult)
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
                        raise CodeParsingError(
                            f"Syntax error after truncation: {str(e)}. "
                            f"The file is very large and was truncated for analysis. "
                            f"Consider splitting into smaller files."
                        )
                    except MemoryError as mem_err:
                        logger.error(f"Memory error during aggressive truncation: {mem_err}")
                        import gc
                        gc.collect()
                else:
                    raise CodeTooLargeError(
                        f"Code too large ({code_lines} lines, {code_size} bytes), cannot parse. "
                        f"Suggestions: 1) Split code into multiple files; "
                        f"2) Use a more powerful machine; "
                        f"3) Analyze only part of the code."
                    )
        
        # Safety check: ensure tree was successfully parsed
        if tree is None:
            raise CodeTooLargeError(
                f"Code too large ({code_lines} lines, {code_size} bytes), cannot parse after all optimization attempts. "
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
        raise
    except RecursionError:
        logger.error("Recursion depth exceeded")
        raise AnalysisError("Code structure too complex to analyze")
    except MemoryError:
        logger.error("Out of memory")
        raise CodeTooLargeError("Code too large, out of memory")


@router.post("/complexity", response_model=ComplexityMetrics)
async def get_complexity(input_data: CodeInput):
    """Get complexity analysis results"""
    logger.debug("Getting complexity analysis")
    
    try:
        code = input_data.code
        tree = ast.parse(code)
        analyzer = AnalyzerFactory.create_complexity_analyzer()
        return analyzer.analyze(code, tree)
    except SyntaxError as e:
        raise CodeParsingError(f"Syntax error: {str(e)}")


@router.post("/performance")
async def get_performance_issues(input_data: CodeInput):
    """Get performance hotspot analysis"""
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


@router.post("/security")
async def get_security_issues(input_data: CodeInput):
    """Get security scan results"""
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


@router.post("/suggestions")
async def get_suggestions(input_data: CodeInput):
    """Get optimization suggestions"""
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


@router.post("/patches")
async def generate_patches(input_data: CodeInput):
    """Generate auto-fix patches"""
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


@router.post("/apply-patch")
async def apply_patch(request: PatchApplyRequest):
    """Apply patch to code"""
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
