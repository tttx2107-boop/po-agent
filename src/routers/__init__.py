"""API 路由"""
from src.routers.ideas import router as ideas_router
from src.routers.risk_warning import router as risk_router

__all__ = ["ideas_router", "risk_router"]
