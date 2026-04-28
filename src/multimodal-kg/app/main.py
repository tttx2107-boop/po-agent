# SPDX-License-Identifier: MIT
"""
Multimodal Knowledge Graph System
Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
import sys

from app.core.config import settings
from app.models.database import init_db
from app.api.routes import router as api_router


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.debug and "DEBUG" or "INFO"
)

# Add file logging
logger.add(
    settings.base_path.parent / "logs" / "app_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG" if settings.debug else "INFO"
)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multimodal Knowledge Graph System - Text + Image Knowledge Graph Construction",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="/root/multimodal-kg/web"), name="static")
    
    # Templates
    templates = Jinja2Templates(directory="/root/multimodal-kg/web")
    
    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.app_version,
            "service": settings.app_name
        }
    
    # Web UI routes
    @app.get("/")
    async def root():
        return {"message": "Multimodal Knowledge Graph System", "docs": "/docs"}
    
    @app.get("/annotation")
    async def annotation_page():
        return {"message": "Annotation UI - Go to /static/annotation/index.html"}
    
    @app.get("/kg-viewer")
    async def kg_viewer_page():
        return {"message": "KG Viewer - Go to /static/kg_viewer/index.html"}
    
    logger.info(f"Application started: {settings.app_name} v{settings.app_version}")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
