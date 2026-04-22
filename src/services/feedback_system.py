"""三层反馈系统 - 输入层/执行层/战略层"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class FeedbackLevel(Enum):
    """反馈级别"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    SUCCESS = "success"    # 成功


class FeedbackCategory(Enum):
    """反馈类别"""
    # 文件级（输入层）
    FORMAT = "format"                    # 格式问题
    COMPLETENESS = "completeness"        # 完整性问题
    DUPLICATE = "duplicate"              # 重复检测
    CLARITY = "clarity"                 # 清晰度问题
    
    # 任务级（执行层）
    BLOCKER = "blocker"                  # 阻塞问题
    PROGRESS = "progress"               # 进度问题
    ALIGNMENT = "alignment"             # 目标对齐问题
    QUALITY = "quality"                 # 质量问题
    
    # 平台级（战略层）
    PATTERN = "pattern"                 # 用户习惯模式
    TREND = "trend"                     # 趋势洞察
    SUGGESTION = "suggestion"           # 改进建议


@dataclass
class Feedback:
    """反馈项"""
    category: str
    level: str
    title: str
    message: str
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def format(self) -> str:
        """格式化反馈消息"""
        emoji = {
            FeedbackLevel.INFO.value: "ℹ️",
            FeedbackLevel.WARNING.value: "⚠️",
            FeedbackLevel.ERROR.value: "❌",
            FeedbackLevel.SUCCESS.value: "✅",
        }.get(self.level, "ℹ️")
        
        lines = [f"{emoji} **{self.title}**", f"   {self.message}"]
        
        if self.suggestions:
            lines.append("   💡 建议：")
            for s in self.suggestions:
                lines.append(f"   - {s}")
        
        return "\n".join(lines)


@dataclass
class FeedbackReport:
    """反馈报告"""
    feedbacks: List[Feedback] = field(default_factory=list)
    
    @property
    def has_warnings(self) -> bool:
        return any(f.level == FeedbackLevel.WARNING.value for f in self.feedbacks)
    
    @property
    def has_errors(self) -> bool:
        return any(f.level == FeedbackLevel.ERROR.value for f in self.feedbacks)
    
    @property
    def warnings(self) -> List[Feedback]:
        return [f for f in self.feedbacks if f.level == FeedbackLevel.WARNING.value]
    
    @property
    def errors(self) -> List[Feedback]:
        return [f for f in self.feedbacks if f.level == FeedbackLevel.ERROR.value]
    
    def format(self) -> str:
        """格式化报告"""
        if not self.feedbacks:
            return "✅ 无反馈问题"
        
        lines = []
        for f in self.feedbacks:
            lines.append(f.format())
            lines.append("")
        
        return "\n".join(lines)


