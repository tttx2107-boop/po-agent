# SPDX-License-Identifier: MIT
"""
M3 Self-Learning Controller for Multimodal Knowledge Graph System
Implements continuous learning from human feedback with incremental model updates
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import (
    ImageAnnotation,
    AnnotationFeedback,
    ModelVersion,
    SyncSessionLocal,
    init_db
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FeedbackResult:
    """Result of recording feedback"""
    feedback_id: str
    annotation_id: str
    success: bool
    message: str
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LearningResult:
    """Result of incremental learning operation"""
    success: bool
    model_version: Optional[str] = None
    samples_trained: int = 0
    accuracy_delta: float = 0.0
    message: str = ""
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QualityReport:
    """Quality assessment report"""
    overall_accuracy: float
    error_categories: Dict[str, int]
    pending_review_count: int
    feedback_ratio: float
    accuracy_vs_feedback_correlation: float
    quality_score: float
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PendingReviewItem:
    """Single item in pending review queue"""
    annotation_id: str
    image_id: str
    annotator_type: str
    confidence: float
    feedback_count: int
    created_at: datetime
    scene_type: Optional[str] = None


@dataclass
class PendingReviewQueue:
    """Paginated pending review queue"""
    items: List[PendingReviewItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass
class QualityMetrics:
    """Quality metrics for annotations"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    error_rate: float
    coverage: float


@dataclass
class TrainingData:
    """Training data for incremental learning"""
    positive_samples: List[Dict[str, Any]]
    negative_samples: List[Dict[str, Any]]
    total_count: int
    source_annotation_ids: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Error Categories
# =============================================================================

class ErrorCategory:
    """Error categories for annotation feedback"""
    MISSING_OBJECT = "missing_object"
    WRONG_TYPE = "wrong_type"
    WRONG_BBOX = "wrong_bbox"
    WRONG_RELATION = "wrong_relation"
    WRONG_ATTRIBUTE = "wrong_attribute"
    
    ALL = [MISSING_OBJECT, WRONG_TYPE, WRONG_BBOX, WRONG_RELATION, WRONG_ATTRIBUTE]


# =============================================================================
# Feedback Collector
# =============================================================================

