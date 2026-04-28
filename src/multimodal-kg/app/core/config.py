# SPDX-License-Identifier: MIT
"""
Multimodal Knowledge Graph - Core Configuration
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import yaml


class Settings(BaseSettings):
    """Application settings loaded from config.yaml"""
    
    # App settings
    app_name: str = "Multimodal Knowledge Graph System"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Storage paths
    base_path: Path = Path("/root/multimodal-kg/data")
    images_raw: Path = Path("/root/multimodal-kg/data/images/raw")
    images_annotated: Path = Path("/root/multimodal-kg/data/images/annotated")
    images_thumbnails: Path = Path("/root/multimodal-kg/data/images/thumbnails")
    annotations_pending: Path = Path("/root/multimodal-kg/data/annotations/pending")
    annotations_verified: Path = Path("/root/multimodal-kg/data/annotations/verified")
    annotations_corrected: Path = Path("/root/multimodal-kg/data/annotations/corrected")
    kg_text: Path = Path("/root/multimodal-kg/data/kg/text")
    kg_image: Path = Path("/root/multimodal-kg/data/kg/image")
    kg_multimodal: Path = Path("/root/multimodal-kg/data/kg/multimodal")
    
    # Database
    db_path: Path = Path("/root/multimodal-kg/data/knowledge_graph.db")
    
    # Vector DB
    vector_db_enabled: bool = True
    vector_db_dir: Path = Path("/root/multimodal-kg/data/chroma_db")
    
    # Models
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: Optional[str] = None
    vision_model: str = "gpt-4o"
    detection_enabled: bool = True
    detection_model: str = "yolov8n.pt"
    ocr_enabled: bool = True
    ocr_engine: str = "paddleocr"
    
    # Thresholds
    auto_annotate_confidence: float = 0.8
    require_human_review: float = 0.7
    low_confidence_threshold: float = 0.5
    min_feedback_ratio: float = 0.2
    feedback_batch_size: int = 50
    cross_modal_match_threshold: float = 0.75
    entity_merge_threshold: float = 0.85
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create all necessary directories"""
        dirs = [
            self.base_path,
            self.images_raw,
            self.images_annotated,
            self.images_thumbnails,
            self.annotations_pending,
            self.annotations_verified,
            self.annotations_corrected,
            self.kg_text,
            self.kg_image,
            self.kg_multimodal,
            self.vector_db_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "/root/multimodal-kg/config.yaml"):
        """Load settings from YAML config file"""
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Flatten nested config
            flat_config = {}
            
            # App settings
            if 'app' in config_data:
                flat_config['app_name'] = config_data['app'].get('name', cls().app_name)
                flat_config['app_version'] = config_data['app'].get('version', cls().app_version)
                flat_config['debug'] = config_data['app'].get('debug', cls().debug)
                flat_config['host'] = config_data['app'].get('host', cls().host)
                flat_config['port'] = config_data['app'].get('port', cls().port)
            
            # Storage paths
            if 'storage' in config_data:
                base = config_data['storage'].get('base_path', '/root/multimodal-kg/data')
                for key, path in config_data['storage'].items():
                    if key == 'base_path':
                        flat_config['base_path'] = Path(path)
                    elif 'images' in key:
                        flat_config[f'images_{key.split("_")[-1]}'] = Path(f"{base}/{path}")
                    elif 'annotations' in key:
                        flat_config[f'annotations_{key.split("_")[-1]}'] = Path(f"{base}/{path}")
                    elif 'kg' in key:
                        flat_config[f'kg_{key.split("_")[-1]}'] = Path(f"{base}/{path}")
            
            # Database
            if 'database' in config_data:
                flat_config['db_path'] = Path(config_data['database'].get('path', cls().db_path))
            
            # Vector DB
            if 'vector_db' in config_data:
                flat_config['vector_db_enabled'] = config_data['vector_db'].get('enabled', True)
                flat_config['vector_db_dir'] = Path(config_data['vector_db'].get('persist_dir', cls().vector_db_dir))
            
            # Models
            if 'models' in config_data:
                if 'llm' in config_data['models']:
                    flat_config['llm_provider'] = config_data['models']['llm'].get('provider', 'openai')
                    flat_config['llm_model'] = config_data['models']['llm'].get('model', 'gpt-4o')
                    api_key = config_data['models']['llm'].get('api_key', '')
                    if api_key and not api_key.startswith('${'):
                        flat_config['llm_api_key'] = api_key
                if 'vision' in config_data['models']:
                    flat_config['vision_model'] = config_data['models']['vision'].get('model', 'gpt-4o')
                if 'detection' in config_data['models']:
                    flat_config['detection_enabled'] = config_data['models']['detection'].get('enabled', True)
                    flat_config['detection_model'] = config_data['models']['detection'].get('model_name', 'yolov8n.pt')
                if 'ocr' in config_data['models']:
                    flat_config['ocr_enabled'] = config_data['models']['ocr'].get('enabled', True)
                    flat_config['ocr_engine'] = config_data['models']['ocr'].get('engine', 'paddleocr')
            
            # Thresholds
            if 'annotation' in config_data:
                flat_config['auto_annotate_confidence'] = config_data['annotation'].get('auto_annotate_confidence', 0.8)
                flat_config['require_human_review'] = config_data['annotation'].get('require_human_review', 0.7)
                flat_config['low_confidence_threshold'] = config_data['annotation'].get('low_confidence_threshold', 0.5)
                flat_config['min_feedback_ratio'] = config_data['annotation'].get('min_feedback_ratio', 0.2)
                flat_config['feedback_batch_size'] = config_data['annotation'].get('feedback_batch_size', 50)
            
            if 'kg' in config_data:
                flat_config['cross_modal_match_threshold'] = config_data['kg'].get('cross_modal_match_threshold', 0.75)
                flat_config['entity_merge_threshold'] = config_data['kg'].get('merge_threshold', 0.85)
            
            return cls(**flat_config)
        return cls()


# Global settings instance
settings = Settings.load_from_yaml()
