# SPDX-License-Identifier: MIT
"""
Multimodal Knowledge Graph - M4 Multimodal Fusion Engine
Text-Image bidirectional fusion module
"""
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
from loguru import logger

from app.core.config import settings
from app.models.database import (
    Image, ImageAnnotation, KGEntity, KGRelationship,
    KnowledgeGraph, get_sync_session
)


@dataclass
class ImageMatch:
    """Result of matching text entity to image"""
    image_id: str
    confidence: float
    match_type: str  # 'reference', 'semantic', 'type'
    annotation_id: Optional[str] = None


@dataclass
class EntityMatch:
    """Result of matching image annotation to text entity"""
    entity_id: str
    entity_name: str
    confidence: float
    match_type: str
    linked_objects: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """Detected conflict in fusion"""
    conflict_id: str
    conflict_type: str  # 'duplicate_entity', 'contradictory_image', 'missing_correspondence'
    description: str
    entities_involved: List[str] = field(default_factory=list)
    suggested_resolution: Optional[str] = None
    resolved: bool = False


@dataclass
class MultimodalFusionResult:
    """Result of multimodal fusion"""
    multimodal_entities: List[Dict]
    relationships: List[Dict]
    fusion_quality: Dict
    mermaid_code: str
    d3_json: Optional[Dict] = None


class TextToImageMapper:
    """Maps text entities to images"""
    
    def __init__(self):
        self.session = get_sync_session()
    
    def map_entity_to_image(
        self, 
        entity: KGEntity, 
        image_annotations: List[ImageAnnotation]
    ) -> List[ImageMatch]:
        """Match a text entity to relevant images"""
        matches = []
        entity_name = entity.name.lower()
        
        for annotation in image_annotations:
            if not annotation.objects:
                continue
            
            # Check object type match
            for obj in annotation.objects:
                obj_type = obj.get('type', '').lower()
                
                # Exact or partial name match
                if (entity_name in obj_type or 
                    obj_type in entity_name or
                    self._similarity(entity_name, obj_type) > settings.cross_modal_match_threshold):
                    
                    matches.append(ImageMatch(
                        image_id=annotation.image_id,
                        confidence=self._similarity(entity_name, obj_type),
                        match_type='type',
                        annotation_id=annotation.id
                    ))
            
            # Check OCR text match
            if annotation.ocr_text:
                ocr_lower = annotation.ocr_text.lower()
                if entity_name in ocr_lower:
                    matches.append(ImageMatch(
                        image_id=annotation.image_id,
                        confidence=0.9,
                        match_type='reference',
                        annotation_id=annotation.id
                    ))
            
            # Check tags match
            for tag in annotation.tags:
                if entity_name in tag.lower():
                    matches.append(ImageMatch(
                        image_id=annotation.image_id,
                        confidence=0.8,
                        match_type='semantic',
                        annotation_id=annotation.id
                    ))
        
        # Deduplicate and sort by confidence
        seen = set()
        unique_matches = []
        for m in sorted(matches, key=lambda x: x.confidence, reverse=True):
            if m.image_id not in seen:
                seen.add(m.image_id)
                unique_matches.append(m)
        
        return unique_matches
    
    def parse_image_references(self, document_text: str) -> List[str]:
        """Extract image references from document text"""
        import re
        # Match patterns like "见图X.X", "如图所示", "图X-X"
        patterns = [
            r'见[图阁](\d+[.\-]\d+)',
            r'[图圖](?:\d+[.\-]\d+|\d+)',
            r'如图所示',
            r'如图\d+',
        ]
        
        references = []
        for pattern in patterns:
            matches = re.findall(pattern, document_text, re.IGNORECASE)
            references.extend(matches)
        
        return list(set(references))
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity"""
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return 1.0
        if s1 in s2 or s2 in s1:
            return 0.8
        
        # Simple character overlap
        set1, set2 = set(s1), set(s2)
        overlap = len(set1 & set2)
        total = len(set1 | set2)
        
        return overlap / total if total > 0 else 0.0


class ImageToTextMapper:
    """Maps image annotations to text entities"""
    
    def __init__(self):
        self.session = get_sync_session()
    
    def map_image_to_entity(
        self,
        annotation: ImageAnnotation,
        text_entities: List[KGEntity]
    ) -> List[EntityMatch]:
        """Match an image annotation to relevant text entities"""
        matches = []
        
        for entity in text_entities:
            entity_name = entity.name.lower()
            
            # Check object type match
            for obj in annotation.objects:
                obj_type = obj.get('type', '').lower()
                if (entity_name in obj_type or 
                    obj_type in entity_name or
                    self._similarity(entity_name, obj_type) > settings.cross_modal_match_threshold):
                    
                    matches.append(EntityMatch(
                        entity_id=entity.id,
                        entity_name=entity.name,
                        confidence=self._similarity(entity_name, obj_type),
                        match_type='type',
                        linked_objects=[obj.get('id', '')]
                    ))
            
            # Check annotation tags
            for tag in annotation.tags:
                if entity_name in tag.lower():
                    matches.append(EntityMatch(
                        entity_id=entity.id,
                        entity_name=entity.name,
                        confidence=0.8,
                        match_type='semantic'
                    ))
        
        # Deduplicate
        seen = set()
        unique_matches = []
        for m in sorted(matches, key=lambda x: x.confidence, reverse=True):
            if m.entity_id not in seen:
                seen.add(m.entity_id)
                unique_matches.append(m)
        
        return unique_matches
    
    def extract_entity_references(self, annotation: ImageAnnotation) -> List[str]:
        """Extract potential entity references from annotation"""
        references = []
        
        # From OCR text
        if annotation.ocr_text:
            references.append(annotation.ocr_text)
        
        # From object types
        for obj in annotation.objects:
            obj_type = obj.get('type', '')
            if obj_type:
                references.append(obj_type)
        
        # From tags
        references.extend(annotation.tags or [])
        
        return references
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity"""
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return 1.0
        if s1 in s2 or s2 in s1:
            return 0.8
        
        set1, set2 = set(s1), set(s2)
        overlap = len(set1 & set2)
        total = len(set1 | set2)
        
        return overlap / total if total > 0 else 0.0


