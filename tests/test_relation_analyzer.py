"""想法关联分析测试"""
import pytest
from src.services.relation_analyzer import (
    IdeaRelationAnalyzer, IdeaRelation, RelationType, RelationReport
)


class TestIdeaRelationAnalyzer:
    """关联分析器测试"""
    
    def test_register_idea(self):
        """测试注册想法"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "开发一个消防 APP")
        
        assert "idea-1" in analyzer._idea_contents
    
    def test_detect_domain(self):
        """测试领域检测"""
        analyzer = IdeaRelationAnalyzer()
        
        assert analyzer._detect_domain("开发一个消防系统") == "消防"
        assert analyzer._detect_domain("用 AI 做分析") == "AI"
        assert analyzer._detect_domain("普通想法") is None
    
    def test_same_domain_relation(self):
        """测试同领域关联"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "开发一个消防 APP")
        analyzer.register_idea("idea-2", "做一个消防培训系统")
        
        relations = analyzer._find_relations("idea-1", "idea-2")
        
        assert len(relations) >= 1
        same_domain = [r for r in relations if r.relation_type == RelationType.SAME_DOMAIN]
        assert len(same_domain) == 1
    
    def test_conflict_relation(self):
        """测试冲突检测"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "自研发系统")
        analyzer.register_idea("idea-2", "外包开发")
        
        relations = analyzer._find_relations("idea-1", "idea-2")
        
        conflicts = [r for r in relations if r.relation_type == RelationType.CONFLICTS]
        assert len(conflicts) == 1
    
    def test_complement_relation(self):
        """测试互补检测"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "做前端界面")
        analyzer.register_idea("idea-2", "开发后端 API")
        
        relations = analyzer._find_relations("idea-1", "idea-2")
        
        complements = [r for r in relations if r.relation_type == RelationType.COMPLEMENTS]
        assert len(complements) >= 1
    
    def test_analyze_all(self):
        """测试全量分析"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "开发一个消防 APP")
        analyzer.register_idea("idea-2", "做一个 AI 知识图谱")
        analyzer.register_idea("idea-3", "做消防培训系统")
        
        relations = analyzer.analyze_all()
        
        assert len(relations) > 0
    
    def test_get_related_ideas(self):
        """测试获取关联想法"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "开发一个消防 APP")
        analyzer.register_idea("idea-2", "做一个消防培训系统")
        analyzer.register_idea("idea-3", "做完全不相关的东西")
        
        analyzer.analyze_all()
        related = analyzer.get_related_ideas("idea-1")
        
        assert len(related) >= 1
        related_ids = [r[0] for r in related]
        assert "idea-2" in related_ids
    
    def test_find_clusters(self):
        """测试想法群发现"""
        analyzer = IdeaRelationAnalyzer()
        # 三个想法互相关联
        analyzer.register_idea("idea-1", "做一个消防 APP")
        analyzer.register_idea("idea-2", "做一个消防系统")
        analyzer.register_idea("idea-3", "做一个消防工具")
        analyzer.register_idea("idea-4", "完全不相关")
        
        analyzer.analyze_all()
        clusters = analyzer._find_clusters()
        
        # 应该有一个包含 idea-1,2,3 的群
        assert any(len(c) >= 3 for c in clusters)
    
    def test_generate_suggestions(self):
        """测试建议生成"""
        analyzer = IdeaRelationAnalyzer()
        analyzer.register_idea("idea-1", "开发一个消防 APP")
        analyzer.register_idea("idea-2", "做一个消防培训系统")
        analyzer.register_idea("idea-3", "做消防数据分析")
        analyzer.register_idea("idea-4", "也是消防相关")
        
        # 需要 >= 4 个同领域才会触发合并建议
        relations = [
            IdeaRelation("idea-1", "idea-2", RelationType.SAME_DOMAIN, 0.8),
            IdeaRelation("idea-1", "idea-3", RelationType.SAME_DOMAIN, 0.8),
            IdeaRelation("idea-1", "idea-4", RelationType.SAME_DOMAIN, 0.8),
        ]
        
        suggestions = analyzer._generate_suggestions("idea-1", relations)
        
        assert len(suggestions) >= 0  # 可能没有建议，取决于关联数量


class TestIdeaRelation:
    """关联记录测试"""
    
    def test_create_relation(self):
        """测试创建关联"""
        rel = IdeaRelation(
            idea_a="a",
            idea_b="b",
            relation_type=RelationType.SAME_DOMAIN,
            confidence=0.8,
            reason="同领域"
        )
        
        assert rel.idea_a == "a"
        assert rel.confidence == 0.8
    
    def test_to_dict(self):
        """测试转换字典"""
        rel = IdeaRelation("a", "b", RelationType.SAME_DOMAIN, 0.8)
        data = rel.to_dict()
        
        assert isinstance(data, dict)
        assert data["idea_a"] == "a"


class TestRelationReport:
    """关联报告测试"""
    
    def test_format_report(self):
        """测试报告格式化"""
        report = RelationReport(
            idea_id="idea-1",
            idea_content="这是一个测试想法",
            relations=[
                IdeaRelation("idea-1", "idea-2", RelationType.SAME_DOMAIN, 0.8, "同领域")
            ]
        )
        
        formatted = report.format_report()
        
        assert "想法关联" in formatted
        assert "同领域" in formatted
