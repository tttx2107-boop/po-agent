"""TaskBreaker 测试"""
import pytest
from src.services.task_breaker import TaskBreaker, SubTask, BreakdownResult


class TestTaskBreaker:
    """TaskBreaker 测试类"""
    
    def test_basic_breakdown(self):
        """测试基本拆解"""
        breaker = TaskBreaker()
        idea = "开发一个 Python 命令行工具"
        result = breaker.breakdown(idea)
        
        assert isinstance(result, BreakdownResult)
        assert result.original_idea == idea
        assert len(result.subtasks) > 0
        assert result.estimated_total_hours > 0
    
    def test_complexity_detection(self):
        """测试复杂度检测"""
        breaker = TaskBreaker()
        
        # 高复杂度
        result = breaker.breakdown("开发一个复杂的 AI 系统")
        assert len(result.subtasks) > 5
        
        # 低复杂度  
        result = breaker.breakdown("做一个简单的 MVP")
        assert len(result.subtasks) >= 4
    
    def test_task_types(self):
        """测试任务类型识别"""
        breaker = TaskBreaker()
        
        # 开发类
        result = breaker.breakdown("开发一个 APP")
        assert any(t.task_type == "development" for t in result.subtasks)
        
        # 研究类
        result = breaker.breakdown("调研 AI 技术趋势")
        assert any(t.task_type == "research" for t in result.subtasks)
        
        # 设计类
        result = breaker.breakdown("设计一个新的系统架构")
        assert any(t.task_type == "design" for t in result.subtasks)
    
    def test_dependencies(self):
        """测试任务依赖"""
        breaker = TaskBreaker()
        result = breaker.breakdown("开发一个网站")
        
        # 检查是否存在有依赖的任务
        has_deps = any(len(t.dependencies) > 0 for t in result.subtasks)
        assert has_deps or len(result.subtasks) >= 3
    
    def test_risk_notes(self):
        """测试风险提示"""
        breaker = TaskBreaker()
        result = breaker.breakdown("开发一个复杂系统")
        
        assert result.risk_notes is not None
        assert len(result.risk_notes) > 0
    
    def test_success_criteria(self):
        """测试验收标准"""
        breaker = TaskBreaker()
        result = breaker.breakdown("做一个项目")
        
        assert result.success_criteria is not None
        assert "核心功能" in result.success_criteria or len(result.success_criteria) > 20
    
    def test_format_output(self):
        """测试格式化输出"""
        breaker = TaskBreaker()
        result = breaker.breakdown("开发一个工具")
        
        formatted = result.format()
        
        assert "任务拆解" in formatted
        assert "验收标准" in formatted
        assert "任务清单" in formatted
        assert "预估总工时" in formatted
    
    def test_empty_idea(self):
        """测试空想法"""
        breaker = TaskBreaker()
        result = breaker.breakdown("")
        
        assert isinstance(result, BreakdownResult)
        assert len(result.subtasks) > 0


class TestSubTask:
    """SubTask 测试"""
    
    def test_subtask_creation(self):
        """测试创建子任务"""
        task = SubTask(
            title="测试任务",
            description="测试描述",
            task_type="development",
            estimated_hours=2.0
        )
        
        assert task.title == "测试任务"
        assert task.estimated_hours == 2.0
    
    def test_subtask_to_dict(self):
        """测试转换为字典"""
        task = SubTask(title="Test", description="Desc")
        data = task.to_dict()
        
        assert isinstance(data, dict)
        assert data["title"] == "Test"
