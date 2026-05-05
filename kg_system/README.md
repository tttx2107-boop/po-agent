# 知识图谱构建系统 v3.0

融合 Hyper-Extract 核心思想的三层架构知识图谱构建系统。

## 目录结构

```
kg_system/
├── __init__.py          # 主入口
├── main.py              # CLI 命令行工具
├── types/               # Layer 1: 数据类型层
│   └── __init__.py     # 8种强类型定义
├── methods/             # Layer 2: 算法层
│   └── __init__.py     # 提取引擎
├── templates/           # Layer 3: 配置层
│   └── __init__.py     # YAML模板系统
├── visualizer/           # 可视化编译器
│   └── __init__.py     # Mermaid/D3/GeoJSON
└── requirements.txt     # 依赖
```

## 核心能力

### 8种强类型（Auto-Types）

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **AutoModel** | 单个结构化对象 | 论文摘要、产品规格 |
| **AutoList** | 有序集合 | 排行榜、操作步骤 |
| **AutoSet** | 去重集合 | 关键词列表 |
| **AutoGraph** | 二元关系图 | 经典知识图谱 |
| **AutoHypergraph** | 超图（3+实体） | 多方协作、联合行动 |
| **AutoTemporalGraph** | 时序图 | 事件时间线 |
| **AutoSpatialGraph** | 空间图 | 设施布局、扩散路径 |
| **AutoSpatioTemporalGraph** | 时空图 | 应急事件4W分析 |

### 提取引擎（Methods）

- **RAG-based**: GraphRAG, HypergraphRAG, LightRAG
- **Typical**: KG-Gen, iText2KG

### 预置模板

- `fire_emergency`: 消防应急知识图谱
- `academic_paper`: 学术论文知识图谱

## 安装

```bash
pip install pydantic pyyaml

# 可选依赖
pip install networkx folium  # 地理可视化
pip install openai         # LLM集成
```

## 使用方法

### Python API

```python
from kg_system import KGBuilder, compile_knowledge_graph

# 创建构建器
builder = KGBuilder(template_name='fire_emergency', method='graphrag')

# 提取知识图谱
kg = builder.extract(text, graph_type='AutoSpatioTemporalGraph')

# 可视化
mermaid_code = compile_knowledge_graph(kg.to_dict(), 'mermaid')
```

### CLI 命令

```bash
# 提取
python main.py extract --input doc.txt --template fire_emergency --output kg.json

# 可视化
python main.py visualize --input kg.json --format mermaid --output graph.mmd

# 模板管理
python main.py template list
python main.py template show --name fire_emergency

# 方法列表
python main.py method list
```

## 示例

### 创建超图

```python
from kg_system.types import AutoHypergraph, HyperEdge

hg = AutoHypergraph(id='test', name='应急超图')
hg.add_hyperedge(HyperEdge(
    id='he1',
    label='协同灭火',
    entities=['消防队A', '消防队B', '指挥中心'],
    relation_type='hyperedge',
    roles={'leader': '指挥中心', 'execute': ['消防队A', '消防队B']}
))
```

### 创建时空图

```python
from kg_system.types import AutoSpatioTemporalGraph, SpatioTemporalNode

stg = AutoSpatioTemporalGraph(id='evt1', name='泄漏事件')
stg.add_spatio_temporal_node(SpatioTemporalNode(
    id='泄漏',
    label='液化气泄漏',
    time='2024-03-15T14:30:00',
    location={'lat': 39.9, 'lng': 116.4}
))
```

## 依赖

- Python >= 3.10
- pydantic >= 2.0.0
- pyyaml >= 6.0

## TODO

- [ ] 完善 LLM 集成调用
- [ ] 实现增量演进（feed/merge）
- [ ] 添加更多预置模板
- [ ] GeoJSON 时空可视化
- [ ] D3.js 超图可视化
