"""
知识图谱可视化编译器 - Skill 12
支持 Mermaid.js, D3.js, ECharts, GeoJSON 等多种格式
"""

from typing import List, Dict, Any, Optional
import json


class BaseVisualizer:
    """可视化基类"""
    
    def compile(self, kg_data: dict) -> str:
        """编译图谱数据为可视化代码"""
        raise NotImplementedError
    
    def _extract_nodes(self, kg_data: dict) -> List[dict]:
        """提取节点"""
        return kg_data.get('nodes', [])
    
    def _extract_edges(self, kg_data: dict) -> List[dict]:
        """提取边"""
        return kg_data.get('edges', [])
    
    def _extract_hyperedges(self, kg_data: dict) -> List[dict]:
        """提取超边"""
        return kg_data.get('hyperedges', [])
    
    def _sanitize_id(self, text: str) -> str:
        """清理ID为安全格式"""
        return text.replace(' ', '_').replace('-', '_').replace('.', '_').replace('(', '').replace(')', '')[:50]


class MermaidVisualizer(BaseVisualizer):
    """Mermaid.js 可视化编译器"""
    
    # 颜色配置
    COLORS = {
        'person': '#e3f2fd:#1565c0',
        'organization': '#fff3e0:#e65100',
        'location': '#e8f5e9:#2e7d32',
        'event': '#ffebee:#c62828',
        'concept': '#f3e5f5:#7b1fa2',
        'default': '#f5f5f5:#757575'
    }
    
    def compile(self, kg_data: dict) -> str:
        graph_type = kg_data.get('type', 'AutoGraph')
        
        if graph_type in ['AutoTemporalGraph', 'AutoSpatioTemporalGraph']:
            return self._compile_temporal_mermaid(kg_data)
        elif graph_type == 'AutoHypergraph':
            return self._compile_hypergraph_mermaid(kg_data)
        else:
            return self._compile_basic_mermaid(kg_data)
    
    def _compile_basic_mermaid(self, kg_data: dict) -> str:
        """编译基础图谱"""
        lines = ['%%{init: {\'theme\': \'base\', \'themeVariables\': {\'fontSize\': \'14px\'}}}%%', '']
        lines.append('flowchart TB')
        lines.append('')
        
        # 节点
        node_ids = set()
        for node in self._extract_nodes(kg_data):
            node_id = self._sanitize_id(node.get('id', ''))
            if node_id and node_id not in node_ids:
                label = node.get('label', node.get('name', node_id))
                node_type = node.get('type', 'default')
                fill, stroke = self._get_colors(node_type)
                lines.append(f'    {node_id}["{label}"]')
                lines.append(f'    style {node_id} fill:{fill},stroke:{stroke}')
                node_ids.add(node_id)
        
        lines.append('')
        
        # 边
        for edge in self._extract_edges(kg_data):
            source = self._sanitize_id(edge.get('source', ''))
            target = self._sanitize_id(edge.get('target', ''))
            if source and target and source in node_ids and target in node_ids:
                relation = edge.get('relation', '相关')
                lines.append(f'    {source} -->|{relation}| {target}')
        
        return '\n'.join(lines)
    
    def _compile_hypergraph_mermaid(self, kg_data: dict) -> str:
        """编译超图（使用subgraph模拟）"""
        lines = ['%%{init: {\'theme\': \'base\', \'themeVariables\': {\'fontSize\': \'14px\'}}}%%', '']
        lines.append('flowchart TB')
        lines.append('')
        
        # 节点
        node_ids = set()
        for node in self._extract_nodes(kg_data):
            node_id = self._sanitize_id(node.get('id', ''))
            if node_id and node_id not in node_ids:
                label = node.get('label', node.get('name', node_id))
                node_type = node.get('type', 'default')
                fill, stroke = self._get_colors(node_type)
                lines.append(f'    {node_id}["{label}"]')
                lines.append(f'    style {node_id} fill:{fill},stroke:{stroke}')
                node_ids.add(node_id)
        
        lines.append('')
        
        # 超边（用subgraph模拟）
        for hyperedge in self._extract_hyperedges(kg_data):
            he_id = self._sanitize_id(hyperedge.get('id', ''))
            label = hyperedge.get('label', hyperedge.get('relation_type', '关系'))
            entities = hyperedge.get('entities', [])
            
            # 过滤有效的实体ID
            valid_entities = [self._sanitize_id(e) for e in entities if self._sanitize_id(e)]
            
            if valid_entities:
                lines.append(f'    subgraph "【超边】{label}"')
                for entity_id in valid_entities[:6]:  # 限制显示数量
                    lines.append(f'        {entity_id}')
                lines.append('    end')
                lines.append('')
                
                # 超边连接到目标实体
                for entity_id in valid_entities:
                    lines.append(f'    {entity_id} -.->|{label}| {valid_entities[-1]}')
        
        lines.append('')
        
        # 普通边
        for edge in self._extract_edges(kg_data):
            source = self._sanitize_id(edge.get('source', ''))
            target = self._sanitize_id(edge.get('target', ''))
            if source and target:
                relation = edge.get('relation', '相关')
                lines.append(f'    {source} -->|{relation}| {target}')
        
        return '\n'.join(lines)
    
    def _compile_temporal_mermaid(self, kg_data: dict) -> str:
        """编译时序图"""
        lines = ['%%{init: {\'theme\': \'base\', \'themeVariables\': {\'fontSize\': \'14px\'}}}%%', '']
        lines.append('timeline')
        lines.append('')
        
        # 获取时间线事件
        events = kg_data.get('events', kg_data.get('temporal_events', []))
        
        if not events:
            return self._compile_basic_mermaid(kg_data)
        
        # 按时间排序
        sorted_events = sorted(events, key=lambda x: x.get('time', ''))
        
        for event in sorted_events:
            time = event.get('time', '未知时间')
            label = event.get('label', event.get('event', '事件'))
            # 只显示日期部分
            time_display = time[:10] if len(time) >= 10 else time
            lines.append(f'    {time_display}: {label}')
        
        lines.append('')
        lines.append('    %% 关系网络')
        
        # 普通边
        for edge in self._extract_edges(kg_data):
            source = self._sanitize_id(edge.get('source', ''))
            target = self._sanitize_id(edge.get('target', ''))
            if source and target:
                relation = edge.get('relation', '相关')
                lines.append(f'    {source} -->|{relation}| {target}')
        
        return '\n'.join(lines)
    
    def _get_colors(self, node_type: str) -> tuple:
        """获取节点颜色"""
        return self.COLORS.get(node_type, self.COLORS['default']).split(':')


