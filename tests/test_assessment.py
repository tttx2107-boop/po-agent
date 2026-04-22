"""测试评估服务 - TDD"""
import pytest
from src.services.quick_assessment import QuickAssessmentService
from src.services.deep_assessment import DeepAssessmentService, format_deep_report


class TestQuickAssessment:
    """快速评估测试"""
    
    @pytest.fixture
    def service(self):
        return QuickAssessmentService()
    
    def test_assess_returns_dict(self, service):
        """测试返回字典"""
        result = service.assess("测试想法")
        assert isinstance(result, dict)
    
    def test_assess_contains_required_fields(self, service):
        """测试包含必需字段"""
        result = service.assess("测试想法")
        assert "intent_type" in result
        assert "domain_tags" in result
        assert "completeness" in result
        assert "keywords_note" in result
        assert "assessment_time" in result
    
    def test_intent_type_idea(self, service):
        """测试识别为想法"""
        result = service.assess("我想做一个APP")
        assert result["intent_type"] == "idea"
    
    def test_intent_type_command(self, service):
        """测试识别为命令"""
        result = service.assess("查看想法")
        assert result["intent_type"] == "command"
    
    def test_domain_tags_fire_safety(self, service):
        """测试消防标签识别"""
        result = service.assess("做一个消防APP")
        assert "消防" in result["domain_tags"]
    
    def test_domain_tags_tech(self, service):
        """测试技术标签识别"""
        result = service.assess("开发一个AI系统")
        assert "技术" in result["domain_tags"]
    
    def test_domain_tags_side_hustle(self, service):
        """测试副业标签识别"""
        result = service.assess("做一个副业项目")
        assert "副业" in result["domain_tags"]
    
    def test_completeness_score_range(self, service):
        """测试完整性分数范围"""
        result = service.assess("测试想法")
        assert 0 <= result["completeness"] <= 1
    
    def test_completeness_longer_is_higher(self, service):
        """测试更长的想法完整性更高"""
        short = service.assess("测试")
        long = service.assess("这是一个更长的想法描述，包含了目标和预期效果")
        assert long["completeness"] >= short["completeness"]
    
    @pytest.mark.parametrize("input_text,expected_tag", [
        ("消防", "消防"),
        ("电商", "副业"),
        ("学习Python", "学习"),
        ("健康", "生活"),
    ])
    def test_tag_extraction(self, service, input_text, expected_tag):
        """参数化测试标签提取"""
        result = service.assess(input_text)
        assert expected_tag in result["domain_tags"]


class TestDeepAssessment:
    """深度评估测试"""
    
    @pytest.fixture
    def service(self):
        return DeepAssessmentService()
    
    @pytest.fixture
    def sample_idea(self):
        return {"content": "我想做一个智能消防巡检APP，结合物联网和AI技术"}
    
    def test_assess_returns_dict(self, service, sample_idea):
        """测试返回字典"""
        result = service.assess(sample_idea)
        assert isinstance(result, dict)
    
    def test_assess_contains_scores(self, service, sample_idea):
        """测试包含评分字段"""
        result = service.assess(sample_idea)
        assert "innovation_score" in result
        assert "feasibility_score" in result
        assert "value_score" in result
        assert "risk_score" in result
        assert "overall_score" in result
    
    def test_score_range_0_to_100(self, service, sample_idea):
        """测试分数范围"""
        result = service.assess(sample_idea)
        assert 0 <= result["overall_score"] <= 100
        assert 0 <= result["innovation_score"] <= 100
        assert 0 <= result["feasibility_score"] <= 100
        assert 0 <= result["value_score"] <= 100
    
    def test_decision_exists(self, service, sample_idea):
        """测试决策建议存在"""
        result = service.assess(sample_idea)
        assert "decision_level" in result
        assert "decision_action" in result
        assert "decision_reason" in result
    
    def test_innovation_keywords_increase_score(self, service):
        """测试创新关键词提升分数"""
        normal = service.assess({"content": "做一个APP"})
        innovative = service.assess({"content": "做一个全新的原创AI应用"})
        assert innovative["innovation_score"] >= normal["innovation_score"]
    
    def test_tech_keywords_increase_score(self, service):
        """测试技术关键词提升分数"""
        normal = service.assess({"content": "做一个项目"})
        tech = service.assess({"content": "做一个AI物联网项目"})
        assert tech["innovation_score"] > normal["innovation_score"]
    
    def test_format_deep_report(self, service, sample_idea):
        """测试报告格式化"""
        result = service.assess(sample_idea)
        report = format_deep_report(result, sample_idea["content"])
        
        assert "综合得分" in report
        assert "决策建议" in report
        assert "前景评估" in report
        assert "风险评估" in report


class TestAssessmentIntegration:
    """评估集成测试"""
    
    def test_quick_assessment_before_deep(self):
        """测试快速评估先于深度评估"""
        quick = QuickAssessmentService()
        deep = DeepAssessmentService()
        
        idea = {"content": "做一个消防APP"}
        
        quick_result = quick.assess(idea["content"])
        deep_result = deep.assess(idea)
        
        assert "domain_tags" in quick_result
        assert "overall_score" in deep_result
    
    def test_multiple_ideas_consistent(self):
        """测试多个想法评估一致性"""
        deep = DeepAssessmentService()
        
        ideas = [
            {"content": "做一个APP"},
            {"content": "做一个网站"},
            {"content": "做一个小程序"},
        ]
        
        scores = [deep.assess(idea)["overall_score"] for idea in ideas]
        
        # 所有分数应该在有效范围内
        assert all(0 <= s <= 100 for s in scores)
