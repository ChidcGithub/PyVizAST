"""
Analyzer Factory - Shared factory for creating analyzer instances

@author: Chidc
@link: github.com/chidcGithub
"""
from ..ast_parser import ASTParser, NodeMapper
from ..analyzers import (
    ComplexityAnalyzer,
    PerformanceAnalyzer,
    CodeSmellDetector,
    SecurityScanner,
)
from ..optimizers import SuggestionEngine, PatchGenerator


def get_parser(options: dict = None) -> ASTParser:
    """Get configured parser instance"""
    options = options or {}
    max_nodes = options.get('max_nodes', 2000)
    simplified = options.get('simplified', False)
    
    return ASTParser(max_nodes=max_nodes, simplified=simplified)


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
