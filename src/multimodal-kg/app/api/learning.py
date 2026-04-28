# SPDX-License-Identifier: MIT
"""
Self-Learning API Routes for Multimodal Knowledge Graph System
Handles feedback collection, model updates, and quality reporting
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from app.schemas.models import (
    FeedbackCreate,
    FeedbackResponse,
    QualityReport,
    LearningStats,
    PendingReviewQueue
)
from app.services.self_learning import (
    FeedbackCollector,
    IncrementalLearner,
    QualityReport as SelfLearningQualityReport,
    PendingReviewQueue as SelfLearningPendingQueue
)

logger.add(lambda msg: print(msg))

router = APIRouter(prefix="", tags=["learning"])

# In-memory storage (replace with database)
_feedback_store: dict = {}


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackCreate):
    """
    Submit feedback for an annotation
    
    - **annotation_id**: Annotation being reviewed
    - **feedback_type**: Type of feedback (correct, incorrect, partial)
    - **correction_data**: Optional correction data
    - **notes**: Optional notes
    - **user_id**: Optional user identifier
    """
    try:
        import uuid
        
        feedback_id = f"FB_{uuid.uuid4().hex[:8].upper()}"
        
        # Use FeedbackCollector
        collector = FeedbackCollector()
        
        try:
            collector.collect_correction(
                annotation_id=feedback.annotation_id,
                corrections={
                    "feedback_type": feedback.feedback_type.value,
                    "corrected_data": feedback.correction_data,
                    "notes": feedback.notes
                },
                user_id=feedback.user_id
            )
        finally:
            collector.close()
        
        response = FeedbackResponse(
            id=feedback_id,
            annotation_id=feedback.annotation_id,
            feedback_type=feedback.feedback_type,
            correction_data=feedback.correction_data,
            notes=feedback.notes,
            user_id=feedback.user_id,
            user_role="annotator",
            created_at=datetime.utcnow()
        )
        
        _feedback_store[feedback_id] = response
        
        logger.info(f"Submitted feedback: {feedback_id} for annotation {feedback.annotation_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-update", response_model=dict)
async def trigger_model_update(
    force: bool = Query(False, description="Force update even if criteria not met"),
    background_tasks: BackgroundTasks = None
):
    """
    Trigger incremental model update
    
    - **force**: Force update regardless of criteria
    """
    try:
        learner = IncrementalLearner()
        
        try:
            # Check if update should happen
            if not force and not learner.should_update_model():
                return {
                    "success": False,
                    "message": "Model update criteria not met",
                    "details": {
                        "feedback_ratio_required": "Check config",
                        "minimum_corrections_required": "Check config"
                    }
                }
            
            # Prepare training data
            training_data = learner.prepare_training_data()
            
            if training_data.total_count == 0:
                return {
                    "success": False,
                    "message": "No training data available"
                }
            
            # Update model
            new_version = learner.update_annotator_model(training_data)
            
            logger.info(f"Model updated to version: {new_version.version if new_version else 'unknown'}")
            
            return {
                "success": True,
                "message": "Model updated successfully",
                "model_version": new_version.version if new_version else None,
                "samples_trained": training_data.total_count
            }
            
        finally:
            learner.close()
        
    except Exception as e:
        logger.error(f"Error triggering model update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality", response_model=QualityReport)
async def get_quality_report(
    include_trends: bool = Query(False, description="Include accuracy trends")
):
    """
    Get quality assessment report
    
    - **include_trends**: Include accuracy trend data
    """
    try:
        collector = FeedbackCollector()
        
        try:
            # Calculate quality metrics
            total_annotations = 0
            pending = 0
            verified = 0
            corrected = 0
            total_confidence = 0.0
            low_confidence = 0
            
            # In production, query from database
            # For demo, use mock values
            quality_report = QualityReport(
                total_images=total_annotations,
                pending_annotations=pending,
                verified_annotations=verified,
                corrected_annotations=corrected,
                average_confidence=total_confidence / max(total_annotations, 1),
                low_confidence_count=low_confidence,
                accuracy_estimate=collector.calculate_accuracy() if total_annotations > 0 else None
            )
            
            return quality_report
            
        finally:
            collector.close()
        
    except Exception as e:
        logger.error(f"Error getting quality report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=PendingReviewQueue)
async def get_pending_review(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    priority: Optional[str] = Query(None, description="Filter by priority: low, medium, high")
):
    """
    Get pending review queue
    
    - **page**: Page number
    - **page_size**: Items per page
    - **priority**: Optional priority filter
    """
    try:
        # In production, query from database
        # For demo, return empty queue
        items = []
        total = 0
        
        return PendingReviewQueue(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting pending review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=LearningStats)
async def get_learning_stats(
    time_range: Optional[str] = Query("7d", description="Time range: 1d, 7d, 30d, all")
):
    """
    Get learning statistics
    
    - **time_range**: Time range for stats
    """
    try:
        collector = FeedbackCollector()
        
        try:
            recent_feedback = collector.get_recent_feedback(limit=100)
            
            # Calculate feedback by type
            feedback_by_type = {}
            for fb in recent_feedback:
                fb_type = fb.get("feedback_type", "unknown")
                feedback_by_type[fb_type] = feedback_by_type.get(fb_type, 0) + 1
            
            return LearningStats(
                total_feedback=len(recent_feedback),
                feedback_by_type=feedback_by_type,
                accuracy_trend=[],  # Would calculate from historical data
                model_version="v1.0.0"  # Would get from ModelVersion table
            )
            
        finally:
            collector.close()
        
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(feedback_id: str):
    """
    Get a specific feedback record
    
    - **feedback_id**: Feedback identifier
    """
    try:
        feedback = _feedback_store.get(feedback_id)
        
        if not feedback:
            raise HTTPException(
                status_code=404,
                detail=f"Feedback not found: {feedback_id}"
            )
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
