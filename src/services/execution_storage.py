"""执行状态持久化 - 执行状态、检查点、日志存储"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4
import json
import os
from pathlib import Path


class StorageType(Enum):
    """存储类型"""
    MEMORY = "memory"        # 内存存储
    JSON_FILE = "json"       # JSON 文件
    SQLITE = "sqlite"        # SQLite 数据库


@dataclass
class ExecutionLog:
    """执行日志"""
    log_id: str
    execution_id: str
    timestamp: str
    level: str  # debug, info, warning, error
    message: str
    step_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.log_id:
            self.log_id = str(uuid4())[:12]
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionLog":
        return cls(**data)


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str
    execution_id: str
    task_id: str
    step_id: str
    
    # 检查点数据
    data: Dict[str, Any] = field(default_factory=dict)
    
    # 元信息
    created_at: str = ""
    description: str = ""
    
    # 关联的执行上下文快照
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.checkpoint_id:
            self.checkpoint_id = str(uuid4())[:12]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(**data)


@dataclass
class ExecutionState:
    """执行状态"""
    execution_id: str
    task_id: str
    idea_id: str
    
    # 状态信息
    status: str = "pending"
    progress: int = 0
    current_step: int = 0
    total_steps: int = 0
    
    # 时间
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    
    # 输出和结果
    output: Any = None
    error: str = ""
    
    # 产物
    artifacts: List[str] = field(default_factory=list)
    
    # 检查点
    checkpoint_id: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionState":
        return cls(**data)
    
    def get_duration_display(self) -> str:
        """获取时长显示"""
        duration = self.actual_duration or self.estimated_duration
        if duration < 60:
            return f"{duration:.1f}秒"
        elif duration < 3600:
            return f"{duration/60:.1f}分钟"
        else:
            return f"{duration/3600:.1f}小时"
    
    def get_status_display(self) -> str:
        """获取状态显示"""
        status_map = {
            "pending": "⏳ 待执行",
            "running": "🔄 执行中",
            "paused": "⏸️ 已暂停",
            "completed": "✅ 已完成",
            "failed": "❌ 失败",
            "cancelled": "🚫 已取消"
        }
        return status_map.get(self.status, self.status)


class ExecutionStorage:
    """
    执行状态持久化存储
    
    负责执行状态、检查点、日志的存储和恢复
    """
    
    def __init__(
        self,
        storage_type: str = StorageType.JSON_FILE.value,
        base_path: str = "/tmp/po-agent/executions"
    ):
        self.storage_type = storage_type
        self.base_path = Path(base_path)
        
        # 内存存储
        self._memory_states: Dict[str, ExecutionState] = {}
        self._memory_checkpoints: Dict[str, Checkpoint] = {}
        self._memory_logs: List[ExecutionLog] = []
        
        # 初始化存储路径
        if self.storage_type == StorageType.JSON_FILE.value:
            self._init_storage_path()
    
    def _init_storage_path(self):
        """初始化存储路径"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.base_path / "states").mkdir(exist_ok=True)
        (self.base_path / "checkpoints").mkdir(exist_ok=True)
        (self.base_path / "logs").mkdir(exist_ok=True)
    
    # ==================== 执行状态 ====================
    
    def save_state(self, state: ExecutionState) -> bool:
        """
        保存执行状态
        
        Args:
            state: 执行状态对象
            
        Returns:
            是否保存成功
        """
        if self.storage_type == StorageType.MEMORY.value:
            self._memory_states[state.execution_id] = state
            return True
        
        elif self.storage_type == StorageType.JSON_FILE.value:
            try:
                state_file = self.base_path / "states" / f"{state.execution_id}.json"
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(state.to_dict(), f, ensure_ascii=False, indent=2, default=str)
                return True
            except Exception as e:
                print(f"保存执行状态失败: {e}")
                return False
        
        return False
    
    def load_state(self, execution_id: str) -> Optional[ExecutionState]:
        """
        加载执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            执行状态对象
        """
        if self.storage_type == StorageType.MEMORY.value:
            return self._memory_states.get(execution_id)
        
        elif self.storage_type == StorageType.JSON_FILE.value:
            try:
                state_file = self.base_path / "states" / f"{execution_id}.json"
                if state_file.exists():
                    with open(state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return ExecutionState.from_dict(data)
            except Exception as e:
                print(f"加载执行状态失败: {e}")
        
        return None
    
    def delete_state(self, execution_id: str) -> bool:
        """删除执行状态"""
        if self.storage_type == StorageType.MEMORY.value:
            if execution_id in self._memory_states:
                del self._memory_states[execution_id]
                return True
            return False
        
        elif self.storage_type == StorageType.JSON_FILE.value:
            try:
                state_file = self.base_path / "states" / f"{execution_id}.json"
                if state_file.exists():
                    state_file.unlink()
                return True
            except Exception:
                return False
        
        return False
    
    def list_states(
        self,
        task_id: str = None,
        idea_id: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[ExecutionState]:
        """列出执行状态"""
        if self.storage_type == StorageType.MEMORY.value:
            states = list(self._memory_states.values())
        else:
            states = self._load_all_states()
        
        # 过滤
        if task_id:
            states = [s for s in states if s.task_id == task_id]
        if idea_id:
            states = [s for s in states if s.idea_id == idea_id]
        if status:
            states = [s for s in states if s.status == status]
        
        # 排序
        states.sort(key=lambda x: x.created_at or "", reverse=True)
        return states[:limit]
    
    def _load_all_states(self) -> List[ExecutionState]:
        """加载所有执行状态"""
        states = []
        states_dir = self.base_path / "states"
        
        if not states_dir.exists():
            return states
        
        for state_file in states_dir.glob("*.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    states.append(ExecutionState.from_dict(data))
            except Exception:
                continue
        
        return states
    
    # ==================== 检查点 ====================
    
    def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """
        保存检查点
        
        Args:
            checkpoint: 检查点对象
            
        Returns:
            是否保存成功
        """
        if self.storage_type == StorageType.MEMORY.value:
            self._memory_checkpoints[checkpoint.checkpoint_id] = checkpoint
            return True
        
        elif self.storage_type == StorageType.JSON_FILE.value:
            try:
                checkpoint_file = self.base_path / "checkpoints" / f"{checkpoint.checkpoint_id}.json"
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2, default=str)
                
                # 同时保存到索引文件
                self._update_checkpoint_index(checkpoint)
                return True
            except Exception as e:
                print(f"保存检查点失败: {e}")
                return False
        
        return False
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        if self.storage_type == StorageType.MEMORY.value:
            return self._memory_checkpoints.get(checkpoint_id)
        
        elif self.storage_type == StorageType.JSON_FILE.value:
            try:
                checkpoint_file = self.base_path / "checkpoints" / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return Checkpoint.from_dict(data)
            except Exception:
                pass
        
        return None
    
    def get_latest_checkpoint(self, execution_id: str) -> Optional[Checkpoint]:
        """获取最新的检查点"""
        checkpoints = self.list_checkpoints(execution_id)
        return checkpoints[0] if checkpoints else None
    
    def list_checkpoints(self, execution_id: str = None) -> List[Checkpoint]:
        """列出检查点"""
        if self.storage_type == StorageType.MEMORY.value:
            checkpoints = list(self._memory_checkpoints.values())
        else:
            checkpoints = self._load_all_checkpoints()
        
        if execution_id:
            checkpoints = [c for c in checkpoints if c.execution_id == execution_id]
        
        checkpoints.sort(key=lambda x: x.created_at or "", reverse=True)
        return checkpoints
    
    def _load_all_checkpoints(self) -> List[Checkpoint]:
        """加载所有检查点"""
        checkpoints = []
        checkpoints_dir = self.base_path / "checkpoints"
        
        if not checkpoints_dir.exists():
            return checkpoints
        
        for checkpoint_file in checkpoints_dir.glob("*.json"):
            if checkpoint_file.name == "index.json":
                continue
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    checkpoints.append(Checkpoint.from_dict(data))
            except Exception:
                continue
        
        return checkpoints
    
    def _update_checkpoint_index(self, checkpoint: Checkpoint):
        """更新检查点索引"""
        index_file = self.base_path / "checkpoints" / "index.json"
        
        try:
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)
            else:
                index = {}
        except Exception:
            index = {}
        
        if checkpoint.execution_id not in index:
            index[checkpoint.execution_id] = []
        
        # 添加新的检查点ID
        if checkpoint.checkpoint_id not in index[checkpoint.execution_id]:
            index[checkpoint.execution_id].append(checkpoint.checkpoint_id)
        
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    # ==================== 执行日志 ====================
    
    def save_log(self, log: ExecutionLog) -> bool:
        """
        保存执行日志
        
        Args:
            log: 日志对象
            
        Returns:
            是否保存成功
        """
        if self.storage_type == StorageType.MEMORY.value:
            self._memory_logs.append(log)
            return True
        
        elif self.storage_type == StorageType.JSON_FILE.value:
            try:
                log_file = self.base_path / "logs" / f"{log.execution_id}.jsonl"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log.to_dict(), ensure_ascii=False, default=str) + "\n")
                return True
            except Exception as e:
                print(f"保存日志失败: {e}")
                return False
        
        return False
    
    def save_logs_batch(self, logs: List[ExecutionLog]) -> int:
        """批量保存日志"""
        saved = 0
        for log in logs:
            if self.save_log(log):
                saved += 1
        return saved
    
    def load_logs(
        self,
        execution_id: str,
        level: str = None,
        limit: int = 500
    ) -> List[ExecutionLog]:
        """加载执行日志"""
        if self.storage_type == StorageType.MEMORY.value:
            logs = [l for l in self._memory_logs if l.execution_id == execution_id]
        else:
            logs = self._load_logs_from_file(execution_id)
        
        if level:
            logs = [l for l in logs if l.level == level]
        
        logs.sort(key=lambda x: x.timestamp or "")
        return logs[:limit]
    
    def _load_logs_from_file(self, execution_id: str) -> List[ExecutionLog]:
        """从文件加载日志"""
        logs = []
        log_file = self.base_path / "logs" / f"{execution_id}.jsonl"
        
        if not log_file.exists():
            return logs
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            logs.append(ExecutionLog.from_dict(data))
                        except Exception:
                            continue
        except Exception:
            pass
        
        return logs
    
    # ==================== 清理和维护 ====================
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        清理旧数据
        
        Args:
            days: 保留天数
            
        Returns:
            清理统计
        """
        if self.storage_type != StorageType.JSON_FILE.value:
            return {"states": 0, "checkpoints": 0, "logs": 0}
        
        cutoff = datetime.now().timestamp() - (days * 86400)
        stats = {"states": 0, "checkpoints": 0, "logs": 0}
        
        # 清理状态文件
        states_dir = self.base_path / "states"
        for state_file in states_dir.glob("*.json"):
            if state_file.stat().st_mtime < cutoff:
                state_file.unlink()
                stats["states"] += 1
        
        # 清理检查点
        checkpoints_dir = self.base_path / "checkpoints"
        for checkpoint_file in checkpoints_dir.glob("*.json"):
            if checkpoint_file.name == "index.json":
                continue
            if checkpoint_file.stat().st_mtime < cutoff:
                checkpoint_file.unlink()
                stats["checkpoints"] += 1
        
        # 清理日志
        logs_dir = self.base_path / "logs"
        for log_file in logs_dir.glob("*.jsonl"):
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                stats["logs"] += 1
        
        return stats
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        info = {
            "storage_type": self.storage_type,
            "memory_states": len(self._memory_states),
            "memory_checkpoints": len(self._memory_checkpoints),
            "memory_logs": len(self._memory_logs)
        }
        
        if self.storage_type == StorageType.JSON_FILE.value:
            info["path"] = str(self.base_path)
            
            # 计算文件数量
            states_count = len(list((self.base_path / "states").glob("*.json"))) if (self.base_path / "states").exists() else 0
            checkpoints_count = len(list((self.base_path / "checkpoints").glob("*.json"))) if (self.base_path / "checkpoints").exists() else 0
            logs_count = len(list((self.base_path / "logs").glob("*.jsonl"))) if (self.base_path / "logs").exists() else 0
            
            info["states_files"] = states_count
            info["checkpoints_files"] = checkpoints_count
            info["logs_files"] = logs_count
            
            # 计算大小
            total_size = 0
            for path in [self.base_path / "states", self.base_path / "checkpoints", self.base_path / "logs"]:
                if path.exists():
                    for f in path.rglob("*"):
                        total_size += f.stat().st_size
            
            info["total_size_bytes"] = total_size
            info["total_size_mb"] = total_size / 1024 / 1024
        
        return info
    
    def export_execution(
        self,
        execution_id: str,
        include_logs: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        导出执行完整数据
        
        Args:
            execution_id: 执行ID
            include_logs: 是否包含日志
            
        Returns:
            导出的数据
        """
        state = self.load_state(execution_id)
        if not state:
            return None
        
        checkpoint = self.get_latest_checkpoint(execution_id)
        logs = self.load_logs(execution_id) if include_logs else []
        
        return {
            "execution_id": execution_id,
            "state": state.to_dict() if state else None,
            "checkpoint": checkpoint.to_dict() if checkpoint else None,
            "logs": [log.to_dict() for log in logs],
            "exported_at": datetime.now().isoformat()
        }


# 全局实例
_execution_storage = None


def get_execution_storage(
    storage_type: str = StorageType.JSON_FILE.value,
    base_path: str = "/tmp/po-agent/executions"
) -> ExecutionStorage:
    """获取执行存储实例"""
    global _execution_storage
    if _execution_storage is None:
        _execution_storage = ExecutionStorage(storage_type, base_path)
    return _execution_storage
