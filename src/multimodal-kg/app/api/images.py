# SPDX-License-Identifier: MIT
"""
Image API Routes for Multimodal Knowledge Graph System
Handles image upload, batch operations, and retrieval
"""
import logging
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from app.schemas.models import (
    ImageUploadResponse,
    ImageMetadata,
    ImageDetailResponse,
    ImageAnnotationResponse,
    PaginatedResponse,
    StatusResponse
)
from app.services.acquisition_service import DocumentImageExtractor, ImageData
from app.core.config import settings

logger.add(lambda msg: print(msg))

router = APIRouter(prefix="", tags=["images"])

# In-memory image storage (replace with actual database integration)
_image_store: dict = {}


async def save_upload_file(upload_file: UploadFile, destination: Path) -> Path:
    """Save uploaded file to destination"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        content = await upload_file.read()
        buffer.write(content)
    return destination


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a single image file
    
    - **file**: Image file (jpg, png, webp, etc.)
    """
    try:
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}"
            )
        
        # Generate unique filename
        import uuid
        file_ext = Path(file.filename).suffix if file.filename else ".jpg"
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        storage_path = settings.images_raw / unique_filename
        
        # Save file
        await save_upload_file(file, storage_path)
        
        # Create image metadata
        from datetime import datetime
        image_id = uuid.uuid4().hex[:16]
        
        image_metadata = ImageMetadata(
            id=image_id,
            filename=file.filename or unique_filename,
            storage_path=str(storage_path),
            mime_type=file.content_type,
            annotation_status="pending",
            created_at=datetime.utcnow()
        )
        
        # Store in memory (replace with DB)
        _image_store[image_id] = image_metadata
        
        logger.info(f"Uploaded image: {image_id} - {file.filename}")
        
        return ImageUploadResponse(
            id=image_id,
            filename=file.filename or unique_filename,
            storage_path=str(storage_path),
            message="Image uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=StatusResponse)
async def batch_upload_images(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Batch upload multiple images
    
    - **files**: List of image files
    """
    try:
        import uuid
        from datetime import datetime
        
        results = {"successful": [], "failed": []}
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
        
        for file in files:
            try:
                if file.content_type not in allowed_types:
                    results["failed"].append({
                        "filename": file.filename,
                        "error": f"Unsupported file type: {file.content_type}"
                    })
                    continue
                
                file_ext = Path(file.filename).suffix if file.filename else ".jpg"
                unique_filename = f"{uuid.uuid4().hex}{file_ext}"
                storage_path = settings.images_raw / unique_filename
                
                await save_upload_file(file, storage_path)
                
                image_id = uuid.uuid4().hex[:16]
                image_metadata = ImageMetadata(
                    id=image_id,
                    filename=file.filename or unique_filename,
                    storage_path=str(storage_path),
                    mime_type=file.content_type,
                    annotation_status="pending",
                    created_at=datetime.utcnow()
                )
                
                _image_store[image_id] = image_metadata
                results["successful"].append({"id": image_id, "filename": file.filename})
                
            except Exception as e:
                results["failed"].append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        total = len(files)
        successful = len(results["successful"])
        
        logger.info(f"Batch upload: {successful}/{total} successful")
        
        return StatusResponse(
            success=successful > 0,
            message=f"Uploaded {successful}/{total} images",
            data=results
        )
        
    except Exception as e:
        logger.error(f"Error in batch upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=PaginatedResponse)
async def list_images(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    image_type: Optional[str] = Query(None, description="Filter by image type"),
    annotation_status: Optional[str] = Query(None, description="Filter by annotation status")
):
    """
    List all images with pagination
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page
    - **image_type**: Optional filter by image type
    - **annotation_status**: Optional filter by annotation status
    """
    try:
        # Filter images
        filtered_images = list(_image_store.values())
        
        if image_type:
            filtered_images = [
                img for img in filtered_images 
                if img.image_type == image_type
            ]
        
        if annotation_status:
            filtered_images = [
                img for img in filtered_images 
                if img.annotation_status.value == annotation_status
            ]
        
        total = len(filtered_images)
        pages = (total + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_images = filtered_images[start_idx:end_idx]
        
        return PaginatedResponse(
            items=[img.model_dump() for img in paginated_images],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_details(image_id: str):
    """
    Get detailed information about a specific image
    
    - **image_id**: Unique image identifier
    """
    try:
        image = _image_store.get(image_id)
        
        if not image:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        
        # In production, fetch annotations from database
        # For now, return empty list
        annotations_list = []
        
        return ImageDetailResponse(
            **image.model_dump(),
            annotations=annotations_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}", response_model=StatusResponse)
async def delete_image(image_id: str):
    """
    Delete an image by ID
    
    - **image_id**: Unique image identifier
    """
    try:
        image = _image_store.pop(image_id, None)
        
        if not image:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        
        # Delete file from storage if exists
        storage_path = Path(image.storage_path)
        if storage_path.exists():
            storage_path.unlink()
        
        logger.info(f"Deleted image: {image_id}")
        
        return StatusResponse(
            success=True,
            message=f"Image {image_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail=str(e))
