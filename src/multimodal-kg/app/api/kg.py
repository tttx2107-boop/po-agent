# SPDX-License-Identifier: MIT
"""
Knowledge Graph API Routes for Multimodal Knowledge Graph System
Handles KG generation, retrieval, and entity/relationship queries
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from app.schemas.models import (
    KnowledgeGraphCreate,
    KnowledgeGraphResponse,
    KGEntityCreate,
    KGEntityResponse,
    KGRelationshipCreate,
    KGRelationshipResponse,
    EntityType,
    GraphType
)

logger.add(lambda msg: print(msg))

router = APIRouter(prefix="", tags=["knowledge-graph"])

# In-memory storage (replace with database)
_kg_store: dict = {}
_entity_store: dict = {}
_relationship_store: dict = {}


@router.post("/generate", response_model=KnowledgeGraphResponse)
async def generate_knowledge_graph(
    request: KnowledgeGraphCreate,
    text_content: str = Query(..., description="Text content to extract KG from")
):
    """
    Generate a knowledge graph from text content
    
    - **name**: KG name
    - **description**: Optional description
    - **graph_type**: Type of graph (text, image, multimodal)
    - **text_content**: Text content to process
    """
    try:
        import uuid
        
        kg_id = f"KG_{uuid.uuid4().hex[:8].upper()}"
        
        # In production, use actual NLP/KG extraction
        # For now, create empty KG with metadata
        kg = KnowledgeGraphResponse(
            id=kg_id,
            name=request.name,
            description=request.description,
            graph_type=request.graph_type,
            entity_count=0,
            relationship_count=0,
            source_documents=["extracted_from_text"],
            visualization_format="mermaid",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        _kg_store[kg_id] = kg
        
        logger.info(f"Generated knowledge graph: {kg_id}")
        
        return kg
        
    except Exception as e:
        logger.error(f"Error generating KG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kg_id}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(kg_id: str):
    """
    Get knowledge graph details
    
    - **kg_id**: Knowledge graph identifier
    """
    try:
        kg = _kg_store.get(kg_id)
        
        if not kg:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge graph not found: {kg_id}"
            )
        
        return kg
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting KG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kg_id}/entities", response_model=List[KGEntityResponse])
async def list_entities(
    kg_id: str,
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    List entities in a knowledge graph
    
    - **kg_id**: Knowledge graph identifier
    - **entity_type**: Optional filter by entity type
    - **page**: Page number
    - **page_size**: Items per page
    """
    try:
        if kg_id not in _kg_store:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge graph not found: {kg_id}"
            )
        
        # Filter entities by KG and type
        entities = [
            ent for ent in _entity_store.values()
            if ent.get("kg_id") == kg_id
        ]
        
        if entity_type:
            entities = [e for e in entities if e.get("entity_type") == entity_type]
        
        total = len(entities)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = entities[start_idx:end_idx]
        
        return [
            KGEntityResponse(
                id=e.get("id"),
                name=e.get("name"),
                entity_type=e.get("entity_type"),
                text_content=e.get("text_content"),
                source_document=e.get("source_document"),
                source_section=e.get("source_section"),
                properties=e.get("properties", {}),
                cluster=e.get("cluster"),
                description=e.get("description"),
                confidence=e.get("confidence", 1.0),
                image_id=e.get("image_id"),
                verification_status=e.get("verification_status", "auto"),
                created_at=e.get("created_at", datetime.utcnow()),
                updated_at=e.get("updated_at", datetime.utcnow()),
                linked_images=e.get("linked_images", [])
            )
            for e in paginated
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kg_id}/entities", response_model=KGEntityResponse)
async def create_entity(
    kg_id: str,
    entity: KGEntityCreate
):
    """
    Create a new entity in a knowledge graph
    
    - **kg_id**: Knowledge graph identifier
    - **entity**: Entity data
    """
    try:
        if kg_id not in _kg_store:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge graph not found: {kg_id}"
            )
        
        entity_data = entity.model_dump()
        entity_data["kg_id"] = kg_id
        entity_data["created_at"] = datetime.utcnow()
        entity_data["updated_at"] = datetime.utcnow()
        
        _entity_store[entity.id] = entity_data
        
        # Update KG entity count
        kg = _kg_store[kg_id]
        kg.entity_count += 1
        kg.updated_at = datetime.utcnow()
        
        logger.info(f"Created entity: {entity.id} in KG {kg_id}")
        
        return KGEntityResponse(
            **entity_data,
            linked_images=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kg_id}/relationships", response_model=List[KGRelationshipResponse])
async def list_relationships(
    kg_id: str,
    relation_type: Optional[str] = Query(None, description="Filter by relation type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    List relationships in a knowledge graph
    
    - **kg_id**: Knowledge graph identifier
    - **relation_type**: Optional filter by relation type
    - **page**: Page number
    - **page_size**: Items per page
    """
    try:
        if kg_id not in _kg_store:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge graph not found: {kg_id}"
            )
        
        # Filter relationships by KG
        relationships = [
            rel for rel in _relationship_store.values()
            if rel.get("kg_id") == kg_id
        ]
        
        if relation_type:
            relationships = [
                r for r in relationships 
                if r.get("relation_type") == relation_type
            ]
        
        total = len(relationships)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = relationships[start_idx:end_idx]
        
        return [
            KGRelationshipResponse(
                id=r.get("id"),
                source_id=r.get("source_id"),
                target_id=r.get("target_id"),
                relation_type=r.get("relation_type"),
                properties=r.get("properties", {}),
                evidence=r.get("evidence"),
                hypothesis_status=r.get("hypothesis_status"),
                confidence=r.get("confidence", 1.0),
                source=r.get("source"),
                created_at=r.get("created_at", datetime.utcnow()),
                updated_at=r.get("updated_at", datetime.utcnow())
            )
            for r in paginated
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kg_id}/relationships", response_model=KGRelationshipResponse)
async def create_relationship(
    kg_id: str,
    relationship: KGRelationshipCreate
):
    """
    Create a new relationship in a knowledge graph
    
    - **kg_id**: Knowledge graph identifier
    - **relationship**: Relationship data
    """
    try:
        if kg_id not in _kg_store:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge graph not found: {kg_id}"
            )
        
        import uuid
        rel_id = f"REL_{uuid.uuid4().hex[:8].upper()}"
        
        rel_data = relationship.model_dump()
        rel_data["id"] = rel_id
        rel_data["kg_id"] = kg_id
        rel_data["created_at"] = datetime.utcnow()
        rel_data["updated_at"] = datetime.utcnow()
        
        _relationship_store[rel_id] = rel_data
        
        # Update KG relationship count
        kg = _kg_store[kg_id]
        kg.relationship_count += 1
        kg.updated_at = datetime.utcnow()
        
        logger.info(f"Created relationship: {rel_id} in KG {kg_id}")
        
        return KGRelationshipResponse(
            id=rel_id,
            source_id=rel_data["source_id"],
            target_id=rel_data["target_id"],
            relation_type=rel_data["relation_type"],
            properties=rel_data.get("properties", {}),
            evidence=rel_data.get("evidence"),
            hypothesis_status=rel_data.get("hypothesis_status"),
            confidence=rel_data.get("confidence", 1.0),
            source=rel_data.get("source"),
            created_at=rel_data["created_at"],
            updated_at=rel_data["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))