class FeedbackCollector:
    """Collects and analyzes user feedback on annotations"""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._feedback_cache: List[Dict[str, Any]] = []
    
    @property
    def session(self) -> Session:
        """Get database session"""
        if self._session is None:
            self._session = SyncSessionLocal()
        return self._session
    
    def close(self):
        """Close database session"""
        if self._session:
            self._session.close()
            self._session = None
    
    def collect_correction(
        self,
        annotation_id: str,
        corrections: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> None:
        """
        Collect a correction from user feedback.
        
        Args:
            annotation_id: The annotation being corrected
            corrections: Dictionary containing correction details
            user_id: Optional user ID for tracking
        """
        try:
            # Validate annotation exists
            annotation = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.id == annotation_id
            ).first()
            
            if not annotation:
                logger.warning(f"Annotation {annotation_id} not found")
                return
            
            # Create feedback record
            feedback = AnnotationFeedback(
                id=f"FB_{uuid.uuid4().hex[:8].upper()}",
                annotation_id=annotation_id,
                feedback_type=corrections.get('feedback_type', 'corrected'),
                correction_data=corrections,
                user_id=user_id,
                user_role=corrections.get('user_role', 'annotator'),
                notes=corrections.get('notes')
            )
            
            self.session.add(feedback)
            
            # Update annotation metadata
            annotation.feedback_count += 1
            annotation.last_feedback_at = datetime.utcnow()
            
            # If correction provided, update annotation status
            if corrections.get('corrected_data'):
                annotation.status = 'corrected'
                self._save_corrected_annotation(annotation, corrections)
            
            self.session.commit()
            
            # Add to cache for batch analysis
            self._feedback_cache.append({
                'annotation_id': annotation_id,
                'corrections': corrections,
                'user_id': user_id,
                'timestamp': datetime.utcnow()
            })
            
            logger.info(f"Collected feedback for annotation {annotation_id}")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error collecting feedback: {e}")
            raise
    
    def _save_corrected_annotation(
        self,
        annotation: ImageAnnotation,
        corrections: Dict[str, Any]
    ) -> None:
        """Save corrected annotation to file system"""
        try:
            corrected_path = settings.annotations_corrected
            corrected_path.mkdir(parents=True, exist_ok=True)
            
            # Load existing annotation data
            annotation_data = {
                'id': annotation.id,
                'image_id': annotation.image_id,
                'objects': annotation.objects,
                'relationships': annotation.relationships,
                'scene_type': annotation.scene_type,
                'scene_confidence': annotation.scene_confidence,
                'ocr_text': annotation.ocr_text,
                'ocr_regions': annotation.ocr_regions,
                'corrected_data': corrections.get('corrected_data'),
                'original_corrections': corrections,
                'corrected_at': datetime.utcnow().isoformat()
            }
            
            # Save to JSON file
            output_file = corrected_path / f"{annotation.id}_corrected.json"
            with open(output_file, 'w') as f:
                json.dump(annotation_data, f, indent=2)
            
            logger.debug(f"Saved corrected annotation to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving corrected annotation: {e}")
    
    def categorize_errors(self, feedback_list: Optional[List[Dict]] = None) -> Dict[str, int]:
        """
        Categorize errors from feedback.
        
        Args:
            feedback_list: Optional list of feedback dicts. If None, uses cached feedback.
            
        Returns:
            Dictionary mapping error categories to counts
        """
        if feedback_list is None:
            feedback_list = self._feedback_cache
        
        error_counts = {cat: 0 for cat in ErrorCategory.ALL}
        
        for feedback in feedback_list:
            corrections = feedback.get('corrections', {})
            error_categories = corrections.get('error_categories', [])
            
            for error in error_categories:
                if error in error_counts:
                    error_counts[error] += 1
        
        return error_counts
    
    def calculate_accuracy(self) -> float:
        """
        Calculate overall annotation accuracy based on feedback.
        
        Returns:
            Accuracy score between 0 and 1
        """
        try:
            total_feedback = self.session.query(AnnotationFeedback).count()
            
            if total_feedback == 0:
                return 1.0  # No feedback = assume accurate
            
            # Count positive (correct) vs negative (incorrect) feedback
            correct_count = self.session.query(AnnotationFeedback).filter(
                AnnotationFeedback.feedback_type == 'correct'
            ).count()
            
            partial_count = self.session.query(AnnotationFeedback).filter(
                AnnotationFeedback.feedback_type == 'partial'
            ).count()
            
            # Weight partial corrections (50% credit)
            weighted_correct = correct_count + (partial_count * 0.5)
            accuracy = weighted_correct / total_feedback
            
            return round(accuracy, 4)
            
        except Exception as e:
            logger.error(f"Error calculating accuracy: {e}")
            return 0.0
    
    def get_recent_feedback(
        self,
        limit: int = 100,
        annotation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent feedback records"""
        query = self.session.query(AnnotationFeedback)
        
        if annotation_id:
            query = query.filter(AnnotationFeedback.annotation_id == annotation_id)
        
        feedback_records = query.order_by(
            AnnotationFeedback.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                'id': f.id,
                'annotation_id': f.annotation_id,
                'feedback_type': f.feedback_type,
                'correction_data': f.correction_data,
                'user_id': f.user_id,
                'created_at': f.created_at.isoformat()
            }
            for f in feedback_records
        ]


# =============================================================================
# Incremental Learner
# =============================================================================

class IncrementalLearner:
    """Handles incremental model learning from corrected annotations"""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._current_version = self._load_current_version()
    
    @property
    def session(self) -> Session:
        """Get database session"""
        if self._session is None:
            self._session = SyncSessionLocal()
        return self._session
    
    def close(self):
        """Close database session"""
        if self._session:
            self._session.close()
            self._session = None
    
    def _load_current_version(self) -> Optional[ModelVersion]:
        """Load the current active model version"""
        return self.session.query(ModelVersion).filter(
            ModelVersion.status == 'active'
        ).order_by(ModelVersion.created_at.desc()).first()
    
    def should_update_model(self) -> bool:
        """
        Determine if model should be updated based on accumulated feedback.
        
        Returns:
            True if update criteria are met
        """
        try:
            # Check minimum feedback ratio threshold
            total_annotations = self.session.query(ImageAnnotation).count()
            
            if total_annotations == 0:
                return False
            
            # Count annotations with feedback
            annotated_with_feedback = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.feedback_count > 0
            ).count()
            
            feedback_ratio = annotated_with_feedback / total_annotations
            
            # Check if we have enough feedback
            has_enough_feedback = (
                feedback_ratio >= settings.min_feedback_ratio or
                annotated_with_feedback >= settings.feedback_batch_size
            )
            
            # Check if there's been improvement opportunity
            corrected_count = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'corrected'
            ).count()
            
            has_corrections = corrected_count > 0
            
            should_update = has_enough_feedback and has_corrections
            
            logger.info(
                f"Model update check: ratio={feedback_ratio:.2%}, "
                f"feedback_count={annotated_with_feedback}, "
                f"corrections={corrected_count}, "
                f"should_update={should_update}"
            )
            
            return should_update
            
        except Exception as e:
            logger.error(f"Error checking model update criteria: {e}")
            return False
    
    def prepare_training_data(self) -> TrainingData:
        """
        Prepare training data from corrected annotations.
        
        Returns:
            TrainingData object containing samples for training
        """
        try:
            # Get corrected annotations
            corrected_annotations = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'corrected'
            ).all()
            
            positive_samples = []
            negative_samples = []
            source_ids = []
            
            for annotation in corrected_annotations:
                source_ids.append(annotation.id)
                
                # Load corrected data from file if available
                corrected_file = settings.annotations_corrected / f"{annotation.id}_corrected.json"
                
                if corrected_file.exists():
                    with open(corrected_file, 'r') as f:
                        corrected_data = json.load(f)
                    
                    # Add as positive sample (ground truth)
                    positive_samples.append({
                        'annotation_id': annotation.id,
                        'image_id': annotation.image_id,
                        'corrected_objects': corrected_data.get('corrected_data', {}).get('objects'),
                        'corrected_relationships': corrected_data.get('corrected_data', {}).get('relationships'),
                        'scene_type': corrected_data.get('corrected_data', {}).get('scene_type'),
                        'source': 'human_correction'
                    })
                else:
                    # Use current annotation as positive sample
                    positive_samples.append({
                        'annotation_id': annotation.id,
                        'image_id': annotation.image_id,
                        'objects': annotation.objects,
                        'relationships': annotation.relationships,
                        'scene_type': annotation.scene_type,
                        'source': 'verified_annotation'
                    })
                
                # Add original (incorrect) as negative sample if we have corrections
                if corrected_file.exists():
                    negative_samples.append({
                        'annotation_id': annotation.id,
                        'original_objects': annotation.objects,
                        'original_relationships': annotation.relationships,
                        'correction_reason': 'human_feedback'
                    })
            
            training_data = TrainingData(
                positive_samples=positive_samples,
                negative_samples=negative_samples,
                total_count=len(positive_samples),
                source_annotation_ids=source_ids
            )
            
            logger.info(
                f"Prepared training data: {len(positive_samples)} positive, "
                f"{len(negative_samples)} negative samples"
            )
            
            return training_data
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return TrainingData(
                positive_samples=[],
                negative_samples=[],
                total_count=0,
                source_annotation_ids=[]
            )
    
    def update_annotator_model(self, training_data: TrainingData) -> ModelVersion:
        """
        Update the annotator model with new training data.
        
        Args:
            training_data: Prepared training data
            
        Returns:
            New ModelVersion record
        """
        try:
            if training_data.total_count == 0:
                raise ValueError("No training samples available")
            
            # Generate new version number
            current_ver = self._current_version
            if current_ver:
                try:
                    major, minor = current_ver.version.split('.')
                    version = f"{major}.{int(minor) + 1}"
                except:
                    version = "1.1"
            else:
                version = "1.0"
            
            # Calculate mock accuracy (in real system, this would be from evaluation)
            old_accuracy = current_ver.accuracy if current_ver else 0.5
            new_accuracy = min(0.99, old_accuracy + (training_data.total_count * 0.001))
            
            # Create new model version record
            model_version = ModelVersion(
                id=f"MV_{uuid.uuid4().hex[:8].upper()}",
                model_type="annotation",
                version=version,
                training_samples=training_data.total_count,
                accuracy=round(new_accuracy, 4),
                status='training'
            )
            
            self.session.add(model_version)
            
            # Mark old version as deprecated
            if current_ver:
                current_ver.status = 'deprecated'
            
            self.session.commit()
            
            # Simulate training completion (in real system, would call ML pipeline)
            model_version.status = 'active'
            self.session.commit()
            
            self._current_version = model_version
            
            logger.info(
                f"Updated model to version {version} "
                f"with {training_data.total_count} samples"
            )
            
            return model_version
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating model: {e}")
            raise
    
    def get_model_versions(self, limit: int = 10) -> List[ModelVersion]:
        """Get recent model versions"""
        return self.session.query(ModelVersion).order_by(
            ModelVersion.created_at.desc()
        ).limit(limit).all()


# =============================================================================
# Active Learning Selector
# =============================================================================

class ActiveLearningSelector:
    """Selects samples for active learning based on uncertainty"""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
    
    @property
    def session(self) -> Session:
        """Get database session"""
        if self._session is None:
            self._session = SyncSessionLocal()
        return self._session
    
    def close(self):
        """Close database session"""
        if self._session:
            self._session.close()
            self._session = None
    
    def select_uncertain_samples(
        self,
        annotation_ids: List[str],
        n: int = 10
    ) -> List[str]:
        """
        Select the most uncertain samples for human review.
        
        Args:
            annotation_ids: List of candidate annotation IDs
            n: Number of samples to select
            
        Returns:
            List of selected annotation IDs
        """
        if not annotation_ids:
            return []
        
        # Get annotations with their uncertainty scores
        annotations = self.session.query(ImageAnnotation).filter(
            ImageAnnotation.id.in_(annotation_ids)
        ).all()
        
        # Calculate uncertainty scores
        uncertainty_scores = self.uncertainty_sampling(annotations)
        
        # Sort by uncertainty (highest first) and take top n
        sorted_samples = sorted(
            uncertainty_scores,
            key=lambda x: x[1],
            reverse=True
        )
        
        selected = [ann_id for ann_id, _ in sorted_samples[:n]]
        
        logger.info(f"Selected {len(selected)} uncertain samples from {len(annotation_ids)} candidates")
        
        return selected
    
    def uncertainty_sampling(
        self,
        annotations: List[ImageAnnotation]
    ) -> List[Tuple[str, float]]:
        """
        Calculate uncertainty scores for annotations.
        
        Uncertainty is based on:
        - Low confidence scores
        - High feedback count (repeated corrections)
        - Low annotator agreement
        
        Args:
            annotations: List of ImageAnnotation objects
            
        Returns:
            List of (annotation_id, uncertainty_score) tuples
        """
        scores = []
        
        for annotation in annotations:
            # Base uncertainty from confidence
            confidence = annotation.confidence or 0.5
            base_uncertainty = 1.0 - confidence
            
            # Penalty for multiple feedback rounds
            feedback_penalty = min(0.3, annotation.feedback_count * 0.1)
            
            # Penalty for AI annotations (higher uncertainty)
            annotator_penalty = 0.2 if annotation.annotator_type == 'AI' else 0.0
            
            # Penalty for complex scenes
            complexity_penalty = 0.0
            if annotation.objects and len(annotation.objects) > 5:
                complexity_penalty = 0.1
            if annotation.relationships and len(annotation.relationships) > 3:
                complexity_penalty += 0.1
            
            # Calculate final uncertainty score
            uncertainty = (
                base_uncertainty +
                feedback_penalty +
                annotator_penalty +
                complexity_penalty
            )
            
            # Normalize to [0, 1]
            uncertainty = min(1.0, max(0.0, uncertainty))
            
            scores.append((annotation.id, uncertainty))
        
        return scores
    
    def get_batch_for_review(
        self,
        batch_size: int = 10,
        prefer_uncertain: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get a batch of annotations for human review.
        
        Args:
            batch_size: Number of annotations to return
            prefer_uncertain: Whether to prioritize uncertain samples
            
        Returns:
            List of annotation details for review
        """
        try:
            # Get pending annotations
            query = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'pending'
            )
            
            if prefer_uncertain:
                # Order by confidence (lowest first)
                query = query.order_by(ImageAnnotation.confidence.asc())
            else:
                # Order by creation time (oldest first)
                query = query.order_by(ImageAnnotation.created_at.asc())
            
            annotations = query.limit(batch_size).all()
            
            return [
                {
                    'annotation_id': ann.id,
                    'image_id': ann.image_id,
                    'confidence': ann.confidence,
                    'scene_type': ann.scene_type,
                    'objects_count': len(ann.objects) if ann.objects else 0,
                    'relationships_count': len(ann.relationships) if ann.relationships else 0,
                    'created_at': ann.created_at.isoformat()
                }
                for ann in annotations
            ]
            
        except Exception as e:
            logger.error(f"Error getting batch for review: {e}")
            return []


