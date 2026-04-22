"""双模式路由 - 判断和处理简单/复杂想法"""
from dataclasses import dataclass
from typing import Tuple, Optional
import re


@dataclass
class ModeDecision:
    """模式决策结果"""
    is_simple: bool
    confidence: float  # 0-1
    reasoning: str
    suggested_domain: str = "default"


class DualModeRouter:
    """
    双模式路由器
    
    判断想法是简单（快捷模式）还是复杂（精细模式）
    
    快捷模式特征：
    - 明确的动作词（做、学、买、去）
    - 单一目标
    - 短句（<50字）
    - 无复杂依赖
    
    精细模式特征：
    - 需要多步规划
    - 涉及多个方面
    - 需要资源评估
    - 需要风险分析
    """
    
    # 简单想法动作词
    SIMPLE_ACTIONS = [
        "做", "学", "买", "去", "看", "读", "写", "听",
        "开始", "完成", "整理", "清理", "检查", "准备",
        "提交", "发送", "回复", "打电话", "发消息",
        "跑步", "健身", "休息", "睡觉", "吃饭"
    ]
    
    # 复杂想法关键词
    COMPLEX_INDICATORS = [
        # 多步骤/多方
        "先...再...", "首先...然后...", "第一步...第二步...",
        "需要...和...", "涉及...以及...",
        # 不确定性
        "可能", "也许", "不确定", "不知道", "要不要",
        "要不要", "考虑", "规划", "计划",
        # 评估需求
        "评估", "分析", "比较", "研究", "调研", "调查",
        "值不值得", "好不好", "怎么样",
        # 风险/投入
        "投资", "投入", "风险", "成本", "收益",
        # 大型项目
        "项目", "产品", "系统", "平台", "APP", "网站"
    ]
    
    # 长度阈值
    SIMPLE_MAX_LENGTH = 50
    MEDIUM_MAX_LENGTH = 150
    
    def decide_mode(self, idea_content: str) -> ModeDecision:
        """
        判断想法应该走哪个模式
        
        Args:
            idea_content: 想法内容
            
        Returns:
            模式决策结果
        """
        # 1. 长度检查
        length = len(idea_content)
        length_score = self._evaluate_length(length)
        
        # 2. 动作词检查
        action_score = self._evaluate_actions(idea_content)
        
        # 3. 复杂性指标检查
        complexity_score = self._evaluate_complexity(idea_content)
        
        # 4. 综合判断
        # 简单想法：长度短 + 有明确动作词 + 无复杂指标
        # 复杂想法：有复杂指标 或 长度较长
        
        simple_indicators = action_score + length_score
        complex_indicators = complexity_score
        
        # 边界情况处理
        if length <= 20 and action_score > 0.5:
            # 超短+明确动作 = 简单
            confidence = 0.9
            is_simple = True
            reasoning = f"短句({length}字)且包含明确动作词，识别为简单想法"
        elif complexity_score > 0.6:
            # 明显复杂
            confidence = 0.85
            is_simple = False
            reasoning = "包含复杂规划/评估相关词汇，识别为复杂想法"
        elif length > self.MEDIUM_MAX_LENGTH:
            # 过长
            confidence = 0.8
            is_simple = False
            reasoning = f"长度({length}字)超过中等阈值，需要精细分析"
        elif simple_indicators > complex_indicators * 1.5:
            # 简单指标明显强
            confidence = 0.7
            is_simple = True
            reasoning = "整体特征偏向简单执行类想法"
        elif complex_indicators > simple_indicators:
            # 复杂指标强
            confidence = 0.75
            is_simple = False
            reasoning = "整体特征偏向需要规划的复杂想法"
        else:
            # 模棱两可，保守判断为复杂
            confidence = 0.6
            is_simple = False
            reasoning = "特征不明显，保守判断为复杂想法"
        
        return ModeDecision(
            is_simple=is_simple,
            confidence=confidence,
            reasoning=reasoning,
            suggested_domain="default"  # 后续由 prompt_library 确定
        )
    
    def _evaluate_length(self, length: int) -> float:
        """评估长度得分（短=简单）"""
        if length <= self.SIMPLE_MAX_LENGTH:
            return 1.0
        elif length <= self.MEDIUM_MAX_LENGTH:
            return 0.5
        else:
            return 0.0
    
    def _evaluate_actions(self, content: str) -> float:
        """评估是否包含简单动作词"""
        matches = sum(1 for action in self.SIMPLE_ACTIONS if action in content)
        # 归一化：3个以上匹配认为是简单
        return min(matches / 3, 1.0)
    
    def _evaluate_complexity(self, content: str) -> float:
        """评估复杂性指标"""
        matches = sum(1 for indicator in self.COMPLEX_INDICATORS 
                      if indicator in content.lower())
        # 归一化：2个以上匹配认为是复杂
        return min(matches / 2, 1.0)
    
    def format_quick_response(self, idea_content: str, action: str = "创建任务") -> str:
        """
        格式化快捷模式响应
        
        Args:
            idea_content: 想法内容
            action: 建议的动作
            
        Returns:
            格式化响应
        """
        lines = [
            f"💡 **想法**: {idea_content}",
            "",
            f"✅ 已识别为简单想法",
            f"📋 建议: {action}",
            "",
            "「确认」执行 | 「详情」进入精细模式",
        ]
        return "\n".join(lines)
    
    def format_detailed_response(self, idea_content: str) -> str:
        """
        格式化精细模式响应
        
        Args:
            idea_content: 想法内容
            
        Returns:
            格式化响应
        """
        lines = [
            f"💡 **想法**: {idea_content}",
            "",
            f"🔍 已识别为复杂想法，进入精细评估模式",
            "",
            "将进行：",
            "1. 深度评估（创新性/可行性/价值性）",
            "2. 风险分析",
            "3. 任务拆解",
            "...",
        ]
        return "\n".join(lines)


# 全局实例
_dual_mode_router = None


def get_dual_mode_router() -> DualModeRouter:
    """获取双模式路由器实例"""
    global _dual_mode_router
    if _dual_mode_router is None:
        _dual_mode_router = DualModeRouter()
    return _dual_mode_router
