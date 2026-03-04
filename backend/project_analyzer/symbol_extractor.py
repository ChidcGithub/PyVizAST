"""
Symbol Extractor - Extract symbol definitions and usages from modules
"""
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SymbolDefinition:
    """Symbol definition"""
    name: str
    type: str  # 'function', 'class', 'variable', 'constant', 'import'
    module: str
    lineno: int
    col_offset: int = 0
    is_public: bool = True
    is_exported: bool = False  # Whether in __all__


@dataclass
class SymbolUsage:
    """Symbol usage"""
    name: str
    module: str
    source_module: str  # Module using this symbol
    lineno: int
    context: str = ''  # Usage context


class SymbolExtractor:
    """Symbol Extractor"""
    
    def __init__(self):
        self.definitions: Dict[str, List[SymbolDefinition]] = defaultdict(list)
        self.usages: Dict[str, List[SymbolUsage]] = defaultdict(list)
        self.module_exports: Dict[str, Set[str]] = {}  # module -> __all__ content
    
    def extract_from_project(self, module_files: Dict[str, str]) -> Tuple[Dict[str, List[SymbolDefinition]], Dict[str, List[SymbolUsage]]]:
        """
        Extract all symbols from a project
        
        Args:
            module_files: {module_name: file_path}
        
        Returns:
            (definitions dict, usages dict)
        """
        # First pass: extract all definitions
        for module_name, file_path in module_files.items():
            self._extract_definitions(module_name, file_path)
        
        # Second pass: extract all usages
        for module_name, file_path in module_files.items():
            self._extract_usages(module_name, file_path)
        
        return dict(self.definitions), dict(self.usages)
    
    def _extract_definitions(self, module_name: str, file_path: str) -> None:
        """Extract symbol definitions from a module"""
        try:
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to parse file: {file_path}: {e}")
            return
        
        # Check __all__
        exports = self._extract_all(tree)
        self.module_exports[module_name] = exports
        
        # Extract top-level definitions
        for node in ast.iter_child_nodes(tree):
            definition = self._node_to_definition(node, module_name)
            if definition:
                # Check if public
                definition.is_public = not definition.name.startswith('_')
                definition.is_exported = definition.name in exports if exports else definition.is_public
                self.definitions[module_name].append(definition)
    
    def _extract_all(self, tree: ast.AST) -> Set[str]:
        """Extract __all__ content"""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            exports = set()
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.add(elt.value)
                            return exports
        return set()
    
    def _node_to_definition(self, node: ast.AST, module_name: str) -> Optional[SymbolDefinition]:
        """Convert AST node to symbol definition"""
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            return SymbolDefinition(
                name=node.name,
                type='function',
                module=module_name,
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
        
        elif isinstance(node, ast.ClassDef):
            return SymbolDefinition(
                name=node.name,
                type='class',
                module=module_name,
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
        
        elif isinstance(node, ast.Assign):
            # Only handle simple assignments with single target
            if len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    # Determine if it's a constant (uppercase name)
                    is_constant = target.id.isupper() or (
                        target.id[0].isupper() and '_' in target.id
                    )
                    return SymbolDefinition(
                        name=target.id,
                        type='constant' if is_constant else 'variable',
                        module=module_name,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    )
        
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                return SymbolDefinition(
                    name=node.target.id,
                    type='variable',
                    module=module_name,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                )
        
        return None
    
    def _extract_usages(self, source_module: str, file_path: str) -> None:
        """Extract symbol usages from a module"""
        try:
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to parse file: {file_path}: {e}")
            return
        
        # Use visitor to extract name usages
        visitor = UsageVisitor(source_module)
        visitor.visit(tree)
        
        for name, usages in visitor.usages.items():
            self.usages[name].extend(usages)
    
    def get_public_symbols(self, module_name: str) -> List[SymbolDefinition]:
        """Get public symbols of a module"""
        return [
            d for d in self.definitions.get(module_name, [])
            if d.is_public
        ]
    
    def get_exported_symbols(self, module_name: str) -> List[SymbolDefinition]:
        """Get exported symbols of a module"""
        return [
            d for d in self.definitions.get(module_name, [])
            if d.is_exported
        ]


class UsageVisitor(ast.NodeVisitor):
    """Symbol usage visitor"""
    
    def __init__(self, source_module: str):
        self.source_module = source_module
        self.usages: Dict[str, List[SymbolUsage]] = defaultdict(list)
        self._in_definition = False
        self._definition_names: Set[str] = set()
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._definition_names.add(node.name)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._definition_names.add(node.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._definition_names.add(node.name)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        # Only record usages (loads), not definitions
        if isinstance(node.ctx, ast.Load):
            # Exclude locally defined names
            if node.id not in self._definition_names:
                self.usages[node.id].append(SymbolUsage(
                    name=node.id,
                    module='',  # Needs resolution later
                    source_module=self.source_module,
                    lineno=node.lineno,
                    context='load',
                ))
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Record attribute access
        if isinstance(node.ctx, ast.Load):
            self.usages[node.attr].append(SymbolUsage(
                name=node.attr,
                module='',  # Needs resolution later
                source_module=self.source_module,
                lineno=node.lineno,
                context='attribute',
            ))
        self.generic_visit(node)