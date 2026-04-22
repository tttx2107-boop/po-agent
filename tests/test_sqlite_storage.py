"""
SQLite 存储测试 - TDD 阶段
先写测试，再实现功能
"""
import pytest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试数据
SAMPLE_IDEAS = [
    {
        "id": "test-001",
        "content": "开发一个博客系统",
        "tags": ["编程", "Web"],
        "status": "NEW",
        "quick_assessment": {"completeness": 0.6, "domain_tags": ["编程"]},
        "deep_assessment": None,
        "created_at": "2024-01-01T10:00:00",
        "updated_at": "2024-01-01T10:00:00"
    },
    {
        "id": "test-002",
        "content": "学习机器学习",
        "tags": ["AI", "学习"],
        "status": "CONFIRMED",
        "quick_assessment": {"completeness": 0.8, "domain_tags": ["AI"]},
        "deep_assessment": {"overall_score": 85},
        "created_at": "2024-01-02T10:00:00",
        "updated_at": "2024-01-02T10:00:00"
    }
]

SAMPLE_TASKS = [
    {
        "id": "task-001",
        "idea_id": "test-001",
        "content": "设计数据库架构",
        "status": "PENDING",
        "priority": "HIGH",
        "progress": 0,
        "created_at": "2024-01-01T11:00:00",
        "updated_at": "2024-01-01T11:00:00"
    },
    {
        "id": "task-002",
        "idea_id": "test-001",
        "content": "开发后端API",
        "status": "IN_PROGRESS",
        "priority": "MEDIUM",
        "progress": 50,
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00"
    }
]

SAMPLE_ACTIVITIES = [
    {
        "id": "act-001",
        "type": "idea_created",
        "content": "创建想法: 开发博客系统",
        "timestamp": "2024-01-01T10:00:00"
    },
    {
        "id": "act-002",
        "type": "assessment_completed",
        "content": "完成深度评估",
        "timestamp": "2024-01-02T10:00:00"
    }
]


class TestSQLiteStorageInit:
    """R1: SQLiteStorage 初始化测试"""
    
    def test_storage_init_creates_database(self, tmp_path):
        """AC1: 创建数据库文件"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        assert db_path.exists(), "数据库文件应该被创建"
    
    def test_storage_init_creates_tables(self, tmp_path):
        """AC1: 创建数据表"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        # 检查表是否存在
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('ideas', 'tasks', 'activities')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "ideas" in tables, "ideas 表应该存在"
        assert "tasks" in tables, "tasks 表应该存在"
        assert "activities" in tables, "activities 表应该存在"
        
        conn.close()
    
    def test_storage_init_creates_indexes(self, tmp_path):
        """R1: 创建索引"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert len(indexes) > 0, "应该创建索引"
        
        conn.close()


class TestSQLiteStorageIdeasCRUD:
    """R1: 想法 CRUD 测试"""
    
    def test_save_ideas(self, tmp_path):
        """AC2: 保存想法"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        result = storage.save_ideas(SAMPLE_IDEAS)
        
        assert result is True, "保存应该成功"
    
    def test_load_ideas(self, tmp_path):
        """AC2: 加载想法"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.save_ideas(SAMPLE_IDEAS)
        loaded = storage.load_ideas()
        
        assert len(loaded) == 2, "应该加载2条想法"
        # 由于 ORDER BY created_at DESC，最新的在前
        assert loaded[0]["id"] == "test-002"  # 第二条更新
        assert loaded[1]["id"] == "test-001"
    
    def test_save_load_preserves_all_fields(self, tmp_path):
        """AC2: 保存加载保留所有字段"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.save_ideas(SAMPLE_IDEAS)
        loaded = storage.load_ideas()
        
        # 由于 ORDER BY DESC，按 ID 排序检查
        original = SAMPLE_IDEAS[0]
        # 找对应的记录
        loaded_first = next((i for i in loaded if i["id"] == "test-001"), None)
        
        assert loaded_first is not None
        assert loaded_first["id"] == original["id"]
        assert loaded_first["content"] == original["content"]
        assert loaded_first["tags"] == original["tags"]
        assert loaded_first["status"] == original["status"]
        assert loaded_first["quick_assessment"] == original["quick_assessment"]
    
    def test_save_empty_ideas(self, tmp_path):
        """边界: 保存空列表"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        result = storage.save_ideas([])
        
        assert result is True
        assert storage.load_ideas() == []


class TestSQLiteStorageTasksCRUD:
    """R1: 任务 CRUD 测试"""
    
    def test_save_load_tasks(self, tmp_path):
        """AC2: 保存和加载任务"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.save_tasks(SAMPLE_TASKS)
        loaded = storage.load_tasks()
        
        assert len(loaded) == 2
        # ORDER BY updated_at DESC，最新的在前
        assert loaded[0]["id"] == "task-002"
        assert loaded[1]["id"] == "task-001"
        assert loaded[0]["idea_id"] == "test-001"


