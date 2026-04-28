# SPDX-License-Identifier: MIT
"""
M2 Image Annotation Engine for Multimodal Knowledge Graph System

Provides AI-assisted image annotation with:
- Scene classification
- Object detection (YOLO or vision model fallback)
- OCR processing (PaddleOCR/EasyOCR)
- Relationship extraction
- Norm reference linking
"""

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.config import settings
from app.schemas.models import (
    DetectedObject as SchemaDetectedObject,
    ObjectRelationship as SchemaObjectRelationship,
    AnnotationStatus,
    ImageType,
)
from app.models.database import Image, ImageAnnotation, SyncSessionLocal


# ============== Dataclasses ==============

@dataclass
class AnnotationResult:
    """Complete annotation result"""
    id: str
    image_id: str
    annotator_type: str
    confidence: float
    status: str
    feedback_count: int
    created_at: datetime
    updated_at: datetime
    
    # Scene info
    scene_type: Optional[str] = None
    scene_confidence: float = 0.0
    
    # Detected objects
    objects: List[Dict[str, Any]] = field(default_factory=list)
    
    # Relationships
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    
    # OCR
    ocr_text: Optional[str] = None
    ocr_regions: Optional[List[Dict]] = None
    
    # Norm reference
    norm_standard: Optional[str] = None
    norm_clause: Optional[str] = None
    norm_description: Optional[str] = None
    
    # Tags
    tags: List[str] = field(default_factory=list)
    
    # Verification
    verified_by: Optional[str] = None
    correction_note: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_db_model(cls, model: ImageAnnotation) -> 'AnnotationResult':
        """Create from database model"""
        return cls(
            id=model.id,
            image_id=model.image_id,
            annotator_type=model.annotator_type,
            confidence=model.confidence,
            status=model.status,
            feedback_count=model.feedback_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
            scene_type=model.scene_type,
            scene_confidence=model.scene_confidence or 0.0,
            objects=model.objects or [],
            relationships=model.relationships or [],
            ocr_text=model.ocr_text,
            ocr_regions=model.ocr_regions,
            norm_standard=model.norm_standard,
            norm_clause=model.norm_clause,
            norm_description=model.norm_description,
            tags=model.tags or [],
            verified_by=model.annotator_id if model.annotator_type == 'human' else None,
            correction_note=model.correction_note,
        )


@dataclass
class DetectedObject:
    """Detected object in image"""
    type: str
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_schema(self, obj_id: str) -> SchemaDetectedObject:
        return SchemaDetectedObject(
            id=obj_id,
            type=self.type,
            bbox=self.bbox,
            confidence=self.confidence,
            attributes=self.attributes,
        )


@dataclass
class ObjectRelationship:
    """Relationship between detected objects"""
    source: str
    target: str
    relation_type: str
    spatial: Optional[str] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_schema(self) -> SchemaObjectRelationship:
        return SchemaObjectRelationship(
            source=self.source,
            target=self.target,
            relation_type=self.relation_type,
            spatial=self.spatial,
            confidence=self.confidence,
        )


@dataclass
class NormReference:
    """Norm/standard reference"""
    standard: str
    clause: str
    description: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass  
class OCRResult:
    """OCR processing result"""
    full_text: str
    regions: List[Dict[str, Any]]  # [{text, bbox, confidence}]
    
    def to_tuple(self) -> Tuple[str, List[Dict]]:
        return (self.full_text, self.regions)


# ============== Vision Model Client ==============

class VisionModelClient:
    """Client for vision model (GPT-4o or similar)"""
    
    def __init__(self):
        self.model = settings.vision_model
        self.api_key = settings.llm_api_key
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the vision model client"""
        try:
            if settings.llm_provider == "openai":
                from openai import OpenAI
                # Handle missing API key gracefully
                api_key = self.api_key or "dummy-key-for-init"
                try:
                    self._client = OpenAI(api_key=api_key)
                except Exception as e:
                    if "api_key" in str(e).lower():
                        logger.warning("OpenAI API key not configured, vision features disabled")
                        self._client = None
                    else:
                        raise
            elif settings.llm_provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            else:
                logger.warning(f"Unknown LLM provider: {settings.llm_provider}")
        except ImportError as e:
            logger.warning(f"Could not import LLM client: {e}")
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using vision model"""
        if self._client is None:
            logger.error("Vision model client not initialized")
            return {"error": "Client not initialized"}
        
        try:
            with open(image_path, "rb") as f:
                import base64
                image_data = base64.b64encode(f.read()).decode()
            
            if settings.llm_provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2048,
                )
                return {"content": response.choices[0].message.content}
            
            elif settings.llm_provider == "anthropic":
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data
                                    }
                                }
                            ]
                        }
                    ]
                )
                return {"content": response.content[0].text}
                
        except Exception as e:
            logger.error(f"Vision model error: {e}")
            return {"error": str(e)}


