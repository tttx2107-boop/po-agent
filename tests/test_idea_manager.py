"""测试想法管理器 - TDD RED阶段"""
import pytest
from src.models.idea import Idea


class TestIdeaModel:
    """想法模型测试"""
    
    def test_idea_creation(self):
        """测试想法创建"""
        idea = Idea(
            id="test-001",
            content="测试想法",
            created_at="2026-04-22T10:00:00"
        )
        assert idea.id == "test-001"
        assert idea.content == "测试想法"
        assert idea.status == "NEW"
    
    def test_idea_default_values(self):
        """测试默认值"""
        idea = Idea(
            id="test-002",
            content="测试"
        )
        assert idea.source == "cli"
        assert idea.status == "NEW"
        assert idea.tags == []
        assert idea.progress == 0
    
    def test_idea_status_display(self):
        """测试状态显示"""
        idea = Idea(id="1", content="test", created_at="2026-04-22")
        assert "新想法" in idea.get_status_display()
        
        idea.status = "COMPLETED"
        assert "已完成" in idea.get_status_display()
    
    def test_idea_is_pending(self):
        """测试是否待评估"""
        idea = Idea(id="1", content="test", created_at="2026-04-22")
        assert idea.is_pending_assessment() is True
        
        idea.status = "CONFIRMED"
        assert idea.is_pending_assessment() is False
    
    def test_idea_to_dict(self):
        """测试转字典"""
        idea = Idea(id="1", content="test", created_at="2026-04-22")
        data = idea.to_dict()
        assert data["id"] == "1"
        assert data["content"] == "test"
        assert "created_at" in data


class TestIdeaManager:
    """想法管理器测试"""
    
    def test_create_idea(self, idea_manager, sample_idea):
        """测试创建想法"""
        idea = idea_manager.create(sample_idea)
        
        assert idea is not None
        assert idea.content == sample_idea
        assert idea.status == "NEW"
        assert idea.id is not None
        assert len(idea.id) == 8  # UUID 前8位
    
    def test_create_idea_with_tags(self, idea_manager):
        """测试创建带标签的想法"""
        content = "我想做一个消防APP"
        idea = idea_manager.create(content)
        
        assert "消防" in idea.tags
    
    def test_list_ideas(self, idea_manager, sample_ideas):
        """测试列出想法"""
        # 创建多个想法
        for content in sample_ideas:
            idea_manager.create(content)
        
        ideas = idea_manager.list()
        assert len(ideas) == 3
    
    def test_list_ideas_by_status(self, idea_manager, sample_ideas):
        """测试按状态筛选"""
        idea_manager.create(sample_ideas[0])
        idea = idea_manager.create(sample_ideas[1])
        idea_manager.update_status(idea.id, "CONFIRMED")
        
        pending = idea_manager.list(status="NEW")
        confirmed = idea_manager.list(status="CONFIRMED")
        
        assert len(pending) == 1
        assert len(confirmed) == 1
    
    def test_get_idea(self, idea_manager, sample_idea):
        """测试获取单个想法"""
        created = idea_manager.create(sample_idea)
        
        retrieved = idea_manager.get(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.content == sample_idea
    
    def test_get_nonexistent_idea(self, idea_manager):
        """测试获取不存在的想法"""
        result = idea_manager.get("nonexistent-id")
        assert result is None
    
    def test_update_idea(self, idea_manager, sample_idea):
        """测试更新想法"""
        idea = idea_manager.create(sample_idea)
        
        updated = idea_manager.update(idea.id, {"notes": "测试备注"})
        
        assert updated is not None
        assert updated.notes == "测试备注"
    
    def test_update_status(self, idea_manager, sample_idea):
        """测试更新状态"""
        idea = idea_manager.create(sample_idea)
        
        idea_manager.update_status(idea.id, "CONFIRMED")
        
        updated = idea_manager.get(idea.id)
        assert updated.status == "CONFIRMED"
    
    def test_delete_idea(self, idea_manager, sample_idea):
        """测试删除想法"""
        idea = idea_manager.create(sample_idea)
        
        result = idea_manager.delete(idea.id)
        
        assert result is True
        assert idea_manager.get(idea.id) is None
    
    def test_search_ideas(self, idea_manager, sample_ideas):
        """测试搜索想法"""
        idea_manager.create(sample_ideas[0])
        idea_manager.create(sample_ideas[1])
        
        results = idea_manager.search("消防")
        
        assert len(results) >= 1
        assert any("消防" in idea.content for idea in results)
    
    def test_get_pending_assessment(self, idea_manager, sample_ideas):
        """测试获取待评估想法"""
        idea_manager.create(sample_ideas[0])
        idea2 = idea_manager.create(sample_ideas[1])
        idea_manager.assess(idea2.id)  # 评估后状态会变
        
        pending = idea_manager.get_pending_assessment()
        
        assert len(pending) >= 1
        for idea in pending:
            assert idea.is_pending_assessment() is True
    
    def test_get_stats(self, idea_manager, sample_ideas):
        """测试统计"""
        for content in sample_ideas:
            idea_manager.create(content)
        
        stats = idea_manager.get_stats()
        
        assert stats["total"] == 3
        assert stats["pending_assessment"] == 3
        assert "by_status" in stats
        assert "by_tag" in stats
    
    def test_should_trigger_assessment(self, idea_manager, sample_ideas):
        """测试评估触发条件"""
        # 少于5个，不触发
        for i in range(3):
            idea_manager.create(sample_ideas[i % len(sample_ideas)])
        
        assert idea_manager.should_trigger_assessment(5) is False
        
        # 达到5个，触发
        idea_manager.create(sample_ideas[0])
        idea_manager.create(sample_ideas[1])
        
        assert idea_manager.should_trigger_assessment(5) is True
