"""
记忆增强服务 - 基于 SQLite + FTS5 的语义搜索
支持长期记忆存储、语义检索、上下文关联
"""
import sqlite3
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import os


class MemoryType(Enum):
    """记忆类型"""
    EPISODIC = "episodic"      # 情景记忆 - 事件/经历
    SEMANTIC = "semantic"      # 语义记忆 - 知识/概念
    PROCEDURAL = "procedural"  # 程序记忆 - 技能/流程
    WORKING = "working"        # 工作记忆 - 临时上下文


class MemoryImportance(Enum):
    """记忆重要性"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    memory_type: str = MemoryType.SEMANTIC.value
    importance: int = MemoryImportance.NORMAL.value
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: str = ""                    # 上下文/来源
    access_count: int = 0               # 访问次数
    last_accessed: str = ""              # 最后访问时间
    created_at: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{self.content}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata,
            "context": self.context,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at
        }


@dataclass
class MemorySearchResult:
    """记忆搜索结果"""
    memory: MemoryEntry
    relevance_score: float = 0.0
    matched_terms: List[str] = field(default_factory=list)


class MemoryService:
    """
    记忆增强服务
    
    功能：
    1. 持久化存储 - SQLite + FTS5 全文搜索
    2. 语义检索 - 支持关键词和语义相似度搜索
    3. 上下文关联 - 自动关联相关记忆
    4. 遗忘机制 - 基于访问频率和重要性自动清理
    5. 记忆强化 - 重要记忆定期复习
    """
    
    def __init__(self, db_path: str = "data/memory.db"):
        """
        初始化记忆服务
        
        Args:
            db_path: 记忆数据库路径
        """
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()
    
    def _ensure_dir(self):
        """确保目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    
    def _init_db(self):
        """初始化数据库"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建主记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'semantic',
                importance INTEGER DEFAULT 2,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                context TEXT DEFAULT '',
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 创建 FTS5 全文搜索虚拟表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                tags,
                content='memories',
                content_rowid='rowid'
            )
        """)
        
        # 创建关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                link_type TEXT DEFAULT 'related',
                strength REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_id)")
        
        # 触发器：自动更新 FTS
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, tags) VALUES (new.rowid, new.content, new.tags);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, tags) VALUES('delete', old.rowid, old.content, old.tags);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, tags) VALUES('delete', old.rowid, old.content, old.tags);
                INSERT INTO memories_fts(rowid, content, tags) VALUES (new.rowid, new.content, new.tags);
            END
        """)
        
        conn.commit()
        conn.close()
    
    def _serialize(self, data: Any) -> str:
        """序列化数据"""
        if data is None:
            return None
        return json.dumps(data, ensure_ascii=False, default=str)
    
    def _deserialize(self, data: str) -> Any:
        """反序列化数据"""
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    
    # ==================== 基础 CRUD ====================
    
    def add_memory(
        self,
        content: str,
        memory_type: str = MemoryType.SEMANTIC.value,
        importance: int = MemoryImportance.NORMAL.value,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        context: str = ""
    ) -> MemoryEntry:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性 (1-4)
            tags: 标签
            metadata: 元数据
            context: 上下文来源
            
        Returns:
            创建的记忆条目
        """
        tags = tags or []
        metadata = metadata or {}
        
        memory = MemoryEntry(
            id="",
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            metadata=metadata,
            context=context
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO memories (id, content, memory_type, importance, tags, metadata, context, access_count, last_accessed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.content,
                memory.memory_type,
                memory.importance,
                self._serialize(memory.tags),
                self._serialize(memory.metadata),
                memory.context,
                memory.access_count,
                memory.last_accessed,
                memory.created_at
            ))
            
            conn.commit()
            return memory
            
        finally:
            conn.close()
    
    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """获取单个记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_memory(row)
            return None
            
        finally:
            conn.close()
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """更新记忆"""
        allowed_fields = {"content", "memory_type", "importance", "tags", "metadata", "context"}
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if "tags" in updates:
            updates["tags"] = self._serialize(updates["tags"])
        if "metadata" in updates:
            updates["metadata"] = self._serialize(updates["metadata"])
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [memory_id]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"UPDATE memories SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def _row_to_memory(self, row: sqlite3.Row) -> MemoryEntry:
        """行转记忆对象"""
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            memory_type=row["memory_type"],
            importance=row["importance"],
            tags=self._deserialize(row["tags"]) or [],
            metadata=self._deserialize(row["metadata"]) or {},
            context=row["context"] or "",
            access_count=row["access_count"],
            last_accessed=row["last_accessed"],
            created_at=row["created_at"]
        )
    
    # ==================== 搜索功能 ====================
    
    def search(
        self,
        query: str,
        memory_type: str = None,
        tags: List[str] = None,
        limit: int = 20,
        include_related: bool = True
    ) -> List[MemorySearchResult]:
        """
        搜索记忆
        
        Args:
            query: 搜索关键词
            memory_type: 按类型筛选
            tags: 按标签筛选
            limit: 返回数量
            include_related: 是否包含关联记忆
            
        Returns:
            搜索结果列表
        """
        results = []
        seen_ids = set()
        
        # 1. FTS5 全文搜索
        fts_results = self._fts_search(query, limit)
        for rowid, rank in fts_results:
            memory = self._get_memory_by_rowid(rowid)
            if memory and memory.id not in seen_ids:
                seen_ids.add(memory.id)
                results.append(MemorySearchResult(
                    memory=memory,
                    relevance_score=1.0 / (1.0 + rank),
                    matched_terms=[query]
                ))
        
        # 2. 标签精确匹配提升
        if tags:
            tag_results = self._tag_search(tags, limit)
            for memory in tag_results:
                if memory.id not in seen_ids:
                    seen_ids.add(memory.id)
                    results.append(MemorySearchResult(
                        memory=memory,
                        relevance_score=0.9,
                        matched_terms=tags
                    ))
        
        # 3. 类型过滤
        if memory_type:
            results = [r for r in results if r.memory.memory_type == memory_type]
        
        # 4. 按相关性排序
        results.sort(key=lambda x: (x.relevance_score, x.memory.importance), reverse=True)
        
        return results[:limit]
    
    def _fts_search(self, query: str, limit: int) -> List[Tuple[int, float]]:
        """FTS5 全文搜索"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 使用 BM25 排名
            cursor.execute("""
                SELECT rowid, bm25(memories_fts) as rank
                FROM memories_fts
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            return [(row["rowid"], row["rank"]) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def _tag_search(self, tags: List[str], limit: int) -> List[MemoryEntry]:
        """标签搜索"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            params = [f'%"{tag}"%' for tag in tags]
            
            cursor.execute(f"""
                SELECT * FROM memories
                WHERE {conditions}
                ORDER BY importance DESC, access_count DESC
                LIMIT ?
            """, params + [limit])
            
            return [self._row_to_memory(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def _get_memory_by_rowid(self, rowid: int) -> Optional[MemoryEntry]:
        """通过行号获取记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM memories WHERE rowid = ?", (rowid,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_memory(row)
            return None
            
        finally:
            conn.close()
    
    def semantic_search(
        self,
        query: str,
        limit: int = 10
    ) -> List[MemorySearchResult]:
        """
        语义搜索（基于关键词扩展）
        
        Args:
            query: 搜索查询
            limit: 返回数量
            
        Returns:
            搜索结果
        """
        # 简单的语义扩展
        expansions = self._expand_query(query)
        all_results = []
        seen_ids = set()
        
        for expanded_query in expansions:
            results = self.search(expanded_query, limit=limit)
            for result in results:
                if result.memory.id not in seen_ids:
                    seen_ids.add(result.memory.id)
                    all_results.append(result)
        
        # 去重并排序
        all_results.sort(key=lambda x: (x.relevance_score, x.memory.importance), reverse=True)
        return all_results[:limit]
    
    def _expand_query(self, query: str) -> List[str]:
        """查询扩展"""
        expansions = [query]
        
        # 中文同义词简化版
        synonyms = {
            "学习": ["学", "掌握", "了解", "研究"],
            "工作": ["任务", "项目", "上班", "办公"],
            "编程": ["代码", "开发", "写代码", "coding"],
            "旅行": ["旅游", "游玩", "出游", "trip"],
            "健康": ["健身", "运动", "锻炼", "body"],
            "读书": ["阅读", "看书", "学习"],
        }
        
        words = query.lower()
        for base, syns in synonyms.items():
            if base in words:
                expansions.extend(syns)
            for syn in syns:
                if syn in words:
                    expansions.append(base)
        
        return list(set(expansions))
    
    # ==================== 关联管理 ====================
    
    def link_memories(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "related",
        strength: float = 0.5
    ) -> bool:
        """
        关联两条记忆
        
        Args:
            source_id: 源记忆ID
            target_id: 目标记忆ID
            link_type: 关联类型 (related/causes/depends_on)
            strength: 关联强度 (0-1)
            
        Returns:
            是否成功
        """
        if source_id == target_id:
            return False
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO memory_links (source_id, target_id, link_type, strength, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (source_id, target_id, link_type, strength, datetime.now().isoformat()))
            
            conn.commit()
            return True
            
        finally:
            conn.close()
    
    def get_related_memories(
        self,
        memory_id: str,
        link_type: str = None,
        limit: int = 10
    ) -> List[MemorySearchResult]:
        """获取关联记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if link_type:
                cursor.execute("""
                    SELECT m.*, l.strength, l.link_type
                    FROM memories m
                    JOIN memory_links l ON m.id = l.target_id
                    WHERE l.source_id = ? AND l.link_type = ?
                    ORDER BY l.strength DESC
                    LIMIT ?
                """, (memory_id, link_type, limit))
            else:
                cursor.execute("""
                    SELECT m.*, l.strength, l.link_type
                    FROM memories m
                    JOIN memory_links l ON m.id = l.target_id
                    WHERE l.source_id = ?
                    ORDER BY l.strength DESC
                    LIMIT ?
                """, (memory_id, limit))
            
            results = []
            for row in cursor.fetchall():
                memory = self._row_to_memory(row)
                results.append(MemorySearchResult(
                    memory=memory,
                    relevance_score=row["strength"],
                    matched_terms=[row["link_type"]]
                ))
            
            return results
            
        finally:
            conn.close()
    
    # ==================== 访问与强化 ====================
    
    def access_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """访问记忆（更新访问计数）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))
            
            conn.commit()
            
            return self.get_memory(memory_id)
            
        finally:
            conn.close()
    
    def reinforce_memory(self, memory_id: str, delta_importance: int = 1) -> bool:
        """强化记忆（提升重要性）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE memories 
                SET importance = MIN(importance + ?, 4)
                WHERE id = ?
            """, (delta_importance, memory_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    # ==================== 遗忘机制 ====================
    
    def cleanup_old_memories(
        self,
        days: int = 90,
        min_importance: int = MemoryImportance.HIGH.value
    ) -> int:
        """
        清理旧记忆
        
        保留策略：
        1. 高重要性记忆永久保留
        2. 低访问频率的记忆更容易被清理
        3. 情景记忆有更短的保留期
        
        Args:
            days: 保留天数
            min_importance: 最低重要性（低于此值才清理）
            
        Returns:
            清理的记忆数量
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 删除低重要性且久未访问的记忆
            cursor.execute("""
                DELETE FROM memories
                WHERE importance < ?
                AND created_at < ?
                AND access_count < 3
                AND memory_type != 'critical'
            """, (min_importance, cutoff_date))
            
            deleted = cursor.rowcount
            conn.commit()
            
            return deleted
            
        finally:
            conn.close()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 总数
            cursor.execute("SELECT COUNT(*) as count FROM memories")
            stats["total"] = cursor.fetchone()["count"]
            
            # 按类型统计
            cursor.execute("""
                SELECT memory_type, COUNT(*) as count 
                FROM memories GROUP BY memory_type
            """)
            stats["by_type"] = {row["memory_type"]: row["count"] for row in cursor.fetchall()}
            
            # 按重要性统计
            cursor.execute("""
                SELECT importance, COUNT(*) as count 
                FROM memories GROUP BY importance
            """)
            stats["by_importance"] = {row["importance"]: row["count"] for row in cursor.fetchall()}
            
            # 访问统计
            cursor.execute("SELECT SUM(access_count) as total_access FROM memories")
            stats["total_access"] = cursor.fetchone()["total_access"] or 0
            
            return stats
            
        finally:
            conn.close()
    
    # ==================== 批量操作 ====================
    
    def import_memories(self, memories: List[Dict[str, Any]]) -> int:
        """批量导入记忆"""
        count = 0
        for data in memories:
            try:
                self.add_memory(
                    content=data.get("content", ""),
                    memory_type=data.get("memory_type", MemoryType.SEMANTIC.value),
                    importance=data.get("importance", MemoryImportance.NORMAL.value),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                    context=data.get("context", "")
                )
                count += 1
            except Exception:
                continue
        
        return count
    
    def export_memories(
        self,
        memory_type: str = None,
        since: str = None
    ) -> List[Dict[str, Any]]:
        """导出记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            conditions = []
            params = []
            
            if memory_type:
                conditions.append("memory_type = ?")
                params.append(memory_type)
            
            if since:
                conditions.append("created_at >= ?")
                params.append(since)
            
            where = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC", params)
            
            return [self._row_to_memory(row).to_dict() for row in cursor.fetchall()]
            
        finally:
            conn.close()
