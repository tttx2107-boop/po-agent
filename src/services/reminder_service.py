"""提醒服务 - 多种类型的提醒触发"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json


class ReminderType(Enum):
    """提醒类型"""
    ASSESSMENT = "assessment"           # 评估提醒
    BLOCKED = "blocked"                 # 阻塞提醒
    OVERDUE = "overdue"                 # 逾期提醒
    REVIEW = "review"                   # 复盘提醒
    PROGRESS = "progress"              # 进度提醒
    WEEKLY = "weekly"                  # 周报提醒


@dataclass
class Reminder:
    """提醒项"""
    id: str
    type: str
    title: str
    message: str
    
    # 关联实体
    idea_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # 时间信息
    created_at: str = ""
    scheduled_at: Optional[str] = None
    
    # 操作建议
    actions: List[str] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def format_message(self) -> str:
        """格式化提醒消息"""
        lines = [f"🔔 **{self.title}**\n"]
        lines.append(f"{self.message}\n")
        
        if self.actions:
            lines.append("\n💡 建议操作：")
            for action in self.actions:
                lines.append(f"• {action}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "idea_id": self.idea_id,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "scheduled_at": self.scheduled_at,
            "actions": self.actions,
            "metadata": self.metadata
        }


@dataclass
class ReminderSchedule:
    """提醒计划"""
    reminder_id: str
    scheduled_time: datetime
    repeat: bool = False
    repeat_interval: Optional[timedelta] = None
    
    def should_fire(self) -> bool:
        """检查是否应该触发"""
        return datetime.now() >= self.scheduled_time


class ReminderService:
    """
    提醒服务
    
    管理各种类型的提醒
    """
    
    # 提醒配置
    CONFIG = {
        "blocked_threshold_days": 3,      # 阻塞超过3天提醒
        "overdue_grace_days": 1,          # 逾期1天后提醒
        "review_delay_days": 7,          # 完成后7天提醒复盘
        "weekly_day": 5,                 # 周五 (0=周一)
        "weekly_hour": 18,
        "assessment_threshold": 5,      # 5个想法触发评估提醒
    }
    
    def __init__(self):
        self._reminders: List[Reminder] = []
        self._schedules: List[ReminderSchedule] = []
        self._notification_callbacks: List[Callable[[Reminder], None]] = []
    
    def register_notification_callback(self, callback: Callable[[Reminder], None]):
        """注册通知回调"""
        self._notification_callbacks.append(callback)
    
    def _notify(self, reminder: Reminder):
        """触发通知"""
        for callback in self._notification_callbacks:
            callback(reminder)
    
    # ==================== 评估提醒 ====================
    
    def check_assessment_reminder(self, ideas: List[Dict]) -> Optional[Reminder]:
        """
        检查是否需要评估提醒
        
        当待评估想法达到阈值时触发
        """
        pending = [i for i in ideas if i.get("status") in ["NEW", "ASSESSING"]]
        
        if len(pending) >= self.CONFIG["assessment_threshold"]:
            # 找出新增的想法
            new_ideas = [i for i in pending if i.get("status") == "NEW"]
            new_content = [i["content"][:20] for i in new_ideas[:3]]
            
            return Reminder(
                id=f"rem_assessment_{datetime.now().strftime('%Y%m%d%H%M')}",
                type=ReminderType.ASSESSMENT.value,
                title="📊 评估提醒",
                message=f"已积累 {len(pending)} 个待评估想法，建议进行批量评估。\n\n待评估想法：\n" + 
                        "\n".join(f"• {c}..." for c in new_content),
                actions=[
                    "「立即评估」- 开始深度评估",
                    "「稍后」- 稍后再说"
                ],
                metadata={"pending_count": len(pending), "new_count": len(new_ideas)}
            )
        
        return None
    
    def create_weekly_assessment_reminder(self) -> Reminder:
        """创建每周评估提醒"""
        now = datetime.now()
        return Reminder(
            id=f"rem_weekly_{now.strftime('%Y%m%d')}",
            type=ReminderType.ASSESSMENT.value,
            title="📊 每周评估提醒",
            message=f"⏰ 今天是 {now.strftime('%A')}",
            actions=[
                "「立即评估」- 开始深度评估",
                "「统计」- 查看想法库概览"
            ]
        )
    
    # ==================== 阻塞提醒 ====================
    
    def check_blocked_reminders(self, tasks: List[Dict]) -> List[Reminder]:
        """
        检查阻塞任务
        
        任务阻塞超过阈值时触发
        """
        reminders = []
        threshold = self.CONFIG["blocked_threshold_days"]
        
        for task in tasks:
            if task.get("status") != "blocked":
                continue
            
            # 计算阻塞天数
            blocked_at = task.get("blocked_at") or task.get("updated_at")
            if not blocked_at:
                continue
            
            blocked_time = datetime.fromisoformat(blocked_at.replace("Z", "+00:00"))
            blocked_days = (datetime.now() - blocked_time).days
            
            if blocked_days >= threshold:
                priority = "🔴" if blocked_days >= threshold * 2 else "🟠"
                reminder = Reminder(
                    id=f"rem_blocked_{task['id']}",
                    type=ReminderType.BLOCKED.value,
                    title=f"{priority} 任务阻塞提醒",
                    message=f"「{task.get('title', '未知任务')}」已阻塞 {blocked_days} 天",
                    task_id=task.get("id"),
                    idea_id=task.get("idea_id"),
                    actions=[
                        "「查看阻塞」- 查看阻塞详情",
                        "分析阻塞原因",
                        "考虑缩小范围或延长时间"
                    ],
                    metadata={"blocked_days": blocked_days, "reason": task.get("block_reason")}
                )
                reminders.append(reminder)
                self._notify(reminder)
        
        return reminders
    
    # ==================== 逾期提醒 ====================
    
    def check_overdue_reminders(self, tasks: List[Dict]) -> List[Reminder]:
        """
        检查逾期任务
        
        任务逾期时触发
        """
        reminders = []
        grace_days = self.CONFIG["overdue_grace_days"]
        
        now = datetime.now()
        
        for task in tasks:
            if task.get("status") in ["done", "cancelled"]:
                continue
            
            due_date = task.get("due_date")
            if not due_date:
                continue
            
            due_time = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            if now > due_time:
                overdue_days = (now - due_time).days
                
                if overdue_days >= grace_days:
                    reminder = Reminder(
                        id=f"rem_overdue_{task['id']}",
                        type=ReminderType.OVERDUE.value,
                        title="⚠️ 任务逾期提醒",
                        message=f"「{task.get('title', '未知任务')}」已逾期 {overdue_days} 天",
                        task_id=task.get("id"),
                        idea_id=task.get("idea_id"),
                        actions=[
                            "更新预期完成时间",
                            "调整后续计划",
                            "考虑缩小任务范围"
                        ],
                        metadata={"overdue_days": overdue_days, "due_date": due_date}
                    )
                    reminders.append(reminder)
                    self._notify(reminder)
        
        return reminders
    
    # ==================== 复盘提醒 ====================
    
    def check_review_reminders(self, ideas: List[Dict]) -> List[Reminder]:
        """
        检查复盘提醒
        
        任务完成后一段时间提醒复盘
        """
        reminders = []
        delay_days = self.CONFIG["review_delay_days"]
        
        now = datetime.now()
        
        for idea in ideas:
            if idea.get("status") != "COMPLETED":
                continue
            
            # 检查是否已有最近复盘
            reviews = idea.get("reviews", [])
            if reviews:
                last_review = reviews[-1]
                last_review_date = datetime.fromisoformat(last_review.get("date", "2000-01-01"))
                if (now - last_review_date).days < 30:
                    continue
            
            # 检查完成时间
            completed_at = idea.get("completed_at")
            if not completed_at:
                continue
            
            completed_time = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            days_since_completion = (now - completed_time).days
            
            if delay_days <= days_since_completion < delay_days + 7:  # 在一周窗口内
                reminder = Reminder(
                    id=f"rem_review_{idea['id']}",
                    type=ReminderType.REVIEW.value,
                    title="🔄 复盘提醒",
                    message=f"「{idea['content'][:30]}...」已完成 {days_since_completion} 天，建议进行复盘",
                    idea_id=idea.get("id"),
                    actions=[
                        "「复盘」- 开始复盘",
                        "总结经验教训",
                        "记录后续改进"
                    ],
                    metadata={"days_since_completion": days_since_completion}
                )
                reminders.append(reminder)
                self._notify(reminder)
        
        return reminders
    
    # ==================== 进度提醒 ====================
    
    def check_progress_reminders(self, ideas: List[Dict]) -> List[Reminder]:
        """
        检查进度提醒
        
        长时间无进度的想法提醒
        """
        reminders = []
        
        now = datetime.now()
        
        for idea in ideas:
            if idea.get("status") != "IN_PROGRESS":
                continue
            
            # 检查是否有进行中的任务但无进度
            tasks = idea.get("tasks", [])
            active_tasks = [t for t in tasks if t.get("status") in ["todo", "in_progress"]]
            
            if not active_tasks:
                continue
            
            # 检查更新时间
            updated_at = idea.get("updated_at")
            if not updated_at:
                continue
            
            updated_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since_update = (now - updated_time).days
            
            # 超过7天无更新
            if days_since_update >= 7:
                reminder = Reminder(
                    id=f"rem_progress_{idea['id']}",
                    type=ReminderType.PROGRESS.value,
                    title="📈 进度提醒",
                    message=f"「{idea['content'][:30]}...」已 {days_since_update} 天无进度更新",
                    idea_id=idea.get("id"),
                    actions=[
                        "更新项目进度",
                        "是否有阻塞需要处理？",
                        "是否需要调整计划？"
                    ],
                    metadata={"days_since_update": days_since_update}
                )
                reminders.append(reminder)
                self._notify(reminder)
        
        return reminders
    
    # ==================== 调度管理 ====================
    
    def schedule_reminder(self, reminder: Reminder, delay_seconds: int = 0):
        """调度提醒"""
        scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)
        
        schedule = ReminderSchedule(
            reminder_id=reminder.id,
            scheduled_time=scheduled_time
        )
        self._schedules.append(schedule)
    
    def get_pending_reminders(self) -> List[Reminder]:
        """获取待发送的提醒"""
        now = datetime.now()
        
        # 检查调度器
        pending = []
        for schedule in self._schedules[:]:
            if schedule.should_fire():
                # 找到对应的提醒
                for reminder in self._reminders:
                    if reminder.id == schedule.reminder_id:
                        pending.append(reminder)
                        break
                self._schedules.remove(schedule)
        
        return pending
    
    # ==================== 提醒管理 ====================
    
    def add_reminder(self, reminder: Reminder):
        """添加提醒"""
        self._reminders.append(reminder)
    
    def dismiss_reminder(self, reminder_id: str):
        """Dismiss提醒"""
        self._reminders = [r for r in self._reminders if r.id != reminder_id]
    
    def get_reminder_history(self, limit: int = 50) -> List[Reminder]:
        """获取提醒历史"""
        return sorted(self._reminders, 
                     key=lambda r: r.created_at, 
                     reverse=True)[:limit]
    
    def generate_daily_summary(self, ideas: List[Dict], tasks: List[Dict]) -> str:
        """
        生成每日提醒汇总
        
        Args:
            ideas: 想法列表
            tasks: 任务列表
            
        Returns:
            汇总消息
        """
        lines = ["📋 每日提醒汇总\n━━━━━━━━━━━━━━━━━━━━\n"]
        
        # 阻塞提醒
        blocked = self.check_blocked_reminders(tasks)
        if blocked:
            lines.append(f"⚠️ 阻塞任务：{len(blocked)} 个")
            for r in blocked[:3]:
                lines.append(f"  • {r.message}")
            lines.append("")
        
        # 逾期提醒
        overdue = self.check_overdue_reminders(tasks)
        if overdue:
            lines.append(f"🔴 逾期任务：{len(overdue)} 个")
            for r in overdue[:3]:
                lines.append(f"  • {r.message}")
            lines.append("")
        
        # 评估提醒
        assessment = self.check_assessment_reminder(ideas)
        if assessment:
            lines.append(f"📊 待评估：{assessment.metadata.get('pending_count', 0)} 个\n")
        
        # 复盘提醒
        review = self.check_review_reminders(ideas)
        if review:
            lines.append(f"🔄 待复盘：{len(review)} 个\n")
        
        if len(lines) == 1:
            lines.append("✅ 今天暂无提醒\n")
        
        # 统计
        stats = self._get_idea_stats(ideas)
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"\n📈 想法库统计：")
        lines.append(f"  总数：{stats['total']}")
        lines.append(f"  执行中：{stats['in_progress']}")
        lines.append(f"  已完成：{stats['completed']}")
        
        return "\n".join(lines)
    
    def _get_idea_stats(self, ideas: List[Dict]) -> Dict[str, int]:
        """获取想法统计"""
        return {
            "total": len(ideas),
            "in_progress": len([i for i in ideas if i.get("status") == "IN_PROGRESS"]),
            "completed": len([i for i in ideas if i.get("status") == "COMPLETED"]),
            "pending": len([i for i in ideas if i.get("status") in ["NEW", "ASSESSING"]])
        }


# 全局实例
_reminder_service = None


def get_reminder_service() -> ReminderService:
    """获取提醒服务实例"""
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = ReminderService()
    return _reminder_service
