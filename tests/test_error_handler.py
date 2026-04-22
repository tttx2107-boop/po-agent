"""错误处理测试"""
import pytest
from src.services.error_handler import (
    ErrorHandler, ErrorType, RecoveryAction, ErrorContext, ClarificationQuestion,
    get_error_handler
)


class TestErrorHandler:
    """错误处理器测试"""
    
    def setup_method(self):
        """每个测试前重置"""
        self.handler = ErrorHandler()
    
    def test_generate_clarification_questions(self):
        """测试生成澄清问题"""
        questions = self.handler._analyze_idea_gaps("做点什么")
        
        assert len(questions) >= 1
        assert any("目标" in q.question for q in questions)
    
    def test_handle_clarity_request_attempts(self):
        """测试不同次数的澄清请求"""
        # 第一次
        msg = self.handler.handle_clarity_request("测试", 0)
        assert "目标" in msg
        
        # 第二次
        msg = self.handler.handle_clarity_request("测试", 1)
        assert "时间" in msg or "资源" in msg
        
        # 第三次
        msg = self.handler.handle_clarity_request("测试", 2)
        assert "成果" in msg or "成功" in msg
    
    def test_analyze_task_failure_resource(self):
        """测试资源不足错误分析"""
        task = {"id": "task_1", "title": "测试任务"}
        error = {"message": "资源不足，无法继续"}
        
        context = self.handler.analyze_task_failure(task, error)
        
        assert context.error_type == ErrorType.RESOURCE.value
        assert len(context.recovery_actions) > 0
        assert context.recovery_actions[0].action_type == "replace"
    
    def test_analyze_task_failure_skill_gap(self):
        """测试技能缺口错误分析"""
        task = {"id": "task_1", "title": "测试任务"}
        error = {"message": "我不知道怎么实现这个功能"}
        
        context = self.handler.analyze_task_failure(task, error)
        
        assert context.error_type == ErrorType.SKILL_GAP.value
    
    def test_analyze_task_failure_dependency(self):
        """测试依赖问题错误分析"""
        task = {"id": "task_1", "title": "测试任务"}
        error = {"message": "等待前置任务完成"}
        
        context = self.handler.analyze_task_failure(task, error)
        
        assert context.error_type == ErrorType.DEPENDENCY.value
    
    def test_handle_timeout_with_checkpoint(self):
        """测试带检查点的超时处理"""
        action = self.handler.handle_timeout(
            task_id="task_1",
            elapsed_seconds=300,
            checkpoint_data={"progress": 50}
        )
        
        assert "检查点" in action.description
        assert action.estimated_impact == "低"
    
    def test_handle_timeout_without_checkpoint(self):
        """测试不带检查点的超时处理"""
        action = self.handler.handle_timeout(
            task_id="task_1",
            elapsed_seconds=300
        )
        
        assert "检查点" not in action.description
        assert action.estimated_impact == "中"
    
    def test_error_history(self):
        """测试错误历史"""
        # 触发一些错误
        task = {"id": "task_1", "title": "测试"}
        self.handler.analyze_task_failure(task, {"message": "错误1"})
        self.handler.analyze_task_failure(task, {"message": "资源不足"})
        
        history = self.handler.get_error_history()
        assert len(history) >= 2
    
    def test_resolve_error(self):
        """测试解决错误"""
        task = {"id": "task_1", "title": "测试"}
        self.handler.analyze_task_failure(task, {"message": "错误"})
        
        history = self.handler.get_error_history()
        if history:
            error_id = history[0].timestamp
            self.handler.resolve_error(error_id, "已处理")
            
            # 再次获取
            updated = self.handler.get_error_history()
            assert updated[0].resolved
    
    def test_format_error_report(self):
        """测试错误报告格式化"""
        context = ErrorContext(
            error_type=ErrorType.TASK_FAILURE.value,
            message="测试错误",
            timestamp="2024-01-01T00:00:00",
            recovery_actions=[
                RecoveryAction(
                    action_type="replace",
                    description="建议重试",
                    alternatives=["选项1", "选项2"]
                )
            ]
        )
        
        report = self.handler.format_error_report(context)
        assert "错误报告" in report
        assert "测试错误" in report
        assert "重试" in report


class TestClarificationQuestion:
    """澄清问题测试"""
    
    def test_create_question(self):
        """测试创建问题"""
        q = ClarificationQuestion(
            question="目标是什么？",
            hint="具体要达成什么",
            required=True,
            options=["A", "B"]
        )
        
        assert q.question == "目标是什么？"
        assert len(q.options) == 2
    
    def test_question_defaults(self):
        """测试问题默认值"""
        q = ClarificationQuestion(question="测试？")
        
        assert q.required is True
        assert q.hint == ""
        assert q.options == []


class TestRecoveryAction:
    """恢复动作测试"""
    
    def test_create_recovery_action(self):
        """测试创建恢复动作"""
        action = RecoveryAction(
            action_type="replace",
            description="替换方案",
            alternatives=["方案1", "方案2"],
            estimated_impact="中"
        )
        
        assert action.action_type == "replace"
        assert action.estimated_impact == "中"
        assert len(action.alternatives) == 2
