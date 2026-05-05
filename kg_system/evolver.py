"""
增量演进系统 - 支持 feed/merge/diff 操作
实现知识的持续扩展和更新
"""

import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class KnowledgePatch:
    """知识变更补丁"""
    id: str
    timestamp: str
    source: str  # 来源文档
    added_entities: List[Dict] = field(default_factory=list)
    added_relations: List[Dict] = field(default_factory=list)
    added_hyperedges: List[Dict] = field(default_factory=list)
    modified_entities: List[Dict] = field(default_factory=list)
    removed_entity_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "added_entities": self.added_entities,
            "added_relations": self.added_relations,
            "added_hyperedges": self.added_hyperedges,
            "modified_entities": self.modified_entities,
            "removed_entity_ids": self.removed_entity_ids,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'KnowledgePatch':
        return cls(
            id=d["id"],
            timestamp=d["timestamp"],
            source=d["source"],
            added_entities=d.get("added_entities", []),
            added_relations=d.get("added_relations", []),
            added_hyperedges=d.get("added_hyperedges", []),
            modified_entities=d.get("modified_entities", []),
            removed_entity_ids=d.get("removed_entity_ids", []),
            metadata=d.get("metadata", {})
        )


@dataclass
class DiffResult:
    """差异对比结果"""
    added: Dict[str, List] = field(default_factory=dict)  # {"entities": [...], "relations": [...]}
    removed: Dict[str, List] = field(default_factory=dict)
    modified: Dict[str, List] = field(default_factory=dict)
    unchanged: Dict[str, List] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged
        }


