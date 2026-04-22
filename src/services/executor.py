"""执行引擎 - 任务执行与调度核心"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from uuid import uuid4
import json


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"           # 等待执行
    READY = "ready"              # 准备就绪
    RUNNING = "running"          # 执行中
    PAUSED = "paused"            # 暂停
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 取消


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"    # 串行执行
    PARALLEL = "parallel"        # 并行执行
    CONDITIONAL = "conditional"  # 条件执行


@dataclass
class ExecutionContext:
    """执行上下文"""
    execution_id: str
    task_id: str
    idea_id: str
    
    # 状态
    status: str = ExecutionStatus.PENDING.value
    mode: str = ExecutionMode.SEQUENTIAL.value
    
    # 时间
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    paused_at: str = ""
    
    # 执行信息
    current_step: int = 0
    total_steps: int = 0
    progress: int = 0
    
    # 检查点（用于恢复）
    checkpoint: Dict[str, Any] = field(default_factory=dict)
    
    # 日志
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    # 错误信息
    error_message: str = ""
    retry_count: int = 0
    
    # 回调
    on_progress: Optional[str] = None  # 进度回调函数名
    on_complete: Optional[str] = None  # 完成回调函数名
    
    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = str(uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        return cls(**data)
    
    def add_log(self, level: str, message: str, data: Dict[str, Any] = None):
        """添加执行日志"""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        })
    
    def create_checkpoint(self) -> Dict[str, Any]:
        """创建检查点"""
        self.checkpoint = {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "current_step": self.current_step,
            "status": self.status,
            "created_at": self.created_at,
            "checkpoint_time": datetime.now().isoformat()
        }
        return self.checkpoint
    
    def update_progress(self, step: int, total: int):
        """更新进度"""
        self.current_step = step
        self.total_steps = total
        self.progress = int(step / total * 100) if total > 0 else 0
        self.add_log("info", f"进度更新: {self.progress}% ({step}/{total})")


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    execution_id: str
    task_id: str
    
    # 输出
    output: Any = None
    error: str = ""
    
    # 统计
    duration_seconds: float = 0.0
    steps_executed: int = 0
    
    # 详细信息
    details: Dict[str, Any] = field(default_factory=dict)
    
    # 生成的产物
    artifacts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def format_summary(self) -> str:
        """格式化摘要"""
        status_emoji = "✅" if self.success else "❌"
        lines = [
            f"{status_emoji} 执行{'成功' if self.success else '失败'}",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"执行ID: {self.execution_id}",
            f"任务ID: {self.task_id}",
            f"耗时: {self.duration_seconds:.2f}秒",
            f"执行步骤: {self.steps_executed}",
        ]
        
        if self.error:
            lines.append(f"错误: {self.error}")
        
        if self.artifacts:
            lines.append(f"\n📦 产物:")
            for artifact in self.artifacts:
                lines.append(f"  • {artifact}")
        
        return "\n".join(lines)


class ExecutionStep:
    """执行步骤基类"""
    
    def __init__(self, step_id: str, name: str, task: "Task"):
        self.step_id = step_id
        self.name = name
        self.task = task
    
    def can_execute(self, context: ExecutionContext) -> bool:
        """检查是否可以执行"""
        return True
    
    def execute(self, context: ExecutionContext) -> Any:
        """执行步骤"""
        raise NotImplementedError
    
    def rollback(self, context: ExecutionContext):
        """回滚步骤"""
        pass
    
    def get_estimated_duration(self) -> float:
        """预估执行时长（秒）"""
        return 60.0


class Executor:
    """
    执行引擎核心
    
    负责任务的执行、调度和状态管理
    """
    
    def __init__(self, max_retries: int = 3, default_timeout: int = 3600):
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        
        # 执行中的任务
        self._running_executions: Dict[str, ExecutionContext] = {}
        
        # 执行历史
        self._execution_history: List[ExecutionResult] = []
        
        # 步骤注册表
        self._step_registry: Dict[str, type] = {}
        
        # 钩子函数
        self._hooks: Dict[str, List[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_error": [],
            "on_progress": [],
            "on_complete": []
        }
    
    # ==================== 步骤注册 ====================
    
    def register_step(self, step_type: str, step_class: type):
        """注册执行步骤类型"""
        self._step_registry[step_type] = step_class
    
    def create_step(self, step_type: str, step_id: str, name: str, task: "Task") -> ExecutionStep:
        """创建执行步骤"""
        if step_type not in self._step_registry:
            # 默认使用通用步骤
            return GenericExecutionStep(step_id, name, task, step_type)
        
        return self._step_registry[step_type](step_id, name, task)
    
    # ==================== 执行控制 ====================
    
    def execute(
        self,
        task: "Task",
        idea_id: str,
        mode: str = ExecutionMode.SEQUENTIAL.value,
        steps: List[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务对象
            idea_id: 想法ID
            mode: 执行模式
            steps: 自定义步骤列表
            
        Returns:
            执行结果
        """
        # 创建执行上下文
        context = ExecutionContext(
            execution_id=str(uuid4())[:8],
            task_id=task.id,
            idea_id=idea_id,
            mode=mode
        )
        
        # 保存到运行中列表
        self._running_executions[context.execution_id] = context
        
        # 触发前钩子
        self._trigger_hook("before_execute", context)
        
        try:
            # 准备步骤
            if steps is None:
                steps = self._default_steps(task)
            
            context.total_steps = len(steps)
            context.status = ExecutionStatus.RUNNING.value
            context.started_at = datetime.now().isoformat()
            
            # 执行步骤
            start_time = datetime.now()
            output = None
            
            for i, step_config in enumerate(steps):
                context.update_progress(i + 1, len(steps))
                
                # 创建步骤
                step = self.create_step(
                    step_config.get("type", "generic"),
                    step_config.get("id", f"step_{i}"),
                    step_config.get("name", f"步骤{i+1}"),
                    task
                )
                
                # 检查前置条件
                if not step.can_execute(context):
                    context.add_log("warning", f"步骤 {step.name} 跳过（前置条件不满足）")
                    continue
                
                # 执行步骤
                context.add_log("info", f"开始执行: {step.name}")
                step_output = step.execute(context)
                
                if output is None:
                    output = step_output
                
                # 检查是否有检查点
                if step_config.get("checkpoint"):
                    context.create_checkpoint()
                    self._save_checkpoint(context)
                
                # 触发进度钩子
                self._trigger_hook("on_progress", context, step)
            
            # 计算耗时
            duration = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            result = ExecutionResult(
                success=True,
                execution_id=context.execution_id,
                task_id=task.id,
                output=output,
                duration_seconds=duration,
                steps_executed=len(steps),
                details={"context": context.to_dict()}
            )
            
            context.status = ExecutionStatus.COMPLETED.value
            context.completed_at = datetime.now().isoformat()
            
            self._trigger_hook("on_complete", result)
            
            return result
            
        except Exception as e:
            context.status = ExecutionStatus.FAILED.value
            context.error_message = str(e)
            context.add_log("error", f"执行失败: {str(e)}")
            
            # 尝试回滚
            self._attempt_rollback(context)
            
            result = ExecutionResult(
                success=False,
                execution_id=context.execution_id,
                task_id=task.id,
                error=str(e),
                details={"context": context.to_dict()}
            )
            
            self._trigger_hook("on_error", result, e)
            return result
        
        finally:
            # 从运行中移除
            if context.execution_id in self._running_executions:
                del self._running_executions[context.execution_id]
            
            # 添加到历史
            self._execution_history.append(result)
    
    def pause(self, execution_id: str) -> bool:
        """暂停执行"""
        if execution_id not in self._running_executions:
            return False
        
        context = self._running_executions[execution_id]
        context.status = ExecutionStatus.PAUSED.value
        context.paused_at = datetime.now().isoformat()
        context.create_checkpoint()
        self._save_checkpoint(context)
        
        return True
    
    def resume(self, execution_id: str) -> ExecutionResult:
        """恢复执行"""
        checkpoint = self._load_checkpoint(execution_id)
        if not checkpoint:
            raise ValueError(f"无法找到执行 {execution_id} 的检查点")
        
        # 从检查点恢复上下文
        context = ExecutionContext.from_dict(checkpoint.get("context_data", checkpoint))
        context.status = ExecutionStatus.RUNNING.value
        
        self._running_executions[execution_id] = context
        
        # 继续执行剩余步骤...
        # TODO: 实现真正的恢复逻辑
        
        return ExecutionResult(
            success=True,
            execution_id=execution_id,
            task_id=context.task_id,
            details={"resumed_from_checkpoint": True}
        )
    
    def cancel(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self._running_executions:
            context = self._running_executions[execution_id]
            context.status = ExecutionStatus.CANCELLED.value
            context.completed_at = datetime.now().isoformat()
            context.add_log("info", "执行已取消")
            
            del self._running_executions[execution_id]
            return True
        return False
    
    def retry(self, execution_id: str) -> ExecutionResult:
        """重试执行"""
        if execution_id not in self._running_executions:
            raise ValueError(f"执行 {execution_id} 不在运行中")
        
        context = self._running_executions[execution_id]
        context.retry_count += 1
        
        if context.retry_count > self.max_retries:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                task_id=context.task_id,
                error=f"超过最大重试次数 ({self.max_retries})"
            )
        
        # 重新执行
        context.status = ExecutionStatus.READY.value
        return self.execute_from_context(context)
    
    # ==================== 执行编排 ====================
    
    def execute_parallel(
        self,
        tasks: List["Task"],
        idea_id: str,
        max_concurrent: int = 3
    ) -> List[ExecutionResult]:
        """
        并行执行多个任务
        
        Args:
            tasks: 任务列表
            idea_id: 想法ID
            max_concurrent: 最大并发数
            
        Returns:
            执行结果列表
        """
        results = []
        
        # 按依赖关系分组
        independent_tasks = []
        dependent_groups = []
        
        for task in tasks:
            if task.depends_on:
                dependent_groups.append(task)
            else:
                independent_tasks.append(task)
        
        # 先执行独立任务（分组并行）
        for i in range(0, len(independent_tasks), max_concurrent):
            batch = independent_tasks[i:i + max_concurrent]
            batch_results = [self.execute(t, idea_id) for t in batch]
            results.extend(batch_results)
        
        # 再执行有依赖的任务
        for task in dependent_groups:
            # 检查依赖是否都完成
            # TODO: 实现依赖检查
            result = self.execute(task, idea_id)
            results.append(result)
        
        return results
    
    def execute_conditional(
        self,
        task: "Task",
        idea_id: str,
        condition_fn: Callable[[ExecutionContext], bool],
        true_branch: List[Dict[str, Any]],
        false_branch: List[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        条件执行
        
        Args:
            task: 任务
            idea_id: 想法ID
            condition_fn: 条件函数
            true_branch: 条件为真时执行的步骤
            false_branch: 条件为假时执行的步骤
            
        Returns:
            执行结果
        """
        # 创建临时上下文用于条件判断
        temp_context = ExecutionContext(
            execution_id=str(uuid4())[:8],
            task_id=task.id,
            idea_id=idea_id
        )
        
        # 判断条件
        if condition_fn(temp_context):
            steps = true_branch
            temp_context.add_log("info", "条件判断: True")
        else:
            steps = false_branch or []
            temp_context.add_log("info", "条件判断: False")
        
        return self.execute(task, idea_id, mode=ExecutionMode.CONDITIONAL.value, steps=steps)
    
    # ==================== 钩子系统 ====================
    
    def add_hook(self, event: str, callback: Callable):
        """添加钩子函数"""
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    def remove_hook(self, event: str, callback: Callable):
        """移除钩子函数"""
        if event in self._hooks:
            self._hooks[event].remove(callback)
    
    def _trigger_hook(self, event: str, *args, **kwargs):
        """触发钩子"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"钩子执行错误 ({event}): {e}")
    
    # ==================== 辅助方法 ====================
    
    def _default_steps(self, task: "Task") -> List[Dict[str, Any]]:
        """生成默认执行步骤"""
        steps = []
        
        # 如果有子任务，逐个执行
        if task.subtasks:
            for i, subtask in enumerate(task.subtasks):
                steps.append({
                    "id": f"subtask_{i}",
                    "name": subtask.title,
                    "type": "subtask"
                })
        else:
            # 默认单一执行步骤
            steps.append({
                "id": "main",
                "name": task.title,
                "type": "main"
            })
        
        return steps
    
    def _attempt_rollback(self, context: ExecutionContext):
        """尝试回滚"""
        context.add_log("warning", "开始回滚...")
        # TODO: 实现回滚逻辑
    
    def _save_checkpoint(self, context: ExecutionContext):
        """保存检查点"""
        checkpoint_path = f"/tmp/checkpoint_{context.execution_id}.json"
        with open(checkpoint_path, "w") as f:
            json.dump(context.to_dict(), f, indent=2)
        context.add_log("info", f"检查点已保存: {checkpoint_path}")
    
    def _load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        checkpoint_path = f"/tmp/checkpoint_{execution_id}.json"
        try:
            with open(checkpoint_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    # ==================== 查询接口 ====================
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        """获取执行上下文"""
        return self._running_executions.get(execution_id)
    
    def get_execution_history(
        self,
        task_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ExecutionResult]:
        """获取执行历史"""
        results = self._execution_history
        
        if task_id:
            results = [r for r in results if r.task_id == task_id]
        
        return sorted(results, key=lambda x: x.execution_id, reverse=True)[:limit]
    
    def get_running_executions(self) -> List[ExecutionContext]:
        """获取所有运行中的执行"""
        return list(self._running_executions.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = len(self._execution_history)
        success = sum(1 for r in self._execution_history if r.success)
        failed = total - success
        
        return {
            "total_executions": total,
            "success_count": success,
            "failed_count": failed,
            "success_rate": success / total if total > 0 else 0,
            "running_count": len(self._running_executions),
            "average_duration": sum(r.duration_seconds for r in self._execution_history) / total if total > 0 else 0
        }


class GenericExecutionStep(ExecutionStep):
    """通用执行步骤"""
    
    def __init__(self, step_id: str, name: str, task: "Task", step_type: str = "generic"):
        super().__init__(step_id, name, task)
        self.step_type = step_type
    
    def execute(self, context: ExecutionContext) -> Any:
        """执行通用步骤"""
        context.add_log("info", f"执行通用步骤: {self.name}")
        # 这里应该调用实际的执行逻辑
        # 实际使用时会被具体的执行器实现覆盖
        return {"step_id": self.step_id, "status": "completed"}


# 全局实例
_executor = None


def get_executor() -> Executor:
    """获取执行器实例"""
    global _executor
    if _executor is None:
        _executor = Executor()
    return _executor