# =============================================================================
# Quality Assessor
# =============================================================================

class QualityAssessor:
    """Assesses annotation quality and provides metrics"""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._collector = FeedbackCollector(session)
    
    @property
    def session(self) -> Session:
        """Get database session"""
        if self._session is None:
            self._session = SyncSessionLocal()
        return self._session
    
    def close(self):
        """Close database session"""
        if self._session:
            self._session.close()
            self._session = None
        self._collector.close()
    
    def calculate_metrics(self) -> QualityMetrics:
        """
        Calculate comprehensive quality metrics.
        
        Returns:
            QualityMetrics object with quality scores
        """
        try:
            # Get annotation counts
            total_annotations = self.session.query(ImageAnnotation).count()
            verified = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'verified'
            ).count()
            corrected = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'corrected'
            ).count()
            
            if total_annotations == 0:
                return QualityMetrics(
                    accuracy=0.0,
                    precision=0.0,
                    recall=0.0,
                    f1_score=0.0,
                    error_rate=0.0,
                    coverage=0.0
                )
            
            # Calculate accuracy
            accuracy = self._collector.calculate_accuracy()
            
            # Calculate precision based on AI vs human annotations
            ai_annotations = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.annotator_type == 'AI'
            ).count()
            
            human_annotations = total_annotations - ai_annotations
            precision = human_annotations / total_annotations if total_annotations > 0 else 0.0
            
            # Calculate recall (how many verified vs total)
            recall = (verified + corrected) / total_annotations
            
            # F1 score
            if precision + recall > 0:
                f1_score = 2 * (precision * recall) / (precision + recall)
            else:
                f1_score = 0.0
            
            # Error rate
            feedback_count = self.session.query(AnnotationFeedback).count()
            error_rate = feedback_count / total_annotations if total_annotations > 0 else 0.0
            
            # Coverage (how many images have annotations)
            annotated_images = self.session.query(
                func.count(func.distinct(ImageAnnotation.image_id))
            ).scalar()
            
            total_images = self.session.query(func.count()).select_from(
                # This would need an Image table, using annotation count as proxy
            ).scalar() or total_annotations
            
            coverage = min(1.0, annotated_images / max(1, total_annotations))
            
            return QualityMetrics(
                accuracy=round(accuracy, 4),
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1_score=round(f1_score, 4),
                error_rate=round(error_rate, 4),
                coverage=round(coverage, 4)
            )
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return QualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def accuracy_vs_feedback(self) -> float:
        """
        Calculate correlation between annotation accuracy and feedback.
        
        Returns:
            Correlation coefficient between accuracy and feedback volume
        """
        try:
            # Get annotations with feedback
            annotations_with_feedback = self.session.query(ImageAnnotation).filter(
                ImageAnnotation.feedback_count > 0
            ).all()
            
            if len(annotations_with_feedback) < 2:
                return 0.0
            
            # Calculate accuracy for each annotation with feedback
            correct = 0
            incorrect = 0
            
            for annotation in annotations_with_feedback:
                feedback = self.session.query(AnnotationFeedback).filter(
                    AnnotationFeedback.annotation_id == annotation.id
                ).first()
                
                if feedback:
                    if feedback.feedback_type == 'correct':
                        correct += 1
                    elif feedback.feedback_type in ['incorrect', 'partial']:
                        incorrect += 1
            
            total = correct + incorrect
            if total == 0:
                return 0.0
            
            # Higher ratio of correct feedback indicates good accuracy
            correlation = (correct - incorrect) / total
            
            return round(correlation, 4)
            
        except Exception as e:
            logger.error(f"Error calculating accuracy-feedback correlation: {e}")
            return 0.0
    
    def generate_recommendations(self, metrics: QualityMetrics) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        if metrics.accuracy < 0.7:
            recommendations.append("Low accuracy detected. Consider reviewing AI annotation thresholds.")
        
        if metrics.error_rate > 0.3:
            recommendations.append("High error rate. Implement more stringent validation rules.")
        
        if metrics.coverage < 0.5:
            recommendations.append("Low annotation coverage. Increase annotation efforts.")
        
        if metrics.f1_score < 0.6:
            recommendations.append("Poor precision-recall balance. Review annotation guidelines.")
        
        # Check for specific error patterns
        collector = FeedbackCollector(self.session)
        errors = collector.categorize_errors()
        
        if errors.get(ErrorCategory.WRONG_BBOX, 0) > errors.get(ErrorCategory.MISSING_OBJECT, 0):
            recommendations.append("Focus on bbox accuracy in training data.")
        
        if errors.get(ErrorCategory.WRONG_TYPE, 0) > 5:
            recommendations.append("Type classification errors detected. Review type hierarchy.")
        
        if errors.get(ErrorCategory.WRONG_RELATION, 0) > 5:
            recommendations.append("Relationship detection needs improvement. Add more relation examples.")
        
        if not recommendations:
            recommendations.append("Quality metrics are within acceptable ranges.")
        
        return recommendations


