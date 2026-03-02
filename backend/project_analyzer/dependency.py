"""
依赖图构建模块
解析 Python 文件的 import 语句，构建项目内文件之间的依赖关系图
"""

import ast
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Dict, List, Set, Optional, Tuple, Any

from .models import ProjectFile, ImportInfo, ExportInfo, FileDependency, ProjectDependencies

logger = logging.getLogger(__name__)


@dataclass
class DependencyNode:
    """依赖图节点"""
    file_path: str
    module_name: str
    is_package: bool = False  # 是否是包（__init__.py）
    imports: Set[str] = field(default_factory=set)  # 导入的模块名
    imported_by: Set[str] = field(default_factory=set)  # 被哪些模块导入
    exports: Set[str] = field(default_factory=set)  # 导出的符号


class DependencyGraphBuilder:
    """
    依赖图构建器
    负责解析项目文件的导入关系，构建完整的依赖图
    """

    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}
        self.module_to_file: Dict[str, str] = {}  # 模块名 -> 文件路径
        self.file_to_module: Dict[str, str] = {}  # 文件路径 -> 模块名
        self.external_modules: Set[str] = set()  # 外部依赖模块

        # Python 标准库模块（部分常见模块）
        self.stdlib_modules = self._get_stdlib_modules()

    def _get_stdlib_modules(self) -> Set[str]:
        """获取 Python 标准库模块列表"""
        import sys

        # 常见标准库模块
        common_stdlib = {
            'os', 'sys', 're', 'json', 'io', 'abc', 'ast', 'asyncio', 'atexit',
            'base64', 'bisect', 'builtins', 'bytesio', 'calendar', 'collections',
            'concurrent', 'configparser', 'contextlib', 'copy', 'csv', 'dataclasses',
            'datetime', 'decimal', 'difflib', 'dis', 'doctest', 'email', 'enum',
            'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
            'fractions', 'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob',
            'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imp',
            'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
            'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'marshal', 'math',
            'mimetypes', 'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'numbers',
            'operator', 'optparse', 'os', 'pathlib', 'pdb', 'pickle', 'pipes',
            'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath',
            'pprint', 'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr',
            'pydoc', 'queue', 'quopri', 'random', 're', 'readline', 'reprlib',
            'resource', 'rlcompleter', 'runpy', 'sched', 'secrets', 'select',
            'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd',
            'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd', 'sqlite3',
            'ssl', 'stat', 'statistics', 'string', 'stringio', 'struct', 'subprocess',
            'sunau', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile',
            'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading',
            'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace', 'traceback',
            'tracemalloc', 'tty', 'turtle', 'types', 'typing', 'unicodedata',
            'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave',
            'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
            'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib',
            # 第三方常见库
            'numpy', 'pandas', 'django', 'flask', 'fastapi', 'requests', 'httpx',
            'pytest', 'selenium', 'beautifulsoup4', 'bs4', 'lxml', 'pillow', 'PIL',
            'sqlalchemy', 'alembic', 'celery', 'redis', 'pymongo', 'motor',
            'cryptography', 'pydantic', 'uvicorn', 'gunicorn', 'click', 'typer',
            'rich', 'tqdm', 'aiohttp', 'boto3', 'botocore', 'google', 'aws',
        }

        return common_stdlib

    def build_dependency_graph(
        self,
        files: List[ProjectFile]
    ) -> Tuple[Dict[str, List[str]], ProjectDependencies]:
        """
        构建依赖图

        Args:
            files: 项目文件列表

        Returns:
            Tuple[Dict[str, List[str]], ProjectDependencies]:
                - 文件路径级别的依赖图 {文件路径: [依赖的文件路径列表]}
                - 完整的依赖信息对象
        """
        # 重置状态
        self.nodes.clear()
        self.module_to_file.clear()
        self.file_to_module.clear()
        self.external_modules.clear()

        # 第一遍：构建模块名映射
        self._build_module_mapping(files)

        # 第二遍：解析每个文件的导入
        file_dependencies: List[FileDependency] = []

        for file in files:
            try:
                tree = ast.parse(file.content)
                file_dep = self._analyze_file_imports(file, tree)
                file_dependencies.append(file_dep)
            except SyntaxError as e:
                logger.warning(f"文件 {file.path} 语法错误，跳过依赖分析: {e}")
                file_dependencies.append(FileDependency(
                    file_path=file.path,
                    imports=[],
                    exports=[],
                    internal_imports=[],
                    external_imports=[]
                ))

        # 构建文件路径级别的依赖图
        dependency_graph = self._build_file_dependency_graph(file_dependencies)

        # 构建完整的依赖信息
        project_deps = self._build_project_dependencies(file_dependencies)

        return dependency_graph, project_deps

    def _build_module_mapping(self, files: List[ProjectFile]):
        """
        构建模块名到文件路径的双向映射

        Args:
            files: 文件列表
        """
        for file in files:
            path = file.path.replace('\\', '/')
            module_name = self._path_to_module_name(path)

            # 记录映射
            self.module_to_file[module_name] = path
            self.file_to_module[path] = module_name

            # 创建节点
            is_package = path.endswith('__init__.py')
            self.nodes[path] = DependencyNode(
                file_path=path,
                module_name=module_name,
                is_package=is_package
            )

            # 对于包，也注册父包名
            if is_package:
                parent_module = module_name.rsplit('.', 1)[0] if '.' in module_name else ''
                if parent_module and parent_module not in self.module_to_file:
                    # 包本身也可以通过父名访问
                    self.module_to_file[parent_module] = path

    def _path_to_module_name(self, path: str) -> str:
        """
        将文件路径转换为模块名

        Args:
            path: 文件路径

        Returns:
            str: 模块名
        """
        # 统一使用正斜杠
        path = path.replace('\\', '/')

        # 去掉 .py 后缀
        if path.endswith('.py'):
            path = path[:-3]

        # 将路径分隔符替换为点
        module_name = path.replace('/', '.')

        return module_name

    def _analyze_file_imports(
        self,
        file: ProjectFile,
        tree: ast.AST
    ) -> FileDependency:
        """
        分析单个文件的导入语句

        Args:
            file: 项目文件
            tree: AST 树

        Returns:
            FileDependency: 文件依赖信息
        """
        imports: List[ImportInfo] = []
        exports: List[ExportInfo] = []
        internal_imports: List[str] = []
        external_imports: List[str] = []

        current_path = file.path.replace('\\', '/')
        current_module = self.file_to_module.get(current_path, '')

        for node in ast.walk(tree):
            # 处理 import xxx
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    import_info = ImportInfo(
                        module=module_name,
                        alias=alias.asname,
                        lineno=node.lineno
                    )
                    imports.append(import_info)

                    # 判断内部还是外部导入
                    resolved_path = self._resolve_module_to_path(module_name)
                    if resolved_path:
                        internal_imports.append(module_name)
                        # 更新节点信息
                        if current_path in self.nodes:
                            self.nodes[current_path].imports.add(module_name)
                    else:
                        external_imports.append(module_name)
                        self.external_modules.add(module_name.split('.')[0])

            # 处理 from xxx import yyy
            elif isinstance(node, ast.ImportFrom):
                level = node.level  # 相对导入层级
                module_name = node.module or ''
                items = [alias.name for alias in node.names]

                import_info = ImportInfo(
                    module=module_name,
                    items=items,
                    is_relative=level > 0,
                    level=level,
                    lineno=node.lineno
                )
                imports.append(import_info)

                # 解析实际模块名
                if level > 0:
                    # 相对导入
                    resolved_module = self._resolve_relative_import(
                        module_name, level, current_module, current_path
                    )
                else:
                    resolved_module = module_name

                if resolved_module:
                    resolved_path = self._resolve_module_to_path(resolved_module)
                    if resolved_path:
                        internal_imports.append(resolved_module)
                        if current_path in self.nodes:
                            self.nodes[current_path].imports.add(resolved_module)
                    else:
                        if resolved_module:
                            external_imports.append(resolved_module)
                            self.external_modules.add(resolved_module.split('.')[0])
                else:
                    if module_name:
                        external_imports.append(module_name)
                        self.external_modules.add(module_name.split('.')[0])

            # 收集导出信息
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    exports.append(ExportInfo(
                        name=node.name,
                        type='function',
                        lineno=node.lineno
                    ))
                    if current_path in self.nodes:
                        self.nodes[current_path].exports.add(node.name)

            elif isinstance(node, ast.AsyncFunctionDef):
                if not node.name.startswith('_'):
                    exports.append(ExportInfo(
                        name=node.name,
                        type='function',
                        lineno=node.lineno
                    ))
                    if current_path in self.nodes:
                        self.nodes[current_path].exports.add(node.name)

            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    exports.append(ExportInfo(
                        name=node.name,
                        type='class',
                        lineno=node.lineno
                    ))
                    if current_path in self.nodes:
                        self.nodes[current_path].exports.add(node.name)

            # 处理 __all__ 定义
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    if current_path in self.nodes:
                                        self.nodes[current_path].exports.add(elt.value)

        return FileDependency(
            file_path=file.path,
            imports=imports,
            exports=exports,
            internal_imports=list(set(internal_imports)),
            external_imports=list(set(external_imports))
        )

    def _resolve_module_to_path(self, module_name: str) -> Optional[str]:
        """
        将模块名解析为文件路径

        Args:
            module_name: 模块名

        Returns:
            Optional[str]: 文件路径，如果不在项目中则返回 None
        """
        # 直接匹配
        if module_name in self.module_to_file:
            return self.module_to_file[module_name]

        # 尝试匹配子模块
        for known_module, path in self.module_to_file.items():
            if known_module.startswith(module_name + '.'):
                return path
            if module_name.startswith(known_module + '.'):
                # 可能是包中的模块
                return path

        # 尝试作为包名
        if module_name in self.module_to_file:
            return self.module_to_file[module_name]

        return None

    def _resolve_relative_import(
        self,
        module_name: str,
        level: int,
        current_module: str,
        current_path: str
    ) -> Optional[str]:
        """
        解析相对导入

        Args:
            module_name: 模块名（可能为空）
            level: 相对导入层级（from .xxx 中点的数量）
            current_module: 当前文件所属模块名
            current_path: 当前文件路径

        Returns:
            Optional[str]: 解析后的完整模块名
        """
        # 获取当前模块的层级结构
        module_parts = current_module.split('.') if current_module else []

        # 计算基础模块（去掉 level 层）
        if level > len(module_parts):
            # 层级超出范围，可能是项目根目录之上的导入
            logger.warning(f"相对导入层级 {level} 超出当前模块层级: {current_module}")
            return None

        base_parts = module_parts[:-level] if level <= len(module_parts) else []

        # 构建完整模块名
        if module_name:
            full_module = '.'.join(base_parts + [module_name]) if base_parts else module_name
        else:
            # from . import xxx 的情况
            full_module = '.'.join(base_parts) if base_parts else None

        return full_module

    def _build_file_dependency_graph(
        self,
        file_dependencies: List[FileDependency]
    ) -> Dict[str, List[str]]:
        """
        构建文件路径级别的依赖图

        Args:
            file_dependencies: 文件依赖列表

        Returns:
            Dict[str, List[str]]: 文件路径依赖图
        """
        graph: Dict[str, List[str]] = {}

        for file_dep in file_dependencies:
            file_path = file_dep.file_path.replace('\\', '/')
            dependencies: List[str] = []

            # 将模块名转换为文件路径
            for module_name in file_dep.internal_imports:
                resolved_path = self._resolve_module_to_path(module_name)
                if resolved_path and resolved_path != file_path:
                    dependencies.append(resolved_path)

            graph[file_path] = list(set(dependencies))

        return graph

    def _build_project_dependencies(
        self,
        file_dependencies: List[FileDependency]
    ) -> ProjectDependencies:
        """
        构建项目级依赖信息

        Args:
            file_dependencies: 文件依赖列表

        Returns:
            ProjectDependencies: 项目依赖信息
        """
        # 构建依赖图
        dependency_graph: Dict[str, List[str]] = {}
        reverse_dependency_graph: Dict[str, List[str]] = defaultdict(list)

        for file_dep in file_dependencies:
            file_path = file_dep.file_path.replace('\\', '/')

            # 构建依赖图（模块名级别）
            dependency_graph[file_path] = file_dep.internal_imports

            # 构建反向依赖图
            for module_name in file_dep.internal_imports:
                resolved_path = self._resolve_module_to_path(module_name)
                if resolved_path:
                    reverse_dependency_graph[resolved_path].append(file_path)

        return ProjectDependencies(
            internal=file_dependencies,
            external=list(self.external_modules),
            dependency_graph=dependency_graph,
            reverse_dependency_graph=dict(reverse_dependency_graph)
        )

    def detect_cycles(self) -> List[List[str]]:
        """
        检测依赖图中的循环依赖

        Returns:
            List[List[str]]: 循环依赖列表，每个循环是一组文件路径
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(path: str, current_path: List[str]):
            visited.add(path)
            rec_stack.add(path)
            current_path.append(path)

            # 获取该文件的依赖
            node = self.nodes.get(path)
            if node:
                for imported_module in node.imports:
                    imported_path = self._resolve_module_to_path(imported_module)
                    if imported_path:
                        if imported_path not in visited:
                            dfs(imported_path, current_path)
                        elif imported_path in rec_stack:
                            # 找到循环
                            cycle_start = current_path.index(imported_path)
                            cycle = current_path[cycle_start:] + [imported_path]
                            # 标准化循环（从最小的节点开始）
                            min_idx = cycle.index(min(cycle[:-1]))
                            normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                            if normalized not in cycles:
                                cycles.append(normalized)

            current_path.pop()
            rec_stack.remove(path)

        for path in self.nodes:
            if path not in visited:
                dfs(path, [])

        return cycles

    def get_topological_order(self) -> Optional[List[str]]:
        """
        获取拓扑排序（用于确定模块加载顺序）

        Returns:
            Optional[List[str]]: 拓扑排序结果，存在循环依赖时返回 None
        """
        in_degree: Dict[str, int] = defaultdict(int)
        graph: Dict[str, List[str]] = defaultdict(list)

        # 构建图和入度
        for path, node in self.nodes.items():
            if path not in in_degree:
                in_degree[path] = 0

            for imported_module in node.imports:
                imported_path = self._resolve_module_to_path(imported_module)
                if imported_path and imported_path in self.nodes:
                    graph[imported_path].append(path)
                    in_degree[path] += 1

        # Kahn 算法
        queue = [path for path, degree in in_degree.items() if degree == 0]
        result: List[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            return None  # 存在循环

        return result


def build_dependency_graph(
    files: List[ProjectFile]
) -> Tuple[Dict[str, List[str]], ProjectDependencies]:
    """
    便捷函数：构建依赖图

    Args:
        files: 项目文件列表

    Returns:
        Tuple[Dict[str, List[str]], ProjectDependencies]:
            - 文件路径依赖图
            - 完整依赖信息
    """
    builder = DependencyGraphBuilder()
    return builder.build_dependency_graph(files)
