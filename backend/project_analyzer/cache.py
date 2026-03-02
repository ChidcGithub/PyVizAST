"""
缓存模块
提供 AST 解析缓存和依赖图缓存，避免重复解析
"""

import ast
import hashlib
import logging
import os
import pickle
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    content_hash: str  # 内容哈希
    ast_tree: Optional[ast.AST] = None  # AST 树（内存缓存）
    imports: List[Dict[str, Any]] = field(default_factory=list)  # 导入信息
    exports: List[Dict[str, Any]] = field(default_factory=list)  # 导出信息
    timestamp: float = field(default_factory=time.time)


class ASTCache:
    """
    AST 解析缓存
    
    使用内存缓存 + 可选的持久化缓存
    避免对同一文件重复解析 AST
    """

    def __init__(self, max_size: int = 100, persist: bool = False, cache_dir: Optional[str] = None):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            persist: 是否持久化到磁盘
            cache_dir: 缓存目录
        """
        self.max_size = max_size
        self.persist = persist
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".pyvizast" / "cache"
        
        # 内存缓存
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # LRU 队列
        self._access_order: List[str] = []
        
        # 统计
        self._hits = 0
        self._misses = 0
        
        if persist:
            self._ensure_cache_dir()
            self._load_from_disk()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _evict_lru(self):
        """淘汰最久未使用的条目"""
        if len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]
                logger.debug(f"淘汰缓存条目: {oldest_key}")

    def get(self, file_path: str, content: str) -> Optional[Tuple[ast.AST, List[Dict], List[Dict]]]:
        """
        获取缓存的 AST
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            Optional[Tuple[ast.AST, List[Dict], List[Dict]]]: (AST, imports, exports) 或 None
        """
        content_hash = self._compute_hash(content)
        cache_key = file_path
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if entry.content_hash == content_hash:
                    # 命中
                    self._hits += 1
                    # 更新访问顺序
                    if cache_key in self._access_order:
                        self._access_order.remove(cache_key)
                    self._access_order.append(cache_key)
                    
                    return (entry.ast_tree, entry.imports, entry.exports)
            
            # 未命中
            self._misses += 1
            return None

    def set(self, file_path: str, content: str, tree: ast.AST, 
            imports: List[Dict], exports: List[Dict]):
        """
        设置缓存
        
        Args:
            file_path: 文件路径
            content: 文件内容
            tree: AST 树
            imports: 导入信息
            exports: 导出信息
        """
        content_hash = self._compute_hash(content)
        cache_key = file_path
        
        with self._lock:
            # 淘汰旧条目
            if cache_key not in self._cache:
                self._evict_lru()
            
            # 创建缓存条目
            self._cache[cache_key] = CacheEntry(
                content_hash=content_hash,
                ast_tree=tree,
                imports=imports,
                exports=exports
            )
            
            # 更新访问顺序
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            
            # 持久化
            if self.persist:
                self._save_entry_to_disk(cache_key, self._cache[cache_key])

    def parse_with_cache(self, file_path: str, content: str) -> Tuple[ast.AST, bool]:
        """
        使用缓存解析 AST
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            Tuple[ast.AST, bool]: (AST, 是否从缓存获取)
        """
        cached = self.get(file_path, content)
        if cached:
            return cached[0], True
        
        # 解析 AST
        tree = ast.parse(content)
        
        # 提取导入导出信息
        imports = self._extract_imports(tree)
        exports = self._extract_exports(tree)
        
        # 存入缓存
        self.set(file_path, content, tree, imports, exports)
        
        return tree, False

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取导入信息"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'alias': alias.asname,
                        'lineno': node.lineno,
                        'type': 'import'
                    })
            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    'module': node.module or '',
                    'names': [alias.name for alias in node.names],
                    'level': node.level,
                    'lineno': node.lineno,
                    'type': 'from'
                })
        return imports

    def _extract_exports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取导出信息"""
        exports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    exports.append({
                        'name': node.name,
                        'type': 'function',
                        'lineno': node.lineno
                    })
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    exports.append({
                        'name': node.name,
                        'type': 'class',
                        'lineno': node.lineno
                    })
        return exports

    def _save_entry_to_disk(self, key: str, entry: CacheEntry):
        """保存条目到磁盘"""
        try:
            cache_file = self.cache_dir / f"{key.replace('/', '_').replace('\\', '_')}.cache"
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'content_hash': entry.content_hash,
                    'imports': entry.imports,
                    'exports': entry.exports,
                    # 注意：不保存 AST 对象，因为它不容易序列化
                }, f)
        except Exception as e:
            logger.warning(f"保存缓存到磁盘失败: {e}")

    def _load_from_disk(self):
        """从磁盘加载缓存"""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                        # 这里只加载元数据，AST 需要时重新解析
                except Exception as e:
                    logger.debug(f"加载缓存文件失败: {cache_file}: {e}")
        except Exception as e:
            logger.warning(f"从磁盘加载缓存失败: {e}")

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate
        }


