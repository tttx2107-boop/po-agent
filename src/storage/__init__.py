"""
存储模块
支持 Gist、Local、SQLite 三种存储方式
"""
import os
from .base import BaseStorage, LocalStorage
from .gist_store import GistStorage
from .sqlite_storage import SQLiteStorage


def get_storage(
    token: str = None,
    gist_id: str = None,
    local_path: str = "data",
    sqlite_path: str = None
) -> BaseStorage:
    """
    获取存储实例 - 按优先级尝试

    优先级:
    1. SQLite (如果配置了 PO_STORAGE_TYPE=sqlite)
    2. GitHub Gist (如果 token 可用)
    3. LocalStorage (本地 JSON 文件)

    Args:
        token: GitHub Token
        gist_id: GitHub Gist ID
        local_path: 本地存储路径
        sqlite_path: SQLite 数据库路径

    Returns:
        存储实例
    """
    # 检查存储类型配置
    storage_type = os.environ.get("PO_STORAGE_TYPE", "").lower()

    # SQLite 存储
    if storage_type == "sqlite":
        db_path = sqlite_path or os.environ.get("PO_SQLITE_PATH", "data/po_agent.db")
        storage = SQLiteStorage(db_path)
        print("✓ 使用 SQLite 存储")
        return storage

    # 尝试 Gist 存储
    if token:
        try:
            gist = GistStorage(token, gist_id or "")
            gist.load_ideas()  # 测试连接
            print("✓ 使用 GitHub Gist 存储")
            return gist
        except Exception as e:
            print(f"⚠ GitHub Gist 连接失败 ({e})，使用本地存储")

    # LocalStorage 降级
    storage = LocalStorage(local_path)
    print("✓ 使用本地 JSON 文件存储")
    return storage


# 导出所有存储类型
__all__ = [
    "BaseStorage",
    "LocalStorage",
    "GistStorage",
    "SQLiteStorage",
    "get_storage"
]
