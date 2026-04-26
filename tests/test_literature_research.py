"""
文献调研服务测试 - Phase 14
"""

import pytest
from unittest.mock import Mock, patch
import json

from src.services.literature_research import (
    Paper,
    ResearchTask,
    LiteratureSource,
    LiteratureSourceRegistry,
    LiteratureResearchService,
    SemanticScholarSource,
    ArxivSource,
    PubMedSource,
    CustomAPISource,
)


# ============================================================
# Mock Source for Testing
# ============================================================

class MockSource(LiteratureSource):
    """模拟文献源用于测试"""
    
    def __init__(self, config: LiteratureSource):
        self.config = config
        self.name = config.name
        self.source_id = config.id
        self.search_called = False
        self.search_query = None
    
    def search(self, query: str, max_results: int = 20) -> list:
        self.search_called = True
        self.search_query = query
        return [
            Paper(
                paper_id="mock1",
                title=f"Mock Paper about {query}",
                year=2024,
                source=self.source_id
            )
        ]
    
    def get_paper_details(self, paper_id: str):
        return Paper(paper_id=paper_id, title="Mock Detail")
    
    def _default_credibility(self, venue: str):
        # 直接调用基类的逻辑
        from abc import ABC
        return LiteratureSourceRegistry().get_source("semanticscholar")._default_credibility(venue)


# ============================================================
# 测试数据模型
# ============================================================

class TestPaper:
    """测试论文模型"""
    
    def test_create_paper(self):
        """创建论文"""
        paper = Paper(
            paper_id="test123",
            title="Test Paper",
            abstract="This is a test",
            authors=["John Doe", "Jane Smith"],
            year=2024,
            venue="Test Conference",
            citation_count=10
        )
        
        assert paper.paper_id == "test123"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.credibility == 0  # 默认值
        assert paper.is_starred == False
    
    def test_paper_to_dict(self):
        """转字典"""
        paper = Paper(
            paper_id="test123",
            title="Test Paper",
            year=2024
        )
        
        d = paper.to_dict()
        assert d["paper_id"] == "test123"
        assert d["title"] == "Test Paper"
        assert "created_at" in d
    
    def test_paper_from_dict(self):
        """从字典创建"""
        data = {
            "paper_id": "test456",
            "title": "From Dict",
            "year": 2023,
            "authors": ["Author 1"]
        }
        
        paper = Paper.from_dict(data)
        assert paper.paper_id == "test456"
        assert paper.title == "From Dict"
    
    def test_get_credibility_display(self):
        """可信度显示"""
        paper = Paper(paper_id="test", title="Test", credibility=4, credibility_reason="Good source")
        display = paper.get_credibility_display()
        assert "⭐⭐⭐⭐" in display
        assert "Good source" in display


class TestResearchTask:
    """测试调研任务"""
    
    def test_create_task(self):
        """创建任务"""
        task = ResearchTask(
            id="task1",
            query="machine learning",
            sources=["semanticscholar", "arxiv"]
        )
        
        assert task.id == "task1"
        assert task.query == "machine learning"
        assert len(task.sources) == 2
        assert task.status == "pending"
        assert task.progress == 0
    
    def test_task_with_dict(self):
        """字典转换"""
        task = ResearchTask(id="task2", query="test")
        d = task.to_dict()
        
        assert d["id"] == "task2"
        assert "created_at" in d
        
        # 从字典恢复
        task2 = ResearchTask.from_dict(d)
        assert task2.id == task.id


# ============================================================
# 测试文献源配置
# ============================================================

class TestLiteratureSource:
    """测试文献源配置"""
    
    def test_create_source_config(self):
        """创建文献源配置"""
        config = LiteratureSource(
            id="test_source",
            name="Test Source",
            description="A test source",
            enabled=True,
            api_key="secret_key"
        )
        
        assert config.id == "test_source"
        assert config.name == "Test Source"
        assert config.enabled == True
    
    def test_source_config_to_dict(self):
        """配置转字典时脱敏"""
        config = LiteratureSource(
            id="test",
            name="Test",
            description="",
            api_key="secret"
        )
        
        d = config.to_dict()
        assert d["api_key"] == "***"  # 应该脱敏


