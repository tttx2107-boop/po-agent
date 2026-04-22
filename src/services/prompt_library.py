"""Prompt 模板库 - 根据想法类型自动选择最优 Prompt"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum


class PromptDomain(Enum):
    """Prompt 领域"""
    DEFAULT = "default"
    FIREFIGHTING = "firefighting"      # 消防行业
    BUSINESS = "business"              # 副业/创业
    TECH_RESEARCH = "tech_research"   # 技术调研
    LEARNING = "learning"             # 学习成长
    PERSONAL = "personal"              # 个人事务


class PromptType(Enum):
    """Prompt 类型"""
    QUICK_ASSESSMENT = "quick_assessment"
    DEEP_ASSESSMENT = "deep_assessment"
    TASK_BREAKDOWN = "task_breakdown"
    RISK_ANALYSIS = "risk_analysis"
    REPORT_GENERATION = "report_generation"
    REVIEW_GENERATION = "review_generation"


@dataclass
class PromptTemplate:
    """Prompt 模板"""
    domain: str
    prompt_type: str
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)
    
    def fill(self, **kwargs) -> str:
        """填充模板变量"""
        return self.template.format(**kwargs)


class PromptTemplateLibrary:
    """
    Prompt 模板库
    
    管理所有领域和类型的 Prompt 模板
    """
    
    def __init__(self):
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}
        self._domain_detectors: Dict[str, Callable[[str], float]] = {}
        self._init_templates()
        self._init_domain_detectors()
    
    def _init_templates(self):
        """初始化所有模板"""
        self._templates = {
            PromptDomain.DEFAULT.value: {
                PromptType.QUICK_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.DEFAULT.value,
                    prompt_type=PromptType.QUICK_ASSESSMENT.value,
                    description="通用快速评估",
                    variables=["idea_content"],
                    template="""你是想法快速评估专家。请对以下想法进行快速评估：

想法：{idea_content}

请输出（JSON格式）：
{{
    "intent_type": "create|query|command",
    "keywords": ["关键词1", "关键词2"],
    "completeness": 0.0-1.0,
    "completeness_reason": "原因说明",
    "suggestions": "补充建议（如有）"
}}"""
                ),
                
                PromptType.DEEP_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.DEFAULT.value,
                    prompt_type=PromptType.DEEP_ASSESSMENT.value,
                    description="通用深度评估",
                    variables=["idea_content", "background"],
                    template="""你是想法深度评估专家。请从以下维度评估想法：

想法：{idea_content}

背景信息：{background}

请从以下维度评分（0-100分）：
1. **创新性**：这个想法有多新颖？
2. **可行性**：在现有条件下能实现吗？
3. **价值性**：能带来什么价值？

请输出（JSON格式）：
{{
    "innovation_score": 0-100,
    "innovation_reason": "评分理由",
    "feasibility_score": 0-100,
    "feasibility_reason": "评分理由，重点说明约束和风险",
    "value_score": 0-100,
    "value_reason": "评分理由",
    "overall_score": 0-100,
    "decision": "proceed|defer|reject",
    "decision_reason": "决策理由",
    "priority": "high|medium|low",
    "key_risks": ["风险1", "风险2"],
    "next_steps": ["步骤1", "步骤2"]
}}

**原则**：实事求是，说可行性也说局限性，说优势也说风险。"""
                ),
                
                PromptType.TASK_BREAKDOWN.value: PromptTemplate(
                    domain=PromptDomain.DEFAULT.value,
                    prompt_type=PromptType.TASK_BREAKDOWN.value,
                    description="通用任务拆分",
                    variables=["idea_content", "constraints"],
                    template="""你是任务拆解专家。请将以下想法拆解为可执行的任务：

想法：{idea_content}

约束条件：{constraints}

请拆解为具体任务，要求：
1. 每个任务可在一周内完成
2. 明确任务间的依赖关系
3. 给出预估时间
4. 标注任务类型（research/document/mvp/deploy/test/review）

请输出（JSON格式）：
{{
    "tasks": [
        {{
            "id": 1,
            "title": "任务标题",
            "description": "任务描述",
            "type": "research|document|mvp|deploy|test|review",
            "estimated_hours": 8,
            "depends_on": [],
            "deliverable": "产出物"
        }}
    ],
    "total_estimated_days": 总天数,
    "critical_path": ["任务ID列表"],
    "milestones": ["里程碑1", "里程碑2"]
}}"""
                ),
            },
            
            PromptDomain.FIREFIGHTING.value: {
                PromptType.QUICK_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.FIREFIGHTING.value,
                    prompt_type=PromptType.QUICK_ASSESSMENT.value,
                    description="消防行业快速评估",
                    variables=["idea_content"],
                    template="""你是消防行业专家。请对以下消防相关想法进行快速评估：

想法：{idea_content}

