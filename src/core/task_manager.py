"""任务管理器"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.task import Task, SubTask
from ..storage.base import BaseStorage


class TaskManager:
    """任务全生命周期管理"""
    
    def __init__(self, storage: BaseStorage):
        self.storage = storage
        self._tasks: List[Task] = []
        self._load()
    
    def _load(self):
        """加载数据"""
        data = self.storage.load_tasks()
        self._tasks = [Task.from_dict(d) for d in data]
    
    def _save(self) -> bool:
        """保存数据"""
        data = [task.to_dict() for task in self._tasks]
        return self.storage.save_tasks(data)
    
    def create(self, idea_id: str, title: str,
               description: str = "",
               task_type: str = "general",
               priority: int = 3,
               estimated_hours: float = 1.0) -> Task:
        """创建任务"""
        now = datetime.now().isoformat()
        task = Task(
            id=str(uuid.uuid4())[:8],
            idea_id=idea_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            created_at=now,
            updated_at=now,
            estimated_hours=estimated_hours
        )
        
        self._tasks.append(task)
        self._save()
        
        return task
    
    def list(self, idea_id: Optional[str] = None,
             status: Optional[str] = None,
             limit: int = 50) -> List[Task]:
        """列出任务"""
        results = self._tasks
        
        if idea_id:
            results = [t for t in results if t.idea_id == idea_id]
        
        if status:
            results = [t for t in results if t.status == status]
        
        # 按优先级和创建时间排序
        results = sorted(results, key=lambda x: (x.priority, x.created_at))
        
        return results[:limit]
    
    def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None
    
    def update(self, task_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """更新任务"""
        task = self.get(task_id)
        if not task:
            return None
        
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now().isoformat()
        task.update_progress()
        self._save()
        
        return task
    
    def start(self, task_id: str) -> Optional[Task]:
        """开始任务"""
        task = self.get(task_id)
        if not task:
            return None
        
        task.status = "IN_PROGRESS"
        task.started_at = datetime.now().isoformat()
        task.updated_at = datetime.now().isoformat()
        self._save()
        
        return task
    
    def done(self, task_id: str) -> Optional[Task]:
        """完成任务"""
        task = self.get(task_id)
        if not task:
            return None
        
        task.status = "DONE"
        task.completed_at = datetime.now().isoformat()
        task.progress = 100
        task.updated_at = datetime.now().isoformat()
        self._save()
        
        return task
    
    def block(self, task_id: str, reason: str) -> Optional[Task]:
        """阻塞任务"""
        return self.update(task_id, {
            "status": "BLOCKED",
            "block_reason": reason
        })
    
    def unblock(self, task_id: str) -> Optional[Task]:
        """解除阻塞"""
        task = self.get(task_id)
        if not task:
            return None
        
        task.status = "TODO"
        task.block_reason = ""
        task.updated_at = datetime.now().isoformat()
        self._save()
        
        return task
    
    def delete(self, task_id: str) -> bool:
        """删除任务"""
        for i, task in enumerate(self._tasks):
            if task.id == task_id:
                self._tasks.pop(i)
                self._save()
                return True
        return False
    
    def add_subtask(self, task_id: str, title: str) -> Optional[Task]:
        """添加子任务"""
        task = self.get(task_id)
        if not task:
            return None
        
        subtask = SubTask(
            title=title,
            id=str(uuid.uuid4())[:8]
        )
        task.subtasks.append(subtask)
        task.update_progress()
        self._save()
        
        return task
    
    def toggle_subtask(self, task_id: str, subtask_id: str) -> Optional[Task]:
        """切换子任务状态"""
        task = self.get(task_id)
        if not task:
            return None
        
        for st in task.subtasks:
            if st.id == subtask_id:
                st.done = not st.done
                task.update_progress()
                self._save()
                break
        
        return task
    
    def get_by_idea(self, idea_id: str) -> List[Task]:
        """获取想法关联的任务"""
        return self.list(idea_id=idea_id)
    
    def get_blocked(self) -> List[Task]:
        """获取阻塞的任务"""
        return [t for t in self._tasks if t.status == "BLOCKED"]
    
    def get_overdue(self) -> List[Task]:
        """获取逾期的任务"""
        overdue = []
        now = datetime.now()
        for task in self._tasks:
            if task.due_date and task.status not in ["DONE", "CANCELLED"]:
                due = datetime.fromisoformat(task.due_date)
                if due < now:
                    overdue.append(task)
        return overdue
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        total = len(self._tasks)
        by_status = {}
        by_type = {}
        
        for task in self._tasks:
            by_status[task.status] = by_status.get(task.status, 0) + 1
            by_type[task.task_type] = by_type.get(task.task_type, 0) + 1
        
        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "blocked_count": len(self.get_blocked()),
            "overdue_count": len(self.get_overdue())
        }
