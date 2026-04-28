# SPDX-License-Identifier: MIT
"""
Multimodal Knowledge Graph - Main API Routes
Aggregated router combining all sub-routes
"""
import logging
from fastapi import APIRouter, Depends
from loguru import logger

from app.api import images, annotations, kg, fusion, learning, visualization

logger.configure(handlers=[{"sink": __name__}])

# Create main API router
router = APIRouter(prefix="/api", tags=["api"])

# Include sub-routers
router.include_router(images.router, prefix="/images", tags=["images"])
router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
router.include_router(kg.router, prefix="/kg", tags=["knowledge-graph"])
router.include_router(fusion.router, prefix="/fusion", tags=["fusion"])
router.include_router(learning.router, prefix="/learning", tags=["learning"])
router.include_router(visualization.router, prefix="/visualization", tags=["visualization"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "multimodal-kg-api"}


@router.get("/status")
async def get_status():
    """Get system status"""
    return {
        "status": "operational",
        "modules": {
            "images": "active",
            "annotations": "active",
            "knowledge_graph": "active",
            "fusion": "active",
            "learning": "active",
            "visualization": "active"
        }
    }
