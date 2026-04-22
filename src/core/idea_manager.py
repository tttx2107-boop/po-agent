"""想法管理器"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.idea import Idea, QuickAssessment, DeepAssessment
from ..storage.base import BaseStorage
from ..services.quick_assessment import QuickAssessmentService
from ..services.deep_assessment import DeepAssessmentService


class IdeaManager:
    """想法全生命周期管理"""
    
    def __init__(self, storage: BaseStorage):
        self.storage = storage
        self.quick_assessor = QuickAssessmentService()
        self.deep_assessor = DeepAssessmentService()
        self._ideas: List[Idea] = []
        self._load()
    
    def _load(self):
        """加载数据"""
        data = self.storage.load_ideas()
        self._ideas = [Idea.from_dict(d) for d in data]
    
    def _save(self) -> bool:
        """保存数据"""
        data = [idea.to_dict() for idea in self._ideas]
        return self.storage.save_ideas(data)
    
    def create(self, content: str, source: str = "cli") -> Idea:
        """
        创建想法
        
        Args:
            content: 想法内容
            source: 来源 (wechat, cli, schedule)
            
        Returns:
            创建的想法
        """
        # 快速评估
        quick_result = self.quick_assessor.assess(content)
        quick_assessment = QuickAssessment(**quick_result)
        
        # 创建想法
        now = datetime.now().isoformat()
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            content=content,
            created_at=now,
            updated_at=now,
            source=source,
            tags=quick_result.get("domain_tags", []),
            status="NEW",
            quick_assessment=quick_assessment
        )
        
        self._ideas.append(idea)
        self._save()
        
        return idea
    
    def list(self, status: Optional[str] = None, 
             tags: Optional[List[str]] = None,
             limit: int = 50) -> List[Idea]:
        """
        列出想法
        
        Args:
            status: 按状态筛选
            tags: 按标签筛选
            limit: 返回数量限制
            
        Returns:
            想法列表
        """
        results = self._ideas
        
        if status:
            results = [i for i in results if i.status == status]
        
        if tags:
            results = [i for i in results if any(t in i.tags for t in tags)]
        
        # 按创建时间倒序
        results = sorted(results, key=lambda x: x.created_at, reverse=True)
        
        return results[:limit]
    
    def get(self, idea_id: str) -> Optional[Idea]:
        """获取单个想法"""
        for idea in self._ideas:
            if idea.id == idea_id:
                return idea
        return None
    
    def update(self, idea_id: str, updates: Dict[str, Any]) -> Optional[Idea]:
        """更新想法"""
        idea = self.get(idea_id)
        if not idea:
            return None
        
        for key, value in updates.items():
            if hasattr(idea, key):
                setattr(idea, key, value)
        
        idea.updated_at = datetime.now().isoformat()
        self._save()
        return idea
    
    def update_status(self, idea_id: str, status: str) -> Optional[Idea]:
        """更新状态"""
        return self.update(idea_id, {"status": status})
    
    def delete(self, idea_id: str) -> bool:
        """删除想法"""
        for i, idea in enumerate(self._ideas):
            if idea.id == idea_id:
                self._ideas.pop(i)
                self._save()
                return True
        return False
    
    def search(self, query: str) -> List[Idea]:
        """搜索想法"""
        query = query.lower()
        results = []
        for idea in self._ideas:
            if (query in idea.content.lower() or 
                query in " ".join(idea.tags).lower()):
                results.append(idea)
        return results
    
    def get_pending_assessment(self, limit: int = 10) -> List[Idea]:
        """获取待评估想法"""
        pending = [i for i in self._ideas if i.is_pending_assessment()]
        # 按创建时间排序
        pending = sorted(pending, key=lambda x: x.created_at)
        return pending[:limit]
    
    def assess(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """
        深度评估想法
        
        Returns:
            评估结果
        """
        idea = self.get(idea_id)
        if not idea:
            return None
        
        # 执行评估 - DeepAssessmentService 返回扁平结构
        assessment_result = self.deep_assessor.assess(idea.to_dict())
        
        # 构建 DeepAssessment
        deep_assessment = DeepAssessment(
            innovation_score=assessment_result["innovation_score"],
            feasibility_score=assessment_result["feasibility_score"],
            value_score=assessment_result["value_score"],
            risk_score=assessment_result["risk_score"],
            perspective_score=assessment_result["perspective_score"],
            overall_score=assessment_result["overall_score"],
            decision_level=assessment_result.get("decision_level", ""),
            decision_action=assessment_result.get("decision_action", ""),
            decision_reason=assessment_result.get("decision_reason", ""),
            assessment_date=assessment_result["assessment_date"],
            assessor=assessment_result.get("assessor", "ai"),
            notes=""
        )
        
        # 更新想法
        idea.deep_assessment = deep_assessment
        idea.updated_at = datetime.now().isoformat()
        
        # 根据决策更新状态
        action = assessment_result["decision_action"]
        if action == "优先执行":
            idea.status = "CONFIRMED"
        elif action == "建议执行":
            idea.status = "CONFIRMED"
        elif action == "持续关注":
            idea.status = "DEFERRED"
        else:
            idea.status = "REJECTED"
        
        self._save()
        return assessment_result
    
    def assess_pending(self, limit: int = 3) -> List[Dict[str, Any]]:
        """批量评估待评估想法"""
        pending = self.get_pending_assessment(limit)
        results = []
        for idea in pending:
            result = self.assess(idea.id)
            if result:
                results.append(result)
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        total = len(self._ideas)
        by_status = {}
        by_tag = {}
        
        for idea in self._ideas:
            status = idea.status
            by_status[status] = by_status.get(status, 0) + 1
            
            for tag in idea.tags:
                by_tag[tag] = by_tag.get(tag, 0) + 1
        
        return {
            "total": total,
            "by_status": by_status,
            "by_tag": by_tag,
            "pending_assessment": len(self.get_pending_assessment())
        }
    
    def should_trigger_assessment(self, trigger_count: int = 5) -> bool:
        """判断是否应该触发评估"""
        pending = self.get_pending_assessment()
        return len(pending) >= trigger_count
