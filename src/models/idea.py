"""想法模型"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class QuickAssessment:
    """快速评估结果"""
    intent_type: str = "idea"  # idea, command, query
    domain_tags: List[str] = field(default_factory=list)
    completeness: float = 0.0
    keywords_note: str = ""
    assessment_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeepAssessment:
    """深度评估结果"""
    innovation_score: int = 0
    feasibility_score: int = 0
    value_score: int = 0
    risk_score: int = 0
    overall_score: float = 0.0
    perspective_score: float = 0.0
    decision_level: str = ""  # 🌟🌟🌟🌟🌟
    decision_action: str = ""
    decision_reason: str = ""
    assessment_date: str = ""
    assessor: str = "ai"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Review:
    """复盘记录"""
    date: str
    result: str  # success, failed, partial
    lessons: str = ""
    next_actions: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Idea:
    """想法实体"""
    id: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""
    
    # 元信息
    source: str = "cli"  # wechat, cli, schedule
    tags: List[str] = field(default_factory=list)
    status: str = "NEW"  # NEW, ASSESSING, CONFIRMED, DEFERRED, REJECTED, IN_PROGRESS, COMPLETED
    priority: int = 0
    
    # 评估
    quick_assessment: Optional[QuickAssessment] = None
    deep_assessment: Optional[DeepAssessment] = None
    
    # 执行追踪
    tasks: List[str] = field(default_factory=list)  # 任务 ID 列表
    milestone: str = ""
    progress: int = 0
    
    # 复盘
    reviews: List[Review] = field(default_factory=list)
    
    # 备注
    notes: str = ""

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = self.created_at
        if self.quick_assessment and isinstance(self.quick_assessment, dict):
            self.quick_assessment = QuickAssessment(**self.quick_assessment)
        if self.deep_assessment and isinstance(self.deep_assessment, dict):
            self.deep_assessment = DeepAssessment(**self.deep_assessment)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Idea":
        """从字典创建"""
        # 处理 Review
        if "reviews" in data and data["reviews"]:
            data["reviews"] = [Review(**r) if isinstance(r, dict) else r for r in data["reviews"]]
        return cls(**data)

    def get_status_display(self) -> str:
        """状态显示"""
        status_map = {
            "NEW": "🆕 新想法",
            "ASSESSING": "⏳ 待评估",
            "CONFIRMED": "✅ 已确认",
            "DEFERRED": "⏸️ 暂缓",
            "REJECTED": "❌ 已否决",
            "IN_PROGRESS": "🔄 执行中",
            "COMPLETED": "⭐ 已完成"
        }
        return status_map.get(self.status, self.status)

    def is_pending_assessment(self) -> bool:
        """是否待评估"""
        return self.status in ["NEW", "ASSESSING"]
