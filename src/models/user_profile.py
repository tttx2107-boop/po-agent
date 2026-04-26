"""
用户画像模型 - 「破」智能适配的核心
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """用户角色类型"""
    RESEARCHER = "researcher"           # 高校/科研人员
    ENGINEER = "engineer"               # 工程师/技术专家
    ENTREPRENEUR = "entrepreneur"       # 创业者
    STUDENT = "student"                 # 学生
    MANAGER = "manager"                 # 管理者
    CONSULTANT = "consultant"           # 咨询顾问
    HOBBYIST = "hobbyist"               # 爱好者/个人
    OTHER = "other"                     # 其他


class OutputGoal(str, Enum):
    """产出目标"""
    PAPER = "paper"                     # 论文发表
    PATENT = "patent"                   # 专利申请
    PRODUCT = "product"                 # 产品落地
    PROJECT = "project"                 # 项目申报
    PORTFOLIO = "portfolio"             # 作品集/展示
    LEARNING = "learning"               # 学习/练手
    BUSINESS = "business"               # 商业化


class TechLevel(str, Enum):
    """技术能力等级"""
    BEGINNER = "beginner"              # 初学者
    INTERMEDIATE = "intermediate"      # 中级
    ADVANCED = "advanced"               # 高级
    EXPERT = "expert"                   # 专家级


class ResourceConstraint(BaseModel):
    """资源约束"""
    budget: Optional[str] = None       # 预算范围
    time: Optional[str] = None          # 时间约束
    team_size: Optional[int] = None    # 团队人数
    equipment: Optional[List[str]] = [] # 可用设备


class UserProfile(BaseModel):
    """用户画像 - 「破」智能适配的核心"""
    
    # === 基础信息 ===
    user_id: str = "default"
    name: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # === 角色定位 ===
    role: UserRole = UserRole.RESEARCHER
    role_description: str = ""          # 角色描述
    organization: Optional[str] = None  # 所属机构（学校/公司等）
    field: Optional[str] = None         # 专业领域
    
    # === 产出目标（可多选）===
    output_goals: List[OutputGoal] = []
    priority_outputs: List[str] = []    # 优先级排序的产出
    
    # === 技术能力 ===
    tech_level: TechLevel = TechLevel.INTERMEDIATE
    available_techs: List[str] = []     # 掌握的技术栈
    preferred_techs: List[str] = []     # 偏好的技术栈
    hardware_experience: bool = False   # 是否有硬件经验
    
    # === 资源约束 ===
    resources: ResourceConstraint = Field(default_factory=ResourceConstraint)
    
    # === 研究/项目偏好 ===
    interests: List[str] = []            # 关注领域
    past_experience: List[str] = []     # 过往经验（做过什么）
    
    # === 偏好设置 ===
    preferred_task_size: str = "medium" # 偏好的任务粒度
    notification_style: str = "concise"  # 通知风格: concise/detailed
    
    # === 扩展信息（灵活存储）===
    metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = self.model_dump()
        # 处理枚举
        for key, value in data.items():
            if hasattr(value, 'value'):
                data[key] = value.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """从字典创建"""
        # 处理枚举
        if "role" in data and isinstance(data["role"], str):
            data["role"] = UserRole(data["role"])
        if "output_goals" in data and data["output_goals"]:
            data["output_goals"] = [OutputGoal(g) if isinstance(g, str) else g for g in data["output_goals"]]
        if "tech_level" in data and isinstance(data["tech_level"], str):
            data["tech_level"] = TechLevel(data["tech_level"])
        if "resources" in data and isinstance(data["resources"], dict):
            data["resources"] = ResourceConstraint(**data["resources"])
        return cls(**data)


# === 用户画像采集问卷 ===

PROFILE_QUESTIONS = [
    {
        "id": "role",
        "question": "你的角色是什么？",
        "type": "single_choice",
        "options": [
            {"value": "researcher", "label": "高校/科研人员", "icon": "🎓"},
            {"value": "engineer", "label": "工程师/技术专家", "icon": "🔧"},
            {"value": "entrepreneur", "label": "创业者", "icon": "🚀"},
            {"value": "student", "label": "学生", "icon": "📚"},
            {"value": "manager", "label": "管理者", "icon": "📊"},
            {"value": "other", "label": "其他", "icon": "❓"}
        ],
        "required": True
    },
    {
        "id": "organization",
        "question": "你所属的机构类型？",
        "type": "single_choice",
        "options": [
            {"value": "university", "label": "高校/研究所", "icon": "🏫"},
            {"value": "company", "label": "企业", "icon": "🏢"},
            {"value": "government", "label": "政府/事业单位", "icon": "🏛️"},
            {"value": "individual", "label": "个人/自由职业", "icon": "👤"},
            {"value": "none", "label": "暂不确定", "icon": "❓"}
        ],
        "required": False
    },
    {
        "id": "output_goals",
        "question": "你希望产出什么？（可多选）",
        "type": "multi_choice",
        "options": [
            {"value": "paper", "label": "论文发表", "icon": "📄"},
            {"value": "patent", "label": "专利申请", "icon": "📜"},
            {"value": "product", "label": "产品落地", "icon": "📦"},
            {"value": "project", "label": "项目申报", "icon": "📋"},
            {"value": "portfolio", "label": "作品展示", "icon": "🎨"},
            {"value": "business", "label": "商业化", "icon": "💰"}
        ],
        "required": True,
        "min_selections": 1
    },
    {
        "id": "field",
        "question": "你的专业/研究领域？",
        "type": "text",
        "placeholder": "例如：消防安全、人工智能、机械工程...",
        "required": False
    },
    {
        "id": "tech_level",
        "question": "你的技术能力水平？",
        "type": "single_choice",
        "options": [
            {"value": "beginner", "label": "初学者", "description": "刚入门，还在学习中"},
            {"value": "intermediate", "label": "中级", "description": "有实践经验，能独立完成"},
            {"value": "advanced", "label": "高级", "description": "深入理解，能解决复杂问题"},
            {"value": "expert", "label": "专家", "description": "精通领域内各项技术"}
        ],
        "required": True
    },
    {
        "id": "hardware_experience",
        "question": "你有硬件开发经验吗？（单片机、嵌入式、电路等）",
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "有经验", "icon": "👍"},
            {"value": "no", "label": "无经验", "icon": "👎"},
            {"value": "some", "label": "了解一些", "icon": "🤔"}
        ],
        "required": True
    },
    {
        "id": "available_techs",
        "question": "你掌握的技术栈？（输入关键词，用逗号分隔）",
        "type": "text",
        "placeholder": "例如：Python, JavaScript, 机器学习, 嵌入式C...",
        "required": False
    },
    {
        "id": "budget",
        "question": "你的预算范围？",
        "type": "single_choice",
        "options": [
            {"value": "0", "label": "0元（纯软/模拟）", "icon": "💵"},
            {"value": "1k", "label": "1000元以内", "icon": "💶"},
            {"value": "5k", "label": "1000-5000元", "icon": "💷"},
            {"value": "10k", "label": "5000-10000元", "icon": "💴"},
            {"value": "50k", "label": "10000元以上", "icon": "💵💵"},
            {"value": "unknown", "label": "暂不确定", "icon": "❓"}
        ],
        "required": False
    },
    {
        "id": "interests",
        "question": "你最关注的领域？（输入关键词）",
        "type": "text",
        "placeholder": "例如：消防安全、知识图谱、智能硬件...",
        "required": False
    }
]


def generate_profile_from_answers(answers: Dict[str, Any]) -> UserProfile:
    """根据问卷答案生成用户画像"""
    
    # 角色映射
    role_map = {
        "researcher": UserRole.RESEARCHER,
        "engineer": UserRole.ENGINEER,
        "entrepreneur": UserRole.ENTREPRENEUR,
        "student": UserRole.STUDENT,
        "manager": UserRole.MANAGER,
        "consultant": UserRole.CONSULTANT,
        "hobbyist": UserRole.HOBBYIST,
        "other": UserRole.OTHER
    }
    
    # 技术等级映射
    tech_level_map = {
        "beginner": TechLevel.BEGINNER,
        "intermediate": TechLevel.INTERMEDIATE,
        "advanced": TechLevel.ADVANCED,
        "expert": TechLevel.EXPERT
    }
    
    # 产出目标映射
    output_map = {
        "paper": OutputGoal.PAPER,
        "patent": OutputGoal.PATENT,
        "product": OutputGoal.PRODUCT,
        "project": OutputGoal.PROJECT,
        "portfolio": OutputGoal.PORTFOLIO,
        "learning": OutputGoal.LEARNING,
        "business": OutputGoal.BUSINESS
    }
    
    # 硬件经验
    hw_map = {
        "yes": True,
        "no": False,
        "some": True  # 了解一些也算有基础
    }
    
    # 构建资源约束
    budget_map = {
        "0": "无预算（纯软/模拟）",
        "1k": "1000元以内",
        "5k": "1000-5000元",
        "10k": "5000-10000元",
        "50k": "10000元以上",
        "unknown": "待定"
    }
    
    resources = ResourceConstraint(
        budget=budget_map.get(answers.get("budget", ""), "待定"),
        equipment=[]
    )
    
    # 解析技术栈
    available_techs = []
    if answers.get("available_techs"):
        available_techs = [t.strip() for t in answers["available_techs"].split(",") if t.strip()]
    
    # 构建画像
    profile = UserProfile(
        role=role_map.get(answers.get("role", "other"), UserRole.OTHER),
        organization=answers.get("organization"),
        output_goals=[output_map.get(g, OutputGoal.PRODUCT) for g in answers.get("output_goals", [])],
        field=answers.get("field"),
        tech_level=tech_level_map.get(answers.get("tech_level", "intermediate"), TechLevel.INTERMEDIATE),
        hardware_experience=hw_map.get(answers.get("hardware_experience", "no"), False),
        available_techs=available_techs,
        resources=resources,
        interests=[t.strip() for t in answers.get("interests", "").split(",") if t.strip()] if answers.get("interests") else [],
        metadata={"source": "questionnaire", "answers": answers}
    )
    
    return profile