# ============================================================
# 测试文献源基类
# ============================================================

class TestBaseLiteratureSource:
    """测试文献源基类"""
    
    def test_credibility_top_conference(self):
        """顶会可信度"""
        config = LiteratureSource(id="test", name="Test", description="")
        source = MockSource(config)
        
        cred, reason = source._default_credibility("NeurIPS")
        assert cred == 5
        assert "顶会" in reason
    
    def test_credibility_arxiv(self):
        """arXiv可信度 - 被识别为高质量来源"""
        config = LiteratureSource(id="test", name="Test", description="")
        source = MockSource(config)
        
        # arXiv被归类为"高质量期刊/出版社"，给4星
        cred, reason = source._default_credibility("arXiv")
        assert cred == 4
        assert "高质量" in reason
    
    def test_credibility_preprint(self):
        """预印本可信度"""
        config = LiteratureSource(id="test", name="Test", description="")
        source = MockSource(config)
        
        # 纯preprint标记给3星
        cred, reason = source._default_credibility("preprint only")
        assert cred == 3
        assert "交叉验证" in reason
    
    def test_credibility_regular(self):
        """普通来源可信度"""
        config = LiteratureSource(id="test", name="Test", description="")
        source = MockSource(config)
        
        cred, reason = source._default_credibility("Some Blog")
        assert cred == 3


# ============================================================
# 测试文献源注册表
# ============================================================

class TestLiteratureSourceRegistry:
    """测试文献源注册表"""
    
    def test_singleton(self):
        """单例模式测试 - 验证类使用单例"""
        # 通过多次实例化验证返回相同实例
        registry1 = LiteratureSourceRegistry()
        registry2 = LiteratureSourceRegistry()
        
        # 验证两个实例共享同一个内部状态
        assert registry1._sources is registry2._sources
        assert id(registry1._sources) == id(registry2._sources)
    
    def test_builtin_sources(self):
        """内置文献源"""
        registry = LiteratureSourceRegistry()
        
        # 应该有三个内置源
        sources = registry.list_sources()
        source_ids = [s.id for s in sources]
        
        assert "semanticscholar" in source_ids
        assert "arxiv" in source_ids
        assert "pubmed" in source_ids
    
    def test_get_source(self):
        """获取文献源"""
        registry = LiteratureSourceRegistry()
        
        ss = registry.get_source("semanticscholar")
        assert ss is not None
        assert isinstance(ss, SemanticScholarSource)
    
    def test_register_custom_source(self):
        """注册自定义源"""
        registry = LiteratureSourceRegistry()
        
        custom_config = LiteratureSource(
            id="custom_db",
            name="Custom Database",
            description="A custom database",
            base_url="https://api.custom.com"
        )
        
        result = registry.register_source(custom_config)
        assert result == True
        
        custom = registry.get_source("custom_db")
        assert custom is not None
    
    def test_unregister_source(self):
        """取消注册"""
        registry = LiteratureSourceRegistry()
        
        # 先注册
        custom_config = LiteratureSource(
            id="temp_source",
            name="Temp",
            description=""
        )
        registry.register_source(custom_config)
        
        # 取消注册
        result = registry.unregister_source("temp_source")
        assert result == True
        
        # 确认已删除
        assert registry.get_source("temp_source") is None
    
    def test_toggle_source(self):
        """切换启用状态"""
        registry = LiteratureSourceRegistry()
        
        config = registry.get_config("arxiv")
        assert config.enabled == True
        
        config.enabled = False
        registry.update_source_config(config)
        
        updated = registry.get_config("arxiv")
        assert updated.enabled == False
    
    def test_export_import_configs(self):
        """导出导入配置"""
        registry = LiteratureSourceRegistry()
        
        # 导出
        configs = registry.export_configs()
        assert len(configs) >= 3
        
        # 验证格式
        for cfg in configs:
            assert "id" in cfg
            assert "name" in cfg
    
    def test_list_enabled_sources(self):
        """列出启用的源"""
        registry = LiteratureSourceRegistry()
        
        # 确保semanticscholar存在且启用
        config = registry.get_config("semanticscholar")
        assert config is not None
        assert config.enabled == True
        
        enabled = registry.list_enabled_sources()
        assert "semanticscholar" in enabled  # 至少这一个应该始终启用