# ============== Scene Classifier ==============

class SceneClassifier:
    """Classify image scene type"""
    
    SCENE_CATEGORIES = ["facility", "floor_plan", "scene", "standard", "sign"]
    
    SYSTEM_PROMPT = """You are an expert image classifier for building safety inspection images.
    Classify the image into one of these categories:
    - facility: Fire safety equipment (fire extinguishers, hydrants, alarms, etc.)
    - floor_plan: Architectural/building floor plans with rooms, corridors, exits
    - scene: General scene photos (indoor/outdoor, environmental shots)
    - standard: Standards/specifications illustrations or diagrams
    - sign: Warning signs, prohibition signs, information signs
    
    Respond with JSON format:
    {
        "category": "one of the above categories",
        "confidence": 0.0-1.0,
        "reasoning": "brief explanation"
    }"""
    
    def __init__(self):
        self.vision_client = VisionModelClient()
        self.fallback_enabled = True
    
    def classify(self, image_path: str) -> Tuple[str, float]:
        """
        Classify image scene type
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (scene_type, confidence)
        """
        try:
            logger.info(f"Classifying scene for: {image_path}")
            
            # Use vision model for classification
            result = self.vision_client.analyze_image(
                image_path,
                self.SYSTEM_PROMPT
            )
            
            if "error" in result:
                logger.warning(f"Vision model error, using fallback: {result['error']}")
                return self._fallback_classify(image_path)
            
            # Parse result
            import json
            content = result.get("content", "")
            
            # Extract JSON from response
            try:
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                parsed = json.loads(content.strip())
                category = parsed.get("category", "unknown")
                confidence = float(parsed.get("confidence", 0.5))
                
                # Validate category
                if category not in self.SCENE_CATEGORIES:
                    category = "unknown"
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse vision response: {e}")
                return self._fallback_classify(image_path)
            
            logger.info(f"Scene classified as '{category}' with confidence {confidence}")
            return (category, confidence)
            
        except Exception as e:
            logger.error(f"Scene classification error: {e}")
            return ("unknown", 0.0)
    
    def _fallback_classify(self, image_path: str) -> Tuple[str, float]:
        """Fallback classification based on image properties"""
        try:
            from PIL import Image as PILImage
            img = PILImage.open(image_path)
            w, h = img.size
            
            # Simple heuristic based on aspect ratio
            aspect_ratio = w / h if h > 0 else 1.0
            
            if 1.2 < aspect_ratio < 2.0:
                return ("floor_plan", 0.6)
            elif aspect_ratio > 2.5:
                return ("sign", 0.5)
            else:
                return ("scene", 0.5)
                
        except Exception as e:
            logger.warning(f"Fallback classification failed: {e}")
            return ("unknown", 0.3)


# ============== Object Detector ==============

