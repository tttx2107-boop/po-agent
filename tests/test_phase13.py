"""
Phase 13: 高级功能测试
包括：记忆服务、Token监控、内容抓取、浏览器自动化、多模态服务
"""
import pytest
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path


class TestMemoryService:
    """测试记忆增强服务"""
    
    def test_memory_entry_creation(self):
        """测试记忆条目创建"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.memory_service import MemoryEntry, MemoryType, MemoryImportance
        
        entry = MemoryEntry(
            id="test-id-123",
            content="这是一个测试记忆",
            memory_type=MemoryType.SEMANTIC.value,
            importance=MemoryImportance.HIGH.value,
            tags=["测试", "重要"]
        )
        
        assert entry.content == "这是一个测试记忆"
        assert entry.memory_type == "semantic"
        assert entry.importance == 3
        assert "测试" in entry.tags
        assert entry.id == "test-id-123"
        assert entry.created_at != ""
    
    def test_memory_service_init(self):
        """测试记忆服务初始化"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.memory_service import MemoryService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            service = MemoryService(db_path=db_path)
            
            assert os.path.exists(db_path)
    
    def test_add_and_get_memory(self):
        """测试添加和获取记忆"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.memory_service import MemoryService, MemoryType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            service = MemoryService(db_path=db_path)
            
            # 添加记忆
            memory = service.add_memory(
                content="测试记忆内容",
                memory_type=MemoryType.EPISODIC.value,
                tags=["测试"]
            )
            
            assert memory.id != ""
            assert memory.content == "测试记忆内容"
            
            # 获取记忆
            retrieved = service.get_memory(memory.id)
            assert retrieved is not None
            assert retrieved.content == "测试记忆内容"
    
    def test_search_memory(self):
        """测试搜索记忆"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.memory_service import MemoryService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            service = MemoryService(db_path=db_path)
            
            # 添加多条记忆
            service.add_memory(content="Python 编程学习")
            service.add_memory(content="Web 开发技术")
            service.add_memory(content="机器学习基础")
            
            # 搜索
            results = service.search("Python")
            assert len(results) > 0
            assert any("Python" in r.memory.content for r in results)
    
    def test_memory_stats(self):
        """测试记忆统计"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.memory_service import MemoryService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            service = MemoryService(db_path=db_path)
            
            # 添加记忆
            service.add_memory(content="测试1")
            service.add_memory(content="测试2")
            service.add_memory(content="测试3")
            
            stats = service.get_memory_stats()
            assert stats["total"] >= 3


class TestTokenMonitor:
    """测试 Token 监控服务"""
    
    def test_token_usage_record(self):
        """测试使用记录"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.token_monitor import TokenUsage, ModelPricing
        
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            cost=0.01,
            latency_ms=500
        )
        
        assert usage.total_tokens == 1500
        assert usage.cost > 0
    
    def test_model_pricing(self):
        """测试模型定价计算"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.token_monitor import ModelPricing
        
        pricing = ModelPricing("gpt-4o", 0.005, 0.015)
        cost = pricing.calculate_cost(1000, 500)
        
        # 1000 * 0.005 / 1000 + 500 * 0.015 / 1000 = 0.005 + 0.0075 = 0.0125
        assert cost == 0.0125
    
    def test_token_monitor_init(self):
        """测试监控器初始化"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.token_monitor import TokenMonitor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_token.json")
            monitor = TokenMonitor(db_path=db_path)
            
            assert monitor is not None
            assert len(monitor.pricing) > 0
    
    def test_record_usage(self):
        """测试记录使用"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.token_monitor import TokenMonitor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_token.json")
            monitor = TokenMonitor(db_path=db_path)
            
            usage = monitor.record_usage(
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=500
            )
            
            assert usage.total_tokens == 1500
            assert usage.cost > 0
    
    def test_estimate_cost(self):
        """测试成本估算"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.token_monitor import TokenMonitor
        
        monitor = TokenMonitor()
        
        cost = monitor.estimate_cost("gpt-4o", 1000, 500)
        assert cost == 0.0125
    
    def test_token_counter(self):
        """测试 Token 计数器"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.token_monitor import TokenCounter
        
        # 中文文本
        chinese_text = "这是一个测试"
        tokens = TokenCounter.estimate_tokens(chinese_text, "gpt-4o")
        assert tokens > 0
        
        # 英文文本
        english_text = "This is a test"
        tokens = TokenCounter.estimate_tokens(english_text, "gpt-4o")
        assert tokens > 0


class TestContentFetcher:
    """测试内容抓取服务"""
    
    def test_fetched_content(self):
        """测试抓取内容对象"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.content_fetcher import FetchedContent, ContentSource, ContentType
        
        content = FetchedContent(
            url="https://example.com",
            title="Test Title",
            content="Test content",
            source=ContentSource.DIRECT.value,
            content_type=ContentType.ARTICLE.value
        )
        
        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.content == "Test content"
        assert content.source == "direct"
    
    def test_content_fetcher_init(self):
        """测试抓取器初始化"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.content_fetcher import ContentFetcher, CrawlConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CrawlConfig(timeout=10)
            fetcher = ContentFetcher(cache_dir=tmpdir, config=config)
            
            assert fetcher is not None
            assert fetcher.config.timeout == 10
    
    def test_parse_html(self):
        """测试 HTML 解析"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.content_fetcher import ContentFetcher
        
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = ContentFetcher(cache_dir=tmpdir)
            
            html = """
            <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is a test paragraph.</p>
            </body>
            </html>
            """
            
            content = fetcher._parse_html(html, "https://example.com")
            
            assert content.title == "Test Page"
            assert "Hello World" in content.content


