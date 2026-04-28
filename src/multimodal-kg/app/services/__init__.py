# SPDX-License-Identifier: MIT
"""
Services module for multimodal knowledge graph system
"""

from app.services.annotation_engine import (
    AnnotationEngine,
    get_annotation_engine,
    AnnotationResult,
    DetectedObject,
    ObjectRelationship,
    NormReference,
    OCRResult,
    SceneClassifier,
    ObjectDetector,
    OCRProcessor,
    RelationshipExtractor,
    NormReferenceLinker,
)

from app.services.kg_generator import (
    TextKGGenerator,
    KGEntityNode,
    TheoryNode,
    Variable,
    Parameter,
    Boundary,
    ExternalLink,
    ContributionNode,
    ClusterAssignment,
    EvidenceMapping,
    FusedKG,
    QualityReport,
    VisualizationCode,
    VariableType,
    RelationshipLabel,
    HypothesisStatus,
    generate_kg_from_text,
    generate_kg_from_document,
)

__all__ = [
    # Annotation Engine
    "AnnotationEngine",
    "get_annotation_engine",
    "AnnotationResult",
    "DetectedObject",
    "ObjectRelationship",
    "NormReference",
    "OCRResult",
    "SceneClassifier",
    "ObjectDetector",
    "OCRProcessor",
    "RelationshipExtractor",
    "NormReferenceLinker",
    # KG Generator
    "TextKGGenerator",
    "KGEntityNode",
    "TheoryNode",
    "Variable",
    "Parameter",
    "Boundary",
    "ExternalLink",
    "ContributionNode",
    "ClusterAssignment",
    "EvidenceMapping",
    "FusedKG",
    "QualityReport",
    "VisualizationCode",
    "VariableType",
    "RelationshipLabel",
    "HypothesisStatus",
    "generate_kg_from_text",
    "generate_kg_from_document",
]
