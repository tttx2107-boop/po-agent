"""活动日志模型"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ActivityLog:
    """活动日志"""
    id: str
    timestamp: str
    type: str  # idea_created, assessment, task_update, user_action, system_event
    
    # 关联实体
    idea_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # 详情
    action: str
    before: Dict[str, Any] = field(default_factory=dict)
    after: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    user_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityLog":
        return cls(**data)

    @classmethod
    def create(cls, type: str, action: str, **kwargs) -> "ActivityLog":
        """创建活动日志"""
        import uuid
        return cls(
            id=str(uuid.uuid4())[:8],
            type=type,
            action=action,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )
