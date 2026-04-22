"""
知识图谱服务 - Phase 12 增强
基于 5W1H 方法论构建想法关联网络

增强功能：
- LLM自动实体提取
- 关系推理引擎
- 图谱可视化数据结构
- 语义搜索
- 与想法系统深度集成
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple, Callable
from datetime import datetime
from enum import Enum
from uuid import uuid4
import json
import re
from collections import defaultdict


class EntityType(Enum):
    """实体类型 (Who/What/Why/When/Where/How)"""
    WHO = "who"           # 人物/角色
    WHAT = "what"         # 事件/对象
    WHY = "why"           # 目的/原因
    WHEN = "when"         # 时间
    WHERE = "where"       # 地点
    HOW = "how"           # 方式/方法
    CONCEPT = "concept"   # 概念
    PROJECT = "project"   # 项目
    TOPIC = "topic"       # 话题


class RelationType(Enum):
    """关系类型"""
    IS_A = "is_a"              # 是一种
    PART_OF = "part_of"        # 是...的一部分
    DEPENDS_ON = "depends_on"  # 依赖于
    RELATES_TO = "relates_to"  # 与...相关
    SIMILAR_TO = "similar_to"  # 类似于
    LEADS_TO = "leads_to"      # 导致
    COMBINES = "combines"      # 结合
    IMPLEMENTS = "implements"  # 实现
    SUPPORTS = "supports"     # 支持
    CONFLICTS = "conflicts"    # 冲突
    CAUSED_BY = "caused_by"    # 由...引起
    ENABLES = "enables"        # 使能够
    TEMPORAL_BEFORE = "temporal_before"  # 时间顺序：之前
    TEMPORAL_AFTER = "temporal_after"    # 时间顺序：之后


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    entity_type: str
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    idea_ids: List[str] = field(default_factory=list)  # 来源想法
    confidence: float = 1.0
    created_at: str = ""
    aliases: List[str] = field(default_factory=list)  # 同义词/别名
    embeddings: List[float] = field(default_factory=list)  # 向量表示
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "description": self.description,
            "properties": self.properties,
            "idea_ids": self.idea_ids,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "aliases": self.aliases
        }
    
    def matches(self, query: str) -> bool:
        """检查是否匹配查询"""
        query_lower = query.lower()
        if query_lower in self.name.lower():
            return True
        for alias in self.aliases:
            if query_lower in alias.lower():
                return True
        return False


@dataclass
class Relation:
    """知识图谱关系"""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    evidence: str = ""  # 证据/来源
    idea_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    temporal_info: Dict[str, Any] = field(default_factory=dict)  # 时间信息
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type,
            "weight": self.weight,
            "evidence": self.evidence,
            "idea_ids": self.idea_ids,
            "created_at": self.created_at,
            "temporal_info": self.temporal_info
        }


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.entity_index: Dict[str, Set[str]] = {}  # name -> entity_ids
        self.type_index: Dict[str, Set[str]] = defaultdict(set)  # type -> entity_ids
        self.idea_index: Dict[str, Set[str]] = {}  # idea_id -> entity_ids
        
    def add_entity(self, entity: Entity) -> Entity:
        """添加实体"""
        self.entities[entity.id] = entity
        # 更新名称索引
        name_key = entity.name.lower()
        if name_key not in self.entity_index:
            self.entity_index[name_key] = set()
        self.entity_index[name_key].add(entity.id)
        
        # 更新类型索引
        self.type_index[entity.entity_type].add(entity.id)
        
        # 更新想法索引
        for idea_id in entity.idea_ids:
            if idea_id not in self.idea_index:
                self.idea_index[idea_id] = set()
            self.idea_index[idea_id].add(entity.id)
        
        return entity
    
    def add_relation(self, relation: Relation) -> Relation:
        """添加关系"""
        self.relations[relation.id] = relation
        return relation
    
    def find_entity(self, name: str) -> Optional[Entity]:
        """通过名称查找实体"""
        matches = self.entity_index.get(name.lower(), set())
        if matches:
            return self.entities.get(list(matches)[0])
        return None
    
    def find_entities_by_type(self, entity_type: str) -> List[Entity]:
        """按类型查找实体"""
        entity_ids = self.type_index.get(entity_type, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
    
    def find_entities_by_idea(self, idea_id: str) -> List[Entity]:
        """查找某个想法相关的所有实体"""
        entity_ids = self.idea_index.get(idea_id, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
    
    def get_related_entities(self, entity_id: str, depth: int = 1) -> List[Tuple[Entity, Relation]]:
        """获取关联实体"""
        results = []
        visited = {entity_id}
        queue = [(entity_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue
                
            # 查找关系
            for rel in self.relations.values():
                if rel.source_id == current_id and rel.target_id not in visited:
                    target = self.entities.get(rel.target_id)
                    if target:
                        results.append((target, rel))
                        visited.add(rel.target_id)
                        queue.append((rel.target_id, current_depth + 1))
                        
                elif rel.target_id == current_id and rel.source_id not in visited:
                    source = self.entities.get(rel.source_id)
                    if source:
                        results.append((source, rel))
                        visited.add(rel.source_id)
                        queue.append((rel.source_id, current_depth + 1))
        
        return results
    
    def find_paths(self, source_id: str, target_id: str, max_depth: int = 3) -> List[List[Tuple[str, str]]]:
        """查找两个实体之间的路径"""
        if source_id == target_id:
            return [[(source_id, "")]]
        
        paths = []
        queue = [(source_id, [source_id], [])]  # (current_id, path, relation_types)
        
        while queue:
            current, path, rel_types = queue.pop(0)
            
            if len(path) > max_depth + 1:
                continue
            
            for rel in self.relations.values():
                next_id = None
                if rel.source_id == current and rel.target_id not in path:
                    next_id = rel.target_id
                elif rel.target_id == current and rel.source_id not in path:
                    next_id = rel.source_id
                
                if next_id:
                    new_path = path + [next_id]
                    new_rel_types = rel_types + [rel.relation_type]
                    
                    if next_id == target_id:
                        path_edges = list(zip(path, rel_types)) + [(next_id, rel.relation_type)]
                        paths.append(path_edges[:-1])  # 去掉最后一个空关系
                    else:
                        queue.append((next_id, new_path, new_rel_types))
        
        return paths
    
    def get_subgraph(self, entity_ids: List[str], depth: int = 1) -> Dict[str, Any]:
        """获取子图（指定实体及其关联）"""
        subgraph_entities = set(entity_ids)
        subgraph_relations = []
        
        # BFS扩展
        queue = list(entity_ids)
        visited = set(entity_ids)
        
        for _ in range(depth):
            next_queue = []
            for entity_id in queue:
                for rel in self.relations.values():
                    if rel.source_id == entity_id and rel.target_id not in visited:
                        subgraph_entities.add(rel.target_id)
                        subgraph_relations.append(rel)
                        next_queue.append(rel.target_id)
                        visited.add(rel.target_id)
                    elif rel.target_id == entity_id and rel.source_id not in visited:
                        subgraph_entities.add(rel.source_id)
                        subgraph_relations.append(rel)
                        next_queue.append(rel.source_id)
                        visited.add(rel.source_id)
            queue = next_queue
        
        return {
            "entities": [self.entities[eid].to_dict() for eid in subgraph_entities if eid in self.entities],
            "relations": [r.to_dict() for r in subgraph_relations]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
            "stats": {
                "entity_count": len(self.entities),
                "relation_count": len(self.relations)
            }
        }


class EntityExtractor:
    """LLM实体提取器 - 5W1H自动提取"""
    
    # 5W1H 关键词模式
    WHO_PATTERNS = [
        r"(?:我|我们|团队|用户|客户|开发者|设计师|老板|员工|负责人|专家|经理)",
        r"(?<=\s)[A-Z][a-z]+(?:[A-Z][a-z]+)*",  # 大写开头的专有名词
    ]
    
    WHAT_PATTERNS = [
        r"(?:开发|创建|做|实现|构建|设计|分析|研究|学习|计划|目标|任务|项目|产品)",
        r"(?:系统|应用|APP|平台|工具|服务|功能|模块|组件)",
    ]
    
    WHY_PATTERNS = [
        r"(?:为了|因为|原因|目的|动机|价值|意义|好处|提升|改进|解决)",
        r"(?:提高|增加|减少|优化|改善)",
    ]
    
    WHEN_PATTERNS = [
        r"(?:今天|明天|下周|这个月|今年|明年|现在|稍后|立即|尽快)",
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d+天|\d+周|\d+个月",
    ]
    
    WHERE_PATTERNS = [
        r"(?:在|到|位于)(?:公司|家里|线上|线下|平台|市场|云端|本地)",
        r"(?:北京|上海|深圳|杭州|广州|海外|国内)",
    ]
    
    HOW_PATTERNS = [
        r"(?:通过|使用|采用|利用|借助|方法|方式|步骤|流程|计划)",
        r"(?:Python|Java|JS|React|Vue|API|数据库|云服务)",
    ]
    
    # 行业特定词汇 (安全工程领域)
    SAFETY_PATTERNS = [
        r"(?:消防|危化|安全|应急|预案|演练|检查|隐患|整改)",
        r"(?:灭火器|疏散|急救|AED|心肺复苏)",
    ]
    
    @classmethod
    def extract_5w1h(cls, content: str) -> Dict[str, List[str]]:
        """从文本中提取5W1H实体"""
        result = {
            "who": [],
            "what": [],
            "why": [],
            "when": [],
            "where": [],
            "how": []
        }
        
        # 提取 Who
        for pattern in cls.WHO_PATTERNS:
            matches = re.findall(pattern, content)
            result["who"].extend(matches)
        
        # 提取 What
        for pattern in cls.WHAT_PATTERNS:
            matches = re.findall(pattern, content)
            result["what"].extend(matches)
        
        # 提取 Why
        for pattern in cls.WHY_PATTERNS:
            matches = re.findall(pattern, content)
            result["why"].extend(matches)
        
        # 提取 When
        for pattern in cls.WHEN_PATTERNS:
            matches = re.findall(pattern, content)
            result["when"].extend(matches)
        
        # 提取 Where
        for pattern in cls.WHERE_PATTERNS:
            matches = re.findall(pattern, content)
            result["when"].extend(matches)  # 位置信息放入 where
        
        # 提取 How
        for pattern in cls.HOW_PATTERNS:
            matches = re.findall(pattern, content)
            result["how"].extend(matches)
        
        # 安全领域特殊提取
        for pattern in cls.SAFETY_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                result["what"].extend(matches)
        
        # 去重
        for key in result:
            result[key] = list(set(result[key]))[:5]  # 每类最多5个
        
        return result
    
    @classmethod
    def extract_with_llm(cls, content: str, llm_func: Callable = None) -> Dict[str, List[Dict[str, Any]]]:
        """使用LLM进行更智能的实体提取"""
        if llm_func is None:
            # 回退到规则提取
            raw = cls.extract_5w1h(content)
            return {
                "who": [{"name": n, "confidence": 0.7} for n in raw["who"]],
                "what": [{"name": n, "confidence": 0.8} for n in raw["what"]],
                "why": [{"name": n, "confidence": 0.6} for n in raw["why"]],
                "when": [{"name": n, "confidence": 0.7} for n in raw["when"]],
                "where": [{"name": n, "confidence": 0.7} for n in raw["where"]],
                "how": [{"name": n, "confidence": 0.7} for n in raw["how"]],
            }
        
        # LLM增强提取
        prompt = f"""从以下文本中提取5W1H实体，并以JSON格式返回：

