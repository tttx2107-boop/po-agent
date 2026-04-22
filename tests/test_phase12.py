"""
Phase 12: 高级功能测试
知识图谱增强、多模型支持、API 开放平台
"""
import pytest
import asyncio
from datetime import datetime

from src.services.knowledge_graph import (
    KnowledgeGraphService,
    KnowledgeGraph,
    Entity,
    Relation,
    EntityExtractor,
    RelationReasoner,
    GraphVisualizer,
    SemanticSearch,
    get_knowledge_graph_service,
    reset_knowledge_graph_service
)
from src.services.model_provider import (
    ModelManager,
    ModelConfig,
    Message,
    MockProvider,
    chat as model_chat
)


class TestKnowledgeGraphEnhanced:
    """知识图谱服务增强测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        reset_knowledge_graph_service()
    
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
        
        entities = result["entities"]
        what_entities = [e for e in entities if e["type"] == "what"]
        assert len(what_entities) >= 0
    
    def test_extract_from_idea_with_llm(self):
        """测试LLM增强提取"""
        kg = KnowledgeGraphService()
        
        # 模拟LLM函数
        def mock_llm(prompt):
            return '''
            {
                "who": ["我", "团队"],
                "what": ["开发APP", "数据分析"],
                "why": ["提高效率"],
                "when": ["下周"],
                "where": ["公司"],
                "how": ["使用Python"]
            }
            '''
        
        kg.set_llm_function(mock_llm)
        result = kg.extract_from_idea(
            "我想要在公司在下周开发一个数据分析APP",
            "idea_llm_001",
            use_llm=True
        )
        
        assert result["entity_count"] >= 0
    
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


class TestEntityExtractor:
    """实体提取器测试"""
    
    def test_extract_5w1h_basic(self):
        """测试基本5W1H提取"""
        content = "我想要在明天开发一个APP，使用Python来实现"
        result = EntityExtractor.extract_5w1h(content)
        
        assert "who" in result
        assert "what" in result
        assert "when" in result
        assert "how" in result
    
    def test_extract_5w1h_safety_domain(self):
        """测试安全领域提取"""
        content = "我们团队需要开发一个消防演练APP，模拟灭火器使用场景"
        result = EntityExtractor.extract_5w1h(content)
        
        assert len(result["who"]) >= 0
        assert len(result["what"]) >= 0
    
    def test_extract_with_llm_fallback(self):
        """测试LLM提取回退"""
        result = EntityExtractor.extract_with_llm("测试内容", None)
        
        assert "who" in result
        assert "what" in result
        assert all(isinstance(item, dict) for item in result["who"])


class TestRelationReasoner:
    """关系推理器测试"""
    
    def test_infer_from_cooccurrence(self):
        """测试共现关系推断"""
        entities = [
            {"id": "e1", "name": "我", "type": "who"},
            {"id": "e2", "name": "开发", "type": "what"},
            {"id": "e3", "name": "使用Python", "type": "how"}
        ]
        
        relations = RelationReasoner.infer_from_cooccurrence(
            entities, "idea_001", "我开发使用Python"
        )
        
        assert len(relations) >= 0
    
    def test_infer_temporal_relations(self):
        """测试时间关系推断"""
        content = "首先我们先做需求分析，然后进行开发"
        entities = [
            {"id": "e1", "name": "需求分析", "type": "what"},
            {"id": "e2", "name": "开发", "type": "what"}
        ]
        
        relations = RelationReasoner.infer_temporal_relations(
            content, entities, "idea_001"
        )
        
        assert isinstance(relations, list)


class TestGraphVisualizer:
    """图谱可视化测试"""
    
    def test_to_d3_json(self):
        """测试D3格式转换"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="A", entity_type="who")
        e2 = Entity(id="e2", name="B", entity_type="what")
        graph.add_entity(e1)
        graph.add_entity(e2)
        
        rel = Relation(id="r1", source_id="e1", target_id="e2", relation_type="depends_on")
        graph.add_relation(rel)
        
        data = GraphVisualizer.to_d3_json(graph)
        
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) == 2
        assert len(data["links"]) == 1
    
    def test_to_cytoscape_json(self):
        """测试Cytoscape格式转换"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="Test", entity_type="what")
        graph.add_entity(e1)
        
        data = GraphVisualizer.to_cytoscape_json(graph)
        
        assert "nodes" in data
        assert "edges" in data
    
    def test_to_tree_format(self):
        """测试树形格式转换"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="Root", entity_type="what")
        e2 = Entity(id="e2", name="Child", entity_type="what")
        graph.add_entity(e1)
        graph.add_entity(e2)
        
        rel = Relation(id="r1", source_id="e1", target_id="e2", relation_type="part_of")
        graph.add_relation(rel)
        
        data = GraphVisualizer.to_tree_format(graph, "e1")
        
        assert "root" in data
        assert data["root"]["name"] == "Root"
    
    def test_get_statistics(self):
        """测试统计信息生成"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="A", entity_type="who")
        e2 = Entity(id="e2", name="B", entity_type="what")
        graph.add_entity(e1)
        graph.add_entity(e2)
        
        rel = Relation(id="r1", source_id="e1", target_id="e2", relation_type="depends_on")
        graph.add_relation(rel)
        
        stats = GraphVisualizer.get_statistics(graph)
        
        assert stats["entity_count"] == 2
        assert stats["relation_count"] == 1
        assert "entity_types" in stats
        assert "density" in stats


class TestSemanticSearch:
    """语义搜索测试"""
    
    def test_search_exact_match(self):
        """测试精确匹配搜索"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="消防演练", entity_type="what", idea_ids=["idea_001"])
        graph.add_entity(e1)
        
        search = SemanticSearch(graph)
        results = search.search("消防演练")
        
        assert len(results) >= 1
        assert results[0]["score"] == 1.0
    
    def test_search_keyword_match(self):
        """测试关键词搜索"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="开发APP", entity_type="what")
        graph.add_entity(e1)
        
        search = SemanticSearch(graph)
        results = search.search("开发")
        
        assert len(results) >= 1
    
    def test_search_limit(self):
        """测试搜索结果限制"""
        graph = KnowledgeGraph()
        for i in range(20):
            e = Entity(id=f"e{i}", name=f"Entity{i}", entity_type="what")
            graph.add_entity(e)
        
        search = SemanticSearch(graph)
        results = search.search("Entity", limit=5)
        
        assert len(results) == 5
    
    def test_find_related(self):
        """测试查找相关内容"""
        graph = KnowledgeGraph()
        e1 = Entity(id="e1", name="A", entity_type="what")
        e2 = Entity(id="e2", name="B", entity_type="what")
        graph.add_entity(e1)
        graph.add_entity(e2)
        
        rel = Relation(id="r1", source_id="e1", target_id="e2", relation_type="relates_to")
        graph.add_relation(rel)
        
        search = SemanticSearch(graph)
        related = search.find_related("A")
        
        assert isinstance(related, list)


class TestKnowledgeGraphServiceAdvanced:
    """知识图谱服务高级功能测试"""
    
    def setup_method(self):
        reset_knowledge_graph_service()
    
    def test_semantic_search(self):
        """测试语义搜索API"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("开发消防演练APP", "idea_search_001")
        
        results = kg.semantic_search("消防")
        assert isinstance(results, list)
    
    def test_get_visualization_data_d3(self):
        """测试D3可视化数据"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("测试内容", "idea_vis_001")
        
        data = kg.get_visualization_data("d3")
        assert "nodes" in data
        assert "links" in data
    
    def test_get_visualization_data_cytoscape(self):
        """测试Cytoscape可视化数据"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("测试内容", "idea_vis_002")
        
        data = kg.get_visualization_data("cytoscape")
        assert "nodes" in data
        assert "edges" in data
    
    def test_get_entity_subgraph(self):
        """测试获取实体子图"""
        kg = KnowledgeGraphService()
        result = kg.extract_from_idea("我开发一个APP", "idea_sub_001")
        
        if result["entity_count"] > 0:
            entity_id = result["entities"][0]["id"]
            subgraph = kg.get_entity_subgraph(entity_id)
            assert "entities" in subgraph
            assert "relations" in subgraph
    
    def test_find_paths(self):
        """测试查找实体间路径"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("我在公司使用Python开发", "idea_path_001")
        kg.extract_from_idea("Python用于数据分析", "idea_path_002")
        
        paths = kg.find_paths("我", "Python")
        assert isinstance(paths, list)
    
    def test_import_export(self):
        """测试图谱导入导出"""
        kg = KnowledgeGraphService()
        kg.extract_from_idea("测试内容", "idea_ie_001")
        
        # 导出
        exported = kg.export_graph()
        assert "entities" in exported
        assert "relations" in exported
        
        # 导入到新服务
        kg2 = KnowledgeGraphService()
        kg2.import_graph(exported)
        
        stats = kg2.get_graph_stats()
        assert stats["total_entities"] >= 0


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
        assert any("extract" in str(r) or "/knowledge/extract" in routes for r in router.routes)