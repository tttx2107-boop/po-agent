"""pytest fixtures"""
import pytest
import sys
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.base import LocalStorage
from src.core.idea_manager import IdeaManager
from src.core.task_manager import TaskManager
from src.core.router import CommandRouter
from src.po_agent import PoAgent


@pytest.fixture
def test_data_dir(tmp_path):
    """临时测试数据目录"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    yield str(data_dir)
    # Cleanup after test
    shutil.rmtree(data_dir, ignore_errors=True)


@pytest.fixture
def storage(test_data_dir):
    """本地测试存储"""
    return LocalStorage(test_data_dir)


@pytest.fixture
def idea_manager(storage):
    """想法管理器"""
    return IdeaManager(storage)


@pytest.fixture
def task_manager(storage):
    """任务管理器"""
    return TaskManager(storage)


@pytest.fixture
def router():
    """命令路由"""
    return CommandRouter()


@pytest.fixture
def agent(storage):
    """完整 Agent 实例"""
    return PoAgent(storage=storage)


@pytest.fixture
def sample_ideas():
    """示例想法数据"""
    return [
        "我想做一个智能消防巡检APP，结合物联网和AI技术",
        "学习Python自动化，提高工作效率",
        "开发一个副业项目：知识付费小程序",
    ]


@pytest.fixture
def sample_idea():
    """单个示例想法"""
    return "我想做一个智能消防巡检APP"
