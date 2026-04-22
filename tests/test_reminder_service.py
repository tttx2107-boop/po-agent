"""提醒服务测试"""
import pytest
from datetime import datetime, timedelta
from src.services.reminder_service import (
    ReminderService, Reminder, ReminderType, get_reminder_service
)


class TestReminderService:
    """提醒服务测试"""
    
    def setup_method(self):
        """每个测试前重置"""
        self.service = ReminderService()
    
    def test_create_assessment_reminder_threshold(self):
        """测试评估提醒阈值触发"""
        ideas = [
            {"id": f"idea_{i}", "status": "NEW", "content": f"想法{i}"}
            for i in range(5)
        ]
        
        reminder = self.service.check_assessment_reminder(ideas)
        assert reminder is not None
        assert reminder.type == ReminderType.ASSESSMENT.value
        assert "5" in reminder.message
    
    def test_no_assessment_reminder_below_threshold(self):
        """测试低于阈值不触发"""
        ideas = [
            {"id": "idea_1", "status": "NEW", "content": "想法1"},
            {"id": "idea_2", "status": "CONFIRMED", "content": "想法2"},
        ]
        
        reminder = self.service.check_assessment_reminder(ideas)
        assert reminder is None
    
    def test_blocked_reminder_trigger(self):
        """测试阻塞提醒触发"""
        blocked_at = (datetime.now() - timedelta(days=4)).isoformat()
        
        tasks = [
            {
                "id": "task_1",
                "title": "完成文档",
                "status": "blocked",
                "blocked_at": blocked_at,
                "idea_id": "idea_1"
            }
        ]
        
        reminders = self.service.check_blocked_reminders(tasks)
        assert len(reminders) == 1
        assert "阻塞" in reminders[0].title
        assert reminders[0].metadata["blocked_days"] == 4
    
    def test_no_blocked_reminder_below_threshold(self):
        """测试低于阈值不触发阻塞"""
        blocked_at = (datetime.now() - timedelta(days=2)).isoformat()
        
        tasks = [
            {
                "id": "task_1",
                "title": "完成文档",
                "status": "blocked",
                "blocked_at": blocked_at
            }
        ]
        
        reminders = self.service.check_blocked_reminders(tasks)
        assert len(reminders) == 0
    
    def test_overdue_reminder_trigger(self):
        """测试逾期提醒触发"""
        due_date = (datetime.now() - timedelta(days=3)).isoformat()
        
        tasks = [
            {
                "id": "task_1",
                "title": "完成文档",
                "status": "todo",
                "due_date": due_date
            }
        ]
        
        reminders = self.service.check_overdue_reminders(tasks)
        assert len(reminders) == 1
        assert "逾期" in reminders[0].title
    
    def test_review_reminder_trigger(self):
        """测试复盘提醒触发"""
        completed_at = (datetime.now() - timedelta(days=10)).isoformat()
        
        ideas = [
            {
                "id": "idea_1",
                "content": "完成一个项目",
                "status": "COMPLETED",
                "completed_at": completed_at,
                "reviews": []  # 无最近复盘
            }
        ]
        
        reminders = self.service.check_review_reminders(ideas)
        assert len(reminders) == 1
        assert "复盘" in reminders[0].title
    
    def test_no_review_with_recent_review(self):
        """测试有最近复盘不触发"""
        completed_at = (datetime.now() - timedelta(days=10)).isoformat()
        last_review = (datetime.now() - timedelta(days=5)).isoformat()
        
        ideas = [
            {
                "id": "idea_1",
                "content": "完成一个项目",
                "status": "COMPLETED",
                "completed_at": completed_at,
                "reviews": [{"date": last_review}]
            }
        ]
        
        reminders = self.service.check_review_reminders(ideas)
        assert len(reminders) == 0
    
    def test_progress_reminder_trigger(self):
        """测试进度提醒触发"""
        updated_at = (datetime.now() - timedelta(days=10)).isoformat()
        
        ideas = [
            {
                "id": "idea_1",
                "content": "执行中的项目",
                "status": "IN_PROGRESS",
                "updated_at": updated_at,
                "tasks": [{"id": "task_1", "status": "in_progress"}]
            }
        ]
        
        reminders = self.service.check_progress_reminders(ideas)
        assert len(reminders) == 1
        assert "进度" in reminders[0].title
    
    def test_dismiss_reminder(self):
        """测试Dismiss提醒"""
        reminder = Reminder(
            id="test_reminder",
            type=ReminderType.ASSESSMENT.value,
            title="测试",
            message="测试消息"
        )
        self.service.add_reminder(reminder)
        assert len(self.service._reminders) == 1
        
        self.service.dismiss_reminder("test_reminder")
        assert len(self.service._reminders) == 0
    
    def test_reminder_format_message(self):
        """测试提醒消息格式化"""
        reminder = Reminder(
            id="test",
            type=ReminderType.ASSESSMENT.value,
            title="测试提醒",
            message="这是测试消息",
            actions=["操作1", "操作2"]
        )
        
        formatted = reminder.format_message()
        assert "测试提醒" in formatted
        assert "测试消息" in formatted
        assert "操作1" in formatted
    
    def test_weekly_assessment_reminder(self):
        """测试每周评估提醒"""
        reminder = self.service.create_weekly_assessment_reminder()
        assert reminder.type == ReminderType.ASSESSMENT.value
        assert "评估提醒" in reminder.title
    
    def test_get_idea_stats(self):
        """测试想法统计"""
        ideas = [
            {"id": "1", "status": "IN_PROGRESS"},
            {"id": "2", "status": "COMPLETED"},
            {"id": "3", "status": "NEW"},
            {"id": "4", "status": "NEW"},
        ]
        
        stats = self.service._get_idea_stats(ideas)
        assert stats["total"] == 4
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["pending"] == 2
    
    def test_generate_daily_summary(self):
        """测试每日汇总生成"""
        ideas = [
            {"id": "1", "status": "IN_PROGRESS", "content": "想法1", "updated_at": datetime.now().isoformat()},
            {"id": "2", "status": "COMPLETED", "content": "想法2", "completed_at": datetime.now().isoformat()},
            {"id": "3", "status": "NEW", "content": "想法3"},
            {"id": "4", "status": "NEW", "content": "想法4"},
            {"id": "5", "status": "NEW", "content": "想法5"},
        ]
        tasks = []
        
        summary = self.service.generate_daily_summary(ideas, tasks)
        assert "汇总" in summary
        assert "想法库统计" in summary


class TestReminderModel:
    """提醒模型测试"""
    
    def test_reminder_to_dict(self):
        """测试提醒转字典"""
        reminder = Reminder(
            id="test_123",
            type=ReminderType.ASSESSMENT.value,
            title="测试",
            message="消息",
            idea_id="idea_1"
        )
        
        data = reminder.to_dict()
        assert data["id"] == "test_123"
        assert data["idea_id"] == "idea_1"
        assert data["type"] == "assessment"
    
    def test_reminder_default_timestamp(self):
        """测试默认时间戳"""
        reminder = Reminder(
            id="test",
            type=ReminderType.ASSESSMENT.value,
            title="测试",
            message="消息"
        )
        assert reminder.created_at != ""
        # 应该是有效的 ISO 格式
        datetime.fromisoformat(reminder.created_at)
