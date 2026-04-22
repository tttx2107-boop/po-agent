"""
Web UI 测试
"""
import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import create_app


@pytest.fixture
def client():
    """测试客户端"""
    app = create_app()
    return TestClient(app)


class TestWebUI:
    """Web UI 测试"""
    
    def test_index_page(self, client):
        """测试首页（Web UI 入口）"""
        response = client.get("/ui/")
        assert response.status_code == 200
        assert "「破」" in response.text
    
    def test_app_page(self, client):
        """测试应用页面"""
        response = client.get("/ui/app")
        assert response.status_code == 200
        assert "控制台" in response.text
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "po-agent"
    
    def test_websocket_status(self, client):
        """测试WebSocket状态"""
        response = client.get("/ui/status")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data


class TestTerminalUI:
    """Terminal UI 测试"""
    
    def test_color_codes(self):
        """测试颜色代码"""
        from src.ui.terminal_ui import Color
        
        assert Color.RED.startswith("\033")
        assert Color.GREEN.startswith("\033")
        assert Color.RESET == "\033[0m"
    
    def test_theme(self):
        """测试主题"""
        from src.ui.terminal_ui import Theme, TerminalUI
        
        ui = TerminalUI(theme=Theme.DEFAULT)
        assert ui.theme["title"] == Theme.DEFAULT["title"]
        
        ui_minimal = TerminalUI(theme=Theme.MINIMAL)
        assert ui_minimal.theme == Theme.MINIMAL
    
    def test_print_table(self, capsys):
        """测试表格打印"""
        from src.ui.terminal_ui import TerminalUI
        
        ui = TerminalUI()
        ui.print_table(
            headers=["名称", "状态"],
            rows=[["想法1", "新想法"], ["想法2", "已完成"]]
        )
        
        captured = capsys.readouterr()
        assert "名称" in captured.out
        assert "想法1" in captured.out
    
    def test_print_line(self, capsys):
        """测试分隔线"""
        from src.ui.terminal_ui import TerminalUI
        
        ui = TerminalUI()
        ui.print_line("─", 20)
        
        captured = capsys.readouterr()
        assert "─" * 20 in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
