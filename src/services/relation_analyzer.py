"""想法关联分析服务 - Idea Relation Analyzer"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
import re


@dataclass
class RelationType:
    """关联类型定义"""
    SAME_DOMAIN = "same_domain"      # 同领域
    COMPLEMENTS = "complements"      # 互补
    DEPENDS_ON = "depends_on"        # 依赖
    CONFLICTS = "conflicts"          # 冲突
    EVOLVED_FROM = "evolved_from"    # 演进
    SHARES_RESOURCE = "shares_resource"  # 共享资源


@dataclass
class IdeaRelation:
    """想法关联"""
    idea_a: str
    idea_b: str
    relation_type: str
    confidence: float  # 0-1
    reason: str = ""
    bidirectional: bool = True  # 是否双向关联

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idea_a": self.idea_a,
            "idea_b": self.idea_b,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "bidirectional": self.bidirectional
        }


@dataclass
class RelationReport:
    """关联分析报告"""
    idea_id: str
    idea_content: str
    relations: List[IdeaRelation] = field(default_factory=list)
    clusters: List[List[str]] = field(default_factory=list)  # 想法群
    suggestions: List[str] = field(default_factory=list)  # 建议

    def format_report(self) -> str:
        """格式化报告"""
        lines = [f"## 🔗 想法关联分析\n"]
        lines.append(f"**想法**: {self.idea_content[:50]}...\n")
        
        if not self.relations:
            lines.append("\n暂无发现关联\n")
            return "".join(lines)
        
        # 按类型分组
        by_type = defaultdict(list)
        for rel in self.relations:
            by_type[rel.relation_type].append(rel)
        
        lines.append(f"\n发现 {len(self.relations)} 个关联：\n")
        
        for rel_type, rels in by_type.items():
            emoji = {
                RelationType.SAME_DOMAIN: "🏷️",
                RelationType.COMPLEMENTS: "🔄",
                RelationType.DEPENDS_ON: "⏳",
                RelationType.CONFLICTS: "⚠️",
                RelationType.EVOLVED_FROM: "🔱",
                RelationType.SHARES_RESOURCE: "📦"
            }.get(rel_type, "📌")
            
            lines.append(f"\n{emoji} **{rel_type.replace('_', ' ').title()}** ({len(rels)})\n")
            for rel in rels[:3]:  # 最多显示3个
                lines.append(f"- {rel.idea_b}: {rel.reason}\n")
            if len(rels) > 3:
                lines.append(f"- ... 还有 {len(rels) - 3} 个\n")
        
        if self.suggestions:
            lines.append(f"\n### 💡 建议\n")
            for sug in self.suggestions:
                lines.append(f"- {sug}\n")
        
        return "".join(lines)


class IdeaRelationAnalyzer:
    """
    想法关联分析器
    
    自动发现想法之间的关联关系
    """
    
    # 领域关键词
    DOMAIN_KEYWORDS = {
        "消防": ["消防", "火灾", "灭火", "疏散", "危化品", "安全"],
        "AI": ["AI", "人工智能", "机器学习", "深度学习", "大模型", "LLM"],
        "知识管理": ["知识图谱", "知识库", "笔记", "知识管理", "本体"],
        "副业": ["副业", "创业", "变现", "收入", "商业模式"],
        "教育": ["教学", "课程", "培训", "学习", "教育"],
        "效率": ["自动化", "效率", "工具", "提效", "流程"],
        "物联网": ["物联网", "IoT", "传感器", "设备", "监控"],
    }
    
    # 互补关键词
    COMPLEMENT_KEYWORDS = [
        ("前端", "后端"), ("iOS", "Android"), ("Web", "APP"),
        ("移动端", "PC端"), ("数据", "展示"), ("采集", "分析")
    ]
    
    # 冲突关键词
    CONFLICT_PAIRS = [
        (["自研", "外包"], ["自研", "外包"]),
        (["免费", "付费"], ["免费", "付费"]),
        (["本地", "云端"], ["本地", "云端"]),
    ]
    
    # 演进关键词
    EVOLUTION_KEYWORDS = ["升级", "改进", "优化", "演进", "v2", "下一代"]
    
    def __init__(self):
        self._relations: List[IdeaRelation] = []
        self._idea_contents: Dict[str, str] = {}  # idea_id -> content
        self._domain_cache: Dict[str, str] = {}  # idea_id -> domain
    
    def register_idea(self, idea_id: str, content: str):
        """注册想法"""
        self._idea_contents[idea_id] = content
        self._domain_cache[idea_id] = self._detect_domain(content)
    
    def analyze_all(self) -> List[IdeaRelation]:
        """分析所有想法的关联"""
        self._relations = []
        idea_ids = list(self._idea_contents.keys())
        
        # 两两比较
        for i, ida in enumerate(idea_ids):
            for idb in idea_ids[i+1:]:
                relations = self._find_relations(ida, idb)
                self._relations.extend(relations)
        
        return self._relations
    
    def analyze_idea(self, idea_id: str) -> RelationReport:
        """分析单个想法的关联"""
        if idea_id not in self._idea_contents:
            return RelationReport(idea_id=idea_id, idea_content="")
        
        content = self._idea_contents[idea_id]
        
        # 找出所有关联
        relations = [
            rel for rel in self._relations
            if rel.idea_a == idea_id or rel.idea_b == idea_id
        ]
        
        # 找出想法群
        clusters = self._find_clusters()
        
        # 生成建议
        suggestions = self._generate_suggestions(idea_id, relations)
        
        return RelationReport(
            idea_id=idea_id,
            idea_content=content,
            relations=relations,
            clusters=clusters,
            suggestions=suggestions
        )
    
    def get_related_ideas(self, idea_id: str, relation_type: Optional[str] = None) -> List[Tuple[str, IdeaRelation]]:
        """获取关联想法"""
        related = []
        for rel in self._relations:
            if rel.idea_a == idea_id:
                related.append((rel.idea_b, rel))
            elif rel.idea_b == idea_id and rel.bidirectional:
                related.append((rel.idea_a, rel))
        
        if relation_type:
            related = [(id, rel) for id, rel in related if rel.relation_type == relation_type]
        
        # 按置信度排序
        return sorted(related, key=lambda x: x[1].confidence, reverse=True)
    
    def _find_relations(self, idea_a: str, idea_b: str) -> List[IdeaRelation]:
        """找两个想法之间的关联"""
        content_a = self._idea_contents[idea_a]
        content_b = self._idea_contents[idea_b]
        relations = []
        
        # 1. 同领域检测
        domain_a = self._domain_cache[idea_a]
        domain_b = self._domain_cache[idea_b]
        if domain_a and domain_a == domain_b and idea_a != idea_b:
            relations.append(IdeaRelation(
                idea_a=idea_a,
                idea_b=idea_b,
                relation_type=RelationType.SAME_DOMAIN,
                confidence=0.8,
                reason=f"同属「{domain_a}」领域"
            ))
        
        # 2. 互补检测
        for kw_a, kw_b in self.COMPLEMENT_KEYWORDS:
            if kw_a in content_a and kw_b in content_b:
                relations.append(IdeaRelation(
                    idea_a=idea_a,
                    idea_b=idea_b,
                    relation_type=RelationType.COMPLEMENTS,
                    confidence=0.7,
                    reason=f"「{kw_a}」与「{kw_b}」可互补"
                ))
                break
        
        # 3. 冲突检测
        for kws1, kws2 in self.CONFLICT_PAIRS:
            has_kw1_a = any(k in content_a for k in kws1)
            has_kw2_a = any(k in content_a for k in kws2)
            has_kw1_b = any(k in content_b for k in kws1)
            has_kw2_b = any(k in content_b for k in kws2)
            if (has_kw1_a and has_kw2_b) or (has_kw2_a and has_kw1_b):
                relations.append(IdeaRelation(
                    idea_a=idea_a,
                    idea_b=idea_b,
                    relation_type=RelationType.CONFLICTS,
                    confidence=0.9,
                    reason="存在潜在冲突，需谨慎组合",
                    bidirectional=True
                ))
        
        # 4. 演进检测
        for kw in self.EVOLUTION_KEYWORDS:
            if kw in content_a and content_b[:50] in content_a:
                relations.append(IdeaRelation(
                    idea_a=idea_a,
                    idea_b=idea_b,
                    relation_type=RelationType.EVOLVED_FROM,
                    confidence=0.6,
                    reason="可能是前者的演进版本"
                ))
                break
        
        # 5. 共享资源检测
        resource_keywords = ["Python", "React", "微信", "GitHub", "API", "数据库"]
        resources_a = set(k for k in resource_keywords if k in content_a)
        resources_b = set(k for k in resource_keywords if k in content_b)
        shared = resources_a & resources_b
        if shared and len(shared) >= 1:
            relations.append(IdeaRelation(
                idea_a=idea_a,
                idea_b=idea_b,
                relation_type=RelationType.SHARES_RESOURCE,
                confidence=0.5,
                reason=f"可共享资源: {', '.join(shared)}"
            ))
        
        return relations
    
    def _detect_domain(self, content: str) -> Optional[str]:
        """检测领域"""
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return domain
        return None
    
    def _find_clusters(self) -> List[List[str]]:
        """找出想法群（高度相关的想法组）"""
        # 构建邻接图
        graph: Dict[str, Set[str]] = defaultdict(set)
        for rel in self._relations:
            if rel.confidence > 0.6:
                graph[rel.idea_a].add(rel.idea_b)
                graph[rel.idea_b].add(rel.idea_a)
        
        # 找连通分量
        visited: Set[str] = set()
        clusters = []
        
        def dfs(node: str, cluster: List[str]):
            visited.add(node)
            cluster.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, cluster)
        
        for idea_id in graph:
            if idea_id not in visited:
                cluster = []
                dfs(idea_id, cluster)
                if len(cluster) > 1:
                    clusters.append(cluster)
        
        return clusters
    
    def _generate_suggestions(self, idea_id: str, relations: List[IdeaRelation]) -> List[str]:
        """生成建议"""
        suggestions = []
        
        # 同领域建议
        same_domain = [r for r in relations if r.relation_type == RelationType.SAME_DOMAIN]
        if len(same_domain) >= 3:
            suggestions.append(f"你有 {len(same_domain)} 个同领域想法，考虑合并或确定优先级")
        
        # 冲突建议
        conflicts = [r for r in relations if r.relation_type == RelationType.CONFLICTS]
        if conflicts:
            suggestions.append("⚠️ 检测到冲突想法，建议明确取舍")
        
        # 互补建议
        complements = [r for r in relations if r.relation_type == RelationType.COMPLEMENTS]
        if complements:
            suggestions.append("发现互补想法，可以考虑组合实现")
        
        return suggestions
