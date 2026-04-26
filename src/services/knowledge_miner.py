"""
知识挖掘器
从想法复盘、GitHub项目等来源自动提取知识并沉淀
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from src.models.knowledge import (
    KnowledgeEntry, KnowledgeType, KnowledgeSource,
    INDUSTRY_DOMAINS
)
from src.models.idea import Idea, Review
from src.services.knowledge_service import KnowledgeService, get_knowledge_service


class KnowledgeMiner:
    """知识挖掘器 - 自动化知识沉淀"""
    
    def __init__(self, knowledge_service: Optional[KnowledgeService] = None):
        self.knowledge = knowledge_service or get_knowledge_service()
        
        # 回调函数
        self._on_extract: Optional[Callable] = None
        self._on_save: Optional[Callable] = None
    
    def set_callbacks(self, on_extract: Optional[Callable] = None, on_save: Optional[Callable] = None):
        """设置回调函数"""
        self._on_extract = on_extract
        self._on_save = on_save
    
    def mine_from_idea(self, idea: Idea) -> List[KnowledgeEntry]:
        """从想法挖掘知识"""
        extracted = []
        
        # 1. 从深度评估提取
        if idea.deep_assessment:
            assessment_entry = self._extract_from_assessment(idea)
            if assessment_entry:
                extracted.append(assessment_entry)
        
        # 2. 从复盘提取
        if idea.reviews:
            for review in idea.reviews:
                review_entries = self.knowledge.extract_from_review(idea, review)
                extracted.extend(review_entries)
        
        # 3. 从标签提取领域知识
        domain_entries = self._extract_domain_knowledge(idea)
        extracted.extend(domain_entries)
        
        # 保存
        if self._on_extract:
            for entry in extracted:
                self._on_extract(entry)
        
        # 去重并保存
        added = []
        existing_contents = {e.content[:50] for e in self.knowledge.collection.entries}
        for entry in extracted:
            if entry.content[:50] not in existing_contents:
                self.knowledge.add(entry)
                added.append(entry)
                if self._on_save:
                    self._on_save(entry)
        
        return added
    
    def mine_from_review(self, idea: Idea, review: Review) -> List[KnowledgeEntry]:
        """从复盘记录挖掘"""
        extracted = self.knowledge.extract_from_review(idea, review)
        
        # 保存
        added = []
        existing_contents = {e.content[:50] for e in self.knowledge.collection.entries}
        for entry in extracted:
            if entry.content[:50] not in existing_contents:
                self.knowledge.add(entry)
                added.append(entry)
        
        return added
    
    def _extract_from_assessment(self, idea: Idea) -> Optional[KnowledgeEntry]:
        """从评估提取知识"""
        if not idea.deep_assessment:
            return None
        
        assessment = idea.deep_assessment
        
        # 只有高分想法才沉淀
        if hasattr(assessment, 'overall_score') and assessment.overall_score < 6.0:
            return None
        
        entry = KnowledgeEntry(
            id="",
            content=f"高分想法: {idea.content[:150]}...",
            title=f"评估分 {assessment.overall_score}: {idea.content[:40]}...",
            type=KnowledgeType.CONCEPT.value,
            category="general",
            source_type=KnowledgeSource.IDEA_REVIEW.value,
            source_id=idea.id,
            source_content=f"创新性:{assessment.innovation_score} 可行性:{assessment.feasibility_score} 价值:{assessment.value_score}",
            tags=idea.tags.copy(),
            extraction_confidence=0.8
        )
        
        return entry
    
    def _extract_domain_knowledge(self, idea: Idea) -> List[KnowledgeEntry]:
        """从领域标签提取知识"""
        entries = []
        
        for tag in idea.tags:
            tag_lower = tag.lower()
            
            # 检查是否匹配已知领域
            for domain_id, domain in INDUSTRY_DOMAINS.items():
                if any(tag_kw in tag_lower for tag_kw in domain["tags"]):
                    # 检查是否已存在该领域的通用知识
                    existing = [
                        e for e in self.knowledge.collection.entries
                        if e.industry == domain_id and e.type == KnowledgeType.CONCEPT.value
                    ]
                    
                    if not existing:
                        entry = KnowledgeEntry(
                            id="",
                            content=f"{domain['name']}领域知识积累",
                            title=f"📚 {domain['name']}知识库",
                            type=KnowledgeType.CONCEPT.value,
                            category="industry",
                            industry=domain_id,
                            source_type=KnowledgeSource.MANUAL.value,
                            tags=[tag, domain["name"]],
                            domain_tags=[domain["name"]],
                            extraction_confidence=0.9
                        )
                        entries.append(entry)
                    break
        
        return entries
    
    def mine_from_github_reports(self, report_path: str = "data/github_reports/latest.json") -> List[KnowledgeEntry]:
        """从GitHub报告挖掘灵感"""
        report_file = Path(report_path)
        if not report_file.exists():
            return []
        
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                report = json.load(f)
        except:
            return []
        
        added = []
        for project in report.get("high_score_projects", []):
            repo_data = {
                "full_name": project["full_name"],
                "description": project.get("suggestion", ""),
                "stars": project.get("stars", 0),
                "forks": 0,
                "topics": [project["full_name"].split("/")[-1]]
            }
            
            extracted = self.knowledge.extract_from_github(repo_data)
            for entry in extracted:
                # 检查是否已存在
                existing = [e for e in self.knowledge.collection.entries 
                           if e.source_id == entry.source_id]
                if not existing:
                    self.knowledge.add(entry)
                    added.append(entry)
        
        return added
    
    def mine_batch(self, ideas: List[Idea]) -> Dict[str, Any]:
        """批量挖掘"""
        results = {
            "total_ideas": len(ideas),
            "ideas_with_knowledge": 0,
            "total_extracted": 0,
            "by_type": {},
            "entries": []
        }
        
        for idea in ideas:
            extracted = self.mine_from_idea(idea)
            if extracted:
                results["ideas_with_knowledge"] += 1
                results["total_extracted"] += len(extracted)
                results["entries"].extend(extracted)
                
                for entry in extracted:
                    results["by_type"][entry.type] = results["by_type"].get(entry.type, 0) + 1
        
        return results
    
    def get_recommendations(self, current_idea: Optional[Idea] = None, limit: int = 5) -> List[KnowledgeEntry]:
        """获取知识推荐"""
        recommendations = []
        
        # 1. 如果有当前想法，基于其标签推荐
        if current_idea:
            for tag in current_idea.tags:
                related = self.knowledge.search(tag, limit=3)
                recommendations.extend(related)
        
        # 2. 添加热门知识
        popular = self.knowledge.get_popular(limit=5)
        recommendations.extend(popular)
        
        # 3. 添加灵感
        inspirations = self.knowledge.get_inspirations(
            industry=current_idea.tags[0] if current_idea and current_idea.tags else None,
            limit=3
        )
        recommendations.extend(inspirations)
        
        # 去重并返回
        seen_ids = set()
        unique = []
        for entry in recommendations:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                unique.append(entry)
        
        return unique[:limit]


def create_miner() -> KnowledgeMiner:
    """创建挖掘器"""
    return KnowledgeMiner()
