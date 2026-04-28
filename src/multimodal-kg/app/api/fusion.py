# SPDX-License-Identifier: MIT
"""
Fusion API Routes for Multimodal Knowledge Graph System
Handles text-image fusion and conflict resolution
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from app.schemas.models import (
    MultimodalFusionRequest,
    MultimodalFusionResponse,
    MultimodalEntity,
    MultimodalRelationship,
    FusionQuality,
    StatusResponse
)
from app.services.fusion_engine import FusionEngine, Conflict

logger.add(lambda msg: print(msg))

router = APIRouter(prefix="", tags=["fusion"])

# In-memory storage (replace with database)
_fusion_results: dict = {}
_conflicts: dict = {}


@router.post("/fuse", response_model=MultimodalFusionResponse)
async def fuse_kg_with_images(
    request: MultimodalFusionRequest,
    background_tasks: BackgroundTasks = None
):
    """
    Fuse text knowledge graph with image annotations
    
    - **text_kg_id**: Text KG ID to fuse
    - **image_ids**: List of image IDs to incorporate
    """
    try:
        import uuid
        
        fusion_id = f"FUS_{uuid.uuid4().hex[:8].upper()}"
        
        # Use FusionEngine
        engine = FusionEngine()
        
        # In production, call actual fusion
        # result = engine.fuse(text_kg_id, image_ids)
        
        # Mock result for demo
        result = MultimodalFusionResponse(
            multimodal_entities=[],
            relationships=[],
            fusion_quality=FusionQuality(
                text_image_coverage=0.0,
                orphan_images=0,
                orphan_text_entities=0
            ),
            mermaid_code="graph TD\n  A[Text KG] --> B[Fusion]"
        )
        
        _fusion_results[fusion_id] = result
        
        logger.info(f"Completed fusion: {fusion_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in fusion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fuse-all", response_model=StatusResponse)
async def fuse_all_images(
    text_kg_id: str = Query(..., description="Text KG ID"),
    background_tasks: BackgroundTasks = None
):
    """
    Fuse text KG with all available images
    
    - **text_kg_id**: Text KG ID to fuse
    """
    try:
        import uuid
        
        # In production, get all image IDs from database
        # image_ids = get_all_image_ids()
        image_ids = []
        
        fusion_id = f"FUS_{uuid.uuid4().hex[:8].upper()}"
        
        # Process fusion in background
        logger.info(f"Starting fuse-all: KG={text_kg_id}, images={len(image_ids)}")
        
        return StatusResponse(
            success=True,
            message=f"Fusion task started: {fusion_id}",
            data={
                "fusion_id": fusion_id,
                "text_kg_id": text_kg_id,
                "image_count": len(image_ids),
                "status": "processing"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in fuse-all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fusion_id}/conflicts", response_model=List[dict])
async def get_fusion_conflicts(fusion_id: str):
    """
    Get detected conflicts for a fusion result
    
    - **fusion_id**: Fusion result identifier
    """
    try:
        # Get conflicts for fusion
        conflicts = _conflicts.get(fusion_id, [])
        
        return [
            {
                "conflict_id": c.conflict_id if isinstance(c, Conflict) else c.get("conflict_id"),
                "conflict_type": c.conflict_type if isinstance(c, Conflict) else c.get("conflict_type"),
                "description": c.description if isinstance(c, Conflict) else c.get("description"),
                "entities_involved": c.entities_involved if isinstance(c, Conflict) else c.get("entities_involved", []),
                "suggested_resolution": c.suggested_resolution if isinstance(c, Conflict) else c.get("suggested_resolution"),
                "resolved": c.resolved if isinstance(c, Conflict) else c.get("resolved", False)
            }
            for c in conflicts
        ]
        
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflicts/{conflict_id}/resolve", response_model=StatusResponse)
async def resolve_conflict(
    conflict_id: str,
    resolution: str = Query(..., description="Resolution method: merge, keep_first, keep_second, mark_alias"),
    entity_id_to_keep: Optional[str] = Query(None, description="Entity ID to keep if applicable")
):
    """
    Resolve a fusion conflict
    
    - **conflict_id**: Conflict identifier
    - **resolution**: Resolution method
    - **entity_id_to_keep**: Optional entity ID to keep
    """
    try:
        # Find and resolve conflict
        resolved = False
        for fusion_id, conflicts in _conflicts.items():
            for i, conflict in enumerate(conflicts):
                conflict_obj = conflict if isinstance(conflict, Conflict) else None
                if conflict_obj and conflict_obj.conflict_id == conflict_id:
                    conflict_obj.resolved = True
                    resolved = True
                    logger.info(f"Resolved conflict: {conflict_id} with method: {resolution}")
                    break
        
        if not resolved:
            raise HTTPException(
                status_code=404,
                detail=f"Conflict not found: {conflict_id}"
            )
        
        return StatusResponse(
            success=True,
            message=f"Conflict {conflict_id} resolved using: {resolution}",
            data={
                "conflict_id": conflict_id,
                "resolution": resolution,
                "entity_id_to_keep": entity_id_to_keep
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fusion_id}/quality", response_model=FusionQuality)
async def get_fusion_quality(fusion_id: str):
    """
    Get fusion quality metrics for a result
    
    - **fusion_id**: Fusion result identifier
    """
    try:
        result = _fusion_results.get(fusion_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Fusion result not found: {fusion_id}"
            )
        
        return result.fusion_quality
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fusion quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))
