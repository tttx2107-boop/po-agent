"""
多模型支持服务 - Phase 12
支持多种 AI 模型提供商 (OpenAI, Anthropic, 本地模型等)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Awaitable
from enum import Enum
import os
import json
from abc import ABC, abstractmethod


class ModelProvider(Enum):
    """模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"      # 本地模型
    MOCK = "mock"          # 测试用


class ModelType(Enum):
    """模型类型"""
    COMPLETION = "completion"     # 文本补全
    CHAT = "chat"               # 对话
    EMBEDDING = "embedding"      # 向量嵌入


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    api_key: str = ""
    base_url: str = ""  # 自定义 API 地址
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 60
    
    @classmethod
    def from_env(cls, provider: str = "openai") -> "ModelConfig":
        """从环境变量创建配置"""
        config = cls(provider=provider)
        
        if provider == "openai":
            config.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            config.api_key = os.getenv("OPENAI_API_KEY", "")
            config.base_url = os.getenv("OPENAI_BASE_URL", "")
        elif provider == "anthropic":
            config.model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
            config.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        elif provider == "ollama":
            config.model = os.getenv("OLLAMA_MODEL", "llama2")
            config.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        return config


@dataclass
class Message:
    """对话消息"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class CompletionResult:
    """补全结果"""
    text: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage
        }


class BaseModelProvider(ABC):
    """模型提供商基类"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> CompletionResult:
        """发送对话请求"""
        pass
    
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> CompletionResult:
        """发送补全请求"""
        pass
    
    def _get_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """提取用量信息"""
        if "usage" in response:
            return {
                "prompt_tokens": response["usage"].get("prompt_tokens", 0),
                "completion_tokens": response["usage"].get("completion_tokens", 0),
                "total_tokens": response["usage"].get("total_tokens", 0)
            }
        return {}


class OpenAIProvider(BaseModelProvider):
    """OpenAI 提供商"""
    
    async def chat(self, messages: List[Message], **kwargs) -> CompletionResult:
        """OpenAI Chat API"""
        import openai
        
        # 配置 API
        if self.config.base_url:
            openai.api_base = self.config.base_url
        if self.config.api_key:
            openai.api_key = self.config.api_key
        
        # 构建请求
        messages_dict = [m.to_dict() for m in messages]
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=kwargs.get("model", self.config.model),
                messages=messages_dict,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature)
            )
            
            text = response.choices[0].message.content
            return CompletionResult(
                text=text,
                model=response.model,
                provider="openai",
                usage=self._get_usage(response),
                raw_response=response
            )
        except Exception as e:
            return CompletionResult(
                text=f"Error: {str(e)}",
                model=self.config.model,
                provider="openai"
            )
    
    async def complete(self, prompt: str, **kwargs) -> CompletionResult:
        """OpenAI Completion API"""
        import openai
        
        if self.config.base_url:
            openai.api_base = self.config.base_url
        if self.config.api_key:
            openai.api_key = self.config.api_key
        
        try:
            response = await openai.Completion.acreate(
                model=kwargs.get("model", "text-davinci-003"),
                prompt=prompt,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature)
            )
            
            text = response.choices[0].text
            return CompletionResult(
                text=text,
                model=response.model,
                provider="openai",
                usage=self._get_usage(response)
            )
        except Exception as e:
            return CompletionResult(
                text=f"Error: {str(e)}",
                model=self.config.model,
                provider="openai"
            )


class AnthropicProvider(BaseModelProvider):
    """Anthropic (Claude) 提供商"""
    
    async def chat(self, messages: List[Message], **kwargs) -> CompletionResult:
        """Claude API"""
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            return CompletionResult(
                text="Error: anthropic package not installed",
                model=self.config.model,
                provider="anthropic"
            )
        
        client = AsyncAnthropic(api_key=self.config.api_key)
        
        # 提取 system message
        system = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_messages.append(m)
        
        try:
            response = await client.messages.create(
                model=kwargs.get("model", self.config.model),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in chat_messages]
            )
            
            return CompletionResult(
                text=response.content[0].text,
                model=response.model,
                provider="anthropic",
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )
        except Exception as e:
            return CompletionResult(
                text=f"Error: {str(e)}",
                model=self.config.model,
                provider="anthropic"
            )
    
    async def complete(self, prompt: str, **kwargs) -> CompletionResult:
        # Claude 主要使用消息 API
        return await self.chat([Message(role="user", content=prompt)], **kwargs)


