"""
想法 API 测试 - Phase 9 TDD
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import create_app
from src.storage import LocalStorage


@pytest.fixture
def client():
    """测试客户端 - 每个测试使用独立存储"""
    # 创建临时存储
    tmp_storage = LocalStorage(tempfile.mkdtemp())
    
    # Patch get_storage 让 ideas router 返回隔离存储
    import src.routers.ideas as ideas_module
    original_get_storage = ideas_module.get_storage
    ideas_module.get_storage = lambda: tmp_storage
    
    app = create_app()
    with TestClient(app) as c:
        yield c
    
    # 恢复
    ideas_module.get_storage = original_get_storage


class TestIdeasAPI:
    """想法 API 测试"""
    
    def test_list_ideas_empty(self, client):
        """R1: GET /api/ideas - 空列表"""
        response = client.get("/api/ideas")
        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert isinstance(data["ideas"], list)
    
    def test_create_idea(self, client):
        """R1: POST /api/ideas - 创建想法"""
        payload = {"content": "测试想法：开发一个新的App"}
        response = client.post("/api/ideas", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "idea" in data
        assert data["idea"]["content"] == payload["content"]
        assert "id" in data["idea"]
        assert data["idea"]["status"] == "NEW"
    
    def test_create_idea_with_tags(self, client):
        """R1: POST /api/ideas - 带标签创建"""
        payload = {"content": "消防演练App", "tags": ["消防", "App"]}
        response = client.post("/api/ideas", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert set(data["idea"]["tags"]) == {"消防", "App"}
    
    def test_get_idea_by_id(self, client):
        """R1: GET /api/ideas/{id} - 获取详情"""
        # 先创建一个想法
        create_resp = client.post("/api/ideas", json={"content": "测试想法详情"})
        idea_id = create_resp.json()["idea"]["id"]
        
        # 获取详情
        response = client.get(f"/api/ideas/{idea_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == idea_id
        assert data["content"] == "测试想法详情"
    
    def test_get_idea_not_found(self, client):
        """R1: GET /api/ideas/{id} - 不存在"""
        response = client.get("/api/ideas/nonexistent123")
        assert response.status_code == 404
    
    def test_update_idea(self, client):
        """R1: PUT /api/ideas/{id} - 更新想法"""
        # 创建
        create_resp = client.post("/api/ideas", json={"content": "原始内容"})
        idea_id = create_resp.json()["idea"]["id"]
        
        # 更新
        response = client.put(f"/api/ideas/{idea_id}", json={"content": "新内容", "status": "CONFIRMED"})
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "新内容"
        assert data["status"] == "CONFIRMED"
    
    def test_delete_idea(self, client):
        """R1: DELETE /api/ideas/{id} - 删除想法"""
        # 创建
        create_resp = client.post("/api/ideas", json={"content": "待删除"})
        idea_id = create_resp.json()["idea"]["id"]
        
        # 删除
        response = client.delete(f"/api/ideas/{idea_id}")
        assert response.status_code == 200
        
        # 确认已删除
        get_resp = client.get(f"/api/ideas/{idea_id}")
        assert get_resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
