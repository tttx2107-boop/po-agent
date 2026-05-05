"""
知识图谱提取引擎 - Layer 2
支持 RAG-based 和 Typical 两种方法，集成LLM调用
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import json


@dataclass
class ExtractionResult:
    """提取引擎返回结果"""
    entities: List[Dict] = field(default_factory=list)
    relations: List[Dict] = field(default_factory=list)
    hyperedges: List[Dict] = field(default_factory=list)
    temporal: List[Dict] = field(default_factory=list)
    spatial: List[Dict] = field(default_factory=list)
    trajectories: List[Dict] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)


class BaseExtractor(ABC):
    """提取引擎基类"""
    
    def __init__(self, llm_client=None, config: Dict = None):
        self.llm_client = llm_client
        self.config = config or {}
    
    @abstractmethod
    def extract(self, text: str, schema: Dict = None, **kwargs) -> ExtractionResult:
        """
        从文本中提取知识
        
        Args:
            text: 输入文本
            schema: 可选的提取schema定义
            
        Returns:
            ExtractionResult: 包含提取结果的类
        """
        pass
    
    def _call_llm(self, prompt: str, system: str = None) -> str:
        """调用LLM"""
        if self.llm_client:
            return self.llm_client.generate(prompt, system)
        else:
            raise ValueError("LLM客户端未配置")
    
    def _call_llm_json(self, prompt: str, system: str = None) -> Dict:
        """调用LLM并解析JSON"""
        if self.llm_client:
            return self.llm_client.extract_json(prompt, system)
        else:
            raise ValueError("LLM客户端未配置")


# ==================== RAG-based Methods ====================

class GraphRAGExtractor(BaseExtractor):
    """GraphRAG 提取引擎 - 使用知识图谱增强的RAG"""
    
    def extract(self, text: str, schema: Dict = None, **kwargs) -> ExtractionResult:
        # 1. 分块
        chunks = self._chunk_text(text)
        # 2. 实体抽取（带LLM）
        entities = self._extract_entities_llm(chunks, schema)
        # 3. 关系抽取（带LLM）
        relations = self._extract_relations_llm(chunks, entities, schema)
        # 4. 去重
        entities = self._deduplicate_entities(entities)
        # 5. 构建子图
        subgraphs = self._build_subgraphs(entities, relations)
        
        return ExtractionResult(
            entities=entities,
            relations=relations,
            metadata={
                "method": "GraphRAG",
                "chunks": len(chunks),
                "subgraphs": len(subgraphs)
            }
        )
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """文本分块"""
        paragraphs = text.split('\n\n')
        chunks = []
        current = []
        current_len = 0
        
        for p in paragraphs:
            if current_len + len(p) > chunk_size and current:
                chunks.append('\n\n'.join(current))
                current = [p]
                current_len = len(p)
            else:
                current.append(p)
                current_len += len(p)
        
        if current:
            chunks.append('\n\n'.join(current))
        
        return chunks
    
    def _extract_entities_llm(self, chunks: List[str], schema: Dict = None) -> List[Dict]:
        """使用LLM抽取实体"""
        if self.llm_client:
            return self._extract_entities_with_llm(chunks, schema)
        else:
            return self._extract_entities_placeholder(chunks, schema)
    
    def _extract_entities_with_llm(self, chunks: List[str], schema: Dict = None) -> List[Dict]:
        """有LLM时的实体抽取"""
        entity_types = schema.get('entities', []) if schema else []
        type_def = ""
        if entity_types:
            type_def = "\n".join([f"- {e['name']}: {e.get('description', '')}" for e in entity_types])
        else:
            type_def = "- person: 人物\n- organization: 组织\n- location: 地点\n- event: 事件\n- concept: 概念"
        
        prompt = f"""从以下文本中抽取实体，输出JSON数组格式：

文本：
{''.join(chunks[:3])[:3000]}

实体类型定义：
{type_def}

要求：
- 每个实体包含: id(英文小写下划线), name, type, properties
- id格式: {{type}}_{{名称拼音}} 如: person_zhangsan
- properties包含实体的其他属性

