"""
知识图谱 & API 开放平台路由 - Phase 12
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Header, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import time

from ..services.knowledge_graph import (
    get_knowledge_graph_service, 
    KnowledgeGraphService,
    Entity, 
    Relation
)
from ..services.model_provider import (
    ModelManager,
    Message,
    chat as model_chat
)
from ..utils.logger import setup_logger

logger = setup_logger("po-agent.routes.kg-api")
router = APIRouter(prefix="/api/v1", tags=["Phase 12: 高级功能"])


# ==================== API Key 管理 ====================

class APIKeyManager:
    """简单的 API Key 管理"""
    _keys: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_key(cls, name: str, permissions: List[str] = None) -> str:
        """创建 API Key"""
        key = hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:32]
        cls._keys[key] = {
            "name": name,
            "permissions": permissions or ["read"],
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "request_count": 0
        }
        return key
    
    @classmethod
    def validate_key(cls, key: str) -> Optional[Dict[str, Any]]:
        """验证 API Key"""
        if key in cls._keys:
            cls._keys[key]["last_used"] = datetime.now().isoformat()
            cls._keys[key]["request_count"] += 1
            return cls._keys[key]
        return None
    
    @classmethod
    def revoke_key(cls, key: str) -> bool:
        """撤销 API Key"""
        if key in cls._keys:
            del cls._keys[key]
            return True
        return False
    
    @classmethod
    def list_keys(cls) -> List[Dict[str, Any]]:
        """列出所有 Key (不含实际 key)"""
        return [
            {**v, "key_preview": k[:8] + "..."}
            for k, v in cls._keys.items()
        ]


def get_api_key(x_api_key: str = Header(None)) -> Dict[str, Any]:
    """API Key 验证依赖"""
    if x_api_key:
        key_info = APIKeyManager.validate_key(x_api_key)
        if key_info:
            return key_info
    # 开发模式不强制验证
    return {"name": "dev", "permissions": ["all"]}


# ==================== 请求/响应模型 ====================

class IdeaExtractRequest(BaseModel):
    """从想法提取知识图谱请求"""
    idea_content: str = Field(..., description="想法内容")
    idea_id: str = Field(..., description="想法ID")


class EntityResponse(BaseModel):
    """实体响应"""
    id: str
    name: str
    type: str
    description: str
    confidence: float
    idea_ids: List[str]


class RelationResponse(BaseModel):
    """关系响应"""
    id: str
    source: str
    target: str
    type: str
    weight: float
    evidence: str


class GraphStatsResponse(BaseModel):
    """图谱统计响应"""
    total_entities: int
    total_relations: int
    entity_types: Dict[str, int]
    relation_types: Dict[str, int]


class ConnectionRequest(BaseModel):
    """查找关联请求"""
    idea_content: str = Field(..., description="想法内容")
    max_results: int = Field(5, description="最大结果数")


class ModelChatRequest(BaseModel):
    """模型对话请求"""
    prompt: str = Field(..., description="用户提示")
    provider: str = Field("mock", description="模型提供商")
    system: Optional[str] = Field(None, description="系统提示")
    max_tokens: int = Field(1000, description="最大 token 数")
    temperature: float = Field(0.7, description="温度参数")


class ModelChatResponse(BaseModel):
    """模型对话响应"""
    text: str
    model: str
    provider: str
    usage: Dict[str, int]


class CreateAPIKeyRequest(BaseModel):
    """创建 API Key 请求"""
    name: str = Field(..., description="Key 名称")
    permissions: List[str] = Field(["read"], description="权限列表")


class CreateAPIKeyResponse(BaseModel):
    """创建 API Key 响应"""
    api_key: str
    name: str
    permissions: List[str]
    created_at: str


# ==================== 知识图谱 API ====================

@router.post("/knowledge/extract", response_model=Dict[str, Any])
def extract_knowledge(
    request: IdeaExtractRequest,
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """
    从想法中提取知识图谱实体和关系
    
    基于 5W1H 方法论自动识别实体和关系
    """
    if "extract" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    kg_service = get_knowledge_graph_service()
    result = kg_service.extract_from_idea(request.idea_content, request.idea_id)
    
    return {
        "success": True,
        "idea_id": request.idea_id,
        **result
    }


@router.get("/knowledge/graph", response_model=Dict[str, Any])
def get_graph(
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """获取完整知识图谱"""
    if "read" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    kg_service = get_knowledge_graph_service()
    return kg_service.get_graph_stats()


@router.get("/knowledge/stats", response_model=GraphStatsResponse)
def get_graph_stats(
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> GraphStatsResponse:
    """获取图谱统计信息"""
    kg_service = get_knowledge_graph_service()
    stats = kg_service.get_graph_stats()
    
    return GraphStatsResponse(
        total_entities=stats["total_entities"],
        total_relations=stats["total_relations"],
        entity_types=stats["entity_types"],
        relation_types=stats["relation_types"]
    )


@router.post("/knowledge/connections", response_model=Dict[str, Any])
def find_connections(
    request: ConnectionRequest,
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """查找想法之间的关联"""
    if "read" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    kg_service = get_knowledge_graph_service()
    connections = kg_service.find_connections(request.idea_content, request.max_results)
    
    return {
        "success": True,
        "idea_content": request.idea_content[:50] + "...",
        "connections": connections,
        "count": len(connections)
    }


# ==================== 多模型 API ====================

@router.get("/models/providers", response_model=List[Dict[str, str]])
def get_providers() -> List[Dict[str, str]]:
    """获取可用模型提供商列表"""
    return ModelManager.list_providers()


@router.post("/models/chat", response_model=ModelChatResponse)
async def chat_with_model(
    request: ModelChatRequest,
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> ModelChatResponse:
    """
    与 AI 模型对话
    
    支持多种模型提供商：openai, anthropic, ollama, mock
    """
    if "chat" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    messages = []
    if request.system:
        messages.append(Message(role="system", content=request.system))
    messages.append(Message(role="user", content=request.prompt))
    
    from ..services.model_provider import ModelManager
    provider = ModelManager.get_provider(request.provider)
    
    result = await provider.chat(
        messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    return ModelChatResponse(
        text=result.text,
        model=result.model,
        provider=result.provider,
        usage=result.usage
    )


@router.post("/models/complete")
async def complete_with_model(
    request: ModelChatRequest,
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """文本补全"""
    if "chat" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    from ..services.model_provider import ModelManager
    provider_instance = ModelManager.get_provider(request.provider)
    result = await provider_instance.complete(request.prompt)
    
    return {
        "text": result.text,
        "model": result.model,
        "provider": result.provider
    }


# ==================== API Key 管理 API ====================

@router.post("/keys", response_model=CreateAPIKeyResponse)
def create_api_key(
    request: CreateAPIKeyRequest,
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> CreateAPIKeyResponse:
    """创建新的 API Key (管理员)"""
    if "admin" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    new_key = APIKeyManager.create_key(request.name, request.permissions)
    key_info = APIKeyManager._keys[new_key]
    
    return CreateAPIKeyResponse(
        api_key=new_key,
        name=key_info["name"],
        permissions=key_info["permissions"],
        created_at=key_info["created_at"]
    )


@router.get("/keys", response_model=List[Dict[str, Any]])
def list_api_keys(
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> List[Dict[str, Any]]:
    """列出所有 API Keys"""
    if "admin" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    return APIKeyManager.list_keys()


@router.delete("/keys/{key_prefix}")
def revoke_api_key(
    key_prefix: str,
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """撤销 API Key"""
    if "admin" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    # 查找并删除
    for key in list(APIKeyManager._keys.keys()):
        if key.startswith(key_prefix):
            APIKeyManager.revoke_key(key)
            return {"success": True, "message": f"Key {key_prefix}*** revoked"}
    
    raise HTTPException(status_code=404, detail="Key not found")


# ==================== 语义搜索 & 可视化 ====================

@router.get("/knowledge/search")
def search_graph(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(10, description="结果数量限制"),
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """语义搜索知识图谱"""
    kg_service = get_knowledge_graph_service()
    results = kg_service.semantic_search(query, limit)
    
    return {
        "success": True,
        "query": query,
        "results": [
            {
                "entity": r["entity"].to_dict(),
                "score": r["score"],
                "match_type": r["match_type"]
            }
            for r in results
        ],
        "count": len(results)
    }


@router.get("/knowledge/visualization/{format}")
def get_visualization(
    format: str = Path(..., description="可视化格式: d3, cytoscape, tree"),
    focus_entity_id: Optional[str] = Query(None, description="焦点实体ID"),
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """获取可视化数据"""
    valid_formats = ["d3", "cytoscape", "tree", "json"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid format. Supported: {valid_formats}"
        )
    
    kg_service = get_knowledge_graph_service()
    data = kg_service.get_visualization_data(format, focus_entity_id)
    
    return {
        "success": True,
        "format": format,
        "data": data
    }


@router.get("/knowledge/subgraph/{entity_id}")
def get_entity_subgraph(
    entity_id: str,
    depth: int = Query(2, description="探索深度"),
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """获取实体子图"""
    kg_service = get_knowledge_graph_service()
    subgraph = kg_service.get_entity_subgraph(entity_id, depth)
    
    return {
        "success": True,
        "entity_id": entity_id,
        "depth": depth,
        "subgraph": subgraph
    }


@router.get("/knowledge/paths")
def find_entity_paths(
    entity1: str = Query(..., description="实体1名称"),
    entity2: str = Query(..., description="实体2名称"),
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """查找两个实体之间的路径"""
    kg_service = get_knowledge_graph_service()
    paths = kg_service.find_paths(entity1, entity2)
    
    return {
        "success": True,
        "entity1": entity1,
        "entity2": entity2,
        "paths": paths,
        "count": len(paths)
    }


# ==================== 图谱导入导出 ====================

@router.post("/knowledge/import")
def import_graph(
    graph_data: Dict[str, Any],
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """导入知识图谱"""
    if "write" not in api_key.get("permissions", []) and "all" not in api_key.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    kg_service = get_knowledge_graph_service()
    kg_service.import_graph(graph_data)
    
    stats = kg_service.get_graph_stats()
    return {
        "success": True,
        "message": "Graph imported successfully",
        "stats": stats
    }


@router.get("/knowledge/export")
def export_graph(
    api_key: Dict[str, Any] = Depends(get_api_key)
) -> Dict[str, Any]:
    """导出完整知识图谱"""
    kg_service = get_knowledge_graph_service()
    return {
        "success": True,
        "data": kg_service.export_graph()
    }


# ==================== 平台信息 ====================

@router.get("/platform/info")
def get_platform_info() -> Dict[str, Any]:
    """获取平台信息"""
    return {
        "name": "「破」API Platform",
        "version": "1.0.0",
        "phase": "Phase 12: 高级功能",
        "features": [
            "knowledge_graph: 知识图谱服务",
            "multi_model: 多模型支持",
            "api_keys: API Key 管理"
        ],
        "endpoints": {
            "knowledge": "/api/v1/knowledge/*",
            "models": "/api/v1/models/*",
            "keys": "/api/v1/keys/*"
        }
    }


@router.get("/platform/health")
def health_check() -> Dict[str, Any]:
    """平台健康检查"""
    kg_service = get_knowledge_graph_service()
    stats = kg_service.get_graph_stats()
    
    return {
        "status": "healthy",
        "service": "po-agent-platform",
        "version": "1.0.0",
        "knowledge_graph": {
            "entities": stats["total_entities"],
            "relations": stats["total_relations"]
        },
        "providers": ModelManager.list_providers()
    }