文本：{content}

要求：
- who: 人物、角色、组织（如"我"、"团队"、"用户"）
- what: 事件、对象、任务（如"开发APP"、"数据分析"）
- why: 目的、原因、价值（如"提高效率"、"解决问题"）
- when: 时间、期限、阶段（如"明天"、"项目周期"）
- where: 地点、平台、环境（如"公司"、"线上"）
- how: 方法、方式、工具（如"使用Python"、"通过API"）

返回格式：
{{
  "who": ["实体1", "实体2"],
  "what": ["实体1", "实体2"],
  "why": ["实体1"],
  "when": ["实体1"],
  "where": ["实体1"],
  "how": ["实体1", "实体2"]
}}
"""
        
        try:
            result_text = llm_func(prompt)
            # 解析JSON
            import json
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start != -1 and end != 0:
                data = json.loads(result_text[start:end])
                return {
                    k: [{"name": n, "confidence": 0.9} for n in v] 
                    for k, v in data.items()
                }
        except Exception:
            pass
        
        # 回退到规则
        return cls.extract_with_llm(content, None)


class RelationReasoner:
    """关系推理引擎 - 基于共现和时间顺序"""
    
    # 共现关系推断
    CO_OCCUR_WEIGHT = 0.7
    
    # 时间指示词
    TEMPORAL_BEFORE_WORDS = ["之前", "先", "首先", "前提", "基础", "依赖"]
    TEMPORAL_AFTER_WORDS = ["之后", "然后", "接着", "导致", "产生", "结果是"]
    
    @classmethod
    def infer_from_cooccurrence(cls, entities: List[Dict], idea_id: str, content: str) -> List[Dict]:
        """基于共现推断关系"""
        relations = []
        
        # 按类型分组
        by_type = defaultdict(list)
        for e in entities:
            by_type[e["type"]].append(e)
        
        # Who-What: 执行关系
        for who in by_type.get("who", []):
            for what in by_type.get("what", []):
                relations.append({
                    "source": who["id"],
                    "target": what["id"],
                    "type": "depends_on",
                    "weight": 0.8,
                    "evidence": f"'{who['name']}' 执行 '{what['name']}'",
                    "idea_ids": [idea_id]
                })
        
        # What-How: 实现关系
        for what in by_type.get("what", []):
            for how in by_type.get("how", []):
                relations.append({
                    "source": how["id"],
                    "target": what["id"],
                    "type": "implements",
                    "weight": 0.9,
                    "evidence": f"通过 '{how['name']}' 实现 '{what['name']}'",
                    "idea_ids": [idea_id]
                })
        
        # Why-What: 动机关系
        for why in by_type.get("why", []):
            for what in by_type.get("what", []):
                relations.append({
                    "source": why["id"],
                    "target": what["id"],
                    "type": "leads_to",
                    "weight": 0.8,
                    "evidence": f"'{why['name']}' 驱动 '{what['name']}'",
                    "idea_ids": [idea_id]
                })
        
        return relations
    
    @classmethod
    def infer_temporal_relations(cls, content: str, entities: List[Dict], idea_id: str) -> List[Dict]:
        """基于时间顺序推断关系"""
        relations = []
        content_lower = content.lower()
        
        # 检查时间指示词
        has_before = any(w in content_lower for w in cls.TEMPORAL_BEFORE_WORDS)
        has_after = any(w in content_lower for w in cls.TEMPORAL_AFTER_WORDS)
        
        if has_before:
            # 提取"之前"部分的内容
            before_idx = min([content_lower.find(w) for w in cls.TEMPORAL_BEFORE_WORDS if w in content_lower])
            before_content = content[:before_idx]
            
            before_entities = EntityExtractor.extract_5w1h(before_content)
            for etype in ["who", "what", "how"]:
                for name in before_entities.get(etype, [])[:2]:
                    # 查找对应的实体
                    for e in entities:
                        if e["name"] == name or name in e.get("aliases", []):
                            relations.append({
                                "source": e["id"],
                                "target": "",  # 待填充
                                "type": "temporal_before",
                                "weight": 0.6,
                                "evidence": f"'{name}' 发生在之前",
                                "temporal_info": {"phase": "preparation"}
                            })
        
        if has_after:
            # 提取"之后"部分的内容
            after_idx = max([content_lower.find(w) for w in cls.TEMPORAL_AFTER_WORDS if w in content_lower])
            after_content = content[after_idx:]
            
            after_entities = EntityExtractor.extract_5w1h(after_content)
            for etype in ["what", "who"]:
                for name in after_entities.get(etype, [])[:2]:
                    for e in entities:
                        if e["name"] == name or name in e.get("aliases", []):
                            relations.append({
                                "source": "",
                                "target": e["id"],
                                "type": "temporal_after",
                                "weight": 0.6,
                                "evidence": f"'{name}' 发生在之后",
                                "temporal_info": {"phase": "outcome"}
                            })
        
        return relations
    
    @classmethod
    def infer_semantic_relations(cls, entities: List[Dict], content: str, idea_id: str) -> List[Dict]:
        """基于语义相似性推断关系"""
        relations = []
        
        # 关键词共现分析
        keywords = set()
        for pattern in EntityExtractor.WHAT_PATTERNS + EntityExtractor.HOW_PATTERNS:
            matches = re.findall(pattern, content)
            keywords.update(matches)
        
        # 安全领域关系推断
        safety_terms = ["消防", "危化", "安全", "应急"]
        safety_mentioned = [t for t in safety_terms if t in content]
        
        for entity in entities:
            entity_name = entity.get("name", "")
            if entity_name in safety_mentioned:
                # 安全相关的实体
                for other in entities:
                    other_name = other.get("name", "")
                    if other.get("id") != entity.get("id") and other.get("type") == "what":
                        relations.append({
                            "source": entity.get("id", ""),
                            "target": other.get("id", ""),
                            "type": "supports",
                            "weight": 0.7,
                            "evidence": f"'{entity_name}' 支持 '{other_name}'",
                            "idea_ids": [idea_id]
                        })
        
        return relations


class GraphVisualizer:
    """图谱可视化数据结构生成器"""
    
    @classmethod
    def to_d3_json(cls, graph: KnowledgeGraph, focus_entity_id: str = None) -> Dict[str, Any]:
        """转换为 D3.js 可视化格式"""
        nodes = []
        links = []
        
        entities_to_show = list(graph.entities.values())
        
        # 如果有焦点实体，显示其子图
        if focus_entity_id:
            related = graph.get_related_entities(focus_entity_id, depth=2)
            related_ids = {e[0].id for e in related}
            related_ids.add(focus_entity_id)
            entities_to_show = [e for e in entities_to_show if e.id in related_ids]
        
        # 生成节点
        for entity in entities_to_show:
            nodes.append({
                "id": entity.id,
                "label": entity.name,
                "type": entity.entity_type,
                "group": entity.entity_type,
                "count": len(entity.idea_ids),
                "confidence": entity.confidence
            })
        
        # 生成边
        entity_ids = {e.id for e in entities_to_show}
        for relation in graph.relations.values():
            if relation.source_id in entity_ids and relation.target_id in entity_ids:
                links.append({
                    "source": relation.source_id,
                    "target": relation.target_id,
                    "type": relation.relation_type,
                    "weight": relation.weight,
                    "label": relation.relation_type
                })
        
        return {
            "nodes": nodes,
            "links": links
        }
    
    @classmethod
    def to_cytoscape_json(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        """转换为 Cytoscape.js 格式"""
        elements = {"nodes": [], "edges": []}
        
        for entity in graph.entities.values():
            elements["nodes"].append({
                "data": {
                    "id": entity.id,
                    "label": entity.name,
                    "type": entity.entity_type
                }
            })
        
        for relation in graph.relations.values():
            elements["edges"].append({
                "data": {
                    "id": relation.id,
                    "source": relation.source_id,
                    "target": relation.target_id,
                    "label": relation.relation_type,
                    "weight": relation.weight
                }
            })
        
        return elements
    
    @classmethod
    def to_tree_format(cls, graph: KnowledgeGraph, root_id: str = None) -> Dict[str, Any]:
        """转换为树形结构（用于思维导图）"""
        if not root_id:
            # 找到根节点（没有入边的实体）
            has_incoming = {r.target_id for r in graph.relations.values()}
            roots = [e for e in graph.entities.values() if e.id not in has_incoming]
            if roots:
                root = roots[0]
            else:
                root = list(graph.entities.values())[0] if graph.entities else None
        else:
            root = graph.entities.get(root_id)
        
        if not root:
            return {"nodes": [], "edges": []}
        
        def build_tree(entity_id: str, depth: int = 0) -> Dict[str, Any]:
            entity = graph.entities.get(entity_id)
            if not entity:
                return None
            
            node = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type,
                "depth": depth,
                "children": []
            }
            
            for relation in graph.relations.values():
                if relation.source_id == entity_id and depth < 2:
                    child = build_tree(relation.target_id, depth + 1)
                    if child:
                        node["children"].append(child)
            
            return node
        
        return {"root": build_tree(root.id)}
    
    @classmethod
    def get_statistics(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        """生成统计信息"""
        entity_types = defaultdict(int)
        relation_types = defaultdict(int)
        degree_dist = defaultdict(int)
        
        for entity in graph.entities.values():
            entity_types[entity.entity_type] += 1
            degree = sum(1 for r in graph.relations.values() 
                        if r.source_id == entity.id or r.target_id == entity.id)
            degree_dist[degree] += 1
        
        for relation in graph.relations.values():
            relation_types[relation.relation_type] += 1
        
        return {
            "entity_count": len(graph.entities),
            "relation_count": len(graph.relations),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "degree_distribution": dict(degree_dist),
            "avg_degree": sum(degree_dist.keys()) / max(len(degree_dist), 1),
            "density": len(graph.relations) / max(len(graph.entities) * (len(graph.entities) - 1), 1)
        }


class SemanticSearch:
    """语义搜索 - 支持自然语言查询"""
    
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self._keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self._rebuild_keyword_index()
    
    def _rebuild_keyword_index(self):
        """重建关键词索引"""
        self._keyword_index.clear()
        for entity in self.graph.entities.values():
            # 索引名称和别名
            keywords = [entity.name.lower()]
            keywords.extend([a.lower() for a in entity.aliases])
            keywords.extend(entity.name.lower().split())
            
            for keyword in keywords:
                if len(keyword) >= 2:
                    self._keyword_index[keyword].add(entity.id)
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """语义搜索"""
        query_lower = query.lower()
        results = []
        seen_ids = set()
        
        # 1. 精确匹配名称
        for entity in self.graph.entities.values():
            if query_lower in entity.name.lower():
                results.append({
                    "entity": entity,
                    "score": 1.0,
                    "match_type": "name_exact"
                })
                seen_ids.add(entity.id)
        
        # 2. 匹配别名
        for entity in self.graph.entities.values():
            if entity.id in seen_ids:
                continue
            for alias in entity.aliases:
                if query_lower in alias.lower():
                    results.append({
                        "entity": entity,
                        "score": 0.9,
                        "match_type": "alias"
                    })
                    seen_ids.add(entity.id)
                    break
        
        # 3. 关键词匹配
        query_words = query_lower.split()
        for entity in self.graph.entities.values():
            if entity.id in seen_ids:
                continue
            
            matches = 0
            for word in query_words:
                if word in entity.name.lower() or any(word in a.lower() for a in entity.aliases):
                    matches += 1
            
            if matches > 0:
                score = matches / len(query_words) * 0.8
                results.append({
                    "entity": entity,
                    "score": score,
                    "match_type": "keyword"
                })
                seen_ids.add(entity.id)
        
        # 4. 类型匹配
        type_match = query_lower.strip()
        for etype in ["who", "what", "why", "when", "where", "how"]:
            if etype in type_match or f"{etype}s" in type_match or f"{etype}实体" in type_match:
                entities = self.graph.find_entities_by_type(etype)
                for entity in entities:
                    if entity.id not in seen_ids:
                        results.append({
                            "entity": entity,
                            "score": 0.7,
                            "match_type": "type"
                        })
                        seen_ids.add(entity.id)
        
        # 排序并返回
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def find_related(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """查找与查询相关的内容"""
        search_results = self.search(query, limit=limit)
        related = []
        
        for result in search_results:
            entity = result["entity"]
            relations = self.graph.get_related_entities(entity.id, depth=1)
            
            for related_entity, rel in relations:
                related.append({
                    "from": entity.name,
                    "to": related_entity.name,
                    "relation": rel.relation_type,
                    "weight": rel.weight
                })
        
        return related


class KnowledgeGraphService:
    """知识图谱服务 - 基于 5W1H 方法论"""
    
    def __init__(self):
        self.graph = KnowledgeGraph()
        self.extractor = EntityExtractor()
        self.reasoner = RelationReasoner()
        self.search_engine = SemanticSearch(self.graph)
        self._entity_counter = 0
        self._relation_counter = 0
        self._llm_func: Optional[Callable] = None
    
    def set_llm_function(self, func: Callable):
        """设置LLM函数用于增强实体提取"""
        self._llm_func = func
    
    def _new_entity_id(self) -> str:
        self._entity_counter += 1
        return f"e{self._entity_counter:04d}"
    
    def _new_relation_id(self) -> str:
        self._relation_counter += 1
        return f"r{self._relation_counter:04d}"
    
    def extract_from_idea(self, idea_content: str, idea_id: str, use_llm: bool = False) -> Dict[str, Any]:
        """
        从想法中提取知识图谱实体和关系
        
        Args:
            idea_content: 想法内容
            idea_id: 想法ID
            use_llm: 是否使用LLM增强提取
            
        Returns:
            提取结果 {entities, relations}
        """
        entities = []
        relations = []
        
        # 1. 提取5W1H实体
        if use_llm and self._llm_func:
            extracted = self.extractor.extract_with_llm(idea_content, self._llm_func)
        else:
            raw = self.extractor.extract_5w1h(idea_content)
            extracted = {
                k: [{"name": n, "confidence": 0.7} for n in v]
                for k, v in raw.items()
            }
        
        # 2. 添加实体
        entity_ids = {}
        for entity_type, entity_list in extracted.items():
            for item in entity_list:
                name = item["name"]
                confidence = item.get("confidence", 0.7)
                
                # 检查是否已存在
                existing = self.graph.find_entity(name)
                if existing:
                    entity_ids[name] = existing.id
                    if idea_id not in existing.idea_ids:
                        existing.idea_ids.append(idea_id)
                        existing.confidence = max(existing.confidence, confidence)
                else:
                    entity = Entity(
                        id=self._new_entity_id(),
                        name=name,
                        entity_type=entity_type,
                        idea_ids=[idea_id],
                        confidence=confidence
                    )
                    self.graph.add_entity(entity)
                    entities.append(entity)
                    entity_ids[name] = entity.id
        
        # 3. 关系推理
        all_entities = [e.to_dict() for e in entities]
        
        # 共现关系
        co_relations = self.reasoner.infer_from_cooccurrence(
            all_entities, idea_id, idea_content
        )
        
        # 时间关系
        temporal_relations = self.reasoner.infer_temporal_relations(
            idea_content, all_entities, idea_id
        )
        
        # 语义关系
        semantic_relations = self.reasoner.infer_semantic_relations(
            all_entities, idea_content, idea_id
        )
        
        # 添加关系
        for rel_data in co_relations + semantic_relations:
            if rel_data["source"] and rel_data["target"]:
                relation = Relation(
                    id=self._new_relation_id(),
                    source_id=rel_data["source"],
                    target_id=rel_data["target"],
                    relation_type=rel_data["type"],
                    weight=rel_data["weight"],
                    evidence=rel_data["evidence"],
                    idea_ids=[idea_id]
                )
                self.graph.add_relation(relation)
                relations.append(relation)
        
        # 时间关系特殊处理
        for rel_data in temporal_relations:
            if rel_data["source"] and rel_data["target"]:
                relation = Relation(
                    id=self._new_relation_id(),
                    source_id=rel_data["source"],
                    target_id=rel_data["target"],
                    relation_type=rel_data["type"],
                    weight=rel_data["weight"],
                    evidence=rel_data["evidence"],
                    idea_ids=[idea_id],
                    temporal_info=rel_data.get("temporal_info", {})
                )
                self.graph.add_relation(relation)
                relations.append(relation)
        
        # 更新搜索索引
        self.search_engine = SemanticSearch(self.graph)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relations": [r.to_dict() for r in relations],
            "entity_count": len(entities),
            "relation_count": len(relations)
        }
    
    def find_connections(self, idea_content: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        查找想法之间的关联
        """
        search_results = self.search_engine.search(idea_content, limit=max_results)
        connections = []
        
        for result in search_results:
            entity = result["entity"]
            for rel_idea_id in entity.idea_ids:
                # 查找共享想法的其他实体
                related_entities = self.graph.find_entities_by_idea(rel_idea_id)
                for rel_entity in related_entities:
                    if rel_entity.id != entity.id:
                        connections.append({
                            "related_entity": rel_entity.to_dict(),
                            "relation_type": "shares_idea",
                            "shared_idea_id": rel_idea_id,
                            "score": result["score"] * 0.8
                        })
        
        # 去重
        seen = set()
        unique_connections = []
        for conn in connections:
            key = conn["shared_idea_id"]
            if key not in seen:
                seen.add(key)
                unique_connections.append(conn)
        
        return unique_connections[:max_results]
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """语义搜索"""
        return self.search_engine.search(query, limit=limit)
    
    def get_visualization_data(self, format: str = "d3", focus_entity_id: str = None) -> Dict[str, Any]:
        """获取可视化数据"""
        if format == "d3":
            return GraphVisualizer.to_d3_json(self.graph, focus_entity_id)
        elif format == "cytoscape":
            return GraphVisualizer.to_cytoscape_json(self.graph)
        elif format == "tree":
            return GraphVisualizer.to_tree_format(self.graph, focus_entity_id)
        else:
            return self.graph.to_dict()
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图谱统计"""
        stats = GraphVisualizer.get_statistics(self.graph)
        return {
            "total_entities": stats.get("entity_count", 0),
            "total_relations": stats.get("relation_count", 0),
            "entity_types": stats.get("entity_types", {}),
            "relation_types": stats.get("relation_types", {}),
            "density": stats.get("density", 0),
            "avg_degree": stats.get("avg_degree", 0),
            "degree_distribution": stats.get("degree_distribution", {})
        }
    
    def get_entity_subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取实体子图"""
        return self.graph.get_subgraph([entity_id], depth)
    
    def find_paths(self, entity1_name: str, entity2_name: str) -> List[List[Dict]]:
        """查找两个实体之间的路径"""
        e1 = self.graph.find_entity(entity1_name)
        e2 = self.graph.find_entity(entity2_name)
        
        if not e1 or not e2:
            return []
        
        paths = self.graph.find_paths(e1.id, e2.id)
        
        result = []
        for path in paths:
            path_info = []
            for i, (entity_id, rel_type) in enumerate(path):
                entity = self.graph.entities.get(entity_id)
                if entity:
                    path_info.append({
                        "entity": entity.name,
                        "type": entity.entity_type,
                        "relation": rel_type if i < len(path) - 1 else ""
                    })
            result.append(path_info)
        
        return result
    
    def export_graph(self) -> Dict[str, Any]:
        """导出完整图谱"""
        return self.graph.to_dict()
    
    def import_graph(self, data: Dict[str, Any]):
        """导入图谱"""
        # 清除现有数据
        self.graph = KnowledgeGraph()
        self._entity_counter = 0
        self._relation_counter = 0
        
        # 导入实体
        for entity_data in data.get("entities", []):
            entity = Entity(
                id=entity_data["id"],
                name=entity_data["name"],
                entity_type=entity_data["type"],
                description=entity_data.get("description", ""),
                properties=entity_data.get("properties", {}),
                idea_ids=entity_data.get("idea_ids", []),
                confidence=entity_data.get("confidence", 1.0),
                aliases=entity_data.get("aliases", [])
            )
            self.graph.add_entity(entity)
            
            # 更新计数器
            try:
                num = int(entity_data["id"][1:])
                self._entity_counter = max(self._entity_counter, num)
            except:
                pass
        
        # 导入关系
        for rel_data in data.get("relations", []):
            relation = Relation(
                id=rel_data["id"],
                source_id=rel_data["source"],
                target_id=rel_data["target"],
                relation_type=rel_data["type"],
                weight=rel_data.get("weight", 1.0),
                evidence=rel_data.get("evidence", ""),
                idea_ids=rel_data.get("idea_ids", [])
            )
            self.graph.add_relation(relation)
            
            try:
                num = int(rel_data["id"][1:])
                self._relation_counter = max(self._relation_counter, num)
            except:
                pass
        
        # 更新搜索索引
        self.search_engine = SemanticSearch(self.graph)


# 全局单例
_knowledge_graph_service: Optional[KnowledgeGraphService] = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """获取知识图谱服务单例"""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service


def reset_knowledge_graph_service():
    """重置知识图谱服务单例（用于测试）"""
    global _knowledge_graph_service
    _knowledge_graph_service = None