class TestSQLiteStorageActivities:
    """R1: 活动日志测试"""
    
    def test_append_activity(self, tmp_path):
        """AC2: 追加活动日志"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.append_activity(SAMPLE_ACTIVITIES[0])
        storage.append_activity(SAMPLE_ACTIVITIES[1])
        
        loaded = storage.load_activities()
        
        assert len(loaded) == 2
        # ORDER BY created_at DESC，最新的在前
        assert loaded[0]["type"] == "assessment_completed"
        assert loaded[1]["type"] == "idea_created"
    
    def test_load_activities_with_limit(self, tmp_path):
        """R1: 带限制加载活动"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        for i in range(10):
            storage.append_activity({
                "id": f"act-{i}",
                "type": "test",
                "content": f"Activity {i}",
                "timestamp": datetime.now().isoformat()
            })
        
        loaded = storage.load_activities(limit=5)
        
        assert len(loaded) == 5


class TestSQLiteStorageAdvancedQueries:
    """R3: 高级查询测试"""
    
    def test_query_by_status(self, tmp_path):
        """AC4: 按状态查询"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.save_ideas(SAMPLE_IDEAS)
        
        confirmed = storage.query_ideas(status="CONFIRMED")
        assert len(confirmed) == 1
        assert confirmed[0]["status"] == "CONFIRMED"
        
        new_ones = storage.query_ideas(status="NEW")
        assert len(new_ones) == 1
        assert new_ones[0]["status"] == "NEW"
    
    def test_query_by_tag(self, tmp_path):
        """AC4: 按标签查询"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.save_ideas(SAMPLE_IDEAS)
        
        ai_ideas = storage.query_ideas(tags=["AI"])
        assert len(ai_ideas) == 1
        assert "AI" in ai_ideas[0]["tags"]
    
    def test_query_by_status_and_tag(self, tmp_path):
        """R3: 组合查询"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.save_ideas(SAMPLE_IDEAS)
        
        results = storage.query_ideas(status="CONFIRMED", tags=["AI"])
        assert len(results) == 1
    
    def test_query_pagination(self, tmp_path):
        """R3: 分页查询"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        
        # 创建多条想法
        ideas = [
            {"id": f"idea-{i}", "content": f"想法 {i}", "status": "NEW",
             "tags": [], "quick_assessment": None, "deep_assessment": None,
             "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}
            for i in range(15)
        ]
        storage.save_ideas(ideas)
        
        page1 = storage.query_ideas(page=1, page_size=5)
        assert len(page1) == 5
        
        page2 = storage.query_ideas(page=2, page_size=5)
        assert len(page2) == 5
        
        page3 = storage.query_ideas(page=3, page_size=5)
        assert len(page3) == 5


class TestSQLiteStorageMigration:
    """R2: 数据迁移测试"""
    
    def test_migrate_from_json(self, tmp_path):
        """AC3: 从 JSON 迁移"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        # 创建 JSON 文件
        json_dir = tmp_path / "json_data"
        json_dir.mkdir()
        
        (json_dir / "ideas.json").write_text(json.dumps(SAMPLE_IDEAS))
        (json_dir / "tasks.json").write_text(json.dumps(SAMPLE_TASKS))
        (json_dir / "activities.json").write_text(json.dumps(SAMPLE_ACTIVITIES))
        
        # 创建 SQLite 存储
        db_path = tmp_path / "migrated.db"
        storage = SQLiteStorage(str(db_path))
        
        # 执行迁移
        result = storage.migrate_from_json(str(json_dir))
        
        assert result is True
        
        # 验证数据
        loaded_ideas = storage.load_ideas()
        assert len(loaded_ideas) == 2
        
        loaded_tasks = storage.load_tasks()
        assert len(loaded_tasks) == 2
    
    def test_migrate_preserves_all_data(self, tmp_path):
        """AC3: 迁移保留所有数据"""
        from src.storage.sqlite_storage import SQLiteStorage
        
        json_dir = tmp_path / "json_data"
        json_dir.mkdir()
        
        (json_dir / "ideas.json").write_text(json.dumps(SAMPLE_IDEAS))
        (json_dir / "tasks.json").write_text(json.dumps(SAMPLE_TASKS))
        
        db_path = tmp_path / "migrated.db"
        storage = SQLiteStorage(str(db_path))
        
        storage.migrate_from_json(str(json_dir))
        
        # 验证每条数据的每个字段
        loaded_ideas = storage.load_ideas()
        
        # 按 ID 排序后比较
        orig_sorted = sorted(SAMPLE_IDEAS, key=lambda x: x["id"])
        loaded_sorted = sorted(loaded_ideas, key=lambda x: x["id"])
        
        for orig, loaded in zip(orig_sorted, loaded_sorted):
            for key in orig:
                assert orig[key] == loaded.get(key), f"字段 {key} 不匹配: {orig[key]} != {loaded.get(key)}"


class TestSQLiteStorageBackwardCompatibility:
    """R4: 向后兼容测试"""
    
    def test_get_storage_creates_sqlite(self, tmp_path, monkeypatch):
        """AC5: get_storage 支持 SQLite"""
        # 设置环境变量
        monkeypatch.setenv("PO_STORAGE_TYPE", "sqlite")
        monkeypatch.setenv("PO_SQLITE_PATH", str(tmp_path / "test.db"))
        
        from src.storage import get_storage
        
        storage = get_storage(token="dummy", gist_id="dummy")
        
        # 应该返回 SQLiteStorage
        assert storage.__class__.__name__ == "SQLiteStorage"
    
    def test_get_storage_gist_fallback(self, monkeypatch):
        """R4: Gist 不可用时降级（无 token 且无 SQLite 配置时）"""
        # 确保无 token 且无 SQLite
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.delenv("PO_STORAGE_TYPE", raising=False)
        
        from src.storage import get_storage
        
        storage = get_storage(token="", gist_id="dummy")
        
        # 应该返回 LocalStorage (因为没有 token 且没有 sqlite 配置)
        assert storage.__class__.__name__ == "LocalStorage"


class TestSQLiteStorageIntegration:
    """集成测试"""
    
    def test_idea_manager_with_sqlite(self, tmp_path, monkeypatch):
        """AC5: 与 IdeaManager 集成"""
        monkeypatch.setenv("PO_STORAGE_TYPE", "sqlite")
        monkeypatch.setenv("PO_SQLITE_PATH", str(tmp_path / "test.db"))
        
        from src.storage import get_storage
        from src.core.idea_manager import IdeaManager
        
        storage = get_storage(token="", gist_id="")
        manager = IdeaManager(storage)
        
        # 创建想法
        idea = manager.create("测试想法内容")
        
        assert idea is not None
        assert idea.content == "测试想法内容"
        
        # 加载想法
        ideas = manager.list()
        assert len(ideas) == 1
        
        # 获取单个想法
        fetched = manager.get(idea.id)
        assert fetched is not None
        assert fetched.id == idea.id


# ==================== Pytest Fixtures ====================

@pytest.fixture
def tmp_path(tmp_path_factory):
    """创建临时目录"""
    return tmp_path_factory.mktemp("sqlite_test")


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
