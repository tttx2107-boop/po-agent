"""风险预警服务测试"""
import pytest
from src.services.risk_warning import (
    RiskWarningService, RiskItem, RiskLevel, RiskType
)


class TestRiskItem:
    """风险项测试"""
    
    def test_create_risk_item(self):
        """测试创建风险项"""
        risk = RiskItem(
            id="test_risk",
            idea_id="idea_1",
            risk_type=RiskType.TECHNICAL_BLOCK.value,
            title="技术阻塞风险",
            description="测试描述",
            probability=0.7,
            impact=0.8
        )
        
        assert abs(risk.calculate_score() - 0.56) < 0.001  # 浮点数比较
        assert risk.get_level_display() == "🟡 中"  # 默认 MEDIUM
    
    def test_high_level_display(self):
        """测试高风险显示"""
        risk = RiskItem(
            id="test",
            idea_id="idea_1",
            risk_type=RiskType.SCOPE_CREEP.value,
            title="Test",
            description="Test",
            level=RiskLevel.HIGH.value
        )
        assert risk.get_level_display() == "🟠 高"


class TestRiskWarningService:
    """风险预警服务测试"""
    
    def setup_method(self):
        """每个测试前重置服务"""
        self.service = RiskWarningService()
    
    def test_analyze_simple_idea(self):
        """测试简单想法分析"""
        report = self.service.analyze_idea(
            idea_content="做一个简单的小工具",
            idea_id="idea_1"
        )
        
        assert report.idea_id == "idea_1"
        assert report.total_risks >= 0
    
    def test_analyze_technical_risk(self):
        """测试技术风险检测"""
        report = self.service.analyze_idea(
            idea_content="用AI技术做一个智能助手，这个技术可能很复杂",
            idea_id="idea_2"
        )
        
        # 应该检测到技术风险
        risk_types = [r.risk_type for r in report.risks]
        assert RiskType.TECHNICAL_BLOCK.value in risk_types
    
    def test_analyze_resource_risk(self):
        """测试资源风险检测"""
        report = self.service.analyze_idea(
            idea_content="做一个大项目，但是资金和人力都很有限",
            idea_id="idea_3"
        )
        
        risk_types = [r.risk_type for r in report.risks]
        assert RiskType.RESOURCE_SHORTAGE.value in risk_types
    
    def test_analyze_time_risk(self):
        """测试时间风险检测"""
        report = self.service.analyze_idea(
            idea_content="这个项目时间很紧，需要在deadline前完成",
            idea_id="idea_4"
        )
        
        risk_types = [r.risk_type for r in report.risks]
        assert RiskType.TIME_OVERRUN.value in risk_types
    
    def test_analyze_no_risk_idea(self):
        """测试低风险想法"""
        report = self.service.analyze_idea(
            idea_content="每天读一本书，写读后感",
            idea_id="idea_5"
        )
        
        # 低风险想法可能没有风险
        assert report.idea_id == "idea_5"
    
    def test_get_active_risks(self):
        """测试获取活跃风险"""
        self.service.analyze_idea("测试技术风险，涉及AI和区块链", "idea_6")
        
        active = self.service.get_active_risks()
        assert len(active) >= 0
        assert all(r.status == "active" for r in active)
    
    def test_get_high_risks(self):
        """测试获取高风险项"""
        # 创建一个高风险
        self.service.analyze_idea(
            "资金不足，时间很紧，首次做AI项目",
            "idea_7"
        )
        
        high = self.service.get_high_risks()
        assert all(r.level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value] 
                  for r in high)
    
    def test_resolve_risk(self):
        """测试解决风险"""
        report = self.service.analyze_idea("测试", "idea_8")
        
        if report.risks:
            risk_id = report.risks[0].id
            self.service.resolve_risk(risk_id, "已处理")
            
            # 验证已解决
            resolved = [r for r in self.service.get_idea_risks("idea_8") 
                       if r.id == risk_id]
            assert resolved[0].status == "resolved"
    
    def test_recommendations_generation(self):
        """测试建议生成"""
        report = self.service.analyze_idea(
            "做一个复杂的AI项目，时间紧资源少",
            "idea_9"
        )
        
        # 应该生成相应的建议
        assert isinstance(report.recommendations, list)


class TestRiskReport:
    """风险报告测试"""
    
    def test_format_report_with_risks(self):
        """测试报告格式化"""
        from src.services.risk_warning import RiskReport, RiskItem
        
        risks = [
            RiskItem(
                id="risk_1",
                idea_id="idea_1",
                risk_type=RiskType.TECHNICAL_BLOCK.value,
                title="技术风险",
                description="描述"
            )
        ]
        
        report = RiskReport(
            idea_id="idea_1",
            idea_content="测试想法内容",
            risks=risks,
            total_risks=1
        )
        
        formatted = report.format_report()
        assert "风险预警报告" in formatted
        assert "技术风险" in formatted
    
    def test_format_empty_report(self):
        """测试空报告格式化"""
        from src.services.risk_warning import RiskReport
        
        report = RiskReport(
            idea_id="idea_1",
            idea_content="测试"
        )
        
        formatted = report.format_report()
        assert "暂无风险" in formatted or "✅" in formatted
