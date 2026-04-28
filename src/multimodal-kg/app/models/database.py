# SPDX-License-Identifier: MIT
"""
Multimodal Knowledge Graph - Database Models
SQLAlchemy models for storing KG data
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, 
    DateTime, Text, JSON, ForeignKey, Table, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings


# Synchronous engine for migrations and simple operations
sync_engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=settings.debug,
    connect_args={"check_same_thread": False}
)

# Asynchronous engine for API operations
DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_path}"
async_engine = create_async_engine(DATABASE_URL, echo=settings.debug)

# Session factories
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# Association tables for many-to-many relationships
image_entity_association = Table(
    'image_entity_associations',
    Base.metadata,
    Column('image_id', String, ForeignKey('images.id'), primary_key=True),
    Column('entity_id', String, ForeignKey('kg_entities.id'), primary_key=True),
    Column('relation_type', String, default='illustrates'),
    Column('confidence', Float, default=1.0),
    Column('created_at', DateTime, default=datetime.utcnow)
)

entity_entity_association = Table(
    'entity_entity_associations',
    Base.metadata,
    Column('source_id', String, ForeignKey('kg_entities.id'), primary_key=True),
    Column('target_id', String, ForeignKey('kg_entities.id'), primary_key=True),
    Column('relation_type', String, primary_key=True),
    Column('properties', JSON, nullable=True),
    Column('confidence', Float, default=1.0),
    Column('created_at', DateTime, default=datetime.utcnow)
)


class Image(Base):
    """Image entity model"""
    __tablename__ = 'images'
    
    id = Column(String, primary_key=True, default=lambda: f"IMG_{uuid.uuid4().hex[:8].upper()}")
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    
    # Metadata
    source = Column(String, nullable=True)  # URL, document name, device ID
    source_type = Column(String, nullable=True)  # url, document, upload, api
    source_context = Column(String, nullable=True)  # Which chapter/section
    original_width = Column(Integer, nullable=True)
    original_height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    
    # Classification
    image_type = Column(String, nullable=True)  # facility, floor_plan, scene, standard, sign
    tags = Column(JSON, default=list)
    
    # Semantic embedding (stored as JSON array)
    embedding = Column(JSON, nullable=True)
    
    # Status
    annotation_status = Column(String, default='pending')  # pending, ai_assisted, verified, corrected
    annotation_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    annotations = relationship("ImageAnnotation", back_populates="image", cascade="all, delete-orphan")
    linked_entities = relationship(
        "KGEntity",
        secondary=image_entity_association,
        back_populates="linked_images"
    )
    
    def __repr__(self):
        return f"<Image {self.id}: {self.filename}>"


class ImageAnnotation(Base):
    """Image annotation model"""
    __tablename__ = 'image_annotations'
    
    id = Column(String, primary_key=True, default=lambda: f"ANN_{uuid.uuid4().hex[:8].upper()}")
    image_id = Column(String, ForeignKey('images.id'), nullable=False)
    
    # Annotator info
    annotator_type = Column(String, default='AI')  # AI, human, system
    annotator_id = Column(String, nullable=True)  # user ID or model name
    
    # Scene annotation
    scene_type = Column(String, nullable=True)
    scene_confidence = Column(Float, nullable=True)
    
    # Detected objects (JSON array)
    objects = Column(JSON, default=list)  # [{"type": "", "bbox": [], "attributes": {}}]
    
    # Relationships between objects
    relationships = Column(JSON, default=list)  # [{"source": "", "target": "", "type": "", "confidence": 0.9}]
    
    # OCR results
    ocr_text = Column(Text, nullable=True)
    ocr_regions = Column(JSON, nullable=True)
    
    # Norm reference
    norm_standard = Column(String, nullable=True)
    norm_clause = Column(String, nullable=True)
    norm_description = Column(Text, nullable=True)
    
    # Tags
    tags = Column(JSON, default=list)
    
    # Overall confidence
    confidence = Column(Float, default=0.0)
    
    # Verification status
    status = Column(String, default='pending')  # pending, verified, corrected
    correction_note = Column(Text, nullable=True)
    
    # Learning tracking
    feedback_count = Column(Integer, default=0)
    last_feedback_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    image = relationship("Image", back_populates="annotations")
    
    def __repr__(self):
        return f"<Annotation {self.id} for {self.image_id}>"


class KGEntity(Base):
    """Knowledge Graph Entity model"""
    __tablename__ = 'kg_entities'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # text, image, concept, event, etc.
    
    # For text entities
    text_content = Column(Text, nullable=True)
    source_document = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
    
    # For image entities
    image_id = Column(String, ForeignKey('images.id'), nullable=True)
    
    # Properties
    properties = Column(JSON, default=dict)  # Flexible properties
    cluster = Column(String, nullable=True)  # Belongs to which cluster
    
    # Semantic info
    description = Column(Text, nullable=True)
    embedding = Column(JSON, nullable=True)
    
    # Quality metrics
    confidence = Column(Float, default=1.0)
    verification_status = Column(String, default='auto')  # auto, verified, corrected
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    linked_images = relationship(
        "Image",
        secondary=image_entity_association,
        back_populates="linked_entities"
    )
    
    # Self-referential relationships
    outgoing_relations = relationship(
        "KGEntity",
        secondary=entity_entity_association,
        primaryjoin=id==entity_entity_association.c.source_id,
        secondaryjoin=id==entity_entity_association.c.target_id,
        backref="incoming_relations"
    )
    
    __table_args__ = (
        Index('idx_entity_name', 'name'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_entity_cluster', 'cluster'),
    )
    
    def __repr__(self):
        return f"<KGEntity {self.id}: {self.name}>"


class KGRelationship(Base):
    """Knowledge Graph Relationship model"""
    __tablename__ = 'kg_relationships'
    
    id = Column(String, primary_key=True, default=lambda: f"REL_{uuid.uuid4().hex[:8].upper()}")
    source_id = Column(String, ForeignKey('kg_entities.id'), nullable=False)
    target_id = Column(String, ForeignKey('kg_entities.id'), nullable=False)
    relation_type = Column(String, nullable=False)
    
    # Properties
    properties = Column(JSON, default=dict)  # e.g., {"weight": 0.8, "direction": "forward"}
    
    # For evidence linking (Skill 6)
    evidence = Column(Text, nullable=True)  # Statistical evidence
    hypothesis_status = Column(String, nullable=True)  # supported, partial, rejected
    
    # Quality
    confidence = Column(Float, default=1.0)
    source = Column(String, nullable=True)  # which document/paper
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source_entity = relationship("KGEntity", foreign_keys=[source_id])
    target_entity = relationship("KGEntity", foreign_keys=[target_id])
    
    __table_args__ = (
        Index('idx_rel_type', 'relation_type'),
        UniqueConstraint('source_id', 'target_id', 'relation_type', name='uq_relationship'),
    )
    
    def __repr__(self):
        return f"<KGRelationship {self.source_id} --[{self.relation_type}]--> {self.target_id}>"


class KnowledgeGraph(Base):
    """Knowledge Graph container model"""
    __tablename__ = 'knowledge_graphs'
    
    id = Column(String, primary_key=True, default=lambda: f"KG_{uuid.uuid4().hex[:8].upper()}")
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    graph_type = Column(String, default='text')  # text, image, multimodal
    
    # Graph metadata
    entity_count = Column(Integer, default=0)
    relationship_count = Column(Integer, default=0)
    source_documents = Column(JSON, default=list)
    
    # Visualization settings
    visualization_format = Column(String, default='mermaid')
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)
    last_audit_at = Column(DateTime, nullable=True)
    
    # KG data (stored as JSON for flexibility)
    graph_data = Column(JSON, nullable=True)  # Full graph in JSON format
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeGraph {self.id}: {self.name}>"


class AnnotationFeedback(Base):
    """User feedback for annotations"""
    __tablename__ = 'annotation_feedback'
    
    id = Column(String, primary_key=True, default=lambda: f"FB_{uuid.uuid4().hex[:8].upper()}")
    annotation_id = Column(String, ForeignKey('image_annotations.id'), nullable=False)
    
    # Feedback details
    feedback_type = Column(String, nullable=False)  # correct, incorrect, partial
    correction_data = Column(JSON, nullable=True)  # What was corrected
    
    # User info
    user_id = Column(String, nullable=True)
    user_role = Column(String, default='annotator')  # annotator, expert, admin
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Feedback {self.id} for {self.annotation_id}: {self.feedback_type}>"


class ModelVersion(Base):
    """Track annotation model versions"""
    __tablename__ = 'model_versions'
    
    id = Column(String, primary_key=True, default=lambda: f"MV_{uuid.uuid4().hex[:8].upper()}")
    model_type = Column(String, nullable=False)  # detection, ocr, embedding
    version = Column(String, nullable=False)
    
    # Training info
    training_samples = Column(Integer, default=0)
    accuracy = Column(Float, nullable=True)
    
    # Status
    status = Column(String, default='active')  # training, active, deprecated
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ModelVersion {self.model_type} v{self.version}>"


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=sync_engine)


def get_sync_session():
    """Get synchronous database session"""
    session = SyncSessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise


async def get_async_session():
    """Get asynchronous database session"""
    async with AsyncSessionLocal() as session:
        yield session