class D3Visualizer(BaseVisualizer):
    """D3.js 可视化编译器"""
    
    def compile(self, kg_data: dict) -> str:
        graph_type = kg_data.get('type', 'AutoGraph')
        
        if graph_type == 'AutoSpatioTemporalGraph':
            return self._compile_spatiotemporal_d3(kg_data)
        elif graph_type == 'AutoHypergraph':
            return self._compile_hypergraph_d3(kg_data)
        else:
            return self._compile_basic_d3(kg_data)
    
    def _compile_basic_d3(self, kg_data: dict) -> str:
        """生成D3.js力导向图HTML"""
        nodes = []
        for n in self._extract_nodes(kg_data):
            nodes.append({
                "id": self._sanitize_id(n.get('id', '')),
                "label": n.get('label', n.get('name', '')),
                "type": n.get('type', 'default')
            })
        
        links = []
        for e in self._extract_edges(kg_data):
            links.append({
                "source": self._sanitize_id(e.get('source', '')),
                "target": self._sanitize_id(e.get('target', '')),
                "relation": e.get('relation', '')
            })
        
        nodes_json = json.dumps(nodes, ensure_ascii=False)
        links_json = json.dumps(links, ensure_ascii=False)
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>知识图谱可视化</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        svg {{ width: 100vw; height: 100vh; }}
        .node {{ stroke: #fff; stroke-width: 2px; cursor: pointer; }}
        .node:hover {{ stroke-width: 4px; }}
        .link {{ stroke: #999; stroke-opacity: 0.6; }}
        .link-label {{ font: 10px sans-serif; fill: #666; }}
        text {{ font: 12px sans-serif; pointer-events: none; }}
        .tooltip {{ 
            position: absolute; 
            padding: 8px; 
            background: white; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
        }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <div id="tooltip" class="tooltip" style="display:none;"></div>
    <script>
        const nodes = {nodes_json};
        const links = {links_json};
        
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        // 颜色映射
        const colorMap = {{
            person: "#1565c0",
            organization: "#e65100",
            location: "#2e7d32",
            event: "#c62828",
            concept: "#7b1fa2",
            default: "#757575"
        }};
        
        const svg = d3.select("#graph").append("svg")
            .attr("width", width).attr("height", height);
        
        // 添加缩放
        const g = svg.append("g");
        svg.call(d3.zoom().scaleExtent([0.1, 4]).on("zoom", (event) => {{
            g.attr("transform", event.transform);
        }}));
        
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width/2, height/2))
            .force("collision", d3.forceCollide().radius(30));
        
        // 绘制边
        const link = g.append("g")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("class", "link")
            .attr("stroke-width", d => d.relation ? 2 : 1);
        
        // 边的标签
        const linkLabel = g.append("g")
            .selectAll("text")
            .data(links.filter(l => l.relation))
            .join("text")
            .attr("class", "link-label")
            .text(d => d.relation);
        
        // 绘制节点
        const node = g.append("g")
            .selectAll("g")
            .data(nodes)
            .join("g")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        node.append("circle")
            .attr("class", "node")
            .attr("r", 12)
            .attr("fill", d => colorMap[d.type] || colorMap.default);
        
        node.append("text")
            .attr("dx", 15).attr("dy", 4)
            .text(d => d.label);
        
        // tooltip
        const tooltip = d3.select("#tooltip");
        
        node.on("mouseover", (event, d) => {{
            tooltip.style("display", "block")
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px")
                .html(`<strong>${{d.label}}</strong><br/>类型: ${{d.type}}`);
        }}).on("mouseout", () => {{
            tooltip.style("display", "none");
        }});
        
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            linkLabel
                .attr("x", d => (d.source.x + d.target.x) / 2)
                .attr("y", d => (d.source.y + d.target.y) / 2);
            
            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});
        
        function dragstarted(event) {{ if (!event.active) simulation.alphaTarget(0.3).restart(); }}
        function dragged(event, d) {{ d.fx = event.x; d.fy = event.y; }}
        function dragended(event) {{ if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }}
    </script>
</body>
</html>'''
    
    def _compile_hypergraph_d3(self, kg_data: dict) -> str:
        """生成超图D3可视化"""
        nodes = []
        hyperedges = self._extract_hyperedges(kg_data)
        
        # 收集所有实体节点
        entity_ids = set()
        for he in hyperedges:
            for e in he.get('entities', []):
                entity_ids.add(e)
        
        # 添加超边节点
        for he_id, he in enumerate(hyperedges):
            nodes.append({
                "id": f"he_{he_id}",
                "label": he.get('label', '超边'),
                "type": "hyperedge",
                "entities": he.get('entities', [])
            })
        
        # 添加实体节点
        for n in self._extract_nodes(kg_data):
            nid = self._sanitize_id(n.get('id', ''))
            if nid in entity_ids:
                nodes.append({
                    "id": nid,
                    "label": n.get('label', n.get('name', nid)),
                    "type": n.get('type', 'entity')
                })
        
        # 超边到实体的连接
        links = []
        for he_id, he in enumerate(hyperedges):
            for entity in he.get('entities', []):
                links.append({
                    "source": f"he_{he_id}",
                    "target": self._sanitize_id(entity),
                    "relation": "参与"
                })
        
        nodes_json = json.dumps(nodes, ensure_ascii=False)
        links_json = json.dumps(links, ensure_ascii=False)
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>超图可视化</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        svg {{ width: 100vw; height: 100vh; }}
        .node {{ stroke: #fff; stroke-width: 2px; cursor: pointer; }}
        .hyperedge {{ stroke: #9c27b0; stroke-width: 3px; fill: #e1bee7; }}
        .link {{ stroke: #999; stroke-opacity: 0.4; stroke-dasharray: 5,5; }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <script>
        const nodes = {nodes_json};
        const links = {links_json};
        
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const svg = d3.select("#graph").append("svg")
            .attr("width", width).attr("height", height);
        
        const g = svg.append("g");
        
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-500))
            .force("center", d3.forceCenter(width/2, height/2));
        
        // 超边样式
        const hypernode = g.append("g")
            .selectAll("rect")
            .data(nodes.filter(n => n.type === "hyperedge"))
            .join("rect")
            .attr("class", "node hyperedge")
            .attr("rx", 10)
            .attr("width", 120)
            .attr("height", 40);
        
        const hypernodeLabel = g.append("g")
            .selectAll("text")
            .data(nodes.filter(n => n.type === "hyperedge"))
            .join("text")
            .text(d => d.label)
            .attr("text-anchor", "middle")
            .attr("dy", "0.35em")
            .attr("fill", "#7b1fa2");
        
        // 实体节点
        const entitynode = g.append("g")
            .selectAll("circle")
            .data(nodes.filter(n => n.type !== "hyperedge"))
            .join("circle")
            .attr("class", "node")
            .attr("r", 10)
            .attr("fill", "#757575");
        
        const entitynodeLabel = g.append("g")
            .selectAll("text")
            .data(nodes.filter(n => n.type !== "hyperedge"))
            .join("text")
            .text(d => d.label)
            .attr("dx", 15).attr("dy", 4);
        
        // 边
        const link = g.append("g")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("class", "link");
        
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            hypernode.attr("x", d => d.x - 60).attr("y", d => d.y - 20);
            hypernodeLabel.attr("x", d => d.x).attr("y", d => d.y);
            
            entitynode.attr("cx", d => d.x).attr("cy", d => d.y);
            entitynodeLabel.attr("x", d => d.x).attr("y", d => d.y);
        }});
    </script>
</body>
</html>'''
    
    def _compile_spatiotemporal_d3(self, kg_data: dict) -> str:
        """生成时空图D3可视化"""
        # 时空节点
        st_nodes = kg_data.get('spatio_temporal_nodes', [])
        locations = kg_data.get('locations', kg_data.get('spatial_entities', []))
        
        nodes = []
        for i, st in enumerate(st_nodes):
            nodes.append({
                "id": st.get('id', f'st_{i}'),
                "label": st.get('label', st.get('event', f'事件{i}')),
                "type": "spatio_temporal",
                "lat": st.get('location', {}).get('lat'),
                "lng": st.get('location', {}).get('lng'),
                "time": st.get('time', '')
            })
        
        # 轨迹
        trajectories = kg_data.get('trajectories', [])
        
        nodes_json = json.dumps(nodes, ensure_ascii=False)
        trajectories_json = json.dumps(trajectories, ensure_ascii=False)
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>时空图可视化</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        svg {{ width: 100vw; height: 100vh; }}
        .event-node {{ fill: #c62828; stroke: #fff; stroke-width: 2px; cursor: pointer; }}
        .trajectory {{ fill: none; stroke: #1565c0; stroke-width: 2; opacity: 0.6; }}
        .timeline {{ fill: none; stroke: #666; stroke-width: 1; }}
        text {{ font: 11px sans-serif; }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <script>
        const nodes = {nodes_json};
        const trajectories = {trajectories_json};
        
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const svg = d3.select("#graph").append("svg")
            .attr("width", width).attr("height", height);
        
        // 简单散点图（用于展示）
        const g = svg.append("g");
        
        // 绘制时间线
        g.append("line")
            .attr("class", "timeline")
            .attr("x1", 50).attr("y1", height/2)
            .attr("x2", width - 50).attr("y2", height/2);
        
        // 绘制轨迹
        const trajectoryLine = d3.line()
            .x(d => d.location ? (d.location[0] + 180) * 0.5 : 0)
            .y(d => d.time ? parseInt(d.time.split('T')[0].split('-')[2]) * 2 : 0);
        
        trajectories.forEach(traj => {{
            if (traj.points && traj.points.length > 1) {{
                g.append("path")
                    .attr("class", "trajectory")
                    .attr("d", trajectoryLine(traj.points));
            }}
        }});
        
        // 绘制事件节点
        const node = g.selectAll("circle")
            .data(nodes)
            .join("circle")
            .attr("class", "event-node")
            .attr("r", 15)
            .attr("cx", (d, i) => 100 + i * 150)
            .attr("cy", height/2);
        
        // 标签
        g.selectAll("text")
            .data(nodes)
            .join("text")
            .text(d => d.label + (d.time ? '\\n' + d.time.slice(0, 10) : ''))
            .attr("x", (d, i) => 100 + i * 150)
            .attr("y", height/2 + 35)
            .attr("text-anchor", "middle");
        
        // 时间轴标签
        g.append("text").attr("x", 50).attr("y", height/2 - 20).text("时间线");
    </script>
</body>
</html>'''


class GeoJSONVisualizer:
    """GeoJSON 导出器 - 用于时空图的地理可视化"""
    
    def compile(self, kg_data: dict) -> dict:
        """导出为GeoJSON格式"""
        features = []
        
        # 位置节点
        for loc in kg_data.get('locations', kg_data.get('spatial_entities', [])):
            if loc.get('location'):
                loc_data = loc['location']
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [loc_data.get('lng', 0), loc_data.get('lat', 0)]
                    },
                    "properties": {
                        "id": loc.get('id', ''),
                        "name": loc.get('label', loc.get('name', '')),
                        "type": "location",
                        "address": loc.get('address', ''),
                        "radius": loc.get('radius')
                    }
                }
                features.append(feature)
        
        # 时空事件
        for event in kg_data.get('spatio_temporal_nodes', kg_data.get('temporal_events', [])):
            if event.get('location'):
                loc_data = event['location']
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [loc_data.get('lng', 0), loc_data.get('lat', 0)]
                    },
                    "properties": {
                        "id": event.get('id', ''),
                        "name": event.get('label', event.get('event', '')),
                        "type": "event",
                        "time": event.get('time', ''),
                        "duration": event.get('duration', '')
                    }
                }
                features.append(feature)
        
        # 轨迹
        for traj in kg_data.get('trajectories', []):
            if traj.get('points') and len(traj['points']) >= 2:
                coordinates = []
                for p in traj['points']:
                    if p.get('location') and len(p['location']) >= 2:
                        coordinates.append(p['location'])
                
                if coordinates:
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coordinates
                        },
                        "properties": {
                            "id": traj.get('id', ''),
                            "entity_id": traj.get('entity_id', ''),
                            "type": "trajectory"
                        }
                    }
                    features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def export(self, kg_data: dict, filepath: str) -> None:
        """导出到文件"""
        geojson = self.compile(kg_data)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)


# ==================== 编译器注册表 ====================

VISUALIZER_REGISTRY = {
    'mermaid': MermaidVisualizer,
    'd3': D3Visualizer,
    'geojson': GeoJSONVisualizer,
}


def get_visualizer(format: str) -> BaseVisualizer:
    """获取可视化编译器"""
    format_lower = format.lower()
    if format_lower not in VISUALIZER_REGISTRY:
        raise ValueError(
            f"Unknown format: {format}. "
            f"Available: {', '.join(VISUALIZER_REGISTRY.keys())}"
        )
    return VISUALIZER_REGISTRY[format_lower]()


def compile_knowledge_graph(
    kg_data: dict,
    format: str = 'mermaid'
) -> str:
    """编译知识图谱为可视化代码"""
    visualizer = get_visualizer(format)
    return visualizer.compile(kg_data)
