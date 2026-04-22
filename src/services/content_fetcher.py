"""
内容抓取服务 - 支持多种来源的内容获取
集成 Jina Reader / Crawl4AI / 传统 HTTP
"""
import re
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse, urljoin
import json
import os

import requests
from bs4 import BeautifulSoup


class ContentSource(Enum):
    """内容来源"""
    JINA = "jina"                # Jina Reader API
    CRAWL4AI = "crawl4ai"        # Crawl4AI
    DIRECT = "direct"            # 直接请求
    BUFFER = "buffer"            # 本地缓存


class ContentType(Enum):
    """内容类型"""
    ARTICLE = "article"          # 文章
    PRODUCT = "product"          # 产品
    CODE = "code"                # 代码
    DOCUMENT = "document"        # 文档
    SOCIAL = "social"           # 社交媒体
    UNKNOWN = "unknown"


@dataclass
class FetchedContent:
    """抓取的内容"""
    url: str
    title: str
    content: str
    source: str
    content_type: str = ContentType.UNKNOWN.value
    author: str = ""
    publish_date: str = ""
    description: str = ""
    images: List[str] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    raw_html: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetch_time: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "content_type": self.content_type,
            "author": self.author,
            "publish_date": self.publish_date,
            "description": self.description,
            "images": self.images,
            "links": self.links,
            "fetch_time": self.fetch_time,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class CrawlConfig:
    """爬取配置"""
    timeout: int = 30              # 超时秒数
    max_content_length: int = 100000  # 最大内容长度
    user_agent: str = "Mozilla/5.0 (compatible; po-agent/1.0)"
    headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    })
    cache_enabled: bool = True     # 是否启用缓存
    cache_ttl: int = 3600          # 缓存 TTL（秒）
    retry_times: int = 3           # 重试次数
    retry_delay: float = 1.0      # 重试延迟