class ObjectDetector:
    """Detect objects in images using YOLO or vision model"""
    
    def __init__(self):
        self.enabled = settings.detection_enabled
        self.model_name = settings.detection_model
        self._yolo_model = None
        self.vision_client = VisionModelClient()
        self._initialize_yolo()
    
    def _initialize_yolo(self):
        """Initialize YOLO model if available"""
        if not self.enabled:
            return
            
        try:
            from ultralytics import YOLO
            self._yolo_model = YOLO(self.model_name)
            logger.info(f"Loaded YOLO model: {self.model_name}")
        except ImportError:
            logger.warning("Ultralytics YOLO not available, using vision fallback")
            self._yolo_model = None
        except Exception as e:
            logger.warning(f"Failed to load YOLO: {e}")
            self._yolo_model = None
    
    def detect(self, image_path: str) -> List[DetectedObject]:
        """
        Detect objects in image
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of DetectedObject
        """
        try:
            logger.info(f"Detecting objects in: {image_path}")
            
            if self._yolo_model is not None:
                return self._detect_with_yolo(image_path)
            else:
                return self._detect_with_vision(image_path)
                
        except Exception as e:
            logger.error(f"Object detection error: {e}")
            return []
    
    def _detect_with_yolo(self, image_path: str) -> List[DetectedObject]:
        """Detect using YOLO model"""
        try:
            results = self._yolo_model(image_path, verbose=False)
            
            objects = []
            for i, result in enumerate(results):
                boxes = result.boxes
                if boxes is None:
                    continue
                    
                for box in boxes:
                    obj = DetectedObject(
                        type=result.names[int(box.cls.item())],
                        bbox=[int(x) for x in box.xyxy[0].tolist()],
                        confidence=float(box.conf.item()),
                        attributes={
                            "class_id": int(box.cls.item()),
                            "yolo_confidence": float(box.conf.item()),
                        }
                    )
                    objects.append(obj)
            
            logger.info(f"YOLO detected {len(objects)} objects")
            return objects
            
        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            return self._detect_with_vision(image_path)
    
    def _detect_with_vision(self, image_path: str) -> List[DetectedObject]:
        """Fallback detection using vision model"""
        prompt = """Analyze this image and identify all objects of interest.
        For each object, provide:
        - type: what the object is (e.g., fire_extinguisher, door, sign, hydrant)
        - bbox: bounding box coordinates [x1, y1, x2, y2] as percentages (0-100)
        - confidence: confidence score (0-1)
        
        Respond in JSON format:
        {
            "objects": [
                {"type": "object_type", "bbox": [x1, y1, x2, y2], "confidence": 0.9}
            ]
        }
        
        Focus on safety-related objects like:
        - Fire extinguishers, hydrants, alarms
        - Doors, exits, windows
        - Signs (warning, prohibition, information)
        - Safety equipment"""
        
        result = self.vision_client.analyze_image(image_path, prompt)
        
        if "error" in result:
            logger.warning(f"Vision detection failed: {result['error']}")
            return []
        
        try:
            import json
            content = result.get("content", "")
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            parsed = json.loads(content.strip())
            raw_objects = parsed.get("objects", [])
            
            # Convert to DetectedObject, converting percentage bboxes to pixels
            from PIL import Image as PILImage
            try:
                img = PILImage.open(image_path)
                w, h = img.size
                
                objects = []
                for obj in raw_objects:
                    bbox = obj.get("bbox", [0, 0, 0, 0])
                    # Convert from percentage to pixels
                    pixel_bbox = [
                        int(bbox[0] * w / 100),
                        int(bbox[1] * h / 100),
                        int(bbox[2] * w / 100),
                        int(bbox[3] * h / 100),
                    ]
                    objects.append(DetectedObject(
                        type=obj.get("type", "unknown"),
                        bbox=pixel_bbox,
                        confidence=float(obj.get("confidence", 0.5)),
                        attributes={"source": "vision_model"}
                    ))
                return objects
                
            except Exception as img_error:
                logger.warning(f"Could not get image dimensions: {img_error}")
                return []
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse vision detection: {e}")
            return []


# ============== OCR Processor ==============