class DependencyGraphCache:
    """
    依赖图缓存
    
    缓存整个项目的依赖图，支持增量更新
    """

    def __init__(self):
        self._graph_cache: Dict[str, Any] = {}
        self._file_hashes: Dict[str, str] = {}
        self._lock = threading.RLock()

    def _compute_file_hash(self, content: str) -> str:
        """计算文件内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def get_cached_graph(self, project_hash: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的依赖图
        
        Args:
            project_hash: 项目哈希（所有文件哈希的组合）
            
        Returns:
            Optional[Dict]: 缓存的依赖图或 None
        """
        with self._lock:
            return self._graph_cache.get(project_hash)

    def compute_project_hash(self, files: List[Tuple[str, str]]) -> str:
        """
        计算项目哈希
        
        Args:
            files: [(文件路径, 文件内容), ...]
            
        Returns:
            str: 项目哈希
        """
        combined = ''.join(f"{path}:{self._compute_file_hash(content)}" 
                          for path, content in sorted(files))
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]

    def update_file_hash(self, file_path: str, content: str) -> bool:
        """
        更新文件哈希，返回是否有变化
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            bool: 文件是否有变化
        """
        new_hash = self._compute_file_hash(content)
        with self._lock:
            old_hash = self._file_hashes.get(file_path)
            self._file_hashes[file_path] = new_hash
            return old_hash != new_hash

    def get_changed_files(self, files: List[Tuple[str, str]]) -> List[str]:
        """
        获取有变化的文件列表
        
        Args:
            files: [(文件路径, 文件内容), ...]
            
        Returns:
            List[str]: 有变化的文件路径列表
        """
        changed = []
        for path, content in files:
            if self.update_file_hash(path, content):
                changed.append(path)
        return changed

    def set_graph_cache(self, project_hash: str, graph: Dict[str, Any]):
        """设置依赖图缓存"""
        with self._lock:
            self._graph_cache[project_hash] = graph

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._graph_cache.clear()
            self._file_hashes.clear()


# 全局缓存实例
_ast_cache: Optional[ASTCache] = None
_dep_cache: Optional[DependencyGraphCache] = None


def get_ast_cache(max_size: int = 100, persist: bool = False) -> ASTCache:
    """获取全局 AST 缓存实例"""
    global _ast_cache
    if _ast_cache is None:
        _ast_cache = ASTCache(max_size=max_size, persist=persist)
    return _ast_cache


def get_dependency_cache() -> DependencyGraphCache:
    """获取全局依赖图缓存实例"""
    global _dep_cache
    if _dep_cache is None:
        _dep_cache = DependencyGraphCache()
    return _dep_cache


def clear_all_caches():
    """清空所有缓存"""
    global _ast_cache, _dep_cache
    if _ast_cache:
        _ast_cache.clear()
    if _dep_cache:
        _dep_cache.clear()