class ContentFetcher:
    """
    内容抓取服务
    
    功能：
    1. 多源抓取 - Jina Reader / Crawl4AI / 直接请求
    2. 智能解析 - 自动识别内容类型
    3. 内容清洗 - 去除广告和干扰元素
    4. 缓存管理 - 避免重复抓取
    5. 批量抓取 - 支持并发和限流
    """
    
    def __init__(self, cache_dir: str = "data/content_cache", config: CrawlConfig = None):
        """
        初始化内容抓取器
        
        Args:
            cache_dir: 缓存目录
            config: 爬取配置
        """
        self.cache_dir = cache_dir
        self.config = config or CrawlConfig()
        self._ensure_cache_dir()
        self._load_cache_index()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _load_cache_index(self):
        """加载缓存索引"""
        index_path = os.path.join(self.cache_dir, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    self.cache_index = json.load(f)
            except Exception:
                self.cache_index = {}
        else:
            self.cache_index = {}
    
    def _save_cache_index(self):
        """保存缓存索引"""
        if not self.cache_dir:
            return
        index_path = os.path.join(self.cache_dir, "index.json")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _get_cache_path(self, url: str) -> str:
        """获取缓存路径"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")
    
    def _is_cache_valid(self, url: str) -> bool:
        """检查缓存是否有效"""
        if not self.config.cache_enabled:
            return False
        
        if url not in self.cache_index:
            return False
        
        cache_entry = self.cache_index[url]
        cached_at = datetime.fromisoformat(cache_entry["timestamp"])
        ttl = cache_entry.get("ttl", self.config.cache_ttl)
        
        if (datetime.now() - cached_at).total_seconds() > ttl:
            return False
        
        cache_path = self._get_cache_path(url)
        return os.path.exists(cache_path)
    
    def _get_from_cache(self, url: str) -> Optional[FetchedContent]:
        """从缓存获取"""
        cache_path = self._get_cache_path(url)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return FetchedContent(**data)
            except Exception:
                pass
        return None
    
    def _save_to_cache(self, url: str, content: FetchedContent):
        """保存到缓存"""
        if not self.config.cache_enabled or not self.cache_dir:
            return
        
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(content.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.cache_index[url] = {
                "timestamp": content.timestamp,
                "ttl": self.config.cache_ttl
            }
            self._save_cache_index()
        except Exception:
            pass
    
    # ==================== 核心抓取方法 ====================
    
    def fetch(
        self,
        url: str,
        source: str = "auto",
        bypass_cache: bool = False
    ) -> FetchedContent:
        """
        抓取网页内容
        
        Args:
            url: 目标 URL
            source: 来源策略 (auto/jina/crawl4ai/direct)
            bypass_cache: 是否跳过缓存
            
        Returns:
            抓取的内容
        """
        # 检查缓存
        if not bypass_cache and self._is_cache_valid(url):
            cached = self._get_from_cache(url)
            if cached:
                return cached
        
        # 解析 URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        
        # 自动选择来源
        if source == "auto":
            source = self._auto_select_source(url)
        
        # 执行抓取
        start_time = time.time()
        content = None
        error_msg = ""
        
        for attempt in range(self.config.retry_times):
            try:
                if source == ContentSource.JINA.value:
                    content = self._fetch_via_jina(url)
                elif source == ContentSource.CRAWL4AI.value:
                    content = self._fetch_via_crawl4ai(url)
                else:
                    content = self._fetch_direct(url)
                
                if content and content.content:
                    break
                    
            except Exception as e:
                error_msg = str(e)
                if attempt < self.config.retry_times - 1:
                    time.sleep(self.config.retry_delay)
        
        if not content:
            # 返回空内容
            content = FetchedContent(
                url=url,
                title="",
                content="",
                source=source,
                error=error_msg
            )
        
        content.fetch_time = time.time() - start_time
        
        # 保存缓存
        if content.content:
            self._save_to_cache(url, content)
        
        return content
    
    def _auto_select_source(self, url: str) -> str:
        """自动选择最优来源"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 社交媒体使用直接请求
        social_domains = ["twitter.com", "x.com", "weibo.com", "douyin.com"]
        if any(d in domain for d in social_domains):
            return ContentSource.DIRECT.value
        
        # 电商使用直接请求
        ecommerce_domains = ["taobao.com", "jd.com", "amazon.com", "tmall.com"]
        if any(d in domain for d in ecommerce_domains):
            return ContentSource.DIRECT.value
        
        # 默认使用 Jina（效果好且免费）
        return ContentSource.JINA.value
    
    def _fetch_via_jina(self, url: str) -> FetchedContent:
        """通过 Jina Reader API 抓取"""
        jina_url = f"https://r.jina.ai/{url}"
        
        headers = {
            "Accept": "application/json",
            "X-Return-Format": "json"
        }
        
        response = requests.get(
            jina_url,
            headers=headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        
        data = response.json()
        
        return FetchedContent(
            url=url,
            title=data.get("title", ""),
            content=data.get("content", ""),
            source=ContentSource.JINA.value,
            description=data.get("description", ""),
            author=data.get("author", ""),
            publish_date=data.get("published_time", ""),
            metadata=data.get("metadata", {})
        )
    
    def _fetch_via_crawl4ai(self, url: str) -> FetchedContent:
        """通过 Crawl4AI 抓取 (需要安装爬虫)"""
        # Crawl4AI 是异步的，这里提供同步接口
        try:
            from crawl4ai import AsyncWebCrawler
            
            async def _crawl():
                async with AsyncWebCrawler(verbose=False) as crawler:
                    result = await crawler.arun(url=url)
                    return result
            
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(_crawl())
            
            return FetchedContent(
                url=url,
                title=result.metadata.get("title", ""),
                content=result.markdown,
                source=ContentSource.CRAWL4AI.value,
                raw_html=result.html,
                metadata=result.metadata
            )
            
        except ImportError:
            # Crawl4AI 未安装，降级到直接请求
            return self._fetch_direct(url)
    
    def _fetch_direct(self, url: str) -> FetchedContent:
        """直接请求抓取"""
        response = requests.get(
            url,
            headers={
                "User-Agent": self.config.user_agent,
                **self.config.headers
            },
            timeout=self.config.timeout
        )
        response.raise_for_status()
        
        html = response.text
        content = self._parse_html(html, url)
        content.raw_html = html
        
        return content
    
    def _parse_html(self, html: str, url: str) -> FetchedContent:
        """解析 HTML 内容"""
        soup = BeautifulSoup(html, 'html.parser')
        parsed = urlparse(url)
        
        # 提取标题
        title = ""
        if soup.title:
            title = soup.title.string or ""
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "")
        
        # 提取作者
        author = ""
        author_tag = soup.find("meta", attrs={"name": "author"}) or \
                     soup.find("meta", attrs={"property": "article:author"})
        if author_tag:
            author = author_tag.get("content", "")
        
        # 提取发布日期
        publish_date = ""
        date_tag = soup.find("meta", attrs={"property": "article:published_time"}) or \
                   soup.find("time")
        if date_tag:
            if date_tag.name == "meta":
                publish_date = date_tag.get("content", "")
            else:
                publish_date = date_tag.get("datetime", date_tag.string or "")
        
        # 提取描述
        description = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or \
                   soup.find("meta", attrs={"property": "og:description"})
        if desc_tag:
            description = desc_tag.get("content", "")
        
        # 提取正文内容
        content = self._extract_main_content(soup)
        
        # 提取图片
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src", "")
            if src:
                if not src.startswith("http"):
                    src = urljoin(url, src)
                images.append(src)
        
        # 提取链接
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = urljoin(url, href)
            links.append({
                "text": a.get_text(strip=True)[:100],
                "href": href
            })
        
        # 判断内容类型
        content_type = self._detect_content_type(soup, url)
        
        return FetchedContent(
            url=url,
            title=title.strip() if title else "",
            content=content,
            source=ContentSource.DIRECT.value,
            content_type=content_type,
            author=author,
            publish_date=publish_date,
            description=description,
            images=images[:20],  # 限制图片数量
            links=links[:50],    # 限制链接数量
            metadata={
                "domain": parsed.netloc,
                "word_count": len(content)
            }
        )
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """提取主要内容"""
        # 移除干扰元素
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # 尝试常见的内容容器
        content_selectors = [
            ("article", {}),
            ("main", {}),
            ("div", {"class": re.compile(r"article|content|post|entry|main", re.I)}),
            ("div", {"id": re.compile(r"article|content|post|entry|main", re.I)}),
        ]
        
        content_elem = None
        for selector, attrs in content_selectors:
            elements = soup.find_all(selector, attrs)
            for elem in elements:
                text = elem.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    content_elem = elem
                    break
            if content_elem:
                break
        
        if not content_elem:
            content_elem = soup.body if soup.body else soup
        
        # 提取文本
        text = content_elem.get_text(separator="\n", strip=True)
        
        # 清理空白
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        # 限制长度
        if len(text) > self.config.max_content_length:
            text = text[:self.config.max_content_length] + "..."
        
        return text
    
    def _detect_content_type(self, soup: BeautifulSoup, url: str) -> str:
        """检测内容类型"""
        url_lower = url.lower()
        
        # 根据 URL 判断
        if "github.com" in url_lower or "stackoverflow.com" in url_lower:
            return ContentType.CODE.value
        if any(k in url_lower for k in ["product", "item", "shop"]):
            return ContentType.PRODUCT.value
        if any(k in url_lower for k in ["docs", "doc", "wiki"]):
            return ContentType.DOCUMENT.value
        if any(k in url_lower for k in ["twitter.com", "weibo.com", "x.com"]):
            return ContentType.SOCIAL.value
        
        # 根据内容判断
        if soup.find("pre") or soup.find("code"):
            return ContentType.CODE.value
        if soup.find("article"):
            return ContentType.ARTICLE.value
        
        return ContentType.UNKNOWN.value
    
    # ==================== 批量抓取 ====================
    
    def fetch_batch(
        self,
        urls: List[str],
        source: str = "auto",
        max_concurrent: int = 3,
        progress_callback: Callable[[int, int, FetchedContent], None] = None
    ) -> List[FetchedContent]:
        """
        批量抓取
        
        Args:
            urls: URL 列表
            source: 来源策略
            max_concurrent: 最大并发数
            progress_callback: 进度回调 (current, total, content)
            
        Returns:
            抓取结果列表
        """
        results = []
        total = len(urls)
        
        for i, url in enumerate(urls):
            try:
                content = self.fetch(url, source=source)
                results.append(content)
                
                if progress_callback:
                    progress_callback(i + 1, total, content)
                
            except Exception as e:
                results.append(FetchedContent(
                    url=url,
                    title="",
                    content="",
                    source=source,
                    error=str(e)
                ))
            
            # 限流
            if i < total - 1:
                time.sleep(0.5)
        
        return results
    
    # ==================== 缓存管理 ====================
    
    def clear_cache(self, older_than_days: int = 7) -> int:
        """
        清理缓存
        
        Args:
            older_than_days: 清理多少天前的缓存
            
        Returns:
            清理的文件数
        """
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return 0
        
        cutoff = datetime.now() - timedelta(days=older_than_days)
        count = 0
        
        for filename in os.listdir(self.cache_dir):
            if filename == "index.json":
                continue
            
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.isfile(filepath):
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if mtime < cutoff:
                    os.remove(filepath)
                    count += 1
        
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return {"count": 0, "size_mb": 0}
        
        total_size = 0
        count = 0
        
        for filename in os.listdir(self.cache_dir):
            if filename == "index.json":
                continue
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
                count += 1
        
        return {
            "count": count,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": self.cache_dir
        }
