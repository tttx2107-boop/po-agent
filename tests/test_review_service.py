"""复盘服务测试"""
import pytest
from src.services.review_service import ReviewService, ReviewRecord


class TestReviewRecord:
    """复盘记录测试"""
    
    def test_create_review_record(self):
        """测试创建复盘记录"""
        record = ReviewRecord(
            id="test-001",
            idea_id="idea-001",
            result="success",
            completion_rate=80.0
        )
        
        assert record.id == "test-001"
        assert record.result == "success"
        assert record.completion_rate == 80.0
    
    def test_result_display(self):
        """测试结果展示"""
        record = ReviewRecord(id="t1", idea_id="i1", result="success")
        assert "成功" in record.get_result_display()
        
        record.result = "partial"
        assert "部分" in record.get_result_display()
        
        record.result = "failed"
        assert "失败" in record.get_result_display()
    
    def test_accuracy_avg(self):
        """测试准确性计算"""
        record = ReviewRecord(
            id="t1", 
            idea_id="i1",
            time_accuracy=4,
            scope_accuracy=3,
            difficulty_accuracy=5
        )
        
        assert record.get_accuracy_avg() == 4.0
    
    def test_format_report(self):
        """测试报告格式化"""
        record = ReviewRecord(
            id="t1",
            idea_id="i1",
            result="success",
            completion_rate=100.0,
            lessons_learned=["学到了一件事"],
            mistakes=["犯了一个错误"],
            improvements=["改进了流程"],
            next_actions=["下一步行动"],
            time_accuracy=4,
            scope_accuracy=5,
            difficulty_accuracy=3
        )
        
        report = record.format_report()
        
        assert "复盘报告" in report
        assert "成功" in report
        assert "100" in report
        assert "学到了一件事" in report
        assert "犯了一个错误" in report


class TestReviewService:
    """复盘服务测试"""
    
    def test_create_review(self):
        """测试创建复盘"""
        service = ReviewService()
        
        review = service.create_review(
            idea_id="idea-001",
            result="partial",
            completion_rate=60.0,
            lessons=["经验1", "经验2"]
        )
        
        assert review.idea_id == "idea-001"
        assert review.result == "partial"
        assert len(review.lessons_learned) == 2
    
    def test_get_idea_reviews(self):
        """测试获取想法的复盘"""
        service = ReviewService()
        
        service.create_review(idea_id="idea-001")
        service.create_review(idea_id="idea-002")
        service.create_review(idea_id="idea-001")
        
        reviews = service.get_idea_reviews("idea-001")
        assert len(reviews) == 2
    
    def test_get_stats(self):
        """测试统计"""
        service = ReviewService()
        
        service.create_review(idea_id="i1", result="success")
        service.create_review(idea_id="i2", result="success")
        service.create_review(idea_id="i3", result="failed")
        
        stats = service.get_stats()
        
        assert stats["total"] == 3
        assert stats["success_rate"] == pytest.approx(66.7, rel=0.1)
    
    def test_get_recent_lessons(self):
        """测试获取最近经验"""
        service = ReviewService()
        
        service.create_review(idea_id="i1", lessons=["经验A", "经验B"])
        service.create_review(idea_id="i2", lessons=["经验C"])
        
        lessons = service.get_recent_lessons()
        assert len(lessons) >= 3
    
    def test_suggest_review(self):
        """测试复盘建议"""
        service = ReviewService()
        
        suggestion = service.suggest_review_for_idea(
            idea_content="开发一个 APP",
            tasks_completed=2,
            tasks_total=5,
            actual_hours=20,
            estimated_hours=10
        )
        
        assert suggestion["completion_rate"] == 40.0
        assert suggestion["time_ratio"] == 2.0
        assert len(suggestion["questions"]) > 0
    
    def test_suggest_review_low_completion(self):
        """测试低完成度建议"""
        service = ReviewService()
        
        suggestion = service.suggest_review_for_idea(
            idea_content="复杂项目",
            tasks_completed=1,
            tasks_total=10,
            actual_hours=5,
            estimated_hours=100
        )
        
        assert suggestion["completion_rate"] == 10.0
        assert any("少" in q for q in suggestion["questions"])
