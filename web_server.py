"""
「破」Web 服务器入口
启动 FastAPI 服务提供 Web UI 和 API
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.ui.web_ui import router as web_ui_router
from src.routers.ideas import router as ideas_router
from src.routers.tasks import router as tasks_router
from src.ui.terminal_ui import TerminalUI
from src.utils.logger import setup_logger

logger = setup_logger("po-agent.web-server")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="「破」想法实现智能体",
        description="让想法从灵光一现到落地成真的 AI 助理",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(web_ui_router)
    app.include_router(ideas_router)
    app.include_router(tasks_router)
    
    @app.get("/api/health")
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "service": "po-agent",
            "version": "1.0.0"
        }
    
    return app


def main():
    """启动服务器"""
    ui = TerminalUI()
    
    ui.print_title("「破」Web 服务器")
    ui.blank()
    
    # 读取配置
    from src.utils.config import get_config
    config = get_config()
    
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    
    ui.print_info(f"服务器地址: http://{'localhost' if host == '0.0.0.0' else host}:{port}")
    ui.print_info(f"Web UI: http://{'localhost' if host == '0.0.0.0' else host}:{port}/ui/app")
    ui.print_info(f"API 文档: http://{'localhost' if host == '0.0.0.0' else host}:{port}/docs")
    ui.blank()
    
    ui.print_warning("按 Ctrl+C 停止服务器")
    ui.blank()
    
    # 启动服务器
    app = create_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    main()
