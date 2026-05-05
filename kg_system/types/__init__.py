"""
知识图谱类型系统 - 基于Hyper-Extract的Auto-Types设计
支持8种强类型：Record + Graph + Hypergraph + Temporal + Spatial
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Set
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json


# ==================== 基础类型 ====================

@dataclass
class BaseType(ABC):
    """所有类型的基类"""
    id: str
    name: str
    
    @abstractmethod
    def to_dict(self) -> dict:
        pass
    
    @abstractmethod
    def merge(self, other: 'BaseType') -> 'BaseType':
        """增量合并"""
        pass


# ==================== Record Types（记录型） ====================

@dataclass
class AutoModel(BaseType):
    """单个结构化对象（固定字段）"""
    fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "type": "AutoModel",
            "id": self.id,
            "name": self.name,
            "fields": self.fields,
            "metadata": self.metadata
        }
    
    def merge(self, other: 'AutoModel') -> 'AutoModel':
        """合并两个模型，字段取并集"""
        if not isinstance(other, AutoModel):
            raise TypeError("Can only merge AutoModel with AutoModel")
        merged_fields = {**self.fields, **other.fields}
        merged_meta = {**self.metadata, **other.metadata}
        return AutoModel(
            id=self.id,
            name=self.name,
            fields=merged_fields,
            metadata=merged_meta
        )


@dataclass
class AutoList(BaseType):
    """有序集合（保持顺序）"""
    items: List[Any] = field(default_factory=list)
    ordered: bool = True
    
    def to_dict(self) -> dict:
        return {
            "type": "AutoList",
            "id": self.id,
            "name": self.name,
            "items": self.items,
            "ordered": self.ordered
        }
    
    def merge(self, other: 'AutoList') -> 'AutoList':
        """合并两个列表，保持顺序，去重"""
        if not isinstance(other, AutoList):
            raise TypeError("Can only merge AutoList with AutoList")
        seen = set()
        merged = []
        for item in self.items + other.items:
            key = str(item)
            if key not in seen:
                seen.add(key)
                merged.append(item)
        return AutoList(id=self.id, name=self.name, items=merged)


@dataclass
class AutoSet(BaseType):
    """去重集合（自动消重）"""
    items: Set[Any] = field(default_factory=set)
    
    def to_dict(self) -> dict:
        return {
            "type": "AutoSet",
            "id": self.id,
            "name": self.name,
            "items": list(self.items)
        }
    
    def add(self, item: Any) -> None:
        self.items.add(item)
    
    def merge(self, other: 'AutoSet') -> 'AutoSet':
        """合并两个集合"""
        if not isinstance(other, AutoSet):
            raise TypeError("Can only merge AutoSet with AutoSet")
        return AutoSet(
            id=self.id,
            name=self.name,
            items=self.items | other.items
        )


# ==================== Graph Types（图结构） ====================

@dataclass
class GraphNode:
    """图节点"""
    id: str
    label: str
    type: str  # entity, concept, event, location
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "properties": self.properties
        }


@dataclass
class GraphEdge:
    """图边（二元关系）"""
    id: str
    source: str  # 源节点ID
    target: str  # 目标节点ID
    relation: str  # 关系类型
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    direction: str = "directed"  # directed, bidirectional, undirected
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "properties": self.properties,
            "weight": self.weight,
            "direction": self.direction
        }


@dataclass
class AutoGraph(BaseType):
    """二元关系知识图谱"""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "type": "AutoGraph",
            "id": self.id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }
    
    def add_node(self, node: GraphNode) -> None:
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)
    
    def add_edge(self, edge: GraphEdge) -> None:
        # 确保节点存在
        self.add_node(GraphNode(id=edge.source, label=edge.source, type="entity"))
        self.add_node(GraphNode(id=edge.target, label=edge.target, type="entity"))
        if not any(e.id == edge.id for e in self.edges):
            self.edges.append(edge)
    
    def merge(self, other: 'AutoGraph') -> 'AutoGraph':
        """合并两个图"""
        if not isinstance(other, AutoGraph):
            raise TypeError("Can only merge AutoGraph with AutoGraph")
        new_graph = AutoGraph(id=self.id, name=self.name)
        for n in self.nodes + other.nodes:
            new_graph.add_node(n)
        for e in self.edges + other.edges:
            new_graph.add_edge(e)
        return new_graph


# ==================== Hypergraph Types（超图） ====================

@dataclass
class HyperEdge:
    """超边（支持3+实体的多边关系）"""
    id: str
    label: str  # 关系标签
    entities: List[str]  # 参与者ID列表
    relation_type: str = "hyperedge"  # 超边类型
    properties: Dict[str, Any] = field(default_factory=dict)
    roles: Optional[Dict[str, List[str]]] = None  # 可选的角色分组
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "entities": self.entities,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "roles": self.roles
        }


@dataclass
class AutoHypergraph(BaseType):
    """超图 - 支持多实体（3+）参与的复杂关系"""
    nodes: List[GraphNode] = field(default_factory=list)  # 节点
    hyperedges: List[HyperEdge] = field(default_factory=list)  # 超边
    edges: List[GraphEdge] = field(default_factory=list)  # 也保留普通二元边
    
    def to_dict(self) -> dict:
        return {
            "type": "AutoHypergraph",
            "id": self.id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "hyperedges": [h.to_dict() for h in self.hyperedges],
            "edges": [e.to_dict() for e in self.edges]
        }
    
    def add_node(self, node: GraphNode) -> None:
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)
    
    def add_hyperedge(self, hyperedge: HyperEdge) -> None:
        """添加超边，同时确保关联节点存在"""
        # 添加超边中的实体作为节点
        for entity_id in hyperedge.entities:
            self.add_node(GraphNode(id=entity_id, label=entity_id, type="entity"))
        if not any(h.id == hyperedge.id for h in self.hyperedges):
            self.hyperedges.append(hyperedge)
    
    def merge(self, other: 'AutoHypergraph') -> 'AutoHypergraph':
        """合并两个超图"""
        if not isinstance(other, AutoHypergraph):
            raise TypeError("Can only merge AutoHypergraph with AutoHypergraph")
        new_hg = AutoHypergraph(id=self.id, name=self.name)
        for n in self.nodes + other.nodes:
            new_hg.add_node(n)
        for h in self.hyperedges + other.hyperedges:
            new_hg.add_hyperedge(h)
        for e in self.edges + other.edges:
            new_hg.edges.append(e)
        return new_hg


# ==================== Temporal Types（时序图） ====================

@dataclass
class TemporalEdge(GraphEdge):
    """带时间戳的边"""
    start_time: Optional[str] = None  # ISO8601
    end_time: Optional[str] = None
    duration: Optional[str] = None  # ISO8601 Duration format (PT30M)
    
    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration
        })
        return base


@dataclass
class EventNode(GraphNode):
    """事件节点"""
    time: Optional[str] = None  # ISO8601
    duration: Optional[str] = None
    event_type: str = "event"
    
    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "time": self.time,
            "duration": self.duration,
            "event_type": self.event_type
        })
        return base


@dataclass
class AutoTemporalGraph(AutoGraph):
    """时序图 - 在关系上附加时间维度"""
    events: List[EventNode] = field(default_factory=list)
    temporal_edges: List[TemporalEdge] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "type": "AutoTemporalGraph",
            "events": [e.to_dict() for e in self.events],
            "temporal_edges": [t.to_dict() for t in self.temporal_edges]
        })
        return base
    
    def add_temporal_edge(self, edge: TemporalEdge) -> None:
        self.add_node(GraphNode(id=edge.source, label=edge.source, type="entity"))
        self.add_node(GraphNode(id=edge.target, label=edge.target, type="entity"))
        if not any(e.id == edge.id for e in self.temporal_edges):
            self.temporal_edges.append(edge)
    
    def get_timeline(self) -> List[Dict]:
        """获取按时间排序的事件列表"""
        timeline = []
        for event in self.events:
            if event.time:
                timeline.append({
                    "time": event.time,
                    "event": event.label,
                    "id": event.id
                })
        return sorted(timeline, key=lambda x: x.get("time", ""))
    
    def merge(self, other: 'AutoTemporalGraph') -> 'AutoTemporalGraph':
        """合并时序图"""
        merged = super().merge(other)
        if isinstance(merged, AutoTemporalGraph):
            for e in self.events + other.events:
                if not any(ev.id == e.id for ev in merged.events):
                    merged.events.append(e)
            for te in self.temporal_edges + other.temporal_edges:
                if not any(t.id == te.id for t in merged.temporal_edges):
                    merged.temporal_edges.append(te)
        return merged


# ==================== Spatial Types（空间图） ====================

@dataclass
class LocationNode(GraphNode):
    """位置节点"""
    location: Optional[Dict[str, float]] = None  # {"lat": 39.9, "lng": 116.4}
    address: Optional[str] = None
    radius: Optional[float] = None  # 影响半径(m)
    location_type: str = "point"  # point, area, route
    
    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "location": self.location,
            "address": self.address,
            "radius": self.radius,
            "location_type": self.location_type
        })
        return base


@dataclass
class SpatialEdge(GraphEdge):
    """带空间信息的边"""
    path: Optional[List[List[float]]] = None  # [[lng, lat], ...]
    distance: Optional[float] = None  # 距离(m)
    
    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "path": self.path,
            "distance": self.distance
        })
        return base


@dataclass
class AutoSpatialGraph(AutoGraph):
    """空间图 - 附加地理位置信息"""
    locations: List[LocationNode] = field(default_factory=list)
    spatial_edges: List[SpatialEdge] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "type": "AutoSpatialGraph",
            "locations": [l.to_dict() for l in self.locations],
            "spatial_edges": [s.to_dict() for s in self.spatial_edges]
        })
        return base
    
    def add_location(self, loc: LocationNode) -> None:
        if not any(l.id == loc.id for l in self.locations):
            self.locations.append(loc)
    
    def merge(self, other: 'AutoSpatialGraph') -> 'AutoSpatialGraph':
        """合并空间图"""
        merged = super().merge(other)
        if isinstance(merged, AutoSpatialGraph):
            for l in self.locations + other.locations:
                if not any(loc.id == l.id for loc in merged.locations):
                    merged.add_location(l)
            for s in self.spatial_edges + other.spatial_edges:
                if not any(sp.id == s.id for sp in merged.spatial_edges):
                    merged.spatial_edges.append(s)
        return merged


# ==================== SpatioTemporal Types（时空图） ====================

@dataclass
class SpatioTemporalNode(LocationNode, EventNode):
    """时空节点 - 同时具有位置和时间"""
    
    def to_dict(self) -> dict:
        base = LocationNode.to_dict(self)
        base.update({
            "event_type": self.event_type,
            "time": self.time,
            "duration": self.duration
        })
        return base


@dataclass
class Trajectory:
    """轨迹 - 实体随时间和空间的变化"""
    id: str
    entity_id: str  # 追踪的实体ID
    points: List[Dict] = field(default_factory=list)  # [{"time": "", "location": [lng, lat]}]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "points": self.points
        }


@dataclass
class AutoSpatioTemporalGraph(AutoSpatialGraph, AutoTemporalGraph):
    """时空图 - 同时支持时间 + 空间"""
    spatio_temporal_nodes: List[SpatioTemporalNode] = field(default_factory=list)
    trajectories: List[Trajectory] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        base = AutoSpatialGraph.to_dict(self)
        base.update({
            "type": "AutoSpatioTemporalGraph",
            "spatio_temporal_nodes": [n.to_dict() for n in self.spatio_temporal_nodes],
            "trajectories": [t.to_dict() for t in self.trajectories]
        })
        return base
    
    def add_spatio_temporal_node(self, node: SpatioTemporalNode) -> None:
        """添加时空节点"""
        if not any(n.id == node.id for n in self.spatio_temporal_nodes):
            self.spatio_temporal_nodes.append(node)
            # 同时添加到位置列表
            loc_node = LocationNode(
                id=node.id,
                label=node.label,
                type='spatio_temporal',
                location=node.location,
                address=node.address,
                radius=node.radius
            )
            self.add_location(loc_node)
    
    def add_trajectory(self, traj: Trajectory) -> None:
        """添加轨迹"""
        if not any(t.id == traj.id for t in self.trajectories):
            self.trajectories.append(traj)
    
    def merge(self, other: 'AutoSpatioTemporalGraph') -> 'AutoSpatioTemporalGraph':
        """合并时空图"""
        new_stg = AutoSpatioTemporalGraph(id=self.id, name=self.name)
        # 合并基类数据
        for n in self.nodes + other.nodes:
            new_stg.add_node(n)
        for e in self.edges + other.edges:
            new_stg.edges.append(e)
        for e in self.events + other.events:
            if not any(ev.id == e.id for ev in new_stg.events):
                new_stg.events.append(e)
        for l in self.locations + other.locations:
            if not any(loc.id == l.id for loc in new_stg.locations):
                new_stg.add_location(l)
        for st in self.spatio_temporal_nodes + other.spatio_temporal_nodes:
            if not any(n.id == st.id for n in new_stg.spatio_temporal_nodes):
                new_stg.add_spatio_temporal_node(st)
        for t in self.trajectories + other.trajectories:
            if not any(tr.id == t.id for tr in new_stg.trajectories):
                new_stg.add_trajectory(t)
        return new_stg


# ==================== 工厂函数 ====================

def create_knowledge_graph(
    graph_type: str,
    name: str,
    **kwargs
) -> BaseType:
    """根据类型创建知识图谱"""
    type_map = {
        "AutoModel": AutoModel,
        "AutoList": AutoList,
        "AutoSet": AutoSet,
        "AutoGraph": AutoGraph,
        "AutoHypergraph": AutoHypergraph,
        "AutoTemporalGraph": AutoTemporalGraph,
        "AutoSpatialGraph": AutoSpatialGraph,
        "AutoSpatioTemporalGraph": AutoSpatioTemporalGraph,
    }
    
    if graph_type not in type_map:
        raise ValueError(f"Unknown graph type: {graph_type}. Available: {list(type_map.keys())}")
    
    return type_map[graph_type](id=kwargs.get("id", ""), name=name, **kwargs)


def merge_knowledge_graphs(
    graphs: List[BaseType],
    result_type: str,
    result_id: str = "merged",
    result_name: str = "Merged Graph"
) -> BaseType:
    """合并多个知识图谱"""
    if not graphs:
        raise ValueError("No graphs to merge")
    
    if len(graphs) == 1:
        return graphs[0]
    
    # 使用第一个图作为基础，依次合并
    result = graphs[0]
    for g in graphs[1:]:
        result = result.merge(g)
    
    return result


# ==================== 序列化工具 ====================

def save_knowledge_graph(kg: BaseType, filepath: str) -> None:
    """保存知识图谱到JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(kg.to_dict(), f, ensure_ascii=False, indent=2)


def load_knowledge_graph(filepath: str) -> dict:
    """从JSON文件加载知识图谱"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
