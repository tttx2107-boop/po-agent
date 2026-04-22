"""深度评估服务"""
from typing import Dict, Any, List, Tuple
from datetime import datetime


class DeepAssessmentService:
    """
    深度评估服务（周级）
    
    评估四个维度：
    1. 创新性 (40%)
    2. 可行性 (35%)  
    3. 价值性 (25%)
    4. 风险评估 (独立参考)
    """
    
    # 评估权重
    WEIGHTS = {
        "innovation": 0.40,
        "feasibility": 0.35,
        "value": 0.25
    }
    
    def assess(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度评估想法
        
        Args:
            idea: 想法数据
            
        Returns:
            评估结果
        """
        content = idea.get("content", "")
        
        # 评估各维度
        innovation = self._assess_innovation(content)
        feasibility = self._assess_feasibility(content)
        value = self._assess_value(content)
        risk = self._assess_risk(content)
        
        # 计算前景得分
        perspective_score = (
            innovation["score"] * self.WEIGHTS["innovation"] +
            feasibility["score"] * self.WEIGHTS["feasibility"] +
            value["score"] * self.WEIGHTS["value"]
        )
        
        # 综合得分 = 前景70% + 风险30%
        overall_score = perspective_score * 0.7 + risk["score"] * 0.3
        
        # 决策建议
        decision = self._make_decision(overall_score, risk["score"])
        
        return {
            "assessment_date": datetime.now().isoformat(),
            "innovation_score": innovation["score"],
            "feasibility_score": feasibility["score"],
            "value_score": value["score"],
            "risk_score": risk["score"],
            "perspective_score": round(perspective_score, 1),
            "overall_score": round(overall_score, 1),
            "decision_level": decision["level"],
            "decision_action": decision["action"],
            "decision_reason": decision["reason"],
            "innovation_detail": innovation["factors"],
            "feasibility_detail": feasibility["factors"],
            "value_detail": value["factors"],
            "risk_detail": risk,
            "assessor": "ai"
        }
    
    def _assess_innovation(self, content: str) -> Dict[str, Any]:
        """评估创新性"""
        score = 50
        factors = []
        
        # 新颖度检查
        if any(word in content for word in ["全新", "首创", "原创", "首次"]):
            score += 15
            factors.append("具有原创性")
        
        # 技术关键词
        tech_words = ["AI", "智能", "自动化", "物联网", "大数据", "机器学习", "深度学习"]
        tech_count = sum(1 for w in tech_words if w in content)
        score += min(tech_count * 5, 15)
        if tech_count > 0:
            factors.append(f"涉及{tech_count}个技术领域")
        
        # 差异化检查
        diff_words = ["区别", "不同", "创新", "突破", "改进", "优化", "差异化"]
        if any(w in content for w in diff_words):
            score += 10
            factors.append("有明显差异化意图")
        
        return {
            "score": min(score, 100),
            "factors": factors or ["中规中矩"]
        }
    
    def _assess_feasibility(self, content: str) -> Dict[str, Any]:
        """评估可行性"""
        score = 50
        factors = []
        
        # 资源关键词
        resource_words = ["资源", "资金", "人力", "技术", "经验", "渠道"]
        resource_count = sum(1 for w in resource_words if w in content)
        if resource_count >= 2:
            score += 15
            factors.append("考虑了资源需求")
        elif resource_count >= 1:
            score += 8
            factors.append("提及部分资源")
        
        # 时间关键词
        if any(word in content for word in ["快速", "简单", "轻量", "MVP", "最小"]):
            score += 10
            factors.append("采用轻量化方案")
        
        # 具体性
        if len(content) >= 50:
            score += 10
            factors.append("描述较为具体")
        
        # 风险词减少分
        risk_words = ["困难", "复杂", "难度", "挑战", "不确定"]
        if any(w in content for w in risk_words):
            score -= 10
            factors.append("意识到潜在困难")
        
        return {
            "score": min(max(score, 0), 100),
            "factors": factors or ["可行性一般"]
        }
    
    def _assess_value(self, content: str) -> Dict[str, Any]:
        """评估价值性"""
        score = 50
        factors = []
        
        # 价值关键词
        value_words = ["价值", "收益", "好处", "帮助", "解决", "需求", "痛点"]
        value_count = sum(1 for w in value_words if w in content)
        score += min(value_count * 8, 24)
        if value_count > 0:
            factors.append("有价值导向")
        
        # 目标导向
        if any(word in content for word in ["目标", "目的", "预期", "效果"]):
            score += 10
            factors.append("有明确目标")
        
        # 用户/市场导向
        market_words = ["用户", "市场", "客户", "受众", "群体", "用户需求"]
        if any(w in content for w in market_words):
            score += 10
            factors.append("考虑目标用户")
        
        return {
            "score": min(score, 100),
            "factors": factors or ["价值一般"]
        }
    
    def _assess_risk(self, content: str) -> Dict[str, Any]:
        """评估风险（实事求是原则）"""
        risks = []
        limitations = []
        assumptions = []
        
        # 识别风险
        risk_keywords = {
            "技术风险": ["不确定", "未知", "探索", "实验", "技术难点"],
            "市场风险": ["竞争", "变化", "波动", "不确定", "市场验证"],
            "资源风险": ["资源有限", "资金不足", "人力不足", "预算紧张"],
            "执行风险": ["困难", "复杂", "周期长", "难度大", "协调难"]
        }
        
        for risk_type, keywords in risk_keywords.items():
            found = [kw for kw in keywords if kw in content]
            if found:
                risks.append({"type": risk_type, "keywords": found})
        
        # 识别局限
        limitation_words = ["只能", "限于", "局限", "难以", "无法做到"]
        limitations = [w for w in limitation_words if w in content]
        
        # 识别假设
        assumption_words = ["假设", "前提", "假定", "如果能"]
        assumptions = [w for w in assumption_words if w in content]
        
        # 风险评分（低风险=高分）
        score = 100 - len(risks) * 10 - len(limitations) * 5
        
        return {
            "score": min(max(score, 0), 100),
            "risks": risks[:3] if risks else [],
            "limitations": limitations[:2] if limitations else [],
            "assumptions": assumptions[:2] if assumptions else []
        }
    
    def _make_decision(self, overall_score: float, risk_score: float) -> Dict[str, str]:
        """生成决策建议"""
        if overall_score >= 75 and risk_score >= 60:
            return {
                "level": "🌟🌟🌟🌟🌟 强烈推荐",
                "action": "优先执行",
                "reason": "综合得分高，风险可控，值得立即行动"
            }
        elif overall_score >= 65 and risk_score >= 55:
            return {
                "level": "🌟🌟🌟🌟 推荐",
                "action": "建议执行",
                "reason": "有较好前景，需关注风险点"
            }
        elif overall_score >= 55:
            return {
                "level": "🌟🌟🌟 观望",
                "action": "持续关注",
                "reason": "价值一般，可以先放一放"
            }
        elif overall_score >= 45:
            return {
                "level": "🌟🌟 暂缓",
                "action": "暂不推进",
                "reason": "风险较高或价值不明显"
            }
        else:
            return {
                "level": "🌟 放弃",
                "action": "优先止损",
                "reason": "综合得分低，建议放弃或彻底重构"
            }


def format_deep_report(assessment: Dict[str, Any], idea_content: str) -> str:
    """格式化深度评估报告"""
    risk = assessment["risk_detail"]
    
    # 风险列表
    risk_str = "暂无明显风险"
    if risk.get("risks"):
        risk_str = "；".join([r["type"] for r in risk["risks"][:2]])
    
    report = f"""📊 深度评估报告

━━━━━━━━━━━━━━━━━━━━

🎯 综合得分：{assessment['overall_score']}/100
📌 决策建议：{assessment['decision_level']}

━━━━━━━━━━━━━━━━━━━━

🌟 前景评估：

• 创新性：{assessment['innovation_score']}分
  └ {assessment['innovation_detail'][0] if assessment['innovation_detail'] else '一般'}

• 可行性：{assessment['feasibility_score']}分
  └ {assessment['feasibility_detail'][0] if assessment['feasibility_detail'] else '一般'}

• 价值性：{assessment['value_score']}分
  └ {assessment['value_detail'][0] if assessment['value_detail'] else '一般'}

⚠️ 风险评估：

• 风险评分：{assessment['risk_score']}分
• 主要风险：{risk_str}

━━━━━━━━━━━━━━━━━━━━

💡 诚实建议：

{assessment['decision_action']}：{assessment['decision_reason']}

━━━━━━━━━━━━━━━━━━━━
"""
    return report