请输出（JSON格式）：
{{
    "intent_type": "create|query|command",
    "keywords": ["消防", "法规", "安全", "..."],
    "industry_relevance": "high|medium|low",
    "compliance_notes": "合规注意点（如有）",
    "completeness": 0.0-1.0,
    "suggestions": "补充建议"
}}"""
                ),
                
                PromptType.DEEP_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.FIREFIGHTING.value,
                    prompt_type=PromptType.DEEP_ASSESSMENT.value,
                    description="消防行业深度评估",
                    variables=["idea_content", "background"],
                    template="""你是消防行业资深专家。请评估以下消防相关想法：

想法：{idea_content}

背景信息：{background}

请从以下维度评分（0-100分）：
1. **创新性**：技术创新或模式创新程度
2. **可行性**：技术实现+政策合规可行性
3. **价值性**：安全效益+经济价值

**消防行业特别注意**：
- 法规合规性（GB标准、NFPA规范等）
- 实际安全效益
- 技术成熟度
- 实施成本与周期

请输出（JSON格式）：
{{
    "innovation_score": 0-100,
    "innovation_reason": "评分理由",
    "feasibility_score": 0-100,
    "feasibility_reason": "技术+合规可行性分析",
    "compliance_checklist": ["合规项1", "合规项2"],
    "value_score": 0-100,
    "value_reason": "安全+经济效益分析",
    "overall_score": 0-100,
    "decision": "proceed|defer|reject",
    "decision_reason": "决策理由",
    "priority": "high|medium|low",
    "key_risks": ["风险1", "风险2"],
    "regulatory_notes": "法规相关备注"
}}

**原则**：实事求是，不仅评估可行性，也明确指出合规风险。"""
                ),
            },
            
            PromptDomain.BUSINESS.value: {
                PromptType.DEEP_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.BUSINESS.value,
                    prompt_type=PromptType.DEEP_ASSESSMENT.value,
                    description="商业模式评估",
                    variables=["idea_content", "background"],
                    template="""你是商业模式评估专家。请评估以下副业/创业想法：

想法：{idea_content}

背景信息：{background}

请从以下维度评估：
1. **商业模式清晰度**：盈利模式是否清晰？
2. **市场规模估算**：目标市场有多大？
3. **盈利路径**：如何赚钱？
4. **启动成本**：需要投入多少？
5. **竞争壁垒**：护城河是什么？
6. **团队要求**：需要什么能力？

请输出（JSON格式）：
{{
    "business_model_score": 0-100,
    "business_model_analysis": "商业模式分析",
    "market_size": "市场规模估算",
    "revenue_path": "盈利路径说明",
    "startup_cost": "启动成本估算",
    "startup_cost_level": "low|medium|high",
    "competition_barrier": "竞争壁垒分析",
    "team_requirements": ["能力1", "能力2"],
    "feasibility_score": 0-100,
    "value_score": 0-100,
    "overall_score": 0-100,
    "decision": "proceed|defer|reject",
    "decision_reason": "决策理由",
    "key_risks": ["风险1", "风险2"],
    "swot": {{
        "strengths": ["优势1", "优势2"],
        "weaknesses": ["劣势1", "劣势2"],
        "opportunities": ["机会1", "机会2"],
        "threats": ["威胁1", "威胁2"]
    }}
}}

**原则**：客观评估，不画大饼，诚实说明风险和挑战。"""
                ),
            },
            
            PromptDomain.TECH_RESEARCH.value: {
                PromptType.DEEP_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.TECH_RESEARCH.value,
                    prompt_type=PromptType.DEEP_ASSESSMENT.value,
                    description="技术调研评估",
                    variables=["idea_content", "background"],
                    template="""你是技术调研专家。请评估以下技术研究方向：

想法：{idea_content}

背景信息：{background}

请从以下维度评估：
1. **技术可行性**：当前技术能否支撑？
2. **技术成熟度**：是否成熟技术？研究可行性如何？
3. **资源需求**：需要什么技术栈和资源？
4. **创新性**：理论创新还是应用创新？
5. **可落地性**：多久能出成果？

请输出（JSON格式）：
{{
    "tech_feasibility_score": 0-100,
    "tech_feasibility_analysis": "技术可行性分析",
    "maturity_level": "emerging|developing|mature",
    "resource_requirements": ["资源1", "资源2"],
    "skill_gaps": ["技能缺口1", "技能缺口2"],
    "innovation_score": 0-100,
    "innovation_type": "theoretical|practical|both",
    "time_to_result": "预估时间",
    "overall_score": 0-100,
    "decision": "proceed|defer|reject",
    "decision_reason": "决策理由",
    "key_risks": ["技术风险1", "技术风险2"],
    "research_suggestions": ["建议1", "建议2"]
}}

**原则**：从第一性原理分析技术可行性，不夸大不缩小。"""
                ),
            },
            
            PromptDomain.LEARNING.value: {
                PromptType.DEEP_ASSESSMENT.value: PromptTemplate(
                    domain=PromptDomain.LEARNING.value,
                    prompt_type=PromptType.DEEP_ASSESSMENT.value,
                    description="学习成长评估",
                    variables=["idea_content", "background"],
                    template="""你是学习规划专家。请评估以下学习计划：

