"""GitHub项目模型"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class GitHubRepo:
    """GitHub仓库"""
    # 基础信息
    owner: str
    name: str
    full_name: str
    description: str = ""
    url: str = ""
    homepage: str = ""
    
    # 统计
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    language: str = ""
    
    # 时间
    created_at: str = ""
    updated_at: str = ""
    pushed_at: str = ""
    
    # 评分
    quality_score: float = 0.0
    relevance_score: float = 0.0
    
    # 元信息
    topics: List[str] = field(default_factory=list)
    license: str = ""
    
    # 评估
    assessment: str = "PENDING"  # PENDING, REVIEWED, INTERESTING, INTEGRATED, REJECTED
    assessment_notes: str = ""
    integration_suggestion: str = ""  # 集成建议
    
    # 追踪
    discovered_at: str = ""
    last_checked: str = ""
    change_log: List[Dict[str, Any]] = field(default_factory=list)  # 更新历史
    
    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()
        if not self.url:
            self.url = f"https://github.com/{self.full_name}"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_github_api(cls, data: Dict[str, Any]) -> "GitHubRepo":
        """从GitHub API响应创建"""
        return cls(
            owner=data.get("owner", {}).get("login", ""),
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description", "") or "",
            url=data.get("html_url", ""),
            homepage=data.get("homepage", "") or "",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            watchers=data.get("watchers_count", 0),
            open_issues=data.get("open_issues_count", 0),
            language=data.get("language", "") or "",
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            pushed_at=data.get("pushed_at", ""),
            topics=data.get("topics", []) or [],
            license=data.get("license", {}).get("name", "") if data.get("license") else "",
            discovered_at=datetime.now().isoformat(),
            last_checked=datetime.now().isoformat(),
        )
    
    def get_stars_display(self) -> str:
        """格式化stars显示"""
        if self.stars >= 1000:
            return f"{self.stars/1000:.1f}k"
        return str(self.stars)
    
    def is_recently_updated(self, days: int = 30) -> bool:
        """是否近期更新"""
        if not self.pushed_at:
            return False
        pushed = datetime.fromisoformat(self.pushed_at.replace("Z", "+00:00"))
        delta = datetime.now(pushed.tzinfo) - pushed
        return delta.days <= days
    
    def get_change_level(self) -> str:
        """获取变更等级"""
        if not self.change_log:
            return "NEW"
        return f"UPDATED({len(self.change_log)})"


@dataclass
class GitHubMonitorConfig:
    """监测配置"""
    # 监测模式
    mode: str = "trending"  # trending, keywords, both
    
    # 关键词配置
    keywords: List[str] = field(default_factory=list)  # ["ai agent", "langchain", "autonomous agent"]
    keywords_per_page: int = 30
    
    # Trending配置
    trending_languages: List[str] = field(default_factory=list)  # ["Python", "JavaScript", "TypeScript"]
    trending_since: str = "daily"  # daily, weekly, monthly
    
    # 质量过滤
    min_stars: int = 50  # 最低stars
    min_forks: int = 5   # 最低forks
    exclude_topics: List[str] = field(default_factory=list)  # 排除的话题
    preferred_licenses: List[str] = field(default_factory=list)  # 偏好的许可证
    
    # 评分权重
    star_weight: float = 0.4
    fork_weight: float = 0.2
    recency_weight: float = 0.2
    relevance_weight: float = 0.2
    
    # 通知
    notify_on_discovery: bool = True
    min_notify_score: float = 7.0  # 低于此分数不通知
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
