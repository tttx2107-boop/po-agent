"""
SQLite 存储实现
支持结构化数据存储、索引、高级查询
"""
import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .base import BaseStorage


class SQLiteStorage(BaseStorage):
    """SQLite 结构化存储"""

    def __init__(self, db_path: str = "data/po_agent.db"):
        """
        初始化 SQLite 存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_dir()
        self._init_database()

    def _ensure_dir(self):
        """确保目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 启用 WAL 模式，支持多进程
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建 ideas 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ideas (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT,
                status TEXT DEFAULT 'NEW',
                quick_assessment TEXT,
                deep_assessment TEXT,
                tasks TEXT DEFAULT '[]',
                progress INTEGER DEFAULT 0,
                reviews TEXT DEFAULT '[]',
                source TEXT DEFAULT 'cli',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建 tasks 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                idea_id TEXT,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                priority TEXT DEFAULT 'MEDIUM',
                progress INTEGER DEFAULT 0,
                subtasks TEXT DEFAULT '[]',
                dependencies TEXT DEFAULT '[]',
                execution_context TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (idea_id) REFERENCES ideas(id) ON DELETE CASCADE
            )
        """)

        # 创建 activities 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT,
                metadata TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # 创建索引
        self._create_indexes(cursor)

        conn.commit()
        conn.close()

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """创建索引"""
        # Ideas 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ideas_created_at ON ideas(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ideas_updated_at ON ideas(updated_at)")

        # Tasks 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_idea_id ON tasks(idea_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")

        # Activities 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_timestamp ON activities(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(type)")

    def _serialize(self, data: Any) -> str:
        """序列化数据为 JSON 字符串"""
        if data is None:
            return None
        return json.dumps(data, ensure_ascii=False, default=str)

    def _deserialize(self, data: str) -> Any:
        """反序列化 JSON 字符串"""
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    # ==================== Ideas CRUD ====================

    def save_ideas(self, ideas: List[Dict[str, Any]]) -> bool:
        """
        保存想法列表 (全量覆盖)

        Args:
            ideas: 想法列表

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 清空现有数据
            cursor.execute("DELETE FROM ideas")

            # 批量插入
            for idea in ideas:
                cursor.execute("""
                    INSERT OR REPLACE INTO ideas
                    (id, content, tags, status, quick_assessment, deep_assessment,
                     tasks, progress, reviews, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    idea.get("id"),
                    idea.get("content", ""),
                    self._serialize(idea.get("tags", [])),
                    idea.get("status", "NEW"),
                    self._serialize(idea.get("quick_assessment")),
                    self._serialize(idea.get("deep_assessment")),
                    self._serialize(idea.get("tasks", [])),
                    idea.get("progress", 0),
                    self._serialize(idea.get("reviews", [])),
                    idea.get("source", "cli"),
                    idea.get("created_at", datetime.now().isoformat()),
                    idea.get("updated_at", datetime.now().isoformat())
                ))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"保存想法失败: {e}")
            return False

        finally:
            conn.close()

    def load_ideas(self) -> List[Dict[str, Any]]:
        """
        加载所有想法

        Returns:
            想法列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, content, tags, status, quick_assessment, deep_assessment,
                       tasks, progress, reviews, source, created_at, updated_at
                FROM ideas
                ORDER BY created_at DESC
            """)

            ideas = []
            for row in cursor.fetchall():
                ideas.append({
                    "id": row["id"],
                    "content": row["content"],
                    "tags": self._deserialize(row["tags"]) or [],
                    "status": row["status"],
                    "quick_assessment": self._deserialize(row["quick_assessment"]),
                    "deep_assessment": self._deserialize(row["deep_assessment"]),
                    "tasks": self._deserialize(row["tasks"]) or [],
                    "progress": row["progress"],
                    "reviews": self._deserialize(row["reviews"]) or [],
                    "source": row["source"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })

            return ideas

        except Exception as e:
            print(f"加载想法失败: {e}")
            return []

        finally:
            conn.close()

    # ==================== Tasks CRUD ====================

    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """
        保存任务列表 (全量覆盖)

        Args:
            tasks: 任务列表

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM tasks")

            for task in tasks:
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks
                    (id, idea_id, content, status, priority, progress,
                     subtasks, dependencies, execution_context, created_at, updated_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.get("id"),
                    task.get("idea_id"),
                    task.get("content", ""),
                    task.get("status", "PENDING"),
                    task.get("priority", "MEDIUM"),
                    task.get("progress", 0),
                    self._serialize(task.get("subtasks", [])),
                    self._serialize(task.get("dependencies", [])),
                    self._serialize(task.get("execution_context")),
                    task.get("created_at", datetime.now().isoformat()),
                    task.get("updated_at", datetime.now().isoformat()),
                    task.get("completed_at")
                ))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"保存任务失败: {e}")
            return False

        finally:
            conn.close()

    def load_tasks(self) -> List[Dict[str, Any]]:
        """
        加载所有任务

        Returns:
            任务列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, idea_id, content, status, priority, progress,
                       subtasks, dependencies, execution_context, created_at, updated_at, completed_at
                FROM tasks
                ORDER BY created_at DESC
            """)

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row["id"],
                    "idea_id": row["idea_id"],
                    "content": row["content"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "progress": row["progress"],
                    "subtasks": self._deserialize(row["subtasks"]) or [],
                    "dependencies": self._deserialize(row["dependencies"]) or [],
                    "execution_context": self._deserialize(row["execution_context"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "completed_at": row["completed_at"]
                })

            return tasks

        except Exception as e:
            print(f"加载任务失败: {e}")
            return []

        finally:
            conn.close()

    # ==================== Activities ====================

    def append_activity(self, log: Dict[str, Any]) -> bool:
        """
        追加活动日志

        Args:
            log: 活动日志

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO activities (id, type, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                log.get("id", f"act-{datetime.now().timestamp()}"),
                log.get("type", "unknown"),
                log.get("content", ""),
                self._serialize(log.get("metadata")),
                log.get("timestamp", datetime.now().isoformat())
            ))

            # 只保留最近 1000 条
            cursor.execute("""
                DELETE FROM activities
                WHERE id NOT IN (
                    SELECT id FROM activities ORDER BY timestamp DESC LIMIT 1000
                )
            """)

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"追加活动失败: {e}")
            return False

        finally:
            conn.close()

    def load_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        加载活动日志

        Args:
            limit: 返回数量限制

        Returns:
            活动日志列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, type, content, metadata, timestamp
                FROM activities
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "id": row["id"],
                    "type": row["type"],
                    "content": row["content"],
                    "metadata": self._deserialize(row["metadata"]),
                    "timestamp": row["timestamp"]
                })

            return activities

        except Exception as e:
            print(f"加载活动失败: {e}")
            return []

        finally:
            conn.close()

    # ==================== 高级查询 ====================

    def query_ideas(
        self,
        status: str = None,
        tags: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        高级查询想法

        Args:
            status: 按状态筛选
            tags: 按标签筛选 (OR 逻辑)
            start_date: 开始日期 (ISO 格式)
            end_date: 结束日期 (ISO 格式)
            page: 页码 (从 1 开始)
            page_size: 每页数量

        Returns:
            想法列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 构建 WHERE 条件
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status)

            if tags:
                tag_conditions = " OR ".join(["tags LIKE ?"] * len(tags))
                conditions.append(f"({tag_conditions})")
                params.extend([f'%"{tag}"%' for tag in tags])

            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 计算总数
            count_sql = f"SELECT COUNT(*) as total FROM ideas WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"""
                SELECT id, content, tags, status, quick_assessment, deep_assessment,
                       tasks, progress, reviews, source, created_at, updated_at
                FROM ideas
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])

            cursor.execute(sql, params)

            ideas = []
            for row in cursor.fetchall():
                ideas.append({
                    "id": row["id"],
                    "content": row["content"],
                    "tags": self._deserialize(row["tags"]) or [],
                    "status": row["status"],
                    "quick_assessment": self._deserialize(row["quick_assessment"]),
                    "deep_assessment": self._deserialize(row["deep_assessment"]),
                    "tasks": self._deserialize(row["tasks"]) or [],
                    "progress": row["progress"],
                    "reviews": self._deserialize(row["reviews"]) or [],
                    "source": row["source"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })

            return ideas

        except Exception as e:
            print(f"查询想法失败: {e}")
            return []

        finally:
            conn.close()

    def query_tasks(
        self,
        idea_id: str = None,
        status: str = None,
        priority: str = None
    ) -> List[Dict[str, Any]]:
        """
        高级查询任务

        Args:
            idea_id: 按想法 ID 筛选
            status: 按状态筛选
            priority: 按优先级筛选

        Returns:
            任务列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            conditions = []
            params = []

            if idea_id:
                conditions.append("idea_id = ?")
                params.append(idea_id)

            if status:
                conditions.append("status = ?")
                params.append(status)

            if priority:
                conditions.append("priority = ?")
                params.append(priority)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(f"""
                SELECT id, idea_id, content, status, priority, progress,
                       subtasks, dependencies, execution_context, created_at, updated_at, completed_at
                FROM tasks
                WHERE {where_clause}
                ORDER BY created_at DESC
            """, params)

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row["id"],
                    "idea_id": row["idea_id"],
                    "content": row["content"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "progress": row["progress"],
                    "subtasks": self._deserialize(row["subtasks"]) or [],
                    "dependencies": self._deserialize(row["dependencies"]) or [],
                    "execution_context": self._deserialize(row["execution_context"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "completed_at": row["completed_at"]
                })

            return tasks

        except Exception as e:
            print(f"查询任务失败: {e}")
            return []

        finally:
            conn.close()

    # ==================== 数据迁移 ====================

    def migrate_from_json(self, json_dir: str) -> bool:
        """
        从 JSON 文件迁移数据

        Args:
            json_dir: JSON 文件目录

        Returns:
            是否成功
        """
        json_path = Path(json_dir)

        try:
            # 迁移 ideas
            ideas_file = json_path / "ideas.json"
            if ideas_file.exists():
                with open(ideas_file, "r", encoding="utf-8") as f:
                    ideas = json.load(f)
                self.save_ideas(ideas)

            # 迁移 tasks
            tasks_file = json_path / "tasks.json"
            if tasks_file.exists():
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                self.save_tasks(tasks)

            # 迁移 activities
            activities_file = json_path / "activities.json"
            if activities_file.exists():
                with open(activities_file, "r", encoding="utf-8") as f:
                    activities = json.load(f)
                # 清空后批量插入
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM activities")
                for act in activities:
                    cursor.execute("""
                        INSERT INTO activities (id, type, content, metadata, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        act.get("id", f"act-{datetime.now().timestamp()}"),
                        act.get("type", "unknown"),
                        act.get("content", ""),
                        self._serialize(act.get("metadata")),
                        act.get("timestamp", datetime.now().isoformat())
                    ))
                conn.commit()
                conn.close()

            print(f"✓ 从 {json_dir} 迁移完成")
            return True

        except Exception as e:
            print(f"迁移失败: {e}")
            return False

    def migrate_from_gist(self, token: str, gist_id: str) -> bool:
        """
        从 GitHub Gist 迁移数据

        Args:
            token: GitHub Token
            gist_id: Gist ID

        Returns:
            是否成功
        """
        from .gist_store import GistStorage

        try:
            gist = GistStorage(token, gist_id)

            # 迁移 ideas
            ideas = gist.load_ideas()
            if ideas:
                self.save_ideas(ideas)

            # 迁移 tasks
            tasks = gist.load_tasks()
            if tasks:
                self.save_tasks(tasks)

            # 迁移 activities
            activities = gist.load_activities(limit=1000)
            if activities:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM activities")
                for act in activities:
                    cursor.execute("""
                        INSERT INTO activities (id, type, content, metadata, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        act.get("id", f"act-{datetime.now().timestamp()}"),
                        act.get("type", "unknown"),
                        act.get("content", ""),
                        self._serialize(act.get("metadata")),
                        act.get("timestamp", datetime.now().isoformat())
                    ))
                conn.commit()
                conn.close()

            print(f"✓ 从 Gist {gist_id} 迁移完成")
            return True

        except Exception as e:
            print(f"Gist 迁移失败: {e}")
            return False

    # ==================== 工具方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            统计信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            stats = {}

            # Ideas 统计
            cursor.execute("SELECT COUNT(*) as total, status FROM ideas GROUP BY status")
            stats["ideas"] = {"total": 0, "by_status": {}}
            for row in cursor.fetchall():
                stats["ideas"]["total"] += row["total"]
                stats["ideas"]["by_status"][row["status"]] = row["total"]

            # Tasks 统计
            cursor.execute("SELECT COUNT(*) as total, status FROM tasks GROUP BY status")
            stats["tasks"] = {"total": 0, "by_status": {}}
            for row in cursor.fetchall():
                stats["tasks"]["total"] += row["total"]
                stats["tasks"]["by_status"][row["status"]] = row["total"]

            # Activities 统计
            cursor.execute("SELECT COUNT(*) as total FROM activities")
            stats["activities"] = {"total": cursor.fetchone()["total"]}

            return stats

        except Exception as e:
            print(f"获取统计失败: {e}")
            return {}

        finally:
            conn.close()

    def backup(self, backup_path: str = None) -> str:
        """
        备份数据库

        Args:
            backup_path: 备份文件路径，默认加时间戳

        Returns:
            备份文件路径
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}.db"

        import shutil
        shutil.copy2(self.db_path, backup_path)

        print(f"✓ 备份已保存: {backup_path}")
        return backup_path

    def vacuum(self):
        """清理数据库碎片"""
        conn = self._get_connection()
        try:
            conn.execute("VACUUM")
            print("✓ 数据库清理完成")
        finally:
            conn.close()
