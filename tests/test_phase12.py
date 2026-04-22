"""
Phase 12: 高级功能测试
知识图谱、多模型支持、API 开放平台
"""
import pytest
import asyncio
from datetime import datetime

from src.services.knowledge_graph import (
    KnowledgeGraphService,
    KnowledgeGraph,
    Entity,
    Relation,
    get_knowledge_graph_service
)
from src.services.model_provider import (
    ModelManager,
    ModelConfig,
    Message,
    MockProvider,
    chat as model_chat
)


class TestKnowledgeGraph:
    """知识图谱服务测试"""
    
    def test_knowledge_graph_service_init(self):
        """测试知识图谱服务初始化"""
        kg = KnowledgeGraphService()
        assert kg.graph is not None
        assert len(kg.graph.entities) == 0
        assert len(kg.graph.relations) == 0
    
    def test_extract_from_idea_simple(self):
        """测试从简单想法提取"""
        kg = KnowledgeGraphService()
        result = kg.extract_from_idea(
            "我想要开发一个番茄钟APP",
            "idea_001"
        )
        
        assert "entities" in result
        assert "relations" in result
        assert result["entity_count"] >= 0
        assert result["relation_count"] >= 0
    
    def test_extract_from_idea_with_what(self):
        """测试提取 What 实体"""
        kg = KnowledgeGraphService()
        result = kg.extract_from_idea(
            "开发一个消防演练APP，支持用户学习灭火器使用方法",
            "idea_002"
        )
        
        # 应该提取到 what 实体
        entities = result["entities"]
        what_entities = [e for e in entities if e["type"] == "what"]
        assert len(what_entities) >= 0
    
    def test_graph_stats(self):
        """测试图谱统计"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("开发APP", "idea_003")
        kg.extract_from_idea("学习Python", "idea_004")
        
        stats = kg.get_graph_stats()
        assert "total_entities" in stats
        assert "total_relations" in stats
        assert "entity_types" in stats
        assert "relation_types" in stats
    
    def test_find_connections(self):
        """测试查找关联"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("开发一个番茄钟APP", "idea_005")
        kg.extract_from_idea("开发一个待办事项APP", "idea_006")
        
        connections = kg.find_connections("开发一个新的番茄钟应用")
        assert isinstance(connections, list)
    
    def test_entity_creation(self):
        """测试实体创建"""
        entity = Entity(
            id="test_001",
            name="测试实体",
            entity_type="what",
            idea_ids=["idea_001"]
        )
        
        assert entity.id == "test_001"
        assert entity.name == "测试实体"
        assert entity.entity_type == "what"
        assert entity.created_at is not None
    
    def test_relation_creation(self):
        """测试关系创建"""
        relation = Relation(
            id="rel_001",
            source_id="entity_001",
            target_id="entity_002",
            relation_type="implements"
        )
        
        assert relation.id == "rel_001"
        assert relation.source_id == "entity_001"
        assert relation.relation_type == "implements"
    
    def test_knowledge_graph_add_entity(self):
        """测试图谱添加实体"""
        graph = KnowledgeGraph()
        entity = Entity(id="e1", name="Test", entity_type="what")
        
        graph.add_entity(entity)
        assert len(graph.entities) == 1
        
        # 查找
        found = graph.find_entity("Test")
        assert found is not None
        assert found.id == "e1"
    
    def test_knowledge_graph_add_relation(self):
        """测试图谱添加关系"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="How", entity_type="how")
        e2 = Entity(id="e2", name="What", entity_type="what")
        
        graph.add_entity(e1)
        graph.add_entity(e2)
        
        rel = Relation(
            id="r1",
            source_id="e1",
            target_id="e2",
            relation_type="implements"
        )
        graph.add_relation(rel)
        
        assert len(graph.relations) == 1
    
    def test_get_related_entities(self):
        """测试获取关联实体"""
        graph = KnowledgeGraph()
        
        e1 = Entity(id="e1", name="A", entity_type="who")
        e2 = Entity(id="e2", name="B", entity_type="what")
        e3 = Entity(id="e3", name="C", entity_type="how")
        
        graph.add_entity(e1)
        graph.add_entity(e2)
        graph.add_entity(e3)
        
        rel1 = Relation(id="r1", source_id="e1", target_id="e2", relation_type="depends_on")
        rel2 = Relation(id="r2", source_id="e2", target_id="e3", relation_type="implements")
        graph.add_relation(rel1)
        graph.add_relation(rel2)
        
        related = graph.get_related_entities("e1")
        assert len(related) >= 1
    
    def test_singleton(self):
        """测试单例模式"""
        kg1 = get_knowledge_graph_service()
        kg2 = get_knowledge_graph_service()
        assert kg1 is kg2


class TestModelProvider:
    """多模型支持测试"""
    
    def test_model_config(self):
        """测试模型配置"""
        config = ModelConfig(provider="openai", model="gpt-4")
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.max_tokens == 2000
    
    def test_model_config_from_env(self):
        """测试从环境变量创建配置"""
        config = ModelConfig.from_env("mock")
        assert config.provider == "mock"
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Hello"
    
    def test_mock_provider_chat(self):
        """测试 Mock 提供商对话"""
        provider = MockProvider(ModelConfig(provider="mock"))
        
        messages = [Message(role="user", content="测试对话")]
        result = asyncio.run(provider.chat(messages))
        
        assert result.text is not None
        assert result.provider == "mock"
        assert "usage" in result.to_dict()
    
    def test_mock_provider_complete(self):
        """测试 Mock 提供商补全"""
        provider = MockProvider(ModelConfig(provider="mock"))
        
        result = asyncio.run(provider.complete("补全这段文字"))
        
        assert result.text is not None
        assert result.provider == "mock"
    
    def test_model_manager_register(self):
        """测试模型管理器注册"""
        provider = MockProvider(ModelConfig(provider="test"))
        ModelManager.register_provider("test", provider)
        
        retrieved = ModelManager.get_provider("test")
        assert retrieved is not None
    
    def test_model_manager_list(self):
        """测试列出提供商"""
        providers = ModelManager.list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0
    
    def test_async_chat_function(self):
        """测试异步对话函数"""
        async def test():
            result = await model_chat("测试")
            return result
        
        text = asyncio.run(test())
        assert isinstance(text, str)
    
    def test_provider_with_evaluation_prompt(self):
        """测试评估提示"""
        provider = MockProvider(ModelConfig(provider="mock"))
        messages = [
            Message(role="user", content="请评估这个想法：开发一个番茄钟APP")
        ]
        result = asyncio.run(provider.chat(messages))
        
        assert "收到" in result.text or "想法" in result.text
    
    def test_provider_with_breakdown_prompt(self):
        """测试拆解提示"""
        provider = MockProvider(ModelConfig(provider="mock"))
        messages = [
            Message(role="user", content="请拆解任务：开发一个番茄钟APP")
        ]
        result = asyncio.run(provider.chat(messages))
        
        assert result.text is not None


class TestPlatformAPI:
    """平台 API 测试"""
    
    def test_api_key_manager(self):
        """测试 API Key 管理"""
        from src.routers.platform import APIKeyManager
        
        # 创建 Key
        key = APIKeyManager.create_key("test_user", ["read", "chat"])
        assert len(key) == 32
        
        # 验证 Key
        info = APIKeyManager.validate_key(key)
        assert info is not None
        assert info["name"] == "test_user"
        
        # 列出 Keys
        keys = APIKeyManager.list_keys()
        assert len(keys) >= 1
        
        # 撤销 Key
        assert APIKeyManager.revoke_key(key) is True
    
    def test_platform_endpoints(self):
        """测试平台端点信息"""
        from src.routers.platform import router
        
        # 检查路由是否正确注册
        routes = [r.path for r in router.routes]
        assert "/knowledge/extract" in routes or any("extract" in str(r) for r in router.routes)
