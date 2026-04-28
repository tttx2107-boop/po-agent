# SPDX-License-Identifier: MIT
"""
Multimodal Knowledge Graph - Pydantic Schemas
API request and response models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============== Enums ==============

class ImageType(str, Enum):
    FACILITY = "facility"  # 消防设施
    FLOOR_PLAN = "floor_plan"  # 平面图
    SCENE = "scene"  # 现场图
    STANDARD = "standard"  # 规范配图
    SIGN = "sign"  # 标志图
    UNKNOWN = "unknown"


class AnnotationStatus(str, Enum):
    PENDING = "pending"
    AI_ASSISTED = "ai_assisted"
    VERIFIED = "verified"
    CORRECTED = "corrected"


class FeedbackType(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"


class EntityType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    CONCEPT = "concept"
    EVENT = "event"
    RELATION = "relation"


class GraphType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


# ============== Image Schemas ==============

class DetectedObject(BaseModel):
    """Detected object in image"""
    id: str = Field(..., description="Object ID")
    type: str = Field(..., description="Object type")
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Object attributes")
    linked_entity_id: Optional[str] = Field(None, description="Linked KG entity ID")
    confidence: float = Field(1.0, ge=0, le=1)


class ObjectRelationship(BaseModel):
    """Relationship between detected objects"""
    source: str = Field(..., description="Source object ID")
    target: str = Field(..., description="Target object ID")
    relation_type: str = Field(..., description="Relationship type")
    spatial: Optional[str] = Field(None, description="Spatial description")
    confidence: float = Field(1.0, ge=0, le=1)


class SceneAnnotation(BaseModel):
    """Scene-level annotation"""
    type: str = Field(..., description="Scene type")
    confidence: float = Field(..., ge=0, le=1)
    annotated_by: str = Field("AI", description="Annotator type")
    verified_by: Optional[str] = Field(None, description="Verifier")


class ImageAnnotationCreate(BaseModel):
    """Create annotation request"""
    scene: Optional[SceneAnnotation] = None
    objects: List[DetectedObject] = Field(default_factory=list)
    relationships: List[ObjectRelationship] = Field(default_factory=list)
    ocr_text: Optional[str] = None
    ocr_regions: Optional[List[Dict]] = None
    norm_standard: Optional[str] = None
    norm_clause: Optional[str] = None
    norm_description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ImageAnnotationResponse(ImageAnnotationCreate):
    """Annotation response"""
    id: str
    image_id: str
    annotator_type: str
    confidence: float
    status: AnnotationStatus
    feedback_count: int
    created_at: datetime
    updated_at: datetime


class ImageMetadata(BaseModel):
    """Image metadata"""
    id: str
    filename: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    source_context: Optional[str] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    image_type: Optional[ImageType] = None
    tags: List[str] = Field(default_factory=list)
    annotation_status: AnnotationStatus = AnnotationStatus.PENDING
    annotation_count: int = 0
    linked_entities: List[str] = Field(default_factory=list)
    created_at: datetime


class ImageUploadResponse(BaseModel):
    """Image upload response"""
    id: str
    filename: str
    storage_path: str
    message: str


class ImageDetailResponse(ImageMetadata):
    """Detailed image info with annotations"""
    annotations: List[ImageAnnotationResponse] = Field(default_factory=list)


# ============== KG Entity Schemas ==============

class KGEntityCreate(BaseModel):
    """Create KG entity"""
    id: str = Field(..., description="Entity ID (e.g., E001)")
    name: str = Field(..., description="Entity name")
    entity_type: EntityType = Field(..., description="Entity type")
    text_content: Optional[str] = None
    source_document: Optional[str] = None
    source_section: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    cluster: Optional[str] = None
    description: Optional[str] = None
    confidence: float = Field(1.0, ge=0, le=1)


class KGEntityResponse(KGEntityCreate):
    """KG entity response"""
    image_id: Optional[str] = None
    verification_status: str = "auto"
    created_at: datetime
    updated_at: datetime
    linked_images: List[str] = Field(default_factory=list)


# ============== KG Relationship Schemas ==============

class KGRelationshipCreate(BaseModel):
    """Create KG relationship"""
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence: Optional[str] = None  # Statistical evidence
    hypothesis_status: Optional[str] = None  # supported, partial, rejected
    confidence: float = Field(1.0, ge=0, le=1)
    source: Optional[str] = None


class KGRelationshipResponse(KGRelationshipCreate):
    """KG relationship response"""
    id: str
    created_at: datetime
    updated_at: datetime


# ============== Knowledge Graph Schemas ==============

class KnowledgeGraphCreate(BaseModel):
    """Create knowledge graph"""
    name: str
    description: Optional[str] = None
    graph_type: GraphType = GraphType.TEXT


class KnowledgeGraphResponse(KnowledgeGraphCreate):
    """Knowledge graph response"""
    id: str
    entity_count: int
    relationship_count: int
    source_documents: List[str] = Field(default_factory=list)
    visualization_format: str = "mermaid"
    quality_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# ============== Multimodal Fusion Schemas ==============

class MultimodalEntity(BaseModel):
    """Entity in multimodal KG"""
    id: str
    name: str
    type: str  # text or image
    image_path: Optional[str] = None


class MultimodalRelationship(BaseModel):
    """Relationship in multimodal KG"""
    source: str
    target: str
    type: str
    confidence: float = 1.0


class FusionQuality(BaseModel):
    """Fusion quality metrics"""
    text_image_coverage: float
    orphan_images: int
    orphan_text_entities: int


class MultimodalFusionRequest(BaseModel):
    """Request to fuse text KG with image annotations"""
    text_kg_id: str = Field(..., description="Text KG ID")
    image_ids: List[str] = Field(default_factory=list, description="Image IDs to fuse")


class MultimodalFusionResponse(BaseModel):
    """Multimodal fusion result"""
    multimodal_entities: List[MultimodalEntity]
    relationships: List[MultimodalRelationship]
    fusion_quality: FusionQuality
    mermaid_code: Optional[str] = None
    d3_json: Optional[Dict] = None


# ============== Feedback Schemas ==============

class FeedbackCreate(BaseModel):
    """Create feedback"""
    annotation_id: str
    feedback_type: FeedbackType
    correction_data: Optional[Dict] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None


class FeedbackResponse(FeedbackCreate):
    """Feedback response"""
    id: str
    user_role: str = "annotator"
    created_at: datetime


# ============== Learning Schemas ==============

class QualityReport(BaseModel):
    """Quality assessment report"""
    total_images: int
    pending_annotations: int
    verified_annotations: int
    corrected_annotations: int
    average_confidence: float
    low_confidence_count: int
    accuracy_estimate: Optional[float] = None


class LearningStats(BaseModel):
    """Learning statistics"""
    total_feedback: int
    feedback_by_type: Dict[str, int]
    accuracy_trend: List[Dict[str, Any]]
    model_version: str


class PendingReviewQueue(BaseModel):
    """Queue of items pending review"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


# ============== Visualization Schemas ==============

class VisualizationRequest(BaseModel):
    """KG visualization request"""
    kg_id: str
    format: str = Field("mermaid", description="mermaid, d3, echarts, plotly, graphviz")
    max_nodes: int = Field(50, ge=1, le=200)
    theme: Optional[str] = None


class VisualizationResponse(BaseModel):
    """Visualization response"""
    kg_id: str
    format: str
    code: str
    render_url: Optional[str] = None  # URL to render


# ============== Batch Operations ==============

class BatchAnnotationRequest(BaseModel):
    """Batch annotate images"""
    image_ids: List[str]
    auto_annotate: bool = True
    min_confidence: float = 0.7


class BatchAnnotationResponse(BaseModel):
    """Batch annotation result"""
    processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


class BatchFusionRequest(BaseModel):
    """Batch fuse multiple sources"""
    text_kg_ids: List[str]
    image_ids: List[str]
    fusion_mode: str = "all"  # all, selective


# ============== Common ==============

class PaginatedResponse(BaseModel):
    """Paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class StatusResponse(BaseModel):
    """Generic status response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