# =============================================================================
# Main Self-Learning Controller
# =============================================================================

class SelfLearningController:
    """
    Main controller for the M3 Self-Learning system.
    Coordinates feedback collection, incremental learning, active learning,
    and quality assessment.
    """
    
    def __init__(self):
        self._session = SyncSessionLocal()
        self.feedback_collector = FeedbackCollector(self._session)
        self.incremental_learner = IncrementalLearner(self._session)
        self.active_learning_selector = ActiveLearningSelector(self._session)
        self.quality_assessor = QualityAssessor(self._session)
        
        logger.info("SelfLearningController initialized")
    
    def close(self):
        """Close all resources"""
        self.feedback_collector.close()
        self.incremental_learner.close()
        self.active_learning_selector.close()
        self.quality_assessor.close()
        self._session.close()
    
    def record_feedback(
        self,
        annotation_id: str,
        feedback_data: Dict[str, Any]
    ) -> FeedbackResult:
        """
        Record feedback for an annotation.
        
        Args:
            annotation_id: The annotation ID receiving feedback
            feedback_data: Dictionary containing feedback details
            
        Returns:
            FeedbackResult with recording status
        """
        try:
            # Validate feedback data
            if not feedback_data:
                return FeedbackResult(
                    feedback_id="",
                    annotation_id=annotation_id,
                    success=False,
                    message="No feedback data provided",
                    error_type="missing_data"
                )
            
            # Collect the correction
            self.feedback_collector.collect_correction(
                annotation_id=annotation_id,
                corrections=feedback_data,
                user_id=feedback_data.get('user_id')
            )
            
            # Generate feedback ID
            feedback_id = f"FB_{uuid.uuid4().hex[:8].upper()}"
            
            return FeedbackResult(
                feedback_id=feedback_id,
                annotation_id=annotation_id,
                success=True,
                message="Feedback recorded successfully"
            )
            
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
            return FeedbackResult(
                feedback_id="",
                annotation_id=annotation_id,
                success=False,
                message=f"Error recording feedback: {str(e)}",
                error_type="internal_error"
            )
    
    def trigger_incremental_learning(self) -> LearningResult:
        """
        Trigger incremental learning if criteria are met.
        
        Returns:
            LearningResult with update status
        """
        try:
            # Check if update is needed
            if not self.incremental_learner.should_update_model():
                return LearningResult(
                    success=False,
                    message="Model update criteria not met. Not enough feedback accumulated."
                )
            
            # Prepare training data
            training_data = self.incremental_learner.prepare_training_data()
            
            if training_data.total_count == 0:
                return LearningResult(
                    success=False,
                    message="No training samples available"
                )
            
            # Update model
            new_version = self.incremental_learner.update_annotator_model(training_data)
            
            # Calculate accuracy delta
            old_version = self.incremental_learner._current_version
            accuracy_delta = 0.0
            if old_version and new_version:
                accuracy_delta = new_version.accuracy - old_version.accuracy
            
            return LearningResult(
                success=True,
                model_version=new_version.version,
                samples_trained=training_data.total_count,
                accuracy_delta=round(accuracy_delta, 4),
                message=f"Model updated to version {new_version.version}"
            )
            
        except Exception as e:
            logger.error(f"Error in incremental learning: {e}")
            return LearningResult(
                success=False,
                message=f"Error during learning: {str(e)}",
                errors=[str(e)]
            )
    
    def assess_quality(self) -> QualityReport:
        """
        Assess overall annotation quality.
        
        Returns:
            QualityReport with quality metrics and recommendations
        """
        try:
            # Calculate metrics
            metrics = self.quality_assessor.calculate_metrics()
            
            # Get error categories
            error_categories = self.feedback_collector.categorize_errors()
            
            # Get pending review count
            pending_count = self._session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'pending'
            ).count()
            
            # Calculate feedback ratio
            total_annotations = self._session.query(ImageAnnotation).count()
            feedback_count = self._session.query(AnnotationFeedback).count()
            feedback_ratio = feedback_count / total_annotations if total_annotations > 0 else 0.0
            
            # Get accuracy-feedback correlation
            correlation = self.quality_assessor.accuracy_vs_feedback()
            
            # Generate quality score (weighted average of metrics)
            quality_score = (
                metrics.accuracy * 0.3 +
                metrics.f1_score * 0.3 +
                (1 - metrics.error_rate) * 0.2 +
                metrics.coverage * 0.2
            )
            
            # Generate recommendations
            recommendations = self.quality_assessor.generate_recommendations(metrics)
            
            return QualityReport(
                overall_accuracy=metrics.accuracy,
                error_categories=error_categories,
                pending_review_count=pending_count,
                feedback_ratio=round(feedback_ratio, 4),
                accuracy_vs_feedback_correlation=correlation,
                quality_score=round(quality_score, 4),
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error assessing quality: {e}")
            return QualityReport(
                overall_accuracy=0.0,
                error_categories={},
                pending_review_count=0,
                feedback_ratio=0.0,
                accuracy_vs_feedback_correlation=0.0,
                quality_score=0.0,
                recommendations=["Error assessing quality. Please try again."]
            )
    
    def get_pending_review_queue(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> PendingReviewQueue:
        """
        Get paginated list of annotations pending review.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            PendingReviewQueue with paginated results
        """
        try:
            # Query pending annotations with uncertainty scores
            query = self._session.query(ImageAnnotation).filter(
                ImageAnnotation.status == 'pending'
            )
            
            # Get total count
            total_count = query.count()
            
            # Calculate pagination
            offset = (page - 1) * page_size
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            
            # Get annotations with uncertainty sorting
            annotations = query.order_by(
                ImageAnnotation.confidence.asc(),
                ImageAnnotation.feedback_count.desc()
            ).offset(offset).limit(page_size).all()
            
            # Build items
            items = [
                PendingReviewItem(
                    annotation_id=ann.id,
                    image_id=ann.image_id,
                    annotator_type=ann.annotator_type,
                    confidence=ann.confidence or 0.0,
                    feedback_count=ann.feedback_count,
                    created_at=ann.created_at,
                    scene_type=ann.scene_type
                )
                for ann in annotations
            ]
            
            return PendingReviewQueue(
                items=items,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"Error getting pending review queue: {e}")
            return PendingReviewQueue(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
    
    def select_samples_for_review(self, n: int = 10) -> List[str]:
        """
        Select the most uncertain samples for human review using active learning.
        
        Args:
            n: Number of samples to select
            
        Returns:
            List of annotation IDs to review
        """
        try:
            # Get all pending annotation IDs
            pending_ids = [
                ann[0] for ann in self._session.query(ImageAnnotation.id).filter(
                    ImageAnnotation.status == 'pending'
                ).all()
            ]
            
            return self.active_learning_selector.select_uncertain_samples(pending_ids, n)
            
        except Exception as e:
            logger.error(f"Error selecting samples for review: {e}")
            return []


# =============================================================================
# Factory Function
# =============================================================================

def get_self_learning_controller() -> SelfLearningController:
    """Get a new SelfLearningController instance"""
    return SelfLearningController()
