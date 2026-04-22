"""复盘服务 - Review Service"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class ReviewRecord:
    """复盘记录"""
    id: str
    idea_id: str
    task_id: Optional[str] = ""
    
    # 复盘时间
    review_date: str = ""
    
    # 执行结果
    result: str = "partial"  # success, partial, failed
    completion_rate: float = 0.0  # 0-100%
    
    # 经验总结
    lessons_learned: List[str] = field(default_factory=list)  # 学到的经验
    mistakes: List[str] = field(default_factory=list)  # 犯的错误
    improvements: List[str] = field(default_factory=list)  # 改进点
    
    # 下一步
    next_actions: List[str] = field(default_factory=list)  # 下一步行动
    related_ideas: List[str] = field(default_factory=list)  # 关联想法
    
    # 评估
    time_accuracy: int = 0  # 时间预估准确性 1-5
    scope_accuracy: int = 0  # 范围预估准确性 1-5
    difficulty_accuracy: int = 0  # 难度预估准确性 1-5
    
    # 元数据
    created_at: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.review_date:
            self.review_date = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def get_result_display(self) -> str:
        """结果展示"""
        result_map = {
            "success": "✅ 成功",
            "partial": "⚠️ 部分完成",
            "failed": "❌ 失败"
        }
        return result_map.get(self.result, self.result)

    def get_accuracy_avg(self) -> float:
        """计算平均准确性"""
        scores = [self.time_accuracy, self.scope_accuracy, self.difficulty_accuracy]
        valid_scores = [s for s in scores if s > 0]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0

    def format_report(self) -> str:
        """格式化复盘报告"""
        lines = [f"## 📋 复盘报告\n"]
        lines.append(f"**复盘日期**: {self.review_date[:10]}\n")
        lines.append(f"**执行结果**: {self.get_result_display()}\n")
        lines.append(f"**完成度**: {self.completion_rate}%\n")
        
        if self.lessons_learned:
            lines.append(f"\n### ✅ 经验总结\n")
            for lesson in self.lessons_learned:
                lines.append(f"- {lesson}\n")
        
        if self.mistakes:
            lines.append(f"\n### ❌ 问题与错误\n")
            for mistake in self.mistakes:
                lines.append(f"- {mistake}\n")
        
        if self.improvements:
            lines.append(f"\n### 🔧 改进措施\n")
            for imp in self.improvements:
                lines.append(f"- {imp}\n")
        
        if self.next_actions:
            lines.append(f"\n### 🎯 下一步行动\n")
            for action in self.next_actions:
                lines.append(f"- {action}\n")
        
        lines.append(f"\n### 📊 预估准确性\n")
        lines.append(f"- 时间预估: {'⭐' * self.time_accuracy}{'☆' * (5 - self.time_accuracy)}\n")
        lines.append(f"- 范围预估: {'⭐' * self.scope_accuracy}{'☆' * (5 - self.scope_accuracy)}\n")
        lines.append(f"- 难度预估: {'⭐' * self.difficulty_accuracy}{'☆' * (5 - self.difficulty_accuracy)}\n")
        
        avg = self.get_accuracy_avg()
        if avg > 0:
            lines.append(f"\n**总体准确性**: {avg:.1f}/5.0\n")
        
        return "".join(lines)


class ReviewService:
    """
    复盘服务
    
    定期对已完成或失败的想法/任务进行复盘
    """
    
    def __init__(self):
        self._reviews: List[ReviewRecord] = []
    
    def create_review(
        self,
        idea_id: str,
        task_id: str = "",
        result: str = "partial",
        completion_rate: float = 0.0,
        lessons: List[str] = None,
        mistakes: List[str] = None,
        improvements: List[str] = None,
        next_actions: List[str] = None,
        time_accuracy: int = 3,
        scope_accuracy: int = 3,
        difficulty_accuracy: int = 3,
        notes: str = ""
    ) -> ReviewRecord:
        """
        创建复盘记录
        
        Args:
            idea_id: 想法 ID
            task_id: 任务 ID（可选）
            result: 执行结果
            completion_rate: 完成度
            lessons: 学到的经验
            mistakes: 犯的错误
            improvements: 改进措施
            next_actions: 下一步行动
            time_accuracy: 时间预估准确性 1-5
            scope_accuracy: 范围预估准确性 1-5
            difficulty_accuracy: 难度预估准确性 1-5
            notes: 备注
        """
        review = ReviewRecord(
            id=f"review_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            idea_id=idea_id,
            task_id=task_id,
            result=result,
            completion_rate=completion_rate,
            lessons_learned=lessons or [],
            mistakes=mistakes or [],
            improvements=improvements or [],
            next_actions=next_actions or [],
            time_accuracy=time_accuracy,
            scope_accuracy=scope_accuracy,
            difficulty_accuracy=difficulty_accuracy,
            notes=notes
        )
        
        self._reviews.append(review)
        return review
    
    def get_idea_reviews(self, idea_id: str) -> List[ReviewRecord]:
        """获取想法的所有复盘"""
        return [r for r in self._reviews if r.idea_id == idea_id]
    
    def get_all_reviews(self, limit: int = 50) -> List[ReviewRecord]:
        """获取所有复盘"""
        sorted_reviews = sorted(self._reviews, key=lambda x: x.review_date, reverse=True)
        return sorted_reviews[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取复盘统计"""
        if not self._reviews:
            return {
                "total": 0,
                "success_rate": 0,
                "avg_completion": 0,
                "avg_accuracy": 0
            }
        
        total = len(self._reviews)
        success_count = sum(1 for r in self._reviews if r.result == "success")
        avg_completion = sum(r.completion_rate for r in self._reviews) / total
        avg_accuracy = sum(r.get_accuracy_avg() for r in self._reviews) / total
        
        return {
            "total": total,
            "success_rate": round(success_count / total * 100, 1),
            "avg_completion": round(avg_completion, 1),
            "avg_accuracy": round(avg_accuracy, 1)
        }
    
    def get_recent_lessons(self, limit: int = 10) -> List[str]:
        """获取最近的经验总结"""
        recent = self.get_all_reviews(limit)
        lessons = []
        for review in recent:
            lessons.extend(review.lessons_learned)
        return lessons[:limit]
    
    def suggest_review_for_idea(
        self,
        idea_content: str,
        tasks_completed: int,
        tasks_total: int,
        actual_hours: float,
        estimated_hours: float
    ) -> Dict[str, Any]:
        """
        建议复盘内容（基于任务执行情况）
        
        Args:
            idea_content: 想法内容
            tasks_completed: 已完成任务数
            tasks_total: 总任务数
            actual_hours: 实际耗时
            estimated_hours: 预估耗时
            
        Returns:
            建议的复盘问题
        """
        completion_rate = tasks_completed / tasks_total * 100 if tasks_total > 0 else 0
        time_ratio = actual_hours / estimated_hours if estimated_hours > 0 else 1
        
        suggestions = {
            "completion_rate": completion_rate,
            "time_ratio": time_ratio,
            "questions": []
        }
        
        # 完成度问题
        if completion_rate < 50:
            suggestions["questions"].append("为什么只完成了这么少？主要遇到了什么障碍？")
        elif completion_rate < 100:
            suggestions["questions"].append("未完成的部分计划如何处理？")
        
        # 时间问题
        if time_ratio > 1.5:
            suggestions["questions"].append("时间超出预估50%以上，哪里预估错了？")
        elif time_ratio < 0.5:
            suggestions["questions"].append("时间比预估少很多，是简化了方案还是其他原因？")
        
        # 通用问题
        suggestions["questions"].extend([
            "这次执行中，你学到的最重要的一件事是什么？",
            "下次类似项目，你会做出什么不同？",
            "这个想法的哪些部分值得继续投入？"
        ])
        
        return suggestions
