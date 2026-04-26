"""
文献调研 REST API - Phase 14
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio

from ..services.literature_research import (
    get_literature_service,
    LiteratureSource,
    ResearchTask,
    Paper
)

router = APIRouter(prefix="/api/literature", tags=["文献调研"])


# ============================================================
# 请求/响应模型
# ============================================================

class CreateResearchRequest(BaseModel):
    """创建调研任务请求"""
    query: str = Field(..., description="搜索查询词")
    idea_id: Optional[str] = Field(None, description="关联想法ID")
    sources: Optional[List[str]] = Field(None, description="使用的文献源，默认全部")
    max_results_per_source: int = Field(20, ge=1, le=100, description="每个源最多返回数")
    min_relevance: float = Field(0.3, ge=0, le=1, description="最低相关度阈值")


class SourceConfigRequest(BaseModel):
    """文献源配置请求"""
    id: str = Field(..., description="源ID")
    name: str
    description: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit: int = Field(10, ge=1, le=100)


class UpdatePaperRequest(BaseModel):
    """更新论文请求"""
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_starred: Optional[bool] = None
    relevance_score: Optional[float] = Field(None, ge=0, le=1)


class PaperResponse(BaseModel):
    """论文响应"""
    paper_id: str
    title: str
    abstract: str
    authors: List[str]
    year: int
    venue: str
    citation_count: int
    url: str
    doi: str
    source: str
    relevance_score: float
    credibility: int
    credibility_display: str
    tags: List[str]
    notes: str
    is_starred: bool

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """调研任务响应"""
    id: str
    query: str
    idea_id: str
    sources: List[str]
    total_found: int
    status: str
    progress: int
    papers: List[PaperResponse]
    error: str
    created_at: str
    completed_at: str


class SourceResponse(BaseModel):
    """文献源响应"""
    id: str
    name: str
    description: str
    enabled: bool
    api_key_required: bool
    supports_abstract: bool
    supports_citations: bool
    supports_keywords: bool
    supports_fulltext: bool
    default_credibility: int


# ============================================================
# 辅助函数
# ============================================================

def paper_to_response(paper: Paper) -> PaperResponse:
    """转换为响应模型"""
    return PaperResponse(
        paper_id=paper.paper_id,
        title=paper.title,
        abstract=paper.abstract,
        authors=paper.authors,
        year=paper.year,
        venue=paper.venue,
        citation_count=paper.citation_count,
        url=paper.url,
        doi=paper.doi,
        source=paper.source,
        relevance_score=paper.relevance_score,
        credibility=paper.credibility,
        credibility_display=paper.get_credibility_display(),
        tags=paper.tags,
        notes=paper.notes,
        is_starred=paper.is_starred
    )


def task_to_response(task: ResearchTask) -> TaskResponse:
    """转换为响应模型"""
    return TaskResponse(
        id=task.id,
        query=task.query,
        idea_id=task.idea_id,
        sources=task.sources,
        total_found=task.total_found,
        status=task.status,
        progress=task.progress,
        papers=[paper_to_response(p) for p in task.papers],
        error=task.error,
        created_at=task.created_at,
        completed_at=task.completed_at
    )


# ============================================================
# 文献源管理 API
# ============================================================

@router.get("/sources", response_model=List[SourceResponse])
async def list_sources():
    """列出所有文献源"""
    service = get_literature_service()
    sources = service.registry.list_sources()
    return [
        SourceResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            enabled=s.enabled,
            api_key_required=s.api_key_required,
            supports_abstract=s.supports_abstract,
            supports_citations=s.supports_citations,
            supports_keywords=s.supports_keywords,
            supports_fulltext=s.supports_fulltext,
            default_credibility=s.default_credibility
        )
        for s in sources
    ]


@router.post("/sources", response_model=SourceResponse)
async def register_source(config: SourceConfigRequest):
    """注册新的文献源"""
    service = get_literature_service()
    
    source_config = LiteratureSource(
        id=config.id,
        name=config.name,
        description=config.description,
        enabled=config.enabled,
        api_key=config.api_key or "",
        base_url=config.base_url or "",
        rate_limit=config.rate_limit
    )
    
    if service.registry.register_source(source_config):
        return SourceResponse(
            id=source_config.id,
            name=source_config.name,
            description=source_config.description,
            enabled=source_config.enabled,
            api_key_required=source_config.api_key_required,
            supports_abstract=source_config.supports_abstract,
            supports_citations=source_config.supports_citations,
            supports_keywords=source_config.supports_keywords,
            supports_fulltext=source_config.supports_fulltext,
            default_credibility=source_config.default_credibility
        )
    raise HTTPException(status_code=400, detail="注册失败")


@router.delete("/sources/{source_id}")
async def unregister_source(source_id: str):
    """取消注册文献源"""
    service = get_literature_service()
    if service.registry.unregister_source(source_id):
        return {"status": "ok", "message": f"已取消注册 {source_id}"}
    raise HTTPException(status_code=404, detail="文献源不存在")


@router.put("/sources/{source_id}/toggle")
async def toggle_source(source_id: str, enabled: bool):
    """启用/禁用文献源"""
    service = get_literature_service()
    config = service.registry.get_config(source_id)
    if not config:
        raise HTTPException(status_code=404, detail="文献源不存在")
    
    config.enabled = enabled
    service.registry.update_source_config(config)
    return {"status": "ok", "enabled": enabled}


# ============================================================
# 文献调研 API
# ============================================================

@router.post("/research", response_model=TaskResponse)
async def create_research_task(request: CreateResearchRequest, background_tasks: BackgroundTasks):
    """创建并执行文献调研任务"""
    service = get_literature_service()
    
    # 创建任务
    task = service.create_task(
        query=request.query,
        idea_id=request.idea_id or "",
        sources=request.sources,
        max_results_per_source=request.max_results_per_source,
        min_relevance=request.min_relevance
    )
    
    # 后台执行
    async def run_search():
        await service.execute_task(task.id)
    
    background_tasks.add_task(run_search)
    
    return task_to_response(task)


@router.get("/research/{task_id}", response_model=TaskResponse)
async def get_research_task(task_id: str):
    """获取调研任务状态和结果"""
    service = get_literature_service()
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_to_response(task)


@router.get("/research", response_model=List[TaskResponse])
async def list_research_tasks(idea_id: Optional[str] = None):
    """列出调研任务"""
    service = get_literature_service()
    tasks = service.list_tasks(idea_id)
    return [task_to_response(t) for t in tasks]


@router.post("/research/{task_id}/execute")
async def execute_research_task(task_id: str, background_tasks: BackgroundTasks):
    """重新执行调研任务"""
    service = get_literature_service()
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    async def run_search():
        await service.execute_task(task_id)
    
    background_tasks.add_task(run_search)
    
    return {"status": "ok", "message": "任务已在后台执行"}


# ============================================================
# 论文管理 API
# ============================================================

@router.patch("/research/{task_id}/papers/{paper_id}")
async def update_paper(task_id: str, paper_id: str, request: UpdatePaperRequest):
    """更新论文标注"""
    service = get_literature_service()
    
    updates = {}
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.notes is not None:
        updates["notes"] = request.notes
    if request.is_starred is not None:
        updates["is_starred"] = request.is_starred
    if request.relevance_score is not None:
        updates["relevance_score"] = request.relevance_score
    
    paper = service.update_paper(task_id, paper_id, updates)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    
    return paper_to_response(paper)


@router.get("/research/{task_id}/export")
async def export_papers(task_id: str, format: str = "json"):
    """导出论文列表"""
    service = get_literature_service()
    
    if format not in ["json", "bibtex", "markdown"]:
        raise HTTPException(status_code=400, detail="不支持的格式")
    
    content = service.export_papers(task_id, format)
    if not content:
        raise HTTPException(status_code=404, detail="任务不存在或无数据")
    
    return {
        "task_id": task_id,
        "format": format,
        "content": content
    }


# ============================================================
# 快速搜索（单源直接返回）
# ============================================================

@router.get("/quick-search")
async def quick_search(
    q: str = Query(..., description="搜索词"),
    source: str = Query("semanticscholar", description="文献源"),
    limit: int = Query(10, ge=1, le=50)
):
    """快速搜索（单源，直接返回结果）"""
    service = get_literature_service()
    
    source_impl = service.registry.get_source(source)
    if not source_impl:
        raise HTTPException(status_code=404, detail=f"文献源不存在: {source}")
    
    papers = source_impl.search(q, limit)
    
    return {
        "query": q,
        "source": source,
        "count": len(papers),
        "papers": [paper_to_response(p) for p in papers]
    }