class IncrementalEvolver:
    """
    增量演进器
    
    支持的操作：
    - feed: 向已有图谱追加新文档
    - merge: 合并多个知识图谱
    - diff: 对比两个知识图谱的差异
    """
    
    def __init__(self, kg_data: dict = None):
        """
        Args:
            kg_data: 初始知识图谱数据
        """
        self.kg_data = kg_data or self._create_empty_kg()
        self.patches: List[KnowledgePatch] = []
        self.entity_index: Dict[str, Dict] = {}  # 用于快速查找
        self._rebuild_index()
    
    def _create_empty_kg(self) -> dict:
        """创建空知识图谱"""
        return {
            "id": f"kg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": "Knowledge Graph",
            "type": "AutoGraph",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "temporal_events": [],
            "spatial_entities": [],
            "trajectories": []
        }
    
    def _rebuild_index(self):
        """重建实体索引"""
        self.entity_index = {}
        for node in self.kg_data.get("nodes", []):
            self.entity_index[node.get("id", "")] = node
        for event in self.kg_data.get("temporal_events", []):
            self.entity_index[event.get("id", "")] = event
        for loc in self.kg_data.get("spatial_entities", []):
            self.entity_index[loc.get("id", "")] = loc
    
    def feed(
        self,
        new_kg_data: dict,
        source: str = "unknown",
        conflict_strategy: str = "keep_existing"
    ) -> KnowledgePatch:
        """
        向图谱追加新知识
        
        Args:
            new_kg_data: 新文档提取的知识图谱
            source: 来源标识
            conflict_strategy: 冲突策略
                - "keep_existing": 保留已有
                - "overwrite": 覆盖
                - "merge": 合并字段
        
        Returns:
            KnowledgePatch: 变更记录
        """
        patch = KnowledgePatch(
            id=f"patch_{len(self.patches) + 1}",
            timestamp=datetime.now().isoformat(),
            source=source
        )
        
        # 1. 处理实体
        existing_ids = {n.get("id") for n in self.kg_data.get("nodes", [])}
        for entity in new_kg_data.get("nodes", []):
            entity_id = entity.get("id", "")
            if entity_id and entity_id not in existing_ids:
                # 新增实体
                patch.added_entities.append(entity)
            elif entity_id and conflict_strategy == "overwrite":
                # 覆盖已有实体
                patch.modified_entities.append({"old": self.entity_index.get(entity_id), "new": entity})
        
        # 2. 处理普通关系
        existing_edges = {
            (e.get("source"), e.get("target"), e.get("relation"))
            for e in self.kg_data.get("edges", [])
        }
        for edge in new_kg_data.get("edges", []):
            key = (edge.get("source"), edge.get("target"), edge.get("relation"))
            if key not in existing_edges:
                patch.added_relations.append(edge)
        
        # 3. 处理超边
        existing_hes = {
            (tuple(h.get("entities", [])), h.get("label"))
            for h in self.kg_data.get("hyperedges", [])
        }
        for he in new_kg_data.get("hyperedges", []):
            key = (tuple(he.get("entities", [])), he.get("label"))
            if key not in existing_hes:
                patch.added_hyperedges.append(he)
        
        # 4. 应用变更
        self._apply_patch(patch)
        self.patches.append(patch)
        
        # 更新元数据
        self.kg_data["updated_at"] = datetime.now().isoformat()
        
        return patch
    
    def _apply_patch(self, patch: KnowledgePatch):
        """应用补丁到图谱"""
        # 添加新实体
        for entity in patch.added_entities:
            if entity.get("id"):
                self.kg_data.setdefault("nodes", []).append(entity)
        
        # 添加新关系
        for relation in patch.added_relations:
            self.kg_data.setdefault("edges", []).append(relation)
        
        # 添加新超边
        for he in patch.added_hyperedges:
            self.kg_data.setdefault("hyperedges", []).append(he)
        
        # 修改实体
        for mod in patch.modified_entities:
            old_entity = mod.get("old", {})
            new_entity = mod.get("new", {})
            for i, node in enumerate(self.kg_data.get("nodes", [])):
                if node.get("id") == old_entity.get("id"):
                    self.kg_data["nodes"][i] = new_entity
                    break
        
        # 删除实体
        for removed_id in patch.removed_entity_ids:
            self.kg_data["nodes"] = [
                n for n in self.kg_data.get("nodes", [])
                if n.get("id") != removed_id
            ]
        
        # 重建索引
        self._rebuild_index()
    
    def merge(self, other: 'IncrementalEvolver', strategy: str = "union") -> 'IncrementalEvolver':
        """
        合并两个知识图谱
        
        Args:
            other: 另一个增量演进器
            strategy: 合并策略
                - "union": 取并集
                - "intersection": 取交集
                - "difference": 差集
        
        Returns:
            新的合并后的IncrementalEvolver
        """
        result = IncrementalEvolver()
        
        if strategy == "union":
            # 合并所有实体
            all_entities = {}
            for node in self.kg_data.get("nodes", []) + other.kg_data.get("nodes", []):
                nid = node.get("id")
                if nid:
                    if nid not in all_entities:
                        all_entities[nid] = node
            
            # 合并所有关系
            all_edges = {}
            for edge in self.kg_data.get("edges", []) + other.kg_data.get("edges", []):
                eid = edge.get("id") or f"{edge.get('source')}_{edge.get('target')}_{edge.get('relation')}"
                if eid not in all_edges:
                    all_edges[eid] = edge
            
            # 合并所有超边
            all_hes = {}
            for he in self.kg_data.get("hyperedges", []) + other.kg_data.get("hyperedges", []):
                hid = he.get("id") or hashlib.md5(str(he.get("entities")).encode()).hexdigest()[:8]
                if hid not in all_hes:
                    all_hes[hid] = he
            
            result.kg_data["nodes"] = list(all_entities.values())
            result.kg_data["edges"] = list(all_edges.values())
            result.kg_data["hyperedges"] = list(all_hes.values())
            
        elif strategy == "intersection":
            # 只保留两者都有的
            self_ids = {n.get("id") for n in self.kg_data.get("nodes", [])}
            for node in other.kg_data.get("nodes", []):
                if node.get("id") in self_ids:
                    result.kg_data.setdefault("nodes", []).append(node)
            
            self_edges = {
                (e.get("source"), e.get("target"), e.get("relation"))
                for e in self.kg_data.get("edges", [])
            }
            for edge in other.kg_data.get("edges", []):
                key = (edge.get("source"), edge.get("target"), edge.get("relation"))
                if key in self_edges:
                    result.kg_data.setdefault("edges", []).append(edge)
        
        result._rebuild_index()
        return result
    
    def diff(self, other: 'IncrementalEvolver') -> DiffResult:
        """
        对比两个知识图谱的差异
        
        Returns:
            DiffResult: 差异结果
        """
        result = DiffResult()
        
        # 获取所有ID
        self_entity_ids = {n.get("id") for n in self.kg_data.get("nodes", [])}
        other_entity_ids = {n.get("id") for n in other.kg_data.get("nodes", [])}
        
        # 计算差异
        added_ids = other_entity_ids - self_entity_ids
        removed_ids = self_entity_ids - other_entity_ids
        common_ids = self_entity_ids & other_entity_ids
        
        result.added["entities"] = [n for n in other.kg_data.get("nodes", []) if n.get("id") in added_ids]
        result.removed["entities"] = [n for n in self.kg_data.get("nodes", []) if n.get("id") in removed_ids]
        result.unchanged["entities"] = [n for n in self.kg_data.get("nodes", []) if n.get("id") in common_ids]
        
        # 检查修改
        for node in result.unchanged["entities"]:
            other_node = other.entity_index.get(node.get("id"))
            if other_node and node != other_node:
                result.modified.setdefault("entities", []).append({
                    "id": node.get("id"),
                    "old": node,
                    "new": other_node
                })
        
        # 关系差异
        self_edge_keys = {
            (e.get("source"), e.get("target"), e.get("relation"))
            for e in self.kg_data.get("edges", [])
        }
        other_edge_keys = {
            (e.get("source"), e.get("target"), e.get("relation"))
            for e in other.kg_data.get("edges", [])
        }
        
        added_edges = other_edge_keys - self_edge_keys
        removed_edges = self_edge_keys - other_edge_keys
        
        result.added["relations"] = [
            e for e in other.kg_data.get("edges", [])
            if (e.get("source"), e.get("target"), e.get("relation")) in added_edges
        ]
        result.removed["relations"] = [
            e for e in self.kg_data.get("edges", [])
            if (e.get("source"), e.get("target"), e.get("relation")) in removed_edges
        ]
        
        return result
    
    def save(self, filepath: str):
        """保存知识图谱到文件"""
        data = {
            "kg": self.kg_data,
            "patches": [p.to_dict() for p in self.patches]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, filepath: str):
        """从文件加载知识图谱"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.kg_data = data.get("kg", {})
        self.patches = [KnowledgePatch.from_dict(p) for p in data.get("patches", [])]
        self._rebuild_index()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "entity_count": len(self.kg_data.get("nodes", [])),
            "relation_count": len(self.kg_data.get("edges", [])),
            "hyperedge_count": len(self.kg_data.get("hyperedges", [])),
            "temporal_event_count": len(self.kg_data.get("temporal_events", [])),
            "spatial_entity_count": len(self.kg_data.get("spatial_entities", [])),
            "patch_count": len(self.patches),
            "created_at": self.kg_data.get("created_at"),
            "updated_at": self.kg_data.get("updated_at")
        }


def merge_knowledge_graphs(graphs: List[dict], strategy: str = "union") -> dict:
    """
    合并多个知识图谱（便捷函数）
    
    Args:
        graphs: 图谱数据列表
        strategy: 合并策略
    
    Returns:
        合并后的图谱数据
    """
    evolvers = [IncrementalEvolver(g) for g in graphs]
    
    result = evolvers[0]
    for e in evolvers[1:]:
        result = result.merge(e, strategy)
    
    return result.kg_data
