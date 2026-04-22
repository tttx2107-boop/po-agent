"""想法 CRUD API 路由"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..core.idea_manager import IdeaManager
from ..storage.gist_store import get_storage
from ..utils.logger import setup_logger

logger = setup_logger("po-agent.routes.ideas")

router = APIRouter(prefix="/api/ideas", tags=["想法管理"])


def get_idea_manager() -> IdeaManager:
    """获取 IdeaManager 实例"""
    storage = get_storage()
    return IdeaManager(storage)


# ==================== IdeaResponse ====================

class IdeaResponse(BaseModel):
    """想法响应"""
    id: str
    content: str
    created_at: str
    updated_at: str
    source: str
    tags: List[str]
    status: str
    quick_assessment: Optional[Dict[str, Any]] = None
    deep_assessment: Optional[Dict[str, Any]] = None
    tasks: List[str] = Field(default_factory=list)
    progress: int = 0


def _idea_to_response(idea) -> IdeaResponse:
    """将 Idea 转为响应模型"""
    data = idea.to_dict()
    # 处理 quick_assessment 字段名
    if "quick_assessment" in data and data["quick_assessment"]:
        qa = data["quick_assessment"]
        if isinstance(qa, dict):
            pass  # 已经是字典
        else:
            data["quick_assessment"] = qa.to_dict() if hasattr(qa, 'to_dict') else qa
    # 处理 deep_assessment
    if "deep_assessment" in data and data["deep_assessment"]:
        da = data["deep_assessment"]
        if hasattr(da, 'to_dict'):
            data["deep_assessment"] = da.to_dict()
    return IdeaResponse(**data)


class IdeaCreateRequest(BaseModel):
    """创建想法请求"""
    content: str = Field(..., min_length=1, max_length=5000, description="想法内容")
    tags: List[str] = Field(default_factory=list, description="标签")
    source: str = Field(default="api", description="来源")


class IdeaUpdateRequest(BaseModel):
    """更新想法请求"""
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class IdeaListResponse(BaseModel):
    """想法列表响应"""
    ideas: List[IdeaResponse]
    total: int


# ==================== API 端点 ====================

@router.get("", response_model=IdeaListResponse)
async def list_ideas(
    status: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    manager: IdeaManager = Depends(get_idea_manager)
) -> IdeaListResponse:
    """
    获取想法列表
    
    - 支持按状态筛选
    - 支持按标签筛选
    - 支持分页限制
    """
    ideas = manager.list_ideas()
    
    # 筛选
    if status:
        ideas = [i for i in ideas if i.status == status]
    if tag:
        ideas = [i for i in ideas if tag in i.tags]
    
    # 限制数量
    ideas = ideas[:limit]
    
    return IdeaListResponse(
        ideas=[IdeaResponse(**i.to_dict()) for i in ideas],
        total=len(ideas)
    )


@router.post("", response_model=Dict[str, Any])
async def create_idea(
    request: IdeaCreateRequest,
    manager: IdeaManager = Depends(get_idea_manager)
) -> Dict[str, Any]:
    """
    创建新想法
    
    - 自动进行快速评估
    - 分配唯一ID
    """
    try:
        # 创建基础想法
        idea = manager.create(
            content=request.content,
            source=request.source
        )
        # 合并用户提供的标签和自动提取的标签
        if request.tags:
            merged_tags = list(set(idea.tags + request.tags))
            idea.tags = merged_tags
            manager._save()
        return {
            "success": True,
            "idea": idea.to_dict(),
            "message": "想法创建成功"
        }
    except Exception as e:
        logger.error(f"创建想法失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(
    idea_id: str,
    manager: IdeaManager = Depends(get_idea_manager)
) -> IdeaResponse:
    """
    获取想法详情
    """
    idea = manager.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"想法 [{idea_id}] 不存在")
    return IdeaResponse(**idea.to_dict())


@router.put("/{idea_id}", response_model=IdeaResponse)
async def update_idea(
    idea_id: str,
    request: IdeaUpdateRequest,
    manager: IdeaManager = Depends(get_idea_manager)
) -> IdeaResponse:
    """
    更新想法
    """
    idea = manager.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"想法 [{idea_id}] 不存在")
    
    # 更新字段
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(idea, key):
            setattr(idea, key, value)
    
    idea.updated_at = datetime.now().isoformat()
    manager._save()
    
    return IdeaResponse(**idea.to_dict())


@router.delete("/{idea_id}")
async def delete_idea(
    idea_id: str,
    manager: IdeaManager = Depends(get_idea_manager)
) -> Dict[str, Any]:
    """
    删除想法
    """
    idea = manager.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"想法 [{idea_id}] 不存在")
    
    manager.delete_idea(idea_id)
    return {"success": True, "message": f"想法 [{idea_id}] 已删除"}
