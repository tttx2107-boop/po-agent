"""任务模型"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class SubTask:
    """子任务"""
    title: str
    done: bool = False
    id: str = ""


@dataclass
class Task:
    """任务实体"""
    id: str
    idea_id: str  # 所属想法 ID
    
    title: str
    description: str = ""
    task_type: str = "general"  # research, document, mvp, deploy, test, review, general
    
    status: str = "TODO"  # TODO, IN_PROGRESS, BLOCKED, DONE, CANCELLED
    
    # 优先级
    priority: int = 3  # 1-5, 1=最高
    priority_reason: str = ""
    
    # 时间
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    due_date: str = ""
    completed_at: str = ""
    
    # 预估
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    
    # 依赖
    depends_on: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)
    
    # 进度
    subtasks: List[SubTask] = field(default_factory=list)
    progress: int = 0
    
    # 阻塞
    block_reason: str = ""
    block_duration_days: int = 0
    
    # 产出物
    outputs: List[str] = field(default_factory=list)
    
    # 备注
    notes: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if self.subtasks and isinstance(self.subtasks[0], dict):
            self.subtasks = [SubTask(**s) if isinstance(s, dict) else s for s in self.subtasks]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(**data)

    def get_status_display(self) -> str:
        """状态显示"""
        status_map = {
            "TODO": "📋 待办",
            "IN_PROGRESS": "🔄 进行中",
            "BLOCKED": "🚫 阻塞",
            "DONE": "✅ 完成",
            "CANCELLED": "❌ 取消"
        }
        return status_map.get(self.status, self.status)

    def calculate_progress(self) -> int:
        """计算进度"""
        if self.status == "DONE":
            return 100
        if not self.subtasks:
            return self.progress
        done_count = sum(1 for s in self.subtasks if s.done)
        return int(done_count / len(self.subtasks) * 100)

    def update_progress(self):
        """更新进度"""
        self.progress = self.calculate_progress()
        self.updated_at = datetime.now().isoformat()