想法：{idea_content}

背景信息：{background}

请从以下维度评估：
1. **学习价值**：能提升什么能力？
2. **ROI（投入产出比）**：时间精力投入是否值得？
3. **可执行性**：能否坚持下来？
4. **优先级**：与其他学习计划相比如何？
5. **实用性**：学完能用在什么地方？

请输出（JSON格式）：
{{
    "learning_value_score": 0-100,
    "skill_improvements": ["能力提升1", "能力提升2"],
    "roi_score": 0-100,
    "time_investment": "预估时间投入",
    "roi_analysis": "投入产出比分析",
    "feasibility_score": 0-100,
    "difficulty_level": "beginner|intermediate|advanced",
    "motivation_sustainability": "能否坚持分析",
    "practical_applicability": "实用性分析",
    "priority": "high|medium|low",
    "learning_path": ["步骤1", "步骤2"],
    "resource_recommendations": ["资源1", "资源2"],
    "overall_score": 0-100,
    "decision": "proceed|defer|reject",
    "decision_reason": "决策理由"
}}

**原则**：实事求是，评估真实的学习效果和投入成本。"""
                ),
            },
        }
    
    def _init_domain_detectors(self):
        """初始化领域检测器"""
        self._domain_detectors = {
            PromptDomain.FIREFIGHTING.value: self._detect_firefighting,
            PromptDomain.BUSINESS.value: self._detect_business,
            PromptDomain.TECH_RESEARCH.value: self._detect_tech_research,
            PromptDomain.LEARNING.value: self._detect_learning,
        }
    
    def _detect_firefighting(self, content: str) -> float:
        """检测消防行业相关性"""
        keywords = [
            "消防", "火灾", "灭火", "防火", "危化品", "危化", "安全生产",
            "应急预案", "消防法", "GB", "NFPA", "烟感", "温感", "喷淋",
            "防火门", "疏散", "灭火器", "消火栓", "自动灭火", "气体灭火",
            "阻燃", "耐火", "阻火", "防爆", "静电", "接地", "防雷"
        ]
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return min(matches / 3, 1.0)  # 最多100%
    
    def _detect_business(self, content: str) -> float:
        """检测商业/副业相关性"""
        keywords = [
            "副业", "创业", "赚钱", "盈利", "商业", "收入", "客户",
            "市场", "产品", "运营", "推广", "营销", "销售", "投资",
            "融资", "股权", "分红", "被动收入", "自由职业", "接单",
            "开店", "电商", "直播", "短视频", "自媒体", "知识付费"
        ]
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return min(matches / 3, 1.0)
    
    def _detect_tech_research(self, content: str) -> float:
        """检测技术调研相关性"""
        keywords = [
            "研究", "调研", "算法", "框架", "架构", "技术", "编程",
            "开发", "代码", "API", "数据库", "机器学习", "深度学习",
            "AI", "NLP", "CV", "区块链", "云计算", "大数据", "物联网",
            "实验", "论文", "专利", "学术"
        ]
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return min(matches / 3, 1.0)
    
    def _detect_learning(self, content: str) -> float:
        """检测学习成长相关性"""
        keywords = [
            "学习", "学", "课程", "培训", "读书", "看书", "掌握",
            "技能", "证书", "考证", "认证", "入门", "精通", "提升",
            "成长", "复盘", "总结", "PPT", "演讲", "写作"
        ]
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return min(matches / 3, 1.0)
    
    def detect_domain(self, idea_content: str) -> PromptDomain:
        """
        检测想法所属领域
        
        Args:
            idea_content: 想法内容
            
        Returns:
            最匹配的领域
        """
        scores = {}
        for domain, detector in self._domain_detectors.items():
            scores[domain] = detector(idea_content)
        
        # 返回得分最高的领域
        best_domain = max(scores.items(), key=lambda x: x[1])
        if best_domain[1] > 0.3:
            return PromptDomain(best_domain[0])
        return PromptDomain.DEFAULT
    
    def get_template(self, domain: PromptDomain, prompt_type: PromptType) -> PromptTemplate:
        """获取指定领域和类型的模板"""
        domain_templates = self._templates.get(domain.value, {})
        template = domain_templates.get(prompt_type.value)
        
        if not template:
            # 回退到默认模板
            domain_templates = self._templates.get(PromptDomain.DEFAULT.value, {})
            template = domain_templates.get(prompt_type.value)
        
        return template
    
    def get_all_domains(self) -> List[str]:
        """获取所有可用领域"""
        return list(self._templates.keys())
    
    def get_prompt_types(self, domain: PromptDomain) -> List[str]:
        """获取指定领域的所有 Prompt 类型"""
        templates = self._templates.get(domain.value, {})
        return list(templates.keys())


# 全局模板库实例
_prompt_library = None


def get_prompt_library() -> PromptTemplateLibrary:
    """获取 Prompt 模板库实例"""
    global _prompt_library
    if _prompt_library is None:
        _prompt_library = PromptTemplateLibrary()
    return _prompt_library