class RelationshipEnhancer:
    """Enhances KG relationships using image spatial information"""
    
    def enhance_from_spatial(
        self, 
        annotation: ImageAnnotation
    ) -> List[Dict]:
        """Extract additional relationships from spatial information"""
        enhanced = []
        
        if not annotation.relationships:
            return enhanced
        
        for rel in annotation.relationships:
            rel_type = rel.get('type', '')
            source = rel.get('source', '')
            target = rel.get('target', '')
            spatial = rel.get('spatial', '')
            
            # Convert spatial relations to semantic relations
            spatial_to_semantic = {
                'above': 'superior_to',
                'below': 'inferior_to',
                'left_of': 'adjacent_to',
                'right_of': 'adjacent_to',
                'inside': 'contains',
                'outside': 'excludes',
                'next_to': 'adjacent_to',
            }
            
            if spatial.lower() in spatial_to_semantic:
                enhanced.append({
                    'source': source,
                    'target': target,
                    'relation_type': spatial_to_semantic[spatial.lower()],
                    'original_spatial': spatial,
                    'confidence': rel.get('confidence', 0.8),
                    'source': 'spatial_enhancement'
                })
        
        return enhanced


class ConflictDetector:
    """Detects conflicts in multimodal KG"""
    
    def detect_entity_conflicts(
        self, 
        entities: List[Dict],
        relationships: List[Dict]
    ) -> List[Conflict]:
        """Detect entity-related conflicts"""
        conflicts = []
        
        # Check for duplicate entities (same name, different IDs)
        name_to_ids = {}
        for entity in entities:
            name = entity.get('name', '').lower()
            entity_id = entity.get('id', '')
            if name in name_to_ids:
                conflicts.append(Conflict(
                    conflict_id=f"CON_{uuid.uuid4().hex[:8].upper()}",
                    conflict_type='duplicate_entity',
                    description=f"Entities '{name}' with IDs {name_to_ids[name]} and {entity_id}",
                    entities_involved=[name_to_ids[name], entity_id],
                    suggested_resolution='Merge entities or mark as aliases'
                ))
            else:
                name_to_ids[name] = entity_id
        
        # Check for contradictory images
        image_entities = [e for e in entities if e.get('type') == 'image']
        text_entities = [e for e in entities if e.get('type') == 'text']
        
        for img in image_entities:
            for txt in text_entities:
                # If same name but different types assigned
                if (img.get('name', '').lower() == txt.get('name', '').lower() and
                    img.get('name', '') != txt.get('name', '')):
                    conflicts.append(Conflict(
                        conflict_id=f"CON_{uuid.uuid4().hex[:8].upper()}",
                        conflict_type='contradictory_image',
                        description=f"Text entity '{txt.get('name')}' and image entity '{img.get('name')}' appear similar",
                        entities_involved=[txt.get('id'), img.get('id')],
                        suggested_resolution='Verify if they refer to the same concept'
                    ))
        
        return conflicts
    
    def detect_relationship_conflicts(
        self,
        relationships: List[Dict]
    ) -> List[Conflict]:
        """Detect relationship-related conflicts"""
        conflicts = []
        
        # Check for bidirectional contradictions
        rel_map = {}
        for rel in relationships:
            key = (rel.get('source'), rel.get('target'))
            rev_key = (rel.get('target'), rel.get('source'))
            
            if rev_key in rel_map:
                # Found potential contradiction
                conflicts.append(Conflict(
                    conflict_id=f"CON_{uuid.uuid4().hex[:8].upper()}",
                    conflict_type='contradictory_relation',
                    description=f"Found both {rel_map[rev_key]['relation_type']} and {rel.get('relation_type')} between same entities",
                    entities_involved=[rel.get('source'), rel.get('target')],
                    suggested_resolution='Keep one or clarify relationship type'
                ))
            else:
                rel_map[key] = rel
        
        return conflicts