class OCRProcessor:
    """Extract text from images using PaddleOCR or EasyOCR"""
    
    def __init__(self):
        self.enabled = settings.ocr_enabled
        self.engine = settings.ocr_engine
        self._ocr_engine = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize OCR engine"""
        if not self.enabled:
            return
        
        try:
            if self.engine == "paddleocr":
                from paddleocr import PaddleOCR
                self._ocr_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang='chinese',
                    use_gpu=False,
                    show_log=False,
                )
                logger.info("Initialized PaddleOCR")
            elif self.engine == "easyocr":
                import easyocr
                self._ocr_engine = easyocr.Reader(
                    ['ch_sim', 'en'],
                    gpu=False,
                    verbose=False,
                )
                logger.info("Initialized EasyOCR")
        except ImportError as e:
            logger.warning(f"OCR engine not available: {e}")
            self._ocr_engine = None
    
    def extract_text(self, image_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (full_text, regions)
            regions: List of dicts with {text, bbox, confidence}
        """
        if not self.enabled or self._ocr_engine is None:
            logger.info("OCR disabled or engine not available")
            return ("", [])
        
        try:
            logger.info(f"Extracting text from: {image_path}")
            
            if self.engine == "paddleocr":
                return self._extract_paddleocr(image_path)
            elif self.engine == "easyocr":
                return self._extract_easyocr(image_path)
            else:
                return ("", [])
                
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return ("", [])
    
    def _extract_paddleocr(self, image_path: str) -> Tuple[str, List[Dict]]:
        """Extract using PaddleOCR"""
        try:
            result = self._ocr_engine.ocr(image_path, cls=True)
            
            if not result or not result[0]:
                return ("", [])
            
            regions = []
            text_parts = []
            
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = float(line[1][1])
                
                # Convert bbox to [x1, y1, x2, y2]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                pixel_bbox = [
                    int(min(x_coords)),
                    int(min(y_coords)),
                    int(max(x_coords)),
                    int(max(y_coords)),
                ]
                
                regions.append({
                    "text": text,
                    "bbox": pixel_bbox,
                    "confidence": confidence,
                })
                text_parts.append(text)
            
            full_text = " ".join(text_parts)
            logger.info(f"PaddleOCR extracted {len(regions)} text regions")
            return (full_text, regions)
            
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            return ("", [])
    
    def _extract_easyocr(self, image_path: str) -> Tuple[str, List[Dict]]:
        """Extract using EasyOCR"""
        try:
            results = self._ocr_engine.readtext(image_path)
            
            regions = []
            text_parts = []
            
            for bbox, text, confidence in results:
                # Convert corners to [x1, y1, x2, y2]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                pixel_bbox = [
                    int(min(x_coords)),
                    int(min(y_coords)),
                    int(max(x_coords)),
                    int(max(y_coords)),
                ]
                
                regions.append({
                    "text": text,
                    "bbox": pixel_bbox,
                    "confidence": confidence,
                })
                text_parts.append(text)
            
            full_text = " ".join(text_parts)
            logger.info(f"EasyOCR extracted {len(regions)} text regions")
            return (full_text, regions)
            
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            return ("", [])


# ============== Relationship Extractor ==============

