# SPDX-License-Identifier: MIT
"""
Visualization API Routes for Multimodal Knowledge Graph System
Handles KG visualization generation and rendering
"""
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.schemas.models import (
    VisualizationRequest,
    VisualizationResponse
)
from app.core.config import settings

logger.add(lambda msg: print(msg))

router = APIRouter(prefix="", tags=["visualization"])


def get_visualization_dir() -> Path:
    """Get or create visualization directory"""
    viz_dir = Path(settings.data_dir) / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    return viz_dir


@router.post("/generate", response_model=VisualizationResponse)
async def generate_visualization(request: VisualizationRequest):
    """
    Generate visualization for a knowledge graph
    
    - **kg_id**: Knowledge graph ID
    - **format**: Visualization format (mermaid, d3, echarts, plotly, graphviz)
    - **max_nodes**: Maximum nodes to display
    - **theme**: Optional theme
    """
    try:
        # In production, generate actual visualization
        # For demo, generate mock code
        
        format_type = request.format.lower()
        
        if format_type == "mermaid":
            code = generate_mermaid_code(request.kg_id, request.max_nodes)
        elif format_type == "d3":
            code = generate_d3_json(request.kg_id, request.max_nodes)
        elif format_type == "echarts":
            code = generate_echarts_option(request.kg_id, request.max_nodes)
        elif format_type == "plotly":
            code = generate_plotly_figure(request.kg_id, request.max_nodes)
        elif format_type == "graphviz":
            code = generate_graphviz_code(request.kg_id, request.max_nodes)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {request.format}"
            )
        
        # Save visualization
        viz_path = get_visualization_dir() / f"{request.kg_id}_{request.format}.txt"
        viz_path.write_text(code if isinstance(code, str) else str(code))
        
        logger.info(f"Generated {request.format} visualization for KG: {request.kg_id}")
        
        return VisualizationResponse(
            kg_id=request.kg_id,
            format=request.format,
            code=code if isinstance(code, str) else str(code),
            render_url=f"/api/visualization/render/{request.kg_id}?format={request.format}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/render/{kg_id}")
async def render_visualization(
    kg_id: str,
    format: str = Query("mermaid", description="Visualization format")
):
    """
    Render a knowledge graph visualization
    
    - **kg_id**: Knowledge graph ID
    - **format**: Visualization format
    """
    try:
        viz_path = get_visualization_dir() / f"{kg_id}_{format}.txt"
        
        if not viz_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Visualization not found for KG: {kg_id}"
            )
        
        return FileResponse(
            path=str(viz_path),
            media_type="text/plain",
            filename=f"{kg_id}_{format}.txt"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported visualization formats"""
    return {
        "formats": [
            {"id": "mermaid", "name": "Mermaid", "description": "Mermaid diagram syntax"},
            {"id": "d3", "name": "D3.js", "description": "D3.js force-directed graph"},
            {"id": "echarts", "name": "ECharts", "description": "Apache ECharts knowledge graph"},
            {"id": "plotly", "name": "Plotly", "description": "Plotly network graph"},
            {"id": "graphviz", "name": "Graphviz", "description": "Graphviz DOT format"}
        ]
    }


# Visualization generation helpers
def generate_mermaid_code(kg_id: str, max_nodes: int) -> str:
    """Generate Mermaid diagram code"""
    code = f"""%% Knowledge Graph Visualization: {kg_id}
%% Generated: {datetime.utcnow().isoformat()}

graph TD
    %% Nodes would be populated from KG entities
    A[Knowledge Graph<br/>{kg_id}]
    B[Entities]
    C[Relationships]
    
    A --> B
    A --> C
    
    %% Add more nodes as needed
    B --> D[...]
    C --> E[...]
"""
    return code


def generate_d3_json(kg_id: str, max_nodes: int) -> str:
    """Generate D3.js JSON format"""
    import json
    data = {
        "nodes": [
            {"id": "kg_root", "group": 1, "label": f"KG {kg_id}"}
        ],
        "links": []
    }
    return json.dumps(data, indent=2)


def generate_echarts_option(kg_id: str, max_nodes: int) -> str:
    """Generate ECharts option configuration"""
    option = {
        "title": {"text": f"Knowledge Graph - {kg_id}"},
        "tooltip": {},
        "series": [{
            "type": "graph",
            "layout": "force",
            "data": [],
            "links": [],
            "roam": True,
            "label": {"show": True},
            "force": {"repulsion": 100}
        }]
    }
    import json
    return json.dumps(option, indent=2)


def generate_plotly_figure(kg_id: str, max_nodes: int) -> str:
    """Generate Plotly figure configuration"""
    figure = {
        "data": [{
            "type": "scatter",
            "mode": "markers+text",
            "x": [],
            "y": [],
            "text": [],
            "marker": {"size": 20}
        }],
        "layout": {
            "title": f"Knowledge Graph - {kg_id}",
            "showlegend": False
        }
    }
    import json
    return json.dumps(figure, indent=2)


def generate_graphviz_code(kg_id: str, max_nodes: int) -> str:
    """Generate Graphviz DOT format"""
    code = f"""// Knowledge Graph Visualization: {kg_id}
// Generated: {datetime.utcnow().isoformat()}

digraph KG_{kg_id.replace("-", "_")} {{
    rankdir=TB;
    node [shape=box, style=rounded];
    
    kg_{kg_id.replace("-", "_")} [label="Knowledge Graph\\n{kg_id}"];
}}
"""
    return code
