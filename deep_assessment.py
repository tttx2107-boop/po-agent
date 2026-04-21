"""深度评估模块（周级）"""
import json
from datetime import datetime
from typing import Dict, Any, List

class DeepAssessment:
    """
    深度评估 - 周级
    
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
            "innovation": innovation,
            "feasibility": feasibility,
            "value": value,
            "risk": risk,
            "perspective_score": round(perspective_score, 1),
            "overall_score": round(overall_score, 1),
            "decision": decision,
            "assessor": "ai"
        }
    
    def _assess_innovation(self, content: str) -> Dict[str, Any]:
        """评估创新性"""
        score = 50  # 基础分
        factors = []
        
        # 新颖度检查
        if any(word in content for word in ["全新", "首创", "原创", "首次"]):
            score += 15
            factors.append("具有原创性")
        
        # 技术关键词
        tech_words = ["AI", "智能", "自动化", "物联网", "大数据", "机器学习"]
        tech_count = sum(1 for w in tech_words if w in content)
        score += min(tech_count * 5, 15)
        if tech_count > 0:
            factors.append(f"涉及{tech_count}个技术领域")
        
        # 差异化检查
        diff_words = ["区别", "不同", "创新", "突破", "改进", "优化"]
        if any(w in content for w in diff_words):
            score += 10
            factors.append("有明显差异化意图")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "summary": f"创新性评估：{factors[0] if factors else '中规中矩'}"
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
            "factors": factors,
            "summary": f"可行性评估：{'可行' if score >= 60 else '需进一步验证'}"
        }
    
    def _assess_value(self, content: str) -> Dict[str, Any]:
        """评估价值性"""
        score = 50
        factors = []
        
        # 价值关键词
        value_words = ["价值", "收益", "好处", "帮助", "解决", "需求"]
        value_count = sum(1 for w in value_words if w in content)
        score += min(value_count * 8, 24)
        if value_count > 0:
            factors.append("有价值导向")
        
        # 目标导向
        if any(word in content for word in ["目标", "目的", "预期", "效果"]):
            score += 10
            factors.append("有明确目标")
        
        # 用户/市场导向
        market_words = ["用户", "市场", "客户", "受众", "群体"]
        if any(w in content for w in market_words):
            score += 10
            factors.append("考虑目标用户")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "summary": f"价值性评估：{'价值较高' if score >= 60 else '价值一般'}"
        }
    
    def _assess_risk(self, content: str) -> Dict[str, Any]:
        """
        评估风险（实事求是原则）
        
        注意：风险评估是独立的，不降低分数，而是指出需要关注的问题
        """
        risks = []
        limitations = []
        assumptions = []
        
        # 识别风险
        risk_keywords = {
            "技术风险": ["不确定", "未知", "探索", "实验"],
            "市场风险": ["竞争", "变化", "波动", "不确定"],
            "资源风险": ["资源有限", "资金不足", "人力不足"],
            "执行风险": ["困难", "复杂", "周期长", "难度大"]
        }
        
        for risk_type, keywords in risk_keywords.items():
            if any(kw in content for kw in keywords):
                risks.append(f"{risk_type}需关注")
        
        # 识别局限
        limitation_words = ["只能", "限于", "局限", "只能做到", "难以"]
        for word in limitation_words:
            if word in content:
                limitations.append(f"存在{word}表述的局限")
        
        # 识别假设
        assumption_words = ["假设", "前提", "如果", "假定"]
        for word in assumption_words:
            if word in content:
                assumptions.append(f"依赖{word}条件")
        
        # 风险评分（低风险=高分）
        score = 100 - len(risks) * 10 - len(limitations) * 5
        
        return {
            "score": min(max(score, 0), 100),
            "risks": risks[:3] if risks else ["暂无明显风险"],
            "limitations": limitations[:2] if limitations else ["暂无明显局限"],
            "assumptions": assumptions[:2] if assumptions else ["暂无明显假设"],
            "summary": "风险评估完成"
        }
    
    def _make_decision(self, overall_score: float, risk_score: float) -> Dict[str, Any]:
        """生成决策建议"""
        if overall_score >= 75 and risk_score >= 60:
            return {
                "level": "🌟 强烈推荐",
                "action": "优先执行",
                "reason": "综合得分高，风险可控"
            }
        elif overall_score >= 60 or risk_score >= 60:
            return {
                "level": "⚠️ 谨慎推荐",
                "action": "可考虑执行，需关注风险",
                "reason": "有一定价值，需评估风险"
            }
        elif overall_score >= 45:
            return {
                "level": "📝 建议观望",
                "action": "持续关注",
                "reason": "暂时搁置，等待时机"
            }
        else:
            return {
                "level": "❌ 暂不推荐",
                "action": "优先止损",
                "reason": "综合得分低或风险过高"
            }


def format_deep_report(assessment: Dict[str, Any], idea_content: str) -> str:
    """格式化深度评估报告"""
    risk = assessment["risk"]
    
    report = f"""📊 深度评估报告

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 综合得分：{assessment['overall_score']}/100
📌 决策建议：{assessment['decision']['level']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌟 前景评估（好的一面）：

• 创新性：{assessment['innovation']['score']}分
  {assessment['innovation'].get('factors', ['无突出因素'])[0] if assessment['innovation'].get('factors') else '无突出因素'}

• 可行性：{assessment['feasibility']['score']}分  
  {assessment['feasibility'].get('factors', ['无突出因素'])[0] if assessment['feasibility'].get('factors') else '无突出因素'}

• 价值性：{assessment['value']['score']}分
  {assessment['value'].get('factors', ['无突出因素'])[0] if assessment['value'].get('factors') else '无突出因素'}

⚠️ 风险评估（问题的一面）：

• 主要风险：{'；'.join(risk['risks'][:2]) if risk['risks'] else '暂无明显风险'}
• 已知局限：{'；'.join(risk['limitations'][:1]) if risk['limitations'] else '暂无明显局限'}
• 假设条件：{'；'.join(risk['assumptions'][:1]) if risk['assumptions'] else '暂无明显假设'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 诚实建议：

{assessment['decision']['action']}：{assessment['decision']['reason']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return report
