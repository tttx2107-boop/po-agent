"""
浏览器自动化服务 - Playwright 封装
支持网页交互、截图、PDF 导出
"""
import os
import asyncio
import base64
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class BrowserType(Enum):
    """浏览器类型"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ElementSelector:
    """元素选择器"""
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ROLE = "role"


@dataclass
class BrowserAction:
    """浏览器操作记录"""
    action_type: str
    selector: str = ""
    value: str = ""
    timestamp: str = ""
    success: bool = False
    error: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: str = BrowserType.CHROMIUM.value
    headless: bool = True
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    user_agent: str = ""
    timeout: int = 30000       # 毫秒
    slow_mo: int = 0           # 减速（毫秒）
    downloads_path: str = ""    # 下载目录


class BrowserAutomation:
    """
    浏览器自动化服务
    
    功能：
    1. 页面导航 - 打开 URL，支持前进后退
    2. 元素交互 - 点击、输入、悬停、滚动
    3. 内容提取 - 获取元素内容、属性、表单值
    4. 截图功能 - 全屏截图、元素截图、PDF 导出
    5. 等待机制 - 等待元素、网络空闲、JavaScript 执行
    6. 录制回放 - 记录操作序列用于回放
    """
    
    def __init__(self, config: BrowserConfig = None):
        """
        初始化浏览器自动化服务
        
        Args:
            config: 浏览器配置
        """
        self.config = config or BrowserConfig()
        self._browser = None
        self._context = None
        self._page = None
        self._actions: List[BrowserAction] = []
        self._playwright = None
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            from playwright.async_api import async_playwright
            
            self._playwright = async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo
            )
            
            self._context = await self._browser.new_context(
                viewport=self.config.viewport,
                user_agent=self.config.user_agent or None,
                accept_downloads=True
            )
            
            self._page = await self._context.new_page()
            
            # 设置超时
            self._page.set_default_timeout(self.config.timeout)
    
    async def _close_browser(self):
        """关闭浏览器"""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    # ==================== 页面导航 ====================
    
    async def goto(self, url: str, wait_until: str = "load") -> bool:
        """
        导航到 URL
        
        Args:
            url: 目标 URL
            wait_until: 等待时机 (load/domcontentloaded/networkidle)
            
        Returns:
            是否成功
        """
        await self._ensure_browser()
        
        action = BrowserAction(action_type="goto", selector=url)
        
        try:
            await self._page.goto(url, wait_until=wait_until)
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def back(self) -> bool:
        """后退"""
        await self._ensure_browser()
        
        action = BrowserAction(action_type="back")
        
        try:
            await self._page.go_back()
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def forward(self) -> bool:
        """前进"""
        await self._ensure_browser()
        
        action = BrowserAction(action_type="forward")
        
        try:
            await self._page.go_forward()
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def reload(self) -> bool:
        """刷新"""
        await self._ensure_browser()
        
        action = BrowserAction(action_type="reload")
        
        try:
            await self._page.reload()
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    # ==================== 元素交互 ====================
    
    async def click(
        self,
        selector: str,
        selector_type: str = ElementSelector.CSS,
        modifiers: List[str] = None,
        delay: int = 0
    ) -> bool:
        """
        点击元素
        
        Args:
            selector: 选择器
            selector_type: 选择器类型
            modifiers: 按住的修饰键 (Control/Meta/Shift/Alt)
            delay: 点击后等待（毫秒）
            
        Returns:
            是否成功
        """
        await self._ensure_browser()
        
        action = BrowserAction(action_type="click", selector=selector)
        
        try:
            locator = self._get_locator(selector, selector_type)
            await locator.click(modifiers=modifiers or [], delay=delay)
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def fill(
        self,
        selector: str,
        value: str,
        selector_type: str = ElementSelector.CSS,
        press_enter: bool = False
    ) -> bool:
        """
        填写表单
        
        Args:
            selector: 选择器
            value: 填写值
            selector_type: 选择器类型
            press_enter: 填写后按回车
            
        Returns:
            是否成功
        """
        await self._ensure_browser()
        
        action = BrowserAction(action_type="fill", selector=selector, value=value)
        
        try:
            locator = self._get_locator(selector, selector_type)
            await locator.fill(value)
            
            if press_enter:
                await locator.press("Enter")
            
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def select(
        self,
        selector: str,
        value: str = None,
        label: str = None,
        selector_type: str = ElementSelector.CSS
    ) -> bool:
        """
        选择下拉选项
        
        Args:
            selector: 选择器
            value: 选项值
            label: 选项标签
            selector_type: 选择器类型
            
        Returns:
            是否成功
        """
        await self._ensure_browser()
        
        action = BrowserAction(action_type="select", selector=selector, value=value or label)
        
        try:
            locator = self._get_locator(selector, selector_type)
            
            if value:
                await locator.select_option(value=value)
            else:
                await locator.select_option(label=label)
            
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def hover(
        self,
        selector: str,
        selector_type: str = ElementSelector.CSS
    ) -> bool:
        """悬停元素"""
        await self._ensure_browser()
        
        action = BrowserAction(action_type="hover", selector=selector)
        
        try:
            locator = self._get_locator(selector, selector_type)
            await locator.hover()
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    async def scroll_to(
        self,
        selector: str = None,
        selector_type: str = ElementSelector.CSS,
        y_offset: int = 0
    ) -> bool:
        """
        滚动页面
        
        Args:
            selector: 滚动到元素
            selector_type: 选择器类型
            y_offset: Y 轴偏移量
            
        Returns:
            是否成功
        """
        await self._ensure_browser()
        
        action = BrowserAction(action_type="scroll", selector=selector or f"offset:{y_offset}")
        
        try:
            if selector:
                locator = self._get_locator(selector, selector_type)
                await locator.scroll_into_view_if_needed()
            else:
                await self._page.mouse.wheel(0, y_offset)
            
            action.success = True
        except Exception as e:
            action.error = str(e)
        
        self._actions.append(action)
        return action.success
    
    # ==================== 内容提取 ====================
    
    async def get_text(
        self,
        selector: str,
        selector_type: str = ElementSelector.CSS,
        timeout: int = 5000
    ) -> Optional[str]:
        """
        获取元素文本
        
        Args:
            selector: 选择器
            selector_type: 选择器类型
            timeout: 超时（毫秒）
            
        Returns:
            文本内容
        """
        await self._ensure_browser()
        
        try:
            locator = self._get_locator(selector, selector_type)
            return await locator.text_content()
        except Exception:
            return None
    
    async def get_attribute(
        self,
        selector: str,
        attribute: str,
        selector_type: str = ElementSelector.CSS
    ) -> Optional[str]:
        """
        获取元素属性
        
        Args:
            selector: 选择器
            attribute: 属性名
            selector_type: 选择器类型
            
        Returns:
            属性值
        """
        await self._ensure_browser()
        
        try:
            locator = self._get_locator(selector, selector_type)
            return await locator.get_attribute(attribute)
        except Exception:
            return None
    
    async def get_inner_html(
        self,
        selector: str,
        selector_type: str = ElementSelector.CSS
    ) -> Optional[str]:
        """获取元素 HTML"""
        return await self.get_attribute(selector, "innerHTML", selector_type)
    
    async def evaluate_js(
        self,
        script: str,
        timeout: int = 10000
    ) -> Any:
        """
        执行 JavaScript
        
        Args:
            script: JavaScript 代码
            timeout: 超时（毫秒）
            
        Returns:
            执行结果
        """
        await self._ensure_browser()
        
        try:
            return await self._page.evaluate(script, timeout=timeout)
        except Exception:
            return None
    
    async def get_page_content(self) -> str:
        """获取页面内容"""
        await self._ensure_browser()
        
        try:
            return await self._page.content()
        except Exception:
            return ""
    
    # ==================== 等待机制 ====================
    
    async def wait_for_selector(
        self,
        selector: str,
        selector_type: str = ElementSelector.CSS,
        state: str = "visible",
        timeout: int = 30000
    ) -> bool:
        """
        等待元素
        
        Args:
            selector: 选择器
            selector_type: 选择器类型
            state: 等待状态 (visible/hidden/attached/detached)
            timeout: 超时（毫秒）
            
        Returns:
            是否等到
        """
        await self._ensure_browser()
        
        try:
            locator = self._get_locator(selector, selector_type)
            await locator.wait_for(state=state, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def wait_for_navigation(
        self,
        wait_until: str = "load",
        timeout: int = 30000
    ) -> bool:
        """等待导航完成"""
        await self._ensure_browser()
        
        try:
            await self._page.wait_for_load_state(wait_until, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def wait_for_function(
        self,
        script: str,
        timeout: int = 30000,
        polling: str = "raf"
    ) -> bool:
        """
        等待 JavaScript 函数返回 true
        
        Args:
            script: JavaScript 函数
            timeout: 超时（毫秒）
            polling: 检查间隔 (raf/mutation/interval)
            
        Returns:
            是否等到
        """
        await self._ensure_browser()
        
        try:
            await self._page.wait_for_function(script, timeout=timeout, polling=polling)
            return True
        except Exception:
            return False
    
    # ==================== 截图与导出 ====================
    
    async def screenshot(
        self,
        path: str = None,
        selector: str = None,
        selector_type: str = ElementSelector.CSS,
        full_page: bool = False,
        format: str = "png"
    ) -> Optional[str]:
        """
        截图
        
        Args:
            path: 保存路径
            selector: 只截取指定元素
            selector_type: 选择器类型
            full_page: 是否截取整个页面
            format: 格式 (png/jpeg/webp)
            
        Returns:
            Base64 编码的图片数据或保存路径
        """
        await self._ensure_browser()
        
        try:
            if selector:
                locator = self._get_locator(selector, selector_type)
                img_bytes = await locator.screenshot(type=format)
            else:
                img_bytes = await self._page.screenshot(
                    full_page=full_page,
                    type=format
                )
            
            if path:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(img_bytes)
                return path
            
            return base64.b64encode(img_bytes).decode('utf-8')
            
        except Exception:
            return None
    
    async def export_pdf(
        self,
        path: str,
        format: str = "pdf",
        paper_width: float = 8.5,
        paper_height: float = 11.0,
        margin: Dict[str, float] = None
    ) -> bool:
        """
        导出 PDF
        
        Args:
            path: 保存路径
            format: 格式 (pdf)
            paper_width: 纸张宽度（英寸）
            paper_height: 纸张高度（英寸）
            margin: 页边距
            
        Returns:
            是否成功
        """
        await self._ensure_browser()
        
        margin = margin or {"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"}
        
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            await self._page.pdf(
                path=path,
                format=format,
                width=f"{paper_width}in",
                height=f"{paper_height}in",
                margin=margin
            )
            return True
        except Exception:
            return False
    
    # ==================== 辅助方法 ====================
    
    def _get_locator(self, selector: str, selector_type: str):
        """获取元素定位器"""
        if selector_type == ElementSelector.XPATH:
            return self._page.locator(f"xpath={selector}")
        elif selector_type == ElementSelector.TEXT:
            return self._page.get_by_text(selector)
        elif selector_type == ElementSelector.ROLE:
            return self._page.get_by_role(selector)
        else:
            return self._page.locator(selector)
    
    async def get_current_url(self) -> str:
        """获取当前 URL"""
        if self._page:
            return self._page.url
        return ""
    
    async def get_title(self) -> str:
        """获取页面标题"""
        if self._page:
            return await self._page.title()
        return ""
    
    def get_actions(self) -> List[Dict[str, Any]]:
        """获取操作历史"""
        return [vars(a) for a in self._actions]
    
    async def clear_actions(self):
        """清除操作历史"""
        self._actions = []


# ==================== 同步封装 ====================

class SyncBrowserAutomation:
    """
    同步封装版本
    
    提供同步接口，内部使用 asyncio
    """
    
    def __init__(self, config: BrowserConfig = None):
        self._async = BrowserAutomation(config)
        self._loop = None
    
    def _ensure_loop(self):
        """确保事件循环存在"""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def goto(self, url: str, wait_until: str = "load") -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.goto(url, wait_until))
    
    def back(self) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.back())
    
    def forward(self) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.forward())
    
    def reload(self) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.reload())
    
    def click(self, selector: str, selector_type: str = ElementSelector.CSS) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.click(selector, selector_type))
    
    def fill(self, selector: str, value: str, selector_type: str = ElementSelector.CSS) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.fill(selector, value, selector_type))
    
    def select(self, selector: str, value: str = None, label: str = None) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.select(selector, value, label))
    
    def hover(self, selector: str, selector_type: str = ElementSelector.CSS) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.hover(selector, selector_type))
    
    def scroll_to(self, selector: str = None, selector_type: str = ElementSelector.CSS) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.scroll_to(selector, selector_type))
    
    def get_text(self, selector: str, selector_type: str = ElementSelector.CSS) -> Optional[str]:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.get_text(selector, selector_type))
    
    def get_attribute(self, selector: str, attribute: str, selector_type: str = ElementSelector.CSS) -> Optional[str]:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.get_attribute(selector, attribute, selector_type))
    
    def evaluate_js(self, script: str) -> Any:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.evaluate_js(script))
    
    def get_page_content(self) -> str:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.get_page_content())
    
    def wait_for_selector(self, selector: str, selector_type: str = ElementSelector.CSS) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.wait_for_selector(selector, selector_type))
    
    def wait_for_navigation(self, wait_until: str = "load") -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.wait_for_navigation(wait_until))
    
    def screenshot(self, path: str = None, full_page: bool = False) -> Optional[str]:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.screenshot(path, full_page=full_page))
    
    def export_pdf(self, path: str) -> bool:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.export_pdf(path))
    
    def get_current_url(self) -> str:
        if self._async._page:
            return self._async._page.url
        return ""
    
    def get_title(self) -> str:
        self._ensure_loop()
        return self._loop.run_until_complete(self._async.get_title())
    
    def close(self):
        """关闭浏览器"""
        if self._loop:
            self._loop.run_until_complete(self._async._close_browser())
            self._loop.close()
            self._loop = None
