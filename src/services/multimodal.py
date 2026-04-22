"""
多模态服务 - 语音/图片处理
支持 TTS 语音合成、ASR 语音识别、图片分析
"""
import os
import base64
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import io


class AudioFormat(Enum):
    """音频格式"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    M4A = "m4a"


class ImageFormat(Enum):
    """图片格式"""
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    GIF = "gif"


@dataclass
class SpeechResult:
    """语音合成结果"""
    audio_data: bytes
    format: str
    duration_seconds: float = 0.0
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save(self, path: str) -> bool:
        """保存音频文件"""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(self.audio_data)
            return True
        except Exception:
            return False


@dataclass
class TranscriptionResult:
    """语音识别结果"""
    text: str
    language: str = "zh-CN"
    confidence: float = 0.0
    words: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageAnalysisResult:
    """图片分析结果"""
    description: str
    tags: List[str] = field(default_factory=list)
    objects: List[Dict[str, Any]] = field(default_factory=list)
    faces: List[Dict[str, Any]] = field(default_factory=list)
    text: str = ""                    # 图片中的文字
    ocr_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultimodalService:
    """
    多模态服务
    
    功能：
    1. TTS - 文本转语音，支持多种声音和语言
    2. ASR - 语音转文本，支持实时识别
    3. 图片分析 - 描述、标签、物体检测
    4. OCR - 图片文字识别
    5. 图像生成 - 支持调用图像生成 API
    """
    
    def __init__(self, cache_dir: str = "data/multimodal"):
        """
        初始化多模态服务
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    # ==================== TTS 语音合成 ====================
    
    def text_to_speech(
        self,
        text: str,
        voice: str = "default",
        language: str = "zh-CN",
        speed: float = 1.0,
        output_format: str = AudioFormat.MP3.value
    ) -> SpeechResult:
        """
        文本转语音
        
        Args:
            text: 输入文本
            voice: 声音名称
            language: 语言代码
            speed: 语速 (0.5-2.0)
            output_format: 输出格式
            
        Returns:
            语音合成结果
        """
        # 优先使用 gTTS (免费)
        try:
            from gtts import gTTS
            
            lang_map = {
                "zh-CN": "zh-CN",
                "en-US": "en",
                "ja-JP": "ja",
                "ko-KR": "ko",
                "fr-FR": "fr",
                "de-DE": "de"
            }
            lang = lang_map.get(language, "zh-CN")
            
            tts = gTTS(text=text, lang=lang, slow=(speed < 0.8))
            mp3_buffer = io.BytesIO()
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)
            
            return SpeechResult(
                audio_data=mp3_buffer.read(),
                format=AudioFormat.MP3.value,
                duration_seconds=len(text) / (10 * speed),  # 粗略估算
                text=text
            )
            
        except ImportError:
            # gTTS 未安装，返回占位结果
            return SpeechResult(
                audio_data=b"",
                format=output_format,
                text=text,
                metadata={"error": "gTTS not installed, run: pip install gtts"}
            )
    
    def text_to_speech_elevenlabs(
        self,
        text: str,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikHAM",
        model: str = "eleven_monolingual_v1"
    ) -> SpeechResult:
        """
        使用 ElevenLabs API 进行语音合成
        
        Args:
            text: 输入文本
            api_key: API 密钥
            voice_id: 声音ID
            model: 模型
            
        Returns:
            语音合成结果
        """
        import requests
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        data = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        return SpeechResult(
            audio_data=response.content,
            format=AudioFormat.MP3.value,
            text=text,
            metadata={"voice_id": voice_id, "provider": "elevenlabs"}
        )
    
    # ==================== ASR 语音识别 ====================
    
    def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "zh-CN",
        model: str = "base"
    ) -> TranscriptionResult:
        """
        语音转文本
        
        Args:
            audio_data: 音频数据
            language: 语言代码
            model: 模型大小
            
        Returns:
            识别结果
        """
        # 优先使用 Whisper
        try:
            import whisper
            import numpy as np
            
            # 保存临时文件
            temp_path = os.path.join(self.cache_dir, f"temp_audio_{datetime.now().timestamp()}.mp3")
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
            
            # 加载模型
            whisper_model = whisper.load_model(model)
            
            # 转录
            result = whisper_model.transcribe(temp_path, language=language)
            
            # 清理临时文件
            try:
                os.remove(temp_path)
            except Exception:
                pass
            
            words = []
            if "words" in result:
                words = [{"word": w["word"], "start": w["start"], "end": w["end"]} 
                        for w in result["words"]]
            
            return TranscriptionResult(
                text=result["text"],
                language=language,
                confidence=result.get("confidence", 0.0),
                words=words,
                duration_seconds=result.get("duration", 0.0)
            )
            
        except ImportError:
            return TranscriptionResult(
                text="",
                metadata={"error": "Whisper not installed, run: pip install openai-whisper"}
            )
    
    def speech_to_text_google(
        self,
        audio_data: bytes,
        api_key: str,
        language: str = "zh-CN"
    ) -> TranscriptionResult:
        """
        使用 Google Speech-to-Text API
        
        Args:
            audio_data: 音频数据
            api_key: API 密钥
            language: 语言代码
            
        Returns:
            识别结果
        """
        import requests
        
        # 需要先转换格式
        audio_content = base64.b64encode(audio_data).decode('utf-8')
        
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
        
        data = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": 16000,
                "languageCode": language
            },
            "audio": {
                "content": audio_content
            }
        }
        
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        transcript = ""
        words = []
        
        if "results" in result:
            for r in result["results"]:
                alt = r.get("alternatives", [{}])[0]
                transcript += alt.get("transcript", "")
                
                for w in alt.get("words", []):
                    words.append({
                        "word": w.get("word", ""),
                        "start": w.get("startTime", {}).get("seconds", 0),
                        "end": w.get("endTime", {}).get("seconds", 0)
                    })
        
        return TranscriptionResult(
            text=transcript,
            language=language,
            words=words
        )
    
    # ==================== 图片分析 ====================
    
    def analyze_image(
        self,
        image_data: Union[bytes, str],
        api_key: str = None,
        model: str = "gpt-4o-mini"
    ) -> ImageAnalysisResult:
        """
        分析图片
        
        Args:
            image_data: 图片数据或 URL
            api_key: API 密钥（用于云端服务）
            model: 分析模型
            
        Returns:
            分析结果
        """
        # 支持本地图片或 URL
        if isinstance(image_data, str):
            if image_data.startswith("http"):
                image_data = self._download_image(image_data)
            else:
                with open(image_data, 'rb') as f:
                    image_data = f.read()
        
        # 尝试使用 GPT-4 Vision
        if api_key:
            return self._analyze_with_openai(image_data, api_key, model)
        
        # 回退到本地 OCR
        return self._analyze_local(image_data)
    
    def _download_image(self, url: str) -> bytes:
        """下载图片"""
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    
    def _analyze_with_openai(
        self,
        image_data: bytes,
        api_key: str,
        model: str = "gpt-4o-mini"
    ) -> ImageAnalysisResult:
        """使用 OpenAI Vision API 分析"""
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        # 转换为 base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """请分析这张图片，返回以下格式的 JSON：
{
    "description": "图片描述",
    "tags": ["标签1", "标签2"],
    "objects": [{"name": "物体名", "count": 数量}],
    "text": "图片中的文字（如果有）"
}"""
                    }
                ]
            }],
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content
        
        # 解析 JSON
        import re
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return ImageAnalysisResult(
                description=result.get("description", ""),
                tags=result.get("tags", []),
                objects=result.get("objects", []),
                text=result.get("text", "")
            )
        
        return ImageAnalysisResult(description=result_text)
    
    def _analyze_local(self, image_data: bytes) -> ImageAnalysisResult:
        """本地图片分析（基础版）"""
        try:
            from PIL import Image
            import pytesseract
            
            # 打开图片
            image = Image.open(io.BytesIO(image_data))
            
            # OCR
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            return ImageAnalysisResult(
                description="本地 OCR 分析",
                text=text.strip()
            )
            
        except ImportError:
            return ImageAnalysisResult(
                description="图片分析服务不可用",
                metadata={"error": "需要安装 Pillow 和 pytesseract"}
            )
    
    # ==================== OCR 文字识别 ====================
    
    def ocr(
        self,
        image_data: Union[bytes, str],
        language: str = "chi_sim+eng"
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        OCR 文字识别
        
        Args:
            image_data: 图片数据或路径
            language: 识别语言
            
        Returns:
            (识别的文本, 文字位置列表)
        """
        try:
            from PIL import Image
            import pytesseract
            
            # 打开图片
            if isinstance(image_data, str):
                image = Image.open(image_data)
            else:
                image = Image.open(io.BytesIO(image_data))
            
            # 获取文字数据和位置
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            
            # 提取有效结果
            texts = []
            positions = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if text:
                    texts.append(text)
                    positions.append({
                        "text": text,
                        "x": data['left'][i],
                        "y": data['top'][i],
                        "width": data['width'][i],
                        "height": data['height'][i],
                        "confidence": data['conf'][i]
                    })
            
            return ' '.join(texts), positions
            
        except ImportError:
            return "", []
    
    # ==================== 图像生成 ====================
    
    def generate_image(
        self,
        prompt: str,
        api_key: str,
        provider: str = "openai",
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> bytes:
        """
        生成图像
        
        Args:
            prompt: 图像描述
            api_key: API 密钥
            provider: 服务商 (openai/dalle, stability, midjourney)
            size: 图像尺寸
            quality: 质量
            
        Returns:
            生成的图像数据
        """
        if provider == "openai" or provider == "dalle":
            return self._generate_with_dalle(prompt, api_key, size, quality)
        elif provider == "stability":
            return self._generate_with_stability(prompt, api_key, size)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _generate_with_dalle(
        self,
        prompt: str,
        api_key: str,
        size: str,
        quality: str
    ) -> bytes:
        """使用 DALL-E 生成"""
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1
        )
        
        image_url = response.data[0].url
        
        # 下载图像
        return self._download_image(image_url)
    
    def _generate_with_stability(
        self,
        prompt: str,
        api_key: str,
        size: str
    ) -> bytes:
        """使用 Stability AI 生成"""
        import requests
        
        width, height = map(int, size.split('x'))
        
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        
        data = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        base64_image = result["artifacts"][0]["base64"]
        
        return base64.b64decode(base64_image)
    
    # ==================== 工具方法 ====================
    
    def image_to_base64(self, image_data: bytes, format: str = "jpeg") -> str:
        """图片转 base64"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def base64_to_image(self, base64_str: str) -> bytes:
        """base64 转图片"""
        return base64.b64decode(base64_str)
    
    def resize_image(
        self,
        image_data: bytes,
        width: int,
        height: int,
        maintain_aspect: bool = True
    ) -> bytes:
        """调整图片大小"""
        try:
            from PIL import Image
            
            image = Image.open(io.BytesIO(image_data))
            
            if maintain_aspect:
                image.thumbnail((width, height), Image.LANCZOS)
            else:
                image = image.resize((width, height), Image.LANCZOS)
            
            output = io.BytesIO()
            image.save(output, format=image.format or "JPEG")
            
            return output.getvalue()
            
        except ImportError:
            return image_data


# 修复导入
from pathlib import Path
