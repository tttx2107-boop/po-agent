"""任务执行 API 路由 - Phase 8 补全"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from ..core.task_manager import TaskManager
from ..core.idea_manager import IdeaManager
from ..storage.gist_store import get_storage
from ..services.executor import Executor, ExecutionResult, get_executor
from ..services.task_breaker import TaskBreaker, BreakdownResult
from ..utils.logger import setup_logger

logger = setup_logger("po-agent.routes.tasks")
router = APIRouter(prefix="/api/tasks", tags=["任务执行"])


def get_task_manager() -> TaskManager:
    """获取 TaskManager 实例"""
    storage = get_storage()
    return TaskManager(storage)


def get_idea_manager() -> IdeaManager:
    """获取 IdeaManager 实例"""
    storage = get_storage()
    return IdeaManager(storage)


# ==================== 请求/响应模型 ====================

class TaskBreakdownRequest(BaseModel):
    """任务拆解请求"""
    idea_content: str = Field(..., description="想法内容")
    idea_id: Optional[str] = Field(None, description="关联的想法ID")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="用户画像信息")


class TaskBreakdownResponse(BaseModel):
    """任务拆解响应"""
    subtasks: List[Dict[str, Any]]
    estimated_total_hours: float
    risk_notes: str
    success_criteria: str
    breakdown_time: str


class TaskCreateFromBreakdownRequest(BaseModel):
    """从拆解结果创建任务请求"""
    idea_id: str = Field(..., description="关联的想法ID")
    subtasks: List[Dict[str, Any]] = Field(..., description="子任务列表")


class TaskExecuteRequest(BaseModel):
    """任务执行请求"""
    task_id: str = Field(..., description="任务ID")
    steps: Optional[List[Dict[str, Any]]] = Field(None, description="自定义执行步骤")
    mode: str = Field("sequential", description="执行模式: sequential/parallel/conditional")


class TaskExecuteResponse(BaseModel):
    """任务执行响应"""
    success: bool
    execution_id: str
    task_id: str
    output: Any = None
    error: str = ""
    duration_seconds: float
    steps_executed: int
    artifacts: List[str] = []


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    idea_id: str
    title: str
    description: str
    task_type: str
    status: str
    priority: int
    progress: int
    created_at: str
    updated_at: str
    started_at: str
    completed_at: str
    due_date: str
    depends_on: List[str]
    subtasks: List[Dict[str, Any]]
    block_reason: str
    outputs: List[str]
    estimated_hours: float
    actual_hours: float


class ExecutionHistoryResponse(BaseModel):
    """执行历史响应"""
    results: List[Dict[str, Any]]
    total: int


def _task_to_response(task) -> TaskResponse:
    """Task 转响应模型"""
    return TaskResponse(
        id=task.id,
        idea_id=task.idea_id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        progress=task.progress,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        due_date=task.due_date,
        depends_on=task.depends_on,
        subtasks=[{"id": s.id, "title": s.title, "done": s.done} for s in task.subtasks],
        block_reason=task.block_reason,
        outputs=task.outputs,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours
    )


# ==================== API 端点 ====================

@router.post("/breakdown", response_model=TaskBreakdownResponse)
def breakdown_idea(
    request: TaskBreakdownRequest,
    task_manager: TaskManager = Depends(get_task_manager)
) -> TaskBreakdownResponse:
    """
    拆解想法为任务列表
    
    使用 TaskBreaker 将用户的想法智能拆解为可执行的具体任务
    支持用户画像参数，根据用户角色和产出目标定制任务拆解
    """
    breaker = TaskBreaker()
    result = breaker.breakdown(request.idea_content, user_profile=request.user_profile)
    
    return TaskBreakdownResponse(
        subtasks=[t.to_dict() for t in result.subtasks],
        estimated_total_hours=result.estimated_total_hours,
        risk_notes=result.risk_notes,
        success_criteria=result.success_criteria,
        breakdown_time=result.breakdown_time
    )


@router.post("/create-from-breakdown")
def create_tasks_from_breakdown(
    request: TaskCreateFromBreakdownRequest,
    task_manager: TaskManager = Depends(get_task_manager),
    idea_manager: IdeaManager = Depends(get_idea_manager)
) -> Dict[str, Any]:
    """
    从拆解结果创建任务
    
    将 TaskBreaker 的拆解结果批量创建为实际任务
    """
    # 验证想法存在
    idea = idea_manager.get(request.idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"想法 [{request.idea_id}] 不存在")
    
    created_tasks = []
    task_id_map = {}  # 用于记录原始索引到实际ID的映射
    
    for i, subtask_data in enumerate(request.subtasks):
        # 创建任务
        task = task_manager.create(
            idea_id=request.idea_id,
            title=subtask_data.get("title", f"任务 {i+1}"),
            description=subtask_data.get("description", ""),
            task_type=subtask_data.get("task_type", "general"),
            priority=subtask_data.get("priority", 2),
            estimated_hours=subtask_data.get("estimated_hours", 1.0)
        )
        created_tasks.append(task)
        task_id_map[f"task_{i}"] = task.id
    
    # 更新依赖关系
    for i, subtask_data in enumerate(request.subtasks):
        deps = subtask_data.get("dependencies", [])
        if deps:
            actual_deps = []
            for dep in deps:
                # 依赖可能是标题字符串或索引
                if dep in task_id_map:
                    actual_deps.append(task_id_map[dep])
                else:
                    # 尝试通过标题匹配
                    for t in created_tasks:
                        if t.title == dep or dep in t.title:
                            actual_deps.append(t.id)
                            break
            
            if actual_deps:
                task_manager.update(created_tasks[i].id, {"depends_on": actual_deps})
    
    # 更新想法状态为 IN_PROGRESS
    idea_manager.update_status(request.idea_id, "IN_PROGRESS")
    
    return {
        "success": True,
        "message": f"成功创建 {len(created_tasks)} 个任务",
        "tasks": [{"id": t.id, "title": t.title} for t in created_tasks],
        "idea_id": request.idea_id,
        "idea_status": "IN_PROGRESS"
    }


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    idea_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    task_manager: TaskManager = Depends(get_task_manager)
) -> List[TaskResponse]:
    """获取任务列表"""
    tasks = task_manager.list(idea_id=idea_id, status=status, limit=limit)
    return [_task_to_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> TaskResponse:
    """获取单个任务详情"""
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return _task_to_response(task)


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    updates: Dict[str, Any],
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """更新任务"""
    task = task_manager.update(task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "task": _task_to_response(task)}


@router.post("/{task_id}/start")
def start_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """开始任务"""
    task = task_manager.start(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "message": f"任务 [{task_id}] 已开始", "task": _task_to_response(task)}


@router.post("/{task_id}/done")
def complete_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """完成任务"""
    task = task_manager.done(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "message": f"任务 [{task_id}] 已完成", "task": _task_to_response(task)}


@router.post("/{task_id}/block")
def block_task(
    task_id: str,
    reason: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """阻塞任务"""
    task = task_manager.block(task_id, reason)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "message": f"任务 [{task_id}] 已阻塞", "task": _task_to_response(task)}


@router.post("/{task_id}/unblock")
def unblock_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """解除阻塞"""
    task = task_manager.unblock(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "message": f"任务 [{task_id}] 已解除阻塞", "task": _task_to_response(task)}


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """删除任务"""
    success = task_manager.delete(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "message": f"任务 [{task_id}] 已删除"}


@router.post("/{task_id}/execute", response_model=TaskExecuteResponse)
def execute_task(
    task_id: str,
    request: TaskExecuteRequest,
    task_manager: TaskManager = Depends(get_task_manager)
) -> TaskExecuteResponse:
    """
    执行任务
    
    使用 Executor 执行任务，支持自定义步骤和执行模式
    """
    # 获取任务
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    
    # 检查依赖
    if task.depends_on:
        for dep_id in task.depends_on:
            dep_task = task_manager.get(dep_id)
            if dep_task and dep_task.status != "DONE":
                raise HTTPException(
                    status_code=400,
                    detail=f"依赖任务 [{dep_id}] 尚未完成"
                )
    
    # 启动任务
    task_manager.start(task_id)
    
    # 获取 Executor
    executor = get_executor()
    
    # 执行
    try:
        result = executor.execute(
            task=task,
            idea_id=task.idea_id,
            mode=request.mode,
            steps=request.steps
        )
        
        # 更新任务状态
        if result.success:
            task_manager.done(task_id)
        else:
            task_manager.update(task_id, {"notes": f"执行失败: {result.error}"})
        
        return TaskExecuteResponse(
            success=result.success,
            execution_id=result.execution_id,
            task_id=result.task_id,
            output=result.output,
            error=result.error,
            duration_seconds=result.duration_seconds,
            steps_executed=result.steps_executed,
            artifacts=result.artifacts
        )
    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/subtasks/{subtask_id}/toggle")
def toggle_subtask(
    task_id: str,
    subtask_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """切换子任务状态"""
    task = task_manager.toggle_subtask(task_id, subtask_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "task": _task_to_response(task)}


@router.post("/{task_id}/subtasks")
def add_subtask(
    task_id: str,
    title: str,
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """添加子任务"""
    task = task_manager.add_subtask(task_id, title)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 [{task_id}] 不存在")
    return {"success": True, "task": _task_to_response(task)}


@router.get("/stats/overview")
def get_task_stats(
    task_manager: TaskManager = Depends(get_task_manager)
) -> Dict[str, Any]:
    """获取任务统计"""
    return task_manager.get_stats()


@router.get("/blocked")
def get_blocked_tasks(
    task_manager: TaskManager = Depends(get_task_manager)
) -> List[TaskResponse]:
    """获取阻塞的任务"""
    tasks = task_manager.get_blocked()
    return [_task_to_response(t) for t in tasks]


@router.get("/overdue")
def get_overdue_tasks(
    task_manager: TaskManager = Depends(get_task_manager)
) -> List[TaskResponse]:
    """获取逾期的任务"""
    tasks = task_manager.get_overdue()
    return [_task_to_response(t) for t in tasks]


@router.get("/history")
def get_execution_history() -> ExecutionHistoryResponse:
    """获取执行历史"""
    executor = get_executor()
    results = [r.to_dict() for r in executor._execution_history]
    return ExecutionHistoryResponse(results=results, total=len(results))
