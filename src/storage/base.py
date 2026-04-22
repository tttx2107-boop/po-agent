"""存储基类"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import json
from pathlib import Path


class BaseStorage(ABC):
    """存储抽象基类"""
    
    @abstractmethod
    def save_ideas(self, ideas: List[Dict[str, Any]]) -> bool:
        """保存想法列表"""
        pass
    
    @abstractmethod
    def load_ideas(self) -> List[Dict[str, Any]]:
        """加载想法列表"""
        pass
    
    @abstractmethod
    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """保存任务列表"""
        pass
    
    @abstractmethod
    def load_tasks(self) -> List[Dict[str, Any]]:
        """加载任务列表"""
        pass
    
    @abstractmethod
    def append_activity(self, log: Dict[str, Any]) -> bool:
        """追加活动日志"""
        pass
    
    @abstractmethod
    def load_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """加载活动日志"""
        pass


class LocalStorage(BaseStorage):
    """本地文件存储"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.ideas_file = self.data_dir / "ideas.json"
        self.tasks_file = self.data_dir / "tasks.json"
        self.activities_file = self.data_dir / "activities.json"
        self._ensure_files()
    
    def _ensure_files(self):
        """确保文件存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for f in [self.ideas_file, self.tasks_file, self.activities_file]:
            if not f.exists():
                f.write_text("[]", encoding="utf-8")
    
    def _read_json(self, filepath: Path) -> List[Dict]:
        """读取 JSON 文件"""
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _write_json(self, filepath: Path, data: List[Dict]) -> bool:
        """写入 JSON 文件"""
        try:
            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception:
            return False
    
    def save_ideas(self, ideas: List[Dict[str, Any]]) -> bool:
        return self._write_json(self.ideas_file, ideas)
    
    def load_ideas(self) -> List[Dict[str, Any]]:
        return self._read_json(self.ideas_file)
    
    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        return self._write_json(self.tasks_file, tasks)
    
    def load_tasks(self) -> List[Dict[str, Any]]:
        return self._read_json(self.tasks_file)
    
    def append_activity(self, log: Dict[str, Any]) -> bool:
        logs = self.load_activities()
        logs.append(log)
        # 只保留最近 1000 条
        logs = logs[-1000:]
        return self._write_json(self.activities_file, logs)
    
    def load_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        logs = self._read_json(self.activities_file)
        return logs[-limit:]