class RelationshipExtractor:
    """Extract spatial and semantic relationships between objects"""
    
    def __init__(self):
        self.vision_client = VisionModelClient()
    
    def extract_relations(
        self, 
        image_path: str, 
        objects: List[DetectedObject]
    ) -> List[ObjectRelationship]:
        """
        Extract relationships between detected objects
        
        Args:
            image_path: Path to image
            objects: List of detected objects
            
        Returns:
            List of ObjectRelationship
        """
        try:
            logger.info(f"Extracting relationships for {len(objects)} objects")
            
            if len(objects) < 2:
                return []
            
            # Use vision model for relationship analysis
            return self._extract_with_vision(image_path, objects)
            
        except Exception as e:
            logger.error(f"Relationship extraction error: {e}")
            return []
    
    def _extract_with_vision(
        self, 
        image_path: str, 
        objects: List[DetectedObject]
    ) -> List[ObjectRelationship]:
        """Extract relationships using vision model"""
        
        # Build object description for prompt
        obj_descriptions = []
        for i, obj in enumerate(objects):
            obj_descriptions.append(
                f"Object {i}: {obj.type} at bbox {obj.bbox}"
            )
        
        prompt = f"""Analyze the spatial and semantic relationships between objects in this image.
        
Objects detected:
{chr(10).join(obj_descriptions)}

Identify relationships between pairs of objects. Consider:
- Spatial relationships: left_of, right_of, above, below, inside, adjacent_to, near
- Semantic relationships: part_of, connected_to, same_group, similar_type

Respond in JSON format:
{{
    "relationships": [
        {{
            "source": 0,
            "target": 1,
            "relation_type": "spatial or semantic relationship",
            "spatial": "spatial description if applicable",
            "confidence": 0.9
        }}
    ]
}}"""
        
        result = self.vision_client.analyze_image(image_path, prompt)
        
        if "error" in result:
            logger.warning(f"Vision relationship extraction failed: {result['error']}")
            return self._extract_spatial_relations(objects)
        
        try:
            import json
            content = result.get("content", "")
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            parsed = json.loads(content.strip())
            raw_relations = parsed.get("relationships", [])
            
            relationships = []
            for rel in raw_relations:
                src_idx = rel.get("source", -1)
                tgt_idx = rel.get("target", -1)
                
                if 0 <= src_idx < len(objects) and 0 <= tgt_idx < len(objects):
                    relationships.append(ObjectRelationship(
                        source=objects[src_idx].type,
                        target=objects[tgt_idx].type,
                        relation_type=rel.get("relation_type", "related"),
                        spatial=rel.get("spatial"),
                        confidence=float(rel.get("confidence", 0.5)),
                    ))
            
            logger.info(f"Extracted {len(relationships)} relationships")
            return relationships
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse vision response: {e}")
            return self._extract_spatial_relations(objects)
    
    def _extract_spatial_relations(
        self, 
        objects: List[DetectedObject]
    ) -> List[ObjectRelationship]:
        """Extract basic spatial relationships from bounding boxes"""
        relationships = []
        
        for i, obj1 in enumerate(objects):
            for j, obj2 in enumerate(objects):
                if i >= j:
                    continue
                
                # Calculate spatial relationship
                bbox1 = obj1.bbox
                bbox2 = obj2.bbox
                
                # Center points
                cx1 = (bbox1[0] + bbox1[2]) / 2
                cy1 = (bbox1[1] + bbox1[3]) / 2
                cx2 = (bbox2[0] + bbox2[2]) / 2
                cy2 = (bbox2[1] + bbox2[3]) / 2
                
                # Determine relationship
                dx = cx2 - cx1
                dy = cy2 - cy1
                
                spatial = None
                relation_type = "near"
                
                # Check if bboxes overlap significantly
                overlap_x = min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0])
                overlap_y = min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1])
                
                if overlap_x > 0 and overlap_y > 0:
                    # Bboxes overlap - might be inside/contains
                    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
                    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
                    
                    if overlap_x * overlap_y > 0.5 * min(area1, area2):
                        relation_type = "overlaps"
                        if area1 > area2:
                            spatial = f"{obj1.type} contains {obj2.type}"
                        else:
                            spatial = f"{obj2.type} contains {obj1.type}"
                else:
                    # Non-overlapping
                    if abs(dx) > abs(dy):
                        if dx > 0:
                            relation_type = "right_of"
                            spatial = f"{obj1.type} is left of {obj2.type}"
                        else:
                            relation_type = "left_of"
                            spatial = f"{obj1.type} is right of {obj2.type}"
                    else:
                        if dy > 0:
                            relation_type = "below"
                            spatial = f"{obj1.type} is above {obj2.type}"
                        else:
                            relation_type = "above"
                            spatial = f"{obj1.type} is below {obj2.type}"
                
                relationships.append(ObjectRelationship(
                    source=obj1.type,
                    target=obj2.type,
                    relation_type=relation_type,
                    spatial=spatial,
                    confidence=0.7,
                ))
        
        return relationships


# ============== Norm Reference Linker ==============

