"""任务调度器 - 定时任务与工作流调度"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4
import heapq
import threading
import time


class ScheduleType(Enum):
    """调度类型"""
    ONCE = "once"               # 单次执行
    RECURRING = "recurring"     # 循环执行
    CRON = "cron"               # Cron 表达式
    DELAYED = "delayed"         # 延迟执行
    DEPENDENT = "dependent"     # 依赖执行


class ScheduleStatus(Enum):
    """调度状态"""
    PENDING = "pending"         # 等待执行
    SCHEDULED = "scheduled"    # 已调度
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    CANCELLED = "cancelled"     # 已取消
    FAILED = "failed"          # 失败


@dataclass
class Schedule:
    """调度计划"""
    schedule_id: str
    name: str
    task_id: str
    idea_id: str
    
    # 调度类型
    schedule_type: str = ScheduleType.ONCE.value
    
    # 时间配置
    run_at: str = ""           # 计划执行时间 (ISO格式)
    end_at: str = ""           # 结束时间
    interval_seconds: int = 0  # 循环间隔（秒）
    
    # Cron 配置（可选）
    cron_expression: str = ""
    
    # 依赖配置
    depends_on: List[str] = field(default_factory=list)  # 依赖的调度ID
    
    # 状态
    status: str = ScheduleStatus.PENDING.value
    
    # 执行统计
    run_count: int = 0
    last_run_at: str = ""
    next_run_at: str = ""
    success_count: int = 0
    failure_count: int = 0
    
    # 配置
    max_retries: int = 3
    timeout_seconds: int = 3600
    
    # 元数据
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.schedule_id:
            self.schedule_id = str(uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schedule":
        return cls(**data)
    
    def should_run(self) -> bool:
        """检查是否应该执行"""
        if self.status == ScheduleStatus.CANCELLED.value:
            return False
        if self.status == ScheduleStatus.COMPLETED.value and self.schedule_type == ScheduleType.ONCE.value:
            return False
        
        if not self.next_run_at:
            return True
        
        now = datetime.now()
        next_run = datetime.fromisoformat(self.next_run_at)
        return now >= next_run
    
    def calculate_next_run(self):
        """计算下次执行时间"""
        if self.schedule_type == ScheduleType.ONCE.value:
            self.next_run_at = self.run_at
        elif self.schedule_type == ScheduleType.RECURRING.value:
            if self.last_run_at:
                last = datetime.fromisoformat(self.last_run_at)
                self.next_run_at = (last + timedelta(seconds=self.interval_seconds)).isoformat()
            else:
                self.next_run_at = self.run_at or datetime.now().isoformat()
        elif self.schedule_type == ScheduleType.DELAYED.value:
            self.next_run_at = (datetime.now() + timedelta(seconds=self.interval_seconds)).isoformat()
    
    def mark_run(self, success: bool):
        """标记执行结果"""
        self.run_count += 1
        self.last_run_at = datetime.now().isoformat()
        
        if success:
            self.success_count += 1
            self.status = ScheduleStatus.COMPLETED.value if self.schedule_type == ScheduleType.ONCE.value else ScheduleStatus.SCHEDULED.value
        else:
            self.failure_count += 1
            if self.failure_count >= self.max_retries:
                self.status = ScheduleStatus.FAILED.value
        
        self.calculate_next_run()
        self.updated_at = datetime.now().isoformat()


@dataclass
class ScheduledJob:
    """调度的作业（用于堆排序）"""
    schedule: Schedule
    priority: float = 0  # 优先级（越小越先执行）
    
    def __lt__(self, other):
        return self.priority < other.priority


class Scheduler:
    """
    任务调度器
    
    负责任务的定时调度、循环执行和工作流编排
    """
    
    def __init__(self):
        # 调度队列（按执行时间排序）
        self._schedule_queue: List[ScheduledJob] = []
        
        # 所有调度
        self._schedules: Dict[str, Schedule] = {}
        
        # 运行中的调度
        self._running: Dict[str, Schedule] = {}
        
        # 调度锁
        self._lock = threading.Lock()
        
        # 调度器状态
        self._running_state = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self._callbacks: Dict[str, List[Callable]] = {
            "on_schedule": [],
            "on_execute": [],
            "on_complete": [],
            "on_error": [],
            "on_cancel": []
        }
    
    # ==================== 调度管理 ====================
    
    def schedule_task(
        self,
        task_id: str,
        idea_id: str,
        name: str,
        run_at: str = None,
        schedule_type: str = ScheduleType.ONCE.value,
        interval_seconds: int = 0,
        cron_expression: str = "",
        depends_on: List[str] = None
    ) -> Schedule:
        """
        创建调度任务
        
        Args:
            task_id: 任务ID
            idea_id: 想法ID
            name: 调度名称
            run_at: 执行时间（ISO格式）
            schedule_type: 调度类型
            interval_seconds: 循环间隔
            cron_expression: Cron 表达式
            depends_on: 依赖的调度
            
        Returns:
            创建的调度对象
        """
        schedule = Schedule(
            schedule_id=str(uuid4())[:8],
            name=name,
            task_id=task_id,
            idea_id=idea_id,
            schedule_type=schedule_type,
            run_at=run_at or datetime.now().isoformat(),
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            depends_on=depends_on or []
        )
        
        # 计算下次执行时间
        schedule.calculate_next_run()
        schedule.status = ScheduleStatus.SCHEDULED.value
        
        # 添加到调度器
        with self._lock:
            self._schedules[schedule.schedule_id] = schedule
            self._add_to_queue(schedule)
        
        # 触发回调
        self._trigger_callback("on_schedule", schedule)
        
        return schedule
    
    def cancel_schedule(self, schedule_id: str) -> bool:
        """取消调度"""
        with self._lock:
            if schedule_id not in self._schedules:
                return False
            
            schedule = self._schedules[schedule_id]
            schedule.status = ScheduleStatus.CANCELLED.value
            
            # 从队列中移除
            self._schedule_queue = [
                j for j in self._schedule_queue
                if j.schedule.schedule_id != schedule_id
            ]
            
            self._trigger_callback("on_cancel", schedule)
            return True
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """获取调度"""
        return self._schedules.get(schedule_id)
    
    def list_schedules(
        self,
        idea_id: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[Schedule]:
        """列出调度"""
        schedules = list(self._schedules.values())
        
        if idea_id:
            schedules = [s for s in schedules if s.idea_id == idea_id]
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        # 按创建时间倒序
        schedules.sort(key=lambda x: x.created_at, reverse=True)
        return schedules[:limit]
    
    def update_schedule(self, schedule_id: str, **kwargs) -> Optional[Schedule]:
        """更新调度"""
        with self._lock:
            if schedule_id not in self._schedules:
                return None
            
            schedule = self._schedules[schedule_id]
            
            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            
            schedule.updated_at = datetime.now().isoformat()
            
            # 重新添加到队列
            if schedule.status == ScheduleStatus.SCHEDULED.value:
                self._schedule_queue = [
                    j for j in self._schedule_queue
                    if j.schedule.schedule_id != schedule_id
                ]
                self._add_to_queue(schedule)
            
            return schedule
    
    # ==================== 执行控制 ====================
    
    def start(self):
        """启动调度器"""
        if self._running_state:
            return
        
        self._running_state = True
        self._scheduler_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._scheduler_thread.start()
    
    def stop(self):
        """停止调度器"""
        self._running_state = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
    
    def _run_loop(self):
        """调度循环"""
        while self._running_state:
            try:
                self._process_due_schedules()
            except Exception as e:
                print(f"调度器错误: {e}")
            
            # 休眠直到下次检查
            time.sleep(1)
    
    def _process_due_schedules(self):
        """处理到期的调度"""
        with self._lock:
            now = datetime.now()
            
            # 获取所有到期的调度
            due_schedules = []
            while self._schedule_queue:
                job = heapq.heappop(self._schedule_queue)
                
                if job.schedule.should_run():
                    due_schedules.append(job.schedule)
                else:
                    # 放回队列（时间未到）
                    heapq.heappush(self._schedule_queue, job)
                    break
            
            # 按优先级排序
            due_schedules.sort(key=lambda s: s.priority if hasattr(s, 'priority') else 0)
            
            # 执行到期调度
            for schedule in due_schedules:
                self._execute_schedule(schedule)
    
    def _execute_schedule(self, schedule: Schedule):
        """执行调度"""
        # 检查依赖
        if schedule.depends_on:
            for dep_id in schedule.depends_on:
                dep_schedule = self._schedules.get(dep_id)
                if not dep_schedule or dep_schedule.status != ScheduleStatus.COMPLETED.value:
                    # 依赖未完成，延迟执行
                    schedule.calculate_next_run()
                    heapq.heappush(self._schedule_queue, ScheduledJob(schedule))
                    return
        
        # 标记为运行中
        schedule.status = ScheduleStatus.RUNNING.value
        self._running[schedule.schedule_id] = schedule
        
        # 触发执行回调
        self._trigger_callback("on_execute", schedule)
    
    def complete_schedule(self, schedule_id: str, success: bool = True):
        """标记调度完成"""
        with self._lock:
            if schedule_id not in self._running:
                return
            
            schedule = self._running.pop(schedule_id)
            schedule.mark_run(success)
            
            if success:
                self._trigger_callback("on_complete", schedule)
            else:
                self._trigger_callback("on_error", schedule)
            
            # 如果是循环调度，重新加入队列
            if schedule.schedule_type in [ScheduleType.RECURRING.value, ScheduleType.CRON.value]:
                if schedule.status == ScheduleStatus.SCHEDULED.value:
                    self._add_to_queue(schedule)
    
    def _add_to_queue(self, schedule: Schedule):
        """添加调度到队列"""
        if not schedule.next_run_at:
            schedule.calculate_next_run()
        
        priority = 0
        if schedule.next_run_at:
            next_run = datetime.fromisoformat(schedule.next_run_at)
            priority = next_run.timestamp()
        
        job = ScheduledJob(schedule=schedule, priority=priority)
        heapq.heappush(self._schedule_queue, job)
    
    # ==================== 便捷方法 ====================
    
    def schedule_once(
        self,
        task_id: str,
        idea_id: str,
        name: str,
        run_at: str = None
    ) -> Schedule:
        """单次调度"""
        return self.schedule_task(
            task_id=task_id,
            idea_id=idea_id,
            name=name,
            run_at=run_at,
            schedule_type=ScheduleType.ONCE.value
        )
    
    def schedule_recurring(
        self,
        task_id: str,
        idea_id: str,
        name: str,
        interval_seconds: int,
        start_at: str = None
    ) -> Schedule:
        """循环调度"""
        return self.schedule_task(
            task_id=task_id,
            idea_id=idea_id,
            name=name,
            run_at=start_at,
            schedule_type=ScheduleType.RECURRING.value,
            interval_seconds=interval_seconds
        )
    
    def schedule_delayed(
        self,
        task_id: str,
        idea_id: str,
        name: str,
        delay_seconds: int
    ) -> Schedule:
        """延迟调度"""
        return self.schedule_task(
            task_id=task_id,
            idea_id=idea_id,
            name=name,
            schedule_type=ScheduleType.DELAYED.value,
            interval_seconds=delay_seconds
        )
    
    def schedule_dependent(
        self,
        task_id: str,
        idea_id: str,
        name: str,
        depends_on: List[str]
    ) -> Schedule:
        """依赖调度"""
        return self.schedule_task(
            task_id=task_id,
            idea_id=idea_id,
            name=name,
            schedule_type=ScheduleType.DEPENDENT.value,
            depends_on=depends_on
        )
    
    # ==================== 回调管理 ====================
    
    def add_callback(self, event: str, callback: Callable):
        """添加回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """移除回调"""
        if event in self._callbacks:
            self._callbacks[event].remove(callback)
    
    def _trigger_callback(self, event: str, *args):
        """触发回调"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args)
                except Exception as e:
                    print(f"调度器回调错误 ({event}): {e}")
    
    # ==================== 查询接口 ====================
    
    def get_upcoming_schedules(self, limit: int = 10) -> List[Schedule]:
        """获取即将执行的调度"""
        schedules = []
        for job in self._schedule_queue:
            if job.schedule.status == ScheduleStatus.SCHEDULED.value:
                schedules.append(job.schedule)
        
        schedules.sort(key=lambda s: s.next_run_at or "")
        return schedules[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._schedules)
        by_status = {}
        for s in self._schedules.values():
            by_status[s.status] = by_status.get(s.status, 0) + 1
        
        total_runs = sum(s.run_count for s in self._schedules.values())
        success_rate = (
            sum(s.success_count for s in self._schedules.values()) / total_runs
            if total_runs > 0 else 0
        )
        
        return {
            "total_schedules": total,
            "schedules_by_status": by_status,
            "running_count": len(self._running),
            "queue_size": len(self._schedule_queue),
            "total_runs": total_runs,
            "success_rate": success_rate
        }


# 工作流调度器 - 支持复杂的工作流编排
class WorkflowScheduler:
    """
    工作流调度器
    
    支持任务的串行、并行、条件分支等复杂编排
    """
    
    def __init__(self, scheduler: Scheduler = None):
        self.scheduler = scheduler or get_scheduler()
        
        # 工作流定义
        self._workflows: Dict[str, Dict[str, Any]] = {}
    
    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        创建工作流
        
        Args:
            workflow_id: 工作流ID
            name: 工作流名称
            steps: 工作流步骤定义
                [
                    {"id": "step1", "type": "task", "task_id": "xxx", "next": "step2"},
                    {"id": "step2", "type": "task", "task_id": "yyy", "next": None},
                    {"id": "step3", "type": "parallel", "tasks": ["a", "b"], "next": "step4"},
                    {"id": "step4", "type": "condition", "condition": "x > 0", "true_next": "step5", "false_next": None},
                ]
        """
        workflow = {
            "workflow_id": workflow_id,
            "name": name,
            "steps": steps,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
        self._workflows[workflow_id] = workflow
        return workflow
    
    def execute_workflow(
        self,
        workflow_id: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            context: 执行上下文
            
        Returns:
            执行结果
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        workflow = self._workflows[workflow_id]
        workflow["status"] = "running"
        context = context or {}
        context["workflow_id"] = workflow_id
        
        results = {}
        current_step = workflow["steps"][0] if workflow["steps"] else None
        
        try:
            while current_step:
                step_id = current_step["id"]
                step_type = current_step.get("type", "task")
                
                # 执行步骤
                step_result = self._execute_step(current_step, context)
                results[step_id] = step_result
                
                # 根据类型决定下一步
                if step_type == "condition":
                    # 条件分支
                    if step_result.get("result"):
                        current_step = self._find_step(workflow, current_step.get("true_next"))
                    else:
                        current_step = self._find_step(workflow, current_step.get("false_next"))
                elif step_type == "parallel":
                    # 并行执行
                    current_step = self._find_step(workflow, current_step.get("next"))
                else:
                    # 普通步骤
                    current_step = self._find_step(workflow, current_step.get("next"))
            
            workflow["status"] = "completed"
            return {"success": True, "results": results}
            
        except Exception as e:
            workflow["status"] = "failed"
            return {"success": False, "error": str(e), "results": results}
    
    def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        step_type = step.get("type", "task")
        
        if step_type == "task":
            # 执行任务
            return {"step_id": step["id"], "result": "task_executed"}
        elif step_type == "parallel":
            # 并行执行多个任务
            return {"step_id": step["id"], "result": "parallel_completed", "sub_results": []}
        elif step_type == "condition":
            # 条件判断
            return {"step_id": step["id"], "result": True}
        elif step_type == "delay":
            # 延迟
            return {"step_id": step["id"], "result": "delayed"}
        else:
            return {"step_id": step["id"], "result": "unknown_step_type"}
    
    def _find_step(self, workflow: Dict, step_id: str) -> Optional[Dict]:
        """查找步骤"""
        if not step_id:
            return None
        for step in workflow["steps"]:
            if step["id"] == step_id:
                return step
        return None


# 全局实例
_scheduler = None


def get_scheduler() -> Scheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