输出格式（只输出JSON，不要其他内容）：
{{"entities": [{{"id": "...", "name": "...", "type": "...", "properties": {{}}}}]}}
"""
        
        try:
            result = self._call_llm_json(prompt)
            return result.get('entities', [])
        except:
            return self._extract_entities_placeholder(chunks, schema)
    
    def _extract_entities_placeholder(self, chunks: List[str], schema: Dict = None) -> List[Dict]:
        """无LLM时的占位实现（返回空，需要后续LLM调用）"""
        return []
    
    def _extract_relations_llm(self, chunks: List[str], entities: List[Dict], schema: Dict = None) -> List[Dict]:
        """使用LLM抽取关系"""
        if self.llm_client and entities:
            return self._extract_relations_with_llm(chunks, entities, schema)
        else:
            return []
    
    def _extract_relations_with_llm(self, chunks: List[str], entities: List[Dict], schema: Dict = None) -> List[Dict]:
        """有LLM时的关系抽取"""
        entity_names = {e['name']: e['id'] for e in entities[:20]}
        relation_types = schema.get('relations', []) if schema else []
        
        rel_def = ""
        if relation_types:
            rel_def = "\n".join([f"- {r['name']}: {r.get('description', '')}" for r in relation_types])
        else:
            rel_def = "- 位于: 位置关系\n- 参与: 参与关系\n- 导致: 因果关系\n- 协同: 协作关系"
        
        prompt = f"""从以下文本中抽取实体间的关系，输出JSON数组格式：

文本：
{''.join(chunks[:2])[:2500]}

已知实体（ID -> 名称）：
{json.dumps(entity_names, ensure_ascii=False, indent=2)}

关系类型定义：
{rel_def}

要求：
- 每个关系包含: id, source(实体ID), target(实体ID), relation, properties
- id格式: rel_{{序号}}

输出格式（只输出JSON，不要其他内容）：
{{"relations": [{{"id": "...", "source": "...", "target": "...", "relation": "...", "properties": {{}}}}]}}
"""
        
        try:
            result = self._call_llm_json(prompt)
            return result.get('relations', [])
        except:
            return []
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """实体去重"""
        seen = {}
        for e in entities:
            key = (e.get('name', '').lower(), e.get('type', ''))
            if key not in seen:
                seen[key] = e
        return list(seen.values())
    
    def _build_subgraphs(self, entities: List[Dict], relations: List[Dict]) -> List[Dict]:
        """构建子图"""
        subgraphs = []
        entity_map = {e['id']: e for e in entities}
        visited = set()
        
        for rel in relations:
            source = rel.get('source')
            target = rel.get('target')
            key = (source, target)
            
            if key not in visited:
                visited.add(key)
                subgraph_entities = []
                subgraph_relations = []
                
                for e in entities:
                    if e['id'] == source or e['id'] == target:
                        subgraph_entities.append(e)
                subgraph_relations.append(rel)
                
                subgraphs.append({
                    "entities": subgraph_entities,
                    "relations": subgraph_relations
                })
        
        return subgraphs


class HypergraphRAGExtractor(GraphRAGExtractor):
    """HypergraphRAG 提取引擎 - 支持超边和时空抽取"""
    
    def extract(self, text: str, schema: Dict = None, **kwargs) -> ExtractionResult:
        # 先用父类抽取基础实体和关系
        result = super().extract(text, schema, **kwargs)
        
        if self.llm_client:
            # 额外抽取超边
            hyperedges = self._extract_hyperedges_llm(text, result.entities, schema)
            result.hyperedges = hyperedges
            
            # 额外抽取时空信息
            temporal, spatial, trajectories = self._extract_spatiotemporal_llm(text, result.entities)
            result.temporal = temporal
            result.spatial = spatial
            result.trajectories = trajectories
        
        result.metadata["method"] = "HypergraphRAG"
        return result
    
    def _extract_hyperedges_llm(self, text: str, entities: List[Dict], schema: Dict = None) -> List[Dict]:
        """使用LLM抽取超边"""
        entity_info = "\n".join([f"- {e['id']}: {e['name']} ({e['type']})" for e in entities[:30]])
        
        prompt = f"""从以下文本中抽取涉及3个及以上实体的复杂关系（超边），输出JSON数组格式：

文本：
{text[:3000]}