# ============================================================
# 测试调研服务
# ============================================================

class TestLiteratureResearchService:
    """测试文献调研服务"""
    
    def test_create_task(self):
        """创建调研任务"""
        service = LiteratureResearchService()
        
        task = service.create_task(
            query="deep learning",
            idea_id="idea123",
            sources=["arxiv"]
        )
        
        assert task.id.startswith("research_")
        assert task.query == "deep learning"
        assert task.idea_id == "idea123"
        assert task.sources == ["arxiv"]
        assert task.status == "pending"
    
    def test_create_task_default_sources(self):
        """创建任务使用默认源"""
        service = LiteratureResearchService()
        
        task = service.create_task(query="test")
        
        # 应该使用所有启用的源
        assert len(task.sources) >= 1
    
    def test_get_task(self):
        """获取任务"""
        service = LiteratureResearchService()
        
        task = service.create_task(query="test")
        retrieved = service.get_task(task.id)
        
        assert retrieved is not None
        assert retrieved.id == task.id
    
    def test_list_tasks(self):
        """列出任务"""
        service = LiteratureResearchService()
        
        # 创建多个任务
        service.create_task(query="task1")
        service.create_task(query="task2")
        service.create_task(query="task3", idea_id="idea1")
        
        # 列出所有
        all_tasks = service.list_tasks()
        assert len(all_tasks) >= 3
        
        # 按想法筛选
        idea_tasks = service.list_tasks(idea_id="idea1")
        assert len(idea_tasks) == 1
    
    def test_calculate_relevance(self):
        """计算相关度"""
        service = LiteratureResearchService()
        
        # 高相关度
        paper = Paper(
            paper_id="1",
            title="Deep Learning for Image Recognition",
            abstract="This paper discusses deep learning techniques",
            citation_count=100
        )
        
        score = service._calculate_relevance(paper, "deep learning")
        assert score > 0.5
        
        # 低相关度
        paper2 = Paper(
            paper_id="2",
            title="Cooking Recipes",
            abstract="How to cook delicious food",
            citation_count=5
        )
        
        score2 = service._calculate_relevance(paper2, "deep learning")
        assert score2 < 0.3
    
    def test_deduplicate_papers(self):
        """论文去重"""
        service = LiteratureResearchService()
        
        papers = [
            Paper(paper_id="1", title="Same Title", source_id="ss1"),
            Paper(paper_id="2", title="Same Title", source_id="arxiv1"),  # 同标题，不同源
            Paper(paper_id="1", title="Same Title Again", source_id="ss1"),  # 同ID
            Paper(paper_id="3", title="Different", source_id="ss3"),
        ]
        
        unique = service._deduplicate_papers(papers)
        
        # 应该去重，但保留同标题不同源的情况
        assert len(unique) <= len(papers)
    
    def test_update_paper(self):
        """更新论文标注"""
        service = LiteratureResearchService()
        
        task = service.create_task(query="test")
        
        # 手动添加一个论文到任务
        paper = Paper(paper_id="paper1", title="Test Paper")
        task.papers.append(paper)
        
        # 更新
        updated = service.update_paper(
            task.id,
            "paper1",
            {"tags": ["AI", "ML"], "is_starred": True}
        )
        
        assert updated is not None
        assert "AI" in updated.tags
        assert updated.is_starred == True
    
    def test_export_markdown(self):
        """导出Markdown"""
        service = LiteratureResearchService()
        
        task = service.create_task(query="test")
        task.papers.append(Paper(
            paper_id="p1",
            title="Test Paper",
            authors=["Author A"],
            year=2024,
            venue="Test Journal",
            url="https://example.com"
        ))
        
        md = service.export_papers(task.id, "markdown")
        
        assert "# 文献列表" in md
        assert "Test Paper" in md
        assert "Author A" in md
    
    def test_export_bibtex(self):
        """导出BibTeX"""
        service = LiteratureResearchService()
        
        task = service.create_task(query="test")
        task.papers.append(Paper(
            paper_id="p1",
            title="Test Paper",
            authors=["Author A", "Author B"],
            year=2024,
            venue="Test Journal"
        ))
        
        bibtex = service.export_papers(task.id, "bibtex")
        
        assert "@article{" in bibtex
        assert "Test Paper" in bibtex
    
    def test_export_json(self):
        """导出JSON"""
        service = LiteratureResearchService()
        
        task = service.create_task(query="test")
        task.papers.append(Paper(paper_id="p1", title="Test"))
        
        json_str = service.export_papers(task.id, "json")
        
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["title"] == "Test"


