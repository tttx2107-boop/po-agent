"""快速评估服务"""
import re
from typing import Dict, Any, List
from datetime import datetime


class QuickAssessmentService:
    """快速评估服务（分钟级）"""
    
    # 领域关键词映射
    DOMAIN_KEYWORDS = {
        "消防": ["消防", "火灾", "灭火", "疏散", "烟感", "喷淋", "防火", "危化"],
        "副业": ["副业", "兼职", "创业", "变现", "收入", "赚钱", "电商", "自媒体", "短视频"],
        "学习": ["学习", "课程", "培训", "读书", "研究", "论文", "课题", "考证"],
        "技术": ["开发", "代码", "系统", "AI", "模型", "算法", "数据", "爬虫", "自动化"],
        "生活": ["健康", "健身", "旅行", "理财", "保险", "家庭", "孩子"],
    }
    
    # 意图类型识别
    INTENT_PATTERNS = {
        "command": [
            r"^查看", r"^统计", r"^帮助", r"^设置", r"^立即", r"^完成",
            r"^删除", r"^编辑", r"^更新", r"^同步", r"^备份"
        ],
        "query": [
            r"^(怎么|如何|为什么|什么|哪|是否)", r"^\?",
        ],
    }
    
    def assess(self, content: str) -> Dict[str, Any]:
        """
        快速评估
        
        Args:
            content: 想法内容
            
        Returns:
            评估结果
        """
        return {
            "intent_type": self._detect_intent(content),
            "domain_tags": self._extract_tags(content),
            "completeness": self._check_completeness(content),
            "keywords_note": self._generate_note(content),
            "assessment_time": datetime.now().isoformat()
        }
    
    def _detect_intent(self, content: str) -> str:
        """识别意图类型"""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    return intent
        return "idea"
    
    def _extract_tags(self, content: str) -> List[str]:
        """提取领域标签"""
        tags = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    tags.append(domain)
                    break
        return list(set(tags))
    
    def _check_completeness(self, content: str) -> float:
        """检查想法完整性 (0-1)"""
        score = 0.0
        
        # 长度检查
        if len(content) >= 20:
            score += 0.3
        elif len(content) >= 10:
            score += 0.15
        
        # 明确主题
        if any(char in content for char in "：:"):
            score += 0.2
        
        # 具体描述词
        if any(word in content for word in ["我想", "想做", "计划", "考虑", "觉得", "目标"]):
            score += 0.2
        
        # 问题导向
        if any(word in content for word in ["解决", "问题", "痛点", "需求"]):
            score += 0.2
        
        # 资源/时间导向
        if any(word in content for word in ["资源", "资金", "时间", "周期", "预算"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_note(self, content: str) -> str:
        """生成评估备注"""
        completeness = self._check_completeness(content)
        
        if completeness < 0.5:
            return "建议补充：具体目标、预期效果、所需资源等"
        elif completeness < 0.7:
            return "可以进一步完善，建议补充启动条件"
        return "想法较为完整"


def format_quick_result(assessment: Dict[str, Any], content: str) -> str:
    """格式化快速评估结果"""
    tags_str = "、".join(assessment["domain_tags"]) or "待定"
    completeness_pct = int(assessment["completeness"] * 100)
    
    return f"""💭 想法录入成功

📋 快速评估结果：
• 类型：{assessment['intent_type']}
• 领域：{tags_str}
• 完整性：{completeness_pct}%（{assessment['keywords_note']}）
• 状态：已加入想法库，等待深度评估

📝 后续操作：
• 「查看想法」- 查看想法列表
• 「立即评估」- 触发深度评估"""
