"""
知识图谱服务 - Phase 12
基于 5W1H 方法论构建想法关联网络
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from uuid import uuid4
import json


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
    SUPPORTS = "supports"      # 支持
    CONFLICTS = "conflicts"    # 冲突


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
            "created_at": self.created_at
        }


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
            "created_at": self.created_at
        }


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.entity_index: Dict[str, Set[str]] = {}  # name -> entity_ids
        
    def add_entity(self, entity: Entity) -> Entity:
        """添加实体"""
        self.entities[entity.id] = entity
        # 更新索引
        name_key = entity.name.lower()
        if name_key not in self.entity_index:
            self.entity_index[name_key] = set()
        self.entity_index[name_key].add(entity.id)
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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
            "stats": {
                "entity_count": len(self.entities),
                "relation_count": len(self.relations)
            }
        }


class KnowledgeGraphService:
    """知识图谱服务 - 基于 5W1H 方法论"""
    
    # 5W1H 关键词模式
    WHO_PATTERNS = ["我", "我们", "团队", "用户", "客户", "开发者", "设计师", "老板", "员工", "负责人"]
    WHAT_PATTERNS = ["开发", "创建", "做", "实现", "构建", "设计", "分析", "研究", "学习"]
    WHY_PATTERNS = ["为了", "因为", "目的", "原因", "动机", "价值", "意义", "好处"]
    WHEN_PATTERNS = ["今天", "明天", "下周", "这个月", "项目", "阶段", "期限", "截止"]
    WHERE_PATTERNS = ["在", "公司", "家里", "线上", "线下", "平台", "市场"]
    HOW_PATTERNS = ["通过", "使用", "采用", "利用", "借助", "方法", "方式", "步骤"]
    
    def __init__(self):
        self.graph = KnowledgeGraph()
        self._entity_counter = 0
        self._relation_counter = 0
        
    def _new_entity_id(self) -> str:
        self._entity_counter += 1
        return f"e{self._entity_counter:04d}"
    
    def _new_relation_id(self) -> str:
        self._relation_counter += 1
        return f"r{self._relation_counter:04d}"
    
    def extract_from_idea(self, idea_content: str, idea_id: str) -> Dict[str, Any]:
        """
        从想法中提取知识图谱实体和关系
        
        Args:
            idea_content: 想法内容
            idea_id: 想法ID
            
        Returns:
            提取结果 {entities, relations}
        """
        entities = []
        relations = []
        
        # 1. 识别 5W1H 实体
        who_entities = self._extract_who(idea_content)
        what_entities = self._extract_what(idea_content)
        why_entities = self._extract_why(idea_content)
        how_entities = self._extract_how(idea_content)
        
        # 2. 添加实体
        entity_ids = {}
        for entity_type, entity_list in [
            ("who", who_entities),
            ("what", what_entities),
            ("why", why_entities),
            ("how", how_entities)
        ]:
            for name in entity_list:
                existing = self.graph.find_entity(name)
                if existing:
                    entity_ids[name] = existing.id
                    if idea_id not in existing.idea_ids:
                        existing.idea_ids.append(idea_id)
                else:
                    entity = Entity(
                        id=self._new_entity_id(),
                        name=name,
                        entity_type=entity_type,
                        idea_ids=[idea_id],
                        confidence=0.8
                    )
                    self.graph.add_entity(entity)
                    entities.append(entity)
                    entity_ids[name] = entity.id
        
        # 3. 建立关系
        # What 与 How 的关系 (实现关系)
        for what in what_entities:
            for how in how_entities:
                if what in entity_ids and how in entity_ids:
                    relation = Relation(
                        id=self._new_relation_id(),
                        source_id=entity_ids[how],
                        target_id=entity_ids[what],
                        relation_type="implements",
                        weight=0.9,
                        evidence=f"从想法「{idea_content[:30]}...」提取",
                        idea_ids=[idea_id]
                    )
                    self.graph.add_relation(relation)
                    relations.append(relation)
        
        # Who 与 What 的关系 (执行关系)
        for who in who_entities:
            for what in what_entities:
                if who in entity_ids and what in entity_ids:
                    relation = Relation(
                        id=self._new_relation_id(),
                        source_id=entity_ids[who],
                        target_id=entity_ids[what],
                        relation_type="depends_on",
                        weight=0.7,
                        evidence=f"从想法「{idea_content[:30]}...」提取",
                        idea_ids=[idea_id]
                    )
                    self.graph.add_relation(relation)
                    relations.append(relation)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relations": [r.to_dict() for r in relations],
            "entity_count": len(entities),
            "relation_count": len(relations)
        }
    
    def _extract_who(self, content: str) -> List[str]:
        """提取 Who 实体"""
        entities = []
        for pattern in self.WHO_PATTERNS:
            if pattern in content:
                # 简单提取附近词语
                idx = content.find(pattern)
                start = max(0, idx - 2)
                end = min(len(content), idx + len(pattern) + 3)
                word = content[start:end].strip()
                if word and word not in entities:
                    entities.append(word)
        return entities[:3]  # 限制数量
    
    def _extract_what(self, content: str) -> List[str]:
        """提取 What 实体"""
        entities = []
        for pattern in self.WHAT_PATTERNS:
            if pattern in content:
                entities.append(pattern)
        return entities[:3]
    
    def _extract_why(self, content: str) -> List[str]:
        """提取 Why 实体"""
        entities = []
        for pattern in self.WHY_PATTERNS:
            if pattern in content:
                entities.append(pattern)
        return entities[:2]
    
    def _extract_how(self, content: str) -> List[str]:
        """提取 How 实体"""
        entities = []
        for pattern in self.HOW_PATTERNS:
            if pattern in content:
                entities.append(pattern)
        return entities[:2]
    
    def find_connections(self, idea_content: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        查找想法之间的关联
        
        Args:
            idea_content: 新想法内容
            max_results: 最大结果数
            
        Returns:
            关联的想法列表
        """
        # 从新想法提取关键词
        new_keywords = set()
        for pattern in self.WHAT_PATTERNS + self.HOW_PATTERNS:
            if pattern in idea_content:
                new_keywords.add(pattern)
        
        if not new_keywords:
            return []
        
        # 在图中搜索相似实体
        connections = []
        for entity in self.graph.entities.values():
            if entity.name in new_keywords:
                # 获取关联的想法
                for rel_idea_id in entity.idea_ids:
                    # 查找通过该想法ID关联的其他实体
                    for rel_entity in self.graph.entities.values():
                        if rel_entity.id != entity.id and rel_idea_id in rel_entity.idea_ids:
                            connections.append({
                                "related_entity": rel_entity.name,
                                "relation_type": "shares_idea",
                                "shared_idea_id": rel_idea_id,
                                "score": 0.8
                            })
        
        # 去重并排序
        seen = set()
        unique_connections = []
        for conn in connections:
            key = conn["shared_idea_id"]
            if key not in seen:
                seen.add(key)
                unique_connections.append(conn)
        
        return unique_connections[:max_results]
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图谱统计"""
        entity_types = {}
        for entity in self.graph.entities.values():
            t = entity.entity_type
            entity_types[t] = entity_types.get(t, 0) + 1
        
        relation_types = {}
        for rel in self.graph.relations.values():
            t = rel.relation_type
            relation_types[t] = relation_types.get(t, 0) + 1
        
        return {
            "total_entities": len(self.graph.entities),
            "total_relations": len(self.graph.relations),
            "entity_types": entity_types,
            "relation_types": relation_types,
            "graph_data": self.graph.to_dict()
        }
    
    def export_graph(self) -> Dict[str, Any]:
        """导出完整图谱"""
        return self.graph.to_dict()


# 全局单例
_knowledge_graph_service: Optional[KnowledgeGraphService] = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """获取知识图谱服务单例"""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service