class OllamaProvider(BaseModelProvider):
    """Ollama 本地模型提供商"""
    
    async def chat(self, messages: List[Message], **kwargs) -> CompletionResult:
        """Ollama Chat API"""
        import aiohttp
        
        base_url = kwargs.get("base_url", self.config.base_url)
        model = kwargs.get("model", self.config.model)
        
        url = f"{base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.config.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return CompletionResult(
                            text=data["message"]["content"],
                            model=model,
                            provider="ollama"
                        )
                    else:
                        return CompletionResult(
                            text=f"Error: HTTP {resp.status}",
                            model=model,
                            provider="ollama"
                        )
        except Exception as e:
            return CompletionResult(
                text=f"Error: {str(e)}",
                model=model,
                provider="ollama"
            )
    
    async def complete(self, prompt: str, **kwargs) -> CompletionResult:
        """Ollama Generate API"""
        import aiohttp
        
        base_url = kwargs.get("base_url", self.config.base_url)
        model = kwargs.get("model", self.config.model)
        
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.config.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return CompletionResult(
                            text=data["response"],
                            model=model,
                            provider="ollama"
                        )
                    else:
                        return CompletionResult(
                            text=f"Error: HTTP {resp.status}",
                            model=model,
                            provider="ollama"
                        )
        except Exception as e:
            return CompletionResult(
                text=f"Error: {str(e)}",
                model=model,
                provider="ollama"
            )


class MockProvider(BaseModelProvider):
    """Mock 提供商 (用于测试)"""
    
    async def chat(self, messages: List[Message], **kwargs) -> CompletionResult:
        """返回模拟响应"""
        last_message = messages[-1].content if messages else ""
        
        # 根据内容返回不同响应
        if "评估" in last_message or "评估" in str(messages):
            response = "✅ 这是一个有潜力的想法，建议进一步细化执行方案。"
        elif "拆解" in last_message:
            response = "已拆解为3个子任务：1. 需求分析 2. 开发实现 3. 测试上线"
        else:
            response = f"收到您的想法：{last_message[:50]}...，正在处理中。"
        
        return CompletionResult(
            text=response,
            model="mock-gpt",
            provider="mock",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        )
    
    async def complete(self, prompt: str, **kwargs) -> CompletionResult:
        return await self.chat([Message(role="user", content=prompt)], **kwargs)


class ModelManager:
    """模型管理器"""
    
    _providers: Dict[str, BaseModelProvider] = {}
    _default_provider: str = "mock"
    
    @classmethod
    def register_provider(cls, name: str, provider: BaseModelProvider):
        """注册提供商"""
        cls._providers[name] = provider
    
    @classmethod
    def get_provider(cls, name: str = None) -> BaseModelProvider:
        """获取提供商"""
        name = name or cls._default_provider
        
        if name not in cls._providers:
            # 自动创建
            if name == "openai":
                config = ModelConfig.from_env("openai")
                cls._providers[name] = OpenAIProvider(config)
            elif name == "anthropic":
                config = ModelConfig.from_env("anthropic")
                cls._providers[name] = AnthropicProvider(config)
            elif name == "ollama":
                config = ModelConfig.from_env("ollama")
                cls._providers[name] = OllamaProvider(config)
            elif name == "mock":
                cls._providers[name] = MockProvider(ModelConfig(provider="mock"))
            else:
                raise ValueError(f"Unknown provider: {name}")
        
        return cls._providers[name]
    
    @classmethod
    def set_default(cls, name: str):
        """设置默认提供商"""
        cls._default_provider = name
    
    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        """列出可用提供商"""
        return [
            {"name": name, "status": "active" if name in cls._providers else "lazy"}
            for name in ["openai", "anthropic", "ollama", "mock"]
        ]


# 便捷函数
async def chat(prompt: str, provider: str = None, **kwargs) -> str:
    """发送对话请求"""
    p = ModelManager.get_provider(provider)
    messages = [Message(role="user", content=prompt)]
    result = await p.chat(messages, **kwargs)
    return result.text


async def complete(prompt: str, provider: str = None, **kwargs) -> str:
    """发送补全请求"""
    p = ModelManager.get_provider(provider)
    result = await p.complete(prompt, **kwargs)
    return result.text


def get_model_manager() -> ModelManager:
    """获取模型管理器"""
    return ModelManager


# 初始化默认提供商
ModelManager.register_provider("mock", MockProvider(ModelConfig(provider="mock")))