class ThreeLayerFeedbackSystem:
    """
    三层反馈系统
    
    实现三层反馈机制：
    1. 文件级（输入层） - 想法录入时的检查
    2. 任务级（执行层） - 任务执行时的监控
    3. 平台级（战略层） - 定期分析和建议
    """
    
    def __init__(self):
        self._history: List[Feedback] = []
    
    # ==================== 文件级检查（输入层） ====================
    
    def file_level_check(self, idea_content: str, existing_ideas: List[Dict] = None) -> FeedbackReport:
        """
        文件级检查 - 想法录入时
        
        检查项：
        - 格式规范
        - 完整性
        - 重复检测
        - 清晰度
        """
        feedbacks = []
        
        # 1. 格式检查
        feedbacks.extend(self._check_format(idea_content))
        
        # 2. 完整性检查
        feedbacks.extend(self._check_completeness(idea_content))
        
        # 3. 重复检查
        if existing_ideas:
            feedbacks.extend(self._check_duplicates(idea_content, existing_ideas))
        
        # 4. 清晰度检查
        feedbacks.extend(self._check_clarity(idea_content))
        
        return FeedbackReport(feedbacks=feedbacks)
    
    def _check_format(self, content: str) -> List[Feedback]:
        """检查格式"""
        feedbacks = []
        
        # 检查是否为空
        if not content or not content.strip():
            feedbacks.append(Feedback(
                category=FeedbackCategory.FORMAT.value,
                level=FeedbackLevel.ERROR.value,
                title="内容为空",
                message="想法内容不能为空",
                suggestions=["请输入具体的想法描述"]
            ))
        
        # 检查是否过长
        if len(content) > 500:
            feedbacks.append(Feedback(
                category=FeedbackCategory.FORMAT.value,
                level=FeedbackLevel.WARNING.value,
                title="内容较长",
                message=f"内容长度 {len(content)} 字，建议精简",
                suggestions=["保留核心要点，详细说明可在后续补充"]
            ))
        
        return feedbacks
    
    def _check_completeness(self, content: str) -> List[Feedback]:
        """检查完整性"""
        feedbacks = []
        
        # 缺少目标
        target_indicators = ["为了", "目标是", "想", "做", "开发", "创建"]
        has_target = any(ind in content for ind in target_indicators)
        
        if not has_target and len(content) < 30:
            feedbacks.append(Feedback(
                category=FeedbackCategory.COMPLETENESS.value,
                level=FeedbackLevel.WARNING.value,
                title="目标不够明确",
                message="建议说明具体要做什么或达成什么目标",
                suggestions=["补充：这个想法的目标是什么？"]
            ))
        
        # 缺少时间和资源信息
        time_indicators = ["时间", "多久", "deadline", "周", "天", "小时"]
        resource_indicators = ["资源", "人力", "预算", "资金", "设备"]
        
        if len(content) > 50:
            has_time = any(ind in content for ind in time_indicators)
            has_resource = any(ind in content for ind in resource_indicators)
            
            if not has_time:
                feedbacks.append(Feedback(
                    category=FeedbackCategory.COMPLETENESS.value,
                    level=FeedbackLevel.INFO.value,
                    title="可补充时间预期",
                    message="未提及预计投入时间",
                    suggestions=["可以说明预计投入多少时间/精力"]
                ))
            
            if not has_resource:
                feedbacks.append(Feedback(
                    category=FeedbackCategory.COMPLETENESS.value,
                    level=FeedbackLevel.INFO.value,
                    title="可补充资源需求",
                    message="未提及资源需求",
                    suggestions=["可以说明需要什么资源支持"]
                ))
        
        return feedbacks
    
    def _check_duplicates(self, content: str, existing_ideas: List[Dict]) -> List[Feedback]:
        """检查重复"""
        feedbacks = []
        
        # 简单的关键词重复检测
        content_keywords = self._extract_keywords(content)
        
        for idea in existing_ideas:
            existing_keywords = self._extract_keywords(idea.get("content", ""))
            
            # 计算相似度
            overlap = len(content_keywords & existing_keywords)
            if overlap >= 3 and len(content_keywords) > 0:
                similarity = overlap / max(len(content_keywords), len(existing_keywords))
                if similarity > 0.5:
                    feedbacks.append(Feedback(
                        category=FeedbackCategory.DUPLICATE.value,
                        level=FeedbackLevel.WARNING.value,
                        title="可能存在重复想法",
                        message=f"与已有想法相似度较高：「{idea.get('content', '')[:30]}...」",
                        suggestions=[
                            "确认是否为同一想法",
                            "如果是升级版，请更新原想法而非创建新的",
                            "如果是独立想法，请补充差异化说明"
                        ],
                        metadata={"similar_idea_id": idea.get("id")}
                    ))
                    break
        
        return feedbacks
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词"""
        # 简单分词：按空格和标点分割，过滤短词
        import re
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', text.lower())
        # 去除常见停用词
        stopwords = {"的", "了", "在", "是", "和", "与", "或", "等", "这个", "一个", "我", "想", "做"}
        return set(words) - stopwords
    
    def _check_clarity(self, content: str) -> List[Feedback]:
        """检查清晰度"""
        feedbacks = []
        
        # 模糊词汇检测
        vague_words = ["可能", "也许", "大概", "差不多", "看看", "试试"]
        vague_count = sum(1 for w in vague_words if w in content)
        
        if vague_count >= 2:
            feedbacks.append(Feedback(
                category=FeedbackCategory.CLARITY.value,
                level=FeedbackLevel.WARNING.value,
                title="描述较模糊",
                message="包含较多不确定表述，可能导致执行困难",
                suggestions=[
                    "将「可能」替换为具体计划",
                    "将「试试」替换为明确行动"
                ]
            ))
        
        # 检查是否太抽象
        action_words = ["做", "学", "买", "去", "写", "开发", "设计", "规划"]
        has_action = any(w in content for w in action_words)
        
        abstract_words = ["优化", "改进", "提升", "加强", "完善"]
        abstract_count = sum(1 for w in abstract_words if w in content)
        
        if abstract_count >= 2 and not has_action:
            feedbacks.append(Feedback(
                category=FeedbackCategory.CLARITY.value,
                level=FeedbackLevel.WARNING.value,
                title="描述偏抽象",
                message="建议补充具体行动或可量化的目标",
                suggestions=["将抽象目标转化为具体行动", "明确期望达成的结果"]
            ))
        
        return feedbacks
    
    # ==================== 任务级检查（执行层） ====================
    
    def task_level_check(
        self,
        task_title: str,
        task_status: str,
        blocked_days: int = 0,
        overdue_days: int = 0,
        progress: float = 0.0
    ) -> FeedbackReport:
        """
        任务级检查 - 任务执行时
        
        检查项：
        - 阻塞检查
        - 进度检查
        - 目标对齐检查
        """
        feedbacks = []
        
        # 1. 阻塞检查
        if blocked_days > 0:
            feedbacks.extend(self._check_blockers(task_title, blocked_days))
        
        # 2. 逾期检查
        if overdue_days > 0:
            feedbacks.extend(self._check_overdue(task_title, overdue_days))
        
        # 3. 进度检查
        feedbacks.extend(self._check_progress(task_title, task_status, progress))
        
        return FeedbackReport(feedbacks=feedbacks)
    
    def _check_blockers(self, task_title: str, blocked_days: int) -> List[Feedback]:
        """检查阻塞情况"""
        feedbacks = []
        
        if blocked_days >= 3:
            level = FeedbackLevel.ERROR.value
            title = "任务长时间阻塞"
        else:
            level = FeedbackLevel.WARNING.value
            title = "任务被阻塞"
        
        feedbacks.append(Feedback(
            category=FeedbackCategory.BLOCKER.value,
            level=level,
            title=title,
            message=f"「{task_title}」已阻塞 {blocked_days} 天",
            suggestions=[
                "分析阻塞原因",
                "是否有替代方案？",
                "需要他人协助吗？",
                "考虑缩小范围或延长时间"
            ],
            metadata={"blocked_days": blocked_days}
        ))
        
        return feedbacks
    
    def _check_overdue(self, task_title: str, overdue_days: int) -> List[Feedback]:
        """检查逾期情况"""
        feedbacks = []
        
        feedbacks.append(Feedback(
            category=FeedbackCategory.PROGRESS.value,
            level=FeedbackLevel.WARNING.value,
            title="任务已逾期",
            message=f"「{task_title}」已逾期 {overdue_days} 天",
            suggestions=[
                "重新评估任务可行性",
                "调整后续计划",
                "更新预期完成时间"
            ],
            metadata={"overdue_days": overdue_days}
        ))
        
        return feedbacks
    
    def _check_progress(self, task_title: str, task_status: str, progress: float) -> List[Feedback]:
        """检查进度情况"""
        feedbacks = []
        
        # 正在进行中但进度为0
        if task_status == "in_progress" and progress == 0:
            feedbacks.append(Feedback(
                category=FeedbackCategory.PROGRESS.value,
                level=FeedbackLevel.WARNING.value,
                title="任务无进度",
                message=f"「{task_title}」标记为进行中但无进度更新",
                suggestions=[
                    "是否需要更新进度？",
                    "是否有实际产出？",
                    "是否遇到了问题？"
                ]
            ))
        
        # 进度停滞
        if progress > 0 and progress < 100 and task_status != "in_progress":
            feedbacks.append(Feedback(
                category=FeedbackCategory.PROGRESS.value,
                level=FeedbackLevel.INFO.value,
                title="任务状态待更新",
                message=f"「{task_title}」有进度({progress}%)但状态不是进行中",
                suggestions=["确认任务当前状态"]
            ))
        
        return feedbacks
    
    # ==================== 平台级分析（战略层） ====================
    
    def platform_level_analysis(
        self,
        ideas: List[Dict],
        tasks: List[Dict]
    ) -> FeedbackReport:
        """
        平台级分析 - 定期分析
        
        分析项：
        - 用户习惯模式
        - 趋势洞察
        - 改进建议
        """
        feedbacks = []
        
        # 1. 用户习惯分析
        feedbacks.extend(self._analyze_user_patterns(ideas, tasks))
        
        # 2. 趋势洞察
        feedbacks.extend(self._analyze_trends(ideas, tasks))
        
        # 3. 改进建议
        feedbacks.extend(self._generate_suggestions(ideas, tasks))
        
        return FeedbackReport(feedbacks=feedbacks)
    
    def _analyze_user_patterns(
        self,
        ideas: List[Dict],
        tasks: List[Dict]
    ) -> List[Feedback]:
        """分析用户习惯模式"""
        feedbacks = []
        
        # 分析创建时间模式
        if len(ideas) >= 5:
            # 统计各状态的分布
            status_counts = {}
            for idea in ideas:
                status = idea.get("status", "new")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # 检查是否有太多想法在某个状态
            for status, count in status_counts.items():
                if status == "new" and count >= 5:
                    feedbacks.append(Feedback(
                        category=FeedbackCategory.PATTERN.value,
                        level=FeedbackLevel.INFO.value,
                        title="想法积累较多",
                        message=f"有 {count} 个新想法待评估",
                        suggestions=["建议进行批量评估", "「立即评估」开始深度评估"]
                    ))
                    break
        
        return feedbacks
    
    def _analyze_trends(
        self,
        ideas: List[Dict],
        tasks: List[Dict]
    ) -> List[Feedback]:
        """分析趋势"""
        feedbacks = []
        
        # 分析完成率
        if len(ideas) >= 3:
            completed = len([i for i in ideas if i.get("status") == "completed"])
            total = len(ideas)
            completion_rate = completed / total
            
            if completion_rate < 0.3:
                feedbacks.append(Feedback(
                    category=FeedbackCategory.TREND.value,
                    level=FeedbackLevel.WARNING.value,
                    title="完成率偏低",
                    message=f"完成率 {completion_rate:.0%}，可能需要调整策略",
                    suggestions=[
                        "是否有些想法过于复杂？",
                        "建议优先完成小而确定的任务",
                        "考虑放弃或暂缓长期未动的想法"
                    ]
                ))
        
        return feedbacks
    
    def _generate_suggestions(
        self,
        ideas: List[Dict],
        tasks: List[Dict]
    ) -> List[Feedback]:
        """生成改进建议"""
        feedbacks = []
        
        # 基于分析生成建议
        active_tasks = [t for t in tasks if t.get("status") == "in_progress"]
        
        if len(active_tasks) > 5:
            feedbacks.append(Feedback(
                category=FeedbackCategory.SUGGESTION.value,
                level=FeedbackLevel.INFO.value,
                title="并行任务较多",
                message=f"当前有 {len(active_tasks)} 个并行进行中的任务",
                suggestions=[
                    "考虑聚焦而非分散",
                    "优先完成最重要的1-2个任务"
                ]
            ))
        
        return feedbacks


# 全局实例
_feedback_system = None


def get_feedback_system() -> ThreeLayerFeedbackSystem:
    """获取反馈系统实例"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = ThreeLayerFeedbackSystem()
    return _feedback_system
