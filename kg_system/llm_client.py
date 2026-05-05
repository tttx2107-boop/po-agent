"""
LLM 客户端 - 支持 OpenAI / Claude / 本地模型
用于知识图谱提取引擎的实际LLM调用
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # Ollama, vLLM等
    DASHSCOPE = "dashscope"  # 阿里云通义


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # 自定义API地址
    temperature: float = 0.1
    max_tokens: int = 4096
    
    # 本地模型配置
    device: str = "cuda"  # cuda 或 cpu
    embedding_model: str = "text-embedding-3-small"


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def generate(self, prompt: str, system: str = None, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def extract_json(self, prompt: str, system: str = None) -> Dict:
        """提取JSON响应"""
        pass
    
    def batch_generate(self, prompts: List[str], system: str = None) -> List[str]:
        """批量生成"""
        return [self.generate(p, system) for p in prompts]


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client
    
    def generate(self, prompt: str, system: str = None, **kwargs) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens)
        )
        return response.choices[0].message.content
    
    def extract_json(self, prompt: str, system: str = None) -> Dict:
        text = self.generate(prompt, system)
        return self._parse_json(text)
    
    def _parse_json(self, text: str) -> Dict:
        """从文本中提取JSON"""
        # 尝试提取 ```json ... ``` 块
        match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # 尝试找第一个 { 到最后一个 }
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end+1]
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "JSON解析失败", "raw": text[:500]}


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("请安装 anthropic: pip install anthropic")
        return self._client
    
    def generate(self, prompt: str, system: str = None, **kwargs) -> str:
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        
        response = client.messages.create(
            model=self.config.model,
            system=system,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens)
        )
        return response.content[0].text
    
    def extract_json(self, prompt: str, system: str = None) -> Dict:
        text = self.generate(prompt, system)
        # Claude可能输出到 ``` ... ``` 中
        match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except:
            return {"error": "JSON解析失败", "raw": text[:500]}


class LocalClient(BaseLLMClient):
    """本地模型客户端（Ollama / vLLM）"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                base_url = self.config.base_url or "http://localhost:11434/v1"
                self._client = OpenAI(
                    api_key="ollama",  # Ollama不需要真实key
                    base_url=base_url
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client
    
    def generate(self, prompt: str, system: str = None, **kwargs) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # 本地模型可能用不同的模型名
        model = self.config.model
        if "/" in model:
            model = model.split("/")[-1]
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens)
        )
        return response.choices[0].message.content
    
    def extract_json(self, prompt: str, system: str = None) -> Dict:
        text = self.generate(prompt, system)
        match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except:
            return {"error": "JSON解析失败", "raw": text[:500]}


class DashScopeClient(BaseLLMClient):
    """阿里云通义千问客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import dashscope
                dashscope.api_key = self.config.api_key
                self._client = dashscope
            except ImportError:
                raise ImportError("请安装 dashscope: pip install dashscope")
        return self._client
    
    def generate(self, prompt: str, system: str = None, **kwargs) -> str:
        from dashscope import Generation
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = Generation.call(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            result_format='message'
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"DashScope API错误: {response.message}")
    
    def extract_json(self, prompt: str, system: str = None) -> Dict:
        text = self.generate(prompt, system)
        match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except:
            return {"error": "JSON解析失败", "raw": text[:500]}


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    """创建LLM客户端"""
    clients = {
        LLMProvider.OPENAI: OpenAIClient,
        LLMProvider.ANTHROPIC: AnthropicClient,
        LLMProvider.LOCAL: LocalClient,
        LLMProvider.DASHSCOPE: DashScopeClient,
    }
    
    client_class = clients.get(config.provider)
    if not client_class:
        raise ValueError(f"不支持的LLM提供商: {config.provider}")
    
    return client_class(config)


def load_from_env() -> Optional[LLMConfig]:
    """从环境变量加载配置"""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return None
    
    if os.getenv("OPENAI_API_KEY"):
        provider = LLMProvider.OPENAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    elif os.getenv("ANTHROPIC_API_KEY"):
        provider = LLMProvider.ANTHROPIC
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20250514")
    else:
        provider = LLMProvider.DASHSCOPE
        model = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    
    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL")
    )