class TestBrowserAutomation:
    """测试浏览器自动化服务"""
    
    def test_browser_config(self):
        """测试浏览器配置"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.browser_automation import BrowserConfig, BrowserType
        
        config = BrowserConfig(
            browser_type=BrowserType.CHROMIUM.value,
            headless=True,
            timeout=30000
        )
        
        assert config.browser_type == "chromium"
        assert config.headless == True
        assert config.timeout == 30000
    
    def test_browser_action(self):
        """测试浏览器操作记录"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.browser_automation import BrowserAction, BrowserType
        
        action = BrowserAction(
            action_type="goto",
            selector="https://example.com",
            success=True
        )
        
        assert action.action_type == "goto"
        assert action.success == True
        assert action.timestamp != ""


class TestMultimodalService:
    """测试多模态服务"""
    
    def test_speech_result(self):
        """测试语音结果"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.multimodal import SpeechResult, AudioFormat
        
        result = SpeechResult(
            audio_data=b"test audio data",
            format=AudioFormat.MP3.value,
            duration_seconds=5.0,
            text="测试语音"
        )
        
        assert result.audio_data == b"test audio data"
        assert result.format == "mp3"
        assert result.duration_seconds == 5.0
    
    def test_transcription_result(self):
        """测试语音识别结果"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.multimodal import TranscriptionResult
        
        result = TranscriptionResult(
            text="这是识别的文本",
            language="zh-CN",
            confidence=0.95
        )
        
        assert result.text == "这是识别的文本"
        assert result.language == "zh-CN"
        assert result.confidence == 0.95
    
    def test_image_analysis_result(self):
        """测试图片分析结果"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.multimodal import ImageAnalysisResult
        
        result = ImageAnalysisResult(
            description="测试图片描述",
            tags=["测试", "图片"],
            objects=[{"name": "物体", "count": 1}]
        )
        
        assert result.description == "测试图片描述"
        assert "测试" in result.tags
        assert len(result.objects) > 0
    
    def test_multimodal_service_init(self):
        """测试多模态服务初始化"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        from services.multimodal import MultimodalService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MultimodalService(cache_dir=tmpdir)
            
            assert service is not None
            assert os.path.exists(tmpdir)


class TestDockerConfig:
    """测试 Docker 配置"""
    
    def test_dockerfile_exists(self):
        """测试 Dockerfile 存在"""
        dockerfile_path = Path("/root/po-agent/Dockerfile")
        assert dockerfile_path.exists()
    
    def test_docker_compose_exists(self):
        """测试 docker-compose.yml 存在"""
        compose_path = Path("/root/po-agent/docker-compose.yml")
        assert compose_path.exists()
    
    def test_docker_compose_min_exists(self):
        """测试最小化 docker-compose.yml 存在"""
        compose_path = Path("/root/po-agent/docker-compose.min.yml")
        assert compose_path.exists()
    
    def test_dockerignore_exists(self):
        """测试 .dockerignore 存在"""
        ignore_path = Path("/root/po-agent/.dockerignore")
        assert ignore_path.exists()


class TestServiceIntegration:
    """测试服务集成"""
    
    def test_all_services_importable(self):
        """测试所有服务可导入"""
        import sys
        sys.path.insert(0, '/root/po-agent/src')
        
        from services.memory_service import MemoryService
        from services.token_monitor import TokenMonitor
        from services.content_fetcher import ContentFetcher
        from services.browser_automation import BrowserAutomation, SyncBrowserAutomation
        from services.multimodal import MultimodalService
        
        assert True  # 如果能执行到这里，说明所有模块都成功导入


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
