"""知识沉淀模型"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class KnowledgeType(Enum):
    """知识类型"""
    # 通用知识
    PATTERN = "pattern"          # 执行模式/规律
    LESSON = "lesson"            # 经验教训
    CONCEPT = "concept"          # 核心概念
    METHOD = "method"            # 方法论
    
    # 行业知识
    DOMAIN_FIRE = "domain_fire"           # 消防领域
    DOMAIN_ENERGY = "domain_energy"        # 能源领域
    DOMAIN_AI = "domain_ai"               # AI领域
    DOMAIN_MECHANICAL = "domain_mechanical"  # 机械领域
    DOMAIN_CUSTOM = "domain_custom"        # 自定义行业
    
    # 灵感来源
    INSPIRATION = "inspiration"    # 项目灵感
    REFERENCE = "reference"       # 参考资料


class KnowledgeSource(Enum):
    """知识来源"""
    IDEA_REVIEW = "idea_review"    # 想法复盘
    GITHUB_PROJECT = "github"      # GitHub项目
    MANUAL = "manual"              # 手动添加
    LITERATURE = "literature"     # 文献
    USER_PROFILE = "user"         # 用户提供


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    content: str                    # 核心内容
    title: str = ""                 # 标题/摘要
    type: str = KnowledgeType.CONCEPT.value
    category: str = "general"        # general | industry
    industry: str = ""              # 行业标签
    
    # 来源信息
    source_type: str = KnowledgeSource.MANUAL.value
    source_id: str = ""             # 来源ID (想法ID/项目名等)
    source_content: str = ""        # 原始内容摘要
    
    # 标签
    tags: List[str] = field(default_factory=list)
    domain_tags: List[str] = field(default_factory=list)
    
    # 使用统计
    usage_count: int = 0
    last_used: str = ""
    usefulness_score: float = 0.0   # 实用性评分
    
    # 质量评估
    extraction_confidence: float = 0.0  # 提取置信度
    is_validated: bool = False         # 是否已人工验证
    
    # 关联
    related_ideas: List[str] = field(default_factory=list)  # 关联想法ID
    related_knowledge: List[str] = field(default_factory=list)  # 关联知识ID
    
    # 元数据
    created_at: str = ""
    updated_at: str = ""
    created_by: str = "system"       # system | user
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.title:
            self.title = self.content[:50] + ("..." if len(self.content) > 50 else "")
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        return cls(**data)
    
    def record_usage(self):
        """记录使用"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
    
    def update_usefulness(self, score: float):
        """更新实用性评分"""
        # 指数移动平均
        if self.usefulness_score == 0:
            self.usefulness_score = score
        else:
            self.usefulness_score = self.usefulness_score * 0.7 + score * 0.3
    
    def is_general_knowledge(self) -> bool:
        """是否为通用知识"""
        return self.category == "general" or self.type in [
            KnowledgeType.PATTERN.value,
            KnowledgeType.LESSON.value,
            KnowledgeType.CONCEPT.value,
            KnowledgeType.METHOD.value
        ]
    
    def is_industry_knowledge(self) -> bool:
        """是否为行业知识"""
        return self.category == "industry" or self.type.startswith("domain_")


@dataclass
class KnowledgeCollection:
    """知识集合"""
    entries: List[KnowledgeEntry] = field(default_factory=list)
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeCollection":
        entries = [KnowledgeEntry(**e) for e in data.get("entries", [])]
        return cls(entries=entries, updated_at=data.get("updated_at", ""))


@dataclass
class ExtractionRule:
    """提取规则 - 用于从复盘中自动提取知识"""
    name: str
    pattern: str                    # 匹配模式 (正则或关键词)
    extraction_type: str            # 提取的知识类型
    category: str = "general"       # general | industry
    keywords: List[str] = field(default_factory=list)
    confidence_boost: float = 0.0    # 命中时的置信度加成
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# 默认提取规则
DEFAULT_EXTRACTION_RULES = [
    # 成功经验
    ExtractionRule(
        name="成功模式",
        pattern=r"成功|有效|可行|验证",
        extraction_type=KnowledgeType.PATTERN.value,
        keywords=["成功", "有效", "可行"],
        confidence_boost=0.2
    ),
    # 失败教训
    ExtractionRule(
        name="失败教训",
        pattern=r"失败|问题|风险|错误|踩坑",
        extraction_type=KnowledgeType.LESSON.value,
        keywords=["失败", "问题", "风险", "错误"],
        confidence_boost=0.2
    ),
    # 方法论
    ExtractionRule(
        name="方法论",
        pattern=r"方法|策略|流程|步骤",
        extraction_type=KnowledgeType.METHOD.value,
        keywords=["方法", "策略", "流程"],
        confidence_boost=0.2
    ),
    # 核心概念
    ExtractionRule(
        name="核心概念",
        pattern=r"概念|原理|本质|定义",
        extraction_type=KnowledgeType.CONCEPT.value,
        keywords=["概念", "原理", "本质"],
        confidence_boost=0.1
    ),
]


# 行业领域定义
INDUSTRY_DOMAINS = {
    "fire_safety": {
        "name": "消防安全",
        "tags": ["消防", "火灾", "灭火", "疏散", "防火"],
        "icon": "🚒"
    },
    "energy": {
        "name": "能源石油",
        "tags": ["石油", "钻井", "天然气", "井下", "垂直钻井"],
        "icon": "⛽"
    },
    "ai": {
        "name": "人工智能",
        "tags": ["AI", "LLM", "机器学习", "深度学习", "Agent"],
        "icon": "🤖"
    },
    "mechanical": {
        "name": "机械工程",
        "tags": ["机械", "设计", "制造", "加工"],
        "icon": "⚙️"
    },
    "safety": {
        "name": "安全管理",
        "tags": ["安全", "风险", "隐患", "评估"],
        "icon": "🛡️"
    },
    "knowledge_graph": {
        "name": "知识图谱",
        "tags": ["知识图谱", "KG", "实体", "关系", "图数据库"],
        "icon": "🔗"
    }
}
