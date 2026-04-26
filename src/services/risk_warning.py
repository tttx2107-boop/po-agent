"""风险预警服务 - Risk Warning Service"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(Enum):
    """风险类型"""
    SCOPE_CREEP = "scope_creep"           # 范围蔓延
    RESOURCE_SHORTAGE = "resource_shortage"  # 资源不足
    TECHNICAL_BLOCK = "technical_block"      # 技术阻塞
    TIME_OVERRUN = "time_overrun"            # 时间超期
    QUALITY_ISSUE = "quality_issue"          # 质量问题
    DEPENDENCY_RISK = "dependency_risk"     # 依赖风险
    STAKEHOLDER = "stakeholder"             # 干系人风险


@dataclass
class RiskItem:
    """风险项"""
    id: str
    idea_id: str
    risk_type: str
    
    # 描述
    title: str
    description: str
    
    # 评估
    level: str = RiskLevel.MEDIUM.value  # low, medium, high, critical
    probability: float = 0.5  # 发生概率 0-1
    impact: float = 0.5  # 影响程度 0-1
    
    # 应对
    mitigation: str = ""  # 应对措施
    contingency: str = ""  # 应急预案
    
    # 状态
    status: str = "active"  # active, monitoring, resolved, accepted
    created_at: str = ""
    resolved_at: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def calculate_score(self) -> float:
        """计算风险评分 = 概率 * 影响"""
        return self.probability * self.impact

    def get_level_display(self) -> str:
        """风险等级展示"""
        level_map = {
            RiskLevel.LOW.value: "🟢 低",
            RiskLevel.MEDIUM.value: "🟡 中",
            RiskLevel.HIGH.value: "🟠 高",
            RiskLevel.CRITICAL.value: "🔴 极高"
        }
        return level_map.get(self.level, self.level)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "idea_id": self.idea_id,
            "risk_type": self.risk_type,
            "title": self.title,
            "description": self.description,
            "level": self.level,
            "probability": self.probability,
            "impact": self.impact,
            "score": self.calculate_score(),
            "mitigation": self.mitigation,
            "contingency": self.contingency,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "notes": self.notes
        }


@dataclass 
class RiskReport:
    """风险报告"""
    idea_id: str
    idea_content: str
    
    # 风险列表
    risks: List[RiskItem] = field(default_factory=list)
    
    # 统计
    total_risks: int = 0
    high_risks: int = 0
    avg_score: float = 0.0
    
    # 建议
    recommendations: List[str] = field(default_factory=list)
    
    def format_report(self) -> str:
        """格式化报告"""
        lines = [f"## ⚠️ 风险预警报告\n"]
        lines.append(f"**想法**: {self.idea_content[:50]}...\n")
        
        if not self.risks:
            lines.append("\n✅ 暂未发现明显风险\n")
            return "".join(lines)
        
        # 统计
        lines.append(f"\n### 📊 风险概览\n")
        lines.append(f"- 总风险数: {self.total_risks}\n")
        lines.append(f"- 高风险: {self.high_risks}\n")
        lines.append(f"- 平均风险分: {self.avg_score:.2f}\n")
        
        # 按等级分组
        critical = [r for r in self.risks if r.level == RiskLevel.CRITICAL.value]
        high = [r for r in self.risks if r.level == RiskLevel.HIGH.value]
        medium = [r for r in self.risks if r.level == RiskLevel.MEDIUM.value]
        low = [r for r in self.risks if r.level == RiskLevel.LOW.value]
        
        for title, risk_list in [
            ("🔴 极高风险", critical),
            ("🟠 高风险", high),
            ("🟡 中风险", medium),
            ("🟢 低风险", low)
        ]:
            if risk_list:
                lines.append(f"\n### {title}\n")
                for risk in risk_list:
                    lines.append(f"- **{risk.title}**\n")
                    lines.append(f"  - 描述: {risk.description}\n")
                    if risk.mitigation:
                        lines.append(f"  - 应对: {risk.mitigation}\n")
        
        if self.recommendations:
            lines.append(f"\n### 💡 建议\n")
            for rec in self.recommendations:
                lines.append(f"- {rec}\n")
        
        return "".join(lines)


class RiskWarningService:
    """
    风险预警服务
    
    自动识别和跟踪项目风险
    """
    
    # 风险关键词
    RISK_KEYWORDS = {
        RiskType.SCOPE_CREEP.value: ["扩展", "加功能", "需求变更", "更多", "额外"],
        RiskType.RESOURCE_SHORTAGE.value: ["资源", "人手", "资金", "预算", "人力"],
        RiskType.TECHNICAL_BLOCK.value: ["技术难点", "卡住", "不会", "不确定", "复杂"],
        RiskType.TIME_OVERRUN.value: ["时间紧", "赶", "deadline", "延期", "超期"],
        RiskType.QUALITY_ISSUE.value: ["质量", "bug", "问题", "修复", "返工"],
        RiskType.DEPENDENCY_RISK.value: ["依赖", "第三方", "外包", "等待"],
    }
    
    # 风险模式
    RISK_PATTERNS = [
        # (pattern, risk_type, level, reason)
        (r"(第一次|首次|首创|全新)", RiskType.TECHNICAL_BLOCK.value, "medium",
         "涉及全新领域，可能遇到未知技术风险"),
        (r"(时间紧|很赶|紧急|deadline)", RiskType.TIME_OVERRUN.value, "high",
         "时间压力较大，可能超期"),
        (r"(不确定|不知道|可能)", RiskType.SCOPE_CREEP.value, "medium",
         "需求不明确，可能导致范围蔓延"),
        (r"(没钱|预算少|资源有限)", RiskType.RESOURCE_SHORTAGE.value, "high",
         "资源受限，可能影响项目进度"),
        (r"(AI|机器学习|区块链|大数据)", RiskType.TECHNICAL_BLOCK.value, "medium",
         "涉及新技术，技术难度较高"),
        (r"(团队|协作|多人)", RiskType.DEPENDENCY_RISK.value, "low",
         "多人协作存在沟通风险"),
    ]
    
    def __init__(self):
        self._risks: List[RiskItem] = []
    
    def analyze_idea(self, idea_content: str, idea_id: str = "") -> RiskReport:
        """
        分析想法的风险
        
        Args:
            idea_content: 想法内容
            idea_id: 想法 ID
            
        Returns:
            风险报告
        """
        risks = []
        
        # 1. 基于关键词检测
        for risk_type, keywords in self.RISK_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in idea_content]
            if matches:
                # 根据匹配数量和类型确定风险等级
                if risk_type in [RiskType.TECHNICAL_BLOCK.value, RiskType.RESOURCE_SHORTAGE.value]:
                    level = RiskLevel.HIGH.value if len(matches) > 1 else RiskLevel.MEDIUM.value
                else:
                    level = RiskLevel.MEDIUM.value
                
                risks.append(RiskItem(
                    id=f"risk_{datetime.now().strftime('%H%M%S')}",
                    idea_id=idea_id,
                    risk_type=risk_type,
                    title=self._get_risk_title(risk_type),
                    description=f"检测到相关关键词: {', '.join(matches)}",
                    level=level,
                    probability=0.4,
                    impact=0.6,
                    mitigation=self._get_mitigation(risk_type)
                ))
        
        # 2. 基于模式匹配
        for pattern, risk_type, level, reason in self.RISK_PATTERNS:
            if re.search(pattern, idea_content):
                # 检查是否已有同类风险
                existing = [r for r in risks if r.risk_type == risk_type]
                if not existing:
                    risks.append(RiskItem(
                        id=f"risk_{datetime.now().strftime('%H%M%S%f')}",
                        idea_id=idea_id,
                        risk_type=risk_type,
                        title=self._get_risk_title(risk_type),
                        description=reason,
                        level=level,
                        probability=0.5,
                        impact=0.6,
                        mitigation=self._get_mitigation(risk_type)
                    ))
        
        # 3. 存储风险
        for risk in risks:
            self._risks.append(risk)
        
        # 4. 生成报告
        return self._generate_report(idea_id, idea_content, risks)
    
    def get_idea_risks(self, idea_id: str) -> List[RiskItem]:
        """获取想法的风险"""
        return [r for r in self._risks if r.idea_id == idea_id]
    
    def get_active_risks(self) -> List[RiskItem]:
        """获取活跃风险"""
        return [r for r in self._risks if r.status == "active"]
    
    def resolve_risk(self, risk_id: str, notes: str = ""):
        """解决风险"""
        for risk in self._risks:
            if risk.id == risk_id:
                risk.status = "resolved"
                risk.resolved_at = datetime.now().isoformat()
                if notes:
                    risk.notes = notes
                break
    
    def get_high_risks(self) -> List[RiskItem]:
        """获取高风险项"""
        high_levels = [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
        return [r for r in self._risks if r.level in high_levels and r.status == "active"]
    
    def _generate_report(
        self, 
        idea_id: str, 
        idea_content: str, 
        risks: List[RiskItem]
    ) -> RiskReport:
        """生成风险报告"""
        if not risks:
            return RiskReport(
                idea_id=idea_id,
                idea_content=idea_content,
                risks=[],
                recommendations=["继续保持，当前无明显风险"]
            )
        
        # 统计
        total = len(risks)
        high_count = len([r for r in risks if r.level in 
                        [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]])
        avg_score = sum(r.calculate_score() for r in risks) / total
        
        # 建议
        recommendations = self._generate_recommendations(risks)
        
        return RiskReport(
            idea_id=idea_id,
            idea_content=idea_content,
            risks=risks,
            total_risks=total,
            high_risks=high_count,
            avg_score=avg_score,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, risks: List[RiskItem]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 按类型统计
        risk_types = [r.risk_type for r in risks]
        
        if RiskType.SCOPE_CREEP.value in risk_types:
            recommendations.append("建议明确需求范围，使用 MVP 原则控制功能蔓延")
        
        if RiskType.RESOURCE_SHORTAGE.value in risk_types:
            recommendations.append("建议提前规划资源，识别可获取的外部支持")
        
        if RiskType.TECHNICAL_BLOCK.value in risk_types:
            recommendations.append("建议先进行技术调研，降低技术不确定性")
        
        if RiskType.TIME_OVERRUN.value in risk_types:
            recommendations.append("建议设置更合理的时间节点，预留缓冲时间")
        
        high_risks = [r for r in risks if r.level in 
                      [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]]
        if len(high_risks) > 2:
            recommendations.append("⚠️ 高风险较多，建议先处理最高风险项")
        
        return recommendations
    
    def _get_risk_title(self, risk_type: str) -> str:
        """获取风险标题"""
        titles = {
            RiskType.SCOPE_CREEP.value: "需求范围蔓延风险",
            RiskType.RESOURCE_SHORTAGE.value: "资源不足风险",
            RiskType.TECHNICAL_BLOCK.value: "技术阻塞风险",
            RiskType.TIME_OVERRUN.value: "时间超期风险",
            RiskType.QUALITY_ISSUE.value: "质量风险",
            RiskType.DEPENDENCY_RISK.value: "依赖风险"
        }
        return titles.get(risk_type, "其他风险")
    
    def _get_mitigation(self, risk_type: str) -> str:
        """获取应对措施"""
        mitigations = {
            RiskType.SCOPE_CREEP.value: "采用 MVP 原则，核心功能优先，控制范围蔓延",
            RiskType.RESOURCE_SHORTAGE.value: "提前规划资源，考虑资源复用或外部合作",
            RiskType.TECHNICAL_BLOCK.value: "先进行技术验证，拆分技术难点，寻求专家支持",
            RiskType.TIME_OVERRUN.value: "设置里程碑，定期检查进度，预留缓冲时间",
            RiskType.QUALITY_ISSUE.value: "建立测试规范，尽早发现问题，及时修复",
            RiskType.DEPENDENCY_RISK.value: "明确依赖关系，设置检查点，准备替代方案"
        }
        return mitigations.get(risk_type, "持续关注，及时应对")
