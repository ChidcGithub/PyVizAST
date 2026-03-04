"""
Dependency Analyzer - Analyze module dependencies
"""
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .models import ImportInfo, DependencyEdge, DependencyGraph
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModuleInfo:
    """Module information"""
    path: str
    imports: List[ImportInfo] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    is_package: bool = False


class DependencyAnalyzer:
    """Dependency Analyzer"""
    
    # Standard library modules (partial list)
    STDLIB_MODULES = {
        'os', 'sys', 're', 'json', 'io', 'math', 'random', 'datetime',
        'collections', 'itertools', 'functools', 'typing', 'pathlib',
        'subprocess', 'threading', 'multiprocessing', 'asyncio',
        'logging', 'argparse', 'configparser', 'tempfile', 'shutil',
        'pickle', 'sqlite3', 'http', 'urllib', 'email', 'html', 'xml',
        'unittest', 'doctest', 'pdb', 'profile', 'time', 'copy',
        'abc', 'contextlib', 'dataclasses', 'enum', 'operator',
        'string', 'textwrap', 'unicodedata', 'struct', 'codecs',
        'csv', 'hashlib', 'hmac', 'secrets', 'base64', 'binascii',
        'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile', 'socket',
        'ssl', 'select', 'selectors', 'signal', 'mmap', 'ctypes',
        'warnings', 'traceback', 'exceptions', 'gc', 'inspect',
        'dis', 'ast', 'tokenize', 'keyword', 'token', 'symbol',
        'platform', 'errno', 'stat', 'fileinput', 'glob', 'fnmatch',
        'linecache', 'shutil', 'macpath', 'ntpath', 'posixpath',
        'importlib', 'pkgutil', 'modulefinder', 'runpy', 'zipimport',
        'types', 'weakref', 'builtins', '__future__',
    }
    
    # Common third-party libraries
    THIRD_PARTY_MODULES = {
        'numpy', 'pandas', 'matplotlib', 'scipy', 'sklearn', 'tensorflow',
        'torch', 'keras', 'requests', 'flask', 'django', 'fastapi',
        'pydantic', 'sqlalchemy', 'alembic', 'celery', 'redis',
        'pytest', 'selenium', 'beautifulsoup4', 'lxml', 'pillow',
        'cv2', 'opencv', 'pyyaml', 'toml', 'dotenv', 'click',
        'tqdm', 'rich', 'colorama', 'boto3', 'azure', 'google',
        'sentry', 'prometheus', 'celery', 'kombu', 'pika',
        'aiohttp', 'httpx', 'uvicorn', 'gunicorn', 'werkzeug',
        'jinja2', 'mako', 'chameleon', 'markupsafe', 'wtforms',
        'cython', 'numba', 'pypy', 'gevent', 'eventlet',
        'twisted', 'tornado', 'aiofiles', 'aioredis', 'aiomysql',
        'psycopg2', 'pymysql', 'mysql', 'pymongo', 'elasticsearch',
        'cassandra', 'kafka', 'zmq', 'grpc', 'thrift', 'avro',
        'protobuf', 'msgpack', 'snappy', 'zstd', 'lz4',
    }
    
    def __init__(self, project_root: str):
        """
        Initialize the dependency analyzer
        
        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root).resolve()
        self.modules: Dict[str, ModuleInfo] = {}
        self.module_paths: Dict[str, str] = {}  # module_name -> file_path
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
    
    def analyze(self, file_paths: List[str]) -> DependencyGraph:
        """
        Analyze dependencies
        
        Args:
            file_paths: List of file paths
        
        Returns:
            Dependency graph
        """
        # First pass: collect all module information
        for file_path in file_paths:
            self._analyze_file(file_path)
        
        # Second pass: build dependency graph
        self._build_dependency_graph()
        
        # Build return result
        nodes = list(self.module_paths.keys())
        edges = []
        
        for source, targets in self.dependency_graph.items():
            for target in targets:
                edges.append({
                    'source': source,
                    'target': target,
                    'type': 'import',
                })
        
        logger.info(f"Dependency analysis complete: {len(nodes)} modules, {len(edges)} dependencies")
        
        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            adjacency_list={k: list(v) for k, v in self.dependency_graph.items()},
        )
    
    def _analyze_file(self, file_path: str) -> None:
        """Analyze imports and exports of a single file"""
        path = Path(file_path)
        
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to parse file: {file_path}: {e}")
            return
        
        # Calculate module name
        relative_path = path.relative_to(self.project_root)
        module_name = self._path_to_module_name(relative_path)
        
        # Record module path
        self.module_paths[module_name] = str(relative_path).replace('\\', '/')
        
        # Analyze imports
        imports = self._extract_imports(tree)
        
        # Analyze exports (top-level definitions)
        exports = self._extract_exports(tree)
        
        self.modules[module_name] = ModuleInfo(
            path=str(relative_path).replace('\\', '/'),
            imports=imports,
            exports=exports,
            is_package=path.name == '__init__.py',
        )
    
    def _path_to_module_name(self, relative_path: Path) -> str:
        """Convert file path to module name"""
        parts = list(relative_path.parts)
        
        # Remove .py suffix
        if parts and parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]
        
        # Handle __init__.py
        if parts and parts[-1] == '__init__':
            parts = parts[:-1]
        
        return '.'.join(parts) if parts else '__main__'
    
    def _extract_imports(self, tree: ast.AST) -> List[ImportInfo]:
        """Extract import information"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module=alias.name,
                        names=[alias.name],
                        alias=alias.asname,
                        is_relative=False,
                        lineno=node.lineno,
                    ))
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                is_relative = node.level > 0
                
                names = [alias.name for alias in node.names]
                
                imports.append(ImportInfo(
                    module=module,
                    names=names,
                    is_relative=is_relative,
                    level=node.level,
                    lineno=node.lineno,
                ))
        
        return imports
    
    def _extract_exports(self, tree: ast.AST) -> List[str]:
        """Extract exported symbols (top-level definitions)"""
        exports = []
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                exports.append(node.name)
            elif isinstance(node, ast.ClassDef):
                exports.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        exports.append(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    exports.append(node.target.id)
        
        return exports
    
    def _build_dependency_graph(self) -> None:
        """Build dependency graph"""
        for module_name, module_info in self.modules.items():
            for imp in module_info.imports:
                target_module = self._resolve_import(module_name, imp)
                
                if target_module and target_module in self.module_paths:
                    # Only record internal project dependencies
                    self.dependency_graph[module_name].add(target_module)
    
    def _resolve_import(self, source_module: str, imp: ImportInfo) -> Optional[str]:
        """
        Resolve import and return target module name
        
        Args:
            source_module: Source module name
            imp: Import information
        
        Returns:
            Target module name, or None if unresolved
        """
        if imp.is_relative:
            # Relative import
            parts = source_module.split('.')
            
            # Go up based on level
            if imp.level > len(parts):
                return None
            
            base_parts = parts[:-imp.level] if imp.level <= len(parts) else []
            
            if imp.module:
                target = '.'.join(base_parts + [imp.module])
            else:
                target = '.'.join(base_parts)
            
            # Check if exists
            if target in self.module_paths:
                return target
            
            # Might be a module within a package
            for name in imp.names:
                potential = f"{target}.{name}" if target else name
                if potential in self.module_paths:
                    return potential
            
            return target if target else None
        
        else:
            # Absolute import
            module = imp.module or imp.names[0] if imp.names else ''
            
            # Check if it's a standard library or third-party library
            top_level = module.split('.')[0] if module else ''
            if top_level in self.STDLIB_MODULES or top_level in self.THIRD_PARTY_MODULES:
                return None
            
            # Check if it's an internal project module
            if module in self.module_paths:
                return module
            
            # Check partial match
            for known_module in self.module_paths:
                if known_module.startswith(module + '.') or known_module == module:
                    return module
            
            return None
    
    def get_module_imports(self, module_name: str) -> List[ImportInfo]:
        """Get all imports of a module"""
        return self.modules.get(module_name, ModuleInfo(path='')).imports
    
    def get_module_exports(self, module_name: str) -> List[str]:
        """Get all exports of a module"""
        return self.modules.get(module_name, ModuleInfo(path='')).exports
    
    def get_dependents(self, module_name: str) -> List[str]:
        """Get all modules that depend on a module"""
        dependents = []
        for source, targets in self.dependency_graph.items():
            if module_name in targets:
                dependents.append(source)
        return dependents
    
    def get_dependencies(self, module_name: str) -> List[str]:
        """Get all dependencies of a module"""
        return list(self.dependency_graph.get(module_name, set()))