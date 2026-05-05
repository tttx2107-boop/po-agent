"""
知识图谱构建系统 - KG System
融合 Hyper-Extract 的三层架构设计

主要模块:
- types: 8种强类型知识图谱
- methods: 提取引擎（RAG-based + Typical）
- templates: 声明式YAML模板
- visualizer: 可视化编译器
- evolver: 增量演进系统
- llm_client: LLM客户端

用法:
    from kg_system import KGBuilder
    
    builder = KGBuilder(template_name='fire_emergency')
    kg = builder.extract(text)
"""

from kg_system.types import (
    # 基础类型
    BaseType,
    # Record Types
    AutoModel,
    AutoList,
    AutoSet,
    # Graph Types
    AutoGraph,
    AutoHypergraph,
    AutoTemporalGraph,
    AutoSpatialGraph,
    AutoSpatioTemporalGraph,
    GraphNode,
    GraphEdge,
    HyperEdge,
    EventNode,
    LocationNode,
    SpatioTemporalNode,
    TemporalEdge,
    SpatialEdge,
    Trajectory,
    # 工具函数
    create_knowledge_graph,
    merge_knowledge_graphs as merge_kg,
    save_knowledge_graph,
    load_knowledge_graph,
)

from kg_system.methods import get_extractor, list_methods
from kg_system.visualizer import compile_knowledge_graph, get_visualizer
from kg_system.templates import get_template, list_templates
from kg_system.evolver import IncrementalEvolver, merge_knowledge_graphs as merge_kg_func, DiffResult
from kg_system.llm_client import (
    LLMConfig,
    LLMProvider,
    create_llm_client,
    load_from_env,
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    LocalClient,
    DashScopeClient,
)

# KGBuilder 需要在evolver导入之后定义，避免循环依赖
class KGBuilder:
    """知识图谱构建器"""
    
    def __init__(self, template_name: str = None, method: str = 'graphrag', llm_client=None):
        from kg_system.templates import get_template
        from kg_system.methods import get_extractor
        
        self.template = get_template(template_name) if template_name else None
        self.method = method
        self.llm_client = llm_client
        self.extractor = get_extractor(method, llm_client)
    
    def extract(self, text: str, graph_type: str = 'AutoGraph'):
        from kg_system.types import (
            AutoGraph, AutoHypergraph, AutoTemporalGraph,
            AutoSpatioTemporalGraph, GraphNode, GraphEdge,
            HyperEdge, EventNode, SpatioTemporalNode,
            Trajectory, TemporalEdge
        )
        
        schema = self.template.to_dict().get('schema', {}) if self.template else None
        result = self.extractor.extract(text, schema)
        return self._build_graph(result, graph_type)
    
    def _build_graph(self, result, graph_type: str):
        from kg_system.types import (
            AutoGraph, AutoHypergraph, AutoTemporalGraph,
            AutoSpatioTemporalGraph, GraphNode, GraphEdge,
            HyperEdge, EventNode, SpatioTemporalNode, Trajectory, TemporalEdge
        )
        
        if graph_type == 'AutoGraph':
            kg = AutoGraph(id='kg_001', name='Knowledge Graph')
            for e in result.entities:
                kg.add_node(GraphNode(id=e.get('id', e.get('name', '')), label=e.get('name', ''), type=e.get('type', 'concept')))
            for r in result.relations:
                kg.add_edge(GraphEdge(id=r.get('id', f"edge_{len(kg.edges)}"), source=r.get('source', ''), target=r.get('target', ''), relation=r.get('relation', '')))
            return kg
        
        elif graph_type == 'AutoHypergraph':
            kg = AutoHypergraph(id='kg_001', name='Hyper Knowledge Graph')
            for e in result.entities:
                kg.add_node(GraphNode(id=e.get('id', e.get('name', '')), label=e.get('name', ''), type=e.get('type', 'concept')))
            for he in result.hyperedges:
                kg.add_hyperedge(HyperEdge(id=he.get('id', f"he_{len(kg.hyperedges)}"), label=he.get('label', ''), entities=he.get('entities', []), relation_type=he.get('relation_type', 'hyperedge')))
            for r in result.relations:
                kg.edges.append(GraphEdge(id=r.get('id', f"edge_{len(kg.edges)}"), source=r.get('source', ''), target=r.get('target', ''), relation=r.get('relation', '')))
            return kg
        
        elif graph_type == 'AutoTemporalGraph':
            kg = AutoTemporalGraph(id='kg_001', name='Temporal Knowledge Graph')
            for e in result.entities:
                kg.add_node(GraphNode(id=e.get('id', e.get('name', '')), label=e.get('name', ''), type=e.get('type', 'concept')))
            for t in result.temporal:
                kg.events.append(EventNode(id=t.get('id', ''), label=t.get('event', ''), type='event', time=t.get('time')))
            return kg
        
        elif graph_type == 'AutoSpatioTemporalGraph':
            kg = AutoSpatioTemporalGraph(id='kg_001', name='Spatio-Temporal Knowledge Graph')
            for st in result.temporal + result.spatial:
                if st.get('location') or st.get('time'):
                    node = SpatioTemporalNode(id=st.get('id', st.get('event', '')), label=st.get('event', st.get('name', '')), type='spatio_temporal', time=st.get('time'), location=st.get('location'))
                    kg.add_spatio_temporal_node(node)
            for traj in result.trajectories:
                kg.add_trajectory(Trajectory(id=traj.get('id', ''), entity_id=traj.get('entity_id', ''), points=traj.get('points', [])))
            for he in result.hyperedges:
                kg.add_hyperedge(HyperEdge(id=he.get('id', f"he_{len(kg.hyperedges)}"), label=he.get('label', ''), entities=he.get('entities', [])))
            return kg
        
        else:
            raise ValueError(f"Unknown graph type: {graph_type}")

__version__ = "3.0.0"

__all__ = [
    # KGBuilder
    "KGBuilder",
    # Types
    "BaseType",
    "AutoModel", "AutoList", "AutoSet",
    "AutoGraph", "AutoHypergraph",
    "AutoTemporalGraph", "AutoSpatialGraph", "AutoSpatioTemporalGraph",
    "GraphNode", "GraphEdge", "HyperEdge",
    "EventNode", "LocationNode", "SpatioTemporalNode",
    "TemporalEdge", "SpatialEdge", "Trajectory",
    "create_knowledge_graph", "merge_kg",
    "save_knowledge_graph", "load_knowledge_graph",
    # Methods
    "get_extractor", "list_methods",
    # Visualizer
    "compile_knowledge_graph", "get_visualizer",
    # Templates
    "get_template", "list_templates",
    # Evolver
    "IncrementalEvolver", "merge_kg_func", "DiffResult",
    # LLM
    "LLMConfig", "LLMProvider", "create_llm_client", "load_from_env",
    "BaseLLMClient", "OpenAIClient", "AnthropicClient", "LocalClient", "DashScopeClient",
]
