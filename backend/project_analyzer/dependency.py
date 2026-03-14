"""
Dependency Analyzer - Analyze module dependencies
"""
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from .models import ImportInfo, DependencyGraph
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
    
    # Standard library modules (comprehensive list)
    STDLIB_MODULES = {
        # Core modules
        'os', 'sys', 're', 'json', 'io', 'math', 'random', 'datetime',
        'collections', 'itertools', 'functools', 'typing', 'pathlib',
        'subprocess', 'threading', 'multiprocessing', 'asyncio',
        'logging', 'argparse', 'configparser', 'tempfile', 'shutil',
        
        # Data handling
        'pickle', 'shelve', 'dbm', 'sqlite3', 'csv', 'fileinput',
        
        # Network
        'http', 'urllib', 'http.client', 'urllib.request', 'urllib.parse',
        'socket', 'ssl', 'select', 'selectors', 'signal', 'asyncore', 'asynchat',
        'email', 'html', 'xml', 'xml.etree', 'xml.dom', 'xml.sax',
        
        # Internet protocols
        'ftplib', 'poplib', 'imaplib', 'smtplib', 'telnetlib', 'nntplib',
        
        # Testing
        'unittest', 'doctest', 'pdb', 'profile', 'cProfile', 'timeit', 'trace',
        
        # Utils
        'time', 'copy', 'reprlib', 'pprint', 'textwrap', 'unicodedata',
        'string', 'stringprep', 'difflib', 'heapq', 'bisect', 'array',
        
        # Types and objects
        'abc', 'contextlib', 'dataclasses', 'enum', 'types', 'weakref',
        'operator', 'operator', 'functools',
        
        # Structured data
        'struct', 'codecs', 'codeop',
        
        # Security
        'hashlib', 'hmac', 'secrets', 'base64', 'binascii', 'quopri', 'uu',
        
        # Compression
        'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile', 'zlib',
        
        # File formats
        'plistlib', 'netrc', 'xdrlib',
        
        # Internationalization
        'gettext', 'locale',
        
        # Program framework
        'cmd', 'shlex', 'turtle',
        
        # GUI (Tkinter)
        'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext',
        
        # Development tools
        'pdb', 'profile', 'pstats', 'timeit', 'trace', 'tracemalloc',
        
        # Debugging
        'faulthandler', 'syslog', 'traceback', 'gc', 'inspect', 'dis',
        'symtable', 'tokenize', 'keyword', 'token', 'symbol', 'ast',
        
        # Import system
        'importlib', 'pkgutil', 'modulefinder', 'runpy', 'zipimport',
        'imp',  # Deprecated but still used
        
        # Platform specific
        'platform', 'errno', 'stat', 'filecmp', 'glob', 'fnmatch',
        'linecache', 'macpath', 'ntpath', 'posixpath', 'os.path',
        
        # Unix specific
        'posix', 'pwd', 'grp', 'termios', 'tty', 'pty', 'fcntl', 'pipes',
        'resource', 'syslog', 'mmap',
        
        # Windows specific
        'msilib', 'msvcrt', 'winreg', 'winsound',
        
        # Misc
        'builtins', '__future__', 'warnings', 'atexit', 'sched', 'queue',
        'dummy_threading', '_thread',
        
        # Python runtime
        'code', 'codeop', 'compileall', 'py_compile',
        
        # Data types
        'decimal', 'fractions', 'numbers', 'statistics',
        
        # Cryptographic
        'curses', 'curses.ascii', 'curses.panel', 'curses.textpad',
        
        # Multimedia
        'audioop', 'aifc', 'wave', 'chunk', 'colorsys', 'imghdr', 'sndhdr',
        'ossaudiodev',
        
        # Misc
        'formatter', 'optparse', 'gettext',
    }
    
    # Common third-party libraries (comprehensive list)
    THIRD_PARTY_MODULES = {
        # Data science
        'numpy', 'pandas', 'matplotlib', 'seaborn', 'plotly', 'bokeh',
        'scipy', 'sklearn', 'scikit-learn', 'statsmodels', 'sympy',
        
        # Machine learning
        'tensorflow', 'torch', 'keras', 'caffe', 'theano', 'chainer',
        'mxnet', 'paddle', 'jax', 'flax', 'transformers', 'huggingface',
        
        # Deep learning tools
        'tensorboard', 'wandb', 'mlflow', 'optuna', 'hyperopt',
        
        # Web frameworks
        'flask', 'django', 'fastapi', 'tornado', 'pyramid', 'bottle',
        'aiohttp', 'sanic', 'starlette', 'quart', 'falcon',
        
        # Web servers
        'uvicorn', 'gunicorn', 'werkzeug', 'waitress', 'cheroot',
        
        # API
        'pydantic', 'marshmallow', 'attrs', 'cerberus', 'voluptuous',
        
        # Database
        'sqlalchemy', 'alembic', 'peewee', 'tortoise', 'databases',
        'psycopg2', 'pymysql', 'mysqlclient', 'pyodbc',
        'pymongo', 'motor', 'redis', 'aioredis', 'arango',
        'elasticsearch', 'cassandra', 'neo4j', 'dynamodb',
        
        # Async
        'celery', 'kombu', 'pika', 'aiokafka', 'confluent_kafka',
        
        # HTTP clients
        'requests', 'httpx', 'urllib3', 'aiohttp', 'http.client',
        
        # Testing
        'pytest', 'nose', 'unittest2', 'mock', 'faker', 'factory',
        'hypothesis', 'coverage', 'tox', 'nox',
        
        # Code quality
        'pylint', 'flake8', 'mypy', 'black', 'isort', 'autopep8',
        'bandit', 'pydocstyle', 'radon',
        
        # Web scraping
        'selenium', 'beautifulsoup4', 'bs4', 'lxml', 'scrapy', 'parsel',
        'playwright', 'requests-html',
        
        # Image processing
        'pillow', 'PIL', 'cv2', 'opencv', 'opencv-python', 'imageio',
        'scikit-image', 'imgaug', 'albumentations',
        
        # NLP
        'nltk', 'spacy', 'gensim', 'textblob', 'pattern',
        
        # Configuration
        'pyyaml', 'yaml', 'toml', 'configparser', 'dotenv', 'python-dotenv',
        'hydra', 'confuse',
        
        # CLI
        'click', 'typer', 'argparse', 'docopt', 'fire', 'rich',
        
        # Progress and output
        'tqdm', 'rich', 'colorama', 'termcolor', 'blessed',
        
        # Cloud
        'boto3', 'botocore', 'azure', 'google-cloud', 'gcloud',
        'kubernetes', 'docker', 'fabric', 'paramiko',
        
        # Monitoring
        'sentry', 'sentry-sdk', 'prometheus', 'prometheus_client',
        'datadog', 'newrelic', 'opentelemetry',
        
        # Serialization
        'protobuf', 'msgpack', 'thrift', 'avro', 'capnproto',
        
        # Compression
        'snappy', 'zstd', 'lz4', 'blosc',
        
        # Security
        'cryptography', 'pycryptodome', 'passlib', 'bcrypt', 'pyjwt',
        
        # Task queue
        'rq', 'dramatiq', 'huey',
        
        # Email
        'mailgun', 'sendgrid', 'mailjet',
        
        # Other common
        'pytz', 'dateutil', 'arrow', 'pendulum',
        'jinja2', 'mako', 'chameleon', 'markupsafe',
        'wtforms', 'flask-wtf',
        'wtforms', 'flask-login', 'flask-migrate',
        'cython', 'numba', 'pypy',
        'gevent', 'eventlet', 'twisted',
        'aiofiles', 'aiomultiprocess',
        'pyinstaller', 'cx_freeze', 'nuitka',
        'loguru', 'structlog',
        'tenacity', 'retry', 'backoff',
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
            
            # Calculate the base package path
            # level=1 means current package, level=2 means parent package, etc.
            if imp.level > len(parts):
                # Relative import level exceeds module depth
                # This can happen in __init__.py or when module structure is unusual
                # Try to resolve from project root with warning
                base_parts = []
                logger.warning(
                    f"Relative import level {imp.level} exceeds module depth "
                    f"'{source_module}', attempting to resolve from project root"
                )
            else:
                # Go up 'level' packages
                # For level=1 from 'pkg.sub.mod', base_parts should be ['pkg', 'sub']
                # For level=2 from 'pkg.sub.mod', base_parts should be ['pkg']
                base_parts = parts[:-imp.level] if imp.level > 0 else parts
            
            # Build target module name
            if imp.module:
                target = '.'.join(base_parts + [imp.module]) if base_parts else imp.module
            else:
                # from . import name (level > 0, module is empty)
                target = '.'.join(base_parts) if base_parts else ''
            
            # Check if the target module exists in our known modules
            if target and target in self.module_paths:
                return target
            
            # The import might be importing a specific name from a package
            # e.g., 'from . import submodule' where submodule is a package
            for name in imp.names:
                potential = f"{target}.{name}" if target else name
                if potential in self.module_paths:
                    return potential
            
            # Try partial matches for packages
            if target:
                for known_module in self.module_paths:
                    if known_module.startswith(target + '.') or known_module == target:
                        return target
            
            # Return the resolved target even if not found (for external detection)
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
            
            # Check partial match (importing from a package)
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