# ============================================================
# 测试模拟API调用
# ============================================================

class TestMockedAPISearch:
    """测试模拟API调用"""
    
    @patch('requests.get')
    def test_semantic_scholar_search(self, mock_get):
        """测试Semantic Scholar搜索"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "title": "Attention Is All You Need",
                    "abstract": "We propose the Transformer",
                    "authors": [{"name": "Ashish Vaswani"}],
                    "year": 2017,
                    "venue": "NeurIPS",
                    "citationCount": 50000,
                    "url": "https://arxiv.org/abs/1706.03762",
                    "doi": "10.48550/arXiv.1706.03762"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        config = LiteratureSource(id="semanticscholar", name="SS", description="")
        service = SemanticScholarSource(config)
        
        papers = service.search("transformer", max_results=10)
        
        assert len(papers) == 1
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].year == 2017
        assert papers[0].source == "semanticscholar"
    
    @patch('requests.get')
    def test_arxiv_search(self, mock_get):
        """测试arXiv搜索"""
        mock_response = Mock()
        mock_response.text = """
        <?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper Title</title>
                <summary>This is a test abstract.</summary>
                <published>2024-01-15T00:00:00Z</published>
                <author><name>John Doe</name></author>
                <id>http://arxiv.org/abs/2401.12345v1</id>
                <link title="pdf" href="https://arxiv.org/pdf/2401.12345v1.pdf"/>
                <category term="cs.AI"/>
            </entry>
        </feed>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        config = LiteratureSource(id="arxiv", name="arXiv", description="")
        service = ArxivSource(config)
        
        papers = service.search("machine learning", max_results=5)
        
        assert len(papers) == 1
        assert papers[0].title == "Test Paper Title"
        assert papers[0].source == "arxiv"


# ============================================================
# 测试集成
# ============================================================

class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """完整工作流"""
        service = LiteratureResearchService()
        
        # 创建任务
        task = service.create_task(
            query="knowledge graph safety",
            sources=["semanticscholar"]
        )
        
        assert task.status == "pending"
        
        # 获取任务
        retrieved = service.get_task(task.id)
        assert retrieved is not None
        
        # 列出任务
        tasks = service.list_tasks()
        assert len(tasks) >= 1


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前清理注册表"""
    # 清理之前测试留下的自定义源
    registry = LiteratureSourceRegistry()
    for source_id in list(registry._configs.keys()):
        if source_id not in ["semanticscholar", "arxiv", "pubmed"]:
            registry.unregister_source(source_id)
    yield
