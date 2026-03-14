"""
AST-related API routes

@author: Chidc
@link: github.com/chidcGithub
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..models.schemas import CodeInput, NodeType
from ..exceptions import CodeParsingError, CodeTooLargeError
from ..utils import AnalyzerFactory, get_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ast"])


@router.post("/ast")
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


@router.post("/ast/filter")
async def filter_ast(input_data: CodeInput, node_types: Optional[str] = None, max_depth: Optional[int] = None):
    """Filter AST nodes"""
    logger.debug(f"Filtering AST nodes, types: {node_types}, max depth: {max_depth}")
    
    try:
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