class NormReferenceLinker:
    """Link annotations to standard/regulatory references"""
    
    # Common safety standards mapping
    STANDARD_PATTERNS = {
        "fire_extinguisher": {
            "standard": "GB 4351",
            "clause": "5.1",
            "description": "手提式灭火器"
        },
        "fire_hydrant": {
            "standard": "GB 3446",
            "clause": "5.2", 
            "description": "消防水泵接合器"
        },
        "emergency_exit": {
            "standard": "GB 50016",
            "clause": "7.4",
            "description": "安全疏散"
        },
        "fire_alarm": {
            "standard": "GB 50116",
            "clause": "3.1",
            "description": "火灾自动报警系统"
        },
        "sign": {
            "standard": "GB 2894",
            "clause": "4.1",
            "description": "安全标志"
        },
        "fire_door": {
            "standard": "GB 12955",
            "clause": "5.1",
            "description": "防火门"
        },
        "smoke_detector": {
            "standard": "GB 20517",
            "clause": "5.1",
            "description": "独立式感烟火灾探测报警器"
        },
    }
    
    def __init__(self):
        self.vision_client = VisionModelClient()
    
    def link_to_standard(
        self, 
        annotation: AnnotationResult, 
        kg_context: Optional[Dict] = None
    ) -> Optional[NormReference]:
        """
        Link annotation to relevant standard clauses
        
        Args:
            annotation: The annotation result
            kg_context: Optional knowledge graph context for semantic matching
            
        Returns:
            NormReference if matched, None otherwise
        """
        try:
            logger.info(f"Linking annotation {annotation.id} to standards")
            
            # Find best matching standard based on detected objects
            matched_standards = []
            
            for obj in annotation.objects:
                obj_type = obj.get("type", "").lower()
                
                # Check direct matches
                for key, ref in self.STANDARD_PATTERNS.items():
                    if key in obj_type or obj_type in key:
                        matched_standards.append(ref)
            
            if matched_standards:
                # Return the most common standard
                from collections import Counter
                counts = Counter([
                    (r["standard"], r["clause"], r["description"]) 
                    for r in matched_standards
                ])
                most_common = counts.most_common(1)[0][0]
                
                return NormReference(
                    standard=most_common[0],
                    clause=most_common[1],
                    description=most_common[2],
                    confidence=0.8,
                )
            
            # Try vision model for semantic linking
            if annotation.objects and self._has_vision_client():
                return self._link_with_vision(annotation)
            
            return None
            
        except Exception as e:
            logger.error(f"Norm reference linking error: {e}")
            return None
    
    def _has_vision_client(self) -> bool:
        """Check if vision client is available"""
        try:
            return self.vision_client._client is not None
        except:
            return False
    
    def _link_with_vision(self, annotation: AnnotationResult) -> Optional[NormReference]:
        """Use vision model for semantic standard matching"""
        
        obj_types = [obj.get("type", "") for obj in annotation.objects[:5]]
        ocr_text = annotation.ocr_text or ""
        
        prompt = f"""Based on the detected objects and OCR text, identify the relevant Chinese safety standard.
        
Detected objects: {", ".join(obj_types)}
OCR text: {ocr_text[:200]}

Common safety standards include:
- GB 4351: 手提式灭火器 (Portable Fire Extinguisher)
- GB 3446: 消防水泵接合器 (Fire Pump Adapter)
- GB 50016: 建筑设计防火规范 (Fire Prevention Code)
- GB 50116: 火灾自动报警系统设计规范
- GB 2894: 安全标志 (Safety Signs)
- GB 12955: 防火门 (Fire Door)
- GB 20517: 独立式感烟火灾探测报警器

Respond in JSON format:
{{
    "standard": "standard code like GB XXXX",
    "clause": "relevant clause like X.X",
    "description": "brief description",
    "confidence": 0.0-1.0
}}"""
        
        # This requires the image, which we don't have in annotation
        # In practice, would need to pass image_path
        logger.info("Vision-based linking requires image_path, skipping")
        return None


# ============== Main Annotation Engine ==============