已知实体：
{entity_info}

超边示例：
- "消防队A、消防队B、指挥中心协同灭火" → 超边(协同灭火, [消防队A, 消防队B, 指挥中心])
- "甲乙丙三方签署合同" → 超边(签署合同, [甲, 乙, 丙])
- "张三、李四、王五共同完成项目" → 超边(协作完成, [张三, 李四, 王五])

要求：
- 每个超边包含: id, label, entities(参与实体的ID列表), relation_type, roles(可选的角色分组)
- id格式: he_{{序号}}
- relation_type可选: 协同, 合作, 参与, 签署, 共同等

输出格式（只输出JSON）：
{{"hyperedges": [{{"id": "...", "label": "...", "entities": ["...", "..."], "relation_type": "...", "roles": {{}}}}]}}
"""
        
        try:
            result = self._call_llm_json(prompt)
            return result.get('hyperedges', [])
        except:
            return []
    
    def _extract_spatiotemporal_llm(self, text: str, entities: List[Dict]) -> tuple:
        """使用LLM抽取时空信息"""
        entity_info = "\n".join([f"- {e['id']}: {e['name']}" for e in entities[:20]])
        
        prompt = f"""从以下文本中抽取时间、空间和轨迹信息：

文本：
{text[:3000]}

已知实体：
{entity_info}

要求：
1. temporal: 事件列表，包含 id, event(事件名称), time(ISO8601格式如2024-03-15T14:30:00), duration(可选)
2. spatial: 位置列表，包含 id, name, location({{lat:纬度, lng:经度}}格式), address(地址描述), radius(影响半径米)
3. trajectories: 轨迹列表，包含 id, entity_id(追踪的实体ID), points([{{time:时间, location:[lng,lat]}}])

注意：如果无法确定精确的经纬度，使用null。如果文本中包含地址或位置描述，优先提取。

输出格式（只输出JSON）：
{{"temporal": [...], "spatial": [...], "trajectories": [...]}}
"""
        
        try:
            result = self._call_llm_json(prompt)
            temporal = result.get('temporal', [])
            spatial = result.get('spatial', [])
            trajectories = result.get('trajectories', [])
            return temporal, spatial, trajectories
        except:
            return [], [], []


class LightRAGExtractor(BaseExtractor):
    """LightRAG 提取引擎 - 轻量级快速抽取"""
    
    def extract(self, text: str, schema: Dict = None, **kwargs) -> ExtractionResult:
        if self.llm_client:
            return self._extract_with_llm(text, schema)
        else:
            return ExtractionResult(metadata={"method": "LightRAG", "status": "llm_not_configured"})
    
    def _extract_with_llm(self, text: str, schema: Dict = None) -> ExtractionResult:
        """轻量级LLM抽取"""
        prompt = f"""从以下文本中快速抽取核心实体和关系：

文本：
{text[:2000]}

输出JSON格式：
{{"entities": [{{"id": "e{{n}}", "name": "...", "type": "concept"}}],
 "relations": [{{"id": "r{{n}}", "source": "e{{m}}", "target": "e{{k}}", "relation": "..."}}]}}
"""
        
        try:
            result = self._call_llm_json(prompt)
            return ExtractionResult(
                entities=result.get('entities', []),
                relations=result.get('relations', []),
                metadata={"method": "LightRAG"}
            )
        except:
            return ExtractionResult(metadata={"method": "LightRAG", "status": "error"})


# ==================== Typical Methods ====================

class KGGenExtractor(BaseExtractor):
    """KG-Gen 提取引擎 - 传统知识图谱生成"""
    
    def extract(self, text: str, schema: Dict = None, **kwargs) -> ExtractionResult:
        if self.llm_client:
            entities = self._llm_extract_entities(text, schema)
            relations = self._llm_extract_relations(text, entities, schema)
            return ExtractionResult(
                entities=entities,
                relations=relations,
                metadata={"method": "KG-Gen"}
            )
        else:
            return ExtractionResult(metadata={"method": "KG-Gen", "status": "llm_not_configured"})
    
    def _llm_extract_entities(self, text: str, schema: Dict = None) -> List[Dict]:
        """LLM实体抽取"""
        entity_types = schema.get('entities', []) if schema else []
        if entity_types:
            type_list = '\n'.join([f"- {e['name']}: {e.get('description', '')}" for e in entity_types])
        else:
            type_list = '实体类型不限，可识别：人物、组织、地点、事件、概念'
        
        prompt = f"""从以下文本中抽取实体：

