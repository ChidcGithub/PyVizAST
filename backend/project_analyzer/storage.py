"""
持久化存储模块
使用 SQLite 存储分析结果，支持增量分析
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# 数据库版本，用于迁移
DB_VERSION = 1


@dataclass
class FileRecord:
    """文件记录"""
    path: str
    content_hash: str
    size_bytes: int
    line_count: int
    last_analyzed: float
    analysis_json: str  # JSON 序列化的分析结果


@dataclass 
class ProjectRecord:
    """项目记录"""
    project_hash: str
    project_name: str
    total_files: int
    total_lines: int
    analysis_json: str  # JSON 序列化的完整分析结果
    created_at: float
    updated_at: float


class AnalysisStorage:
    """
    分析结果存储
    
    使用 SQLite 持久化分析结果，支持：
    - 按文件路径和内容哈希索引
    - 增量分析（只分析变化的文件）
    - 历史记录查询
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储
        
        Args:
            db_path: 数据库文件路径，默认为 ~/.pyvizast/analysis.db
        """
        if db_path is None:
            cache_dir = Path.home() / ".pyvizast"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(cache_dir / "analysis.db")
        
        self.db_path = db_path
        self._lock = threading.RLock()
        self._local = threading.local()
        
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（线程安全）"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        
        try:
            yield self._local.conn
        except Exception:
            if self._local.conn:
                self._local.conn.rollback()
            raise
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 元数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 检查版本
            cursor.execute("SELECT value FROM metadata WHERE key = 'version'")
            row = cursor.fetchone()
            current_version = int(row['value']) if row else 0
            
            if current_version < DB_VERSION:
                self._migrate(conn, current_version, DB_VERSION)
            
            # 文件分析结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    size_bytes INTEGER DEFAULT 0,
                    line_count INTEGER DEFAULT 0,
                    last_analyzed REAL NOT NULL,
                    analysis_json TEXT,
                    UNIQUE(path, content_hash)
                )
            """)
            
            # 项目分析结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_hash TEXT NOT NULL UNIQUE,
                    project_name TEXT,
                    total_files INTEGER DEFAULT 0,
                    total_lines INTEGER DEFAULT 0,
                    analysis_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            
            # 文件到项目的映射表（用于增量分析）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_project_map (
                    file_id INTEGER,
                    project_id INTEGER,
                    PRIMARY KEY (file_id, project_id),
                    FOREIGN KEY (file_id) REFERENCES file_analysis(id),
                    FOREIGN KEY (project_id) REFERENCES project_analysis(id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_path 
                ON file_analysis(path)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_hash 
                ON file_analysis(content_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_hash 
                ON project_analysis(project_hash)
            """)
            
            conn.commit()
    
    def _migrate(self, conn, from_version: int, to_version: int):
        """数据库迁移"""
        cursor = conn.cursor()
        
        # 设置版本
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('version', ?)",
            (str(to_version),)
        )
        
        logger.info(f"数据库迁移: v{from_version} -> v{to_version}")
    
    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def save_file_analysis(
        self, 
        file_path: str, 
        content: str,
        analysis: Dict[str, Any]
    ) -> int:
        """
        保存文件分析结果
        
        Args:
            file_path: 文件路径
            content: 文件内容
            analysis: 分析结果
            
        Returns:
            int: 记录 ID
        """
        content_hash = self._compute_hash(content)
        size_bytes = len(content.encode('utf-8'))
        line_count = content.count('\n') + 1
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO file_analysis 
                (path, content_hash, size_bytes, line_count, last_analyzed, analysis_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                file_path,
                content_hash,
                size_bytes,
                line_count,
                time.time(),
                json.dumps(analysis, ensure_ascii=False)
            ))
            
            conn.commit()
            
            # 获取 ID
            cursor.execute("""
                SELECT id FROM file_analysis 
                WHERE path = ? AND content_hash = ?
            """, (file_path, content_hash))
            
            row = cursor.fetchone()
            return row['id'] if row else 0
    
    def get_file_analysis(
        self, 
        file_path: str, 
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取文件分析结果（如果内容未变化）
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            Optional[Dict]: 分析结果或 None
        """
        content_hash = self._compute_hash(content)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT analysis_json, last_analyzed FROM file_analysis 
                WHERE path = ? AND content_hash = ?
            """, (file_path, content_hash))
            
            row = cursor.fetchone()
            if row:
                return {
                    'analysis': json.loads(row['analysis_json']),
                    'last_analyzed': row['last_analyzed']
                }
            return None
    
    def save_project_analysis(
        self,
        project_hash: str,
        project_name: str,
        analysis: Dict[str, Any],
        file_ids: List[int]
    ):
        """
        保存项目分析结果
        
        Args:
            project_hash: 项目哈希
            project_name: 项目名称
            analysis: 完整分析结果
            file_ids: 关联的文件 ID 列表
        """
        now = time.time()
        total_files = analysis.get('summary', {}).get('total_files', 0)
        total_lines = analysis.get('summary', {}).get('total_lines', 0)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM project_analysis WHERE project_hash = ?
            """, (project_hash,))
            
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute("""
                    UPDATE project_analysis 
                    SET project_name = ?, total_files = ?, total_lines = ?,
                        analysis_json = ?, updated_at = ?
                    WHERE project_hash = ?
                """, (
                    project_name, total_files, total_lines,
                    json.dumps(analysis, ensure_ascii=False), now, project_hash
                ))
                project_id = existing['id']
            else:
                # 插入
                cursor.execute("""
                    INSERT INTO project_analysis 
                    (project_hash, project_name, total_files, total_lines, 
                     analysis_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_hash, project_name, total_files, total_lines,
                    json.dumps(analysis, ensure_ascii=False), now, now
                ))
                project_id = cursor.lastrowid
            
            # 更新文件-项目映射
            cursor.execute("""
                DELETE FROM file_project_map WHERE project_id = ?
            """, (project_id,))
            
            for file_id in file_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO file_project_map (file_id, project_id)
                    VALUES (?, ?)
                """, (file_id, project_id))
            
            conn.commit()
    
    def get_project_analysis(self, project_hash: str) -> Optional[Dict[str, Any]]:
        """
        获取项目分析结果
        
        Args:
            project_hash: 项目哈希
            
        Returns:
            Optional[Dict]: 分析结果或 None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT analysis_json, updated_at FROM project_analysis 
                WHERE project_hash = ?
            """, (project_hash,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'analysis': json.loads(row['analysis_json']),
                    'updated_at': row['updated_at']
                }
            return None
    
    def get_changed_files(
        self,
        files: List[Tuple[str, str]]
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """
        获取变化的文件和未变化的文件
        
        Args:
            files: [(文件路径, 文件内容), ...]
            
        Returns:
            Tuple[List, List]: (变化的文件, 未变化的文件)
        """
        changed = []
        unchanged = []
        
        for path, content in files:
            content_hash = self._compute_hash(content)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM file_analysis 
                    WHERE path = ? AND content_hash = ?
                """, (path, content_hash))
                
                if cursor.fetchone():
                    unchanged.append((path, content))
                else:
                    changed.append((path, content))
        
        return changed, unchanged
    
    def get_cached_file_analyses(
        self,
        unchanged_files: List[Tuple[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取未变化文件的分析结果
        
        Args:
            unchanged_files: [(文件路径, 文件内容), ...]
            
        Returns:
            Dict[str, Dict]: {文件路径: 分析结果}
        """
        results = {}
        
        for path, content in unchanged_files:
            cached = self.get_file_analysis(path, content)
            if cached:
                results[path] = cached['analysis']
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM file_analysis")
            file_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM project_analysis")
            project_count = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT SUM(size_bytes) as total_size FROM file_analysis
            """)
            row = cursor.fetchone()
            total_size = row['total_size'] if row and row['total_size'] else 0
            
            return {
                'file_count': file_count,
                'project_count': project_count,
                'total_size_bytes': total_size,
                'db_path': self.db_path
            }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        清理旧记录
        
        Args:
            days: 保留最近多少天的记录
            
        Returns:
            int: 删除的记录数
        """
        cutoff = time.time() - (days * 24 * 60 * 60)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 删除旧的项目记录
            cursor.execute("""
                DELETE FROM project_analysis WHERE updated_at < ?
            """, (cutoff,))
            
            deleted = cursor.rowcount
            
            # 删除孤立的文件记录
            cursor.execute("""
                DELETE FROM file_analysis 
                WHERE id NOT IN (SELECT DISTINCT file_id FROM file_project_map)
            """)
            
            deleted += cursor.rowcount
            
            conn.commit()
            
            return deleted
    
    def clear_all(self):
        """清空所有记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM file_project_map")
            cursor.execute("DELETE FROM project_analysis")
            cursor.execute("DELETE FROM file_analysis")
            conn.commit()


class IncrementalAnalyzer:
    """
    增量分析器
    
    结合 Storage 和 Cache 实现增量分析：
    1. 检查哪些文件有变化
    2. 只分析变化的文件
    3. 从缓存/存储获取未变化文件的结果
    4. 合并结果
    """
    
    def __init__(self, storage: Optional[AnalysisStorage] = None):
        """
        初始化增量分析器
        
        Args:
            storage: 存储实例
        """
        self.storage = storage or AnalysisStorage()
    
    def analyze_incremental(
        self,
        files: List[Any],
        analyze_func,
        force: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        增量分析
        
        Args:
            files: 文件列表（需要有 path 和 content 属性）
            analyze_func: 分析函数，签名为 (file) -> Dict
            force: 是否强制重新分析所有文件
            
        Returns:
            Tuple[Dict, Dict]: (分析结果, 统计信息)
        """
        stats = {
            'total_files': len(files),
            'analyzed': 0,
            'cached': 0,
            'errors': 0
        }
        
        if force:
            # 强制模式：分析所有文件
            results = {}
            for file in files:
                try:
                    results[file.path] = analyze_func(file)
                    stats['analyzed'] += 1
                    
                    # 保存到存储
                    self.storage.save_file_analysis(
                        file.path, file.content, results[file.path]
                    )
                except Exception as e:
                    logger.error(f"分析文件 {file.path} 失败: {e}")
                    stats['errors'] += 1
        else:
            # 增量模式：只分析变化的文件
            file_data = [(f.path, f.content) for f in files]
            changed, unchanged = self.storage.get_changed_files(file_data)
            
            stats['cached'] = len(unchanged)
            stats['analyzed'] = len(changed)
            
            # 获取缓存结果
            results = self.storage.get_cached_file_analyses(unchanged)
            
            # 分析变化的文件
            changed_paths = {p for p, _ in changed}
            for file in files:
                if file.path in changed_paths:
                    try:
                        results[file.path] = analyze_func(file)
                        
                        # 保存到存储
                        self.storage.save_file_analysis(
                            file.path, file.content, results[file.path]
                        )
                    except Exception as e:
                        logger.error(f"分析文件 {file.path} 失败: {e}")
                        stats['errors'] += 1
        
        return results, stats


# 全局存储实例
_storage: Optional[AnalysisStorage] = None


def get_storage(db_path: Optional[str] = None) -> AnalysisStorage:
    """获取全局存储实例"""
    global _storage
    if _storage is None:
        _storage = AnalysisStorage(db_path)
    return _storage
