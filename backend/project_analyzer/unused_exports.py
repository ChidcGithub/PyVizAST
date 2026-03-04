"""
Unused Export Detector - Detect unused exported symbols
"""
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from .models import GlobalIssue
from .symbol_extractor import SymbolExtractor, SymbolDefinition, SymbolUsage
from .dependency import DependencyAnalyzer
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UnusedSymbol:
    """Unused symbol"""
    name: str
    module: str
    type: str
    lineno: int
    is_exported: bool


class UnusedExportDetector:
    """Unused Export Detector"""
    
    # Common implicit entry points
    ENTRY_POINTS = {
        'main',
        '__main__',
        'setup',
        'pytest_configure',
        'pytest_collection_modifyitems',
        'app',
        'create_app',
        'get_app',
    }
    
    # Special methods (usually not called directly)
    MAGIC_METHODS = {
        '__init__', '__new__', '__del__',
        '__repr__', '__str__', '__format__',
        '__bytes__', '__bool__', '__len__',
        '__iter__', '__next__', '__reversed__',
        '__getitem__', '__setitem__', '__delitem__',
        '__contains__', '__call__', '__enter__',
        '__exit__', '__getattr__', '__setattr__',
        '__delattr__', '__eq__', '__ne__',
        '__lt__', '__le__', '__gt__', '__ge__',
        '__hash__', '__add__', '__sub__',
        '__mul__', '__truediv__', '__floordiv__',
        '__mod__', '__pow__', '__and__',
        '__or__', '__xor__', '__radd__',
        '__rsub__', '__rmul__', '__rtruediv__',
        '__rfloordiv__', '__rmod__', '__rpow__',
        '__rand__', '__ror__', '__rxor__',
        '__iadd__', '__isub__', '__imul__',
        '__itruediv__', '__ifloordiv__',
        '__imod__', '__ipow__', '__iand__',
        '__ior__', '__ixor__', '__neg__',
        '__pos__', '__abs__', '__invert__',
        '__complex__', '__int__', '__float__',
        '__index__', '__round__', '__trunc__',
        '__floor__', '__ceil__',
    }
    
    def __init__(self, dependency_analyzer: DependencyAnalyzer):
        """
        Initialize the detector
        
        Args:
            dependency_analyzer: Dependency analyzer
        """
        self.dependency_analyzer = dependency_analyzer
        self.symbol_extractor = SymbolExtractor()
        
        # Internal state
        self.exported_symbols: Dict[str, List[SymbolDefinition]] = {}
        self.used_symbols: Dict[str, Set[str]] = defaultdict(set)
    
    def detect(self, module_files: Dict[str, str]) -> List[GlobalIssue]:
        """
        Detect unused exported symbols
        
        Args:
            module_files: {module_name: file_path}
        
        Returns:
            List of unused export issues
        """
        # Extract all symbol definitions and usages
        definitions, usages = self.symbol_extractor.extract_from_project(module_files)
        
        # Build module to file mapping
        self._build_usage_map(usages, module_files)
        
        issues = []
        
        for module_name, defs in definitions.items():
            for definition in defs:
                # Only check public symbols
                if not definition.is_public:
                    continue
                
                # Skip special methods
                if definition.name in self.MAGIC_METHODS:
                    continue
                
                # Skip entry points
                if definition.name in self.ENTRY_POINTS:
                    continue
                
                # Check if used
                if self._is_symbol_used(definition, module_name, module_files):
                    continue
                
                # Found unused symbol
                issue = GlobalIssue(
                    issue_type='unused_export',
                    severity='info',
                    message=f"Symbol '{definition.name}' is exported but not used by other modules in the project",
                    locations=[
                        {
                            'file_path': module_name,
                            'lineno': definition.lineno,
                            'symbol': definition.name,
                            'type': definition.type,
                        }
                    ],
                    suggestion=self._generate_suggestion(definition),
                )
                issues.append(issue)
        
        if issues:
            logger.info(f"Detected {len(issues)} possibly unused exported symbols")
        
        return issues
    
    def _build_usage_map(self, usages: Dict[str, List[SymbolUsage]], 
                         module_files: Dict[str, str]) -> None:
        """Build symbol usage mapping"""
        for symbol_name, usage_list in usages.items():
            for usage in usage_list:
                # Try to resolve symbol source
                source_module = usage.source_module
                
                # Get dependencies of this module
                deps = self.dependency_analyzer.get_dependencies(source_module)
                
                # Record usage
                self.used_symbols[symbol_name].add(source_module)
                
                # If source module info exists, record it too
                if usage.module:
                    self.used_symbols[symbol_name].add(usage.module)
    
    def _is_symbol_used(self, definition: SymbolDefinition, module_name: str,
                        module_files: Dict[str, str]) -> bool:
        """
        Check if a symbol is used
        
        Args:
            definition: Symbol definition
            module_name: Module where the symbol is defined
            module_files: Module file mapping
        
        Returns:
            Whether the symbol is used
        """
        symbol_name = definition.name
        
        # Check if in __all__
        exports = self.symbol_extractor.module_exports.get(module_name, set())
        if symbol_name in exports:
            # In __all__, possibly a public API, don't report
            return True
        
        # Get modules that depend on this module
        dependents = self.dependency_analyzer.get_dependents(module_name)
        
        if not dependents:
            # No modules depend on this module, check if it's an entry point
            return self._is_entry_module(module_name, module_files)
        
        # Check if used in dependent modules
        for dependent in dependents:
            if symbol_name in self.used_symbols:
                # Check if usage is from dependent module
                usages = self.used_symbols[symbol_name]
                if dependent in usages:
                    return True
        
        # Check internal usage
        return self._is_used_internally(definition, module_name, module_files)
    
    def _is_entry_module(self, module_name: str, module_files: Dict[str, str]) -> bool:
        """Check if it's an entry module"""
        # __main__.py or module with main() function
        if '__main__' in module_name:
            return True
        
        file_path = module_files.get(module_name)
        if file_path:
            try:
                content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(content)
                
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == 'main':
                        return True
                    if isinstance(node, ast.If):
                        # Check if __name__ == '__main__':
                        if self._is_main_block(node):
                            return True
            except Exception:
                pass
        
        return False
    
    def _is_main_block(self, node: ast.If) -> bool:
        """Check if it's an if __name__ == '__main__' block"""
        test = node.test
        if isinstance(test, ast.Compare):
            if len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                if isinstance(test.left, ast.Name) and test.left.id == '__name__':
                    if test.comparators and isinstance(test.comparators[0], ast.Constant):
                        return test.comparators[0].value == '__main__'
        return False
    
    def _is_used_internally(self, definition: SymbolDefinition, module_name: str,
                           module_files: Dict[str, str]) -> bool:
        """Check if symbol is used internally in the module"""
        file_path = module_files.get(module_name)
        if not file_path:
            return False
        
        try:
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
            
            # Find all usages of the symbol
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == definition.name:
                    # Check if it's a usage (not definition)
                    if isinstance(node.ctx, ast.Load):
                        # Check if line number is after definition
                        if node.lineno > definition.lineno:
                            return True
            
            return False
        except Exception:
            return False
    
    def _generate_suggestion(self, definition: SymbolDefinition) -> str:
        """Generate fix suggestion"""
        suggestions = []
        
        if definition.type == 'function':
            suggestions.append("If this function is a public API, consider explicitly declaring it in __all__")
            suggestions.append("If this function is no longer needed, you can delete it or mark it as private (add underscore prefix)")
        elif definition.type == 'class':
            suggestions.append("If this class is a public API, consider explicitly declaring it in __all__")
            suggestions.append("If this class is internal implementation, consider adding an underscore prefix")
        else:
            suggestions.append("Consider adding this symbol to __all__ or marking it as private")
        
        return '\n'.join(suggestions)