文本：{text[:3000]}

实体类型定义：
{type_list}

输出JSON格式：
{{"entities": [{{"id": "...", "name": "...", "type": "...", "properties": {{}}}}]}}
"""
        try:
            result = self._call_llm_json(prompt)
            return result.get('entities', [])
        except:
            return []
    
    def _llm_extract_relations(self, text: str, entities: List[Dict], schema: Dict = None) -> List[Dict]:
        """LLM关系抽取"""
        relation_types = schema.get('relations', []) if schema else []
        if relation_types:
            rel_list = '\n'.join([f"- {r['name']}: {r.get('description', '')}" for r in relation_types])
        else:
            rel_list = '关系类型不限'
        
        entity_map = {e['name']: e['id'] for e in entities}
        
        prompt = f"""从以下文本中抽取实体间的关系：

文本：{text[:3000]}

实体列表（名称->ID）：
{json.dumps(entity_map, ensure_ascii=False, indent=2)}

关系类型：
{rel_list}

输出JSON格式：
{{"relations": [{{"id": "...", "source": "...", "target": "...", "relation": "..."}}]}}
"""
        try:
            result = self._call_llm_json(prompt)
            return result.get('relations', [])
        except:
            return []


class HypergraphExtractor(BaseExtractor):
    """专用超图提取引擎"""
    
    def extract(self, text: str, schema: Dict = None, **kwargs) -> ExtractionResult:
        if not self.llm_client:
            return ExtractionResult(metadata={"method": "HypergraphExtractor", "status": "llm_not_configured"})
        
        result = ExtractionResult()
        
        # 抽取实体
        result.entities = self._extract_entities(text, schema)
        
        # 抽取超边
        result.hyperedges = self._extract_hyperedges(text, result.entities)
        
        result.metadata["method"] = "HypergraphExtractor"
        return result
    
    def _extract_entities(self, text: str, schema: Dict = None) -> List[Dict]:
        """抽取实体"""
        prompt = f"""从以下文本中抽取所有实体：

文本：{text[:3000]}

输出JSON：
{{"entities": [{{"id": "e{{n}}", "name": "...", "type": "person|organization|location|event|concept"}}]}}
"""
        try:
            result = self._call_llm_json(prompt)
            return result.get('entities', [])
        except:
            return []
    
    def _extract_hyperedges(self, text: str, entities: List[Dict]) -> List[Dict]:
        """抽取超边"""
        entity_info = "\n".join([f"- {e['id']}: {e['name']}" for e in entities])
        
        prompt = f"""从以下文本中抽取涉及3个及以上实体的复杂关系（超边）：

文本：{text[:3000]}

实体：
{entity_info}

输出JSON：
{{"hyperedges": [{{"id": "he{{n}}", "label": "...", "entities": ["e1", "e2", "e3"], "relation_type": "..."}}]}}
"""
        try:
            result = self._call_llm_json(prompt)
            return result.get('hyperedges', [])
        except:
            return []


# ==================== 引擎注册表 ====================

EXTRACTOR_REGISTRY = {
    # RAG-based
    "graphrag": GraphRAGExtractor,
    "hypergraphrag": HypergraphRAGExtractor,
    "lightrag": LightRAGExtractor,
    # Typical
    "kggen": KGGenExtractor,
    "hypergraph": HypergraphExtractor,
}


def get_extractor(
    method: str,
    llm_client = None,
    config: Dict = None
) -> BaseExtractor:
    """获取提取引擎"""
    method_lower = method.lower()
    if method_lower not in EXTRACTOR_REGISTRY:
        available = ', '.join(EXTRACTOR_REGISTRY.keys())
        raise ValueError(f"Unknown method: {method}. Available: {available}")
    return EXTRACTOR_REGISTRY[method_lower](llm_client, config)


def list_methods() -> List[str]:
    """列出所有可用的提取引擎"""
    return list(EXTRACTOR_REGISTRY.keys())
