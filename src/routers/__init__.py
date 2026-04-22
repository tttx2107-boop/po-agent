"""API 路由"""
from src.routers.ideas import router as ideas_router
from src.routers.risk_warning import router as risk_router
from src.routers.tasks import router as tasks_router
from src.routers.platform import router as platform_router

__all__ = ["ideas_router", "risk_router", "tasks_router", "platform_router"]