class AnnotationEngine:
    """
    Main annotation engine coordinating all annotation components
    """
    
    def __init__(self):
        """Initialize annotation engine with all components"""
        self.settings = settings
        
        # Initialize components
        self.scene_classifier = SceneClassifier()
        self.object_detector = ObjectDetector()
        self.ocr_processor = OCRProcessor()
        self.relationship_extractor = RelationshipExtractor()
        self.norm_linker = NormReferenceLinker()
        
        # Cache for in-progress annotations
        self._annotation_cache: Dict[str, AnnotationResult] = {}
        
        logger.info("AnnotationEngine initialized")
    
    def annotate(
        self, 
        image_id: str, 
        mode: str = "ai_assisted"
    ) -> AnnotationResult:
        """
        Annotate a single image
        
        Args:
            image_id: ID of the image to annotate
            mode: Annotation mode ('ai_assisted', 'manual', 'batch')
            
        Returns:
            AnnotationResult
        """
        try:
            logger.info(f"Annotating image {image_id} with mode={mode}")
            
            # Get image from database
            session = SyncSessionLocal()
            try:
                image = session.query(Image).filter(Image.id == image_id).first()
                
                if not image:
                    raise ValueError(f"Image not found: {image_id}")
                
                image_path = image.storage_path
                
                if not Path(image_path).exists():
                    raise FileNotFoundError(f"Image file not found: {image_path}")
                
                # Perform annotation steps
                annotation = self._perform_annotation(image_id, image_path, mode)
                
                # Save to database
                db_annotation = self._save_annotation(annotation)
                
                # Update image status
                image.annotation_status = annotation.status
                image.image_type = annotation.scene_type
                image.annotation_count += 1
                
                session.commit()
                
                # Return result
                result = AnnotationResult.from_db_model(db_annotation)
                self._annotation_cache[image_id] = result
                
                return result
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Annotation error for {image_id}: {e}")
            raise
    
    def annotate_batch(
        self, 
        image_ids: List[str], 
        mode: str = "ai_assisted"
    ) -> List[AnnotationResult]:
        """
        Annotate multiple images
        
        Args:
            image_ids: List of image IDs to annotate
            mode: Annotation mode
            
        Returns:
            List of AnnotationResults
        """
        results = []
        
        for image_id in image_ids:
            try:
                result = self.annotate(image_id, mode)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch annotation error for {image_id}: {e}")
                # Continue with other images
                results.append(AnnotationResult(
                    id="",
                    image_id=image_id,
                    annotator_type="error",
                    confidence=0.0,
                    status="failed",
                    feedback_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ))
        
        return results
    
    def verify_annotation(
        self, 
        annotation_id: str, 
        verifier_id: str
    ) -> AnnotationResult:
        """
        Verify an annotation
        
        Args:
            annotation_id: ID of annotation to verify
            verifier_id: ID of verifier
            
        Returns:
            Updated AnnotationResult
        """
        try:
            logger.info(f"Verifying annotation {annotation_id} by {verifier_id}")
            
            session = SyncSessionLocal()
            try:
                annotation = session.query(ImageAnnotation).filter(
                    ImageAnnotation.id == annotation_id
                ).first()
                
                if not annotation:
                    raise ValueError(f"Annotation not found: {annotation_id}")
                
                # Update verification status
                annotation.status = AnnotationStatus.VERIFIED.value
                annotation.annotator_type = "human"
                annotation.annotator_id = verifier_id
                
                session.commit()
                
                return AnnotationResult.from_db_model(annotation)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            raise
    
    def correct_annotation(
        self, 
        annotation_id: str, 
        corrections: Dict[str, Any],
        user_id: str
    ) -> AnnotationResult:
        """
        Apply corrections to an annotation
        
        Args:
            annotation_id: ID of annotation to correct
            corrections: Dictionary of corrections
            user_id: ID of user making corrections
            
        Returns:
            Updated AnnotationResult
        """
        try:
            logger.info(f"Correcting annotation {annotation_id} by {user_id}")
            
            session = SyncSessionLocal()
            try:
                annotation = session.query(ImageAnnotation).filter(
                    ImageAnnotation.id == annotation_id
                ).first()
                
                if not annotation:
                    raise ValueError(f"Annotation not found: {annotation_id}")
                
                # Apply corrections
                if "scene_type" in corrections:
                    annotation.scene_type = corrections["scene_type"]
                if "objects" in corrections:
                    annotation.objects = corrections["objects"]
                if "relationships" in corrections:
                    annotation.relationships = corrections["relationships"]
                if "ocr_text" in corrections:
                    annotation.ocr_text = corrections["ocr_text"]
                if "tags" in corrections:
                    annotation.tags = corrections["tags"]
                if "confidence" in corrections:
                    annotation.confidence = corrections["confidence"]
                
                # Update status
                annotation.status = AnnotationStatus.CORRECTED.value
                annotation.annotator_type = "human"
                annotation.annotator_id = user_id
                annotation.correction_note = corrections.get("note", "")
                
                session.commit()
                
                return AnnotationResult.from_db_model(annotation)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Correction error: {e}")
            raise
    
    def get_annotation(self, image_id: str) -> AnnotationResult:
        """
        Get annotation for an image
        
        Args:
            image_id: ID of image
            
        Returns:
            AnnotationResult or raises error if not found
        """
        # Check cache
        if image_id in self._annotation_cache:
            return self._annotation_cache[image_id]
        
        session = SyncSessionLocal()
        try:
            annotation = session.query(ImageAnnotation).filter(
                ImageAnnotation.image_id == image_id
            ).order_by(ImageAnnotation.created_at.desc()).first()
            
            if not annotation:
                raise ValueError(f"No annotation found for image: {image_id}")
            
            result = AnnotationResult.from_db_model(annotation)
            self._annotation_cache[image_id] = result
            
            return result
            
        finally:
            session.close()
    
    def _perform_annotation(
        self, 
        image_id: str, 
        image_path: str, 
        mode: str
    ) -> AnnotationResult:
        """Perform the actual annotation process"""
        
        # Generate annotation ID
        ann_id = f"ANN_{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()
        
        # Step 1: Scene Classification
        scene_type, scene_confidence = self.scene_classifier.classify(image_path)
        
        # Step 2: Object Detection
        objects = self.object_detector.detect(image_path)
        
        # Step 3: OCR
        ocr_text, ocr_regions = self.ocr_processor.extract_text(image_path)
        
        # Step 4: Relationship Extraction
        relationships = self.relationship_extractor.extract_relations(
            image_path, objects
        )
        
        # Calculate overall confidence
        confidences = [scene_confidence]
        confidences.extend([obj.confidence for obj in objects])
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Create preliminary annotation
        preliminary = AnnotationResult(
            id=ann_id,
            image_id=image_id,
            annotator_type="AI",
            confidence=overall_confidence,
            status=AnnotationStatus.AI_ASSISTED.value,
            feedback_count=0,
            created_at=now,
            updated_at=now,
            scene_type=scene_type,
            scene_confidence=scene_confidence,
            objects=[obj.to_dict() for obj in objects],
            relationships=[rel.to_dict() for rel in relationships],
            ocr_text=ocr_text if ocr_text else None,
            ocr_regions=ocr_regions if ocr_regions else None,
        )
        
        # Step 5: Norm Reference Linking
        norm_ref = self.norm_linker.link_to_standard(preliminary)
        if norm_ref:
            preliminary.norm_standard = norm_ref.standard
            preliminary.norm_clause = norm_ref.clause
            preliminary.norm_description = norm_ref.description
        
        # Add tags based on scene type and objects
        preliminary.tags = self._generate_tags(scene_type, objects, ocr_text)
        
        # Adjust confidence based on OCR availability
        if ocr_text:
            preliminary.confidence = min(overall_confidence * 1.1, 1.0)
        
        return preliminary
    
    def _save_annotation(self, annotation: AnnotationResult) -> ImageAnnotation:
        """Save annotation to database"""
        session = SyncSessionLocal()
        try:
            db_annotation = ImageAnnotation(
                id=annotation.id,
                image_id=annotation.image_id,
                annotator_type=annotation.annotator_type,
                annotator_id=None,
                scene_type=annotation.scene_type,
                scene_confidence=annotation.scene_confidence,
                objects=annotation.objects,
                relationships=annotation.relationships,
                ocr_text=annotation.ocr_text,
                ocr_regions=annotation.ocr_regions,
                norm_standard=annotation.norm_standard,
                norm_clause=annotation.norm_clause,
                norm_description=annotation.norm_description,
                tags=annotation.tags,
                confidence=annotation.confidence,
                status=annotation.status,
                feedback_count=0,
            )
            
            session.add(db_annotation)
            session.commit()
            session.refresh(db_annotation)
            
            return db_annotation
            
        finally:
            session.close()
    
    def _generate_tags(
        self, 
        scene_type: str, 
        objects: List[DetectedObject], 
        ocr_text: str
    ) -> List[str]:
        """Generate tags based on annotation content"""
        tags = [scene_type] if scene_type else []
        
        # Add object types as tags
        obj_types = set()
        for obj in objects:
            obj_type = obj.type.lower()
            # Simplify common types
            if "fire" in obj_type:
                obj_types.add("fire_safety")
            if "exit" in obj_type or "door" in obj_type:
                obj_types.add("egress")
            if "sign" in obj_type:
                obj_types.add("signage")
            if "alarm" in obj_type or "detector" in obj_type:
                obj_types.add("detection_system")
            if "hydrant" in obj_type or "extinguisher" in obj_type:
                obj_types.add("equipment")
        
        tags.extend(list(obj_types))
        
        # Add OCR-based tags
        if ocr_text:
            ocr_lower = ocr_text.lower()
            if any(kw in ocr_lower for kw in ["禁止", "禁止", "no"]):
                tags.append("prohibition")
            if any(kw in ocr_lower for kw in ["注意", "warning", "warning"]):
                tags.append("warning")
            if any(kw in ocr_lower for kw in ["安全", "safety"]):
                tags.append("safety_related")
        
        return list(set(tags))[:10]  # Limit to 10 tags


# Singleton instance
_annotation_engine: Optional[AnnotationEngine] = None


def get_annotation_engine() -> AnnotationEngine:
    """Get singleton annotation engine instance"""
    global _annotation_engine
    if _annotation_engine is None:
        _annotation_engine = AnnotationEngine()
    return _annotation_engine
