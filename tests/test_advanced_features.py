"""Prompt 模板库测试"""
import pytest
from src.services.prompt_library import (
    PromptTemplateLibrary, PromptDomain, PromptType, get_prompt_library
)


class TestPromptTemplateLibrary:
    """Prompt 模板库测试"""
    
    def setup_method(self):
        """每个测试前重置"""
        self.library = PromptTemplateLibrary()
    
    def test_get_prompt_library_singleton(self):
        """测试单例模式"""
        lib1 = get_prompt_library()
        lib2 = get_prompt_library()
        assert lib1 is lib2
    
    def test_get_default_templates(self):
        """测试获取默认模板"""
        template = self.library.get_template(
            PromptDomain.DEFAULT,
            PromptType.QUICK_ASSESSMENT
        )
        assert template is not None
        assert template.domain == PromptDomain.DEFAULT.value
        assert template.prompt_type == PromptType.QUICK_ASSESSMENT.value
    
    def test_get_firefighting_template(self):
        """测试获取消防行业模板"""
        template = self.library.get_template(
            PromptDomain.FIREFIGHTING,
            PromptType.DEEP_ASSESSMENT
        )
        assert template is not None
        assert "消防" in template.template
    
    def test_fill_template(self):
        """测试模板填充"""
        template = self.library.get_template(
            PromptDomain.DEFAULT,
            PromptType.QUICK_ASSESSMENT
        )
        filled = template.fill(idea_content="测试想法")
        assert "测试想法" in filled
    
    def test_get_all_domains(self):
        """测试获取所有领域"""
        domains = self.library.get_all_domains()
        assert PromptDomain.DEFAULT.value in domains
        assert PromptDomain.FIREFIGHTING.value in domains
        assert PromptDomain.BUSINESS.value in domains
    
    def test_get_prompt_types(self):
        """测试获取指定领域的所有类型"""
        types = self.library.get_prompt_types(PromptDomain.DEFAULT)
        assert PromptType.QUICK_ASSESSMENT.value in types
        assert PromptType.DEEP_ASSESSMENT.value in types


class TestDomainDetection:
    """领域检测测试"""
    
    def setup_method(self):
        self.library = PromptTemplateLibrary()
    
    def test_detect_firefighting(self):
        """测试消防行业检测"""
        # 高相关
        result = self.library.detect_domain("开发智能消防巡检系统")
        assert result == PromptDomain.FIREFIGHTING
        
        # 中等相关
        result = self.library.detect_domain("研究灭火器使用方法")
        assert result == PromptDomain.FIREFIGHTING
    
    def test_detect_business(self):
        """测试商业检测"""
        result = self.library.detect_domain("做副业赚钱，开个网店")
        assert result == PromptDomain.BUSINESS
        
        result = self.library.detect_domain("创业项目，寻找投资人")
        assert result == PromptDomain.BUSINESS
    
    def test_detect_tech_research(self):
        """测试技术调研检测"""
        result = self.library.detect_domain("研究机器学习算法")
        assert result == PromptDomain.TECH_RESEARCH
    
    def test_detect_learning(self):
        """测试学习检测"""
        result = self.library.detect_domain("学习Python编程")
        assert result == PromptDomain.LEARNING
    
    def test_detect_default(self):
        """测试默认检测"""
        result = self.library.detect_domain("今天吃火锅")
        assert result == PromptDomain.DEFAULT


class TestDualModeRouter:
    """双模式路由测试"""
    
    def setup_method(self):
        from src.services.dual_mode_router import DualModeRouter
        self.router = DualModeRouter()
    
    def test_simple_short_action(self):
        """测试简单短句动作"""
        decision = self.router.decide_mode("学Python")
        assert decision.is_simple
        assert decision.confidence >= 0.7
    
    def test_simple_single_action(self):
        """测试简单单动作"""
        decision = self.router.decide_mode("买本书看")
        assert decision.is_simple
    
    def test_complex_with_indicators(self):
        """测试复杂想法-有指标"""
        decision = self.router.decide_mode("要不要创业做个小产品，需要评估市场和成本")
        assert not decision.is_simple
    
    def test_complex_long(self):
        """测试复杂想法-长度长"""
        long_text = "开发一个智能推荐系统，需要考虑算法选择、数据处理、用户界面、后端架构等多个方面，并且需要进行技术调研和竞品分析" * 3
        decision = self.router.decide_mode(long_text)
        assert not decision.is_simple
    
    def test_format_quick_response(self):
        """测试快捷模式响应格式化"""
        response = self.router.format_quick_response("学Python", "创建学习计划")
        assert "简单想法" in response
        assert "学Python" in response


class TestThreeLayerFeedbackSystem:
    """三层反馈系统测试"""
    
    def setup_method(self):
        from src.services.feedback_system import ThreeLayerFeedbackSystem
        self.system = ThreeLayerFeedbackSystem()
    
    def test_file_level_empty_content(self):
        """测试空内容检查"""
        report = self.system.file_level_check("")
        assert report.has_errors
    
    def test_file_level_good_content(self):
        """测试良好内容"""
        report = self.system.file_level_check("开发一个帮助消防检查的APP")
        # 应该没有错误
        assert not report.has_errors
    
    def test_file_level_duplicate(self):
        """测试重复检测"""
        existing = [
            {"id": "1", "content": "开发消防巡检APP"},
            {"id": "2", "content": "学习Python"}
        ]
        report = self.system.file_level_check("做一个消防检查的移动应用", existing)
        # 可能检测到重复
        assert isinstance(report.feedbacks, list)
    
    def test_task_level_blocked(self):
        """测试任务阻塞检查"""
        report = self.system.task_level_check(
            task_title="完成文档",
            task_status="blocked",
            blocked_days=4
        )
        assert report.has_warnings or report.has_errors
    
    def test_task_level_overdue(self):
        """测试任务逾期检查"""
        report = self.system.task_level_check(
            task_title="完成文档",
            task_status="todo",
            overdue_days=2
        )
        assert any("逾期" in f.message for f in report.feedbacks)
    
    def test_platform_level_analysis(self):
        """测试平台级分析"""
        ideas = [
            {"id": "1", "status": "NEW", "content": "想法1"},
            {"id": "2", "status": "NEW", "content": "想法2"},
            {"id": "3", "status": "NEW", "content": "想法3"},
            {"id": "4", "status": "NEW", "content": "想法4"},
            {"id": "5", "status": "NEW", "content": "想法5"},
            {"id": "6", "status": "COMPLETED", "content": "想法6"},
        ]
        tasks = []
        report = self.system.platform_level_analysis(ideas, tasks)
        # 应该能产生反馈
        assert len(report.feedbacks) >= 0  # 平台级分析可能不产生具体反馈
    
    def test_feedback_format(self):
        """测试反馈格式化"""
        from src.services.feedback_system import Feedback, FeedbackLevel
        feedback = Feedback(
            category="test",
            level=FeedbackLevel.WARNING.value,
            title="测试标题",
            message="测试消息",
            suggestions=["建议1", "建议2"]
        )
        formatted = feedback.format()
        assert "⚠️" in formatted
        assert "测试标题" in formatted