class FusionEngine:
    """
    Multimodal Fusion Engine
    Fuses text KG with image annotations bidirectionally
    """
    
    def __init__(self):
        self.text_mapper = TextToImageMapper()
        self.image_mapper = ImageToTextMapper()
        self.enhancer = RelationshipEnhancer()
        self.conflict_detector = ConflictDetector()
        self.session = get_sync_session()
        logger.info("FusionEngine initialized")
    
    def fuse(
        self, 
        text_kg_id: str, 
        image_ids: List[str],
        mode: str = 'auto'
    ) -> MultimodalFusionResult:
        """
        Fuse text KG with specified images
        
        Args:
            text_kg_id: ID of the text KG to fuse with
            image_ids: List of image IDs to incorporate
            mode: 'auto' (fuse all) or 'selective' (only strong matches)
        
        Returns:
            MultimodalFusionResult with fused entities and relationships
        """
        logger.info(f"Starting fusion: KG={text_kg_id}, images={len(image_ids)}")
        
        # Load text KG
        text_kg = self.session.query(KnowledgeGraph).filter_by(id=text_kg_id).first()
        if not text_kg:
            raise ValueError(f"Knowledge graph {text_kg_id} not found")
        
        # Load text entities
        text_entities = self.session.query(KGEntity).filter_by().all()
        text_rels = self.session.query(KGRelationship).filter_by().all()
        
        # Load image annotations
        annotations = []
        for img_id in image_ids:
            img_anns = self.session.query(ImageAnnotation).filter_by(image_id=img_id).all()
            annotations.extend(img_anns)
        
        # Collect results
        multimodal_entities = []
        relationships = []
        
        # Add text entities
        for entity in text_entities:
            multimodal_entities.append({
                'id': entity.id,
                'name': entity.name,
                'type': 'text',
                'cluster': entity.cluster,
                'confidence': entity.confidence
            })
        
        # Image-to-Text mapping (images → text entities)
        for annotation in annotations:
            # Get linked image
            image = self.session.query(Image).filter_by(id=annotation.image_id).first()
            
            # Add image as entity
            img_entity = {
                'id': f"{annotation.image_id}_entity",
                'name': f"{image.filename if image else annotation.image_id}",
                'type': 'image',
                'image_path': image.storage_path if image else None,
                'confidence': annotation.confidence
            }
            multimodal_entities.append(img_entity)
            
            # Map to text entities
            entity_matches = self.image_mapper.map_image_to_entity(annotation, text_entities)
            for match in entity_matches:
                if mode == 'selective' and match.confidence < settings.cross_modal_match_threshold:
                    continue
                
                relationships.append({
                    'source': img_entity['id'],
                    'target': match.entity_id,
                    'type': 'illustrates',
                    'confidence': match.confidence,
                    'source_type': 'image_to_text'
                })
        
        # Text-to-Image mapping (text entities → images)
        for entity in text_entities:
            image_matches = self.text_mapper.map_entity_to_image(entity, annotations)
            for match in image_matches:
                if mode == 'selective' and match.confidence < settings.cross_modal_match_threshold:
                    continue
                
                img_entity_id = f"{match.image_id}_entity"
                relationships.append({
                    'source': entity.id,
                    'target': img_entity_id,
                    'type': 'hasImage',
                    'confidence': match.confidence,
                    'source_type': 'text_to_image'
                })
        
        # Add text relationships
        for rel in text_rels:
            relationships.append({
                'source': rel.source_id,
                'target': rel.target_id,
                'type': rel.relation_type,
                'properties': rel.properties or {},
                'evidence': rel.evidence,
                'hypothesis_status': rel.hypothesis_status,
                'confidence': rel.confidence,
                'source_type': 'text'
            })
        
        # Relationship enhancement
        for annotation in annotations:
            enhanced = self.enhancer.enhance_from_spatial(annotation)
            relationships.extend(enhanced)
        
        # Detect conflicts
        conflicts = []
        conflicts.extend(self.conflict_detector.detect_entity_conflicts(multimodal_entities, relationships))
        conflicts.extend(self.conflict_detector.detect_relationship_conflicts(relationships))
        
        # Calculate fusion quality
        fusion_quality = self._calculate_fusion_quality(
            text_entities, image_ids, relationships, conflicts
        )
        
        # Generate visualization code
        mermaid_code = self._generate_mermaid_code(multimodal_entities, relationships)
        d3_json = self._generate_d3_json(multimodal_entities, relationships)
        
        logger.info(f"Fusion complete: {len(multimodal_entities)} entities, {len(relationships)} relationships, {len(conflicts)} conflicts")
        
        return MultimodalFusionResult(
            multimodal_entities=multimodal_entities,
            relationships=relationships,
            fusion_quality=fusion_quality,
            mermaid_code=mermaid_code,
            d3_json=d3_json
        )
    
    def fuse_all(self, text_kg_id: str) -> MultimodalFusionResult:
        """Fuse text KG with all available annotated images"""
        # Get all images with annotations
        annotated_images = self.session.query(Image).filter(
            Image.annotation_status.in_(['verified', 'corrected'])
        ).all()
        
        image_ids = [img.id for img in annotated_images]
        
        return self.fuse(text_kg_id, image_ids, mode='auto')
    
    def detect_conflicts(self, fusion_result: MultimodalFusionResult) -> List[Conflict]:
        """Detect conflicts in fusion result"""
        conflicts = []
        conflicts.extend(self.conflict_detector.detect_entity_conflicts(
            fusion_result.multimodal_entities,
            fusion_result.relationships
        ))
        conflicts.extend(self.conflict_detector.detect_relationship_conflicts(
            fusion_result.relationships
        ))
        return conflicts
    
    def resolve_conflict(
        self, 
        conflict_id: str, 
        resolution: str,
        action: str = 'keep_first'
    ) -> bool:
        """
        Resolve a detected conflict
        
        Args:
            conflict_id: ID of the conflict
            resolution: Resolution description
            action: 'keep_first', 'keep_second', 'merge', 'delete'
        
        Returns:
            True if resolved successfully
        """
        logger.info(f"Resolving conflict {conflict_id} with action {action}")
        # Implementation would modify entities/relationships based on action
        # For now, just log the resolution
        return True
    
    def _calculate_fusion_quality(
        self,
        text_entities: List[KGEntity],
        image_ids: List[str],
        relationships: List[Dict],
        conflicts: List[Conflict]
    ) -> Dict:
        """Calculate fusion quality metrics"""
        text_entity_ids = {e.id for e in text_entities}
        images_with_relations = {r['source'] for r in relationships if r.get('source_type') == 'text_to_image'}
        
        linked_images = len(images_with_relations)
        total_images = len(image_ids)
        
        text_with_images = len(images_with_relations & text_entity_ids)
        total_text = len(text_entity_ids)
        
        # Calculate coverage
        text_image_coverage = linked_images / total_images if total_images > 0 else 0.0
        orphan_images = total_images - linked_images
        
        # Count orphan text entities (text entities without any image link)
        text_with_any_link = set()
        for r in relationships:
            if r.get('source_type') in ['text_to_image', 'text']:
                text_with_any_link.add(r['source'])
            if r.get('source_type') in ['image_to_text', 'text']:
                text_with_any_link.add(r['target'])
        orphan_text_entities = total_text - len(text_with_any_link)
        
        return {
            'text_image_coverage': round(text_image_coverage, 3),
            'orphan_images': orphan_images,
            'orphan_text_entities': orphan_text_entities,
            'total_conflicts': len(conflicts),
            'resolved_conflicts': len([c for c in conflicts if c.resolved])
        }
    
    def _generate_mermaid_code(
        self, 
        entities: List[Dict], 
        relationships: List[Dict]
    ) -> str:
        """Generate Mermaid.js code for visualization"""
        lines = [
            "%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '14px'}}}%%",
            "flowchart TB"
        ]
        
        # Group entities by cluster or type
        text_entities = [e for e in entities if e.get('type') == 'text']
        image_entities = [e for e in entities if e.get('type') == 'image']
        
        # Create subgraphs
        if text_entities:
            lines.append('    subgraph text_entities["🟦 文本实体"]')
            for e in text_entities[:15]:  # Limit for readability
                lines.append(f'        TE_{e["id"].replace("-", "_")}["{e["name"]}"]')
            lines.append('    end')
        
        if image_entities:
            lines.append('    subgraph image_entities["🟧 图像实体"]')
            for e in image_entities[:15]:
                lines.append(f'        IE_{e["id"].replace("-", "_")}["📷 {e["name"]}"]')
            lines.append('    end')
        
        # Add relationships
        seen = set()
        for rel in relationships:
            source = rel['source'].replace('-', '_')
            target = rel['target'].replace('-', '_')
            rel_type = rel['type']
            confidence = rel.get('confidence', 1.0)
            
            # Determine direction
            if rel.get('source_type') == 'text_to_image' or (rel.get('source_type') in [None, 'text'] and source.startswith('E')):
                line = f'    {source} -->|"{rel_type} ({confidence:.2f})"| {target}'
            else:
                line = f'    {source} -->|"{rel_type} ({confidence:.2f})"| {target}'
            
            if line not in seen:
                seen.add(line)
                lines.append(line)
        
        # Add styles
        lines.append('')
        lines.append('    style TE fill:#e1f5ff,stroke:#01579b')
        lines.append('    style IE fill:#fff3e0,stroke:#e65100')
        
        return '\n'.join(lines)
    
    def _generate_d3_json(self, entities: List[Dict], relationships: List[Dict]) -> Dict:
        """Generate D3.js compatible JSON"""
        nodes = []
        for e in entities:
            node = {
                'id': e['id'],
                'name': e['name'],
                'group': e.get('type', 'unknown'),
                'cluster': e.get('cluster', ''),
                'confidence': e.get('confidence', 1.0)
            }
            if e.get('image_path'):
                node['image'] = e['image_path']
            nodes.append(node)
        
        links = []
        for rel in relationships:
            links.append({
                'source': rel['source'],
                'target': rel['target'],
                'type': rel['type'],
                'confidence': rel.get('confidence', 1.0)
            })
        
        return {
            'nodes': nodes,
            'links': links
        }


# Singleton instance
_fusion_engine = None

def get_fusion_engine() -> FusionEngine:
    """Get singleton fusion engine instance"""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = FusionEngine()
    return _fusion_engine
